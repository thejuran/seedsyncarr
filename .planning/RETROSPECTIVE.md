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

## Milestone: v1.2.0 — Test & Quality Hardening

**Shipped:** 2026-04-28
**Phases:** 10 | **Plans:** 23

### What Was Built
- Fixed 19 Python test defects (2 critical false-coverage, 8 warning, 9 medium) across 4 phases
- Fixed 7 Angular test issues (subscription leaks, fakeAsync, double-cast, optional chaining)
- Fixed 9 E2E test + 5 infrastructure issues (Playwright APIs, CSP enforcement, arm64 locale, Docker health)
- Hardened CI (least-privilege permissions, SHA-pinned actions, release dependency chain, Docker build cache)
- Hardened Docker test containers (SSH key-only auth, non-root sshd, ephemeral keys, no hardcoded passwords)
- Filled 6 test coverage gaps (SSE streaming, Logs E2E, Settings E2E, webhook integration, DeleteRemoteProcess, ActiveScanner)
- Added rate limiting to all mutable HTTP endpoints via reusable sliding-window decorator
- Tightened Semgrep rules, eliminating 628 false positives

### What Worked
- The v1.1.2 audit milestone identified exactly the right findings — this milestone executed cleanly against those findings with no scope surprises
- Three-layer parallelism (Python / Angular / E2E+CI independently) allowed efficient phase sequencing
- WSGI iterator harness pattern (Phase 94) unblocked SSE streaming tests that had been skipped since the test suite was written
- TDD approach for rate limiter (Phase 96) — failing tests first, then implementation — caught edge cases early
- Code review after each phase caught real issues (mock time in flaky test, dead mock setup, unsafe afterEach)

### What Was Inefficient
- REQUIREMENTS.md checkbox drift — 12 checkboxes stayed unchecked despite the work being done; had to bulk-update at milestone close
- Summary file one-liner extraction failed for many phases — inconsistent frontmatter format caused garbled MILESTONES.md entry (had to rewrite manually)
- Verification files marked `human_needed` for runtime checks (Docker, Karma) that can't be automated — these accumulate as false-positive gaps in the audit
- The milestone audit was run mid-milestone (at Phase 92) and found 28 gaps — all of which were simply not-yet-executed phases, not real gaps

### Patterns Established
- Closure-based sliding-window rate limiter as the standard pattern for HTTP endpoint protection
- WSGI iterator harness (`wsgi_stream.py`) as the pattern for testing Bottle streaming responses without HTTP
- `helpers.py` module for shared test utilities (replacing conftest fixture scope issues)
- Ephemeral SSH key generation at Docker build time as the standard for test container auth

### Key Lessons
1. Quality-only milestones (no new features) ship faster than mixed milestones — 5 days for 68 items across 10 phases
2. Verification `human_needed` status should not block milestone close — if CI passes, the runtime checks are implicitly satisfied
3. REQUIREMENTS.md checkboxes should be updated at plan completion, not milestone close — prevents the stale-checkbox cleanup step
4. The v1.1.2 audit → v1.2.0 fix pipeline worked well as a two-milestone pattern: audit identifies, hardening fixes

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.2.0 | 10 | 23 | Quality-only hardening; audit→fix pipeline; 5-day execution |
| v1.1.2 | 4 | 6 | Audit-only milestone; research-first per layer |
| v1.1.1 | 8 | 26 | Cleanup sweep; deferred E2E + UAT from v1.1.0 |
| v1.1.0 | 12 | 30 | Full UI redesign with AIDesigner artifacts |

### Cumulative Quality

| Milestone | Python Tests | Angular Tests | E2E Specs | Python Coverage |
|-----------|-------------|---------------|-----------|-----------------|
| v1.2.0 | 1,200+ | 599 | 45+ | 84% (fail_under enforced) |
| v1.1.2 | 1,262 | 599 | 37 | 85.05% |
| v1.1.1 | 1,262 | 599 | 37 | 85.05% |
| v1.1.0 | 1,134 | 552 | 22 | 84% |

### Top Lessons (Verified Across Milestones)

1. Test cleanup happens naturally during feature work — dedicated audit milestones confirm rather than fix
2. E2E harness configuration is a recurring source of subtle CI failures (autoqueue, arm64 rar, CSP)
3. Quality-only milestones execute faster than mixed milestones — clear scope, no feature drift
4. REQUIREMENTS.md checkboxes should be updated at plan completion, not deferred to milestone close
