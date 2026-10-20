---
phase: 120-sonarr-5-compatibility
plan: 01
subsystem: testing
tags: [sonarr5, fixtures, hygiene, test-scaffold]
requires: []
provides:
  - "src/python/tests/fixtures/sonarr5/ (manifest + 5 placeholder fixtures)"
  - "tests.unittests.test_sonarr5.fixtures loader (FIXTURE_DIR, fixture_bytes, fixture_json, manifest, manifest_entry, tested_version, queue_target_download_id)"
  - "Fixture hygiene CI guard with a visible live-source skip gate"
affects: [120-03, 120-04, 120-06]
tech-stack:
  added: []
  patterns: ["path-relative read-only fixture loader", "rule-name-only secret scanner", "skipIf gate tied to manifest source field"]
key-files:
  created:
    - src/python/tests/fixtures/sonarr5/manifest.json
    - src/python/tests/fixtures/sonarr5/system_status.json
    - src/python/tests/fixtures/sonarr5/queue_details_incomplete.json
    - src/python/tests/fixtures/sonarr5/queue_details_complete.json
    - src/python/tests/fixtures/sonarr5/webhook_test.json
    - src/python/tests/fixtures/sonarr5/webhook_download.json
    - src/python/tests/unittests/test_sonarr5/__init__.py
    - src/python/tests/unittests/test_sonarr5/fixtures.py
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py
  modified: []
decisions:
  - "Test modules must import tested_version under an alias (e.g. recorded_version): pytest otherwise collects the imported helper as a test function"
  - "Placeholder target downloadId is 39 zeros + '1'; the unrelated queue record uses 39 zeros + '2'"
metrics:
  duration: "~15 min"
  completed: 2026-10-20
  tasks: 2
  files: 9
---

# Phase 120 Plan 01: Sonarr 5 Fixture Scaffold and Hygiene Guard Summary

Five placeholder Sonarr 5.0.0.2701 fixtures (system/status, queue/details incomplete and complete, Test and Download webhooks) plus a manifest and a stdlib read-only loader. A CI hygiene guard scans every fixture for API-key-shaped tokens, private IPv4 addresses, personal paths, real-TLD hostnames, emails and API-key headers. It reports only the rule names, never the matched values. The strict "all fixtures are live captures" check stays visibly skipped until Plan 06.

## What was built

- **Fixtures** (`src/python/tests/fixtures/sonarr5/`): built by hand from the key sets in RESEARCH. All values are placeholders: `/home/user/v5test`, `/data/torrents`, `/data/media/tv`, `images.example.invalid`, `Indexer (Prowlarr)` and `Deluge`. The target download (`Placeholder.Show.S01E01.1080p.WEB.h264-GROUP`, id `000…001`) shows `downloading` with a positive `sizeleft` in the incomplete queue file. It shows `completed` with `sizeleft` 0 and `importPending` in the complete file. Both files also carry one unrelated completed record. Queue keys use lowercase `sizeleft`/`timeleft`, as Sonarr 5 emits them. `webhook_download.json` carries the same `downloadId` and a `/data/torrents/...` `sourcePath`.
- **manifest.json**: `schema: 1`, `queue_target_download_id`, and one entry per fixture. Every entry has `source: "placeholder"` and `sonarr_version: "5.0.0.2701"`.
- **fixtures.py**: resolves the fixture directory as `Path(__file__).resolve().parents[2] / "fixtures" / "sonarr5"` and has 6 helpers. `manifest_entry` raises `KeyError` when a file has no entry or more than one. `tested_version` reads the build from the system_status manifest entry.
- **test_sonarr5_fixture_hygiene.py** (277 lines, 25 tests):
  - `TestScanner`: inline dirty and clean strings for every rule.
  - `TestFixtureFiles`: scans every fixture and checks it parses as JSON.
  - `TestManifest`: completeness, the field rules, a single 5.x build matching system_status, the same download appearing in both queue states, and the webhook `downloadId`.
  - `TestLiveSource`: a single `skipIf` gate whose reason names Phase 120 Plan 06.

## Verification (observed)

- Task 1 scaffold script (the plan's `<verify>` assertions, run from a scratch file): printed `scaffold OK 5`.
- Task 1 greps:
  - `"source": "placeholder"` appears 5 times.
  - `"sizeleft"` appears 2 times and `"sizeLeft"` 0 times.
  - The personal-data grep found nothing (rc 1).
  - `parents[2]` matches once.
  - There are 6 `def`s.
  - The directory holds exactly the 6 intended files.
- RED: 13 failed, 18 passed, 1 skipped (scanner stubbed to return `[]`). Committed as `2d2fe88`.
- GREEN: `pytest tests/unittests/test_sonarr5 -q -rs -p no:cacheprovider` gave 24 passed, 1 skipped, 53 subtests passed. The skip reason contains "Phase 120 Plan 06 must replace placeholder fixtures with live captures".
- Task 2 greps: `def test_` 25, `skipIf` 1, `5\.0\.0\.2701` 0.
- Mutation/scanner script printed `scanner OK`.
- `ruff check src/python/` (whole tree): All checks passed.
- Caveat: pytest ran from the pipx-installed pytest, because the worktree's fresh poetry venv has no dev dependencies. It warned that `timeout`, `timeout_func_only` and `cache_dir` are unknown config options (pytest-timeout is absent). The tests are stdlib-only, so the results stand, but the full Docker CI suite was not run here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pytest collected the imported `tested_version` helper as a test**
- **Found during:** Task 2 (first RED run, which showed a `PytestReturnNotNoneWarning` on `tested_version`)
- **Issue:** A module-level name starting with `test` that is imported into a test module gets collected by pytest as a test function.
- **Fix:** Import it as `tested_version as recorded_version`. Plans 03/04 should do the same, or import the module rather than the bare name.
- **Files modified:** src/python/tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py
- **Commit:** 2d2fe88

**2. [Rule 3 - Blocking] Lint hook rejected the RED commit**
- **Issue:** The commit hook runs ruff, and the stubbed scanner left `ipaddress` unused (F401).
- **Fix:** Left the import out of the RED commit and added it back with the implementation in GREEN.
- **Commit:** 2d2fe88 / 7600768

**3. [Plan adjustment] RED/GREEN done as separate commits rather than a temporary wrong assertion**
- The plan suggested going RED by asserting a wrong rule name temporarily. Instead, the RED commit has the full test suite with `_scan` stubbed to `[]` (13 failures), and GREEN implements the scanner. This keeps the TDD gate visible in git history.

## TDD Gate Compliance

- RED: `2d2fe88 test(120-01): add failing Sonarr 5 fixture hygiene guard`
- GREEN: `7600768 feat(120-01): implement Sonarr 5 fixture hygiene scanner`

## Known Stubs

- All five fixtures are intentional placeholders (`source: "placeholder"` in manifest.json). Plan 06 replaces them with sanitized live captures and removes the `skipIf` on `TestLiveSource.test_all_fixtures_are_live_captures`. Until then that test shows as 1 skipped.

## Threat Flags

None. Test-only files; no new production surface.

## Self-Check: PASSED

- All 9 created files exist (verified via `ls` and the scaffold script).
- Commits f2c2c9c, 2d2fe88, 7600768 present in `git log`.
