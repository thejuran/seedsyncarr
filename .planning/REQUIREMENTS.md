# Requirements: SeedSyncarr

**Defined:** 2026-10-21
**Milestone:** v1.8.0 Reliability (Phase 121+)
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.8.0 Requirements

Committed scope for this milestone. Each maps to exactly one roadmap phase. Fixes stay small and evidence-backed; existing implementation must be checked before planning any carried-forward fix.

### Credential Forwarding

- [x] **SEC-02**: The app token is attached only to requests to SeedSyncarr's own API; requests to any other destination (including the GitHub update check) carry no app token, with regression tests for both cases

### Safety Acceptance

- [x] **SAFE-01**: Extraction, import and auto-delete checks pass on a running build, with recorded evidence (completes the Phase 119 verification whose browser half passed 2026-10-18)
- [x] **SAFE-02**: The Done-group (`done-group-no-auto-delete`) and extract-staging (`extract-staging-autodel-rearm`) incident records each distinguish verified fixes from remaining operator cleanup; neither is closed solely because its code shipped

### Startup/Shutdown Lifecycle

- [x] **LIFE-01**: When startup of the scanner or another component fails partway, already-started children are cleaned up, demonstrated by an injected-failure test
- [x] **LIFE-02**: When cleanup of one component fails, cleanup is still attempted for the remaining components, demonstrated by an injected-failure test; existing per-component controller cleanup, auto-delete shutdown guards and lock ordering are preserved

### Model-Stream Overflow

- [ ] **STRM-01**: Overflow is reproduced at the model-stream boundary; if reproduction shows an existing recovery guarantee, it is recorded and the item closes with no code change
- [ ] **STRM-02**: After overflow, a slow client converges to the current server state, with bounded buffering (producer atomicity alone is not sufficient)

### LAN Connection Tests

- [ ] **LAN-01**: Test Connection succeeds for representative local Sonarr/Radarr configurations: private-range IP addresses and Docker container/host names resolving to private addresses
- [ ] **LAN-02**: Unintended destinations (e.g. cloud-metadata/link-local addresses, redirects to disallowed targets) remain rejected

### Logging

- [x] **LOG-01**: Webhook handler INFO messages (e.g. "webhook test event received") appear in the app log
- [x] **LOG-02**: The completion gate logs a distinct "dropped" message when a hold is pruned; "cleared" is logged only for a proof-based release

### Release

- [ ] **REL-05**: Open Dependabot alerts and PRs are reviewed before the version bump/tag; runtime/shipped fixes are rolled in, dev-only ones only if cheap (includes the 999.4 braces/karma recheck)
- [ ] **REL-06**: 1.8.0 is published (Docker/GitHub/PyPI), smoke-tested on the NAS by exact digest (restart, transfer, integration, cleanup), and deployed to NAS production by that digest, with a successful post-deploy scan confirming recovery

## Future Requirements

Deferred; tracked in ROADMAP.md Backlog, not in this milestone's phases. Promote only with demonstrated evidence and a bounded fix.

- Scanner buffering investigation (unbounded result queue under a stalled consumer)
- Residual import/restart recovery investigation
- Memory diagnostics (only as needed by the buffering investigation)
- UI and webhook efficiency measurement
- 999.5: Move Sonarr integration to API v5

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication redesign | SEC-02 only restricts where the existing token is attached |
| Lifecycle-framework rewrite | LIFE-01/02 repair specific gaps; existing controller cleanup is preserved |
| Event-bus redesign | STRM-02 needs the smallest recovery mechanism (e.g. fresh snapshot or reconnect) |
| Broad relaxation of outbound requests | LAN-01 permits intended configured LAN services only |
| Rebuilding Phase 119 import safeguards | Early credit, pending-notice revalidation and arm-on-commit already shipped |
| Replacing LFTP / transfer architecture | Planning boundary: retain existing architecture |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-02 | Phase 121 | Complete |
| SAFE-01 | Phase 122 | Complete |
| SAFE-02 | Phase 122 | Complete |
| LIFE-01 | Phase 123 | Complete |
| LIFE-02 | Phase 123 | Complete |
| STRM-01 | Phase 124 | Pending |
| STRM-02 | Phase 124 | Pending |
| LAN-01 | Phase 125 | Pending |
| LAN-02 | Phase 125 | Pending |
| LOG-01 | Phase 122 | Complete |
| LOG-02 | Phase 122 | Complete |
| REL-05 | Phase 126 | Pending |
| REL-06 | Phase 126 | Pending |

**Coverage:**
- v1.8.0 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-10-21*
*Last updated: 2026-10-21 after roadmap creation (Phases 121–126)*
