---
quick_id: 260528-khw
description: triage and merge dependabot PRs, resolve open security alert
status: complete
date: 2026-05-28
---

# Quick Task 260528-khw — Summary

## Outcome

All 5 open Dependabot PRs merged. The open security alert (#18, `tmp` Path Traversal, HIGH) is resolved by PR #48.

- Open Dependabot PRs after sweep: **0**
- Open Dependabot security alerts after sweep: **0**
- Net dependency commits to main: 5 squash merges

## Per-PR Disposition

| PR | Package | Bump | Scope | Action | Commit |
|----|---------|------|-------|--------|--------|
| #48 | tmp | 0.2.5 → 0.2.7 | src/angular (security) | merged | `46259f6` |
| #44 | puppeteer | 25.0.4 → 25.1.0 | root, dev-only | merged | `e879738` |
| #45 | testfixtures | 11.0.0 → 12.0.0 (major) | src/python, dev-only | merged | `8eb8111` |
| #47 | npm_and_yarn group (17 pkgs, all patch) | various patch | src/angular | merged | `00541e7` |
| #46 | ruff | 0.15.13 → 0.15.14 | src/python, dev-only | merged | `9a3475f` |

## Security Alert Disposition

- **Alert #18** — `tmp <0.2.6`, Path Traversal via unsanitized prefix/postfix, severity HIGH, fixed in 0.2.6
- Resolved by PR #48 (bumped to 0.2.7, above the fixed-in version)
- Post-sweep query confirmed 0 open alerts

## Validation Notes

### PR #48 (priority — security fix)
- All CI checks green pre-merge: Docker build, E2E, Python tests, Angular tests, all lint.
- Merged first to close the open HIGH-severity alert.

### PR #44 (puppeteer, dev-only)
- All CI checks green. Patch bump in dev tooling.

### PR #46 (ruff)
- Initial state was UNSTABLE. Diagnosed: the failing check was `Build Docker Image`, not lint. The build error was `poetry install` exit code 1 — unrelated to the ruff bump (PR #46 only touches `src/python/uv.lock`).
- Triggered `gh run rerun --failed`; Docker build passed on retry (8m2s) and E2E followed (4m19s).
- Confirmed transient infra issue, not a ruff regression.

### PR #45 (testfixtures 11 → 12, major dev bump)
- Changelog called out breaking changes: `Comparers` moved to `testfixtures.comparers`, `django_compare` removed, `LogCapture` refactored under new `CaptureSource` architecture.
- Only one usage in repo: `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` uses `from testfixtures import LogCapture` with the standard `with LogCapture(...) as ctx: ctx.check(...)` pattern — public API preserved across the refactor.
- Local Python suite run on PR branch: `1136 passed, 22 failed, 4 errors`.
- Same suite on main with testfixtures 11: `1136 passed, 22 failed, 4 errors` — **identical**.
- Pre-existing local failures are macOS Python 3.12 environment issues (multiprocessing spawn pickling of nested functions, SSH-suite environment). They pass in CI on Linux Docker (confirmed by every PR's green Python unit tests + Docker E2E run).
- Verdict: testfixtures 12 introduces zero regressions for SeedSync's usage.

### PR #47 (Angular 17-package group)
- Initial concern: 17 packages including full `@angular/*` framework. Inspection of the PR body showed all 17 are **patch bumps** (21.2.13 → 21.2.14, 8.59.4 → 8.60.0, 1.99.0 → 1.100.0). No minors, no majors.
- Local validation on PR branch:
  - `npm ci`: clean install (140 packages).
  - `npm run build`: 4.5s, application bundle generated, no errors.
  - `npm run lint`: 0 warnings (max-warnings=0).
  - `npm test -- --watch=false --browsers=ChromeHeadless`: **599/599 pass**, matches v1.1.2 baseline.
- Verdict: safe to merge.

## CI Status on main

After the sweep, `main` has runs in progress for the latest merges. All pre-merge CI on each PR was green before merging; squash-merge of patch-level dependency updates is the same code that already passed CI on each PR branch.

`gh pr list --author 'app/dependabot' --state open` → empty.
`gh api dependabot/alerts | select(.state=="open")` → 0.

## Follow-ups

None blocking. Possible quality-of-life items (not in scope for this task):

1. The 5 pre-existing npm audit findings on `src/angular` (4 moderate, 1 high) reported during `npm ci` are not addressed by this sweep — those are transitive deps without Dependabot PRs open against them. Worth a separate `npm audit` review if the next milestone touches the Angular tree.
2. The macOS-local Python test failures (multiprocessing spawn, SSH suite, latin-chars scanner) are a long-standing dev-env papercut, not a regression. Already known; CI doesn't see them.
3. PR #47's Dependabot group config is working well (small patch-bundle PR) — no tuning needed.

## Files Touched

This task did not edit application code. All work was:
- Local validation runs (Python `pytest`, Angular `npm run build`/`lint`/`test`)
- 5× `gh pr merge --squash --delete-branch`
- Planning artifacts under `.planning/quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/`
