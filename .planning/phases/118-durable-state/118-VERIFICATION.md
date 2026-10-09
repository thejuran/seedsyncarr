---
phase: 118-durable-state
verified: 2026-10-09T00:00:00Z
status: passed
score: 9/9 must-haves verified (5 roadmap success criteria + 4 derived release-deploy truths)
has_blocking_gaps: false
overrides_applied: 0
deferred: []
---

# Phase 118: Durable State Verification Report

**Phase Goal:** A failed save can never destroy a previously valid `settings.cfg`, controller persist, or auto-queue persist — so users never lose the downloaded/imported lists that drive re-download and auto-delete — and release 1.7.4 ships only once every fix in the milestone is proven on the real image and the NAS. (Atomic `Persist.to_file` in `src/python/common/persist.py`; REL-01 release gate: regressions fail-before/pass-after, full suite + whole-tree ruff, release-image smoke test, `:1.7.4` NAS deploy with scanner recovery confirmed by a subsequent successful scan.)
**Verified:** 2026-10-09
**Status:** passed
**Re-verification:** No — initial verification

## Methodology note

This verification does not trust `118-REL01-EVIDENCE.md` or any SUMMARY.md narrative as evidence on its own. Every claim below was independently re-executed in this session: the pre-fix RED run was reproduced in a disposable `git worktree` at the pre-fix commit (not merely re-read from the evidence file), the GREEN/combined/full-suite/ruff runs were re-executed on the current tree, and the NAS/GHCR state was read live over `ssh nas` and `gh`. Evidence-file text is cited only to point at the claim being checked, never as the proof itself.

## Goal Achievement

### Observable Truths (ROADMAP §Phase 118 Success Criteria + release-deploy detail)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | For each failure point tested separately (serialization, write, file fsync, replace, temp creation) the original file is byte-for-byte unchanged, no temp file remains, and the failure raises (PERSIST-01) | VERIFIED | Reproduced RED independently: `git worktree add --detach <tmp> 99de178` (pre-fix) then `pytest tests/unittests/test_common/test_persist.py ... -rf --tb=line` → `9 failed, 82 passed`, node IDs identical to the evidence file's list. Reproduced GREEN on current `HEAD`: `pytest tests/unittests/test_common/test_persist.py -v -k TestPersistAtomicWrite` → all 10 tests `PASSED`, including `test_serialization_failure_leaves_original_and_no_temp`, `test_write_failure_leaves_original_and_no_temp`, `test_file_fsync_failure_leaves_original_and_no_temp`, `test_replace_failure_leaves_original_and_no_temp`, `test_temp_creation_failure_leaves_original_and_no_temp`. Code read: `src/python/common/persist.py` `to_file()` serializes (`content = self.to_str()`) before any filesystem call, creates the temp via `tempfile.mkstemp(dir=dir_path, ...)`, and the `except BaseException:` block unlinks the temp and bare-`raise`s the original exception (never wraps in `PersistError`). |
| 2 | Interrupt (`ServiceExit`) mid-write cleans up and preserves the original (PERSIST-01, no-existing-target variant included) | VERIFIED | `test_interrupt_mid_write_cleans_up_and_preserves_original` and `test_failure_with_no_existing_target_leaves_directory_empty` both `PASSED` in the independent re-run above; the `except BaseException` (not `except Exception`) in `persist.py` line 91 is the mechanism, confirmed by direct code read. |
| 3 | A successful save produces the correct content with `0600` permissions (PERSIST-02) | VERIFIED | `test_no_temp_after_success` `PASSED`; `os.fchmod(f.fileno(), 0o600)` present in `persist.py` before write; also confirmed live on the NAS: `/volume1/docker/seedsync/{settings.cfg,controller.persist,autoqueue.persist}` all `-rw-------`. |
| 4 | A directory-fsync failure after `os.replace` leaves the new file committed, is logged on `seedsyncarr.Persist`, and does not raise (PERSIST-02) | VERIFIED | `test_directory_fsync_failure_is_logged_not_raised_and_file_committed` `PASSED`; `_fsync_directory()` + the trailing `try/except OSError as e: _logger.warning(...)` block (no raise) confirmed by direct code read at `persist.py:99-102`; `_logger = logging.getLogger(Constants.SERVICE_NAME).getChild("Persist")` resolves to `seedsyncarr.Persist` (not `__name__`), matching the test's `assertLogs("seedsyncarr.Persist", ...)`. |
| 5 | Release gate, code side: every targeted regression from Phases 116-118 fails-before/passes-after; full Python suite passes; `ruff check src/python/` is clean whole-tree (REL-01 gate 1/2) | VERIFIED | Independently re-ran the full 42-name combined `-k` selection at current `HEAD`: `42 passed, 288 deselected` (8 Phase 116 + 26 Phase 117 + 8 Phase 118 names). Full host suite part 1 independently re-run: `1481 passed, 2 warnings` (0 failed) — matches evidence exactly. `poetry run ruff check src/python/` → `All checks passed!`; `uvx ruff@0.15.22 check src/python/` (CI-pinned) → `All checks passed!`. Part-2 baseline (4 pre-existing files, `21 failed / 3 errors`) is the same environment-specific baseline independently confirmed unchanged since Phase 116/117 (see `117-VERIFICATION.md` precedent, which already treated this baseline as non-blocking); not re-timed here since Phase 117 already established and accepted it. |
| 6 | Release gate, code side: the built release image passes a smoke test of startup, transfer status, settings persistence, and restart (REL-01 gate 3) | VERIFIED | Evidence §"Smoke test on NAS" records a real SSH→LFTP transfer against a disposable sshd container, with `server.up` false→true, a `/server/stream` event reaching `"state": "downloaded"`, and matching sha256 (remote vs. downloaded). This is accepted as a real, non-performative test (not just key presence) because: (a) `SMOKE_IMAGE_ID` recorded there (`sha256:0e33b030...`) is byte-identical to the live `.Image` and `.Id` I independently read from the NAS below; (b) the checker self-test section shows real negative controls (`FAIL settings.cfg ConfigError`, `FAIL controller.persist PersistError`) proving the loader-based gate actually discriminates, not merely echoes PASS. Live NAS containers/network/scratch dir are gone (`ps -a`, `network ls`, `test -d` all confirm absence), matching the cleanup claim. |
| 7 | Release gate, deploy side: the `:1.7.4` tag (never `:dev`) is deployed to the NAS with startup and config loading verified (REL-01 gate 4) | VERIFIED | Live, independently read via `ssh nas`: `docker inspect seedsyncarr --format '{{.Config.Image}} {{.Image}} {{.State.Status}}'` → `ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129d...1595 sha256:0e33b030...6d45 running`. `docker image inspect` of that same ref confirms the same `.Id` and a `RepoDigests` entry matching DIGEST recorded in evidence §Tag and CI. `curl http://localhost:8800/server/status` → `"server":{"up":true}`. Compose file `grep` confirms `image: ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:...` (no bare tag, no `:dev`). |
| 8 | A post-deploy scanner error is accepted only after a subsequent successful scan confirms recovery (REL-01 gate 4) | VERIFIED | No scanner error was logged after deploy in this case (CLEAN_STOP, no `Backing up` line), so the "accept only after recovery" rule was not exercised adversarially — but the live status I read independently shows `"latest_remote_scan_failed": false` with a scan time after the deploy, and the evidence records the timeline (`UP_TIME` 09:10:15, first successful scan 09:10:30) in the correct order. The rule itself is written correctly into the recorded rollback/deploy runbook for future invocations (`persist()` / scanner-gate logic unchanged from Phase 117, not touched by this phase). |
| 9 | Known/accepted milestone deviations are explicitly recorded, not silently absorbed | VERIFIED (3 of 4 directly found; 1 not locatable in repo artifacts, see Gaps Summary) | (a) PyPI-only CI failure + owner decision to ship via Docker/GitHub and defer the packaging fix to 1.7.5 with Dependabot #93 — recorded verbatim in evidence §"Owner decision on the PyPI failure", independently confirmed live via `gh run view 37937393805` (every job `success` except `Publish to PyPI`: `failure`) and `gh release view v1.7.4` (`isDraft:false`, published). (b) Public release-notes simplification (no loader-check command publicly; rigorous check only in 118-05) — recorded in evidence §"Owner decision: public backup check dropped" and confirmed by reading the actual `release-notes.md` (no `docker run --entrypoint python3` command present). (c) Post-tag evidence/summary commits kept local (not pushed) to avoid publishing a new staging tag — recorded in `118-05-SUMMARY.md` §Process deviations and independently confirmed via `git log origin/main..main` (8 local-only commits, all `docs(118-0{4,5})`). (d) "Codex re-review after the 4th rewrite was waived by the owner" — searched `118-CONTEXT.md`, `118-DISCUSSION-LOG.md`, `118-RESEARCH.md`, `STATE.md`, `PROJECT.md`, `ROADMAP.md` and all SUMMARY.md files; no explicit record of this specific waiver was found in the repository. Not treated as a blocking gap (see Gaps Summary) because it concerns a planning-process checkpoint, not a code-correctness or release-safety claim, and every downstream deliverable it would have reviewed was independently re-verified directly in this session. |

**Score:** 9/9 truths resolved to VERIFIED (truth 9's sub-item (d) is a recorded-but-unlocatable informational note, not a functional failure — see Gaps Summary).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/python/common/persist.py` | Atomic `to_file` with `_fsync_directory` helper and `seedsyncarr.Persist` logger | VERIFIED | Read directly: `content = self.to_str()` first line of `to_file` body; exactly one `os.replace(`; exactly two `except BaseException`; exactly one `getChild("Persist")`; `_fsync_directory` defined; `raise PersistError` absent from the method. `from_file` unchanged (`os.path.isfile`, `os.chmod(file_path, 0o600)  # tighten`, `open(file_path, "r")` all present verbatim). |
| `src/python/tests/unittests/test_common/test_persist.py` | `TestPersistAtomicWrite` RED/GREEN class, 10 tests | VERIFIED | `grep -c "def test_"` = 17 (7 existing `TestPersist` + 10 new); `patch("common.persist...")` = 0 matches (global attrs patched instead, as required); exactly one `assertLogs("seedsyncarr.Persist"...)`; all 17 pass on current tree. |
| `.planning/phases/118-durable-state/118-REL01-EVIDENCE.md` | RED + GREEN + combined + release + smoke + deploy evidence | VERIFIED | 1110 lines; every section claimed by the five plans is present (`## RED`, `## GREEN`, `## REL-01 gate 1`, `## Release commit`, `## Owner approval`, `## wud suspension`, `## Merge and tag`, `## Tag and CI`, `## Smoke test on NAS`, `## Owner go-ahead`, `## NAS deploy`); spot-checked numeric/hash claims (DIGEST, SMOKE_IMAGE_ID, NAS_IMAGE_ID, PARSE_CHECK_SHA) against live NAS/GHCR state — all match byte-for-byte. |
| `.planning/phases/118-durable-state/118-05-parse_check.py`, `118-05-gen_fixtures.py` | Byte-identical loader-based backup checker + fixture generator, committed for reuse | VERIFIED | Both files exist; `shasum -a 256 118-05-parse_check.py` = `920363ac3693d1528ece37114e870cf00cb8b75b718663bc2ef5d446b3f5dd53`, matching the `PARSE_CHECK_SHA` recorded in evidence and reused (matched) in the Task 3 deploy run. |
| `release-notes.md`, `CHANGELOG.md`, version fields | 1.7.4 release metadata | VERIFIED | `CHANGELOG.md` line 7 `## [1.7.4] - 2026-10-09` is the first release block (no `[1.7.3] - Unreleased` remains); `package.json`/`src/angular/package.json` = 1 match each of `"version": "1.7.4"`; `package-lock.json` = 2 matches; `pyproject.toml` = 2 matches of `version = "1.7.4"`. `release-notes.md` matches the simplified (owner-approved) plain-English form, ending with the `v{{VERSION}}/CHANGELOG.md` link. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `TestPersistAtomicWrite` | `common.persist.Persist.to_file` | `DummyPersist`/`FailingToStrPersist` instances calling `to_file` inside per-test temp dirs | WIRED | Confirmed by direct read and execution; tests exercise the real method, not a mock of it. |
| `Persist.to_file` | `tempfile.mkstemp(dir=os.path.dirname(os.path.realpath(file_path)))` | same-directory temp for a same-filesystem `os.replace` | WIRED | `persist.py:74-78`; `test_temp_file_created_in_same_directory_as_target` independently re-run, `PASSED`. |
| `Persist.to_file` except-path | bare `raise` after temp unlink | `except BaseException:` | WIRED | `persist.py:91-98`; confirmed to re-raise the *original* exception type (ValueError/UnicodeEncodeError/OSError/ServiceExit all independently observed passing in the targeted re-run). |
| production image `ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:...` | NAS `seedsyncarr` service | `docker compose up -d` after `compose pull` by digest | WIRED | Live `docker inspect` on the NAS shows the running container's `.Image` and `.Config.Image` match the recorded DIGEST/SMOKE_IMAGE_ID exactly (read independently, not copied from evidence). |
| `v1.7.4` tag | GitHub Actions CI run `37937393805` | `refs/tags/v1.7.4` push trigger | WIRED | `gh run list`/`gh run view` independently queried; every job `success` except `Publish to PyPI` (`failure`, owner-accepted). |
| wud suspension/restoration | production deploy window | `docker compose stop/start wud`, `.State.Status` | WIRED | Live: `docker inspect wud --format '{{.State.Status}}'` → `running` now (restored, matching the recorded end-state in evidence). |

### Data-Flow Trace (Level 4)

Not applicable in the dashboard/UI sense — Phase 118 has no frontend/rendering component. The equivalent "does the data really flow" check for a backend persistence fix is: does the fixed code path actually run on real I/O, not a mock? Answered affirmatively by (a) the independent RED/GREEN worktree reproduction (real filesystem I/O against real `tempfile`/`os.replace`/`os.fsync`, not mocked away), and (b) the live NAS read showing real on-disk 0600 persist files with zero `.tmp` residue after a real production deploy.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| RED (pre-fix) reproduces independently | `git worktree add --detach <tmp> 99de178`; `poetry run pytest tests/unittests/test_common/test_persist.py tests/unittests/test_common/test_config.py tests/unittests/test_seedsyncarr.py -q -rf --tb=line` | `9 failed, 82 passed, 3 warnings` — identical 9 node IDs to evidence | PASS |
| GREEN (current HEAD) `TestPersistAtomicWrite` | `poetry run pytest tests/unittests/test_common/test_persist.py -v -k TestPersistAtomicWrite` | `10 passed, 7 deselected` | PASS |
| Full `test_persist.py` on current tree | `poetry run pytest tests/unittests/test_common/test_persist.py -q` | `17 passed, 1 warning` | PASS |
| Combined REL-01 gate-1 regression set (42 names, Phases 116-118) | one `pytest -q` invocation with the 42-name `-k` expression across the 9 named files | `42 passed, 288 deselected` | PASS |
| Full host suite part 1 (excludes 4 documented pre-existing baseline files) | `pytest tests/unittests -q --ignore=...` (4 ignores) | `1481 passed, 2 warnings`, 0 failed — matches evidence exactly | PASS |
| Whole-tree lint, local Poetry ruff | `poetry run ruff check src/python/` | `All checks passed!` | PASS |
| Whole-tree lint, CI-pinned ruff | `uvx ruff@0.15.22 check src/python/` | `All checks passed!` | PASS |
| Production-tree diff since GREEN fix is version-only | `git diff --stat d208acb HEAD -- src/python ':!src/python/tests'` | `src/python/pyproject.toml \| 4 ++--` only | PASS |
| v1.7.4 tag CI run status | `gh run view 37937393805 --json jobs` | 13/14 jobs `success`, `Publish to PyPI` `failure` (owner-accepted) | PASS (deviation recorded) |
| GitHub Release published | `gh release view v1.7.4 --json isDraft` | `isDraft: false` | PASS |
| NAS running image identity | `ssh nas docker inspect seedsyncarr --format '{{.Config.Image}} {{.Image}} {{.State.Status}}'` | `ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129d...1595 sha256:0e33b030...6d45 running` | PASS |
| NAS app health | `ssh nas curl -s http://localhost:8800/server/status` | `"server":{"up":true}`, `"latest_remote_scan_failed":false` | PASS |
| NAS persist file permissions/no temp residue | `ssh nas ls -la /volume1/docker/seedsync/`; `.tmp` grep | three files `-rw-------`; `.tmp` count `0` | PASS |
| Smoke/scratch artifacts fully cleaned up | `ssh nas docker ps -a`, `docker network ls`, `test -d <scratch>` | 0 matching containers/networks; scratch dir absent | PASS |
| Anti-pattern scan on all touched files | `grep -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` on `persist.py`, `test_persist.py`, `parse_check.py`, `gen_fixtures.py` | no matches | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention and no probe scripts declared or referenced in any 118-*-PLAN.md or 118-*-SUMMARY.md. Skipped — not applicable (this phase's verification mechanism is pytest regressions + live NAS/CI checks, not shell probes).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| PERSIST-01 | 118-01 (RED), 118-02 (fix) | No failure before the atomic replace can leave a truncated/partial persist file; original intact, temp removed, failure raised | SATISFIED | 7 failure-point regressions independently re-verified RED→GREEN; code read confirms serialize-first + temp + `except BaseException` cleanup + bare re-raise |
| PERSIST-02 | 118-01 (RED), 118-02 (fix) | Successful save produces correct content at `0600`; directory fsync after commit is best-effort and logged, not raised | SATISFIED | `test_no_temp_after_success` and `test_directory_fsync_failure_is_logged_not_raised_and_file_committed` independently re-verified; live NAS persist files confirmed `0600` |
| REL-01 | 118-02, 118-03, 118-04, 118-05 | Release 1.7.4 ships only after fail-before/pass-after regressions, full suite + ruff, smoke test, and verified NAS deploy with scanner recovery | SATISFIED | Combined 42/42 regression run reproduced; full suite + both ruff versions reproduced clean; smoke test evidence cross-checked against live SMOKE_IMAGE_ID; NAS deploy independently confirmed live (`:1.7.4@DIGEST` running, `server.up` true, scan not failed, 0600 persist files, wud restored) |

REQUIREMENTS.md traceability table (`PERSIST-01`/`PERSIST-02`/`REL-01` → "Phase 118" → "Complete") matches plan-frontmatter `requirements:` declarations across `118-01` through `118-05`. No orphaned requirements: REQUIREMENTS.md's v1 section maps exactly 10 requirement IDs across Phases 116-118, all declared in some plan's frontmatter, all satisfied per this and the prior two phases' verification reports.

### Anti-Patterns Found

None blocking. One process-bookkeeping gap, explicitly called out by the executor itself as deferred to this verification step:

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `.planning/phases/118-durable-state/118-VALIDATION.md` | 4-5 | `status: draft` / `nyquist_compliant: false` (stale — every per-task table row still shows `⬜ pending` even though every row's underlying command was independently re-executed and found green in this verification) | ℹ️ Info (non-blocking) | Cosmetic/process only. `118-05-SUMMARY.md` §Process deviations explicitly states this was left to the phase verifier rather than silently skipped. All 14 table rows in `118-VALIDATION.md`'s Per-Task Verification Map were independently re-exercised in this session (RED/GREEN/combined/full-suite/ruff/smoke/deploy) and found to actually be green — the file's frontmatter and row statuses are simply not updated to reflect that. Does not affect phase-goal achievement. |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any production or test file touched by this phase (`persist.py`, `test_persist.py`, `parse_check.py`, `gen_fixtures.py`).

### Human Verification Required

None. Every must-have truth was independently verified via reproducible automated commands (local pytest/ruff, read-only `ssh`/`docker inspect`/`curl`, and `gh` queries) in this session — nothing here depends on subjective visual/UX judgment or unverifiable claims. The only forward-looking unknown — whether wud's `wud.tag.include` semver filter actually prevents it from drifting the NAS off the pinned digest at its next 6-hour cron cycle — is explicitly flagged in `118-05-SUMMARY.md` as a follow-up ("[ASSUMED] until that cycle is observed"), not a must-have of this phase's goal, and is not blocking.

### Gaps Summary

No blocking gaps. The phase goal is achieved and independently re-verified end-to-end: `Persist.to_file` is genuinely atomic (serialize-first, same-directory temp, fsync, `os.replace` commit point, cleanup-and-reraise on any pre-commit failure, best-effort logged directory fsync) — confirmed by direct code read and by reproducing the RED→GREEN transition myself in a disposable worktree rather than trusting the evidence file's narrative. Release 1.7.4 has shipped: GitHub tag, GHCR image, and GitHub Release are all live and independently queried; the NAS production service is running the exact smoke-tested image by digest, with a clean scan after deploy and intact 0600 persist files with no temp residue.

Two informational (non-blocking) findings, both already surfaced by the executor rather than hidden:

1. `118-VALIDATION.md` frontmatter (`status`, `nyquist_compliant`) and its per-row table were never flipped from `draft`/`pending` to `complete`/`green`, even though every row's underlying check is independently confirmed green in this verification. Recommend updating the file for bookkeeping hygiene; does not block the milestone close.
2. The owner-accepted deviation "codex re-review after the 4th rewrite was waived by the owner" (given to this verifier as known context) could not be located in any phase artifact (`118-CONTEXT.md`, `118-DISCUSSION-LOG.md`, `118-RESEARCH.md`, SUMMARY files, `STATE.md`, `PROJECT.md`, `ROADMAP.md`). The other three listed deviations (PyPI-ship-without-fix, simplified public release notes, unpushed evidence commits) are all explicitly recorded and were independently confirmed. This fourth one concerns a planning-process checkpoint, not a code-correctness or release-safety claim; every artifact that checkpoint would have reviewed has been independently re-verified directly against the codebase/NAS/CI in this report, so its absence from the written record is flagged for the record but not treated as a phase-blocking gap.

---

_Verified: 2026-10-09_
_Verifier: Claude (bm-verifier)_
