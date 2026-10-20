# Roadmap: SeedSyncarr

Updated 2026-10-20. No milestone is active. v1.7.7 Sonarr 5 Compatibility closed 2026-10-20 (verified; no release needed). Reliability begins at Phase 121 when activated; its detailed phase plans and release version, and those of the milestone after it, are not assigned yet. Existing implementation must be checked before planning any carried-forward fix.

## Milestones

- ✅ v1.7.4 Safety Patch -- Phases 116–118 (shipped 2026-10-09)
- ✅ v1.7.5 Safety Release -- Phases 119 and 119.1; includes release 1.7.6 (shipped 2026-10-15)
- ✅ v1.7.7 Sonarr 5 Compatibility -- Phase 120 (closed 2026-10-20; verified, no release needed)

No active milestone; next is Reliability. Future milestone names and scope are below; their versions remain unassigned. Earlier release history remains in STATE.md and milestone archives.

<details>
<summary>✅ v1.7.7 Sonarr 5 Compatibility (Phase 120) — CLOSED 2026-10-20, verified; no release needed</summary>

- [x] Phase 120: Sonarr 5 Compatibility (6/6 plans) — completed 2026-10-20. [Archived roadmap](milestones/v1.7.7-ROADMAP.md)

</details>

## Next milestone: Reliability

**Goal:** Restrict credential forwarding, close outstanding safety acceptance checks, and repair demonstrated lifecycle and integration failures with small changes.

**Ordered scope (priorities, not assigned phase numbers):**

1. [ ] **Restrict credential forwarding.** The current HTTP interceptor attaches the configured app token to all requests, including the GitHub update-check request. Limit attachment to intended app requests. **Done when:** internal requests retain authentication and external requests receive no app token, with regression coverage for both. Current-code evidence confirms attachment; actual network exposure has not been tested. No authentication redesign.
2. [ ] **Close safety acceptance checks.** Exercise the Waiting badge/reason and manual-release OK/Cancel paths, plus extract-staging/import/auto-delete behavior. Reconcile Done-group and extraction debug records with shipped fixes before proposing more code. **Done when:** browser evidence confirms the hold and confirmation behavior (Cancel preserves the hold), extraction/import checks pass, and incident records distinguish verified fixes from remaining operator cleanup. Do not close incidents solely because code shipped. *Progress 2026-10-18:* browser half evidenced on 1.7.6 (Waiting badge/reason, manual-release Cancel keeps the hold, Release transfers once; `119-HUMAN-UAT.md`). Extraction/import checks and incident reconciliation remain.
3. [ ] **Repair remaining shutdown gaps.** Controller cleanup already isolates failures between components; preserve it. Focus on partial scanner/component startup and cleanup that can skip later children when an earlier operation fails. **Done when:** injected startup and cleanup failures demonstrate cleanup of started children and continued cleanup attempts for remaining components. Preserve auto-delete shutdown guards and lock ordering; no lifecycle-framework rewrite.
4. [ ] **Recover model state after stream overflow.** StreamQueue is already bounded, but discarded incremental model events can leave a slow client out of sync. First reproduce overflow at the model-stream boundary; then implement the smallest recovery mechanism, such as a fresh snapshot or reconnect. **Done when:** a slow client converges to current server state after overflow with bounded buffering. Producer atomicity alone is not sufficient. If reproduction establishes an existing recovery guarantee, record it and close without redundant changes; no event-bus redesign.
5. [ ] **Support intended LAN connection tests.** Current validation rejects private addresses used by normal local Sonarr/Radarr installations. Permit intended configured LAN services while retaining appropriate destination and redirect restrictions. **Done when:** representative LAN configurations pass and unintended destinations remain rejected. No broad relaxation of arbitrary outbound requests.

**Done when:** each scoped item has its stated evidence, targeted regressions and applicable existing checks pass, and the built image passes relevant restart, transfer, integration and cleanup smoke checks. Record residual limitations explicitly. Conditional investigations below are not completion gates unless evidence justifies explicitly promoting a bounded fix.

**Sequence:** begin at Phase 121 when the milestone is activated. Detailed plans and release versions remain unassigned. This roadmap update does not activate the milestone or start implementation.

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

**Scope:** Bounded maintenance side task, separate from milestone scope. recheck the recorded braces/karma dev-test advisory and related deferred PRs (#128/#125/#117), including current affected versions and runtime/build exposure. Apply the smallest supported fix if still relevant, with the affected build/test checks. Records classify it as dev/test-only; current advisory status has not been refreshed. This is not a separate milestone or a general test-runner rewrite, and is not automatically a Reliability completion gate. Escalate priority if current evidence establishes material exposure.

### 999.5: Move Sonarr integration to API v5

**Scope:** Sonarr 5 lists the v3 API as deprecated (still served as of 5.0.0.2701). Move SeedSyncarr's two Sonarr API calls (`system/status` connection test, `queue/details` completion evidence; the webhook payload is version-independent) to `/api/v5` when Sonarr 4 support can be dropped, or with version detection that keeps v3 for Sonarr 4. Note the v5 queue model differences: one tracked item can cover multiple episodes (`episodeIds`/`episodes` lists), `timeLeft` casing, and `includeSubresources`. Activate when Sonarr announces v3 removal, Sonarr 5 goes stable and prod upgrades, or v1.7.7 finds a v3 gap. Radarr unaffected. Not a Reliability gate.

## Following milestone: Performance and Usability (conditional)

**Activation:** Reliability is complete and measurements or recurring user friction justify a bounded follow-up. If no material opportunity is demonstrated, defer this milestone.

**Goal:** Remove demonstrated unnecessary work and remaining setup friction without changing the transfer architecture.

1. [ ] **Measured UI/webhook efficiency.** Select only improvements supported by the backlog investigations, with agreed baseline and before/after targets.
2. [ ] **Setup/configuration documentation.** Correct concrete discrepancies not already fixed in Phase 119 or alongside Reliability work.

Credential forwarding and LAN connection tests belong to Reliability, not this milestone.

**Done when:** selected improvements meet their agreed before/after targets, relevant integration/UI checks pass, and affected documentation matches delivered behavior. Scope, phase numbers and release version are assigned only after activation.

## Operator follow-ups (not development milestones)

- [ ] Confirm credential rotation from the 1.7.6 checklist is complete.
- [ ] Confirm one-time Done-group cleanup is complete. Do not mark the incident closed solely because its code fix shipped.

## Completed releases

- **1.7.4:** safety patch, Phases 116–118. [Archived roadmap](milestones/v1.7.4-ROADMAP.md).
- **v1.7.7 (no release):** Sonarr 5.0.0.2701 compatibility verified on the sandbox and pinned in CI, Phase 120. [Archived roadmap](milestones/v1.7.7-ROADMAP.md).
- **1.7.5 / 1.7.6:** safety release and startup-secret fix, Phases 119/119.1. Records show 1.7.6 deployed to the NAS on 2026-10-15. [Archived audit](milestones/v1.7.5-MILESTONE-AUDIT.md). The remaining browser checks are assigned above.

## Planning boundaries

Retain LFTP and the existing architecture. Keep changes small and supported by demonstrated behavior. No blanket phase-directory cleanup. Routine dependency/test cleanup is tracked in [maintenance](backlog/MAINTENANCE.md), not as its own milestone.

[Earlier roadmap and closed decisions](backlog/archive/2026-10-18/README.md) are preserved outside this active work list.
