---
phase: 125-lan-connection-tests
reviewed: 2026-10-27T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/python/web/handler/config.py
  - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
  - src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
  - CHANGELOG.md
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 125: Code Review Report

**Reviewed:** 2026-10-27
**Depth:** standard (phase diff `6faaecc..HEAD`)
**Files Reviewed:** 4
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

The new classifier `_classify_resolved_address` is careful about the cases it was built for. I ran it against about 55 edge-case addresses on Python 3.11.14, 3.12.12, 3.13.14 and 3.14.5 and got the same result on every version. IPv4-mapped, IPv4-compatible, NAT64 (`64:ff9b::/96` and `64:ff9b:1::/48`), SIIT, 6to4, Teredo, scope-ID link-local, unspecified, multicast and broadcast forms are all refused on current interpreters. The phase tests pass (107 tests plus 16 subtests), and the convention checker found nothing.

The guard can still be bypassed, though not through the classifier. `_validate_url` checks the host that `urllib.parse.urlparse` sees, but `requests`/`urllib3` connect to a different host when the URL contains a backslash. I confirmed end to end that this reaches any loopback port and `169.254.169.254`. The flaw existed before this phase. It is still a BLOCKER because this phase rewrote the guard and the CHANGELOG now promises that metadata stays blocked and that loopback is limited to 8989/7878. Separately, the new `fc00::/7` allowance lets through AWS's IPv6 metadata endpoint, which the old check refused.

Intended behaviour from 125-CONTEXT.md is not flagged: LAN and CGNAT allowed, loopback only on 8989/7878, and the DNS-rebinding TOCTOU gap.

## Critical Issues

### CR-01: URL parser mismatch bypasses the whole SSRF guard (loopback port gate and metadata block)

**File:** `src/python/web/handler/config.py:152-155` (validation) vs `config.py:265-271` (request)
**Issue:** `_validate_url` gets the target host from `urlparse(url).hostname`, which takes everything after the last `@` in the netloc. `requests` re-parses the URL with `urllib3.util.parse_url`, which ends the authority at a backslash. So for `http://127.0.0.1:6390\@8.8.8.8:8989`:

- `urlparse` reports host `8.8.8.8`, port `8989`. It is public, so the URL is allowed.
- `requests` actually connects to `127.0.0.1:6390`, with path `/%5C@8.8.8.8:8989/api/v3/system/status`.

Reproduced locally with requests 2.34.2 and urllib3 2.8.0, which are the locked versions. A listener on 127.0.0.1:6390 received the request with `X-Api-Key: secretkey123`. The endpoint returned `{"success": true, "version": "LOOPBACK-6390-REACHED"}`, while `_validate_url("http://127.0.0.1:6390")` correctly returned the loopback-port refusal. The same trick reaches cloud metadata: `http://169.254.169.254\@8.8.8.8:8989` makes requests connect to `169.254.169.254:80`. With LAN now allowed, an attacker doesn't even need a public decoy: `http://127.0.0.1:6379\@sonarr:8989` works too.

`sonarr_url`/`radarr_url` are stored with `Checkers.null`, and `/server/config/set` needs no auth when no `api_token` is configured, which is the default. That means anyone who can reach the web UI can set such a URL and then trigger the request. The response echoes the remote JSON `version` field and the HTTP status, so this gives read access to that field plus a port and service probe. It breaks D-02 and D-03, and the CHANGELOG claims "loopback ... accepted only on port 8989 or 7878" and "cloud-metadata ... stay blocked". This mismatch was already there before Phase 125, but this phase owns the guard and its security claims.

A second, smaller mismatch has the same cause. The code validates `raw_url.strip()` but requests `raw_url.rstrip("/")`, so the string that is checked is not the string that is fetched.

**Fix:** Validate exactly what `requests` will use, and refuse anything the two parsers disagree on:
```python
from urllib3.util import parse_url

def _validate_url(url: str) -> str | None:
    if any(c in url for c in "\\\t\r\n ") or any(ord(c) < 0x20 for c in url):
        return "Invalid URL"
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        u3 = parse_url(url)
    except ValueError:
        return "Invalid URL"
    if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
        return "Invalid URL: credentials in URL are not allowed"
    u3_host = (u3.host or "").strip("[]").lower()
    if u3_host != (hostname or "") or u3.port != parsed.port:
        return "Invalid URL"
    ...
```
In `_test_arr_connection`, normalize once (`url = raw_url.strip().rstrip("/")`) and pass that same `url` to both `_validate_url` and `requests.get`. A stronger option is to rebuild the request URL from the validated `scheme://host:port` instead of reusing the raw string. Add regression tests for `http://127.0.0.1:6390\@8.8.8.8:8989`, `http://169.254.169.254\@sonarr:8989`, and a userinfo form like `http://a@127.0.0.1:6379`. Each should be refused with `requests.get` never called.

## Warnings

### WR-01: AWS IPv6 instance-metadata endpoint `fd00:ec2::254` is now allowed

**File:** `src/python/web/handler/config.py:24-30` (`fc00::/7` in `_ALLOWED_PRIVATE_NETWORKS`), `config.py:87-88`
**Issue:** `fd00:ec2::254` is the IPv6 endpoint for AWS Nitro instance metadata. It falls inside the ULA range `fc00::/7`, so it now returns `None` (allowed). I checked this on all four interpreter versions. The old guard refused it because of `is_private`. This contradicts D-03's intent and the CHANGELOG line "cloud-metadata and link-local destinations ... stay blocked". `100.100.100.200` (Alibaba Cloud metadata) also passes through the CGNAT allowance. That was allowed before as well and D-01 locks `100.64.0.0/10`, so treat it as a product decision. Excluding just that one host would not affect Tailscale, which uses `100.100.100.100` for MagicDNS.
**Fix:** Check known metadata hosts before the allow-lists:
```python
_METADATA_NETWORKS = (
    ipaddress.ip_network("fd00:ec2::254/128"),   # AWS IMDS (IPv6)
    ipaddress.ip_network("100.100.100.200/32"),  # Alibaba ECS metadata (owner call; D-01)
)
...
if any(addr in net for net in _METADATA_NETWORKS):
    return _MSG_LINK_LOCAL
```
Add a test showing `fd00:ec2::254` gets `LINK_LOCAL_MSG` while `fd00::10` is still allowed.

### WR-02: Hostnames that fail IDNA encoding raise UnicodeError, which escapes as a 500 instead of the JSON refusal

**File:** `src/python/web/handler/config.py:169-172`; caller `config.py:250`
**Issue:** `socket.getaddrinfo` raises `UnicodeError` (not `gaierror`) when the hostname has an empty or over-63-character label, or a lone surrogate. Examples: `http://a..b:8989`, `http://.:8989`, `http://<64 x 'a'>.example:8989`. Only `socket.gaierror` is caught. `_test_arr_connection` calls `_validate_url` outside its `try`, so the exception goes up to bottle, which returns a 500 and a server-side traceback. I confirmed it propagates. No request is made, so the guard still fails closed, but this breaks the D-07 contract (`{"success": false, "error": ...}`, HTTP 200). The Settings UI will show a generic failure instead of a reason.
**Fix:**
```python
try:
    addr_infos = socket.getaddrinfo(hostname, None)
except (socket.gaierror, UnicodeError, ValueError):
    return "Cannot resolve hostname"
```
Add a test with `http://a..b:8989` that expects the JSON error.

### WR-03: The public-address branch depends on interpreter-specific `is_global` tables; production (3.11, floating tag) and CI (3.12) can disagree

**File:** `src/python/web/handler/config.py:90-91`; `src/docker/build/docker-image/Dockerfile:79` (`FROM python:3.11-slim`)
**Issue:** Only IPv4-mapped addresses are unmapped. Every other IPv6 form that embeds an IPv4 address (6to4 `2002::/16`, Teredo `2001::/32`, NAT64, IPv4-compatible) is refused only because `is_global`/`is_reserved` happen to be False/True for it. Those tables changed in CPython 3.11.10 and 3.12.4 (gh-113171). On older 3.11 patches, `2002::/16` reports `is_global=True` and `is_reserved=False`. So `2002:7f00:1::` (6to4 for 127.0.0.1) and `2002:a9fe:a9fe::` (6to4 for 169.254.169.254) would be allowed. The production image floats on `python:3.11-slim` and CI tests on 3.12, so the guard's behaviour depends on whichever patch was pulled at build time. CONTEXT "Claude's Discretion" asked for explicit network checks in preference to stdlib semantics that have changed between versions. Reaching these addresses also needs a 6to4/Teredo route on the host, so the impact is low, but the guard should not depend on interpreter tables.
**Fix:** Add explicit refusals to `_REFUSED_NETWORKS`: `2002::/16`, `2001::/32`, `64:ff9b::/96`, `64:ff9b:1::/48`, `::/96` (IPv4-compatible) and `::ffff:0:0:0/96` (SIIT). Alternatively, unmap `addr.sixtofour` and `addr.teredo[1]` and re-classify the embedded IPv4. Keep the existing NAT64/compatible tests, and add 6to4 and Teredo cases so CI catches any regression.

## Info

### IN-01: Trailing whitespace in a saved URL passes validation but fails with "An unexpected error occurred"

**File:** `src/python/web/handler/config.py:250, 258`
**Issue:** `"http://192.168.1.20:8989 "` passes validation, which strips the whitespace. Then `requests` gets the unstripped `raw_url.rstrip("/")`, raises `InvalidURL`, and the user sees the generic error. This is the same validated-vs-fetched mismatch as CR-01.
**Fix:** Covered by CR-01's fix: normalize once and use the same string for both.

### IN-02: `TestLanRelaxationScope` is brittle and does not fully prove D-06

**File:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py:1092-1146`
**Issue:** `_production_py_files` runs `rglob("*.py")` over all of `src/python` and excludes only `tests/`. An in-project `.venv`, or ignored `build/`/`dist/` output, would get scanned and fail the test for reasons unrelated to the code under test. Also, the outbound-HTTP check only matches unindented `import requests` / `from requests`, so a new path using `urllib3`, `urllib.request`, `http.client` or an indented import would go unnoticed.
**Fix:** List files with `git ls-files '*.py'`, or skip hidden, `build`, `dist`, `site` and `htmlcov` directories. Widen the pattern to `^\s*(import|from)\s+(requests|urllib3|urllib\.request|http\.client|aiohttp|httpx)\b`.

### IN-03: CHANGELOG security wording overstates the guard until CR-01 and WR-01 are fixed

**File:** `CHANGELOG.md:13-29`
**Issue:** The `[Unreleased]` entry says cloud-metadata destinations "stay blocked" and loopback is limited to 8989/7878. Because of CR-01 (any destination via backslash) and WR-01 (`fd00:ec2::254`), neither statement is true yet.
**Fix:** Fix CR-01 and WR-01 first. Then, under `### Security`, add a line saying URLs with backslashes or embedded credentials are now refused, since that also changes what users can save.

---

_Reviewed: 2026-10-27_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
