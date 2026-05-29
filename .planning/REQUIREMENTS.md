# Requirements: SeedSyncarr — v1.3.0 Test Coverage Gaps

**Defined:** 2026-05-28
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1 Requirements

Requirements for milestone v1.3.0. Source: `.planning/codebase/CONCERNS.md` (Test Coverage Gaps, audited 2026-05-26) and the design spec `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md`.

**Tier policy:** Medium-priority gaps get full path coverage (every documented branch, every realistic input class, end-to-end where the gap concerns an integration). Low-priority gaps get one targeted regression test that would have caught the documented risk.

**Trivial-fix policy:** When a test reveals a bug, the fix lands in the same plan (red test commit → green fix commit) **only if** ≤10 net non-blank/non-comment lines, no public-API change, and no observable-behavior change. Otherwise the bug is deferred to v1.4.0 with a one-line entry in STATE.md referencing the documenting test.

### Medium-Priority Coverage (full path)

- [ ] **COVMED-01**: `MultiprocessingLogger` listener-thread shutdown semantics are covered — handler-raises path, `propagate_exception()` re-raise, inner-loop `queue.Empty` non-termination, clean sentinel shutdown (`src/python/common/multiprocessing_logger.py:67-86`)
- [ ] **COVMED-02**: SSRF `_validate_url` covers IPv6 and reserved ranges — IPv4 private/loopback/link-local, IPv6 link-local/loopback/unique-local, IPv6-mapped IPv4, unresolved hostnames, valid public host (`src/python/web/handler/config.py:55-85`)
- [ ] **COVMED-03**: LFTP `JobStatusParser` `ValueError` recovery is covered — malformed line raises `LftpJobStatusParserError`, consecutive-error counter increments, `MAX_CONSECUTIVE_STATUS_ERRORS = 2` triggers recovery, counter resets on success (`src/python/lftp/lftp.py:11-13`, `src/python/lftp/job_status_parser.py:710-727`)
- [x] **COVMED-04**: `confirm-modal.service.ts` `escapeHtml` is covered end-to-end for XSS — every metacharacter (`&<>"'`), attacker payloads in title/body/button labels/classes, resulting `innerHTML` has no executable markup, no bypass call site (`src/angular/src/app/services/utils/confirm-modal.service.ts:33-40`)

### Low-Priority Coverage (targeted regression)

- [ ] **COVLOW-01**: Auto-delete honors a dry-run/enabled toggle flipped during a live Timer — in-method config re-read at `controller.py:838-851` respects the new value (no deletion when disabled; logs-only when dry-run) (`src/python/controller/controller.py:823-851`)
- [ ] **COVLOW-02**: `BoundedOrderedSet` eviction ordering after `touch` is covered — touched item retained, oldest non-touched evicted first (`src/python/common/bounded_ordered_set.py:91-105`)
- [ ] **COVLOW-03**: SSE timeout reconnection race has a regression test — documented race in stream-service registry exercised (`src/angular/src/app/services/base/stream-service.registry.ts:111-164`)
- [ ] **COVLOW-04**: `auth.interceptor.ts` token-missing / rotation path has a regression test (`src/angular/src/app/services/utils/auth.interceptor.ts:7-17`)

### CI Coverage Ratchet

- [ ] **RATCHET-01**: Coverage baseline captured before phase 97 (`.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`)
- [ ] **RATCHET-02**: `--cov-fail-under` (pytest) and Karma `coverageReporter.check.global` thresholds ratcheted up to the new bar after phase 100; before/after numbers recorded in ROADMAP.md and the v1.3.0 retro

## v2 Requirements

Deferred to future milestones (planned order per the design spec):

### v1.4.0 — Known Bugs + Security
- Larger fixes surfaced by v1.3.0 tests that exceed the trivial-fix window (>10 lines, public-API, or behavior change)
- The Known Bugs and Security Considerations buckets of CONCERNS.md

### Later milestones
- v1.5.0 — Frontend Deps + Dead Code
- v1.6.0 — Backend Architecture Refactor

## Out of Scope

Explicitly excluded from v1.3.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Other 8 CONCERNS.md buckets (tech debt, known bugs, security, performance, fragile areas, scaling, deps, missing features) | Future milestones in planned order (v1.4.0+) |
| Per-file coverage floors | Too brittle for a homelab-scale project — global thresholds only |
| DNS-rebind hardening for `_validate_url` | Existing inline comment marks it out-of-scope; the test documents the limitation but does not fix it |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COVMED-01 | Phase 97 | Pending |
| COVMED-02 | Phase 97 | Pending |
| COVMED-03 | Phase 97 | Pending |
| COVMED-04 | Phase 98 | Complete |
| COVLOW-01 | Phase 99 | Pending |
| COVLOW-02 | Phase 99 | Pending |
| COVLOW-03 | Phase 100 | Pending |
| COVLOW-04 | Phase 100 | Pending |
| RATCHET-01 | Phase 97 | Pending |
| RATCHET-02 | Phase 100 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 after initial definition*
