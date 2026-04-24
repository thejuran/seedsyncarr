---
phase: 85-e2e-test-audit
verified: 2026-04-24T22:45:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
deferred:
  - truth: "All remaining specs pass in the CI E2E harness on both amd64 and arm64"
    addressed_in: "Phase 86"
    evidence: "Phase 86 Success Criterion 1: 'CI pipeline completes green across all jobs: Python tests, Angular tests, E2E (amd64 + arm64), lint (ruff + eslint)'"
human_verification:
  - test: "Run full Playwright E2E harness in Docker CI environment"
    expected: "All 7 spec files pass; special attention to autoqueue.page.spec.ts (Pitfall 1 — btn-pattern-add may be disabled because autoqueue/enabled is not set in setup_seedsyncarr.sh)"
    why_human: "Runtime CI requires Docker stack (app + remote + configure containers + pre-built staging image); no local E2E run path exists without this stack"
---

# Phase 85: E2E Test Audit Verification Report

**Phase Goal:** The Playwright E2E suite contains only specs that verify distinct, current user-facing behaviors with no redundant coverage
**Verified:** 2026-04-24T22:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every E2E spec file has been independently cross-referenced against live Angular routes and selectors | VERIFIED | All 19 CSS selectors across 7 spec files grepped against Angular HTML templates — every selector found at exact line numbers matching SUMMARY claims; routes.ts confirms dashboard, settings, logs, about, and root redirect |
| 2 | The staleness audit produces an explicit per-file verdict (LIVE or STALE) for all 7 spec files | VERIFIED | 85-01-SUMMARY.md "Detailed Per-File Verdicts" table contains all 7 spec files with LIVE verdict; all counts match actual test() calls (3+2+1+1+3+1+26=37) |
| 3 | Zero stale specs exist — therefore zero removals are made | VERIFIED | `git diff --name-only src/e2e/` returns empty; `git status --short src/e2e/` returns only untracked package-lock.json (not a spec file); all 7 spec files present and unmodified |
| 4 | The CSP canary spec and all v1.1.1 selection/filter/URL-roundtrip dashboard specs remain in place | VERIFIED | csp-canary.spec.ts (25 lines, real CSP injection logic, 1 test); dashboard.page.spec.ts (562 lines, 26 named tests including UAT-01 selection and UAT-02 filter/URL-roundtrip); both marked MUST KEEP in SUMMARY |
| 5 | The autoqueue.page.spec.ts Pitfall 1 caveat (disabled button in CI harness) is documented | VERIFIED | setup_seedsyncarr.sh confirmed to set only `autoqueue/patterns_only/true` with no `autoqueue/enabled/true` line; settings-page.component.ts confirms autoqueueEnabled initializes to false (line 81); btn-pattern-add has `[disabled]="!(commandsEnabled && newPattern && autoqueueEnabled && patternsOnly)"` at line 237; @if guard at line 206 hides pattern section when autoqueueEnabled is falsy — all documented in SUMMARY Caveat 1 |
| 6 | The Logs page coverage gap is documented as out-of-scope | VERIFIED | Paths.LOGS = '/logs' confirmed in src/e2e/urls.ts; routes.ts confirms path "logs" exists; no logs.page.spec.ts exists on disk; SUMMARY Gap 1 documents as coverage gap, out of scope per audit mandate |

**Score:** 6/6 truths verified

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | All remaining specs pass in the CI E2E harness on both amd64 and arm64 (Roadmap SC2) | Phase 86 | Phase 86 Success Criterion 1: "CI pipeline completes green across all jobs: Python tests, Angular tests, E2E (amd64 + arm64), lint (ruff + eslint)" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/85-e2e-test-audit/85-01-SUMMARY.md` | E2E staleness audit result with per-file verdicts, zero-removal inventory, caveats, and verification evidence | VERIFIED | File exists (236 lines); contains "Removal Inventory" section; contains per-file verdict table for all 7 specs; contains E2E-01/E2E-02/E2E-03 evidence; contains autoqueue Pitfall 1 caveat; contains Logs page gap; contains csp-canary MUST KEEP and dashboard MUST KEEP notations |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| 85-01-SUMMARY.md | 86-final-validation | Phase 86 reads E2E audit result to confirm CI green | VERIFIED | SUMMARY frontmatter `affects: [86-final-validation]`; Requirements table contains "E2E-01 | ... | COMPLETE" at line 186 matching pattern `E2E-01.*COMPLETE`; Phase 86 ROADMAP entry lists Phase 85 as dependency |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces only a planning artifact (SUMMARY.md). No dynamic data rendering or API wiring.

### Behavioral Spot-Checks

Step 7b: SKIPPED — this is a read-only audit phase. The only "runnable" check is the E2E harness itself which requires Docker CI (see Human Verification Required below).

Programmatically verifiable acceptance criteria were all checked directly:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| pattern-section selector in live template | `grep -rn "pattern-section" settings-page.component.html` | Found at line 204 | PASS |
| transfer-table selector in live template | `grep -rn "transfer-table" transfer-table.component.html` | Found at line 142 | PASS |
| version-badge selector in live template | `grep -rn "version-badge" about-page.component.html` | Found at line 13 | PASS |
| top-nav selector in live template | `grep -rn "top-nav" app.component.html` | Found at line 1 | PASS |
| Routes dashboard/settings/logs/about in routes.ts | `grep -n "path" routes.ts` | All 4 routes + root redirect found | PASS |
| csp-listener.ts fixture exists | `ls src/e2e/tests/fixtures/csp-listener.ts` | Exists | PASS |
| seed-state.ts fixture exists | `ls src/e2e/tests/fixtures/seed-state.ts` | Exists | PASS |
| Zero E2E modifications (git diff) | `git diff --name-only src/e2e/` | Empty | PASS |
| Zero E2E modifications (git status) | `git status --short src/e2e/` | Only untracked package-lock.json | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| E2E-01 | 85-01-PLAN.md | Identify Playwright E2E specs with redundant or stale coverage | SATISFIED | Selector cross-check of all 7 spec files confirms zero stale specs; SUMMARY contains full evidence table with per-selector findings |
| E2E-02 | 85-01-PLAN.md | Remove identified redundant E2E specs | SATISFIED | Zero removals made (zero stale specs found); git confirms no E2E files modified or deleted |
| E2E-03 | 85-01-PLAN.md | Verify all remaining E2E specs pass | PARTIAL (static only) | Static analysis complete — all selectors live; runtime verification deferred to Phase 86 per Docker-only constraint; routed to Human Verification below |

**Orphaned requirements check:** REQUIREMENTS.md maps E2E-01, E2E-02, E2E-03 to Phase 85 — all three appear in the plan's `requirements` field. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

No anti-patterns found. The only file created/modified in this phase is `85-01-SUMMARY.md`, a planning document with no stubs or placeholder code.

### Human Verification Required

#### 1. E2E Harness Runtime Pass

**Test:** In the Docker CI environment, run `make run-tests-e2e SEEDSYNCARR_ARCH=amd64` (and arm64 variant). Observe all 7 spec files.

**Expected:** All 37 tests pass. Pay special attention to `autoqueue.page.spec.ts` — the three tests that add/remove patterns will click `.btn-pattern-add`. Because `setup_seedsyncarr.sh` sets `autoqueue/patterns_only/true` but NOT `autoqueue/enabled/true`, the button has `[disabled]="!(commandsEnabled && newPattern && autoqueueEnabled && patternsOnly)"` and the `@if (autoqueueEnabled && patternsOnly)` guard hides the pattern section entirely when `autoqueueEnabled` is falsy. If these tests time out, the fix is a harness configuration bug in Phase 86 (add `curl .../autoqueue/enabled/true` to setup_seedsyncarr.sh), not a Phase 85 staleness issue.

**Why human:** The E2E harness requires Docker Compose with app + remote + configure containers and a pre-built staging image. There is no local-only execution path for Playwright E2E tests in this project.

### Gaps Summary

No programmatic gaps found. All 6 plan must-haves verified against the actual codebase.

The only open item is the runtime CI pass (Roadmap Success Criterion 2: "All remaining specs pass in the CI E2E harness on both amd64 and arm64"), which is explicitly deferred to Phase 86 in the roadmap and cannot be verified without the Docker CI stack.

Phase 85 goal achieved at the static analysis level: the E2E suite contains only specs that verify distinct, current user-facing behaviors (zero stale selectors, zero redundant removals, caveats documented). Runtime confirmation is Phase 86's responsibility.

---

_Verified: 2026-04-24T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
