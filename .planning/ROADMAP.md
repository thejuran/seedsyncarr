# Roadmap: SeedSyncarr

Updated 2026-10-18. Two future milestones remain. Detailed phase plans and release versions are not assigned yet; the next phase number is 120. Existing implementation must be checked before planning any carried-forward fix.

## Milestones

- ✅ v1.7.4 Safety Patch -- Phases 116–118 (shipped 2026-10-09)
- ✅ v1.7.5 Safety Release -- Phases 119 and 119.1; includes release 1.7.6 (shipped 2026-10-15)

Between milestones: no active milestone or phase. Future milestone names and scope are below; versions remain unassigned. Earlier release history remains in STATE.md and milestone archives.

## Next milestone: Reliability

**Goal:** Restrict credential forwarding, close outstanding safety acceptance checks, and repair demonstrated lifecycle and integration failures with small changes.

**Ordered scope (priorities, not assigned phase numbers):**

1. [ ] **Restrict credential forwarding.** The current HTTP interceptor attaches the configured app token to all requests, including the GitHub update-check request. Limit attachment to intended app requests. **Done when:** internal requests retain authentication and external requests receive no app token, with regression coverage for both. Current-code evidence confirms attachment; actual network exposure has not been tested. No authentication redesign.
2. [ ] **Close safety acceptance checks.** Exercise the Waiting badge/reason and manual-release OK/Cancel paths, plus extract-staging/import/auto-delete behavior. Reconcile Done-group and extraction debug records with shipped fixes before proposing more code. **Done when:** browser evidence confirms the hold and confirmation behavior (Cancel preserves the hold), extraction/import checks pass, and incident records distinguish verified fixes from remaining operator cleanup. Do not close incidents solely because code shipped. *Progress 2026-10-18:* browser half evidenced on 1.7.6 (Waiting badge/reason, manual-release Cancel keeps the hold, Release transfers once; `119-HUMAN-UAT.md`). Extraction/import checks and incident reconciliation remain.
3. [ ] **Repair remaining shutdown gaps.** Controller cleanup already isolates failures between components; preserve it. Focus on partial scanner/component startup and cleanup that can skip later children when an earlier operation fails. **Done when:** injected startup and cleanup failures demonstrate cleanup of started children and continued cleanup attempts for remaining components. Preserve auto-delete shutdown guards and lock ordering; no lifecycle-framework rewrite.
4. [ ] **Recover model state after stream overflow.** StreamQueue is already bounded, but discarded incremental model events can leave a slow client out of sync. First reproduce overflow at the model-stream boundary; then implement the smallest recovery mechanism, such as a fresh snapshot or reconnect. **Done when:** a slow client converges to current server state after overflow with bounded buffering. Producer atomicity alone is not sufficient. If reproduction establishes an existing recovery guarantee, record it and close without redundant changes; no event-bus redesign.
5. [ ] **Support intended LAN connection tests.** Current validation rejects private addresses used by normal local Sonarr/Radarr installations. Permit intended configured LAN services while retaining appropriate destination and redirect restrictions. **Done when:** representative LAN configurations pass and unintended destinations remain rejected. No broad relaxation of arbitrary outbound requests.

**Done when:** each scoped item has its stated evidence, targeted regressions and applicable existing checks pass, and the built image passes relevant restart, transfer, integration and cleanup smoke checks. Record residual limitations explicitly. Conditional investigations below are not completion gates unless evidence justifies explicitly promoting a bounded fix.

**Sequence:** begin at Phase 120 when the milestone is activated. Detailed plans and release versions remain unassigned. This roadmap update does not activate the milestone or start implementation.

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
- **1.7.5 / 1.7.6:** safety release and startup-secret fix, Phases 119/119.1. Records show 1.7.6 deployed to the NAS on 2026-10-15. [Archived audit](milestones/v1.7.5-MILESTONE-AUDIT.md). The remaining browser checks are assigned above.

## Planning boundaries

Retain LFTP and the existing architecture. Keep changes small and supported by demonstrated behavior. No blanket phase-directory cleanup. Routine dependency/test cleanup is tracked in [maintenance](backlog/MAINTENANCE.md), not as its own milestone.

[Earlier roadmap and closed decisions](backlog/archive/2026-10-18/README.md) are preserved outside this active work list.
