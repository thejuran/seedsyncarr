---
phase: 122-safety-acceptance-and-logging-fixes
plan: 04
subsystem: infra
tags: [ghcr-digest, nas-sandbox, teardown, webhook-hmac, logging, one-pr-per-phase]

# Dependency graph
requires:
  - phase: 122-safety-acceptance-and-logging-fixes (plan 03)
    provides: "Draft PR #134 (one PR per phase, owner-approved), CI run #400 green, PR_HEAD_SHA 28942cc2b65c6c01929d154d8ffa99be4540a9f8"
provides:
  - "DEV_PIN digest for PR #134's staging image, cross-checked via two independent methods"
  - "seedsyncarr-test deployed to DEV_PIN; production untouched and fingerprint-verified identical"
  - "LOG-01 confirmed live on a running build (seedsyncarr.WebhookHandler logger reaches the app log)"
  - "122-teardown.sh (idempotent session/--final sandbox restore) and 122-webhook-post.sh (HMAC-signed synthetic webhook poster), committed for Plans 05-08 to reuse"
affects: ["122-05 (SAFE-01 import/credit scenarios)", "122-06/07 (extraction, restart)", "122-08 (SAFE-02 reconciliation, key rotation checkpoint)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Trap-protected NAS deploy: trap 'exit 130' INT TERM HUP set first, then trap '[ \"$OK\" = 1 ] || bash teardown.sh --final' EXIT INT TERM HUP, so any interruption restores the sandbox"
    - "HMAC secret piped into the sandbox container's own python3 over stdin (first line = key, rest = body) so it never appears in argv or script output"

key-files:
  created:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-webhook-post.sh
  modified:
    - .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md

key-decisions:
  - "Per the plan's <orchestrator_amendment>, Task 1/2 did not merge PR #134; the staging image ghcr.io/thejuran/seedsyncarr:400 (built from the PR's own CI run) was digest-pinned and deployed instead of a merge-commit :dev image"
  - "DEV_PIN resolved via two independent methods (docker buildx imagetools inspect, and the anonymous GHCR bearer-token registry lookup) that returned an identical digest, raising confidence beyond a single lookup"

patterns-established:
  - "Idempotent sandbox teardown (session and --final modes) with per-step read-back verification and a single SANDBOX_RESTORED ok/FAIL exit contract, extending the Phase 120 discipline with webhook_secret and synthetic-root restores"

requirements-completed: [LOG-01, LOG-02, SAFE-01]

# Metrics
duration: ~25min
completed: 2026-10-22
---

# Phase 122 Plan 04: Build Under Test, Sandbox Deploy, and Live LOG-01 Summary

**Resolved and deployed PR #134's digest-pinned CI staging image (`ghcr.io/thejuran/seedsyncarr@sha256:4463de...`) to `seedsyncarr-test` only, confirmed production untouched by fingerprint, and captured the first-ever live log line proving LOG-01 (`seedsyncarr.WebhookHandler` reaching the app log) on a running build.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-10-22T19:49:00Z (approx.)
- **Completed:** 2026-10-22T19:58:32Z
- **Tasks:** 3 of 3 completed (Task 1 was a recorded pass-through per the orchestrator amendment, no owner checkpoint needed this plan)
- **Files modified:** 3 (`122-SAFE01-EVIDENCE.md` created then appended; `122-teardown.sh`, `122-webhook-post.sh` created)

## Accomplishments
- Resolved PR #134's CI run #400 staging image digest by two independent methods (`docker buildx imagetools inspect` and the anonymous GHCR registry bearer-token lookup) — both returned `sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9`
- Confirmed the equivalence guard: no later push exists on the PR branch (`gh run list` shows exactly one completed run, headSha matches `gh pr view 134`'s current `headRefOid`)
- Deployed `DEV_PIN` to `seedsyncarr-test` under a trap-protected procedure (any interruption would auto-restore via `teardown.sh --final`); `.Config.Image` verified equal to `DEV_PIN` after deploy
- Confirmed production `seedsyncarr`'s container Id/image/StartedAt are byte-identical before and after — production was never named by any write command
- Captured the live LOG-01 line: `2026-10-22 15:57:15,115 - INFO - seedsyncarr.WebhookHandler (MainProcess/worker 1) - Sonarr webhook test event received` — first time this logger has ever emitted on a running build
- Committed `122-teardown.sh` (idempotent, session and `--final` modes, per-step read-back verification) and `122-webhook-post.sh` (HMAC-signed synthetic webhook poster, secret never in argv/output) for Plans 05-08 to reuse; both pass `bash -n` and `shellcheck` cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Owner go-ahead (superseded by orchestrator amendment)** - no commit (decision already recorded in `122-03-SUMMARY.md`; see below)
2. **Task 2: Resolve PR staging image digest, record evidence** - `54a1b56` (docs)
3. **Task 3: Teardown/webhook-post scripts, deploy DEV_PIN, prove LOG-01 live** - `8ba5a39` (test)

**Plan metadata:** (this commit, to follow)

## Files Created/Modified
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` - Build-under-test and Sandbox-deploy evidence sections (PR/digest resolution, original pin, deploy transcript, production-fingerprint comparison, live LOG-01 log line)
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh` - Idempotent sandbox restore (rate_limit, delay_seconds, synthetic `SSA122.*` roots, webhook_secret stop/edit/start, `--final` image-pin restore), single `SANDBOX_RESTORED ok`/`FAIL` exit contract
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-webhook-post.sh` - Builds and HMAC-SHA256-signs a synthetic Sonarr Download webhook body, computing the signature inside the sandbox container over stdin so the secret never touches argv or output

## Decisions Made
- Followed the plan's `<orchestrator_amendment>` exactly: no merge was performed; Task 1's owner decision ("one draft phase PR; live checks on its CI staging image; merge once at the end") was already recorded in `122-03-SUMMARY.md` and is simply carried forward here, not re-asked
- Task 2's digest lookup used both the local `docker buildx imagetools inspect` (available on this machine) and the anonymous GHCR bearer-token method from `122-RESEARCH.md`/`119-REL03-EVIDENCE.md` as a cross-check, rather than relying on a single method
- Used `jq` (confirmed present on the NAS host, matching `120-teardown.sh`'s existing convention) rather than `python3` for parsing sandbox `/server/config/get` JSON inside `122-teardown.sh`; `python3` is still used, per the plan's explicit instruction, for the in-container HMAC computation in `122-webhook-post.sh`

## Deviations from Plan

None requiring a fix. One environmental observation, not a deviation from this plan's required work:

- **Seedbox SSH unreachable (informational, not blocking this plan).** `ssh nyx.usbx.me` from the NAS returned `Connection refused` on port 22 (checked twice, a few seconds apart, after an initial `Permission denied` using the NAS's own default username rather than the seedbox's `jules1651`). This plan creates no synthetic material and `122-teardown.sh`'s seedbox-cleanup step only runs when `SYNTH_ROOTS` is non-empty (it is not, this session), so this did not block or degrade Task 3. It is recorded in the evidence file's "Known issue for Plans 05-08" section and flagged here because Plans 05-08 (SAFE-01 synthetic import/extraction scenarios) do require seedbox reachability — re-check connectivity before those plans create any synthetic material.

## Issues Encountered

- Same seedbox SSH item as above; no other issues. The NAS/sandbox/GHCR portions of this plan all worked on the first attempt with no retries needed.

## User Setup Required

None - no external service configuration required. (The research-session sandbox `sonarr_api_key` exposure and its rotation decision remain tracked separately at `122-08-PLAN.md` Task 1, per `122-RESEARCH.md`'s Open Question #2 resolution — not touched in this plan.)

## Next Phase Readiness

- `seedsyncarr-test` now runs the PR #134 staging image (`DEV_PIN`), verified by digest; production is confirmed untouched
- `122-teardown.sh` and `122-webhook-post.sh` are committed and ready for Plans 05-08's live SAFE-01 scenarios
- **Blocker to resolve before Plan 05 starts creating synthetic material:** confirm the seedbox (`nyx.usbx.me`) accepts SSH connections again from the NAS; it refused TCP connections during this plan's execution window (2026-10-22, ~19:50-19:58Z)

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-22*

## Self-Check: PASSED

- FOUND: .planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md
- FOUND: .planning/phases/122-safety-acceptance-and-logging-fixes/122-teardown.sh
- FOUND: .planning/phases/122-safety-acceptance-and-logging-fixes/122-webhook-post.sh
- FOUND commit 54a1b56 (git log --oneline --all | grep 54a1b56)
- FOUND commit 8ba5a39 (git log --oneline --all | grep 8ba5a39)
- Live LOG-01 log line and production-fingerprint-identical result were both observed directly from command output during this plan's execution (not inferred), quoted verbatim above and in the evidence file
