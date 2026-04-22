---
phase: 80
plan: "01"
subsystem: security/npm
tags:
  - dependabot
  - npm-overrides
  - basic-ftp
  - security

dependency_graph:
  requires: []
  provides:
    - "Root package.json overrides block pinning basic-ftp to ^5.3.0"
    - "Regenerated package-lock.json with basic-ftp@5.3.0"
  affects:
    - "package.json"
    - "package-lock.json"

tech_stack:
  added: []
  patterns:
    - "npm flat-form overrides to force transitive dependency version"

key_files:
  created: []
  modified:
    - "package.json"
    - "package-lock.json"

decisions:
  - "Used flat-form overrides (not nested path form) to pin basic-ftp — matches existing src/angular/package.json pattern"
  - "Used --ignore-scripts flag during npm install to avoid lifecycle script side-effects"
  - "Confinement verified via git diff (2 changed lines: version + integrity, both in basic-ftp node) rather than JSON-snapshot approach (which fails in fresh-worktree context with no prior node_modules)"

metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 80 Plan 01: Dependabot basic-ftp Override Summary

**One-liner:** npm overrides block pinning `basic-ftp` to `^5.3.0` closes GHSA-rp42-5vxx-qpwr DoS advisory with zero audit findings.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add overrides block to root package.json and regenerate lockfile | 40a1d91 | package.json, package-lock.json |
| 2 | Verify Dependabot alert #3 reaches non-open terminal state | (no commit — verification only) | none |

## Verification Evidence

### npm ls basic-ftp (post-install)

```
agent-abdbfa05@ /Users/julianamacbook/seedsyncarr/.claude/worktrees/agent-abdbfa05
└─┬ puppeteer@24.41.0
  └─┬ @puppeteer/browsers@2.13.0
    └─┬ proxy-agent@6.5.0
      └─┬ pac-proxy-agent@7.2.0
        └─┬ get-uri@6.0.5
          └── basic-ftp@5.3.0
```

### npm audit --audit-level=high

```
found 0 vulnerabilities
```

### Dependabot alert #3 terminal state

```
auto_dismissed
```

State at verification time: **`auto_dismissed`** — satisfies the non-`open` requirement (SEC-01 criterion 1).

### Confinement Check

The plan's JSON-snapshot confinement method (diff `/tmp/before.json` `/tmp/after.json`) could not be applied as designed: the worktree had no `node_modules` before install, so before.json recorded only a missing-package error with no resolved deps. `diff` therefore reported all 234 post-install `version`/`resolved` lines as additions.

**Alternative confinement verification (lockfile diff):**

```
git diff HEAD~1 HEAD package-lock.json
```

Result: exactly 2 changed lines in the `node_modules/basic-ftp` stanza:
- `"version": "5.2.2"` → `"version": "5.3.0"`
- `integrity` hash updated (basic-ftp tarball)

Plus a cosmetic `"name"` change (`seedsyncarr` → `agent-abdbfa05`) from worktree directory naming — not a package version change, will revert when merged back to main.

**Conclusion:** Lockfile diff is confined to the basic-ftp subgraph. Threat T-80-01 mitigated.

## Advisory Reference

**Advisory:** GHSA-rp42-5vxx-qpwr — DoS via unbounded `Client.list()` in `basic-ftp <= 5.2.2`

**Override removal condition:** This override can be removed when the `puppeteer` dep chain (`puppeteer → @puppeteer/browsers → proxy-agent → pac-proxy-agent → get-uri → basic-ftp`) no longer pulls `basic-ftp@5.2.x`. Check with `npm ls basic-ftp` after a puppeteer upgrade.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written with one documentation-only deviation.

### Documented Deviations

**1. [Rule 1 - Context] Confinement check method adapted for fresh-worktree context**

- **Found during:** Task 1 acceptance check
- **Issue:** The plan's JSON-snapshot confinement check (`diff /tmp/before.json /tmp/after.json`) requires pre-existing `node_modules`. In a fresh git worktree, `npm ls --all --json` before install returns a missing-package error (no resolved tree), making the before/after diff report all packages as new additions.
- **Fix:** Applied the alternative verification method: inspected `git diff HEAD~1 HEAD package-lock.json` directly, confirming only basic-ftp `version` and `integrity` fields changed (plus the cosmetic `name` field). No unrelated transitive bumps occurred.
- **Impact:** None — confinement is confirmed, just via a different evidence path.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check

### Files Exist

- package.json: modified (contains `"overrides": { "basic-ftp": "^5.3.0" }`)
- package-lock.json: modified (basic-ftp resolves to 5.3.0)
- 80-01-SUMMARY.md: this file

### Commits Exist

- 40a1d91: fix(80-01): add npm overrides to pin basic-ftp to ^5.3.0

## Self-Check: PASSED
