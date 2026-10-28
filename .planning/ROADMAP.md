# Roadmap: SeedSyncarr

Updated 2026-10-28. Milestone v1.8.0 Reliability shipped 2026-10-28 (Phases 121–126; 1.8.0 published and running on NAS production by digest). No milestone is active; the next one starts with `/bm:new-milestone`. Existing implementation must be checked before planning any carried-forward fix.

## Milestones

- ✅ v1.7.4 Safety Patch -- Phases 116–118 (shipped 2026-10-09)
- ✅ v1.7.5 Safety Release -- Phases 119 and 119.1; includes release 1.7.6 (shipped 2026-10-15)
- ✅ v1.7.7 Sonarr 5 Compatibility -- Phase 120 (closed 2026-10-20; verified, no release needed)
- ✅ v1.8.0 Reliability -- Phases 121–126 (shipped 2026-10-28)

Future milestone names and scope are below; their versions remain unassigned. Earlier release history remains in STATE.md and milestone archives.

<details>
<summary>✅ v1.7.7 Sonarr 5 Compatibility (Phase 120) — CLOSED 2026-10-20, verified; no release needed</summary>

- [x] Phase 120: Sonarr 5 Compatibility (6/6 plans) — completed 2026-10-20. [Archived roadmap](milestones/v1.7.7-ROADMAP.md)

</details>

<details>
<summary>✅ v1.8.0 Reliability (Phases 121–126) — SHIPPED 2026-10-28</summary>

- [x] Phase 121: Credential Forwarding (3/3 plans) — completed 2026-10-21
- [x] Phase 122: Safety Acceptance and Logging Fixes (17/17 plans) — completed 2026-10-25
- [x] Phase 123: Startup and Shutdown Lifecycle (17/17 plans) — completed 2026-10-27
- [x] Phase 124: Model-Stream Overflow Recovery (3/3 plans) — completed 2026-10-27
- [x] Phase 125: LAN Connection Tests (6/6 plans) — completed 2026-10-28
- [x] Phase 126: Release 1.8.0 (6/6 plans) — completed 2026-10-28

[Archived roadmap](milestones/v1.8.0-ROADMAP.md) · [Requirements](milestones/v1.8.0-REQUIREMENTS.md)

</details>

## Backlog

These are bounded evidence-gathering candidates, not promised fixes or additional phases. Promote a fix only for a demonstrated gap, recording the evidence, smallest scope and finish line. A reproduced data-loss risk or measured resource problem may change the priority order.

### Deferred: Scanner buffering (first investigation candidate)

the result queue is unbounded and the consumer drains to the latest result. Use a representative scan workload with a deliberately stalled consumer to measure queue/resource growth and recovery. Stop when the need for a bound is established or unsupported. Any fix must retain successful-scan evidence, completion/deletion safety and clean shutdown; do not blindly discard observations.

### Deferred: Residual import/restart recovery

compare current behavior and regression evidence with a specific unmatched-event or restart failure scenario. Early episode credit, pending-notice revalidation and restart arm-on-commit already shipped in Phase 119. Stop with a reproducible remaining gap or a documented no-fix conclusion; do not rebuild delivered safeguards.

### Deferred: Memory diagnostics

add only the measurements needed to resolve the buffering investigation, distinguishing current, child-process and peak usage where relevant. Stop once the resource question is answered. No standalone monitoring or diagnostics project.

### Deferred: UI and webhook efficiency

measure realistic update/idle workloads before proposing optimization. Initial model delivery already uses one snapshot; examine remaining per-update serialization and repeated lookup construction. Stop with a baseline and worthwhile target, or defer. Preserve pending-notice revalidation and correctness; no speculative caching or rendering rewrite.

### 999.4: Recheck the braces/karma dev-test advisory

**Scope:** Bounded maintenance side task, separate from milestone scope. recheck the recorded braces/karma dev-test advisory and related deferred PRs (#128/#125/#117), including current affected versions and runtime/build exposure. Apply the smallest supported fix if still relevant, with the affected build/test checks. Records classify it as dev/test-only; current advisory status has not been refreshed. This is not a separate milestone or a general test-runner rewrite. It is rechecked within REL-05 (Phase 126) as part of the pre-tag Dependabot review; that recheck records the outcome, and the item is rolled into 1.8.0 only if the fix is cheap or current evidence establishes material exposure.

### Deferred: Extract-staging symlink hardening

Refuse symlink entries at publish time in `ExtractDispatch.__publish_staged_output` (skip with a WARNING), closing a pre-existing exposure where patool could write a symlink straight into the release folder. Security HIGH, CWE-59. Source: `.planning/debug/extract-staging-autodel-rearm.md` item C.

### Deferred: Extract-staging max-deferrals config key

Add an `autodelete.max_deferrals` config key (default 24; 0 restores the pre-1.7.3 one-shot behavior) so the auto-delete re-arm cap is configurable instead of a fixed constant. Source: `.planning/debug/extract-staging-autodel-rearm.md` item D.

### Deferred: Extract-staging helper module split

Move the five staging helpers out of `dispatch.py` into a dedicated `controller/extract/staging.py`, and move `_AUTO_DELETE_DEFER_REASONS` next to the reason codes in `auto_delete_manager.py`. Cohesion only, no behavior change. Source: `.planning/debug/extract-staging-autodel-rearm.md` item E.

### Deferred: Extract-staging log sanitization

Apply `sanitize_log_value` to archive-derived paths in the new dispatch log lines (publish, discard, warn-unpublished). Security LOW, CWE-117. Source: `.planning/debug/extract-staging-autodel-rearm.md` item F.

### Deferred: Extract-staging test gaps

Add tests for the three cleanup OSError handlers, a lock-order recorder across a re-arm cycle, and the dispatch loop stop path. Source: `.planning/debug/extract-staging-autodel-rearm.md` item G.

### Deferred: Arr API key normalization (Phase 122 review WR-04)

Test Connection strips and validates the Arr API key before testing (122-14), but the saved key is never normalized and `controller/arr_queue.py` sends it as stored. A key pasted with a stray space or newline passes Test Connection while every real queue check fails, so completions stay held as "Sonarr unavailable" (fail-safe; no wrong deletes, but a false all-clear from the diagnostic). Fix: normalize on save and in `arr_queue.py` so already-saved keys keep working. Owner chose backlog 2026-10-25. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` WR-04.

### Deferred: Post-transfer notice window edge cases (Phase 122 review IN-04, IN-05)

Fail-safe edge cases of the 120 s post-transfer grace window (122-13): a STOP handled in the same cycle that records "last seen transferring" can let a brand-new notice be credited for up to 120 s (credit only, never deletes by itself) (IN-04); a root the local scanner hasn't seen yet is logged as "local copy gone", and a local scan slower than 120 s loses the notice even when the transfer finished normally (no credit, no deletion; brings back the missed-import symptom 122-10 fixed) (IN-05). Owner chose backlog 2026-10-25. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` IN-04, IN-05.

### Deferred: Modern RAR volume coalescing (found in Phase 122-07)

`ExtractDispatch.__coalesce_extractions` (`src/python/controller/extract/dispatch.py`) only filters legacy `.rNN` continuation volumes, so a RAR 5+ archive named `.partN.rar` runs one redundant extraction-and-publish pass per volume. Output is still complete and correct (staging-then-publish holds), so this is efficiency, not safety. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` second section. Kept out of Phase 123 (not a lifecycle issue).

### 999.5: Move Sonarr integration to API v5

**Scope:** Sonarr 5 lists the v3 API as deprecated (still served as of 5.0.0.2701). Move SeedSyncarr's two Sonarr API calls (`system/status` connection test, `queue/details` completion evidence; the webhook payload is version-independent) to `/api/v5` when Sonarr 4 support can be dropped, or with version detection that keeps v3 for Sonarr 4. Note the v5 queue model differences: one tracked item can cover multiple episodes (`episodeIds`/`episodes` lists), `timeLeft` casing, and `includeSubresources`. Activate when Sonarr announces v3 removal, Sonarr 5 goes stable and prod upgrades, or v1.7.7 finds a v3 gap. Radarr unaffected. Not a Reliability gate.

### Deferred: WebAppJob cleanup per-step isolation (Phase 123 PR #137 review)

`WebAppJob.cleanup()` (`src/python/web/web_app_job.py`) does not get the per-step stop isolation Phase 123 added elsewhere: if `self.__app.stop()` raises, `self.__server.stop()` and `self.__server_thread.join()` are skipped, and `MyWSGIRefServer.stop()` can raise AttributeError while its inner server is still None (123-REVIEW IN-01 is the related thread-never-started guard). Fix: wrap each stop step in its own try/except + `logger.exception`, mirroring ScanManager/FileOperationManager/Controller. Owner chose backlog 2026-10-26. Source: `.planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md` item 7.

### Deferred: Controller runtime failures and RECOV-01 auto-restart (Phase 123 PR #137 review)

Only `ControllerJob.setup()` failures are wrapped into `ControllerError` for the RECOV-01 bounded auto-restart; a non-AppError raised later from `Controller.process()` (`ControllerJob.execute()`) still reaches the main loop as a non-AppError and ends the process. Deliberate setup-only scope (Phase 123 D-04/D-05); extending it is a product decision. Owner chose backlog 2026-10-26. Source: `deferred-items.md` item 8.

### Deferred: SIGINT-killed scanners outside the shutdown grace (Phase 123 review WR-01)

The D-01 shutdown-grace window in `ScanManager._check_process_health()` (`src/python/controller/scan_manager.py` ~line 312) recognizes only `-signal.SIGTERM` scanner deaths, although `seedsyncarr.py` handles SIGINT identically. A Ctrl-C on a foreground run or `docker run -it` can still log the false "Scanner process(es) died unexpectedly" ERROR and trigger an auto-restart. Not on this project's docker stop/restart path (always SIGTERM; clean across 17 live cycles). Fix: accept `{-SIGTERM, -SIGINT}` plus a matching test. Verifier classified minor/non-blocking and auto-parked 2026-10-27. Source: `123-REVIEW.md` WR-01, `123-VERIFICATION.md`.

### Deferred: Model-stream resync comment accuracy and test tightening (Phase 124 review WR-01/WR-02)

In `ModelStreamHandler.get_value()` (`src/python/web/handler/stream_model.py` ~lines 81-107), the dropped-count check and `get_next_event()` are two separate unlocked reads. An overflow landing between them can let one post-gap incremental event through before the *next* call resyncs. Convergence still holds, but the comment's "the first value after a drop is never a stale backlog event" overstates it. Fix: either re-check the dropped count after dequeuing and resync instead of emitting, or correct the comment (WR-01). Also: `test_resync_pending_state_is_bounded` asserts `initial_model_files` rather than resync state (WR-02, real property covered by `test_multiple_drops_coalesce_into_one_resync`), and the `_drain` loops in `test_stream_model_overflow.py` have no iteration cap, so a resync-forever regression would hang instead of fail (IN-02). Verifier classified minor/non-blocking and auto-parked 2026-10-27. Source: `124-REVIEW.md`, `124-VERIFICATION.md`.

### Phase 999.6: README documentation discoverability and accurate security defaults (BACKLOG)

**Captured:** 2026-10-26. Owner requested backlog only; do not implement yet.
**Goal:** Make existing guides easy to find and make README security and cleanup claims match actual defaults and limitations.
**Scope:** README.md only; no application behavior changes. This is a concrete candidate for the following Performance and Usability milestone's setup/configuration documentation work, not an active Reliability gate.
**Requirements:** TBD
**Plans:** 0 plans

Acceptance criteria:

- Add a prominent Documentation section linking directly to `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, and `docs/TESTING.md`. Replace the installation section's website-only documentation link with repository guide links.
- Replace "Security by default" with accurate security-control wording. State that API authentication is off when `api_token` is empty, webhook verification is off when `webhook_secret` is empty, `webhook_require_secret` defaults to `False`, and encryption at rest defaults to off (stored secrets are plaintext).
- Qualify HMAC verification claims throughout the README. Replace absolute "never deletes" promises with an explanation of import confirmation, optional pruning, and the safety delay; note that pruning defaults to off.
- Explain near Quick Start that the Docker examples publish port 8800 on all host interfaces and that untrusted access needs an authenticating reverse proxy and restricted network access. Clarify that the API token does not protect the UI, which includes that token.
- Verify relative links, recheck defaults against current code and SECURITY.md at implementation time, and review the entire README for remaining unconditional claims. Documentation review only; no new application tests needed for this prose change.

**Context:** A community comment described SeedSyncArr as having "no documentation" and raised concerns after Huntarr. Existing guides are present, but discoverability and inconsistent security messaging warrant this bounded correction. The comment is motivation, not evidence of equivalent vulnerabilities.

Plans:

- [ ] TBD (promote with $gsd-review-backlog when ready)

### 999.7: Speed up the CI Docker image build

**Scope:** Two small changes first: (1) build the Angular stage once on the build platform (`FROM --platform=$BUILDPLATFORM node:22-slim AS seedsyncarr_build_angular_env` in `src/docker/build/docker-image/Dockerfile`) instead of running `npm install` + the Angular build under QEMU for arm64 (its output is architecture-independent JS); (2) let the `build-docker-image` job in `.github/workflows/ci.yml` start in parallel with the unit-test/lint jobs instead of `needs:`-ing all seven, keeping the end-to-end and publish jobs gated on tests passing. Evidence (last 30 CI runs, 2026-10-27): build job 0–5 min when the registry cache hits, outliers 16/23/27 min on cache misses; Python unit tests (~5–6 min) sit on the critical path before the build starts. Further options only if needed: amd64-only PR images (NAS is x86_64; arm64 E2E already skipped on PRs; main/tags still build both), or native arm64 builds on `ubuntu-24.04-arm` plus a manifest merge. Not a Reliability gate.

## Next milestone: Performance and Usability (conditional)

**Activation:** v1.8.0 Reliability is complete and measurements or recurring user friction justify a bounded follow-up. If no material opportunity is demonstrated, defer this milestone.

**Goal:** Remove demonstrated unnecessary work and remaining setup friction without changing the transfer architecture.

1. [ ] **Measured UI/webhook efficiency.** Select only improvements supported by the backlog investigations, with agreed baseline and before/after targets.
2. [ ] **Setup/configuration documentation.** Correct concrete discrepancies not already fixed in Phase 119 or alongside Reliability work.

Credential forwarding and LAN connection tests belong to v1.8.0 Reliability, not this milestone.

**Done when:** selected improvements meet their agreed before/after targets, relevant integration/UI checks pass, and affected documentation matches delivered behavior. Scope, phase numbers and release version are assigned only after activation.

## Future milestone: UI Redesign (pipeline-first)

**Activation:** after v1.8.0 Reliability (shipped 2026-10-28); set its order relative to Performance and Usability when activated. Not active; no phases or version assigned.

**Goal:** Make the import-driven safe-delete pipeline visible: show each file's lifecycle (seedbox → local → imported → local copy cleaned up), surface problems with per-row actions, regroup Settings around the pipeline, and add phone and iPhone Duo layouts. Full scope, backend dependencies, component change list and finish line: [UI Redesign brief](backlog/UI-REDESIGN.md). Design canvas linked there.

## Operator follow-ups (not development milestones)

- [ ] Rotate the production `api_token` (optional, per the 1.8.0 release-note disclosure; Phase 121 pending item).
- [ ] Confirm credential rotation from the 1.7.6 checklist is complete.
- [x] Confirm one-time Done-group cleanup is complete. Owner confirmed 2026-10-23 (Phase 122-09, verbatim "All confirmed"); `done-group-no-auto-delete.md` and `extract-staging-autodel-rearm.md` both resolved and moved to `.planning/debug/resolved/`.
- [ ] Rotate the sandbox `sonarr-v5` Sonarr API key (exposed once in a Phase 122 research-session tool transcript, never written to a repo file; test Sonarr only, not production). Owner declined rotation during 122-08, verbatim "I'll replace it myself later" (`owner-later`).

## Completed releases

- **1.8.0:** Reliability, Phases 121–126; deployed to NAS production 2026-10-28 by digest. [Archived roadmap](milestones/v1.8.0-ROADMAP.md).
- **1.7.4:** safety patch, Phases 116–118. [Archived roadmap](milestones/v1.7.4-ROADMAP.md).
- **v1.7.7 (no release):** Sonarr 5.0.0.2701 compatibility verified on the sandbox and pinned in CI, Phase 120. [Archived roadmap](milestones/v1.7.7-ROADMAP.md).
- **1.7.5 / 1.7.6:** safety release and startup-secret fix, Phases 119/119.1. Records show 1.7.6 deployed to the NAS on 2026-10-15. [Archived audit](milestones/v1.7.5-MILESTONE-AUDIT.md). The browser checks passed 2026-10-18; the extraction/import checks are Phase 122 (SAFE-01).

## Planning boundaries

Retain LFTP and the existing architecture. Keep changes small and supported by demonstrated behavior. No blanket phase-directory cleanup. Routine dependency/test cleanup is tracked in [maintenance](backlog/MAINTENANCE.md), not as its own milestone.

[Earlier roadmap and closed decisions](backlog/archive/2026-10-18/README.md) are preserved outside this active work list.
