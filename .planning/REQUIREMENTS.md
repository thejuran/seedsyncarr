# Requirements: SeedSyncarr — v1.7.5 Safety Release

**Defined:** 2026-10-14
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.7.5 Requirements

Requirements for the 1.7.5 safety release. All map to Phase 119.

### Transfer State

- [ ] **XFER-06**: After an LFTP status command times out, SeedSyncarr treats transfer status as unavailable until the command stream is verifiably resynchronized; a delayed prompt or stale output can never become a trusted empty job list, so active and submitted-transfer protection stays in force. Normal status resumes after verified synchronization. *(promotes backlog 999.2)*

### Auto-Delete

- [ ] **DEL-01**: A pending auto-delete timer cannot delete a transfer that was submitted but not yet observed in transfer status; it defers and can safely retry once transfer status is successfully observed (the job need not appear active if it already finished) and the existing deletion guards pass. Covered by a regression combining the timer with unavailable status and a submitted-unobserved root. *(promotes backlog 999.3)*

### Import Safety

- [ ] **IMP-01**: An incomplete or unverified copy of a seedbox file is never exposed at a path Sonarr/Radarr can import from — including during transfer, retries, crashes, and restart recovery. A copy becomes importable only after the completion checks pass; a recheck immediately before marking the copy complete is not sufficient on its own. *(Obsession incident, 2026-10-13)*
- [ ] **IMP-02**: Completion is established from reliable evidence; stable size and modification time alone are insufficient. The release is identified reliably in the Sonarr/Radarr download queue, using queue/API semantics verified during planning. An unavailable API, an ambiguous queue match, or a missing queue entry each mean completion remains unproven: SeedSyncarr holds and retries visibly, and elapsed time never grants completion. *(Obsession incident)*
  - **Scope of enforcement (owner-approved 2026-10-14):** verification applies when Sonarr or Radarr integration is enabled. An unavailable service holds an item only when no other configured service provides sufficient completion evidence (strong identity match + completed) for that release. With both integrations disabled, stability-based automatic syncing is retained as a documented compatibility exception — it cannot prove the seedbox download is complete, and disabling integration does not prove no external app watches the folder. Temp-file transfer (incomplete copies hidden until copying finishes) applies in both modes.
  - **Explicit exception (owner-approved 2026-10-14):** the user may deliberately release a held item after confirming "Completion could not be verified. Transfer and release this item anyway?"; the approval covers only that one transfer attempt. Normal automatic transfers keep the strict IMP-01/IMP-02 checks.
- [ ] **IMP-03**: An import notice for a uniquely identified, fully transferred episode is credited and persisted while sibling episodes are still transferring, and the credit survives a restart. That credit alone can never authorize whole-folder deletion: deletion requires both a complete transfer of the folder and import coverage of every required video. Ambiguous-filename protections still reject unsafe matches. *(Days of Hope incident, 2026-10-09)*

### Release

- [x] **REL-02**: The 1.7.5 built distributions have valid member paths, pass packaging checks, install successfully in a clean environment, and publish to PyPI. Dependabot #93 is evaluated only as relevant to this packaging repair.
- [ ] **REL-03**: 1.7.5 ships through the established Docker/GitHub/PyPI process. Each targeted regression fails before its fix and passes after; the full Python suite, whole-tree Ruff, and release CI gates pass. The release image passes smoke checks for startup, a real transfer, import visibility and webhook handling, automatic cleanup, settings persistence, and restart. The tested image is verified on the NAS, including a successful scan after any startup scanner error; any other startup error needs its own resolution before release.

### Startup log hygiene (Phase 119.1)

- [ ] **SEC-01**: The container does not print configuration secrets (seedbox password, Sonarr/Radarr API keys, webhook secret, api_token, any secret-marked setting) to its stdout/container log at startup or on settings reload; non-secret startup diagnostics remain. Regression test fails before the fix.
- [ ] **REL-04**: 1.7.6 ships through the 1.7.5 gates (release PR CI green, tag publish Docker/GitHub/PyPI, smoke on the exact digest incl. no-secrets-in-log) and is deployed to the NAS production container by digest; the owner is reminded to rotate the seedbox password and both arr API keys.

## Future Requirements

Deferred to the Reliability milestone (Phase 120+): import/cleanup recovery across scan timing and restarts, shutdown/resource cleanup, bounded scanner-result buffering, useful memory diagnostics.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Transfer-engine replacement | Patch release; fixes stay within the existing LFTP pipeline |
| Broad path-aware import redesign | Import changes limited to what IMP-01..03 need to stop incomplete imports and incorrect cleanup |
| Broad refactor, UI features, unrelated dependency churn | Patch scope |
| Backlog 999.1 payload-size evidence | Stays deferred as defense in depth; payload-size evidence alone would not satisfy the new completion requirements |
| Reliability milestone work | Next milestone, starting Phase 120 |

## Traceability

| Requirement | Phase | Plan grouping | Status |
|-------------|-------|---------------|--------|
| XFER-06 | Phase 119 | — | Pending |
| DEL-01 | Phase 119 | — | Pending |
| IMP-01 | Phase 119 | Incomplete-import plan (with IMP-02), own regression tests | Pending |
| IMP-02 | Phase 119 | Incomplete-import plan (with IMP-01), own regression tests | Pending |
| IMP-03 | Phase 119 | Early-episode-credit plan, own regression tests | Pending |
| REL-02 | Phase 119 | 119-10 | Complete |
| REL-03 | Phase 119 (NAS portion → 119.1) | — | Pending |
| SEC-01 | Phase 119.1 | — | Pending |
| REL-04 | Phase 119.1 | — | Pending |

**Coverage:**
- v1.7.5 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-14*
*Last updated: 2026-10-14 after owner approval*
