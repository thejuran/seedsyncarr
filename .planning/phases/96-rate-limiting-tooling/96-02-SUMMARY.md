---
phase: 96-rate-limiting-tooling
plan: "02"
subsystem: tooling
tags: [semgrep, security, nosql-injection, xss, false-positives, metavariable-regex]

requires: []
provides:
  - Tightened js-nosql-injection-where Semgrep rule with metavariable-regex constraint
  - Tightened js-xss-eval-user-input Semgrep rule with arrow/named-function pattern-not exclusions
affects: [shield-claude-skill, security-scanning]

tech-stack:
  added: []
  patterns:
    - "metavariable-regex on method-name metavariables to restrict generic call patterns to specific operator names"
    - "pattern-not exclusions for function-typed arguments to distinguish callbacks from dynamic-string eval sinks"

key-files:
  created: []
  modified:
    - shield-claude-skill/configs/semgrep-rules/javascript.yaml

key-decisions:
  - "Use metavariable-regex with regex '^\$where$' on $WHERE to restrict the nosql-injection-where rule to MongoDB's literal $where operator, preventing 617 FPs from generic .where() ORM methods"
  - "Add both zero-arg (() => $BODY) and parameterized (($ARGS) => $BODY) arrow-function pattern-not entries because Semgrep treats them as structurally distinct patterns"
  - "Add named-function pattern-not (function $NAME($PARAMS) { $BODY }) as a third form for setTimeout/setInterval to cover all callback syntax variants"

patterns-established:
  - "metavariable-regex as a sibling pattern under patterns: to constrain structural matches by literal name"
  - "paired arrow-form pattern-not entries (with and without params) when Semgrep cannot use a single wildcard for both"

requirements-completed: [TOOL-01, TOOL-02]

duration: 8min
completed: 2026-04-28
---

# Phase 96 Plan 02: Tighten Shield Semgrep Rules Summary

**Eliminated 628 Semgrep false positives by adding metavariable-regex to js-nosql-injection-where and six pattern-not exclusions to js-xss-eval-user-input, with semgrep --validate and TP/FP scan tests confirming correct behavior**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T22:11Z
- **Completed:** 2026-04-28T22:19Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- TOOL-01: Converted js-nosql-injection-where from a bare `pattern:` to a `patterns:` block with `metavariable-regex` constraining `$WHERE` to `^\$where$` — eliminates 617 FPs from generic ORM `.where()` calls
- TOOL-02: Added 6 `pattern-not` exclusions to js-xss-eval-user-input for all arrow-function and named-function callback forms in setTimeout/setInterval — eliminates 11 FPs while preserving detection of bare-variable argument sinks
- semgrep --validate passes (0 errors, 12 rules) on the modified file
- TP/FP scan tests confirm both rules behave as expected (4/4 assertions passed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten js-nosql-injection-where and js-xss-eval-user-input Semgrep rules** - `bf0fc8b` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `shield-claude-skill/configs/semgrep-rules/javascript.yaml` - Tightened two security rules: metavariable-regex for nosql-injection-where, six pattern-not exclusions for xss-eval-user-input

## Decisions Made
- Used `'^\$where$'` (single-quoted YAML string) for the metavariable-regex to prevent YAML from interpreting `$where` as a variable reference
- Both zero-arg and parameterized arrow-function forms required as separate entries because Semgrep pattern matching treats them as structurally distinct AST forms (Assumption A3 from research)
- Force-added `shield-claude-skill/configs/semgrep-rules/javascript.yaml` with `git add --force` since the directory is in `.gitignore` (intentional — AI tooling is local-only, but this specific rules file is tracked for plan execution)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The `shield-claude-skill/` directory is listed in `.gitignore` as local-only AI tooling. Committed via `git add --force` as instructed by the plan's `files_modified` spec. The worktree did not inherit the directory from the git checkout, so the file was copied from the main repo before editing.
- `semgrep` had a broken `requests` module dependency (Python 3.9 environment) — installed `requests` via pip to restore functionality. This is an environment-only fix, no code changes.

## Known Stubs

None - this plan modifies YAML rule definitions, not UI or data-rendering code.

## Next Phase Readiness
- Both TOOL-01 and TOOL-02 rules are validated and ready for Shield's next scan run
- The javascript.yaml rule set now has 12 total rules, all passing semgrep --validate

---
*Phase: 96-rate-limiting-tooling*
*Completed: 2026-04-28*

## Self-Check: PASSED

- javascript.yaml: FOUND
- 96-02-SUMMARY.md: FOUND
- commit bf0fc8b: FOUND
- `patterns:` block in js-nosql-injection-where: FOUND
- `metavariable-regex:` present: FOUND
- `metavariable: $WHERE` present: FOUND
- pattern-not count: 14 (>= required 7)
