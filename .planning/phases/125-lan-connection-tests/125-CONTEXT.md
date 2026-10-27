# Phase 125: LAN Connection Tests - Context

**Gathered:** 2026-10-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the Sonarr/Radarr **Test Connection** succeed for the local addresses people actually use: private-range IPs, and Docker container/host names that resolve to private addresses (fixes the Phase 120 D-02 `http://sonarr-v5:8989` failure). Unintended destinations stay refused: cloud-metadata/link-local, reserved/unspecified, multicast, loopback outside the allowed ports, and redirects. Requirements: LAN-01, LAN-02. The relaxation is limited to the configured Sonarr/Radarr test-connection path. No other outbound request path changes. The change is the minor-version driver for 1.8.0 and must be noted for the release notes (roadmap criterion 4).

Pre-discussion code reading:
- The only guard is `ConfigHandler._validate_url` (`src/python/web/handler/config.py:59-88`). It resolves the hostname with `socket.getaddrinfo` and refuses if any address is `is_private`, `is_loopback`, `is_reserved` or `is_link_local`. Every LAN Sonarr therefore fails with "URL resolves to a private/reserved IP address".
- Its only caller is `_test_arr_connection` (`config.py:158`), used by the Sonarr and Radarr test endpoints. The URL comes from saved config.
- Tailscale/CGNAT `100.64.0.0/10` passes today because it is in none of those categories.
- Redirects are never followed (`allow_redirects=False`). Any 301/302/307/308 returns "URL redirects to … Update the URL to the final destination."
</domain>

<decisions>
## Implementation Decisions

### Allowed destinations
- **D-01:** Allowed: private LAN ranges (IPv4 `10/8`, `172.16/12`, `192.168/16`), IPv6 unique-local `fc00::/7`, Tailscale/CGNAT `100.64.0.0/10` (allowed today; must not regress), and public addresses (allowed today). A Docker container or host name passes when every address it resolves to is allowed.
- **D-02:** Loopback (`127.0.0.0/8`, `::1`, and names such as `localhost` that resolve to loopback) is allowed **only on port 8989 (Sonarr default) or 7878 (Radarr default)**. A loopback URL with any other port, or with no explicit port (which means 80/443), is refused. Either port is accepted on either service's test. That covers host-networking setups; a custom-port Sonarr is reached via its LAN IP or container name.

### Still refused
- **D-03:** Refused regardless of path: link-local `169.254.0.0/16` (including cloud metadata `169.254.169.254`) and IPv6 link-local `fe80::/10`; unspecified (`0.0.0.0`, `::`); other reserved ranges; multicast; IPv4-mapped/compatible IPv6 forms that map to a refused IPv4 address (e.g. `::ffff:169.254.169.254`, `::ffff:127.0.0.1` on a disallowed port). Loopback outside D-02's ports is refused.
- **D-04:** Mixed resolution: if a hostname resolves to several addresses and **any** of them is refused, the URL is refused (same fail-closed rule as today).
- **D-05:** Redirect handling is unchanged. Responses are never followed, and a 3xx returns the existing "URL redirects to … Update the URL to the final destination." message, covered by a regression test.
- **D-06:** Scope: only `_validate_url` / `_test_arr_connection` (the Sonarr/Radarr Test Connection path) changes. No other outbound request path is relaxed or rerouted through it. The existing DNS-rebinding (TOCTOU) limitation stays documented and out of scope.

### User-visible wording
- **D-07:** A refused URL gets a specific reason in the existing failure shape (`{"success": false, "error": "..."}`, same HTTP status as today). For example: "URL points to a link-local or cloud-metadata address, which is not allowed"; "localhost is only allowed on port 8989 (Sonarr) or 7878 (Radarr)"; a reserved/unspecified/multicast message. The old "private/reserved IP address" message must no longer appear for allowed private addresses. Error text must never echo the API key. Echoing the hostname or IP is acceptable only if it is sanitized like the existing redirect-location display.

### Proof of done
- **D-08:** Test-first regression tests (fail before, pass after) for each representative allowed case: `192.168.x.x`, `10.x.x.x`, `172.16–31.x.x`, a container name resolving to `172.x` (stubbed `getaddrinfo`), IPv6 ULA, loopback on 8989/7878, and Tailscale `100.64/10` unchanged. Also for each refused case: `169.254.169.254`, `fe80::`, `0.0.0.0`, multicast, loopback on another port or no port, mixed resolution, IPv4-mapped bypass forms, and redirect. Plus a test proving no other outbound path calls the relaxed check. Full Python suite and whole-tree `ruff check src/python/` must pass.
- **D-09:** A short live check on the NAS sandbox `seedsyncarr-test` running this phase's PR CI staging image pinned by digest. Test Connection to `http://sonarr-v5:8989` succeeds and reports the Sonarr version, and a refused destination (`http://169.254.169.254`) returns the new refusal message. The sandbox Sonarr URL is restored right after the check (as in Phase 120 D-03). The sandbox image pin is restored to its original value afterwards and checked in a fresh session. Production is read-only checks only.

### Release notes
- **D-10:** Record the behaviour change for the 1.8.0 release notes in `CHANGELOG.md` (an Unreleased/1.8.0-draft entry Phase 126 will finalize). Wording: Test Connection now accepts local network and Docker container addresses, localhost only on 8989/7878, and metadata/link-local destinations stay blocked.

### Post-review additions (owner, 2026-10-27, after code review 125-REVIEW.md)
- **D-11:** Fix the parser-differential bypass (125-REVIEW.md CR-01) inside Phase 125, test-first: refuse URLs that the guard (`urllib.parse`) and the request library (`urllib3`/`requests`) would interpret differently (backslash, whitespace, control characters, embedded credentials/userinfo, or any host/port/scheme disagreement), and validate the exact string that is requested. Also fix WR-02 (malformed hostname → normal JSON error, not 500), WR-03 (explicit refuse ranges for IPv6 transition forms rather than relying on interpreter tables), IN-01 (trailing whitespace) and IN-03 (CHANGELOG wording accurate). IN-02 (scope-test brittleness) at Claude's discretion. PR #140 stays the single PR; re-run CI and a short sandbox re-check.
- **D-12:** Refuse the two cloud-metadata addresses inside allowed ranges: `fd00:ec2::254` (AWS IPv6, inside `fc00::/7`) and `100.100.100.200` (Alibaba, inside `100.64.0.0/10`), with the existing link-local/cloud-metadata refusal message. The rest of the ULA and CGNAT/Tailscale ranges stay allowed (D-01 otherwise unchanged).

### Claude's Discretion
- How the allow/refuse classification is structured (helper function, constants), using `ipaddress` network checks in preference to relying solely on `is_private`, whose semantics changed across Python versions.
- Exact error message strings within D-07's intent.
- Test file placement (extend `test_config_handler.py`'s `_validate_url` test class vs a new class) and how the sandbox check is scripted, reusing the Phase 122/123 sandbox runbook/teardown pattern.

</decisions>

<specifics>
## Specific Ideas

- The motivating real case is the Phase 120 sandbox: `http://sonarr-v5:8989` (Docker container name → `172.x`) failed while the Tailscale address worked.
- The roadmap phrasing "loopback-to-unexpected-port probes" is satisfied by D-02 (only 8989/7878).
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/ROADMAP.md` §"Phase 125: LAN Connection Tests": goal and 4 success criteria (incl. release-notes note)
- `.planning/REQUIREMENTS.md`: LAN-01, LAN-02; Out of Scope row "Broad relaxation of outbound requests"
- `.planning/phases/120-sonarr-5-compatibility/120-CONTEXT.md` D-02/D-03: the recorded container-name failure and the restore-the-URL rule for sandbox Test Connection checks

### Code
- `src/python/web/handler/config.py`: `_validate_url` (SSRF guard), `_test_arr_connection` (sole caller; redirect handling; exception logging that never includes the API key, per 122-14 CR-01), `_sanitize_redirect_location`
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`: existing `_validate_url` full-path tests (COVMED-02) and test-connection tests
- `src/python/tests/unittests/test_web/test_web_app_builder_logging.py`: patches `_validate_url` (must keep working)

### Live sandbox procedure
- `.planning/phases/123-startup-and-shutdown-lifecycle/123-CONTEXT.md` D-07 and `123-teardown.sh`: digest-pinned sandbox deploy, restore-to-original-pin, fresh-session check, production read-only
- User global CLAUDE.md "NAS docker access": `ssh nas`, `sudo /usr/local/bin/docker ...` absolute paths, compose at `/volume1/docker/docker-compose.yml`

### Release notes
- `CHANGELOG.md`: existing per-version format (latest `[1.7.6]`)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_validate_url` is a pure `@staticmethod` that returns an error string or None. The change can stay inside it (plus helpers) without touching callers.
- The existing `_validate_url` test class stubs `socket.getaddrinfo`, which is the right harness for container-name and mixed-resolution cases.
- `_sanitize_redirect_location` is the existing pattern for safely echoing a URL fragment in an error.

### Established Patterns
- Responses to Test Connection are always HTTP 200 JSON `{"success": bool, ...}`. Refusals keep that shape.
- Test-first RED→GREEN with commit order auditable (Phases 122–124); whole-tree ruff as a separate CI gate.
- Sandbox checks use a PR CI staging image pinned by digest (`ghcr.io/thejuran/seedsyncarr:<run_number>`), never `:dev`, with a restore and fresh-session check.

### Integration Points
- `config.py:158`: the single call site. The port is available from `urlparse(url).port` for D-02.
</code_context>

<deferred>
## Deferred Ideas

- DNS-rebinding (TOCTOU) hardening via socket-level interception, still out of scope (documented limitation).
- A user-configurable allowlist of extra loopback ports, not requested; custom ports are reachable via LAN IP or container name.
</deferred>

---

*Phase: 125-lan-connection-tests*
*Context gathered: 2026-10-27*
