---
phase: 125-lan-connection-tests
plan: 04
subsystem: api
tags: [ssrf, parser-differential, urllib3, cr-01, wr-01, wr-02, wr-03, in-01, in-02, d-11, d-12, d-14, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 125-01
    provides: "ConfigHandler._classify_resolved_address, the ordered allow/refuse classifier this plan extends with the metadata check and the explicit IPv6-transition refusals"
  - phase: 125-REVIEW
    provides: "CR-01 (parser-differential SSRF bypass), WR-01/WR-02/WR-03 and IN-01/IN-02 findings this plan closes"
provides:
  - "_validate_url now validates the exact string _test_arr_connection requests (single url = raw_url.strip().rstrip(\"/\") normalization), closing the backslash-userinfo parser-differential bypass (CR-01) between urllib.parse and urllib3.util.parse_url"
  - "_METADATA_NETWORKS refuses fd00:ec2::254 (AWS IPv6 IMDS) and 100.100.100.200 (Alibaba ECS metadata) inside the otherwise-allowed ULA/CGNAT ranges (D-12 / WR-01)"
  - "_REFUSED_NETWORKS gains explicit 6to4/Teredo/NAT64/SIIT entries so IPv6-transition forms are refused independent of interpreter is_global/is_reserved tables (WR-03)"
  - "Malformed hostnames (consecutive dots, bare dot, over-length label) return a normal JSON error instead of an unhandled UnicodeError/500 (WR-02)"
  - "Non-ASCII hosts and URLs containing ?/# are refused; the xn-- (punycode) form is accepted (D-14)"
  - "TestLanRelaxationScope now excludes hidden/venv/build/dist/site/htmlcov/node_modules/__pycache__ directories and matches indented outbound-HTTP imports beyond requests (IN-02)"
affects: [125-05, 125-06, 126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Character allow-list before any parser: _URL_CHARS (printable ASCII without space) plus an explicit backslash check runs before urlparse ever sees the string, so a parser-differential host disagreement can never be reached"
    - "Parser-agreement check: urlparse vs urllib3.util.parse_url compared on scheme/bracket-stripped-lowercased-host/port, refusing any disagreement before DNS resolution"
    - "Single normalization point: _test_arr_connection computes url = raw_url.strip().rstrip(\"/\") once and passes that same string to both _validate_url and requests.get"

key-files:
  created: []
  modified:
    - src/python/web/handler/config.py
    - src/python/tests/unittests/test_web/test_handler/test_config_handler.py

key-decisions:
  - "D-11/D-14 ordering: character allow-list (step 1) before urlparse, then credentials/percent (step 4), then query/fragment (step 5), then hostname-syntax (step 7), then parser-agreement (step 8), then resolution (step 9) -- each earlier step produces a specific message before a later, more generic one could fire"
  - "WR-03 explicit refused ranges (2002::/16, 2001::/32, 64:ff9b::/96, 64:ff9b:1::/48, ::/96, ::ffff:0:0:0/96) are additive defence-in-depth: on this repo's locked Python 3.12.12 these addresses were already refused via the existing is_global/is_reserved fallback (confirmed by the WR-03 'real-table' lock tests passing unchanged before and after), but the explicit entries remove the dependency on interpreter patch version per the CR-01 review (gh-113171)"

requirements-completed: []
# LAN-01/LAN-02 intentionally NOT marked complete here -- gap-closure plans
# 125-05/125-06 are still pending per project instructions; REQUIREMENTS.md
# is left untouched by this plan.

# Metrics
duration: ~35min
completed: 2026-10-27
---

# Phase 125 Plan 04: Parser-Differential SSRF Guard Closure Summary

**Closed the backslash-userinfo parser-differential SSRF bypass (CR-01) by validating the exact string `requests`/`urllib3` will connect to, plus the related D-12 metadata, WR-02 malformed-hostname, WR-03 IPv6-transition and D-14 character/IDN findings from the 125-REVIEW code review.**

## Performance

- **Duration:** ~35 min (RED commit `730d3c7`, GREEN commit `b6d0902`)
- **Completed:** 2026-10-27
- **Tasks:** 2 of 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 2 (`config.py`, `test_config_handler.py`)

## Accomplishments

- **CR-01 (D-11):** `_validate_url` now refuses both review payloads (`http://127.0.0.1:6390\@8.8.8.8:8989` and `http://169.254.169.254\@sonarr:8989`) plus a third (`http://127.0.0.1:6379\@sonarr:8989`) with `BAD_CHARS_MSG`, before `getaddrinfo` is ever called — proven at the direct-call, handler, and transport level (a test that leaves the real `requests`/`urllib3` stack in place and patches only `requests.adapters.HTTPAdapter.send` confirms `send` is never reached).
- **Userinfo/query/percent (D-11/D-14):** `http://a@127.0.0.1:6379` and `http://:@sonarr:8989` refused with `CREDENTIALS_MSG`; `?`/`#` refused with `QUERY_MSG`; `%` in the host refused with `BAD_URL_MSG`; none resolves.
- **Characters (D-14):** tab, leading space, trailing space, trailing newline, and a non-ASCII host (`http://ü.example:8989`) are all refused with `BAD_CHARS_MSG` before resolution; the `xn--` punycode form (`http://xn--tda.example:8989`) is still accepted.
- **Parser-agreement lock:** `urlparse` and `urllib3.util.parse_url` agree on scheme/host/port for six representative allowed URLs (container names, IPv6 brackets, mixed case, underscore hostnames, a path, a bare IP), and `_validate_url` accepts all six.
- **IN-01:** `_test_arr_connection` normalizes once (`url = raw_url.strip().rstrip("/")`) and uses that identical string for both validation and the outbound request — `"  http://192.168.1.20:8989/  "` now succeeds and requests exactly `http://192.168.1.20:8989/api/v3/system/status`, proven directly and via a `wraps`-based test that compares the validated argument to the requested URL.
- **WR-02:** `http://a..b:8989`, `http://.:8989`, and a 64-character label all return `BAD_HOSTNAME_MSG` as normal JSON (HTTP 200) with no resolution and no request; `getaddrinfo` raising `UnicodeError` or `ValueError` is now caught directly and returns `"Cannot resolve hostname"`.
- **WR-03:** `_REFUSED_NETWORKS` gained explicit entries for 6to4 (`2002::/16`), Teredo (`2001::/32`), NAT64 well-known and local-use (`64:ff9b::/96`, `64:ff9b:1::/48`), IPv4-compatible (`::/96`) and SIIT (`::ffff:0:0:0/96`). Five real-table lock tests (6to4 ×2, Teredo, NAT64 local-use, SIIT) pass unchanged before and after. A `PropertyMock`-simulated-old-interpreter test (`is_global=True`, `is_reserved=False`, `is_private=False`) proves all seven forms still refuse via the explicit ranges regardless of what the interpreter's tables report, while `::1` stays allowed on 8989 under the same patches.
- **D-12:** `fd00:ec2::254` (AWS IPv6 instance metadata) and `100.100.100.200` (Alibaba ECS metadata, including its `::ffff:` mapped form) are refused with `LINK_LOCAL_MSG` even though they fall inside the allowed `fc00::/7` and `100.64.0.0/10` ranges; their neighbours (`fd00::10`, `fd00:ec2::253`, `100.100.100.100` Tailscale MagicDNS, `100.100.100.201`, `100.64.0.1`) stay allowed.
- **IN-02:** `TestLanRelaxationScope._production_py_files` now excludes hidden directories and `venv`/`build`/`dist`/`site`/`htmlcov`/`node_modules`/`__pycache__`; the outbound-HTTP pattern now matches indented imports of `requests`, `urllib3`, `urllib.request`, `http.client`, `aiohttp` and `httpx`. The scope test still finds exactly `{web/handler/config.py, controller/arr_queue.py}`.

## Task Commits

1. **Task 1 (RED): Regression tests for CR-01, D-12, WR-02, WR-03, IN-01 and a hardened D-06 scope test** - `730d3c7` (test)
2. **Task 2 (GREEN): Parser-agreement guard, single normalized URL, metadata and transition-network refusals in config.py** - `b6d0902` (fix)

_TDD plan: RED (tests only) landed before GREEN (config.py only), confirmed by `git diff HEAD~1 -- src/python/web/handler/config.py` being empty at the RED commit and `git show --stat --format= HEAD` listing only `config.py` at the GREEN commit._

## RED

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py -p no:cacheprovider -q`

Result: **37 failed, 115 passed, 22 subtests passed** (1 warning, pre-existing `cache_dir` pytest-config notice).

**Failing test ids (expected — exercise CR-01/D-12/WR-02/WR-03-simulated/D-14 behavior not yet implemented):**

```
TestConfigHandlerTestRadarrConnection::test_radarr_backslash_loopback_payload_makes_no_request
TestConfigHandlerTestSonarrConnection::test_sonarr_backslash_loopback_payload_makes_no_request
TestConfigHandlerTestSonarrConnection::test_sonarr_backslash_metadata_payload_makes_no_request
TestConfigHandlerTestSonarrConnection::test_sonarr_backslash_payload_never_reaches_transport
TestConfigHandlerTestSonarrConnection::test_sonarr_backslash_redis_payload_makes_no_request
TestConfigHandlerTestSonarrConnection::test_sonarr_malformed_hostname_returns_json_error
TestConfigHandlerTestSonarrConnection::test_sonarr_rejects_aws_ipv6_metadata_without_request
TestConfigHandlerTestSonarrConnection::test_sonarr_trims_whitespace_and_requests_exact_validated_url
TestConfigHandlerTestSonarrConnection::test_sonarr_userinfo_payload_makes_no_request
TestConfigHandlerTestSonarrConnection::test_sonarr_validated_url_equals_requested_url
TestParserDifferentialGuard::test_getaddrinfo_unicode_error_returns_cannot_resolve
TestParserDifferentialGuard::test_getaddrinfo_value_error_returns_cannot_resolve
TestParserDifferentialGuard::test_rejects_64_char_label_hostname
TestParserDifferentialGuard::test_rejects_backslash_userinfo_loopback_payload
TestParserDifferentialGuard::test_rejects_backslash_userinfo_metadata_payload
TestParserDifferentialGuard::test_rejects_consecutive_dots_hostname
TestParserDifferentialGuard::test_rejects_dot_only_hostname
TestParserDifferentialGuard::test_rejects_fragment
TestParserDifferentialGuard::test_rejects_leading_space
TestParserDifferentialGuard::test_rejects_non_ascii_host
TestParserDifferentialGuard::test_rejects_percent_in_host
TestParserDifferentialGuard::test_rejects_query_string
TestParserDifferentialGuard::test_rejects_tab_in_host
TestParserDifferentialGuard::test_rejects_trailing_newline
TestParserDifferentialGuard::test_rejects_trailing_space
TestParserDifferentialGuard::test_rejects_userinfo_empty_colon
TestParserDifferentialGuard::test_rejects_userinfo_with_username
TestValidateUrl::test_rejects_alibaba_metadata
TestValidateUrl::test_rejects_alibaba_metadata_ipv6_mapped
TestValidateUrl::test_rejects_aws_ipv6_metadata
TestValidateUrl::test_rejects_ipv6_transition_forms_on_simulated_old_interpreter_tables (7 subtests, all SUBFAILED:
    addr='2002:7f00:1::', addr='2002:a9fe:a9fe::',
    addr='2001:0:4136:e378:8000:63bf:3fff:fdd2', addr='64:ff9b::7f00:1',
    addr='64:ff9b:1::7f00:1', addr='::7f00:1', addr='::ffff:0:7f00:1')
```

**Passing lock tests (confirmed green in the RED run, as designed):**

```
TestParserDifferentialGuard::test_accepts_punycode_host               (D-14 xn-- lock)
TestParserDifferentialGuard::test_parser_agreement_matches_for_allowed_hosts (parser-agreement lock)
TestValidateUrl::test_rejects_6to4_embedded_loopback                   (WR-03 real-table lock)
TestValidateUrl::test_rejects_6to4_embedded_metadata                   (WR-03 real-table lock)
TestValidateUrl::test_rejects_teredo                                  (WR-03 real-table lock)
TestValidateUrl::test_rejects_nat64_local_use_embedded_metadata        (WR-03 real-table lock)
TestValidateUrl::test_rejects_siit_embedded_metadata                   (WR-03 real-table lock)
TestValidateUrl::test_accepts_ula_neighbor_of_aws_metadata             (D-12 allow lock)
TestValidateUrl::test_accepts_fd00_ec2_neighbor                        (D-12 allow lock)
TestValidateUrl::test_accepts_tailscale_magicdns                      (D-12 allow lock)
TestValidateUrl::test_accepts_alibaba_metadata_neighbor                (D-12 allow lock)
TestValidateUrl::test_accepts_cgnat_address                           (D-12 allow lock)
TestLanRelaxationScope::test_validate_url_only_called_from_test_arr_connection
TestLanRelaxationScope::test_validate_url_not_referenced_outside_config_handler
TestLanRelaxationScope::test_outbound_http_modules_are_known
```

Every one of the 115 pre-existing (Phase 125-01) tests plus every lock test above passed unchanged in the RED run. No test meant to be a lock failed, and no test meant to be RED passed unexpectedly — no deviation needed.

## GREEN

Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_sonarr5 -p no:cacheprovider -q`

Result: **201 passed, 87 subtests passed, 0 failed** (2 warnings: pre-existing `cache_dir` pytest-config notice and `webob`/`cgi` deprecation, unrelated to this change).

Whole-tree lint: `ruff check src/python/` → **All checks passed!**

Broader sanity (not part of the plan's verify command, run for extra confidence): `tests/unittests/test_web` + `tests/unittests/test_controller/test_arr_queue.py` → **492 passed, 33 subtests passed, 0 failed**.

Interpreter: `poetry run pytest` under this project's poetry venv, Python 3.12.12 (within the project's `>=3.11,<3.13` range) — no Docker fallback needed.

Commit pair: `730d3c7` (test, RED) → `b6d0902` (fix, GREEN).

## Final Refusal-Message Table

| Category | Message | New in this plan? |
|----------|---------|---|
| Loopback, wrong/no port | `Loopback addresses are only allowed on port 8989 (Sonarr) or 7878 (Radarr)` | no (125-01) |
| Link-local / cloud-metadata | `URL points to a link-local or cloud-metadata address, which is not allowed` | reused for D-12 |
| Unspecified | `URL points to an unspecified address (0.0.0.0 or ::), which is not allowed` | no (125-01) |
| Multicast | `URL points to a multicast address, which is not allowed` | no (125-01) |
| Reserved (incl. transition forms) | `URL points to a reserved IP address, which is not allowed` | reused for WR-03 |
| Unparseable resolved address | `URL resolves to an address that could not be checked, which is not allowed` | no (125-01) |
| Malformed port | `Invalid URL: invalid port` | no (125-01) |
| Malformed URL / parser disagreement / `%` in host | `Invalid URL` | reused for CR-01 |
| No hostname / unresolvable | `Invalid URL: no hostname` / `Cannot resolve hostname` | reused for WR-02 |
| Disallowed character (space/backslash/control/non-ASCII) | `Invalid URL: it contains a space, backslash or other character that is not allowed` | **yes (D-11/D-14)** |
| Credentials in URL | `Invalid URL: a user name or password in the URL is not allowed` | **yes (D-11)** |
| Query string / fragment | `Invalid URL: a query string or fragment (? or #) is not allowed` | **yes (D-14)** |
| Malformed hostname | `Invalid URL: malformed hostname` | **yes (WR-02)** |

## Files Created/Modified

- `src/python/web/handler/config.py` — added `_URL_CHARS`, `_HOSTNAME_RE`, `_METADATA_NETWORKS`, four new `_MSG_*` constants, and `from urllib3.util import parse_url`; `_classify_resolved_address` gained the metadata check (after link-local, before the allowed-private-range check) and six new `_REFUSED_NETWORKS` entries; `_validate_url` rewritten as a 9-step ordered check (character allow-list → parse → scheme/hostname → credentials/percent → query/fragment → port → hostname syntax → parser agreement → resolution); `_test_arr_connection` now normalizes once and reuses that string for both validation and the request.
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` — added `BAD_CHARS_MSG`/`CREDENTIALS_MSG`/`QUERY_MSG`/`BAD_HOSTNAME_MSG`/`UNRESOLVABLE_MSG` literals; added 9 new handler-level tests across the Sonarr/Radarr classes; added a new `TestParserDifferentialGuard` class (19 tests) for direct `_validate_url` parser-differential/character/hostname-syntax cases; added 14 new tests to `TestValidateUrl` (WR-03 real-table + simulated-old-interpreter, D-12); widened `TestLanRelaxationScope`'s directory exclusions and outbound-HTTP-module regex.

## Decisions Made

- Used the plan's locked D-11/D-14 message strings verbatim as module-level test literals (not imported from `config.py`), following the established 125-01 convention.
- WR-03's explicit `_REFUSED_NETWORKS` additions are provably defence-in-depth on this repo's current Python 3.12.12 (the five "real-table" lock tests pass identically before and after the GREEN commit); the `PropertyMock`-simulated-old-interpreter test is what actually distinguishes RED from GREEN for the gh-113171 concern.
- `requirements-completed` left empty in this SUMMARY's frontmatter and `REQUIREMENTS.md` is left untouched — LAN-01/LAN-02 completion is deferred to whichever of 125-05/125-06 is the final gap-closure plan, per explicit instruction for this plan.

## Deviations from Plan

None — plan executed exactly as written. Every RED failure and every RED-run lock pass matched the plan's predicted set on the first run; no test correction was needed before the RED commit.

## Issues Encountered

- A full local-suite run (`tests/unittests`, not part of this plan's verify command) shows 21 failed / 1965 passed / 3 errors, all in files unrelated to this plan (`test_ssh/test_sshcp.py`, `test_controller/test_extract/test_extract_process.py`, `test_controller/test_scan/test_scanner_process.py`, `test_system/test_scanner.py::test_scan_file_with_latin_chars`) — confirmed via grep that none of these files reference `ConfigHandler` or `_validate_url`. This is the same category of pre-existing, environment-dependent failure already documented in `.planning/phases/125-lan-connection-tests/deferred-items.md` from Plan 125-01 (missing `testgroup` Unix group, multiprocessing-spawn flakiness under full-suite load, filesystem-encoding dependency); counts differ slightly from the 125-01 baseline (26 failed there) because `test_app_process.py`'s 5 tests passed this run — consistent with the documented flakiness, not a regression from this plan. No fix applied here (out of scope; `deferred-items.md` not modified).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CR-01, WR-01 (via D-12), WR-02, WR-03, IN-01 and IN-02 from `125-REVIEW.md` are closed with regression tests. D-14 (non-ASCII hosts, `?`/`#`) is closed.
- Plans 125-05/125-06 (if they close the remaining D-13 release-notes/CHANGELOG items and any final PR CI / sandbox re-check) can rely on this guard's 9-step `_validate_url` ordering and the message table above.
- `REQUIREMENTS.md` is untouched; LAN-01/LAN-02 completion is deferred to the plan that closes the phase.

## Self-Check: PASSED

All claimed files exist on disk and both commit hashes (`730d3c7`, `b6d0902`) are present in `git log --oneline --all` (verified below).

---
*Phase: 125-lan-connection-tests*
*Completed: 2026-10-27*
