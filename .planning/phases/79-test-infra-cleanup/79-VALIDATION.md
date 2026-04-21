---
phase: 79
slug: test-infra-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 79 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Full sampling map derived from 79-RESEARCH.md §8 "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Python framework** | `pytest` 9.0.3 (`src/python/pyproject.toml:67`) via Docker harness `seedsyncarr_test_python` |
| **E2E framework** | `@playwright/test` ^1.48.0 (`src/e2e/package.json:12`) |
| **Python config file** | `src/python/pyproject.toml` §[tool.pytest.ini_options] |
| **E2E config file** | `src/e2e/playwright.config.ts` (workers: 1, fullyParallel: false) |
| **Python quick run** | `make tests-python` (build) then `make run-tests-python` (execute) |
| **E2E quick run** | `make run-tests-e2e` |
| **CI evidence surface** | `.github/workflows/ci.yml:144` (D-20 precedent from Phase 77) |
| **Estimated Python runtime** | ~60 seconds |
| **Estimated E2E runtime** | ~90 seconds (26 existing dashboard tests + 6 other spec suites + canary) |

---

## Sampling Rate

- **After every task commit:** `make run-tests-python` for Plan 01; `cd src/e2e && npx playwright test <touched>.spec.ts` for Plan 02.
- **After every plan wave:** Full suite — `make run-tests-python` AND `make run-tests-e2e`.
- **Before `/gsd-verify-work`:** Both suites green in CI at `.github/workflows/ci.yml:144` with zero warning lines in stderr.
- **Max feedback latency:** ~90 seconds (E2E full suite is the longest single run).

---

## Per-Task Verification Map

> Populated by the planner; row template below. Every task that modifies code MUST have an automated command. Manual-only verifications go in the table below this one.

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 79-01-01 | 01 | 1 | TEST-01 | N/A (test infra) | integration | `make run-tests-python 2>&1 \| grep -Ec "pytest-cache\|could not create cache"` → 0 | ✅ | ⬜ pending |
| 79-01-02 | 01 | 1 | TEST-01 | N/A (test infra) | integration | `make run-tests-python 2>&1 \| grep -Ec "cgi.*deprecated"` → 0 | ✅ | ⬜ pending |
| 79-01-03 | 01 | 1 | TEST-01 | N/A (test infra) | static | `grep -c "cache_dir\|filterwarnings.*cgi" src/python/pyproject.toml` → 0 | ✅ | ⬜ pending |
| 79-02-01 | 02 | 1 | TEST-02 | N/A (test infra) | manual | Headed-mode devtools inspection — zero existing violations (R-1 pre-flight) | ✅ | ⬜ pending |
| 79-02-02 | 02 | 1 | TEST-02 | N/A (test infra) | unit | `test -f src/e2e/tests/fixtures/csp-listener.ts` | ✅ | ⬜ pending |
| 79-02-03 | 02 | 1 | TEST-02 | N/A (test infra) | integration | `grep -lc "from './fixtures/csp-listener'" src/e2e/tests/*.spec.ts \| wc -l` → 6 | ✅ | ⬜ pending |
| 79-02-04 | 02 | 1 | TEST-02 | N/A (test infra) | e2e | `cd src/e2e && npx playwright test csp-canary.spec.ts` exits 0 | ✅ | ⬜ pending |
| 79-02-05 | 02 | 1 | TEST-02 | N/A (test infra) | e2e | `make run-tests-e2e` exits 0 (all 7 suites green including canary) | ✅ | ⬜ pending |

*Planner may adjust task IDs and expand the table; the signals and thresholds above are locked by RESEARCH.md §8.*
*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Success Criteria Map

From ROADMAP.md §"Phase 79":

| SC | Behavior | Signal | Threshold | Verification Command |
|----|----------|--------|-----------|----------------------|
| 1a | Zero pytest-cache warnings | stderr lines matching `pytest-cache` / `could not create cache dir` | count == 0 | `make run-tests-python 2>&1 \| grep -Ec "pytest-cache\|could not create cache"` |
| 1b | Zero webob/cgi DeprecationWarnings | stderr lines matching `cgi.*deprecated` | count == 0 | `make run-tests-python 2>&1 \| grep -Ec "cgi.*deprecated"` |
| 1c | CI log reflects 1a+1b | GitHub Actions run at `.github/workflows/ci.yml:144` | Both grep counts zero in CI log | Manual CI log inspection (harness-as-evidence) |
| 2  | Shared fixture registered on 6 specs | Top-line import = `./fixtures/csp-listener` | 6/6 specs match | `grep -l "from './fixtures/csp-listener'" src/e2e/tests/*.spec.ts \| wc -l` → 6 |
| 3a | Seeded violation triggers listener | Canary spec passes | 1 canary test GREEN | `cd src/e2e && npx playwright test csp-canary.spec.ts` |
| 3b | Canary detects ≥1 violation | `cspViolations.length > 0` with `script-src` match | Length ≥ 1 | Internal canary assertion: `expect.poll(() => cspViolations.length).toBeGreaterThan(0)` |
| 4  | Existing specs stay green | All 6 existing + canary green | 7/7 PASS | `make run-tests-e2e` exit code 0 |

---

## Wave 0 Requirements

- **None for TEST-01.** Existing pytest infrastructure (Docker harness at `src/docker/test/python/`) covers all requirements.
- **None blocking for TEST-02.** Fixture file is new code; no missing harness. Playwright 1.48 already installed.
- **Optional pre-check (non-blocking):** See Task 79-02-01 below — manual headed-mode Chromium devtools inspection to validate R-1 (current CSP cleanliness) before landing the fixture.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSP clean-room pre-flight (R-1) | TEST-02 / SC #4 | Need human to read Chromium devtools console for "violates the following Content Security Policy directive" text across the 6 spec navigation paths BEFORE landing the listener; otherwise the listener would fail all 6 specs on first deployment | `cd src/e2e && npx playwright test --headed about.page.spec.ts dashboard.page.spec.ts`, open devtools, inspect console, attach screenshot or log to task summary. If violations found: BLOCK Plan 02; surface as follow-up phase per CONTEXT.md `<deferred>`. |
| CI stderr inspection (SC #1c) | TEST-01 | CI log lives in GitHub Actions UI; grep commands cover local runs | After Plan 01 ships, inspect the first post-merge run at `.github/workflows/ci.yml:144` and confirm zero `pytest-cache` and zero `cgi.*deprecated` lines in stderr. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (all 8 rows above have commands or manual instructions)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify ✅ (all tasks verified)
- [ ] Wave 0 covers all MISSING references ✅ (none needed)
- [ ] No watch-mode flags ✅ (all commands are one-shot)
- [ ] Feedback latency < 90s ✅ (E2E full suite is the longest single run)
- [ ] `nyquist_compliant: true` set in frontmatter — **pending planner fill-in of full task map**

**Approval:** pending (will be approved after planner lands PLAN.md files and the task IDs above are confirmed)
