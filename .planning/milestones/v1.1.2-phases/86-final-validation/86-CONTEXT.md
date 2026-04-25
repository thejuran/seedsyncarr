# Phase 86: Final Validation - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm all three test layers (Python, Angular, E2E) pass end-to-end in CI and document the post-audit coverage baseline. This is a pure validation phase — no code changes, no test removals, no bug fixes.

</domain>

<decisions>
## Implementation Decisions

### CI Verification Method
- **D-01:** Verify CI green by pushing to GitHub and confirming the real GitHub Actions pipeline passes. No local pre-check required. The authoritative proof for VAL-01 is the CI run itself.
- **D-02:** The push can be a documentation-only commit (coverage notes in ROADMAP.md) or the phase's own planning artifacts — no source code changes are expected.

### Coverage Documentation
- **D-03:** Document Python coverage before/after in the v1.1.2 milestone section of ROADMAP.md when the milestone is completed. No standalone coverage report file.
- **D-04:** Include Angular coverage baselines (from Phase 84: 83.34%/69.01%/79.73%/84.21%) alongside Python (85.05%) for completeness in the milestone notes.
- **D-05:** Python coverage must not drop below 84% (`fail_under` in pyproject.toml). Phase 83 recorded 85.05% — the "after" number comes from the CI run in this phase.

### Arm64 E2E Sort Failures
- **D-06:** The 2 pre-existing arm64 Unicode sort failures in E2E (documented in Phase 85) are NOT regressions from the test audit. They are deferred to a future phase/todo.
- **D-07:** VAL-01 is satisfied with a caveat documenting these 2 failures as pre-existing and locale-dependent (arm64 glibc sort order differs from amd64). The audit did not introduce them.
- **D-08:** Create a todo for the arm64 sort issue so it's tracked for future resolution.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CI Infrastructure
- `.github/workflows/ci.yml` — Full CI pipeline: Python tests, Angular tests, E2E (amd64+arm64), lint (ruff+eslint), Docker build, publish
- `Makefile` — `run-tests-python`, `run-tests-angular`, `run-tests-e2e`, `coverage-python` targets

### Coverage Configuration
- `src/python/pyproject.toml` — pytest config, `fail_under = 84` coverage threshold

### Prior Phase Results
- `.planning/phases/83-python-test-audit/83-01-SUMMARY.md` — Python audit results: zero removals, 85.05% coverage baseline
- `.planning/phases/84-angular-test-audit/84-CONTEXT.md` — Angular audit results: zero removals, 599/599 green, coverage baseline recorded
- `.planning/phases/85-e2e-test-audit/85-01-SUMMARY.md` — E2E audit results: zero removals, 37 specs verified, arm64 sort caveat documented
- `.planning/phases/85-e2e-test-audit/85-VERIFICATION.md` — Deferred item: CI E2E pass on both architectures → Phase 86

### Requirements
- `.planning/REQUIREMENTS.md` — VAL-01 (full CI green), VAL-02 (Python coverage documented)

</canonical_refs>

<code_context>
## Existing Code Insights

### CI Pipeline Structure
- 6 CI jobs: `unittests-python`, `unittests-angular`, `lint-python`, `lint-angular`, `build-docker-image`, `e2etests-docker-image`
- E2E runs on matrix: amd64 (ubuntu-latest) + arm64 (ubuntu-24.04-arm) — arm64 only on main push + release tags, PRs run amd64 only
- Docker image build is a prerequisite for E2E tests
- Publish job runs only on version tags

### Test Suite State (Post-Audit)
- Python: 1,262 tests, 85.05% coverage, `fail_under = 84`
- Angular: 599 tests, Karma + Jasmine, ChromeHeadlessCI
- E2E: 37 Playwright specs across 7 files, CSP violation listener active
- Known: 2 arm64 Unicode sort failures (pre-existing, locale-dependent)

### Integration Points
- `ROADMAP.md` — milestone notes section for coverage documentation
- GitHub Actions — CI run triggered by push to main or PR

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- **Arm64 Unicode sort failures** — 2 E2E specs fail on arm64 due to locale-dependent Unicode sort order (glibc differences between amd64 and arm64). Pre-existing, not introduced by the audit. Track as a todo for future resolution.

</deferred>

---

*Phase: 86-final-validation*
*Context gathered: 2026-04-24*
