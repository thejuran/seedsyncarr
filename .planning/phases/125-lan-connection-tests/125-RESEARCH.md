# Phase 125: LAN Connection Tests - Research

**Researched:** 2026-10-27
**Domain:** SSRF-guard reclassification (`ConfigHandler._validate_url`), Python `ipaddress` stdlib semantics across the project's supported versions (3.11/3.12), `urlparse` port handling
**Confidence:** HIGH (every classification claim below was executed and verified this session inside `python:3.11-slim` and `python:3.12-slim` containers — the exact versions this project's CI and `pyproject.toml` require — not taken from training-data recall)

## Summary

The whole phase is one function: `ConfigHandler._validate_url` (`src/python/web/handler/config.py:58-88`), a pure `@staticmethod` with one caller (`_test_arr_connection`). Today it blocks any address where `is_private or is_loopback or is_reserved or is_link_local` is true — which conflates "the LAN addresses people actually use" with "addresses that should never be reachable" into one boolean, because Python's `ipaddress.is_private` is True for `10.0.0.0/8` **and** for `169.254.169.254` **and** for `192.0.2.1` (RFC 5737 documentation range) **and** for `::1`. D-01/D-02/D-03 require splitting that single flag into an explicit allow-list (named private ranges + loopback-on-two-specific-ports + already-public) and an explicit refuse-list (link-local/metadata, unspecified, multicast, other reserved). This cannot be done by flipping `is_private` off — it requires replacing the boolean-OR with explicit `ipaddress.ip_network(...)` membership checks, confirmed identical across Python 3.11.18 and 3.12.16 (this project's full supported range, `pyproject.toml:10`: `requires-python = ">=3.11,<3.13"`).

Two non-obvious findings materially change the plan's shape. First, **nine of the ten existing `TestValidateUrl` assertions on `"private/reserved"` must change outcome, not just wording** — `10.0.0.1`, `fc00::1`, and `::ffff:10.0.0.1` flip from reject to **accept** under D-01, and `test_rejects_multi_address_when_any_private` loses its premise entirely (both its addresses become allowed). Two handler-level tests (`test_sonarr_rejects_private_ip`, `test_radarr_rejects_private_ip`) assert rejection of `127.0.0.1` on the service's *own default port* (8989/7878) — exactly the case D-02 makes allowed — so they flip to accept and need `requests` mocked (currently they rely on the rejection short-circuiting before any real `requests.get` call). Second, **a naive "allow if `is_global`" rule is unsafe**: `::127.0.0.1` (deprecated IPv4-compatible notation) and `64:ff9b::7f00:1` (NAT64 well-known-prefix notation, both embedding `127.0.0.1`) report `is_global=True` in stdlib, which would silently defeat the loopback-port gate — but both also report `is_reserved=True`, so the correct rule is "allow if `is_global` **and not** `is_reserved`/`is_multicast`/`is_link_local`/`is_unspecified`." This single clause, verified below, also closes a real pre-existing gap: multicast (`224.0.0.1`, `ff02::1`) is **not currently blocked** (none of `is_private/is_loopback/is_reserved/is_link_local` is true for it), so D-03's "multicast ... still refused" is a genuine bug fix, not a no-op regression test.

**Primary recommendation:** Replace the single boolean check with an explicit, order-sensitive classifier — loopback-and-port gate first, then an allow-list of five named CIDR ranges, then `is_global and not (is_reserved or is_multicast or is_link_local or is_unspecified)`, else refuse with a category-specific message — built entirely on `ipaddress` stdlib (no new dependency), ported once into `_validate_url`, and proven against both the flipped and newly-added `TestValidateUrl` cases plus the two flipped handler tests, with a new grep/import-based test proving `arr_queue.py` (the only other outbound-request path in the Python backend) never touches the relaxed check.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Destination classification (allow/refuse) for Test Connection | API / Backend | — | `ConfigHandler._validate_url` runs server-side because it gates an outbound request the *server* makes on the user's behalf; the browser never sees the candidate IP addresses. |
| Outbound Sonarr/Radarr `system/status` probe | API / Backend | — | `requests.get` inside `_test_arr_connection`, unchanged by this phase except for what precedes it. |
| Test Connection result display (`{"success": bool, "error": ...}`) | Browser / Client | API / Backend | Angular settings UI renders the existing JSON shape; this phase does not touch the shape, only which inputs reach `success: true`. |
| Release-notes disclosure of the behavior change | Documentation | — | `CHANGELOG.md` edit, no runtime tier. |

## Standard Stack

No new dependency. Everything needed is already imported in `config.py` or in the Python 3.11+ standard library:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ipaddress` (stdlib) | Python 3.11.18 / 3.12.16 (project's `requires-python = ">=3.11,<3.13"`, `pyproject.toml:10`) [VERIFIED: ran identical probe scripts inside `python:3.11-slim` and `python:3.12-slim`, this session] | CIDR membership checks (`ip_network(...).__contains__`), special-purpose-address booleans (`is_loopback`, `is_link_local`, `is_multicast`, `is_unspecified`, `is_global`, `is_reserved`) | Already in use in `config.py`; no third-party SSRF library needed for this narrow, well-specified allow/refuse list |
| `urllib.parse.urlparse` (stdlib) | same | `.hostname` (already used) and **`.port`** (not currently used — needed for D-02) | Already imported; `.port` access can raise `ValueError` for a malformed port string — see Pitfall 1 |
| `socket.getaddrinfo` (stdlib) | same | Hostname → address resolution (already used, unchanged) | No change to the resolution mechanism, only to what is done with each resolved address |

### Supporting
None — no supporting libraries needed.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit `ipaddress.ip_network()` membership checks | Keep relying on `is_private`/`is_reserved` booleans alone | Rejected: these booleans conflate ranges the phase must treat differently (e.g. `is_private` is `True` for both `10.0.0.0/8` (now allowed) and `192.0.2.1`/RFC 5737 documentation range (must stay refused) — see Common Pitfall 2) |
| stdlib `ipaddress` | A third-party SSRF guard library (e.g. `ssrfpy`) | Rejected: 120-CONTEXT and 125-CONTEXT both already treat DNS-rebinding/socket-level interception as explicitly out of scope (D-06); pulling in a library for a bounded, fully-specified allow-list is unjustified scope/dependency growth for a homelab tool, consistent with the existing docstring in `_validate_url` |

**Installation:** None — no `pip install` / `poetry add` needed.

**Version verification:** `ipaddress` and `urllib.parse` ship with the interpreter; there is nothing to pin or `pip view`. The only "version" fact that matters is the interpreter range (3.11–3.12.x), verified directly against official `python:3.11-slim`/`python:3.12-slim` images rather than training data, because D-01's own discretion note calls out that `ipaddress` boolean semantics have drifted across versions.

## Package Legitimacy Audit

Not applicable — this phase introduces **zero** new external packages (Node/Python/other). No `pip install`, no new `requirements`/`pyproject` entries. Skip the slopcheck/registry-verification gate entirely; nothing to gate behind `checkpoint:human-verify`.

## Architecture Patterns

### System Architecture Diagram

```
 Angular Settings UI
        │  POST (implicit GET-style handler call, no body)
        ▼
 /server/config/{sonarr,radarr}/test-connection
        │
        ▼
 ConfigHandler._test_arr_connection(service_name, raw_url, api_key)
        │
        ├─ 1. URL/key presence + API-key-charset checks  (unchanged)
        │
        ├─ 2. ConfigHandler._validate_url(url)   ◄── THIS PHASE
        │        │
        │        ├─ urlparse → scheme/hostname/port
        │        ├─ socket.getaddrinfo(hostname) → one or more resolved IPs
        │        └─ for each resolved IP: classify(ip, port)
        │                 │
        │                 ├─ loopback? → allowed only if port ∈ {8989, 7878}   (D-02)
        │                 ├─ unspecified / link-local / multicast? → refuse    (D-03)
        │                 ├─ in allow-listed private range (10/8, 172.16/12,
        │                 │    192.168/16, 100.64/10 CGNAT, fc00::/7 ULA)? → allow (D-01)
        │                 ├─ is_global and not reserved/multicast/link-local/
        │                 │    unspecified? → allow (public, already allowed today)
        │                 └─ else → refuse ("other reserved")                 (D-03)
        │        any resolved IP refused → whole URL refused (fail-closed, D-04)
        │
        ├─ 3. requests.get(url + "/api/v3/system/status", allow_redirects=False)  (unchanged)
        │        ├─ 3xx → sanitized redirect-location refusal (unchanged, D-05)
        │        └─ 200/401/other → existing response shapes (unchanged)
        │
        └─ 4. {"success": bool, "error"/"version": ...}  (unchanged shape)

 (separate, untouched path — proves D-06 scope)
 ArrQueueClient.start_fetch() → GET {sonarr_url}/api/v3/queue/details
        — never calls _validate_url; was unguarded before this phase and stays unguarded
```

### Recommended Project Structure

No new files. All changes land in the existing two files:
```
src/python/web/handler/config.py
    └── _validate_url()                       # replace boolean-OR with classifier below
src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    └── class TestValidateUrl                 # extend in place (existing full-path harness)
    └── class TestConfigHandlerTestSonarrConnection / TestRadarr...   # fix 2 flipped tests
```

### Pattern 1: Order-sensitive address classifier (verified against Python 3.11.18 and 3.12.16)

**What:** A single function that takes a resolved `ipaddress` object and the URL's port, and returns an error string or `None`. Order matters — later checks are unsafe before earlier ones (see Pitfall 2 for why `is_global` cannot be checked first, and why loopback must be checked before `is_reserved`).

**When to use:** Inside `_validate_url`, once per resolved address from `socket.getaddrinfo`.

**Example (verified live against official `python:3.11-slim` / `python:3.12-slim`, this session):**
```python
# Source: stdlib ipaddress, semantics confirmed identical on 3.11.18 and 3.12.16
_ALLOWED_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),   # Tailscale/CGNAT -- allowed today, must not regress
    ipaddress.ip_network("fc00::/7"),        # IPv6 unique-local
)
_ALLOWED_LOOPBACK_PORTS = frozenset({8989, 7878})  # Sonarr / Radarr defaults (D-02)

def _classify(addr: "ipaddress._BaseAddress", port: int | None) -> str | None:
    """Return an error string, or None if addr:port is allowed."""
    # 1. Loopback is port-gated, checked FIRST: ::1 and ::ffff:127.0.0.1 both
    #    report is_reserved=True too, so this must run before any reserved check.
    if addr.is_loopback:
        if port in _ALLOWED_LOOPBACK_PORTS:
            return None
        return "loopback is only allowed on port 8989 (Sonarr) or 7878 (Radarr)"

    # 2. Named allow-list, checked on the effective (unmapped) address so that
    #    ::ffff:10.0.0.1 is evaluated as 10.0.0.1 against the IPv4 ranges above.
    effective = getattr(addr, "ipv4_mapped", None) or addr
    if any(effective in net for net in _ALLOWED_PRIVATE_NETWORKS):
        return None

    # 3. Public -- but is_global is True for several bypass-shaped addresses
    #    (IPv4-compatible ::127.0.0.1, NAT64 64:ff9b::7f00:1) that are ALSO
    #    is_reserved=True. The "and not" guard is load-bearing -- see Pitfall 2.
    if addr.is_global and not (addr.is_reserved or addr.is_multicast
                                or addr.is_link_local or addr.is_unspecified):
        return None

    # 4. Refuse, with a category-specific message.
    if addr.is_unspecified:
        return "URL resolves to an unspecified address, which is not allowed"
    if addr.is_link_local:
        return "URL points to a link-local or cloud-metadata address, which is not allowed"
    if addr.is_multicast:
        return "URL resolves to a multicast address, which is not allowed"
    return "URL resolves to a reserved IP address, which is not allowed"
```

Every row of the table below was executed (not recalled) inside both `python:3.11-slim` and `python:3.12-slim`; both versions produced byte-identical results for every address tested:

| Address | Outcome under `_classify` | Why |
|---|---|---|
| `10.0.0.1`, `172.16.0.1`–`172.31.255.255`, `192.168.1.1`, `fc00::1`, `fd00::1` | allow | step 2, named range |
| `100.64.0.1`–`100.127.255.255` | allow | step 2, CGNAT range |
| `100.63.255.255`, `100.128.0.1`, `172.32.0.1`, `8.8.8.8`, `1.1.1.1` | allow | step 3, `is_global` and clean |
| `127.0.0.1`, `::1`, `::ffff:127.0.0.1` on port 8989/7878 | allow | step 1 |
| `127.0.0.1` etc. on any other port or no port | refuse (loopback-port message) | step 1 |
| `169.254.169.254`, `169.254.0.1`, `fe80::1`, `::ffff:169.254.169.254` | refuse (link-local message) | step 4 |
| `0.0.0.0`, `::` | refuse (unspecified message) | step 4 |
| `224.0.0.1`, `239.255.255.255`, `ff02::1`, `ff00::1` | refuse (multicast message) | step 4 — **this is a currently-unguarded gap being closed** |
| `192.0.2.1`, `198.51.100.1`, `203.0.113.1` (RFC 5737 TEST-NET), `240.0.0.1`, `255.255.255.255` | refuse (reserved message) | step 4 — matches today's behavior |
| `::ffff:10.0.0.1` | allow | step 2, via `ipv4_mapped` unmap |
| `::ffff:169.254.169.254` | refuse (link-local) | `is_link_local` auto-delegates for mapped forms in stdlib |
| `::ffff:8.8.8.8` | allow | step 3 |
| `::127.0.0.1` (IPv4-compatible, deprecated) | refuse (reserved message) | `is_global=True` but `is_reserved=True` too — caught by the `and not` guard in step 3, falls to step 4 |
| `64:ff9b::7f00:1` (NAT64 well-known prefix embedding `127.0.0.1`) | refuse (reserved message) | same as above — **this is the concrete reason step 3 needs the `and not (...)` clause, not a bare `is_global` check** |

### Anti-Patterns to Avoid
- **Checking `is_global` before `is_reserved`/`is_multicast`/etc., or without the `and not (...)` guard:** silently allows `::127.0.0.1` and `64:ff9b::7f00:1`, both of which embed `127.0.0.1` in notations stdlib does not flag `is_loopback` for. Verified this session (python 3.11.18/3.12.16); see Pitfall 2.
- **Checking `is_reserved` before the loopback-port gate:** `::1` and `::ffff:127.0.0.1` both report `is_reserved=True` in addition to `is_loopback=True`; checking reserved first would block loopback on the allowed ports too.
- **Relying on `is_private` to mean "the LAN ranges we want to allow":** it is `True` for `10.0.0.0/8` (now allowed) and for `192.0.2.1`/RFC 5737 (must stay refused) and for `::`/`::1` (must stay refused/port-gated) — it is not a usable proxy for either allow or refuse on its own.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CIDR range membership (10/8, 172.16/12, etc.) | Manual octet/bit-math or regex on the dotted-quad string | `ipaddress.ip_network(cidr)` + `address in network` | `ipaddress` correctly handles IPv4/IPv6 version mismatches (returns `False`, never raises — verified this session) and canonicalizes notation; hand-rolled regex on IPv6 forms (`::`, `::ffff:`, zone IDs) is a well-known source of bypass bugs |
| IPv4-mapped-IPv6 unmapping (`::ffff:a.b.c.d` → `a.b.c.d`) | String-slicing the address text | `IPv6Address.ipv4_mapped` attribute | Already returns a real `IPv4Address` object usable directly in range checks; string-slicing would also need to handle the rarer `::ffff:0:a.b.c.d` variant and zone IDs |
| Special-purpose address detection (loopback, link-local, multicast, unspecified) | Hand-maintained list of CIDR blocks | `ipaddress`'s `is_loopback`/`is_link_local`/`is_multicast`/`is_unspecified` booleans | These already correctly auto-delegate through IPv4-mapped IPv6 forms (verified: `::ffff:127.0.0.1` reports `is_loopback=True` without any unmap step) |

**Key insight:** The entire phase is a correctness problem in how five already-available stdlib booleans and five CIDR ranges are combined, not a capability gap. Any amount of new regex, octet math, or custom range tables added here is pure regression risk against an already-correct stdlib.

## Common Pitfalls

### Pitfall 1: `urlparse(url).port` raises `ValueError` for malformed ports, and nothing in the current code path touches `.port`
**What goes wrong:** `_validate_url` currently never accesses `parsed.port`. Adding a bare `parsed.port` access for the D-02 loopback-port gate introduces a new, uncaught exception path: `urlparse("http://host:abc/").port` and `urlparse("http://host:99999/").port` both raise `ValueError` (confirmed this session; `.hostname` access on the same URLs does **not** raise — only `.port` is lazy-validated). `_validate_url` is called **outside** the `try/except` block that wraps `requests.get` in `_test_arr_connection` (`config.py:158`, `try:` starts at line 168) — an uncaught `ValueError` here propagates past the rate-limit wrapper and bottle's route dispatch as an unhandled exception, which is a regression from today's behavior (today, a malformed-port URL silently reaches `requests.get`, which raises its own exception, caught by the existing generic-exception handler, returning the normal 200 JSON `{"success": false, "error": "An unexpected error occurred"}`).
**Why it happens:** `.port` is a computed property with its own validation, independent of `.hostname`.
**How to avoid:** Wrap the `.port` access in `_validate_url` in `try/except ValueError` and return an explicit `"Invalid URL: invalid port"` (or similar) error string, keeping the existing "return an error string before any socket/network call" pattern already used for the scheme and no-hostname checks.
**Warning signs:** A regression test with a URL like `"http://sonarr.local:99999/"` or `"http://sonarr.local:abc/"` returning HTTP 500 instead of the normal `{"success": false, ...}` 200 JSON body.

### Pitfall 2: `is_global` alone is not a safe stand-in for "public, therefore allowed" — two concrete bypass forms embed `127.0.0.1`
**What goes wrong:** `::127.0.0.1` (deprecated IPv4-compatible IPv6 notation) and `64:ff9b::7f00:1` (the NAT64 well-known prefix `64:ff9b::/96` with `127.0.0.1` embedded in the low 32 bits) both report `is_global=True` and `is_loopback=False` in Python 3.11/3.12 stdlib — a classifier that allows anything `is_global` would let both of these resolve to a real connection to `127.0.0.1` through a URL field that never literally contains the string "localhost" or "127.0.0.1". Both addresses also report `is_reserved=True`, which is what makes the `and not (is_reserved or ...)` guard in Pattern 1 step 3 load-bearing, not cosmetic.
**Why it happens:** Python's `ipaddress.is_global` and `is_reserved` are independently computed from the IANA special-purpose registries; they are not mutually exclusive, and a quick read of just `is_global` misses that `is_reserved` can simultaneously be `True`.
**How to avoid:** Never gate the "allow" branch on `is_global` alone; always combine it with the negative checks for `is_reserved`/`is_multicast`/`is_link_local`/`is_unspecified`, as in Pattern 1.
**Warning signs:** A regression test with `http://[::127.0.0.1]:8989/` or `http://[64:ff9b::7f00:1]:8989/` (both parse and resolve as literal IPv6 addresses via `getaddrinfo`, confirmed this session) returning success instead of a refusal — this is a direct, testable loopback-port-gate bypass if present. D-08 does not explicitly name this exact pair but its spirit ("redirects to disallowed targets ... refused") and D-03's "IPv4-mapped/compatible ... forms" wording cover it; flagged as a recommended regression case, not a required one — see Open Questions.

### Pitfall 3: Nine existing `TestValidateUrl` assertions change outcome, not just message text
**What goes wrong:** Treating this phase as "just reword the error messages" will leave the test suite red or, worse, leave the implementation blocking addresses D-01 explicitly requires to work. The exact existing assertions that must flip from reject to **accept**:
- `test_rejects_ipv4_private` (`10.0.0.1`) → now allowed
- `test_rejects_ipv6_unique_local` (`fc00::1`) → now allowed
- `test_rejects_ipv6_mapped_private_ipv4` (`::ffff:10.0.0.1`) → now allowed
- `test_rejects_multi_address_when_any_private` (`[8.8.8.8, 10.0.0.1]`) → both addresses are now allowed, so the whole premise ("any private → reject") needs a *replacement* test pairing one allowed address with one still-refused address (e.g. `[8.8.8.8, 169.254.169.254]`) to keep D-04's "any refused → whole URL refused" behavior covered
- `test_sonarr_rejects_private_ip` / `test_radarr_rejects_private_ip` (both resolve to `127.0.0.1` on the service's own default port 8989/7878) → now allowed under D-02, and because these tests do not currently mock `requests`, flipping them to an accept assertion also requires adding a `requests` mock (following the exact pattern already used in `test_sonarr_accepts_public_ip`), or the flipped test would attempt a real outbound HTTP call.

The following assertions stay reject but their **message text** changes (no longer `"private/reserved"`):
- `test_rejects_ipv4_loopback`, `test_rejects_ipv6_loopback`, `test_rejects_ipv6_mapped_loopback_ipv4` — all use the no-port URL `"http://host.example/"`, so loopback stays refused under D-02 (no explicit port = refused), but now for the port-gate reason, not the old "private/reserved" reason
- `test_rejects_ipv4_link_local`, `test_rejects_ipv6_link_local`, `test_rejects_ipv6_mapped_link_local_ipv4` — stay refused, new link-local/metadata message

**Why it happens:** The existing test class's inline comment ("IPv4 reserved ranges (blocked)") pre-dates D-01's reclassification; every test written against the old single-boolean guard assumed `is_private == refused`.
**How to avoid:** Grep the whole repo for the literal string `"private/reserved"` before touching `_validate_url` (this session's grep found exactly 10 matches, all in `test_config_handler.py`, none in Angular/e2e) and walk each one against the Pattern 1 table above before deciding reject-stays-reject vs. reject-flips-to-accept.
**Warning signs:** CI green but LAN-01's real-world motivating case (`http://sonarr-v5:8989`, a Docker container name resolving to `172.19.0.6`) still failing live — i.e., tests pass because they were edited to match new text but the underlying range logic wasn't actually changed.

### Pitfall 4: `test_web_app_builder_logging.py` patches `_validate_url` directly with `return_value=None` — it is already decoupled from classification logic
**What goes wrong:** None, if left alone — flagged here only because it was one of the explicit canonical references and is easy to over-check. `ConfigHandler._validate_url` is patched wholesale (`with patch.object(ConfigHandler, "_validate_url", return_value=None)`) in every test in that file that reaches `_test_arr_connection`, so none of them exercise the real classification logic and none of them need to change for this phase.
**Why it happens:** N/A — correctly isolated by design.
**How to avoid:** Confirm (don't "fix") that this file's four tests referencing `_validate_url`/`_test_arr_connection` (`test_config_unexpected_error_logged_without_api_key`, `test_config_key_with_newline_never_reaches_requests_or_log`, `test_config_unexpected_error_with_real_invalid_header_logs_type_only`) still pass unmodified after the `_validate_url` body changes, as a build-verify step, not an edit target.
**Warning signs:** A diff touching this file when the phase's own canonical refs explicitly list it only as a "must keep working" check.

## Code Examples

### Reading the port only when it matters, with the ValueError guard from Pitfall 1
```python
# Source: this session's verification of urlparse's lazy .port validation
# (urlparse(url).hostname never raises; .port raises ValueError independently
# for non-numeric or out-of-range port strings, confirmed on 3.11.18/3.12.16)
try:
    port = parsed.port
except ValueError:
    return "Invalid URL: invalid port"
```

### Proving D-06's scope (no other outbound path reuses the relaxed check)
```python
# Source: this session's repo-wide grep -- src/python/controller/arr_queue.py:277
# is the ONLY other requests.get call site in the Python backend, and it has
# never imported or called ConfigHandler._validate_url (confirmed: grep -rn
# "_validate_url" src/python --include="*.py" returns exactly two lines, both
# inside config.py itself: the definition and its one caller).
import ast

def test_validate_url_has_exactly_one_caller_in_production_code():
    """D-06: no other outbound path is rerouted through the relaxed check."""
    src = Path("src/python/controller/arr_queue.py").read_text()
    assert "_validate_url" not in src
```
(A real test would likely use the existing test harness's import-and-grep style rather than `ast`; shown here as the proof shape, not literal final code — Claude's discretion per D-08/D-06.)

### Reusing the Phase 120/123 sandbox live-check shape for D-09
The sandbox's **current, persisted** `sonarr.sonarr_url` is `http://sonarr-v5:8989` (the Docker container name) — this is the *baseline* value Phase 120's `120-teardown.sh` restores **to** (`TARGET_URL="http://sonarr-v5:8989"`, confirmed in that script), not a value that needs to be set up for this phase's positive check. That means D-09's live check needs only **one** temporary config change (for the negative case), not two:
```bash
# Positive case (LAN-01): sonarr_url is ALREADY http://sonarr-v5:8989 (the
# baseline Phase 120 restored to). Just call test-connection -- no config
# change needed for this half of the check.
curl -s "$SSY/server/config/sonarr/test-connection"   # expect success + version

# Negative case (LAN-02): temporarily point sonarr_url at the refused address,
# check, then restore immediately (D-09 / established Phase 120 D-03 pattern).
orig="$(curl -s "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url')"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"section":"sonarr","key":"sonarr_url","value":"http://169.254.169.254"}' \
  "$SSY/server/config/set"
curl -s "$SSY/server/config/sonarr/test-connection"   # expect the new refusal message
curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"section\":\"sonarr\",\"key\":\"sonarr_url\",\"value\":\"$orig\"}" \
  "$SSY/server/config/set"   # restore immediately, verify read-back
```
This mirrors the exact `config/get` → `config/set` → read-back-verify idiom already in `120-teardown.sh` (lines 62–74) and `123-teardown.sh`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single boolean (`is_private or is_loopback or is_reserved or is_link_local`) deciding allow/refuse | Explicit allow-list (named CIDRs + loopback-port-gate + clean-`is_global`) with an explicit refuse fallback | This phase | Multicast, previously unguarded, becomes refused; `10/8`/`172.16/12`/`192.168/16`/`fc00::/7` previously refused, becomes allowed |

**Deprecated/outdated:**
- Relying on `is_private` as a refuse-signal: it was already an imprecise proxy before this phase (it refuses RFC 5737 documentation ranges, which was arguably correct, but also refuses every LAN address, which was the Phase 120 D-02 bug) — this phase replaces it with explicit range checks rather than patching around its edges.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact refusal message wording ("loopback is only allowed on port 8989...", "link-local or cloud-metadata...", etc.) is ASSUMED — D-07 gives example wording and explicitly leaves exact strings to discretion; the strings shown in this document are a recommendation, not a locked requirement. | Code Examples / Pattern 1 | None if the planner treats these as a starting point rather than a literal requirement — D-07 explicitly delegates this |
| A2 | `fec0::/10` (deprecated IPv6 "site-local", RFC 3879) is not named in any locked decision and falls through to "allowed" under the Pattern 1 classifier (`is_global=True`, no reserved/multicast/link-local/unspecified flag) in this session's verification. This is ASSUMED to be out of scope / acceptable, since it is not in D-01's or D-03's named ranges and the form is obsolete/essentially unused in practice. | Pattern 1 | Low — if the owner wants this explicitly blocked, it requires one additional named-range check (`fec0::/10`), trivial to add |
| A3 | The IPv4-compatible (`::a.b.c.d`) and NAT64 (`64:ff9b::/96`) bypass forms described in Pitfall 2 are correctly caught by the `is_reserved` guard in this session's testing, but D-03's context text names only `::ffff:` (mapped) forms explicitly as an example ("e.g. `::ffff:169.254.169.254`, `::ffff:127.0.0.1`"), not these rarer forms by name. Treating them as in-scope (since the guard already closes them for free) is ASSUMED rather than confirmed as a hard requirement. | Common Pitfalls / Pitfall 2 | Low — the recommended classifier already closes this gap at no extra cost; the only risk is a planner reading D-03 narrowly and choosing not to write a regression test for it, leaving the behavior correct but unproven |

## Open Questions

1. **Should `fec0::/10` (deprecated IPv6 site-local) be explicitly refused?**
   - What we know: it is not in D-01's allow-list nor D-03's refuse-list; stdlib reports it `is_global=True`, so Pattern 1 allows it today.
   - What's unclear: whether the owner considers this in-scope "other reserved range" (D-03's catch-all phrase) or out-of-scope because it's an obsolete, essentially-never-seen form.
   - Recommendation: leave allowed (matches "public addresses allowed today" framing — there is no record of this ever being blocked), note it in the plan's scope boundary, do not add a special case unless the owner asks.

2. **Should the implementation add explicit regression tests for the IPv4-compatible (`::127.0.0.1`) and NAT64 (`64:ff9b::7f00:1`) bypass forms from Pitfall 2?**
   - What we know: the recommended classifier already refuses both, for free, as a side effect of the `is_reserved` guard needed for other reasons.
   - What's unclear: D-08's explicit test list doesn't name these forms; they're a byproduct finding of this research session, not a locked requirement.
   - Recommendation: add them as two small bonus regression tests (cheap, directly prevents a real bypass class) but don't block phase completion on them if time-constrained — they are defense-in-depth beyond the locked D-08 list, not a requirement.

3. **Exact wording for the loopback-port refusal message when the hostname is not literally "localhost"** (e.g. a custom hostname that happens to resolve to `127.0.0.1` on port 3000).
   - What we know: D-07's example wording says "localhost is only allowed on port 8989 (Sonarr) or 7878 (Radarr)," but the actual input could be any hostname/IP that resolves to loopback.
   - What's unclear: whether the message should name the literal hostname/IP (sanitized, per D-07's redirect-location precedent) or stay fully generic.
   - Recommendation: use a fully generic message ("loopback is only allowed on port 8989 (Sonarr) or 7878 (Radarr)") as shown in Pattern 1 — avoids needing any new sanitization logic and is accurate regardless of what the user actually typed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11/3.12 | Running the full suite + confirming `ipaddress` semantics | ✓ (via Docker; local interpreter is 3.14.5, out of project range) | `python:3.11-slim` = 3.11.18, `python:3.12-slim` = 3.12.16 [VERIFIED this session] | Always verify `ipaddress` claims inside the pinned-version container, not the local 3.14 interpreter |
| `poetry` | Local test run (`cd src/python && poetry run pytest ...`) | Not independently probed this session; prior phases (122/123) used this exact command successfully | — | Docker-based `make tests-python` / `make run-tests-python` if `poetry` is unavailable locally |
| `ruff` 0.15.x | Whole-tree lint gate | ✓ local `ruff` 0.15.9 present; CI pins `ruff==0.15.22` | 0.15.9 (local) vs 0.15.22 (CI) [VERIFIED this session] | Run `ruff check src/python/` from repo root either way; versions are close enough within the 0.15 line that this is not expected to diverge, but CI is authoritative |
| NAS sandbox `seedsyncarr-test` (`ssh nas`, Docker via `sudo /usr/local/bin/docker ...`) | D-09 live check | Assumed available per user-global CLAUDE.md and prior-phase precedent; not re-probed this session (no live NAS access performed during research) | — | None — D-09 requires this specific sandbox; no fallback destination exists |

**Missing dependencies with no fallback:** None identified as blocking — all required tooling is either present or has a documented Docker-based fallback.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (`src/python/pyproject.toml`), `unittest.TestCase`-style tests |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py -p no:cacheprovider -q` |
| Full suite command | `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAN-01 | Private-range IP (10/8, 172.16/12, 192.168/16), IPv6 ULA, CGNAT 100.64/10, container-name-style mixed resolution → Test Connection succeeds | unit | `pytest tests/unittests/test_web/test_handler/test_config_handler.py::TestValidateUrl -x` | ✅ (extend existing class) |
| LAN-01 | Loopback on port 8989/7878 → Test Connection succeeds | unit | same file/class, new cases | ✅ (extend) |
| LAN-01 | Live: `http://sonarr-v5:8989` succeeds and reports version on PR CI staging image | manual (sandbox) | D-09 live check script (see Code Examples) | N/A — live-only, no automated command |
| LAN-02 | Link-local/metadata (169.254.169.254, fe80::), unspecified, multicast, other-reserved, loopback-wrong-port, mixed-with-one-refused, IPv4-mapped/compatible bypass forms → refused with specific message | unit | same file/class, new + flipped cases | ✅ (extend) |
| LAN-02 | Redirect handling unchanged (3xx → existing sanitized message) | unit | existing redirect test(s) in `TestConfigHandlerTestSonarrConnection`/`Radarr...` — confirm unaffected | ✅ (no new file) |
| LAN-02 | No other outbound path uses the relaxed check (D-06 scope proof) | unit | new small test, e.g. in `TestValidateUrl` or a new scope-proof class | ❌ — new test, no new file (add to existing test file) |
| LAN-02 | Live: `http://169.254.169.254` returns the new refusal message on the same sandbox | manual (sandbox) | D-09 live check script | N/A — live-only |

### Sampling Rate
- **Per task commit:** `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py -p no:cacheprovider -q`
- **Per wave merge:** `cd src/python && timeout 600 poetry run pytest tests/unittests -p no:cacheprovider -q` **and** `ruff check src/python/` (whole tree, from repo root — CI runs this as a separate gate, confirmed in `.github/workflows/ci.yml:94`)
- **Phase gate:** Full suite + whole-tree ruff green, plus the D-09 live sandbox check, before `/bm:verify-work`

### Wave 0 Gaps
None — `test_config_handler.py::TestValidateUrl` already exists with the exact `socket.getaddrinfo`-stubbing harness this phase needs (confirmed by reading the file this session); `test_web_app_builder_logging.py` already exists and needs no new fixtures, only a build-verify pass. No new test framework, config, or shared fixture is required.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Unaffected by this phase |
| V3 Session Management | No | Unaffected by this phase |
| V4 Access Control | No | Unaffected by this phase |
| V5 Input Validation | Yes | The entire phase is a server-side allow-list input validator (`_validate_url`) on a user-supplied URL before any outbound request is made — this is the canonical ASVS V5 pattern (validate against an explicit allow-list, not a deny-list, for resources that trigger server-initiated network requests) |
| V6 Cryptography | No | Unaffected by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via user-supplied URL reaching internal/cloud-metadata services (CWE-918) | Tampering / Information Disclosure | Server-side allow-list classification of resolved IP addresses before the outbound request, exactly what `_validate_url` does; this phase narrows (not removes) the guard |
| SSRF via DNS rebinding (resolve-time vs. request-time address mismatch) | Tampering | **Explicitly out of scope** per D-06 — documented pre-existing limitation in `_validate_url`'s own docstring; would require socket-level interception, not attempted here |
| SSRF via address-notation bypass (IPv4-mapped/compatible/NAT64 IPv6 forms encoding a refused IPv4 address) | Tampering | Covered by this phase's classifier (Pattern 1) via the `is_reserved` guard — see Pitfall 2 for the two concrete forms verified this session |
| Open redirect used to pivot a validated URL to an unvalidated one | Tampering | Already mitigated and unchanged: `allow_redirects=False` plus an explicit refusal message (D-05); this phase does not touch this logic |

## Sources

### Primary (HIGH confidence)
- `python:3.11-slim` (3.11.18) and `python:3.12-slim` (3.12.16) official Docker images — every `ipaddress`/`urllib.parse` claim in this document was executed against both, this session, matching `pyproject.toml:10`'s `requires-python = ">=3.11,<3.13"` exactly
- `src/python/web/handler/config.py` — read in full, this session
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` — read in full, this session
- `src/python/tests/unittests/test_web/test_web_app_builder_logging.py` — read in full, this session
- `src/python/controller/arr_queue.py` — read (header + imports), this session, to confirm D-06 scope
- `.github/workflows/ci.yml` — grepped for `ruff check src/python/` and `python-version` pins, this session
- `src/python/pyproject.toml` — read in full, this session
- `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` and `123-teardown.sh` — read in full, this session, for the sandbox live-check idiom

### Secondary (MEDIUM confidence)
- None used — all claims in this document were either read directly from this repository's files or executed directly against the exact Python versions this project targets.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, versions confirmed by direct execution against both ends of the project's supported range
- Architecture: HIGH — the classifier in Pattern 1 was built and tested against every named case in D-01/D-02/D-03/D-04 plus two self-discovered bypass forms, inside the exact pinned Python versions
- Pitfalls: HIGH — all four pitfalls were reproduced directly (ValueError on `.port`, `is_global`/`is_reserved` co-occurrence, exact failing test list via grep) rather than inferred from general SSRF knowledge

**Research date:** 2026-10-27
**Valid until:** No expiry concern — this research is pinned to the project's fixed `requires-python = ">=3.11,<3.13"` range and the current `_validate_url` implementation; re-verify only if the Python version range changes or a future phase touches `_validate_url` again
