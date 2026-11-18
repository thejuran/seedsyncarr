# Roadmap: SeedSyncarr

Updated 2026-11-18. Milestone v1.8.1 Configuration and Shutdown Correctness is active (Phases 127–130, started 2026-11-18; nothing implemented yet). Milestone v1.8.0 Reliability shipped 2026-10-28 (Phases 121–126; 1.8.0 published and running on NAS production by digest). Existing implementation must be checked before planning any carried-forward fix.

## Milestones

- ✅ v1.7.4 Safety Patch -- Phases 116–118 (shipped 2026-10-09)
- ✅ v1.7.5 Safety Release -- Phases 119 and 119.1; includes release 1.7.6 (shipped 2026-10-15)
- ✅ v1.7.7 Sonarr 5 Compatibility -- Phase 120 (closed 2026-10-20; verified, no release needed)
- ✅ v1.8.0 Reliability -- Phases 121–126 (shipped 2026-10-28)
- 🔨 v1.8.1 Configuration and Shutdown Correctness -- Phases 127–130 (in progress)

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

### 🔨 v1.8.1 Configuration and Shutdown Correctness (Phases 127–130, in progress)

**Goal:** Make setup guidance accurate, Sonarr/Radarr connection diagnostics agree with real queue requests, and web-service cleanup complete after failures; release and deploy 1.8.1.

**Requirements:** `REQUIREMENTS.md` (11: DOC-01..04, ARR-01..03, WEB-01..02, REL-07..08). Scope agreed 2026-11-18 from a code review of current local code; research skipped (small, code-confirmed fixes). Boundaries: no transfer-architecture replacement, runtime auto-restart expansion, blanket test project, UI redesign or speculative optimization; existing completion/import/deletion safeguards stay intact.

**CI gate (every phase):** full Python suite green AND whole-tree `ruff check src/python/` clean (CI runs ruff as a separate gate from pytest, so build-verify must run it on the whole tree, not just touched files); Python `fail_under` ≥ 88 holds; every targeted regression shown to fail before its fix and pass after.

- [x] **Phase 127: README Accuracy** - Setup, security and documentation-discoverability claims in the README match current defaults, SECURITY.md and the repository guides (completed 2026-11-18)
- [ ] **Phase 128: Arr Key Normalization** - Sonarr/Radarr API keys normalize the same way on save and on read for queue requests, matching Test Connection
- [ ] **Phase 129: Web-Service Cleanup Isolation** - Each web-service shutdown step runs independently so one failure never skips the rest
- [ ] **Phase 130: Release 1.8.1** - Targeted regressions, required gates, release-image smoke test and NAS production deploy pinned to the tag

#### Phase Details

### Phase 127: README Accuracy

**Goal**: A reader following the README reaches every existing guide and sees setup, security and cleanup claims stated as they actually behave
**Depends on**: Nothing (first phase of the milestone; follows Phase 126)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04
**Success Criteria** (what must be TRUE):
  1. A prominent README Documentation section links `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md` and `docs/TESTING.md`, the installation section links repository guides instead of website-only docs, and every relative link resolves
  2. "Security by default" is replaced with accurate wording: API authentication is off when `api_token` is empty, webhook verification is off when `webhook_secret` is empty, `webhook_require_secret` defaults to `False`, and encryption at rest is off by default (stored secrets plaintext) — rechecked against current code and SECURITY.md at implementation time
  3. Absolute "never deletes" claims are replaced by an explanation of import confirmation, optional pruning (off by default) and the safety delay, and the whole README is reviewed for remaining unconditional claims
  4. The Quick Start section tells the reader that the Docker examples publish port 8800 on all host interfaces, that untrusted access needs an authenticating reverse proxy and restricted network access, and that the API token does not protect the UI (which contains that token)
**Plans:** 1/1 plans complete

Plans:
- [x] 127-01-PLAN.md — README structure, guide links and exposure note; conditioned cleanup and security wording; SECURITY.md posture intro sentence and webhook bullet

### Phase 128: Arr Key Normalization

**Goal**: A Sonarr/Radarr API key behaves the same whether it is being saved, tested, or used for a live queue check, regardless of incidental whitespace
**Depends on**: Nothing (independent of Phase 127; disjoint code paths)
**Requirements**: ARR-01, ARR-02, ARR-03
**Success Criteria** (what must be TRUE):
  1. Save, Test Connection and queue completion checks all use one consistent normalization rule: a key entered with leading/trailing whitespace is saved normalized, using the same rule Test Connection already applies
  2. A previously saved whitespace-padded key works for queue completion checks **without the user resaving it** (normalized on read), so Test Connection and queue requests agree on the same stored key (regression test fails before the fix, passes after)
  3. Invalid keys still fail safely: an empty or invalid key in queue completion checks produces no unsafe import or deletion decision, and no key value ever appears in logs
**Plans**: TBD

### Phase 129: Web-Service Cleanup Isolation

**Goal**: A failure in one web-service shutdown step never skips the remaining steps, matching the per-step isolation already present elsewhere in the lifecycle code
**Depends on**: Nothing (independent of Phases 127–128; disjoint code paths)
**Requirements**: WEB-01, WEB-02
**Success Criteria** (what must be TRUE):
  1. With a failure injected into `app.stop()`, `server.stop()` and `thread.join()` still run and the failure is logged (regression test fails before the fix, passes after — confirmed 2026-11-18 that today's code skips both)
  2. With a failure injected into `server.stop()` or `thread.join()` instead, the other steps still run and the failure is logged
  3. Cleanup handles an uninitialized server and an unstarted thread (partial startup) without raising, and still attempts every step that applies
  4. After any failure, cleanup attempts every applicable step and terminates cleanly; tests demonstrate clean termination for both the per-step-failure and the partial-startup scenarios, mirroring the isolation pattern already used by ScanManager/FileOperationManager/Controller
**Plans**: TBD

### Phase 130: Release 1.8.1

**Goal**: 1.8.1 passes its release gates and is running on NAS production, pinned to the released digest
**Depends on**: Phases 127, 128, 129 (all milestone work complete)
**Requirements**: REL-07, REL-08
**Success Criteria** (what must be TRUE):
  1. Fail-before/pass-after regressions exist for the ARR and WEB fixes; full test suite, whole-tree `ruff check src/python/` and release CI are all green on the release commit
  2. Dependency work stays limited to triage and justified fixes: before the tag, open Dependabot alerts and PRs are triaged and surfaced to the owner in plain terms; only justified fixes are rolled in (runtime/shipped fixes in-release; cheap dev-only ones folded in), with no broader dependency upgrades
  3. The release image is smoke-tested by exact digest: setup, a queue completion check using a whitespace-padded key, and stop/restart
  4. NAS production is deployed using the **exact smoke-tested image digest** (pinned `:1.8.1@sha256:…`), followed by a successful scan and queue check, and owner confirmation
**Plans**: TBD

#### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 127. README Accuracy | 1/1 | Complete   | 2026-11-18 |
| 128. Arr Key Normalization | 0/TBD | Not started | - |
| 129. Web-Service Cleanup Isolation | 0/TBD | Not started | - |
| 130. Release 1.8.1 | 0/TBD | Not started | - |

**Done when:** all four success-criteria sets are verified, targeted regression/integration checks and required repository gates pass, a release-image smoke check covers setup, queue completion checks and stop/restart, and 1.8.1 is deployed to NAS production. Boundaries: no transfer-architecture replacement, runtime auto-restart expansion, blanket test project, UI redesign or speculative optimization; existing completion/import/deletion safeguards stay intact.

## Backlog

Items marked Narrow fed the now-active v1.8.1 milestone (promoted into phases 127–129 below); Deferred items remain conditional candidates, not promised fixes or additional phases. Promote a fix only for a demonstrated gap, recording the evidence, smallest scope and finish line. A reproduced data-loss risk or measured resource problem may change the priority order.

### Deferred: Scanner buffering (first investigation candidate)

the result queue is unbounded and the consumer drains to the latest result. Use a representative scan workload with a deliberately stalled consumer to measure queue/resource growth and recovery. Stop when the need for a bound is established or unsupported. Any fix must retain successful-scan evidence, completion/deletion safety and clean shutdown; do not blindly discard observations.

### Deferred: Residual import/restart recovery

compare current behavior and regression evidence with a specific unmatched-event or restart failure scenario. Early episode credit, pending-notice revalidation and restart arm-on-commit already shipped in Phase 119. Stop with a reproducible remaining gap or a documented no-fix conclusion; do not rebuild delivered safeguards.

### Deferred: Memory diagnostics

add only the measurements needed to resolve the buffering investigation, distinguishing current, child-process and peak usage where relevant. Stop once the resource question is answered. No standalone monitoring or diagnostics project.

### Deferred: UI and webhook efficiency

measure realistic update/idle workloads before proposing optimization. Initial model delivery already uses one snapshot; examine remaining per-update serialization and repeated lookup construction. Stop with a baseline and worthwhile target, or defer. Preserve pending-notice revalidation and correctness; no speculative caching or rendering rewrite.



### Deferred: Extract-staging max-deferrals config key

Add an `autodelete.max_deferrals` config key (default 24; 0 restores the pre-1.7.3 one-shot behavior) so the auto-delete re-arm cap is configurable instead of a fixed constant. Source: `.planning/debug/extract-staging-autodel-rearm.md` item D.

### Deferred: Extract-staging helper module split

Move the five staging helpers out of `dispatch.py` into a dedicated `controller/extract/staging.py`, and move `_AUTO_DELETE_DEFER_REASONS` next to the reason codes in `auto_delete_manager.py`. Cohesion only, no behavior change. Source: `.planning/debug/extract-staging-autodel-rearm.md` item E.

### Deferred: Extract-staging log sanitization

Apply `sanitize_log_value` to archive-derived paths in the new dispatch log lines (publish, discard, warn-unpublished). Security LOW, CWE-117. Source: `.planning/debug/extract-staging-autodel-rearm.md` item F.

### Deferred: Extract-staging test gaps

Add tests for the three cleanup OSError handlers, a lock-order recorder across a re-arm cycle, and the dispatch loop stop path. Source: `.planning/debug/extract-staging-autodel-rearm.md` item G.

### Narrow: Arr API key normalization (Phase 122 review WR-04)

**Disposition (2026-11-18):** Selected for the corrective milestone; promoted into Phase 128 (v1.8.1) on 2026-11-18 at roadmap creation. Retained here for provenance only; plan and track implementation in Phase 128, not as a separate backlog phase.

Test Connection strips and validates the Arr API key before testing (122-14), but the saved key is never normalized and `controller/arr_queue.py` sends it as stored. A key pasted with a stray space or newline passes Test Connection while every real queue check fails, so completions stay held as "Sonarr unavailable" (fail-safe; no wrong deletes, but a false all-clear from the diagnostic). Fix: normalize on save and in `arr_queue.py` so already-saved keys keep working. Owner chose backlog 2026-10-25. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` WR-04.

### Deferred: Post-transfer notice window edge cases (Phase 122 review IN-04, IN-05)

Fail-safe edge cases of the 120 s post-transfer grace window (122-13): a STOP handled in the same cycle that records "last seen transferring" can let a brand-new notice be credited for up to 120 s (credit only, never deletes by itself) (IN-04); a root the local scanner hasn't seen yet is logged as "local copy gone", and a local scan slower than 120 s loses the notice even when the transfer finished normally (no credit, no deletion; brings back the missed-import symptom 122-10 fixed) (IN-05). Owner chose backlog 2026-10-25. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` IN-04, IN-05.

### Deferred: Modern RAR volume coalescing (found in Phase 122-07)

`ExtractDispatch.__coalesce_extractions` (`src/python/controller/extract/dispatch.py`) only filters legacy `.rNN` continuation volumes, so a RAR 5+ archive named `.partN.rar` runs one redundant extraction-and-publish pass per volume. Output is still complete and correct (staging-then-publish holds), so this is efficiency, not safety. Source: `.planning/phases/122-safety-acceptance-and-logging-fixes/deferred-items.md` second section. Still deferred. Promote only if `.partN.rar` archives recur in the actual workload; measure redundant passes and validate one complete extraction per archive set. Not a lifecycle issue.

### 999.5: Move Sonarr integration to API v5

**Scope:** Sonarr 5 lists the v3 API as deprecated (still served as of 5.0.0.2701). Move SeedSyncarr's two Sonarr API calls (`system/status` connection test, `queue/details` completion evidence; the webhook payload is version-independent) to `/api/v5` when Sonarr 4 support can be dropped, or with version detection that keeps v3 for Sonarr 4. Note the v5 queue model differences: one tracked item can cover multiple episodes (`episodeIds`/`episodes` lists), `timeLeft` casing, and `includeSubresources`. Activate when Sonarr announces v3 removal, Sonarr 5 goes stable and prod upgrades, or v1.7.7 finds a v3 gap. Radarr unaffected. Not a Reliability gate.

### Narrow: WebAppJob cleanup per-step isolation (Phase 123 PR #137 review)

**Disposition (2026-11-18):** Selected for the corrective milestone; promoted into Phase 129 (v1.8.1) on 2026-11-18 at roadmap creation. Retained here for provenance only; plan and track implementation in Phase 129, not as a separate backlog phase.

`WebAppJob.cleanup()` (`src/python/web/web_app_job.py`) does not get the per-step stop isolation Phase 123 added elsewhere: if `self.__app.stop()` raises, `self.__server.stop()` and `self.__server_thread.join()` are skipped, and `MyWSGIRefServer.stop()` can raise AttributeError while its inner server is still None (123-REVIEW IN-01 is the related thread-never-started guard). Fix: wrap each stop step in its own try/except + `logger.exception`, mirroring ScanManager/FileOperationManager/Controller. Owner chose backlog 2026-10-26. Source: `.planning/phases/123-startup-and-shutdown-lifecycle/deferred-items.md` item 7.

### Deferred: Controller runtime failures and RECOV-01 auto-restart (Phase 123 PR #137 review)

Only `ControllerJob.setup()` failures are wrapped into `ControllerError` for the RECOV-01 bounded auto-restart; a non-AppError raised later from `Controller.process()` (`ControllerJob.execute()`) still reaches the main loop as a non-AppError and ends the process. Deliberate setup-only scope (Phase 123 D-04/D-05); extending it is a product decision. Owner chose backlog 2026-10-26. Source: `deferred-items.md` item 8.

### Deferred: SIGINT-killed scanners outside the shutdown grace (Phase 123 review WR-01)

The D-01 shutdown-grace window in `ScanManager._check_process_health()` (`src/python/controller/scan_manager.py` ~line 312) recognizes only `-signal.SIGTERM` scanner deaths, although `seedsyncarr.py` handles SIGINT identically. A Ctrl-C on a foreground run or `docker run -it` can still log the false "Scanner process(es) died unexpectedly" ERROR and trigger an auto-restart. Not on this project's docker stop/restart path (always SIGTERM; clean across 17 live cycles). Fix: accept `{-SIGTERM, -SIGINT}` plus a matching test. Verifier classified minor/non-blocking and auto-parked 2026-10-27. Source: `123-REVIEW.md` WR-01, `123-VERIFICATION.md`.

### Deferred: Model-stream resync comment accuracy and test tightening (Phase 124 review WR-01/WR-02)

In `ModelStreamHandler.get_value()` (`src/python/web/handler/stream_model.py` ~lines 81-107), the dropped-count check and `get_next_event()` are two separate unlocked reads. An overflow landing between them can let one post-gap incremental event through before the *next* call resyncs. Convergence still holds, but the comment's "the first value after a drop is never a stale backlog event" overstates it. Fix: either re-check the dropped count after dequeuing and resync instead of emitting, or correct the comment (WR-01). Also: `test_resync_pending_state_is_bounded` asserts `initial_model_files` rather than resync state (WR-02, real property covered by `test_multiple_drops_coalesce_into_one_resync`), and the `_drain` loops in `test_stream_model_overflow.py` have no iteration cap, so a resync-forever regression would hang instead of fail (IN-02). Verifier classified minor/non-blocking and auto-parked 2026-10-27. Source: `124-REVIEW.md`, `124-VERIFICATION.md`.

### Phase 999.6: README documentation discoverability and accurate security defaults (BACKLOG)

**Captured:** 2026-10-26. Selected for the corrective milestone on 2026-11-18; promoted into Phase 127 (v1.8.1) on 2026-11-18 at roadmap creation. Retained here for provenance only; plan and track implementation in Phase 127, not as a separate backlog phase.
**Goal:** Make existing guides easy to find and make README security and cleanup claims match actual defaults and limitations.
**Scope:** README.md only; no application behavior changes. This is the documentation item in the corrective milestone.
**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04 (Phase 127)
**Plans:** 0 plans

Acceptance criteria:

- Add a prominent Documentation section linking directly to `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, and `docs/TESTING.md`. Replace the installation section's website-only documentation link with repository guide links.
- Replace "Security by default" with accurate security-control wording. State that API authentication is off when `api_token` is empty, webhook verification is off when `webhook_secret` is empty, `webhook_require_secret` defaults to `False`, and encryption at rest defaults to off (stored secrets are plaintext).
- Qualify HMAC verification claims throughout the README. Replace absolute "never deletes" promises with an explanation of import confirmation, optional pruning, and the safety delay; note that pruning defaults to off.
- Explain near Quick Start that the Docker examples publish port 8800 on all host interfaces and that untrusted access needs an authenticating reverse proxy and restricted network access. Clarify that the API token does not protect the UI, which includes that token.
- Verify relative links, recheck defaults against current code and SECURITY.md at implementation time, and review the entire README for remaining unconditional claims. Documentation review only; no new application tests needed for this prose change.

**Context:** A community comment described SeedSyncArr as having "no documentation" and raised concerns after Huntarr. Existing guides are present, but discoverability and inconsistent security messaging warrant this bounded correction. The comment is motivation, not evidence of equivalent vulnerabilities.

Plans:

- [x] Defined: Phase 127 (v1.8.1), 2026-11-18. No phase or version assigned before this roadmap; see Phase 127 above for plans.

### 999.7: Speed up the CI Docker image build

**Scope:** Two small changes first: (1) build the Angular stage once on the build platform (`FROM --platform=$BUILDPLATFORM node:22-slim AS seedsyncarr_build_angular_env` in `src/docker/build/docker-image/Dockerfile`) instead of running `npm install` + the Angular build under QEMU for arm64 (its output is architecture-independent JS); (2) let the `build-docker-image` job in `.github/workflows/ci.yml` start in parallel with the unit-test/lint jobs instead of `needs:`-ing all seven, keeping the end-to-end and publish jobs gated on tests passing. Evidence (last 30 CI runs, 2026-10-27): build job 0–5 min when the registry cache hits, outliers 16/23/27 min on cache misses; Python unit tests (~5–6 min) sit on the critical path before the build starts. Further options only if needed: amd64-only PR images (NAS is x86_64; arm64 E2E already skipped on PRs; main/tags still build both), or native arm64 builds on `ubuntu-24.04-arm` plus a manifest merge. Not a Reliability gate.

### 999.8: Webhook authentication Sonarr/Radarr can send

**Captured:** 2026-11-18 (Phase 127 research). SeedSyncarr verifies inbound import webhooks only via an HMAC-SHA256 of the request body in `X-Webhook-Signature` (`src/python/web/handler/webhook.py`). Sonarr (confirmed in `WebhookProxy.cs`, PR #7371) and Radarr (assumed same) send only fixed custom headers or basic auth and never compute a signature, so setting `webhook_secret` or `webhook_require_secret = true` rejects every import webhook (401/503) and pruning silently stops (fail-safe, nothing deleted). **Scope:** accept an authentication method the *arrs can send (e.g. a fixed shared-secret header or basic-auth credentials, constant-time compared) alongside or instead of body HMAC, then update README/SECURITY.md advice. Owner chose backlog 2026-11-18. Not in v1.8.1.

### 999.9: Prune only files SeedSyncarr transferred

**Captured:** 2026-11-18 (Phase 127 code review WR-02 / SA-01). The README (How It Works, the Security section's forged-import sentence) and `docs/CONFIGURATION.md:169` say pruning applies only to releases SeedSyncarr itself downloaded. The code does not check that: an item is treated as downloaded when a local entry has the same name as a seedbox entry and is at least as large (`src/python/controller/model_builder.py:510-525`, `model_pipeline.py:205-227`, `controller.py:828-970`), so a copy placed in the downloads folder by hand or by another tool can be pruned after a real or forged import webhook. **Owner ruling 2026-11-18:** keep the docs' promise and make the code true (record which files SeedSyncarr transferred and prune only those), rather than weakening the wording. The README ships with this claim ahead of the code until the fix lands. Also fix the stale comment at `controller.py:31-32` (says 300 s default safety delay; actual 60 s, review SA-02). Milestone placement is the owner's call.

## Following milestone: Performance and Usability (conditional)

**Activation:** Complete the corrective milestone, then demonstrate meaningful resource pressure, repeated redundant work or recurring user friction. Cancel or defer if representative evidence shows no worthwhile opportunity.

**Goal:** Remove demonstrated unnecessary work without changing transfer architecture.

1. [ ] **Bounded scanner investigation.** Measure queue growth, parent/child memory and recovery under a representative scan workload with a deliberately stalled consumer. Stop with a demonstrated need for a safe bound or a documented no-fix conclusion; preserve successful-scan and deletion evidence.
2. [ ] **Measured efficiency improvements.** Select UI/webhook changes only from realistic baseline measurements. Consider modern multipart RAR coalescing only if those archives recur in the user's workload. Agree before/after targets before implementation.

**Done when:** selected improvements meet their agreed targets and preserve correctness under relevant integration checks. Setup documentation belongs to the preceding corrective milestone. No standalone diagnostics project or speculative caching/rendering rewrite.

## Future milestone: Pipeline Visibility (conditional)

**Activation:** After the corrective milestone, validate recurring confusion about why a completed transfer awaits import or cleanup. Set its order relative to performance work from that evidence; neither follow-up is promised.

**Goal:** Help users understand import and cleanup state with a narrowly scoped dashboard improvement.

1. [ ] **Explain import and cleanup progress.** Start with existing status, import_status and hold_reason data. Confirm deletion/restart semantics before adding a minimal field if needed. Done when a walkthrough can explain a held transfer, a completed transfer awaiting import and an imported file awaiting cleanup without guessing from logs.

**Boundaries:** The UI already displays Waiting and a hold reason. Do not rebuild that safeguard. Settings restructuring, phone/iPhone Duo layouts, onboarding, release-name parsing and global visual changes stay deferred. The [original UI Redesign brief](backlog/UI-REDESIGN.md) preserves those ideas, not an approved delivery scope.

## Review evidence and reconciled items

The 2026-11-18 prioritization used current local code and the recorded October 28 release acceptance. GitHub access failed; present-day remote issues, advisory status and production health were not reverified. No full test suite was run for this planning review.

- Extraction symlink filtering already exists in `ExtractDispatch.__strip_symlinks`, called before publication, with a regression test. Remove this stale proposed fix from active consideration.
- Phase 126 records braces/karma item 999.4 as **no fix needed** (`braces@3.0.3`). This is historical release evidence, not a claim about today's advisory database.
- Original entries, evidence and reopening conditions are retained in [the reconciliation archive](backlog/archive/2026-11-18/README.md).

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
