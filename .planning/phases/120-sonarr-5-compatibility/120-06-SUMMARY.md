---
phase: 120-sonarr-5-compatibility
plan: 06
status: complete
subsystem: fixtures-evidence-release-decision
tags: [sonarr5, sanitize, fixtures, evidence, release-decision]
requires:
  - phase: 120-03
    provides: SON5-01/02 CI tests over the fixture manifest
  - phase: 120-04
    provides: SON5-02 negatives and SON5-03 webhook CI tests
  - phase: 120-05
    provides: raw Sonarr 5.0.0.2701 captures on the NAS and the live SON5-01..03 results
provides:
  - Five sanitized live Sonarr 5.0.0.2701 fixtures plus manifest (all source live)
  - Strict fixture hygiene guard (no skip path)
  - 120-SON5-EVIDENCE.md with the SON5-05 decision "verified; no release needed", owner approved
affects: [milestone v1.7.7 close]
tech-stack:
  added: []
  patterns:
    - "Sanitize on the NAS, transfer only sanitized output (ssh cat), exact-secret count of sandbox-only values before commit"
key-files:
  created:
    - .planning/phases/120-sonarr-5-compatibility/120-SON5-EVIDENCE.md
  modified:
    - src/python/tests/fixtures/sonarr5/manifest.json
    - src/python/tests/fixtures/sonarr5/system_status.json
    - src/python/tests/fixtures/sonarr5/queue_details_incomplete.json
    - src/python/tests/fixtures/sonarr5/queue_details_complete.json
    - src/python/tests/fixtures/sonarr5/webhook_test.json
    - src/python/tests/fixtures/sonarr5/webhook_download.json
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md
key-decisions:
  - "SON5-05: verified; no release needed on Sonarr 5.0.0.2701 (owner approved 2026-10-20); no bump, tag or deploy; production stays 1.7.6"
  - "Container-name Test Connection failure is the pre-existing LAN guard (D-02, Reliability item 5), not a Sonarr 5 failure"
requirements-completed: [SON5-04, SON5-05]
duration: ~45 min (excluding the owner checkpoint wait)
completed: 2026-10-20
---

# Phase 120 Plan 06: Live fixtures, SON5 evidence and SON5-05 decision Summary

Sanitized live Sonarr 5.0.0.2701 captures replaced the placeholder fixtures. The hygiene guard is now strict, the
exact-secret count is 0 and CI is green. SON5-05 is decided "verified; no release needed", and the owner approved
that outcome.

## Accomplishments
- **Sandbox pre-flight (fresh session):** version 5.0.0.2701, 1 notification (`Seedsyncarr`), 0 sink containers,
  `sonarr_url=http://sonarr-v5:8989`, Deluge `downloadDirectory` matches L0, queue 0. Teardown was not needed.
- **Sanitized on the NAS.** The mapping has 14 keys: downloadId, 9 indexer names, the seedbox directories as a
  precaution, and the artwork host. Every sanitizer run printed `RESIDUAL=0` and exited 0. The checks printed
  `BASENAMES_PRESERVED ok` (4 path-bearing files), `STATUS_VERSION 5.0.0.2701 match` and `CHECKS ok`.
- **Exact-secret count:** `VALUES lines=19 expected=19`, `EXACT_SECRET_COUNT total=0 rc=1`. A raw-file control
  count found 6, so the values file does detect them. Only `/volume1/docker/v5test/` sources were read; no
  production config was read.
- **Fixtures and manifest committed.** All 5 entries are `source: live`, `5.0.0.2701`, captured 2026-10-20. The
  `skipIf` gate and the `_has_placeholders` helper are removed.
- **CI** on `6e0341f` (run 39498893798) was success. Python unit tests: 1944 passed, 2 unrelated skips.
  `test_all_fixtures_are_live_captures` PASSED. Lint (Python) succeeded, CodeQL succeeded.
- **Raw captures deleted.** All three `son5-capture-*` dirs were removed from the NAS after the push and green CI
  (`RAW_DIR_DELETED`, remaining=0).
- **Evidence record** `120-SON5-EVIDENCE.md` covers the builds verified, SON5-01..04 (live and CI), sandbox
  restoration, the decision matrix, follow-ups and the owner confirmation.

## Task Commits
1. **Task 1: live fixtures, strict guard** - `6e0341f` (test; pushed to origin/main)
2. **Task 2: evidence and decision** - `5397478` (docs)
3. **Task 3: owner confirmation recorded, SON5-05 ticked, SUMMARY** - this plan's final docs commit

## Verification (observed)
- `pytest tests/unittests/test_sonarr5`: 49 passed, 0 skipped, 0 failed (58 subtests).
- `ruff check src/python/`: All checks passed.
- Full local run of `tests/unittests tests/integration`: 1823 passed, 62 skipped, 21 failed, 43 errors. Every
  failure and error is host-only:
  - sshcp, scanner_process, extract_process and test_scanner latin-1. These match the host baseline recorded
    earlier for `3618be6`, which was not rerun here.
  - 40 lftp integration errors from `getgrnam ... 'testgroup'`, which needs the Docker test environment. The
    lftp code is unchanged since the baseline.
  - CI, which runs in Docker, was green.
- Task 1 verify: the manifest has 0 placeholder and 5 live entries, `skipIf` count is 0, ruff is clean, and the NAS
  `son5-capture-*` count is 0. The prod-config grep on the plan printed 0.
- Task 2 verify: the evidence sections, decision line, `EXACT_SECRET_COUNT`, `RAW_DIR_DELETED` and the D-09 and
  Reliability lines are all present. The 32-hex / 100.x / `/home/<real>` grep printed 0. STATE `last_updated` was
  within 24 h. `120-SON5-05-RELEASE-NEEDED.md` was not created (Outcome A).

## Deviations from Plan

1. **[Rule 1 - Bug, test only] Placeholder-specific queue test assumption** (Task 1, classification (i)).
   - Issue: `_unrelated_record` expected a second, unrelated record in `queue_details_complete.json`. The live
     sandbox queue held only the tracked download, so that record does not exist.
   - Fix: the test now derives the unrelated completed record from the captured target record, with a different
     downloadId and root.
   - No production code changed. File: `test_sonarr5_queue.py`. Commit `6e0341f`.
2. **Path prefix expectations.** The plan expected seedbox `outputPath` prefixes to map to `/home/user/v5test`.
   Sonarr's remote path mapping already reports the container-local `/data/torrents/<root>`, so no seedbox path
   was present. The seedbox-directory keys stayed in the mapping as a precaution (they matched nothing), and the
   path check accepts `/data/torrents/`.
3. **`system_status.json` source.** It comes from the attempt-2 L1 capture dir (`-151815`), the plan's named L1
   artifact. It is the same build as the attempt-3 files, so D-08 holds.
4. **Exact-secret sources.** The seedbox user and host come from the sandbox `settings.cfg` under
   `/volume1/docker/v5test/seedsyncarr/`, and the Deluge host from the sandbox Sonarr download client, so both
   stay inside sandbox scope. The plan allowed this.
5. **SON5-05 ticked only after owner approval.** Task 2 left SON5-05 `[ ]`, marked "decided, awaiting owner
   confirmation", instead of `[x]`. The owner rule says never invent completion. It was ticked in Task 3 after the
   owner replied "approved".
6. **STATE status wording.** The status line avoids the word "verified" while the plan was awaiting the owner.
   PLANNING-FORMAT treats "verified" as phase-finished.
7. **holdout_guard block.** One pytest/grep pipeline contained a `.*` token and hit the known false positive. I
   rewrote the command without bypassing the guard.

## Assumption Drift (advisory)
- **Found during Task 1.** Planned: raw queue and webhook captures contain seedbox home paths that need mapping.
  Actual: Sonarr 5 reported the remote-path-mapped `/data/torrents` paths. Why: the sandbox Sonarr has a remote
  path mapping for the Deluge seedbox.
- **Found during Task 1.** Planned: the live complete-queue snapshot contains an unrelated download. Actual: it
  holds a single record. Why: the sandbox queue had only the one approved grab.

## Owner confirmation
2026-10-20, relayed by the phase coordinator: "approved". The owner accepts SON5-05 "verified; no release needed"
on Sonarr 5.0.0.2701. Next: orchestrator verification and phase completion, then `/bm:complete-milestone`.

## Known Stubs
None.

## Self-Check: PASSED
Commits `6e0341f` and `5397478` exist. The 5 fixtures, the manifest and `120-SON5-EVIDENCE.md` exist. The NAS
capture-dir count is 0.
