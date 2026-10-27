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
