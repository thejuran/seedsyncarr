---
phase: 125-lan-connection-tests
verified: 2026-10-28T18:30:00Z
status: passed
score: 13/13 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 125: LAN Connection Tests Verification Report

**Phase Goal:** Test Connection works for the local Sonarr/Radarr addresses people actually use, without opening the test endpoint to arbitrary destinations
**Verified:** 2026-10-28
**Status:** passed
**Re-verification:** No — initial verification (no prior 125-VERIFICATION.md existed)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC1/LAN-01) | Test Connection succeeds for private-range IPs (`10.x`, `172.16-31.x`, `192.168.x`) and for a Docker container/host name resolving to a private address; Phase 120 D-02 failure fixed | ✓ VERIFIED | `_classify_resolved_address` in `config.py:85-141` allows these ranges; unit tests `test_accepts_ipv4_private_10/172_16/192_168`, `test_accepts_container_name_resolving_to_docker_bridge` (ran locally, pass). Live NAS evidence (125-LAN-EVIDENCE.md "Live re-check"): `POSITIVE PASS` against `http://sonarr-v5:8989` on `DEV_PIN_R2`, `success=true version=5.0.0.2800`; `BEFORE` on 1.7.6 reproduces the old failure exactly |
| 2 (SC2/LAN-02) | Cloud-metadata/link-local, loopback-to-unexpected-port, and redirects to disallowed targets still rejected with the same user-visible outcome shape | ✓ VERIFIED | `_MSG_LINK_LOCAL`/`_MSG_LOOPBACK_PORT` paths unchanged in shape (`{success: false, error}` HTTP 200); unit tests `test_rejects_cloud_metadata`, `test_rejects_loopback_on_other_port`, `test_sonarr_redirect_to_metadata_is_not_followed` all pass; live `NEGATIVE PASS` against `http://169.254.169.254` with exact locked message |
| 3 (SC3/D-06) | New acceptance limited to the Sonarr/Radarr test-connection path; no other outbound path relaxed | ✓ VERIFIED | `TestLanRelaxationScope` (3 tests, `test_config_handler.py:1549-1629`) proves `_validate_url` has exactly one definition, one call site (`_test_arr_connection`), and the only outbound-HTTP production modules are `config.py` + `controller/arr_queue.py` (which never calls the guard) — confirmed by direct grep of `arr_queue.py` (imports `requests`, no reference to `_validate_url`) |
| 4 (SC4/D-10/D-13) | Change noted as the minor-version driver in 1.8.0 release notes, including a plain security disclosure | ✓ VERIFIED | `CHANGELOG.md` `## [Unreleased]` section (lines 7-50) states the behaviour accurately post-gap-closure: Changed bullets for LAN acceptance + malformed/ambiguous-URL refusals; Security bullets lead with the plain D-13 disclosure, the backslash parser-differential explanation, and the D-12 metadata note |
| 5 (CR-01) | Parser-differential bypass (backslash/userinfo URLs reaching refused destinations) closed | ✓ VERIFIED | `config.py:213-275` 9-step ordered validation: character allow-list before any parsing, parser-agreement check (`urlparse` vs `urllib3.util.parse_url`) before resolution. `test_sonarr_backslash_payload_never_reaches_transport` patches only `requests.adapters.HTTPAdapter.send` (real requests/urllib3 stack) and asserts `send` never called — ran locally, passes. Live NAS: `NEGATIVE_CR01 PASS` against `http://169.254.169.254\@sonarr-v5:8989` with exact locked message, real Docker DNS and real transport |
| 6 (WR-01/D-12) | AWS IPv6 IMDS (`fd00:ec2::254`) and Alibaba metadata (`100.100.100.200`) refused despite falling inside allowed ULA/CGNAT ranges | ✓ VERIFIED | `_METADATA_NETWORKS` (`config.py:45-48`) checked before the allowed-private-range check; `test_rejects_aws_ipv6_metadata`, `test_rejects_alibaba_metadata(+ipv6_mapped)` pass; neighbor-allow locks (`test_accepts_fd00_ec2_neighbor`, `test_accepts_tailscale_magicdns`) pass, proving no over-broad refusal |
| 7 (WR-02) | Malformed hostnames return a normal JSON error instead of an unhandled 500 | ✓ VERIFIED | `config.py:254-262,277-282` catches `UnicodeError`/`ValueError` from `getaddrinfo` and validates hostname syntax via `_HOSTNAME_RE` before resolution; `test_sonarr_malformed_hostname_returns_json_error` and `TestParserDifferentialGuard` consecutive-dot/bare-dot/64-char-label tests pass |
| 8 (WR-03) | IPv6-transition forms (6to4, Teredo, NAT64, SIIT) refused by explicit network checks, not interpreter-version-dependent `is_global`/`is_reserved` tables | ✓ VERIFIED | `_REFUSED_NETWORKS` (`config.py:59-67`) lists all 6 explicit ranges; `test_rejects_ipv6_transition_forms_on_simulated_old_interpreter_tables` (`PropertyMock` simulating old-interpreter tables) proves refusal is independent of stdlib table version — pass |
| 9 (IN-01) | Validated string equals the requested string (no whitespace/trailing-slash mismatch) | ✓ VERIFIED | `_test_arr_connection` (`config.py:369`) normalizes once (`raw_url.strip().rstrip("/")`) and reuses that exact string for both `_validate_url` and `requests.get`; `test_sonarr_trims_whitespace_and_requests_exact_validated_url` passes |
| 10 (IN-02) | `TestLanRelaxationScope` no longer brittle to `.venv`/`build`/`dist` dirs or narrow import regex | ✓ VERIFIED | `_EXCLUDED_DIR_NAMES` and widened `pattern` in `test_config_handler.py:1558-1628`; scope test still correctly finds exactly `{web/handler/config.py, controller/arr_queue.py}` |
| 11 (IN-03) | CHANGELOG wording accurate once CR-01/WR-01 fixed | ✓ VERIFIED | `CHANGELOG.md` rewritten in 125-05 (commit `18de612`) to match post-125-04 behavior; verified by direct read above |
| 12 (D-14) | Non-ASCII hosts and `?`/`#` refused; `xn--` punycode form still accepted | ✓ VERIFIED | `_URL_CHARS` character allow-list (`config.py:213-219`) and explicit `?`/`#` check (`config.py:245-246`); `test_rejects_non_ascii_host`, `test_rejects_query_string`, `test_rejects_fragment`, `test_accepts_punycode_host` all pass |
| 13 (TDD ordering) | `test(125-01)` precedes `fix(125-01)`; `test(125-04)` precedes `fix(125-04)`; each fix commit touches only `config.py` | ✓ VERIFIED | `git log`: `8a69fdf` (test, 2 test files only) → `f82e256` (fix, `config.py` only); `730d3c7` (test, test file only) → `b6d0902` (fix, `config.py` only). Confirmed via `git show --stat` on each commit |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/web/handler/config.py` | Ordered allow/refuse classifier + parser-agreement guard + metadata refusal + IPv6-transition refusal | ✓ VERIFIED | `_classify_resolved_address`, `_ALLOWED_PRIVATE_NETWORKS`, `_METADATA_NETWORKS`, `_REFUSED_NETWORKS`, 9-step `_validate_url`, single-normalization `_test_arr_connection` all present and match SUMMARY claims line-for-line |
| `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` | LAN-01/LAN-02 + CR-01/WR-01..03/IN-01..03/D-14 regression tests | ✓ VERIFIED | `TestValidateUrl`, `TestParserDifferentialGuard` (19 tests), `TestLanRelaxationScope` (3 tests, hardened) all present; 201 passed/87 subtests confirmed by direct run |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` | Container-name motivating case flipped to accepted | ✓ VERIFIED | `test_docker_network_url_accepted_by_lan_guard` present and passing |
| `CHANGELOG.md` | 1.8.0-draft `[Unreleased]` entry noting the behaviour change + security disclosure | ✓ VERIFIED | Present, accurate post-gap-closure (read directly) |
| `.planning/phases/125-lan-connection-tests/125-livecheck.sh` / `125-teardown.sh` | D-09 live-check scripts incl. `NEGATIVE_CR01` and restore-on-any-failure | ✓ VERIFIED (via SUMMARY + evidence; scripts present on disk, not independently re-run against the live NAS per task instructions) | Live NAS evidence is owner-approved human verification per task instructions — not re-executed by this verifier |
| `125-LAN-EVIDENCE.md` | Full phase-gate record, live-check narrative, verdict tables (both pre- and post-gap-closure) | ✓ VERIFIED | Present, internally consistent, cites exact commit hashes and test names that match the actual git history and code |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_test_arr_connection` | `ConfigHandler._validate_url` | single call on normalized `url` before `requests.get` | WIRED | `config.py:372`: `error_msg = ConfigHandler._validate_url(url)` called on the same `url` variable later passed to `requests.get` (`config.py:381`) |
| `_validate_url` | `_classify_resolved_address` | called once per `getaddrinfo` result with resolved port | WIRED | `config.py:287-295` loop over `addr_infos`, calling `_classify_resolved_address(addr, port)` |
| `_validate_url` | `urllib3.util.parse_url` | parser-agreement check before resolution | WIRED | `config.py:269` `u3 = parse_url(url)`, compared against `urlparse` result at `config.py:272-275`, before step 9 (resolution) |
| `controller/arr_queue.py` | `_validate_url` | (must NOT exist — scope boundary) | CORRECTLY NOT WIRED | `arr_queue.py` imports `requests` but never references `_validate_url`; confirmed by grep and `TestLanRelaxationScope` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LAN-01 | 125-01, 125-04, 125-06 | Test Connection succeeds for representative local configs | ✓ SATISFIED | Unit + live evidence above; REQUIREMENTS.md marks "Complete" |
| LAN-02 | 125-01, 125-04, 125-06 | Unintended destinations stay rejected | ✓ SATISFIED | Unit + live evidence above; REQUIREMENTS.md marks "Complete" |

No orphaned requirements found — REQUIREMENTS.md maps only LAN-01/LAN-02 to Phase 125, and both appear in plan frontmatter `requirements:` fields.

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across `config.py`, `test_config_handler.py`, `test_sonarr5_system_status.py`, and `CHANGELOG.md` returned no matches.

### Behavioral Spot-Checks / Test Execution

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Targeted phase test suite | `poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_sonarr5 -p no:cacheprovider -q` | 201 passed, 87 subtests passed, 0 failed | ✓ PASS |
| Whole-tree lint | `ruff check src/python/` (from repo root) | All checks passed! | ✓ PASS |
| TDD commit ordering (125-01) | `git show --stat 8a69fdf` / `f82e256` | test commit = 2 test files only; fix commit = `config.py` only, test precedes fix in history | ✓ PASS |
| TDD commit ordering (125-04) | `git show --stat 730d3c7` / `b6d0902` | test commit = test file only; fix commit = `config.py` only, test precedes fix in history | ✓ PASS |
| Full local suite regression check (not part of plan's verify command, run for extra confidence) | `poetry run pytest tests/unittests -p no:cacheprovider -q` | 21 failed, 1965 passed, 3 errors — exact match to the documented pre-existing environmental baseline (`test_ssh/test_sshcp.py`, `test_extract_process.py`, `test_scanner_process.py`, `test_scanner.py::test_scan_file_with_latin_chars`); zero failures reference `ConfigHandler`/`_validate_url` | ✓ PASS (no regression) |
| Scope boundary: `_validate_url` only in `config.py`; `arr_queue.py` never calls it | direct grep + `TestLanRelaxationScope` | confirmed | ✓ PASS |
| Transport-level CR-01 proof (unmocked `requests`/`urllib3`) | `test_sonarr_backslash_payload_never_reaches_transport` (part of the targeted suite run above) | passes; `requests.adapters.HTTPAdapter.send` never called | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; the equivalent live-system check is the NAS sandbox live-check (`125-livecheck.sh`), which is owner-approved human verification (see Human Verification Required below) rather than an automated probe this verifier re-executes.

### Human Verification Required

None outstanding. The phase's one `checkpoint:human-verify` gate (Task 3 of 125-06: "Owner review of the updated Phase 125 verdict") was already executed during the phase and the owner replied "approved" (recorded verbatim in both `125-06-SUMMARY.md` and `125-LAN-EVIDENCE.md`, independently cross-checked by the orchestrator in a fresh `ssh nas` session per the SUMMARY). D-09's live NAS check (container-name success, cloud-metadata refusal, CR-01 payload refusal, sandbox restore, production untouched) is recorded as live evidence in `125-LAN-EVIDENCE.md` and treated as already-completed human verification per the task instructions ("Live sandbox evidence (owner-approved twice) ... treat it as recorded human verification; do not touch the NAS").

### Gaps Summary

No gaps found. All 13 derived observable truths (roadmap success criteria 1-4, plus the code-review closure items CR-01, WR-01, WR-02, WR-03, IN-01, IN-02, IN-03, D-14, and TDD ordering) are verified against the actual codebase:

- `src/python/web/handler/config.py` implements exactly what the SUMMARYs and `125-LAN-EVIDENCE.md` claim — read directly and cross-checked line-by-line against the review's suggested fixes.
- The targeted test suite (201 passed, 87 subtests, 0 failed) and whole-tree `ruff check` both pass when run independently by this verifier, not just quoted from SUMMARY.md.
- A full local-suite run confirms zero regressions: the exact same 21 pre-existing, environment-dependent failures (unrelated to `ConfigHandler`) appear before and after this phase's commits.
- TDD commit ordering (test-before-fix, each commit touching only its expected files) is independently confirmed via `git show --stat` for both the original fix (125-01) and the gap-closure fix (125-04).
- The scope boundary (D-06: only the Sonarr/Radarr Test Connection path changed) is independently confirmed: `_validate_url` has one definition, one call site, and `controller/arr_queue.py` — the only other outbound-HTTP production module — never references it.
- CHANGELOG.md accurately reflects the final guard behavior, including the D-13 plain-language security disclosure.
- REQUIREMENTS.md correctly marks LAN-01 and LAN-02 "Complete" with no orphaned requirement IDs for this phase.
- The one blocking human-verification checkpoint in the phase (owner review of the gap-closure verdict) was already completed and approved during phase execution, with the owner's verbatim reply recorded in two places.

---

_Verified: 2026-10-28_
_Verifier: Claude (bm-verifier)_
