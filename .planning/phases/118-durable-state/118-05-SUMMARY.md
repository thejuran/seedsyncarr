---
phase: 118-durable-state
plan: 05
subsystem: release
tags: [release, smoke-test, nas-deploy, docker-compose, wud, scanner-recovery]
requires:
  - phase: 118-durable-state
    provides: "118-04 published :1.7.4 (DIGEST sha256:682d129d…1595, NAS_IMAGE_ID sha256:0e33b030…6d45), wud stopped"
provides:
  - "REL-01 gate 3: smoke PASS on :1.7.4@DIGEST with a real LFTP transfer (sha256 match) and SMOKE_IMAGE_ID == NAS_IMAGE_ID"
  - "Proven read-only backup checker 118-05-parse_check.py (PARSE_CHECK_SHA 920363ac…dd53, SELFTEST_OK on :357 and :1.7.4)"
  - "REL-01 gate 4: NAS production on ghcr.io/thejuran/seedsyncarr:1.7.4@sha256:682d129d…1595, running .Image == SMOKE_IMAGE_ID"
  - "Pre-upgrade backups *.pre-1.7.4-20261009-0908 on the NAS with recorded sha256 and an ordered rollback runbook"
  - "wud restored (healthy) with wud.tag.include semver filter; compose digest pin kept"
affects: [milestone v1.7.4 close, 1.7.5 follow-up]
tech-stack:
  added: []
  patterns:
    - "Loader-level backup gate: app's own from_str loaders in a --read-only, --network none, --cap-drop ALL, --user <file owner> one-shot container"
    - "tag@digest compose pin with pre-stop .Id match against the smoke-tested image"
key-files:
  created:
    - .planning/phases/118-durable-state/118-05-parse_check.py
    - .planning/phases/118-durable-state/118-05-gen_fixtures.py
    - .planning/phases/118-durable-state/118-05-SUMMARY.md
  modified:
    - .planning/phases/118-durable-state/118-REL01-EVIDENCE.md
decisions:
  - "Owner go-ahead 2026-10-09: \"deploy keep pin\"; item (f) = keep the @sha256 digest pin in compose after wud restarts"
  - "Stop classification uses exit code, duration vs 10 s grace and OOMKilled; the known ScannerProcessDiedError shutdown traceback (present on :357 since 2026-09) is recorded separately"
  - "Backup checker runs with --user 1026:100: under --cap-drop ALL, container root cannot read 0600 files owned by uid 1026"
  - "wud.tag.include written as ^\\d+\\.\\d+\\.\\d+$$ in compose (the $$ escape); the effective container label is ^\\d+\\.\\d+\\.\\d+$"
metrics:
  duration: "~19 min wall clock (smoke start 08:54, wud restored 09:11 NAS time) plus the checkpoint wait"
  completed: 2026-10-09
  tasks: 3
  files: 4
requirements: [REL-01]
---

# Phase 118 Plan 05: Smoke test and NAS deploy of 1.7.4 Summary

**The published `:1.7.4@sha256:682d129d…` image passed a scratch smoke test on the NAS. The test used a real SSH-to-LFTP transfer and checked the file's checksum. The same platform image (`sha256:0e33b030…`) now runs production, after a clean 7-second stop and backups verified by the app's own loaders in both images. Downtime was 79 s, the first remote scan after the deploy succeeded 15 s after start, and wud was restored last with the semver filter and the digest pin kept.**

## Tasks

| # | Task | Result | Commit |
|---|------|--------|--------|
| 1 | Smoke test on the NAS (gate 3) plus the checker self-test | All five sub-verdicts PASS: startup, transfer, settings persistence, restart, checker self-test. Scratch containers, network and dirs removed. wud still `exited` and production unchanged at the end | `5faf07f` |
| 2 | Owner go-ahead checkpoint | Reply was "deploy keep pin". Recorded in evidence | `7bf85da` |
| 3 | Deploy to the NAS (gate 4) and restore wud | Production checks and wud restore below | `8367cdc` |

Task 3 detail:
- **Pre-stop checks:** PRE_STOP_ID_MATCH, then STOP_CLASS CLEAN_STOP, then COPIES_OK.
- **Loader checks:** PARSE_OK with `EXIT=0` in both `:357` and `:1.7.4`. `AutoDelete.enabled=True` was recorded.
- **After start:** IMAGE_ID_MATCH. No `Backing up` line and no traceback. The scan gate passed at 09:10:30. Persist files are 0600 with 0 `.tmp`.
- **wud:** restored `running`/`healthy` at 09:10:57.

## Observed verification

- **Task 1 verify (automated):** every grep matched. The section header is at line 490, with `smoke-test.invalid` ×4, `"state": "downloaded"` ×2, `"up": true` ×2, a `SMOKE_IMAGE_ID=` line, `SELFTEST_OK`, a `PARSE_CHECK_SHA=` line and `FAIL settings.cfg ConfigError`. The NAS smoke container count is `0`.
- **Task 2 verify:** the section header count is 1.
- **Task 3 verify (automated):** printed `DEPLOY_OK`. This covered:
  - live `:1.7.4@sha256:… running`, with `.Image` equal to SMOKE_IMAGE_ID;
  - the PRE_STOP_ID_MATCH, IMAGE_ID_MATCH and STOP_CLASS lines;
  - `latest_remote_scan_failed: false` live;
  - `.tmp` count 0;
  - wud `running`;
  - the NAS deploy section and WUD_START_TIME.
- **Absolute docker path check:** the grep over the evidence `## NAS deploy` section found 0 violations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Checker could not read 0600 files under `--cap-drop ALL`**
- **Found during:** Task 1 step 8b, the real-file run.
- **Issue:** Container root without `CAP_DAC_OVERRIDE` hit `PermissionError` on uid-1026 `-rw-------` files. The checker failed closed, which is correct. Production files have the same owner and mode, so the deploy would have hit the same error.
- **Fix:** Added `--user 1026:100` and re-ran the entire self-test (good, bad, mixed, cross and real) with the final flags. Task 3 used the identical flags. The script itself is unchanged, and PARSE_CHECK_SHA matched.
- **Commit:** `5faf07f`

**2. [Rule 3 - Blocking] Disposable sshd took longer than the 120 s readiness poll**
- **Found during:** Task 1 step 2.
- **Issue:** apt install on the NAS took about 4 minutes, so the first script exited, and its password variable went with it.
- **Fix:** A resume script generated a fresh password on the NAS and applied it via stdin with `docker exec -i … chpasswd`, so it never appeared in argv or output. Steps 3-4 then ran in that same session.
- **Detail:** The remote password went to `docker run` through a 0600 `--env-file` rather than `-e SMOKE_PW=…`, keeping it off the command line. The env file was deleted immediately.

**3. [Rule 3] Checker and fixture generator committed into the phase dir**
- **What:** `118-05-parse_check.py` and `118-05-gen_fixtures.py` were committed so Task 3, or any future rollback, can use the byte-identical proven script. Previously they existed only in a session scratchpad.

**4. Stop classification of the known shutdown traceback (orchestrator instruction)**
- **Plan rule:** read literally, any traceback means FORCED_STOP.
- **What was done:** Production's stop was exit 0, 7 s and not OOM-killed, ending with `Exited successfully`. It was classified CLEAN_STOP. The pre-existing `ScannerProcessDiedError` shutdown race was recorded separately. The loader check, which is mandatory either way, passed.

**5. Item (d) label escape**
- **What:** The label is written `$$` in compose so that compose interpolation yields a literal `$`.
- **Verified:** on the recreated container, the label reads `^\d+\.\d+\.\d+$`.

### Process deviations

- **Evidence commits not pushed.** The plan's Task 3 ends with `git push origin main`. Per the orchestrator, `5faf07f`, `7bf85da`, `8367cdc` and this summary commit stay local, because every push to main publishes a staging image.
- **`118-VALIDATION.md` not updated.** `status: complete` / `nyquist_compliant: true` were not set, because the per-row statuses for 118-01..03 were not re-exercised in this plan. That is left to the phase verifier.

## Assumption Drift (advisory)

- **Found during:** Task 3 step 8. **Planned:** observe wud's handling of the digest-pinned service at its first watch cycle. **Actual:** that cycle is the next `0 */6 * * *` cron, which falls after plan end, and there were 0 seedsyncarr mentions in the first minutes. **Why it matters:** the digest-pin behaviour is still [ASSUMED] and should be checked in the wud UI or logs after the next cron.

## Follow-ups

- Check the wud log after the next 6-hour cron and confirm seedsyncarr is left on the pinned digest.
- Auto-delete is ON in production (`AutoDelete.enabled=True` in the backup). Any rollback must run step (iii) of the recorded runbook.
- 1.7.5 backlog unchanged: PyPI packaging fix and Dependabot #93.

## Known Stubs

None.

## Threat Flags

None. The `--user 1026:100` flag narrows the checker's privileges and does not widen them.

## Self-Check: PASSED

- **Files:** all three exist.
  - `118-05-parse_check.py`: FOUND, sha `920363ac…dd53`
  - `118-05-gen_fixtures.py`: FOUND
  - `118-REL01-EVIDENCE.md`: contains `## Smoke test on NAS (Plan 118-05`, `## Owner go-ahead (Plan 118-05 Task 2)` and `## NAS deploy (Plan 118-05`
- **Commits:** `5faf07f`, `7bf85da` and `8367cdc` are all on `main`.
