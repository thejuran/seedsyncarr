---
phase: quick
plan: 260528-khw
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: false
requirements: [dependabot-triage, security-alert-resolution]

must_haves:
  truths:
    - "The open Dependabot security alert is either resolved (closed/dismissed) or has a documented remediation path"
    - "All 5 open Dependabot PRs are either merged, closed with rationale, or explicitly deferred"
    - "main branch CI is green after all merges"
    - "Any major-version bump (testfixtures 11->12) has been validated against the Python test suite before merge"
    - "The grouped Angular npm bump (#47) has been validated with Angular build + tests before merge"
    - "PR #46 (ruff UNSTABLE) check failures were diagnosed, not blind-merged"
  artifacts:
    - path: ".planning/quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/260528-khw-SUMMARY.md"
      provides: "Merge log: PR -> action taken (merged/closed/deferred), CI status, alert disposition"
  key_links:
    - from: "dependabot security alert"
      to: "merged PR or dismissal rationale"
      via: "gh api dependabot/alerts + gh pr merge"
      pattern: "alert (resolved|dismissed) with reason"
    - from: "each merged PR"
      to: "main branch CI green"
      via: "gh pr checks <num> after merge"
      pattern: "all checks (passed|skipped)"
---

<objective>
Triage and merge 5 open Dependabot PRs and resolve 1 open Dependabot security alert in the SeedSync repo, in risk order (security-driven first, then dev-only patches, then major dev bump, then grouped npm bump last).

Purpose: Reduce supply-chain exposure (close the open alert) and keep dependency lag low without breaking main. SeedSync is mid-cycle between v1.2.0 (shipped) and the next milestone, so a clean dependency sweep is the right thing to do before the next milestone starts.

Output: All 5 PRs resolved (merged/closed/deferred with reason), security alert closed or documented, main CI green, SUMMARY.md written.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md

Project context:
- Python backend (src/python) — uses ruff, testfixtures, pytest
- Angular frontend (src/angular) — npm-based, has Angular build + Karma tests
- Node tooling (root) — uses puppeteer (dev), tmp
- v1.2.0 shipped 2026-04-28, no active milestone

Prior dependency precedent (PROJECT.md v4.0.3 entry, 2026-04-08):
- Repo has previously closed Dependabot security alerts via npm overrides (hono ^4.12.12, @hono/node-server ^1.19.13)
- Deep review pattern: fix unbounded `>=` constraints to `^` for supply-chain safety

PR landscape (from task context, not re-fetched yet — Task 1 will re-verify):
| PR | Package | Scope | Risk | Status |
|----|---------|-------|------|--------|
| #44 | puppeteer 25.0.4 -> 25.1.0 | root, dev-only | low | MERGEABLE/CLEAN |
| #45 | testfixtures 11.0.0 -> 12.0.0 | src/python, dev-only | medium (major) | MERGEABLE/CLEAN |
| #46 | ruff 0.15.13 -> 0.15.14 | src/python, dev-only | low (but UNSTABLE) | MERGEABLE/UNSTABLE |
| #47 | npm_and_yarn group (17 pkgs) | src/angular | high (blast radius) | MERGEABLE/CLEAN |
| #48 | tmp 0.2.5 -> 0.2.7 | src/angular, dep | low | MERGEABLE/CLEAN |
</context>

<tasks>

<task type="auto">
  <name>Task 1: Investigate security alert and merge low-risk dev/patch PRs (#44, #46, #48)</name>
  <files>(no file edits — gh CLI operations only)</files>
  <action>
    Investigate the open Dependabot security alert and merge the three low-risk PRs.

    1. Fetch the open Dependabot security alert details:
       `gh api repos/:owner/:repo/dependabot/alerts --jq '.[] | select(.state=="open") | {number, dependency: .dependency.package.name, ecosystem: .dependency.package.ecosystem, severity: .security_advisory.severity, summary: .security_advisory.summary, fix_pr: .auto_dismissed_at}'`
       Record: alert number, affected package, severity, summary.

    2. Cross-reference the alert against open PRs (#44-#48). For each candidate PR:
       `gh pr view <num> --json title,body,files`
       Determine if any PR resolves the alert (package name match in the PR diff).

    3. If a PR resolves the alert: that PR becomes the priority merge in this task. If no PR resolves it: note this in the SUMMARY and continue — alert disposition will be addressed via Dependabot rebase or manual override in a follow-up (do NOT block the merge sweep on it).

    4. Re-verify current mergeability for #44, #46, #48 (status may have shifted since the task brief):
       `gh pr view 44 --json mergeable,mergeStateStatus,statusCheckRollup`
       `gh pr view 46 --json mergeable,mergeStateStatus,statusCheckRollup`
       `gh pr view 48 --json mergeable,mergeStateStatus,statusCheckRollup`

    5. Diagnose PR #46 (ruff, UNSTABLE). Pull the failing check details:
       `gh pr checks 46`
       `gh run view <run-id-of-failure> --log-failed` for any failed runs.
       If the failure is unrelated to the ruff bump (flaky test, infrastructure, unrelated CI job), retry the failed run with `gh run rerun <run-id>` and wait. If the failure is caused by new ruff lint rules in 0.15.14, do NOT auto-merge — instead, document the failing rule(s) in the SUMMARY and either (a) fix the lint findings in a follow-up commit on a branch, or (b) close PR #46 with a comment explaining why and let the next ruff patch handle it. Decide based on what the diagnosis shows; do not blind-merge.

    6. Merge PR #44 (puppeteer dev-only patch — root group):
       `gh pr merge 44 --squash --auto --delete-branch`
       If `--auto` is not available on this repo (auto-merge disabled), use `gh pr merge 44 --squash --delete-branch` after confirming `gh pr checks 44` is green.

    7. Merge PR #48 (tmp 0.2.5 -> 0.2.7, Angular):
       `gh pr merge 48 --squash --auto --delete-branch`
       Same `--auto` fallback as above.

    8. Merge PR #46 (ruff) only if step 5 cleared it (checks now green); otherwise leave open or close per step 5 disposition.

    9. After merges complete (poll `gh pr view <num> --json state` until each is MERGED, or wait up to 10 min for `--auto`), pull main locally and confirm CI:
       `git checkout main && git pull origin main`
       `gh run list --branch main --limit 5` — confirm the most recent run on main is success or in_progress.

    10. If main CI fails after any merge, immediately open a follow-up issue with the failing job log and STOP — do not proceed to Task 2 until main is green again. The revert path is `gh pr revert <num>` (creates a revert PR) — do not force-push to main.
  </action>
  <verify>
    <automated>gh pr view 44 --json state --jq '.state' | grep -qx MERGED && gh pr view 48 --json state --jq '.state' | grep -qx MERGED && gh run list --branch main --limit 1 --json conclusion --jq '.[0].conclusion' | grep -qxE 'success|null|'</automated>
  </verify>
  <done>
    - Security alert investigated; disposition (resolved by PR / no PR fix / dismissed with reason) recorded
    - PR #44 merged with squash, branch deleted
    - PR #48 merged with squash, branch deleted
    - PR #46 either merged (if checks cleared) OR has a documented disposition (failing lint findings, close+wait, or deferred to follow-up)
    - main branch CI is green (or last run is in_progress with no failures) after all merges
  </done>
</task>

<task type="auto">
  <name>Task 2: Validate and merge major dev bump (#45 testfixtures) + grouped npm bump (#47)</name>
  <files>(no file edits — local test runs + gh CLI)</files>
  <action>
    Handle the two higher-risk PRs after Task 1's low-risk sweep is green.

    1. PR #45 — testfixtures 11.0.0 -> 12.0.0 (major, Python dev):

       a. Fetch the PR body and changelog link:
          `gh pr view 45 --body`
          Read the Dependabot-generated release notes section. List any breaking changes called out (API removals, signature changes, dropped Python versions).

       b. Check out the PR locally:
          `gh pr checkout 45`
          `cd src/python`
          Install the updated dev deps per the project's normal install path (check src/python/README.md or pyproject.toml for `pip install -e .[dev]` or `pip install -r requirements-dev.txt` or `uv sync` — use whichever the repo uses).

       c. Run the Python test suite:
          `pytest` (or the project's documented test command — check src/python/Makefile / pyproject.toml [tool.pytest.ini_options] / CI workflow at .github/workflows/ for the exact invocation).
          Record: total tests, passed, failed, errors. Compare to v1.1.2 baseline (1262 Python tests, per PROJECT.md).

       d. If tests pass: return to main (`git checkout main`), then merge:
          `gh pr merge 45 --squash --auto --delete-branch`
          (fallback to `--squash --delete-branch` without `--auto` if needed)

       e. If tests fail: identify which test(s) broke and whether the failure is due to testfixtures 12.0.0 API changes. Document findings. Either (a) fix the test usage in a follow-up branch and re-run, (b) pin testfixtures back to 11.x in the requirements file and close PR #45 with rationale, or (c) defer — leave PR open and document in SUMMARY. Do NOT merge a red suite.

    2. PR #47 — grouped npm_and_yarn bump (17 packages, Angular):

       a. Fetch the PR body and list the 17 packages being bumped:
          `gh pr view 47 --body`
          Record: package names, old -> new versions, any flagged as security advisories vs. regular updates.

       b. Check the diff for `src/angular/package.json` and `src/angular/package-lock.json`:
          `gh pr diff 47 -- src/angular/package.json`
          Note any major-version bumps within the group (those carry breakage risk even within a grouped update). Highlight any Angular framework package bumps (`@angular/*`) — those need extra care.

       c. Check out the PR locally:
          `gh pr checkout 47`
          `cd src/angular`
          `npm ci` (uses the locked versions from the PR)

       d. Run the Angular build:
          `npm run build` (or `ng build` — check src/angular/package.json scripts and src/angular/angular.json for the production build script; use `npm run build:prod` if that's what CI uses).
          Build must succeed with zero errors. Warnings are acceptable but worth noting.

       e. Run the Angular unit tests:
          `npm test -- --watch=false --browsers=ChromeHeadless` (or whatever the CI invocation is — check .github/workflows/*.yml for the exact command).
          Compare to v1.1.2 baseline (599 Angular tests).

       f. (Optional, only if step e passes and time permits) Run the E2E suite locally OR verify CI runs it on the PR branch automatically. If CI already runs E2E on the PR, prefer waiting for the PR's CI run over running it locally.

       g. If build + tests pass: return to main, then merge:
          `gh pr merge 47 --squash --auto --delete-branch`

       h. If build or tests fail: identify the offending package(s). Options: (a) ask Dependabot to split the group by commenting `@dependabot recreate` after temporarily narrowing the group config (out of scope here — note as a follow-up), (b) close PR #47 with rationale and let Dependabot regenerate individual PRs on its next run, (c) pin the breaking package(s) in package.json and merge the rest manually (out of scope here unless trivial). Do NOT merge a red suite.

    3. After both PRs are resolved, pull main locally and confirm CI:
       `git checkout main && git pull origin main`
       `gh run list --branch main --limit 5`
       Confirm the latest run on main is success (or in_progress with no prior failures).

    4. Re-check the Dependabot security alert state:
       `gh api repos/:owner/:repo/dependabot/alerts --jq '.[] | select(.state=="open") | .number'`
       If the alert is now closed: confirm in SUMMARY. If still open and no PR resolves it: document the remaining remediation path (manual override / pin / dismiss with reason).

    5. Write SUMMARY.md to `.planning/quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/260528-khw-SUMMARY.md` capturing:
       - Per-PR disposition (merged/closed/deferred) with merge commit SHA where applicable
       - Security alert disposition (resolved by PR #X / dismissed with reason / remaining open + remediation plan)
       - CI status on main after the sweep
       - Any follow-up items (e.g., re-grouped npm PR pending, lint findings to fix, deferred items)
  </action>
  <verify>
    <automated>gh pr view 45 --json state --jq '.state' | grep -qxE 'MERGED|CLOSED' && gh pr view 47 --json state --jq '.state' | grep -qxE 'MERGED|CLOSED' && test -f .planning/quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/260528-khw-SUMMARY.md && gh run list --branch main --limit 1 --json conclusion --jq '.[0].conclusion' | grep -qxE 'success|null|'</automated>
  </verify>
  <done>
    - PR #45 resolved: either merged after Python suite pass, or closed/deferred with documented rationale
    - PR #47 resolved: either merged after Angular build + tests pass, or closed/deferred with documented rationale
    - main branch CI green (or in_progress with no failures) after the sweep
    - Dependabot security alert state re-checked and disposition recorded
    - SUMMARY.md written with full disposition log
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. `gh pr list --author 'app/dependabot' --state open` — should be empty, OR only contain PRs explicitly deferred with documented rationale in SUMMARY.md
2. `gh api repos/:owner/:repo/dependabot/alerts --jq '[.[] | select(.state=="open")] | length'` — should be 0, OR the remaining open alert has a remediation plan in SUMMARY.md
3. `gh run list --branch main --limit 1` — most recent main run is `success` or `in_progress`
4. `git log --oneline -10` on main shows the squash-merge commits from this sweep
5. SUMMARY.md exists at the planned path and lists every PR's disposition
</verification>

<success_criteria>
- All 5 open Dependabot PRs have a documented disposition (merged / closed / deferred)
- The open Dependabot security alert is either resolved or has a documented remediation path
- main branch CI is green after the sweep (no broken main)
- No force-pushes to main, no direct commits bypassing PR review
- Higher-risk PRs (#45 major bump, #47 grouped bump) were validated locally before merge — not blind-merged
- PR #46's UNSTABLE check was diagnosed, not ignored
- SUMMARY.md captures the full triage log for future reference
</success_criteria>

<output>
Create `.planning/quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/260528-khw-SUMMARY.md` when done.
</output>
