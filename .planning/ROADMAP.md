# Roadmap: SeedSyncarr

Updated 2026-10-21. Milestone v1.8.0 Reliability is active (Phases 121–126, started 2026-10-21; nothing implemented yet). v1.7.7 Sonarr 5 Compatibility closed 2026-10-20 (verified; no release needed). NAS production runs 1.7.6. Existing implementation must be checked before planning any carried-forward fix.

## Milestones

- ✅ v1.7.4 Safety Patch -- Phases 116–118 (shipped 2026-10-09)
- ✅ v1.7.5 Safety Release -- Phases 119 and 119.1; includes release 1.7.6 (shipped 2026-10-15)
- ✅ v1.7.7 Sonarr 5 Compatibility -- Phase 120 (closed 2026-10-20; verified, no release needed)
- 🔨 v1.8.0 Reliability -- Phases 121–126 (in progress)

Future milestone names and scope are below; their versions remain unassigned. Earlier release history remains in STATE.md and milestone archives.

<details>
<summary>✅ v1.7.7 Sonarr 5 Compatibility (Phase 120) — CLOSED 2026-10-20, verified; no release needed</summary>

- [x] Phase 120: Sonarr 5 Compatibility (6/6 plans) — completed 2026-10-20. [Archived roadmap](milestones/v1.7.7-ROADMAP.md)

</details>

### 🔨 v1.8.0 Reliability (Phases 121–126, in progress)

**Goal:** Stop the app token from being sent to outside services, close the outstanding safety acceptance checks, and repair demonstrated lifecycle and integration failures with small changes, then release and deploy 1.8.0.

**Requirements:** `REQUIREMENTS.md` (13: SEC-02, SAFE-01/02, LIFE-01/02, STRM-01/02, LAN-01/02, LOG-01/02, REL-05/06). Owner-approved priority order: credential forwarding → safety acceptance → startup/shutdown → model-stream overflow → LAN connection tests → release. Planning boundaries: small, evidence-backed changes only; no authentication, lifecycle-framework or event-bus redesign; no broad relaxation of outbound requests; retain LFTP, the existing architecture, the Phase 119 import/deletion safeguards, existing per-component controller cleanup, auto-delete shutdown guards and lock ordering.

**CI gate (every phase):** full Python suite green AND whole-tree `ruff check src/python/` clean (CI runs ruff as a separate gate from pytest, so build-verify must run it on the whole tree, not just touched files); Python `fail_under` ≥ 88 holds; Angular unit tests and Karma `check.global` thresholds green where Angular code is touched (Phase 121); every targeted regression shown to fail before its fix and pass after.

- [x] **Phase 121: Credential Forwarding** - The app token is attached only to SeedSyncarr's own API requests, never to external destinations such as the GitHub update check (completed 2026-10-21)
- [ ] **Phase 122: Safety Acceptance and Logging Fixes** - Extraction/import/auto-delete checks pass on a running build, incident records are reconciled, and webhook/completion-gate log messages are accurate
- [ ] **Phase 123: Startup and Shutdown Lifecycle** - Partial startup failures clean up started children; a failing component cleanup does not stop the remaining cleanups
- [ ] **Phase 124: Model-Stream Overflow Recovery** - A slow client converges to current server state after overflow, with bounded buffering (or a recorded existing guarantee)
- [ ] **Phase 125: LAN Connection Tests** - Test Connection accepts intended local Sonarr/Radarr addresses, including Docker container names, while unintended destinations stay rejected
- [ ] **Phase 126: Release 1.8.0** - Dependabot review, publish to Docker/GitHub/PyPI, NAS digest smoke test, production deploy by digest confirmed by a successful scan

#### Phase Details

### Phase 121: Credential Forwarding

**Goal**: The configured app token reaches only SeedSyncarr's own API; no outside service ever receives it
**Depends on**: Nothing (first phase of the milestone; follows Phase 120)
**Requirements**: SEC-02
**Success Criteria** (what must be TRUE):

  1. A request from the UI to a SeedSyncarr `/server/*` endpoint still carries the Bearer token and succeeds (no regression in authenticated UI flows, verified by Angular unit tests and the existing E2E suite)
  2. The GitHub update-check request, and any other request to a non-app origin, is sent with no `Authorization` header or app token (regression test asserts the absence)
  3. A regression test that asserts the token is absent on an external request fails against the current interceptor and passes after the fix
  4. No authentication redesign: the token source (meta tag), the interceptor mechanism and the server-side Bearer check are unchanged

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 121-01-PLAN.md — TDD: destination-gated authInterceptor (own origin + /server/, fail closed), RED-first GitHub-URL test, D-10 case table, VersionCheckService pin
- [x] 121-02-PLAN.md — Token-configured E2E: dependent `chromium-token` Playwright project asserting no Authorization to api.github.com

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 121-03-PLAN.md — Phase gate: full Angular/lint/SC4 checks, D-07 evidence, D-08/D-09 carried to 126, PR CI E2E green (owner go-ahead to push)

**UI hint**: yes

### Phase 122: Safety Acceptance and Logging Fixes

**Goal**: The Phase 119 safety behaviors are proven on a running build, the two open incident records say truthfully what is fixed and what is not, and the two log messages found in Phase 120 stop misleading operators
**Depends on**: Phase 121 (sequencing only; disjoint code paths)
**Requirements**: SAFE-01, SAFE-02, LOG-01, LOG-02
**Success Criteria** (what must be TRUE):

  1. On a running build (sandbox `seedsyncarr-test`; prod untouched), extraction, import and auto-delete checks each pass with recorded evidence (log excerpts, timestamps, resulting file state), completing the extraction/import half of `119-VERIFICATION.md` whose browser half passed 2026-10-18
  2. `.planning/debug/done-group-no-auto-delete.md` and `extract-staging-autodel-rearm` each record, per finding, "verified fixed (evidence)" or "remaining operator cleanup"; neither is marked closed solely because its code shipped, and the Done-group one-time cleanup remains an operator follow-up until the owner confirms it
  3. A webhook Test event produces a `<source> webhook test event received` INFO line in the app log (handler logger attached under the app logger), with a regression test that fails before and passes after
  4. When the completion gate prunes a hold (root left the stability sweep), the app log says the hold was *dropped* (no release); `Completion hold cleared` appears only for a proof-based release, with a regression test covering both paths
  5. Phase 119 import safeguards (early credit, pending-notice revalidation, arm-on-commit, Waiting holds, one-shot manual release) are exercised, not rebuilt

**Plans**: 17 plans (9 + 8 gap closure)

Plans:
**Wave 1**

- [x] 122-01-PLAN.md — TDD: completion gate says "dropped (reason)" for prune/no-arr removals, "cleared" only for proof-based release (LOG-02)
- [x] 122-02-PLAN.md — TDD: webhook/controller/config handlers and rate_limit log under the app logger; D-14 secret review (LOG-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 122-03-PLAN.md — Phase gate (suite, ruff, RED-first, scope) and PR with CI green (owner go-ahead to push)

**Wave 3**

- [x] 122-04-PLAN.md — Owner go-ahead to merge; `:dev` digest of the merge commit pinned on `seedsyncarr-test`; teardown/webhook harness; LOG-01 live

**Wave 4**

- [x] 122-05-PLAN.md — SAFE-01 import: Waiting hold + one-shot release, early credit, deferral/revalidation, arm-on-commit and 300 s auto-delete (D-06(c) FAIL found; gap closed by 122-10..12)

**Wave 5-7** *(gap closure for 122-05 D-06(c); same PR #134)*

- [x] 122-10-PLAN.md — TDD: keep a revalidated pending import notice between transfer end and commit (D-06(c) fix) + local gates
- [x] 122-11-PLAN.md — Push fix to PR #134, CI green, new staging digest as DEV_PIN, re-pin sandbox, LOG-01 recheck
- [x] 122-12-PLAN.md — Rerun D-06 (c) on the fixed build plus (e)/(a)/(b) regression and a (c) repeat

**Wave 8-10** *(sequential, sandbox only, on the fixed build)*

- [x] 122-06-PLAN.md — SAFE-01 restart persistence of early credit
- [x] 122-07-PLAN.md — SAFE-01 extraction staging (~1 GB multi-part RAR) and auto-delete re-arm
- [x] 122-08-PLAN.md — Sandbox Sonarr key rotation decision, restore sandbox to 1.7.6 pin, SAFE-01 verdict (owner review)

**Wave 11**

- [x] 122-09-PLAN.md — SAFE-02: reconcile both incident records, owner cleanup checklist, close rule, deferred C-G to backlog

**Wave 12-15** *(gap closure for verification CR-01, WR-01..03; owner decision 2026-10-23; same PR #134)*

- [ ] 122-13-PLAN.md — TDD: bound post-transfer pending-notice window to 120 s with a local copy, discard on stop/delete-local, accurate credit reason (WR-02, WR-03)
- [ ] 122-14-PLAN.md — TDD: never log the Arr API key from Test Connection; status rate-limit warning on the app logger, rate_limit logger required (CR-01, WR-01)
- [ ] 122-15-PLAN.md — Phase gates, push to PR #134, CI green, new staging digest as DEV_PIN
- [ ] 122-16-PLAN.md — Re-pin sandbox; LOG-01/WR-01 live; D-06(c) rerun with (e)/(a)/(b) regression and live WR-02 stop check (D-03 checkpoint)
- [ ] 122-17-PLAN.md — Rerun evidence, restore sandbox to 1.7.6 pin, SAFE-01 gap-cycle-2 verdict (owner review)

### Phase 123: Startup and Shutdown Lifecycle

**Goal**: A failure partway through startup or cleanup never leaves started children running or skips the cleanup of later components
**Depends on**: Phase 122 (sequencing only; disjoint code paths)
**Requirements**: LIFE-01, LIFE-02
**Success Criteria** (what must be TRUE):

  1. With a failure injected into the startup of the scanner or another component after some children have started, the already-started children are stopped/cleaned up and the failure still surfaces (test fails before the fix, passes after)
  2. With a failure injected into the cleanup of one component, cleanup is still attempted for every remaining component and the first failure is logged, not swallowed (test fails before the fix, passes after)
  3. The existing per-component controller cleanup, the auto-delete shutdown guards (`threading.Event` in-flight guard under `__auto_delete_lock`) and the established lock ordering are unchanged, and their existing tests stay green
  4. A clean startup and a clean shutdown behave exactly as before (no new sleeps, no lifecycle-framework rewrite)

**Plans**: TBD

### Phase 124: Model-Stream Overflow Recovery

**Goal**: A slow SSE client that loses incremental model events converges back to the server's current state without unbounded buffering
**Depends on**: Phase 123 (sequencing only; disjoint code paths)
**Requirements**: STRM-01, STRM-02
**Success Criteria** (what must be TRUE):

  1. Overflow is reproduced at the model-stream boundary (bounded `StreamQueue` dropping events for a stalled consumer) with a recorded, repeatable test or script, before any fix is proposed
  2. If reproduction shows an existing recovery guarantee (for example a fresh snapshot already follows a drop), that guarantee is recorded with evidence and STRM-02 closes with no code change
  3. Otherwise, after overflow the slow client's model matches the server's current state (fresh snapshot or reconnect — the smallest mechanism), demonstrated by a test that fails before and passes after
  4. Buffering stays bounded under a stalled consumer; producer atomicity alone is not accepted as the recovery mechanism, and there is no event-bus redesign

**Plans**: TBD

### Phase 125: LAN Connection Tests

**Goal**: Test Connection works for the local Sonarr/Radarr addresses people actually use, without opening the test endpoint to arbitrary destinations
**Depends on**: Phase 124 (sequencing only; disjoint code paths)
**Requirements**: LAN-01, LAN-02
**Success Criteria** (what must be TRUE):

  1. Test Connection succeeds for a private-range IP (e.g. `192.168.x.x`, `10.x.x.x`, `172.16–31.x.x`) running Sonarr/Radarr, and for a Docker container or host name that resolves to a private address (the container-name failure recorded in Phase 120, D-02, is fixed), with regression tests for each representative case
  2. Cloud-metadata and link-local addresses (e.g. `169.254.169.254`), loopback-to-unexpected-port probes outside the allowed intent, and redirects to disallowed targets are still rejected with the same user-visible outcome as today, with regression tests
  3. The new acceptance is limited to the configured Sonarr/Radarr test-connection path; no other outbound request path is relaxed
  4. The change is noted as the minor-version driver (behavior change) in the 1.8.0 release notes

**Plans**: TBD

### Phase 126: Release 1.8.0

**Goal**: 1.8.0 is published, smoke-tested by exact digest, and running on NAS production with a confirmed successful scan
**Depends on**: Phases 121, 122, 123, 124, 125 (all milestone work complete)
**Requirements**: REL-05, REL-06
**Success Criteria** (what must be TRUE):

  1. Before the version bump/tag, open Dependabot alerts and PRs are reviewed and listed for the owner in plain terms; runtime/shipped fixes are rolled into 1.8.0, dev-only ones only if cheap; backlog 999.4 (braces/karma advisory, PRs #128/#125/#117) is rechecked as part of this review and its outcome recorded
  2. Full Python suite, whole-tree ruff, Angular tests and release CI are green on the release commit; tag `v1.8.0` publishes the image to GHCR, the GitHub release and PyPI, with CHANGELOG and release notes (including the LAN test behavior change and a rollback runbook)
  3. The published image is smoke-tested on the NAS sandbox by exact digest: restart, a real transfer, Sonarr/Radarr integration and cleanup checks pass
  4. NAS production compose is pinned to `:1.8.0@sha256:…` (the same digest; never `:dev`, never a local build — NAS local build is blocked by QEMU) and a successful post-deploy scan confirms recovery, with the owner's confirmation recorded

**Plans**: TBD

#### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 121. Credential Forwarding | 3/3 | Complete   | 2026-10-21 |
| 122. Safety Acceptance and Logging Fixes | 12/17 | In Progress|  |
| 123. Startup and Shutdown Lifecycle | 0/TBD | Not started | - |
| 124. Model-Stream Overflow Recovery | 0/TBD | Not started | - |
| 125. LAN Connection Tests | 0/TBD | Not started | - |
| 126. Release 1.8.0 | 0/TBD | Not started | - |

**Done when:** each scoped item has its stated evidence, targeted regressions and applicable existing checks pass, and the built image passes relevant restart, transfer, integration and cleanup smoke checks and is deployed to NAS production by digest. Record residual limitations explicitly. Conditional investigations in the Backlog are not completion gates unless evidence justifies explicitly promoting a bounded fix.

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

### 999.5: Move Sonarr integration to API v5

**Scope:** Sonarr 5 lists the v3 API as deprecated (still served as of 5.0.0.2701). Move SeedSyncarr's two Sonarr API calls (`system/status` connection test, `queue/details` completion evidence; the webhook payload is version-independent) to `/api/v5` when Sonarr 4 support can be dropped, or with version detection that keeps v3 for Sonarr 4. Note the v5 queue model differences: one tracked item can cover multiple episodes (`episodeIds`/`episodes` lists), `timeLeft` casing, and `includeSubresources`. Activate when Sonarr announces v3 removal, Sonarr 5 goes stable and prod upgrades, or v1.7.7 finds a v3 gap. Radarr unaffected. Not a Reliability gate.

## Following milestone: Performance and Usability (conditional)

**Activation:** v1.8.0 Reliability is complete and measurements or recurring user friction justify a bounded follow-up. If no material opportunity is demonstrated, defer this milestone.

**Goal:** Remove demonstrated unnecessary work and remaining setup friction without changing the transfer architecture.

1. [ ] **Measured UI/webhook efficiency.** Select only improvements supported by the backlog investigations, with agreed baseline and before/after targets.
2. [ ] **Setup/configuration documentation.** Correct concrete discrepancies not already fixed in Phase 119 or alongside Reliability work.

Credential forwarding and LAN connection tests belong to v1.8.0 Reliability, not this milestone.

**Done when:** selected improvements meet their agreed before/after targets, relevant integration/UI checks pass, and affected documentation matches delivered behavior. Scope, phase numbers and release version are assigned only after activation.

## Future milestone: UI Redesign (pipeline-first)

**Activation:** after v1.8.0 Reliability; set its order relative to Performance and Usability when activated. Not active; no phases or version assigned.

**Goal:** Make the import-driven safe-delete pipeline visible: show each file's lifecycle (seedbox → local → imported → local copy cleaned up), surface problems with per-row actions, regroup Settings around the pipeline, and add phone and iPhone Duo layouts. Full scope, backend dependencies, component change list and finish line: [UI Redesign brief](backlog/UI-REDESIGN.md). Design canvas linked there.

## Operator follow-ups (not development milestones)

- [ ] Confirm credential rotation from the 1.7.6 checklist is complete.
- [x] Confirm one-time Done-group cleanup is complete. Owner confirmed 2026-10-23 (Phase 122-09, verbatim "All confirmed"); `done-group-no-auto-delete.md` and `extract-staging-autodel-rearm.md` both resolved and moved to `.planning/debug/resolved/`.
- [ ] Rotate the sandbox `sonarr-v5` Sonarr API key (exposed once in a Phase 122 research-session tool transcript, never written to a repo file; test Sonarr only, not production). Owner declined rotation during 122-08, verbatim "I'll replace it myself later" (`owner-later`).

## Completed releases

- **1.7.4:** safety patch, Phases 116–118. [Archived roadmap](milestones/v1.7.4-ROADMAP.md).
- **v1.7.7 (no release):** Sonarr 5.0.0.2701 compatibility verified on the sandbox and pinned in CI, Phase 120. [Archived roadmap](milestones/v1.7.7-ROADMAP.md).
- **1.7.5 / 1.7.6:** safety release and startup-secret fix, Phases 119/119.1. Records show 1.7.6 deployed to the NAS on 2026-10-15. [Archived audit](milestones/v1.7.5-MILESTONE-AUDIT.md). The browser checks passed 2026-10-18; the extraction/import checks are Phase 122 (SAFE-01).

## Planning boundaries

Retain LFTP and the existing architecture. Keep changes small and supported by demonstrated behavior. No blanket phase-directory cleanup. Routine dependency/test cleanup is tracked in [maintenance](backlog/MAINTENANCE.md), not as its own milestone.

[Earlier roadmap and closed decisions](backlog/archive/2026-10-18/README.md) are preserved outside this active work list.
