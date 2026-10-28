---
phase: 125-lan-connection-tests
plan: 01
subsystem: api
tags: [ssrf, ipaddress, test-connection, sonarr, radarr, tdd]

# Dependency graph
requires:
  - phase: 120-sonarr-5-compatibility
    provides: the recorded Phase 120 D-02 Docker-container-name Test Connection failure this plan fixes
provides:
  - "ConfigHandler._classify_resolved_address, an ordered allow/refuse classifier replacing the single is_private-or-loopback-or-reserved-or-link_local check"
  - "LAN-01: private ranges (10/8, 172.16/12, 192.168/16), IPv6 ULA (fc00::/7), CGNAT/Tailscale (100.64/10), public addresses, and container/host names resolving to any of those pass Test Connection"
  - "LAN-02: link-local/cloud-metadata, unspecified, multicast, other reserved ranges (incl. fec0::/10 and IPv4-mapped/compatible/NAT64 bypass notations), and loopback outside ports 8989/7878 stay refused with category-specific messages"
  - "TestLanRelaxationScope: regression proof that _validate_url has exactly one production caller and the outbound-HTTP module set is unchanged"
affects: [125-02, 125-03, 126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ordered ipaddress classifier: unmap ::ffff: first, then unspecified -> loopback-port-gate -> link-local -> multicast -> named refused ranges -> named allowed private ranges -> is_global-and-not-is_reserved -> reserved fallback"
    - "Pure-validator contract preserved: _validate_url still returns an error string or None, never raises past its own boundary (urlparse/.hostname and .port each get their own try/except ValueError)"

key-files:
  created:
    - .planning/phases/125-lan-connection-tests/deferred-items.md
  modified:
    - src/python/web/handler/config.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py

key-decisions:
  - "D-05 redirect lock tests use a public resolved address (8.8.8.8), not the plan action text's literal 192.168.1.20, so they genuinely pass unchanged before and after the GREEN fix (192.168.1.20 was rejected by the pre-fix guard, which would have made the 'lock' fail in RED)"
  - "fec0::/10 explicitly refused via _REFUSED_NETWORKS (orchestrator decision 1); ::127.0.0.1 and 64:ff9b:: NAT64 bypass forms explicitly tested and refused via the is_global-and-not-is_reserved guard (orchestrator decision 2)"

patterns-established:
  - "Locked refusal-message constants duplicated as literals in the test file (not imported from config.py) so tests pin exact wording rather than drift silently with the implementation"

requirements-completed: [LAN-01, LAN-02]

# Metrics
duration: ~25min
completed: 2026-10-27
---

# Phase 125 Plan 01: LAN-Aware SSRF Classifier Summary

**Replaced ConfigHandler._validate_url's single is_private/is_loopback/is_reserved/is_link_local check with an ordered ipaddress classifier so Sonarr/Radarr Test Connection accepts LAN IPs, IPv6 ULA, CGNAT/Tailscale, and Docker container names, while cloud-metadata, link-local, unspecified, multicast, other-reserved and off-port loopback stay refused with specific messages.**

## Performance

- **Duration:** ~25 min (RED commit `8a69fdf` at 2026-10-27T15:20:53-04:00, GREEN commit `f82e256` at 2026-10-27T15:25:28-04:00; elapsed time includes the preceding plan/file investigation before the first commit)
- **Completed:** 2026-10-27
- **Tasks:** 2 of 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 3 (`config.py`, `test_config_handler.py`, `test_sonarr5_system_status.py`); 1 file created (`deferred-items.md`)

## Accomplishments

- LAN-01: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`, `100.64.0.0/10`, public addresses, and the motivating Phase 120 D-02 case (`http://sonarr-v5:8989` resolving to `172.19.0.6`) all pass `_validate_url` and reach a mocked Sonarr/Radarr successfully
- LAN-02: cloud-metadata/link-local (`169.254.169.254`, `fe80::/10`, mapped forms), unspecified (`0.0.0.0`, `::`), multicast (`224.0.0.1`, `239.255.255.250`, `ff02::1` — previously an unguarded gap), other reserved ranges (`192.0.2.1`, `240.0.0.1`, `255.255.255.255`, `fec0::/10`), and three notation-bypass forms (`::127.0.0.1`, `64:ff9b::7f00:1`, `64:ff9b::a9fe:a9fe`) are all refused with category-specific messages, including on an otherwise-allowed port
- D-02: loopback (`127.0.0.1`, `127.0.1.1`, `::1`, `::ffff:127.0.0.1`) is allowed only on port 8989 or 7878 (either port works for either service's test); any other port, or no explicit port, is refused
- D-04: mixed-resolution results refuse the whole URL if any resolved address is refused, or if any address is unparseable, or if resolution returns no addresses
- D-05: redirect handling is unchanged (one `requests.get` call, `allow_redirects=False`, sanitized redirect message), proven by two regression locks
- D-06: a new `TestLanRelaxationScope` class proves `_validate_url` has exactly one caller (`_test_arr_connection`), is referenced from no other production file, and the outbound-HTTP module set is exactly `{config.py, arr_queue.py}` with `arr_queue.py` never calling the guard
- D-07: refusal messages are fixed, generic strings that never contain "private" and never echo the hostname, IP or API key (proven by a dedicated regression test); a malformed port returns `{"success": false, "error": "Invalid URL: invalid port"}` as JSON rather than an unhandled exception

## Task Commits

1. **Task 1 (RED): Regression tests for every allowed and refused case** - `8a69fdf` (test)
2. **Task 2 (GREEN): Ordered address classifier in _validate_url** - `f82e256` (fix)

_TDD plan: RED (tests only) landed before GREEN (config.py only), confirmed by `git diff HEAD~1 -- src/python/web/handler/config.py` being empty at the RED commit and `git show --stat --format= HEAD` listing only `config.py` at the GREEN commit._

## RED

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_sonarr5/test_sonarr5_system_status.py -p no:cacheprovider -q`

Result: **69 failed, 54 passed** (pytest-subtests reports 16 of the 69 as `SUBFAILED` sub-cases of one test, `test_refusal_messages_never_mention_private_or_echo_host`, parametrized over 16 refused addresses — 53 distinct top-level failing tests + that one multi-case test = 69).

**Failing test ids (expected — exercise the new classifier behavior not yet implemented):**

```
TestConfigHandlerTestSonarrConnection::test_sonarr_accepts_lan_ip_and_reports_version
TestConfigHandlerTestSonarrConnection::test_sonarr_accepts_loopback_on_default_port
TestConfigHandlerTestSonarrConnection::test_sonarr_accepts_loopback_on_radarr_port
TestConfigHandlerTestSonarrConnection::test_sonarr_invalid_port_returns_json_error
TestConfigHandlerTestSonarrConnection::test_sonarr_rejects_cloud_metadata_without_request
TestConfigHandlerTestRadarrConnection::test_radarr_accepts_loopback_on_default_port
TestConfigHandlerTestRadarrConnection::test_radarr_rejects_loopback_on_other_port_without_request
TestValidateUrl::test_accepts_container_name_resolving_to_docker_bridge
TestValidateUrl::test_accepts_https_loopback_on_sonarr_port
TestValidateUrl::test_accepts_ipv4_private_10
TestValidateUrl::test_accepts_ipv4_private_172_16
TestValidateUrl::test_accepts_ipv4_private_172_31_upper_edge
TestValidateUrl::test_accepts_ipv4_private_192_168
TestValidateUrl::test_accepts_ipv6_loopback_on_sonarr_port
TestValidateUrl::test_accepts_ipv6_mapped_loopback_on_radarr_port
TestValidateUrl::test_accepts_ipv6_mapped_private_ipv4
TestValidateUrl::test_accepts_ipv6_unique_local
TestValidateUrl::test_accepts_ipv6_unique_local_fd
TestValidateUrl::test_accepts_loopback_127_range_on_sonarr_port
TestValidateUrl::test_accepts_loopback_on_radarr_port
TestValidateUrl::test_accepts_loopback_on_sonarr_port
TestValidateUrl::test_accepts_multi_address_when_all_allowed
TestValidateUrl::test_rejects_cloud_metadata
TestValidateUrl::test_rejects_empty_resolution
TestValidateUrl::test_rejects_ipv4_class_e
TestValidateUrl::test_rejects_ipv4_compatible_loopback_bypass_on_allowed_port
TestValidateUrl::test_rejects_ipv4_documentation_range
TestValidateUrl::test_rejects_ipv4_limited_broadcast
TestValidateUrl::test_rejects_ipv4_link_local
TestValidateUrl::test_rejects_ipv4_loopback_without_port
TestValidateUrl::test_rejects_ipv4_multicast
TestValidateUrl::test_rejects_ipv4_multicast_ssdp
TestValidateUrl::test_rejects_ipv4_unspecified
TestValidateUrl::test_rejects_ipv6_deprecated_site_local
TestValidateUrl::test_rejects_ipv6_link_local
TestValidateUrl::test_rejects_ipv6_loopback_without_port
TestValidateUrl::test_rejects_ipv6_mapped_cloud_metadata
TestValidateUrl::test_rejects_ipv6_mapped_link_local_ipv4
TestValidateUrl::test_rejects_ipv6_mapped_loopback_ipv4_without_port
TestValidateUrl::test_rejects_ipv6_mapped_loopback_on_other_port
TestValidateUrl::test_rejects_ipv6_multicast
TestValidateUrl::test_rejects_ipv6_unspecified
TestValidateUrl::test_rejects_loopback_https_default_port
TestValidateUrl::test_rejects_loopback_on_other_port
TestValidateUrl::test_rejects_malformed_ipv6_url
TestValidateUrl::test_rejects_mixed_resolution_with_loopback_on_wrong_port
TestValidateUrl::test_rejects_multi_address_when_any_refused
TestValidateUrl::test_rejects_nat64_embedded_loopback_bypass_on_allowed_port
TestValidateUrl::test_rejects_nat64_embedded_metadata
TestValidateUrl::test_rejects_non_numeric_port
TestValidateUrl::test_rejects_out_of_range_port
TestValidateUrl::test_rejects_unparseable_resolved_address
TestValidateUrl::test_refusal_messages_never_mention_private_or_echo_host (16 subtests, all SUBFAILED)
TestSonarr5SystemStatus::test_docker_network_url_accepted_by_lan_guard
```

**Passing lock tests (confirmed green in the RED run, individually re-verified):**

```
TestLanRelaxationScope::test_outbound_http_modules_are_known
TestLanRelaxationScope::test_validate_url_not_referenced_outside_config_handler
TestLanRelaxationScope::test_validate_url_only_called_from_test_arr_connection
TestConfigHandlerTestSonarrConnection::test_sonarr_redirect_to_metadata_is_not_followed
TestConfigHandlerTestRadarrConnection::test_radarr_redirect_is_not_followed
TestSonarr5SystemStatus::test_cgnat_address_passes_url_validation
```

No test expected to fail passed unexpectedly; the run matched the plan's RED expectations after one correction (see Deviations).

## GREEN

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_sonarr5 -p no:cacheprovider -q`

Result: **158 passed, 74 subtests passed, 0 failed, 2 warnings** (warnings are the pre-existing `cache_dir` pytest-config and `webob`/`cgi` deprecation notices, unrelated to this change).

Whole-tree lint: `ruff check src/python/` → **All checks passed!**

Interpreter: `poetry run pytest` under this project's poetry venv, Python 3.12.12 (within the project's `>=3.11,<3.13` range) — no Docker fallback needed.

Commit pair: `8a69fdf` (test, RED) → `f82e256` (fix, GREEN).

## Final Refusal-Message Table

| Category | Message |
|----------|---------|
| Loopback, wrong/no port | `Loopback addresses are only allowed on port 8989 (Sonarr) or 7878 (Radarr)` |
| Link-local / cloud-metadata | `URL points to a link-local or cloud-metadata address, which is not allowed` |
| Unspecified | `URL points to an unspecified address (0.0.0.0 or ::), which is not allowed` |
| Multicast | `URL points to a multicast address, which is not allowed` |
| Reserved (incl. `fec0::/10`, `::127.0.0.1`, `64:ff9b::` NAT64 forms) | `URL points to a reserved IP address, which is not allowed` |
| Unparseable resolved address | `URL resolves to an address that could not be checked, which is not allowed` |
| Malformed port | `Invalid URL: invalid port` |
| Malformed URL (e.g. unclosed IPv6 bracket) | `Invalid URL` |
| No hostname / unresolvable (unchanged) | `Invalid URL: no hostname` / `Cannot resolve hostname` |

## Files Created/Modified

- `src/python/web/handler/config.py` - replaced the single boolean guard with `_classify_resolved_address` and supporting module constants (`_ALLOWED_PRIVATE_NETWORKS`, `_REFUSED_NETWORKS`, `_ALLOWED_LOOPBACK_PORTS`, `_MSG_*`); `_validate_url` now guards `urlparse`/`.hostname` and `.port` each with their own `try/except ValueError`, treats empty/unparseable resolution as fail-closed, and documents the new scope
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` - rewrote `TestValidateUrl` (flipped 3 accept cases, reworded 6 still-refused cases, added 13 new accepts, 22 new refusals, 1 multi-address accept, 1 message-hygiene test); flipped 2 handler-level private-IP-rejection tests to loopback-accept; added 7 new Sonarr/Radarr handler tests (LAN-IP, cloud-metadata-without-request, malformed-port, loopback-on-other-port, 2 redirect locks); added `TestLanRelaxationScope` (3 tests)
- `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` - rewrote the module docstring and renamed/flipped `test_docker_network_url_rejected_by_lan_guard_known_limitation` to `test_docker_network_url_accepted_by_lan_guard`
- `.planning/phases/125-lan-connection-tests/deferred-items.md` - (new) records 26 pre-existing, unrelated local full-suite failures found while running the broader verification sweep

## Decisions Made

- Used the plan's locked D-07 message strings verbatim as module-level literals in the test file (not imported from `config.py`), so the tests pin wording independently of the implementation.
- Adjusted the two D-05 redirect "lock" tests to resolve to a public address (`8.8.8.8`) instead of the plan action text's literal `192.168.1.20`, so they are genuine locks that pass unchanged in both RED and GREEN (see Deviations).
- Followed the research's resolved open questions: `fec0::/10` explicitly refused (orchestrator decision 1); `::127.0.0.1` and `64:ff9b::` NAT64 bypass forms explicitly tested and refused (orchestrator decision 2); loopback refusal message stays fully generic, never echoing the hostname/IP (orchestrator decision 3 / open question 3).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Redirect lock tests used a private IP that the pre-fix guard would reject, breaking the "lock" property**
- **Found during:** Task 1 (RED) verification — first RED run showed `test_sonarr_redirect_to_metadata_is_not_followed` and `test_radarr_redirect_is_not_followed` both failing, but Task 1's acceptance criteria require these two tests to pass in both RED and GREEN runs (they prove D-05 redirect handling is unaffected by the classifier rewrite).
- **Issue:** The plan's action text specified resolving to `192.168.1.20` for these two tests. Under the *old* (pre-fix) guard, `192.168.1.20` is `is_private` and gets rejected before the mocked `requests.get`/redirect branch is ever reached, so the test asserted on the wrong error message and failed in RED — contradicting its own role as an unchanged-behavior lock.
- **Fix:** Changed the resolved address (and the configured URL) in both tests to `8.8.8.8`, a public address that was already allowed under the old guard and remains allowed under the new one, so the redirect branch is reached and asserted on identically before and after the GREEN commit.
- **Files modified:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`
- **Verification:** Re-ran the RED suite; both tests passed individually and in the full RED run (69 failed / 54 passed, down from 71 failed / 52 passed before the fix — i.e. exactly these 2 tests moved from failing to passing, with no other count changes).
- **Committed in:** `8a69fdf` (Task 1 RED commit; the tests were fixed before that commit was made, so the committed RED state already reflects the corrected lock tests)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test bug in my own first draft, found and fixed before the RED commit landed)
**Impact on plan:** No scope creep; the fix only corrected which address two new regression tests resolve to, preserving their intended role as D-05 locks.

## Issues Encountered

- The full local test suite (`tests/unittests`, 1917+ tests) has 26 pre-existing failures unrelated to this plan's files (missing `testgroup` Unix group for SSH tests, multiprocessing-spawn flakiness, filesystem-encoding test) — documented in `deferred-items.md`, not fixed here (out of this plan's scope; none of the failing files reference `ConfigHandler`).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- LAN-01 and LAN-02 are both implemented and regression-tested; the Phase 120 D-02 Docker-container-name Test Connection failure is fixed.
- Plan 125-02 and 125-03 (if they build on this guard) can rely on the new `_classify_resolved_address` ordering and the locked refusal-message set documented above.
- D-09 (live NAS sandbox check against `seedsyncarr-test`) and the `CHANGELOG.md` 1.8.0-draft entry (D-10) are out of this plan's scope — expected to land in a later Phase 125 plan or Phase 126.
- `deferred-items.md`'s pre-existing local full-suite failures are unrelated to this plan and not a blocker for it.

## Self-Check: PASSED

All claimed files exist on disk and both commit hashes (`8a69fdf`, `f82e256`) are present in `git log --oneline --all`.

---
*Phase: 125-lan-connection-tests*
*Completed: 2026-10-27*
