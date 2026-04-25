# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1.2 — Test Suite Audit

**Shipped:** 2026-04-24
**Phases:** 4 | **Plans:** 6

### What Was Built
- Independent staleness audit of all three test layers (72 Python files, 40 Angular specs, 7 E2E specs)
- Zero stale tests found across all layers -- prior milestones' rebrand and redesign had already cleaned them
- HttpClientTestingModule migrated to provideHttpClient() in 6 Angular spec files
- E2E harness autoqueue config fixed, coverage baselines documented
- Full CI green: 1262 Python, 599 Angular, 37 E2E on amd64+arm64

### What Worked
- Layer-by-layer sequencing (Python -> Angular -> E2E -> Validation) gave clear coverage impact visibility before moving on
- Research phase per layer surfaced the audit methodology before planning, preventing wasted effort
- The "zero stale" finding validated that the v1.0.0 rebrand and v1.1.0 redesign milestones were thorough with test cleanup
- Code review (Phase 86) caught missing `set -euo pipefail` and `curl --fail` in the E2E harness script

### What Was Inefficient
- The milestone was scoped for removal work but found nothing to remove -- the audit confirmed health rather than performing cleanup
- Phase 86 missing VERIFICATION.md created a tech debt item that could have been avoided with a verify step
- REQUIREMENTS.md E2E checkboxes went stale despite the work being done -- traceability updates should happen at plan completion, not milestone close

### Patterns Established
- Coverage baselines should be documented in ROADMAP.md at milestone boundaries for historical tracking
- E2E harness configuration (setup_seedsyncarr.sh) needs `set -euo pipefail` and `curl -Sf` as standard practice

### Key Lessons
1. An audit milestone that confirms "everything is clean" is still valuable -- it provides documented confidence and coverage baselines
2. HttpClientTestingModule migration was a worthwhile opportunistic cleanup found during audit, even though it wasn't in the original scope
3. arm64 Unicode sort order variance (glibc locale differences) is a platform concern to monitor, not a test bug

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.1.2 | 4 | 6 | Audit-only milestone; research-first per layer |
| v1.1.1 | 8 | 26 | Cleanup sweep; deferred E2E + UAT from v1.1.0 |
| v1.1.0 | 12 | 30 | Full UI redesign with AIDesigner artifacts |

### Cumulative Quality

| Milestone | Python Tests | Angular Tests | E2E Specs | Python Coverage |
|-----------|-------------|---------------|-----------|-----------------|
| v1.1.2 | 1,262 | 599 | 37 | 85.05% |
| v1.1.1 | 1,262 | 599 | 37 | 85.05% |
| v1.1.0 | 1,134 | 552 | 22 | 84% |

### Top Lessons (Verified Across Milestones)

1. Test cleanup happens naturally during feature work -- dedicated audit milestones confirm rather than fix
2. E2E harness configuration is a recurring source of subtle CI failures (autoqueue, arm64 rar, CSP)
