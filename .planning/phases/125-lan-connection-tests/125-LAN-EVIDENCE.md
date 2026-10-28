# Phase 125 LAN-01 / LAN-02 evidence

## Unit regressions (RED before GREEN)

- RED (test, `8a69fdf`): `test(125-01): add failing LAN classifier regression tests (LAN-01, LAN-02)`
  - Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_sonarr5/test_sonarr5_system_status.py -p no:cacheprovider -q`
  - Result: **69 failed, 54 passed** (pytest-subtests reports 16 of the 69 as `SUBFAILED` sub-cases of one parametrized test, `test_refusal_messages_never_mention_private_or_echo_host`)
  - Representative failing test ids (full list in 125-01-SUMMARY.md "RED"): `TestValidateUrl::test_accepts_ipv4_private_10`, `TestValidateUrl::test_accepts_container_name_resolving_to_docker_bridge`, `TestValidateUrl::test_rejects_cloud_metadata`, `TestValidateUrl::test_rejects_ipv4_multicast`, `TestSonarr5SystemStatus::test_docker_network_url_accepted_by_lan_guard`
  - Passing lock tests confirmed green in the same RED run: `TestLanRelaxationScope::test_outbound_http_modules_are_known`, `TestLanRelaxationScope::test_validate_url_not_referenced_outside_config_handler`, `TestLanRelaxationScope::test_validate_url_only_called_from_test_arr_connection`, `TestConfigHandlerTestSonarrConnection::test_sonarr_redirect_to_metadata_is_not_followed`, `TestConfigHandlerTestRadarrConnection::test_radarr_redirect_is_not_followed`, `TestSonarr5SystemStatus::test_cgnat_address_passes_url_validation`

- GREEN (fix, `f82e256`): `fix(125-01): accept LAN and container addresses in Test Connection, keep metadata/link-local/multicast/reserved refused (LAN-01, LAN-02)`
  - Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_sonarr5 -p no:cacheprovider -q`
  - Result: **158 passed, 74 subtests passed, 0 failed, 2 warnings** (warnings are pre-existing `cache_dir` pytest-config and `webob`/`cgi` deprecation notices, unrelated to this change)
  - Whole-tree lint at GREEN: `ruff check src/python/` -> `All checks passed!`

## Gates

### Gate 1 (suite vs. environmental baseline)

Preconditions: `git branch --show-current` -> `gsd/phase-125-lan-connection-tests`; `git status --porcelain -- src/` -> empty; `git fetch origin`; `BASE=$(git merge-base origin/main HEAD)` -> `1ce120c642ae984cd66c055a38aa70804ab18e53`.

Command: `cd src/python && timeout 900 poetry run pytest tests/unittests -p no:cacheprovider -q`

Completed normally in 85.02s (no timeout/exit 124 — the `--ignore` rerun path was not needed).

Verbatim summary line:
```
21 failed, 1922 passed, 2 warnings, 3 errors, 93 subtests passed in 85.02s (0:01:25)
```

Extracted `FAILED `/`ERROR ` lines (suffix after ` - ` stripped), sorted, 24 lines — identical to the documented 122-03/123-05 environmental baseline (test_extract_process.py x6, test_scanner_process.py 3 FAILED + 3 ERROR, test_sshcp.py x11, test_scanner.py::test_scan_file_with_latin_chars x1):

```
ERROR tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_retrieves_scan_results
ERROR tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_sends_error_result_on_recoverable_error
ERROR tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_sends_fatal_exception_on_nonrecoverable_error
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_calls_start_dispatch
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_forwards_extract_commands
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_param_out_dir_path
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_param_out_local_path
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_retrieves_completed
FAILED tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_retrieves_status
FAILED tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_retrieves_scan_results
FAILED tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_sends_error_result_on_recoverable_error
FAILED tests/unittests/test_controller/test_scan/test_scanner_process.py::TestScannerProcess::test_sends_fatal_exception_on_nonrecoverable_error
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_copy
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_copy_error_bad_host
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_copy_error_bad_port
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_copy_error_missing_local_file
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_copy_error_missing_remote_dir
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_ctor
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_shell
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_shell_error_bad_command
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_shell_error_bad_host
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_shell_error_bad_port
FAILED tests/unittests/test_ssh/test_sshcp.py::TestSshcp::test_shell_with_escape_characters
FAILED tests/unittests/test_system/test_scanner.py::TestSystemScanner::test_scan_file_with_latin_chars
```

`comm -23 current baseline` -> empty (no new failure; the current 24-line set is exactly the documented baseline set). No new failure, no fix-code step needed.

Result: **PASS** (24 lines, 21 FAILED + 3 ERROR, subset of/equal to the fixed baseline).

### Gate 2 (lint)

Command: `cd /Users/julianamacbook/seedsyncarr && ruff check src/python/`

Output: `All checks passed!`

Result: **PASS**

### Gate 3 (RED before GREEN, D-08)

`git log --format="%h %s" --reverse $BASE..HEAD` (relevant excerpt, in order):
```
8a69fdf test(125-01): add failing LAN classifier regression tests (LAN-01, LAN-02)
f82e256 fix(125-01): accept LAN and container addresses in Test Connection, keep metadata/link-local/multicast/reserved refused (LAN-01, LAN-02)
```
`test(125-01)` precedes `fix(125-01)`.

`git show --stat --format= 8a69fdf`:
```
 .../test_sonarr5/test_sonarr5_system_status.py     |  25 +-
 .../test_web/test_handler/test_config_handler.py   | 632 ++++++++++++++++++---
 2 files changed, 577 insertions(+), 80 deletions(-)
```
Both paths are under `src/python/tests/`.

`git show --stat --format= f82e256`:
```
 src/python/web/handler/config.py | 119 +++++++++++++++++++++++++++++++++++----
 1 file changed, 109 insertions(+), 10 deletions(-)
```
Only `src/python/web/handler/config.py`.

Result: **PASS**

### Gate 4 (scope, D-06)

`git diff --name-only $BASE..HEAD -- src/ | sort`:
```
src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
src/python/tests/unittests/test_web/test_handler/test_config_handler.py
src/python/web/handler/config.py
```
Exactly 3 lines, exactly the expected set.

`git diff $BASE..HEAD -- src/python/controller/` -> empty (0 lines).

`grep -n "_validate_url" src/python/web/handler/config.py`:
```
137:    def _validate_url(url: str) -> str | None:
257:        error_msg = ConfigHandler._validate_url(raw_url.strip())
```

`grep -rn "_validate_url" src/python --include="*.py" | grep -v "/tests/"`:
```
src/python/web/handler/config.py:137:    def _validate_url(url: str) -> str | None:
src/python/web/handler/config.py:257:        error_msg = ConfigHandler._validate_url(raw_url.strip())
```
One definition, one call, both in `web/handler/config.py` only.

Result: **PASS**

### Gate 5 (log/secret hygiene, D-07)

Command: `git diff $BASE..HEAD -- src/python/web/handler/config.py | grep "^+" | grep -cE "logger\.|api_key|X-Api-Key"`

Output: `0`

Result: **PASS**

## Build under test

- PR: https://github.com/thejuran/seedsyncarr/pull/140 (draft, base `main`)
- NEW_HEAD_SHA: `30220569c5802f090d535f74bb151f5c9bb45240` (`docs(125-02): add 1.8.0 draft CHANGELOG entry for LAN Test Connection change`); confirmed equal to `gh pr view 140 --json headRefOid` both before and after the digest lookup
- CI run: https://github.com/thejuran/seedsyncarr/actions/runs/40570275905 (run number 415, workflow `ci.yml`, triggered via `pull_request`), conclusion `success`

Per-check conclusions (`gh pr checks 140`):

| Check | Conclusion | Duration |
|---|---|---|
| Analyze (actions) | pass | 38s |
| Analyze (javascript-typescript) | pass | 57s |
| Analyze (python) | pass | 1m0s |
| Angular unit tests | pass | 2m13s |
| Build Docker Image | pass | 2m44s |
| CodeQL | pass | 3s |
| End-to-end tests on Docker Image (amd64) | pass | 4m23s |
| Lint (Angular) | pass | 19s |
| Lint (Python) | pass | 10s |
| Python unit tests | pass | 5m4s |
| Verify Python package | pass | 27s |
| Verify release metadata | pass | 3s |
| Release metadata verifier tests | pass | 11s |
| Publish Docker Image | skipping | - |
| Publish Docker Image (:dev) | skipping | - |
| Publish Documentation | skipping | - |
| Publish GitHub Release | skipping | - |
| Publish to PyPI | skipping | - |

Publish-* jobs are skipped on `pull_request`, as expected (they run only on `main`/tag pushes).

Equivalence guard (run immediately before the digest lookup): newest `ci.yml` run on the branch still has `headSha == 30220569c5802f090d535f74bb151f5c9bb45240`; `gh pr view 140 --json headRefOid` still equals the same SHA. No later push occurred between CI completion and digest resolution.

Digest resolution — two independent methods, both against `ghcr.io/thejuran/seedsyncarr:415`:

1. `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:415` → index `Digest: sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3`
2. Anonymous GHCR token (`https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io`) + `HEAD https://ghcr.io/v2/thejuran/seedsyncarr/manifests/415` with `Accept: application/vnd.oci.image.index.v1+json` → `docker-content-digest: sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3`

Both methods agree (64 hex chars). The token itself was never printed.

```
DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3
```

This differs from the 1.7.6 digest (`da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`), as required.

Expected sandbox restore pin for 125-03 teardown (unchanged from Phase 123/124, verified restored by 123-07):

```
IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
```

## Live check (D-09)

### Attempt 1 (harness bug, retried)

Capture dir `/volume1/docker/v5test/results/lan01-125-20261027T195659Z`. Preflight passed (`.Config.Image` and the compose line both equal `IMAGE_PIN_L0`). The script deployed `DEV_PIN` cleanly (inode-preserved compose edit, fresh `Starting SeedSyncarr` line, `/server/status` 200, `.Config.Image` == `DEV_PIN`) and `POSITIVE` genuinely passed (`success=true version=5.0.0.2800`), but `NEGATIVE` was reported `FAIL` with an **empty** captured error even though the raw response written to `negative.json` was already exactly correct:

```
{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}
```

Root cause: `tc()`'s field extraction used `jq -r '.success, (.version // empty), (.error // empty)'`. jq's `empty` filter produces **zero output values** for a missing field, rather than a blank line, so on a response with no `version` field the `.error` value silently shifted from line 3 up to line 2 -- exactly where the script's fixed-line-number read (`sed -n '3p'`) expected nothing. The same shift affected the `BEFORE` check (`before.json` also had no `version` field), which is why that attempt printed `old_msg=0` for a response that does contain "private/reserved". `POSITIVE` was unaffected only because its read uses line 2, which is where `version` already was.

Because `NEGATIVE`'s own `sonarr_url` restore step ran and succeeded before this miscount was evaluated, `OK=1` fired and the EXIT trap correctly did **not** run `teardown.sh --final` -- the sandbox was left mid-session on `DEV_PIN` with `sonarr_url` already back at `http://sonarr-v5:8989`, confirmed by a direct read-back immediately afterward. No product code was touched. Fixed in `125-livecheck.sh` (`fix(125-03)`, commit `d642a59`): both fallbacks changed to `// ""`, which always emits an empty string in place of a missing field, verified locally against both response shapes before reuse. `teardown.sh --final` was then run against this same capture dir to restore the sandbox to `IMAGE_PIN_L0` as a clean baseline for the retry (`SANDBOX_RESTORED ok`).

### Attempt 2 (DEV_PIN, PASS)

Capture dir `/volume1/docker/v5test/results/lan01-125-20261027T200205Z-retry`. Same `state.env` (`IMAGE_PIN_L0`, `DEV_PIN` as above). Both scripts copied via `ssh nas 'cat > ...'` (not `scp`, which the session's SSH config refused) and checksum-verified byte-identical to the committed files before running.

- **Preflight:** `PREFLIGHT ok` -- compose line and `.Config.Image` both equal `IMAGE_PIN_L0` before any change.
- **Compose inode (DEV_PIN edit):** `INODE before=101505523 after=101505523` -- same inode, in-place rewrite confirmed.
- **Readiness transcript:** `seedsyncarr-test Pulling` -> `Pulled` -> `Container seedsyncarr-test Recreate` -> `Recreated` -> `Starting` -> `Started` -> `DEPLOY starting-line ok` (fresh `Starting SeedSyncarr` line after the pre-deploy marker) -> `WAIT server/status ok` -> 8s settle.
- **Deployed image:** `DEPLOY image=ghcr.io/thejuran/seedsyncarr@sha256:162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3 id=sha256:1edee4fbe186b13f93c46adaa778e30355f49b09497125b9d836fa51dc5e8fcf` -- `.Config.Image` matched `DEV_PIN` exactly.
- **BEFORE (informational, still on `IMAGE_PIN_L0`):** `BEFORE success=false old_msg=1` -- `before.json`: `{"success": false, "error": "URL resolves to a private/reserved IP address"}`. On the shipping 1.7.6 image, Test Connection to the Docker container name `http://sonarr-v5:8989` fails with the old message, reproducing the Phase 120 D-02 problem being fixed.
- **POSITIVE (LAN-01):** `POSITIVE PASS success=true version=5.0.0.2800` -- `positive.json`: `{"success": true, "version": "5.0.0.2800"}`. On `DEV_PIN`, the same container-name URL now succeeds and reports the live Sonarr 5 version.
- **NEGATIVE (LAN-02):** `NEGATIVE PASS success=false error=URL points to a link-local or cloud-metadata address, which is not allowed` -- `negative.json`: `{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}`, an exact match to the locked refusal string against `http://169.254.169.254`.
- **sonarr_url restore:** `RESTORED sonarr_url ok` -- read back equal to `SONARR_URL_L0` (`http://sonarr-v5:8989`) immediately after the negative check.
- **Informational log counts (window after the pre-deploy marker):** `LOGCOUNT error=2 unexpected_error_testing=0`. The 2 ` - ERROR - ` lines are the pre-existing "Scanner process(es) died unexpectedly: LocalScanner" / "Caught exception in job ControllerJob" pair logged during the container recreate (app-log `2026-10-27 16:02:28`, NAS host clock 20:02:28 UTC) -- the known Phase 123 D-01-scanner-half restart pattern, unrelated to LAN-01/LAN-02 and not part of this phase's scope. Zero `Unexpected error testing` lines.
- **Production fingerprint during the check:** `prod-before.txt` and `prod-after.txt` are byte-identical (`diff` empty): `2feb4073db71... sha256:5b801f83... ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0... running 2026-10-23T07:04:18.591254939Z`.
- **CHECK_STATUS:** `PASS` (`state.env`: `POSITIVE=PASS`, `NEGATIVE=PASS`, `SONARR_URL_SET=0`, `CHECK_STATUS=PASS`). Last line: `LIVECHECK PASS`, exit 0.

### Final restore (`teardown.sh --final`)

Run against the Attempt 2 capture dir immediately after `LIVECHECK PASS`:

```
INODE before=101505523 after=101505523
 seedsyncarr-test Pulling
 seedsyncarr-test Pulled
 Container seedsyncarr-test  Recreate
 Container seedsyncarr-test  Recreated
 Container seedsyncarr-test  Starting
 Container seedsyncarr-test  Started
WAIT server/status ok
RESTORED sonarr_url ok (not set this session)
CHECK image=restored ok
SANDBOX_RESTORED ok
```

Last line `SANDBOX_RESTORED ok`.

### Fresh-session restore check

In a second, independent `ssh nas` call, after the final restore:

| Check | Result |
|---|---|
| `.Config.Image` | `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` -- equals `IMAGE_PIN_L0` exactly |
| Compose `seedsyncarr-test` image line | `image: ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` -- equals `IMAGE_PIN_L0` |
| `.sonarr.sonarr_url` | `http://sonarr-v5:8989` -- equals `SONARR_URL_L0` |
| `GET /server/status` | `200` |
| Production fingerprint (`prod-final.txt`) vs `prod-before.txt` | byte-identical, `diff` empty |

### Production unchanged

`prod-before.txt`, `prod-after.txt` (during the check) and `prod-final.txt` (fresh session, after the final restore) are all byte-identical:

```
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 sha256:5b801f8397d68bf9bb35eed0d4f882cae2ab24100e4d28be4006f8f028e0ef62 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e running 2026-10-23T07:04:18.591254939Z
```

`StartedAt` (`2026-10-23T07:04:18.591254939Z`) matches the value recorded in `123-LIFE-EVIDENCE.md` "### Production unchanged" exactly -- no drift. Production `seedsyncarr` was never started, stopped, recreated or reconfigured anywhere in this plan; the only command ever run against it was the single read-only `docker inspect` fingerprint, confirmed by the acceptance grep on `125-livecheck.sh` (`PROD_NAME` appears only in its own definition and one `inspect "$PROD_NAME" --format` line).

## Phase 125 verdict

| Item | Decision / criterion | Evidence | Verdict |
|------|----------------------|----------|---------|
| LAN-01 (SC1) | Test Connection succeeds for private-range IPs and a Docker container/host name resolving to a private address; the Phase 120 D-02 container-name failure is fixed | Unit: 125-01 `test_accepts_ipv4_private_10`, `test_accepts_container_name_resolving_to_docker_bridge` + other representative-range tests (`8a69fdf`→`f82e256`), 158 passed/74 subtests. Live: this plan's Attempt 2 `BEFORE` on `IMAGE_PIN_L0` (1.7.6) reproduces the old failure (`success=false`, "private/reserved" message) against `http://sonarr-v5:8989`; `POSITIVE` on `DEV_PIN` succeeds (`success=true version=5.0.0.2800`) against the identical URL | PASS |
| LAN-02 (SC2) | Cloud-metadata/link-local addresses, loopback-to-unexpected-port probes and redirects stay rejected with the same user-visible outcome | Unit: 125-01 `test_rejects_cloud_metadata`, `test_rejects_ipv4_multicast`, loopback-port and redirect-not-followed tests (`TestConfigHandlerTestSonarrConnection::test_sonarr_redirect_to_metadata_is_not_followed`, `TestConfigHandlerTestRadarrConnection::test_radarr_redirect_is_not_followed`). Live: this plan's `NEGATIVE` on `DEV_PIN` against `http://169.254.169.254` returns `success=false` with the exact locked string "URL points to a link-local or cloud-metadata address, which is not allowed" | PASS |
| SC3 (scope: only the Sonarr/Radarr test-connection path changes) | No other outbound request path is relaxed | 125-02 Gate 4: `_validate_url` has exactly one definition and one call site, both in `web/handler/config.py`; `TestLanRelaxationScope` suite (`test_outbound_http_modules_are_known`, `test_validate_url_not_referenced_outside_config_handler`, `test_validate_url_only_called_from_test_arr_connection`) passed at RED and GREEN | PASS |
| SC4 (release notes note the behaviour change) | The change is recorded as the 1.8.0 minor-version driver | 125-02 Task 1: `CHANGELOG.md` `## [Unreleased]` section with `### Changed`/`### Security` bullets for the LAN Test Connection behaviour change, above `## [1.7.6]` | PASS |
| D-01 (allowed destinations) | Private LAN ranges, IPv6 ULA, Tailscale/CGNAT and public addresses allowed; container/host names pass when every resolved address is allowed | 125-01-SUMMARY.md RED/GREEN test list (`test_accepts_ipv4_private_10`, `172.16-31` range, IPv6 ULA, `test_cgnat_address_passes_url_validation` unchanged); live `POSITIVE` confirms the container-name case | PASS |
| D-02 (loopback only on 8989/7878) | Loopback allowed only on Sonarr/Radarr default ports; other ports or no explicit port refused | 125-01 loopback-port test class (full-path coverage, both allowed ports and both disallowed cases) | PASS (unit-proven; not separately exercised live in this plan) |
| D-03 (still refused) | Link-local/cloud-metadata, IPv6 link-local, unspecified, other reserved, multicast, mapped-form bypasses stay refused | 125-01 `test_rejects_cloud_metadata`, `test_rejects_ipv4_multicast`, unspecified/`fe80::`/mapped-form tests; live `NEGATIVE` reproduces the cloud-metadata case end to end | PASS |
| D-04 (mixed resolution fail-closed) | A hostname resolving to several addresses is refused if any is refused | 125-01 mixed-resolution regression test (stubbed `getaddrinfo`) | PASS (unit-proven only) |
| D-05 (redirects unchanged) | 3xx responses are never followed; existing redirect message unchanged | 125-01 `test_sonarr_redirect_to_metadata_is_not_followed`, `test_radarr_redirect_is_not_followed` | PASS |
| D-06 (scope) | Only `_validate_url`/`_test_arr_connection` changes; no other outbound path relaxed | Same as SC3 row above (125-02 Gate 4) | PASS |
| D-07 (wording) | Specific refusal reasons; old "private/reserved IP address" message no longer appears for allowed addresses; the Sonarr key is never echoed | 125-01 `test_refusal_messages_never_mention_private_or_echo_host`; live `BEFORE` shows the old message only on 1.7.6 (pre-fix), `POSITIVE`/`NEGATIVE` on `DEV_PIN` show the new messages; a case-insensitive key-marker scan of both scripts and the new evidence added in this plan found no matches | PASS |
| D-08 (test-first proof) | RED-before-GREEN regression coverage for every representative case; full suite + whole-tree ruff pass | 125-02 Gates 1-5: suite matches the fixed 24-line environmental baseline exactly, whole-tree `ruff check src/python/` clean, `test(125-01)` (`8a69fdf`) precedes `fix(125-01)` (`f82e256`), exact 3-file scope, 0 new logger/secret lines | PASS |
| D-09 (live check) | Container-name Test Connection works live on the PR image; metadata destination refused with the new message; sandbox restored and verified; production read-only | This plan: Attempt 2 `CHECK_STATUS=PASS`; `teardown.sh --final` ends `SANDBOX_RESTORED ok`; fresh-session check confirms `IMAGE_PIN_L0`, compose line, `sonarr_url`, `/server/status` 200; production fingerprint byte-identical across before/after/final with zero drift vs `123-LIFE-EVIDENCE.md` | PASS |
| D-10 (release notes) | 1.8.0 draft CHANGELOG entry records the behaviour change | 125-02 Task 1 commit `3022056` | PASS |

**Phase 125 live check: PASSED**

The sandbox is restored to `IMAGE_PIN_L0` (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`) and verified in a fresh, independent session. Production `seedsyncarr` was never touched beyond the single permitted read-only fingerprint and is byte-identical before, during and after this plan. PR #140 remains open and draft; nothing was merged.

## Owner review (Task 3)

Owner reply, verbatim, 2026-10-27: "approved"

The owner reviewed, before replying: 1.7.6 failed Test Connection on `http://sonarr-v5:8989` (the old problem); the PR build succeeded against the identical URL and reported Sonarr `5.0.0.2800`; `http://169.254.169.254` was refused with the locked message; the sandbox was restored to 1.7.6 and its original Sonarr URL; production was untouched. The orchestrator independently re-verified in a separate `ssh nas` session: `seedsyncarr-test` and `seedsyncarr` both report `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`; production `StartedAt` `2026-10-23T07:04:18.591254939Z` unchanged.

**Phase 125: owner-approved.**

## Gap closure (D-11, D-12)

A post-approval code review (`125-REVIEW.md`) found a parser-differential SSRF bypass (CR-01) and related gaps after the Phase 125 verdict above; the owner reopened the phase for gap closure (D-11 through D-14). This section records the 125-04 regression closure and the 125-05 gate rerun over it.

### Unit regressions 125-04 (RED before GREEN)

- RED (test, `730d3c7`): `test(125-04): add parser-differential, metadata and malformed-host regressions for Test Connection guard`
  - Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py -p no:cacheprovider -q`
  - Result: **37 failed, 115 passed, 22 subtests passed** (1 warning, pre-existing `cache_dir` pytest-config notice)
  - Full failing-id list and passing-lock-test list are in `125-04-SUMMARY.md` "RED" (CR-01 backslash-userinfo payloads, D-12 metadata addresses, WR-02 malformed hostnames, WR-03 simulated-old-interpreter IPv6-transition forms, D-14 character/IDN cases)

- GREEN (fix, `b6d0902`): `fix(125-04): refuse URLs the guard and requests parse differently; block metadata hosts in allowed ranges`
  - Command: `cd src/python && timeout 600 poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_sonarr5 -p no:cacheprovider -q`
  - Result: **201 passed, 87 subtests passed, 0 failed** (2 warnings, pre-existing and unrelated)
  - Whole-tree lint at GREEN: `ruff check src/python/` -> `All checks passed!`

### Gates (125-05)

Preconditions: `git branch --show-current` -> `gsd/phase-125-lan-connection-tests`; `git status --porcelain -- src/` -> empty; `git fetch origin`; `BASE=$(git merge-base origin/main HEAD)` -> `1ce120c642ae984cd66c055a38aa70804ab18e53` (unchanged from the 125-02 gate run).

**Gate 1 (suite vs. environmental baseline):**

Command: `cd src/python && timeout 900 poetry run pytest tests/unittests -p no:cacheprovider -q`

Completed normally in 82.69s (no timeout/exit 124 — the `--ignore` rerun path was not needed).

Verbatim summary line:
```
21 failed, 1965 passed, 2 warnings, 3 errors, 106 subtests passed in 82.69s (0:01:22)
```

Extracted `FAILED `/`ERROR ` lines (suffix after ` - ` stripped), sorted, 24 lines — `comm -23 current baseline` against the fixed 24-line baseline recorded above under "### Gate 1 (suite vs. environmental baseline)" (test_extract_process.py x6, test_scanner_process.py 3 FAILED + 3 ERROR, test_sshcp.py x11, test_scanner.py::test_scan_file_with_latin_chars x1) is empty — the two 24-line sets are identical (`diff` empty).

Result: **PASS** (24 lines, 21 FAILED + 3 ERROR, no new failure).

**Gate 2 (lint):**

Command: `cd /Users/julianamacbook/seedsyncarr && ruff check src/python/`

Output: `All checks passed!`

Result: **PASS**

**Gate 3 (RED before GREEN, D-08):**

`git log --format="%h %s" --reverse $BASE..HEAD` (relevant excerpt, in order):
```
8a69fdf test(125-01): add failing LAN classifier regression tests (LAN-01, LAN-02)
f82e256 fix(125-01): accept LAN and container addresses in Test Connection, keep metadata/link-local/multicast/reserved refused (LAN-01, LAN-02)
...
730d3c7 test(125-04): add parser-differential, metadata and malformed-host regressions for Test Connection guard
b6d0902 fix(125-04): refuse URLs the guard and requests parse differently; block metadata hosts in allowed ranges
```
`test(125-01)` precedes `fix(125-01)`; `test(125-04)` precedes `fix(125-04)`.

`git show --stat --format= 730d3c7`:
```
 .../test_web/test_handler/test_config_handler.py   | 491 ++++++++++++++++++++-
 1 file changed, 488 insertions(+), 3 deletions(-)
```
Only `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`.

`git show --stat --format= b6d0902`:
```
 src/python/web/handler/config.py | 126 ++++++++++++++++++++++++++++++++++++---
 1 file changed, 119 insertions(+), 7 deletions(-)
```
Only `src/python/web/handler/config.py`.

Result: **PASS**

**Gate 4 (scope, D-06):**

`git diff --name-only $BASE..HEAD -- src/ | sort`:
```
src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
src/python/tests/unittests/test_web/test_handler/test_config_handler.py
src/python/web/handler/config.py
```
Exactly 3 lines, exactly the expected set — unchanged from the 125-02 gate run (125-04 touched only files already in this set).

`git diff $BASE..HEAD -- src/python/controller/` -> empty (0 lines).

`grep -rn "_validate_url" src/python --include="*.py" | grep -v "/tests/"`:
```
src/python/web/handler/config.py:182:    def _validate_url(url: str) -> str | None:
src/python/web/handler/config.py:372:        error_msg = ConfigHandler._validate_url(url)
```
One definition, one call, both in `web/handler/config.py` only.

Result: **PASS**

**Gate 5 (log/secret hygiene, D-07):**

Command: `git diff b6d0902~1 b6d0902 -- src/python/web/handler/config.py | grep "^+" | grep -cE "logger\.|api_key|X-Api-Key"`

Output: `0`

Result: **PASS**

### Build under test (125-05)

- PR: https://github.com/thejuran/seedsyncarr/pull/140 (draft, base `main`, reused — one PR per phase)
- NEW_HEAD_SHA: `18de612d0d3a0ab316b2c108857ba2f768b5d727` (`docs(125-05): make 1.8.0 draft CHANGELOG accurate after Test Connection guard hardening`); confirmed equal to `gh pr view 140 --json headRefOid` both before and after the digest lookup; `fix(125-04)` (`b6d0902`) confirmed an ancestor via `git merge-base --is-ancestor`
- PR description updated: trailing attribution line removed, a "Review follow-up" paragraph appended in plain terms (backslash parser-differential bypass, exact-URL validation, credentials/query/malformed-hostname refusals, the two cloud-metadata-in-allowed-range addresses, explicit IPv6-transition refusals, CHANGELOG updated), attribution line re-added last; PR stayed draft throughout (`gh pr view 140` confirmed `OPEN true` after the edit)
- CI run: https://github.com/thejuran/seedsyncarr/actions/runs/40605742420 (run number 416, workflow `ci.yml`, triggered via `pull_request`), conclusion `success`

Per-check conclusions (`gh pr checks 140`):

| Check | Conclusion | Duration |
|---|---|---|
| Analyze (actions) | pass | 44s |
| Analyze (javascript-typescript) | pass | 55s |
| Analyze (python) | pass | 1m0s |
| Angular unit tests | pass | 2m16s |
| Build Docker Image | pass | 2m26s |
| CodeQL | pass | 2s |
| End-to-end tests on Docker Image (amd64) | pass | 4m4s |
| Lint (Angular) | pass | 24s |
| Lint (Python) | pass | 10s |
| Python unit tests | pass | 4m56s |
| Verify Python package | pass | 27s |
| Verify release metadata | pass | 3s |
| Release metadata verifier tests | pass | 10s |
| Publish Docker Image | skipping | - |
| Publish Docker Image (:dev) | skipping | - |
| Publish Documentation | skipping | - |
| Publish GitHub Release | skipping | - |
| Publish to PyPI | skipping | - |

Publish-* jobs are skipped on `pull_request`, as expected (they run only on `main`/tag pushes).

Equivalence guard (run immediately before the digest lookup): newest `ci.yml` run on the branch still has `headSha == 18de612d0d3a0ab316b2c108857ba2f768b5d727`; `gh pr view 140 --json headRefOid` still equals the same SHA. No later push occurred between CI completion and digest resolution.

Digest resolution — two independent methods, both against `ghcr.io/thejuran/seedsyncarr:416`:

1. `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:416` → index `Digest: sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45`
2. Anonymous GHCR token (`https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io`) + `HEAD https://ghcr.io/v2/thejuran/seedsyncarr/manifests/416` with `Accept: application/vnd.oci.image.index.v1+json` → `docker-content-digest: sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45`

Both methods agree (64 hex chars). The token itself was never printed.

```
DEV_PIN_R2=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45
```

This differs from the pre-fix digest (`DEV_PIN=...162d453217fbada459504d084b8ea2915aca6bd9b2285239f972a487888a75d3`, recorded above under "Build under test") and from the 1.7.6 production digest (`da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`), as required.

Expected sandbox restore pin for 125-06 teardown (unchanged from Phase 123/124/125-03, verified restored by 123-07 and 125-03):

```
IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
```

Routine push output: `git push` surfaced GitHub's standing Dependabot summary (10 vulnerabilities on the default branch, 1 critical/4 high/4 moderate/1 low) — out of this plan's scope; Dependabot review is Phase 126's release-gate responsibility (same note as 125-02).

### Live re-check (D-09, D-11)

Capture dir `/volume1/docker/v5test/results/lan01-125r2-20261028T001748Z` (mode 0700). `livecheck.sh`/`teardown.sh` copied via `ssh nas 'cat > ...' < file` (not `scp`) and sha256-verified byte-identical to the committed files before running. Preflight re-read `seedsyncarr-test .Config.Image` in a fresh `ssh nas` call before writing `state.env` — it equalled `IMAGE_PIN_L0` exactly, confirming no drift since 125-05.

```
IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45
```

(the `DEV_PIN` key in `state.env` holds the `DEV_PIN_R2` value recorded above under "Build under test (125-05)".)

- **Preflight:** `PREFLIGHT ok` — compose line and `.Config.Image` both equal `IMAGE_PIN_L0` before any change.
- **Compose inode (DEV_PIN_R2 edit):** `INODE before=101505523 after=101505523` — same inode, in-place rewrite confirmed.
- **Readiness transcript:** `seedsyncarr-test Pulling` → `Pulled` → `Container seedsyncarr-test Recreate` → `Recreated` → `Starting` → `Started` → `DEPLOY starting-line ok` (fresh `Starting SeedSyncarr` line after the pre-deploy marker) → `WAIT server/status ok` → 8s settle.
- **Deployed image:** `DEPLOY image=ghcr.io/thejuran/seedsyncarr@sha256:76df9d9a5dccb89d1106ca7d0b66e98319e482c6aa65f0d010159df5a19d9d45 id=sha256:81f0377d60508d0ae109756c2733336f43e0a9d438539d757bdc4acd44d1bd1f` — `.Config.Image` matched `DEV_PIN_R2` exactly.
- **BEFORE (informational, still on `IMAGE_PIN_L0`, CR-01 payload intentionally not sent on 1.7.6):** `BEFORE success=false old_msg=1` — `before.json`: `{"success": false, "error": "URL resolves to a private/reserved IP address"}`. Unchanged from 125-03's attempt 2 BEFORE result — the shipping 1.7.6 image still fails the container-name case with the pre-fix message.
- **POSITIVE (LAN-01):** `POSITIVE PASS success=true version=5.0.0.2800` — `positive.json`: `{"success": true, "version": "5.0.0.2800"}`. On the hardened `DEV_PIN_R2` build, `http://sonarr-v5:8989` still succeeds and reports the live Sonarr 5 version — the 125-04 guard rewrite did not break LAN-01.
- **NEGATIVE (LAN-02):** `NEGATIVE PASS success=false error=URL points to a link-local or cloud-metadata address, which is not allowed` — `negative.json`: `{"success": false, "error": "URL points to a link-local or cloud-metadata address, which is not allowed"}`, an exact match to the locked refusal string against `http://169.254.169.254`.
- **NEGATIVE_CR01 (D-11, the 125-REVIEW CR-01 backslash payload):** `NEGATIVE_CR01 PASS success=false error=Invalid URL: it contains a space, backslash or other character that is not allowed` — `negative_cr01.json`: `{"success": false, "error": "Invalid URL: it contains a space, backslash or other character that is not allowed"}`, an exact match to the locked CR-01 refusal string against `http://169.254.169.254\@sonarr-v5:8989`. This is the live, real-`requests`/real-`urllib3`/real-Docker-DNS proof that the parser-differential bypass closed by `fix(125-04)` (`b6d0902`) holds outside the unit-test harness: the backslash payload never reached Sonarr or any other host, and the sandbox's own Sonarr `sonarr-v5` container was reachable throughout (proven by the immediately preceding `POSITIVE` check against it).
- **sonarr_url restore:** `RESTORED sonarr_url ok` — read back equal to `SONARR_URL_L0` (`http://sonarr-v5:8989`) immediately after both negative checks, run once after `NEGATIVE_CR01` per the script's updated restore-after-both-negatives step.
- **Informational log counts (window after the pre-deploy marker):** `LOGCOUNT error=2 unexpected_error_testing=0`. The 2 ` - ERROR - ` lines (app-log `2026-10-27 20:18:58`, NAS host clock ~`2026-10-28 00:18` UTC) are the same pre-existing "Scanner process(es) died unexpectedly" / "Caught exception in job ControllerJob" pair logged during the container recreate as in 125-03's attempt 2 — the known Phase 123 D-01-scanner-half restart pattern, unrelated to LAN-01/LAN-02/D-11 and not part of this phase's scope. Zero `Unexpected error testing` lines.
- **Production fingerprint during the check:** `prod-before.txt` and `prod-after.txt` are byte-identical (`diff` empty): `2feb4073db71... sha256:5b801f83... ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0... running 2026-10-23T07:04:18.591254939Z`.
- **CHECK_STATUS:** `PASS` (`state.env`: `POSITIVE=PASS`, `NEGATIVE=PASS`, `NEGATIVE_CR01=PASS`, `SONARR_URL_SET=0`, `CHECK_STATUS=PASS`). Last line: `LIVECHECK PASS`, exit 0.

No harness defect was hit this round (Task 1's trap fix was not exercised by a failure path, since the check passed cleanly on the first attempt) — unlike 125-03's attempt 1, no retry cycle was needed.

### Final restore (re-check)

Run against this capture dir immediately after `LIVECHECK PASS`:

```
INODE before=101505523 after=101505523
 seedsyncarr-test Pulling
 seedsyncarr-test Pulled
 Container seedsyncarr-test  Recreate
 Container seedsyncarr-test  Recreated
 Container seedsyncarr-test  Starting
 Container seedsyncarr-test  Started
WAIT server/status ok
RESTORED sonarr_url ok (not set this session)
CHECK image=restored ok
SANDBOX_RESTORED ok
```

Last line `SANDBOX_RESTORED ok`.

### Fresh-session restore check (re-check)

In a second, independent `ssh nas` call, after the final restore:

| Check | Result |
|---|---|
| `.Config.Image` | `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` — equals `IMAGE_PIN_L0` exactly |
| Compose `seedsyncarr-test` image line | `image: ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` — equals `IMAGE_PIN_L0` |
| `.sonarr.sonarr_url` | `http://sonarr-v5:8989` — equals `SONARR_URL_L0` |
| `GET /server/status` | `200` |
| Production fingerprint (`prod-final.txt`) vs `prod-before.txt` | byte-identical, `diff` empty |

### Production unchanged (re-check)

`prod-before.txt`, `prod-after.txt` (during the check) and `prod-final.txt` (fresh session, after the final restore) are all byte-identical:

```
2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 sha256:5b801f8397d68bf9bb35eed0d4f882cae2ab24100e4d28be4006f8f028e0ef62 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e running 2026-10-23T07:04:18.591254939Z
```

`StartedAt` (`2026-10-23T07:04:18.591254939Z`) matches the value recorded in `123-LIFE-EVIDENCE.md` and 125-03's "### Production unchanged" exactly — no drift across the whole gap-closure cycle. Production `seedsyncarr` was never started, stopped, recreated or reconfigured anywhere in this plan; the only command ever run against it was the single permitted read-only `docker inspect` fingerprint.

## Phase 125 verdict (after gap closure)

Rows below update or add to the original "## Phase 125 verdict" table above. Any row from the original verdict not repeated here (SC1, SC3, D-01, D-02, D-03, D-04, D-05) stands unchanged — the 125-04 guard rewrite did not touch the allowed-range classification, the loopback-port rule, mixed-resolution handling, redirect handling or the relaxation-scope test, confirmed by the 125-05 whole-suite baseline match (24-line environmental baseline, identical before and after 125-04) and the full `TestLanRelaxationScope`/`TestValidateUrl` suites passing unchanged at the 125-04 GREEN commit.

| Item | Decision / criterion | Evidence | Verdict |
|------|----------------------|----------|---------|
| LAN-01 | Container-name/private-range Test Connection still succeeds on the hardened build | Live: this plan's `POSITIVE PASS` (`success=true version=5.0.0.2800`) against `http://sonarr-v5:8989` on `DEV_PIN_R2`. Unit: 125-04 GREEN leaves all 125-01 allow-case tests passing (201 passed/87 subtests) | PASS |
| LAN-02 | Cloud-metadata/link-local still refused with the same message | Live: this plan's `NEGATIVE PASS` against `http://169.254.169.254` with the exact locked string | PASS |
| SC2 (metadata/link-local, loopback-wrong-port, redirects stay rejected) | Same outcome preserved after the guard rewrite | Live `NEGATIVE PASS` (this plan) plus 125-04 unit `test_rejects_aws_ipv6_metadata`, `test_rejects_alibaba_metadata`(+ipv6-mapped); loopback-port and redirect tests unchanged from 125-01 | PASS |
| SC4 (release notes note the behaviour change) | 1.8.0 draft notes describe the behaviour accurately | 125-05 Task 1 commit `18de612` rewrote `CHANGELOG.md` `## [Unreleased]` to match post-125-04 behavior | PASS |
| D-06 (scope) | Only `_validate_url`/`_test_arr_connection` changed by the gap-closure fix | 125-05 Gate 4 rerun over 125-04: exactly 3 files in the `src/` diff since `BASE`, `controller/` untouched, one definition/one call site of `_validate_url` | PASS |
| D-07 (wording; key never echoed) | Specific refusal reasons for the new cases; no new logger/key lines | 125-05 Gate 5 rerun: 0 new `logger.`/`api_key`/`X-Api-Key` lines in `b6d0902`; live `NEGATIVE_CR01` shows the new `BAD_CHARS_MSG` text end to end | PASS |
| D-08 (test-first proof) | RED-before-GREEN for the gap-closure fix; full suite + whole-tree ruff pass | 125-05 Gates 1–3 rerun over 125-04: suite matches the fixed 24-line baseline, whole-tree `ruff check src/python/` clean, `test(125-04)` (`730d3c7`) precedes `fix(125-04)` (`b6d0902`) | PASS |
| D-09 (live check) | The hardened build passes the live re-check; sandbox restored and verified; production read-only | This plan: `CHECK_STATUS=PASS`; `teardown.sh --final` ends `SANDBOX_RESTORED ok`; fresh-session check confirms `IMAGE_PIN_L0`, compose line, `sonarr_url`, `/server/status` 200; production fingerprint byte-identical across before/after/final, matching 125-03's `StartedAt` with zero drift | PASS |
| D-10 (release notes) | 1.8.0 draft CHANGELOG entry records the behaviour change | 125-02 Task 1 commit `3022056` (original entry), kept accurate by 125-05's rewrite | PASS |
| D-11 (parser-differential bypass fixed) | URLs the guard and `requests`/`urllib3` would interpret differently are refused; exact-string validation | Unit: 125-04 `TestParserDifferentialGuard` (19 tests) plus handler-level backslash tests, RED (`730d3c7`) → GREEN (`b6d0902`), 201 passed/87 subtests. Live: this plan's `NEGATIVE_CR01 PASS` against the exact CR-01-style backslash payload `http://169.254.169.254\@sonarr-v5:8989`, refused with the exact locked message, with the real `requests`/`urllib3` stack and real Docker DNS | PASS |
| D-12 (metadata addresses inside allowed ranges refused) | `fd00:ec2::254` and `100.100.100.200` refused; ULA/CGNAT neighbors stay allowed | Unit only: 125-04 `test_rejects_aws_ipv6_metadata`, `test_rejects_alibaba_metadata`(+ipv6-mapped), `test_accepts_fd00_ec2_neighbor`/`test_accepts_tailscale_magicdns`/`test_accepts_alibaba_metadata_neighbor` | PASS (unit-proven; not separately exercised live in this plan — neither address is the sandbox's Sonarr target) |
| D-13 (release notes disclose the pre-upgrade risk) | Plain-language note that 1.7.6 and earlier could be tricked by a crafted URL, and upgrading fixes it | 125-05 `CHANGELOG.md` `### Security` section leads with this exact disclosure, commit `18de612` | PASS |
| D-14 (non-ASCII hosts and `?`/`#` refused; `xn--` accepted) | International host names must use the `xn--` form; query/fragment refused | Unit: 125-04 `TestParserDifferentialGuard::test_rejects_non_ascii_host`, `test_rejects_query_string`, `test_rejects_fragment`, `test_accepts_punycode_host` (lock). CHANGELOG: 125-05's Changed-section bullet states the `xn--` guidance | PASS |

### Review-closure table (125-REVIEW.md findings)

| Finding | Issue | Closure evidence | Verdict |
|---------|-------|-------------------|---------|
| CR-01 | Parser mismatch (`urlparse` vs `urllib3.util.parse_url`) let a backslash payload bypass the loopback-port gate and the metadata block | 125-04 RED (`730d3c7`) → GREEN (`b6d0902`): character allow-list before any parser, parser-agreement check, single normalized URL reused for validation and the request. 125-05 Gate rerun confirms the fix is scoped to `config.py` with 0 new log/key lines. Live: this plan's `NEGATIVE_CR01 PASS` against the real payload with the real `requests`/`urllib3` stack | CLOSED |
| WR-01 | AWS IPv6 instance-metadata `fd00:ec2::254` allowed via the new `fc00::/7` range | 125-04 `_METADATA_NETWORKS` check (`test_rejects_aws_ipv6_metadata`); CHANGELOG 125-05 note | CLOSED (unit-proven) |
| WR-02 | Malformed hostnames raised `UnicodeError`, escaping as an HTTP 500 instead of the JSON refusal contract | 125-04 `test_sonarr_malformed_hostname_returns_json_error` plus `TestParserDifferentialGuard` consecutive-dots/bare-dot/64-char-label tests; `UnicodeError`/`ValueError` now caught and mapped to a normal JSON error | CLOSED |
| WR-03 | Refusal of IPv6-transition forms depended on interpreter-version-specific `is_global`/`is_reserved` tables | 125-04 explicit `_REFUSED_NETWORKS` entries (6to4/Teredo/NAT64/SIIT) plus a `PropertyMock`-simulated-old-interpreter test proving refusal independent of interpreter tables; 5 real-table lock tests pass unchanged | CLOSED |
| IN-01 | Trailing whitespace: validated string differed from the fetched string | 125-04 single normalization point (`url = raw_url.strip().rstrip("/")`) reused for both `_validate_url` and `requests.get`; `test_sonarr_trims_whitespace_and_requests_exact_validated_url` | CLOSED |
| IN-02 | `TestLanRelaxationScope` brittle (scanned `.venv`/`build`/`dist`; narrow import regex) | 125-04 widened directory exclusions and the outbound-HTTP-module regex | CLOSED |
| IN-03 | CHANGELOG overstated the guard's behaviour before CR-01/WR-01 were fixed | 125-05 rewrote the `[Unreleased]` entry to match post-125-04 behaviour (D-10 through D-14), commit `18de612` | CLOSED |

**Phase 125 live re-check: PASSED**

The sandbox is restored to `IMAGE_PIN_L0` (`ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`) and verified in a fresh, independent session. Production `seedsyncarr` was never touched beyond the single permitted read-only fingerprint and is byte-identical before, during and after this plan (and unchanged since 125-03). PR #140 remains open and draft (`isDraft: true`, `state: OPEN`, `headRefOid: 18de612d...`); nothing was merged.

## Owner review (gap closure, Task 3)

Owner reply, verbatim, 2026-10-28: "approved"

The owner reviewed, before replying: a positive check against `http://sonarr-v5:8989` succeeding with Sonarr `5.0.0.2800`; `http://169.254.169.254` refused with the link-local/cloud-metadata message; the CR-01 payload `http://169.254.169.254\@sonarr-v5:8989` refused with the invalid-character message; the sandbox restored to the 1.7.6 pin and original Sonarr URL; production untouched; PR #140 still draft. The orchestrator independently re-verified in a separate `ssh nas` session: `seedsyncarr-test` and `seedsyncarr` both report `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...`, and production `StartedAt` `2026-10-23T07:04:18.591254939Z` is unchanged. The owner was told one CHANGELOG `### Security` bullet names the backslash character and did not ask to change it.

**Phase 125: gap-closure owner-approved.**
