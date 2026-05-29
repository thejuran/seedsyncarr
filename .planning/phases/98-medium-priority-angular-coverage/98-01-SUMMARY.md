---
phase: 98-medium-priority-angular-coverage
plan: 01
subsystem: testing
tags: [angular, jasmine, karma, xss, escapeHtml, dom-testing, security]

# Dependency graph
requires: []
provides:
  - "Full end-to-end XSS regression guard for ConfirmModalService.escapeHtml (COVMED-04)"
  - "D-04: Direct unit tests for all five metacharacter mappings + &-first ordering"
  - "D-03/D-05: DOM XSS assertions for all six escaped inputs (title/body/okBtn/cancelBtn/okBtnClass/cancelBtnClass)"
  - "D-02: skipCount-exemption documenting test + runtime-boundary probe pinning coercible-object behavior"
  - "describe('XSS / escapeHtml coverage') nested block with escape() and hasOnAttribute() helpers"
affects: [100-angular-coverage-ratchet]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "escape() helper: (ConfirmModalService as any).escapeHtml(s) — idiomatic private-static access"
    - "hasOnAttribute() helper: element.attributes loop with startsWith('on') — correct on*-name detection"
    - "Four-layer D-03 assertion: no script element, no on* attr, no javascript: URL, entity-encoded innerHTML"
    - "Runtime-boundary probe: coercible object cast as unknown as number to pin service behavior"

key-files:
  created: []
  modified:
    - src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts

key-decisions:
  - "D-01 (locked): escape set stays &<>\"' — backtick/U+2028/U+2029/null not exploitable in element-content or double-quoted-attr contexts; documenting test records reasoning"
  - "D-02 (locked): skipCount is number-only, not routed through escapeHtml; runtime-boundary probe pins coercible-object path as v1.4.0 deferred work"
  - "D-06: Supersede two partial XSS tests (former lines 300-338) with fuller D-03 assertions, preserving their unique textContent assertions"
  - "Use \\u2028/\\u2029/\\0 escape sequences for deferred-chars test (not raw bytes) to avoid file corruption"
  - "eslint-disable-next-line for no-explicit-any on class cast to any (idiomatic test pattern, not value-cast risk)"

patterns-established:
  - "Pattern: (Class as any).privateStaticMethod(input) for private-static access in Jasmine specs"
  - "Pattern: hasOnAttribute(root) helper — walks root.querySelectorAll('*') + root via element.attributes[i].name.startsWith('on')"
  - "Pattern: Dual innerHTML/textContent assertion — innerHTML proves entity encoding, textContent proves visible-text decoding"

requirements-completed: [COVMED-04]

# Metrics
duration: 8min
completed: 2026-05-29
---

# Phase 98 Plan 01: XSS / escapeHtml Coverage Summary

**Full end-to-end XSS regression guard for ConfirmModalService: 12 new Jasmine tests covering all five metacharacter mappings, six escaped inputs (element-content + class-attribute), skipCount exemption audit, and coercible-object runtime-boundary probe**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-29T14:12:35Z
- **Completed:** 2026-05-29T14:20:53Z
- **Tasks:** 3 of 3
- **Files modified:** 1

## Accomplishments

- Added `describe("XSS / escapeHtml coverage")` nested block with `escape()` and `hasOnAttribute()` module-scope helpers; Karma suite grows from 599 to 611 tests (12 added, 2 superseded = net +10)
- D-04 direct unit tests: five metacharacter mappings, `&`-first ordering guard against double-escape regression, combined payload, D-01 documenting test for intentionally un-escaped chars
- D-03/D-05 end-to-end DOM XSS tests for all six inputs: four assertion layers each (no script element, no on* attr, no javascript: URL, entity-encoded innerHTML string); supersede two partial XSS tests (former lines 300-338) while preserving their unique textContent assertions
- D-02 skipCount-exemption: numeric-render documenting test + runtime-boundary probe (codex adversarial review) pinning that a coercible object's toString() markup reaches innerHTML un-escaped — documents the v1.4.0 deferred hardening scope

## Task Commits

1. **Task 1: XSS describe scaffold, helpers, D-04 unit tests** - `1c83016` (test)
2. **Task 2: D-03/D-05 end-to-end DOM XSS coverage, supersede partial tests** - `987c4cf` (test)
3. **Task 3: D-02 skipCount-exemption + runtime-boundary probe** - `5db6d61` (test)

## Files Created/Modified

- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` — Extended with 76+208+72 lines; two former partial XSS tests removed; 12 new it-blocks added in `describe("XSS / escapeHtml coverage")`

## Decisions Made

- Used TypeScript escape sequences ` `, ` `, `\0` instead of raw Unicode characters in the deferred-chars documenting test (plan instruction: avoid file corruption from raw byte embedding)
- Added `// eslint-disable-next-line @typescript-eslint/no-explicit-any` on the `(ConfirmModalService as any)` class cast — consistent with RESEARCH.md Area 1 rationale (class cast, not value cast; no runtime null-fault risk)
- Runtime-boundary probe asserts `expect(skipP.querySelector("img")).not.toBeNull()` after observing that the coercible object's `toString()` markup IS parsed by the browser HTML parser — the test pins actual behavior per plan Task 3 guidance
- Plural "s" assertion in runtime probe uses `"files will be skipped"` because `{...} === 1` is false (strict equality, object !== number literal)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Raw Unicode bytes replaced with escape sequences**
- **Found during:** Task 1 (deferred-chars documenting test)
- **Issue:** Edit tool embedded raw U+2028, U+2029, U+0000 bytes in the spec file; plan explicitly requires escaped literals to avoid file corruption
- **Fix:** Python byte-replacement script to swap `\xe2\x80\xa8` → ` `, `\xe2\x80\xa9` → ` `, `\x00` → `\0` in the file binary
- **Files modified:** confirm-modal.service.spec.ts
- **Committed in:** 1c83016 (Task 1 commit, after fix)

**2. [Rule 3 - Blocking] ESLint failures on three rules after Task 1 additions**
- **Found during:** Task 1 eslint run
- **Issues:** `no-explicit-any` warn (blocked by --max-warnings 0); `no-unused-vars` error for `hasOnAttribute` (not yet used in Task 1); `max-len` error (test description 142 chars, limit 140)
- **Fixes:** Added `// eslint-disable-next-line @typescript-eslint/no-explicit-any` on class cast; added `// eslint-disable-next-line @typescript-eslint/no-unused-vars` on hasOnAttribute (removed in Task 2 when the helper was used); shortened test description to 137 chars
- **Files modified:** confirm-modal.service.spec.ts
- **Committed in:** 1c83016 (Task 1 commit, after fix)

---

**Total deviations:** 2 auto-fixed (1 blocking byte-encoding fix, 1 blocking lint fix)
**Impact on plan:** Both fixes necessary for file integrity and CI compliance. No scope creep.

## Issues Encountered

- `node_modules` not installed in worktree's `src/angular/` — created a symlink to main repo's `src/angular/node_modules` (same `package.json`, identical install). Tests and eslint ran correctly via the symlink.
- The ALERT logs (`ALERT: 1`) visible in the full test run output are expected — they are fired by the `onerror=alert(1)` in the runtime-boundary probe's coercible-object payload, which is deliberately parsed by the browser. This is the service's documented runtime behavior, not a test failure.

## Known Stubs

None — this is a test-only plan; no production stubs introduced.

## Threat Flags

None — this plan only modifies a spec file. No new network endpoints, auth paths, file access patterns, or schema changes.

## Next Phase Readiness

- COVMED-04 fully closed: all success criteria met
- Full Angular suite 611/611 passing (no regression in sibling specs)
- ESLint clean on spec file
- `confirm-modal.service.ts` unchanged (D-01 no-op confirmed)
- Phase 100 (RATCHET-02) may now ratchet Angular coverage thresholds upward; this plan contributes branch/statement coverage on `escapeHtml` and `createModal`

---
*Phase: 98-medium-priority-angular-coverage*
*Completed: 2026-05-29*
