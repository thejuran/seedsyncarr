---
phase: 98-medium-priority-angular-coverage
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 98: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed the additive XSS / `escapeHtml` test coverage added to
`confirm-modal.service.spec.ts`. The production source
(`confirm-modal.service.ts`) is intentionally unchanged; the runtime-boundary
probe (lines 700-730) is a deliberate characterization test pinning a deferred
hardening decision and is correctly scoped — not flagged.

The new tests are largely well-constructed: the `hasOnAttribute` helper
correctly walks `element.attributes[].name` (not a CSS selector), the dual
DOM-plus-`innerHTML` assertion layers are both present in every end-to-end XSS
test, `escape()` and `hasOnAttribute()` are declared at `describe` scope (not
inside test bodies), `fakeAsync`/`tick()` is used consistently, and no loose
`==` equality appears anywhere. The direct `escapeHtml` unit tests
(lines 456-497) prove what they claim, including the `&`-first ordering
regression guard.

No blockers. The findings below concern flake risk from real-DOM focus
dependence, service-state leakage from tests that never close the modal, and a
small number of assertion-strength / documentation-accuracy nits.

## Warnings

### WR-01: Focus-dependent assertions flake under the default non-headless `Chrome` launcher

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:311,349,369,392`
**Issue:** Four tests assert on `document.activeElement` after calling
`.focus()` ("should focus cancel button", "should trap Tab focus", "should trap
Shift+Tab focus", "should restore focus to previously focused element").
`HTMLElement.focus()` and `document.activeElement` are only deterministic when
the browser window holds OS-level focus. `karma.conf.js` sets
`browsers: ['Chrome']` as the default (non-headless); when that window is
backgrounded, `.focus()` becomes a no-op and `document.activeElement` remains
`<body>`, so these assertions fail non-deterministically. The dedicated
`ChromeHeadlessCI` launcher avoids this, but local `ng test` runs against the
default `Chrome` launcher are exposed.

These tests exercise genuine production behavior (the service really moves
focus), so the assertions are not wrong — the risk is environmental flake, not
a logic defect. This is a Warning, not a blocker.
**Fix:** Either gate these four focus tests behind the headless launcher, or
add a guard that skips/relaxes the activeElement assertion when the document is
not focused, e.g.:
```typescript
if (!document.hasFocus()) {
    pending("window not focused — focus assertions unreliable in this environment");
    return;
}
expect(document.activeElement).toBe(cancelButton);
```

### WR-02: Tab / Shift+Tab focus-trap tests never close the modal, leaking service state and DOM listeners across tests

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:332-350,352-370`
**Issue:** Both focus-trap tests call `service.confirm(...)` + `tick()` and then
assert, but never trigger a close path (no OK/Cancel click, no Escape). On exit
the service still holds `modalElement`, `backdropElement`, `keydownHandler`, and
`previouslyFocusedElement`, and the `keydown` listener is still attached to the
modal node. The `afterEach` (lines 18-23) removes `.modal`/`.modal-backdrop`
DOM nodes via `querySelectorAll`, but it does NOT call `destroyModal()`, so the
service's internal references and the previously-focused-element restoration are
never run for these tests. Because `TestBed` constructs a fresh service in each
`beforeEach`, this does not leak *across* tests today, but it does leave a live
event listener bound to an orphaned (about-to-be-removed) node and relies on the
DOM-only cleanup rather than the service's own teardown — a fragile coupling
that will break silently if the cleanup selector or service internals change.
**Fix:** Close the modal at the end of each focus-trap test so the service's own
teardown runs and the listener is removed:
```typescript
// after the focus assertion:
const okBtn = modal.querySelector("[data-action=\"ok\"]") as HTMLButtonElement;
okBtn.click();
tick();
```
Alternatively, dispatch an Escape keydown to drive `closeModal(false)`.

### WR-03: Focus-trap tests assert focus movement without first confirming the pre-Tab focus state, weakening the assertion

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:346-349,366-369`
**Issue:** The Tab test does `okButton.focus()` then dispatches Tab and expects
`activeElement === cancelButton`; the Shift+Tab test does `cancelButton.focus()`
then expects `activeElement === okButton`. Neither test asserts that the
explicit `.focus()` actually took effect *before* dispatching the key. The
production handler (source lines 145-162) decides the wrap target by reading
`document.activeElement`. If the preparatory `.focus()` silently failed (the
same windowing condition as WR-01), `document.activeElement` would be `<body>`,
the handler's `else` branch would fire, and the test could pass for the wrong
reason — masking a real regression in the focus-trap branch logic.
**Fix:** Assert the pre-condition before dispatching the key:
```typescript
okButton.focus();
expect(document.activeElement).toBe(okButton); // pre-condition
modal.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
expect(document.activeElement).toBe(cancelButton);
```

## Info

### IN-01: `escape()` helper has no test for empty string or multi-character/idempotency inputs

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:456-477`
**Issue:** The direct unit tests cover single metacharacters, the `&`-first
ordering, and one combined payload, but not the empty-string boundary
(`escape("")` should be `""`) nor an already-escaped string being passed through
again (idempotency is intentionally NOT held — `escape("&amp;")` becomes
`&amp;amp;`). Documenting these boundaries would make the contract explicit.
**Fix:** Add `expect(escape("")).toBe("");` and a short note/assertion recording
that double-application is expected to re-escape (not idempotent).

### IN-02: Comment claims assertions were "preserved from line 315" but the body script test asserts `<script>`, not the img/onerror payload referenced

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:565-567`
**Issue:** The inline comment says "Preserved from superseded test (line 315):
img-based onerror payload visible as literal text (mirrors the former
textContent assertion for body)", but the body of this test injects
`<script>alert(1)</script>` and asserts `modalBodyP.textContent` contains
`<script>`. The comment's reference to an "img-based onerror payload" is
inaccurate for this test (that payload is exercised in the separate test at
lines 570-587). The assertion itself is correct; only the comment is
misleading.
**Fix:** Correct the comment to reference the script payload actually asserted
here, or drop the "img-based onerror" phrasing.

### IN-03: Repeated javascript:-URL scan block is duplicated verbatim across five tests

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:531-536,557-562,624-629,649-654` (and the title test 531-536)
**Issue:** The "no `[href]`/`[src]` value starts with `javascript:`" scan is
copy-pasted in five end-to-end XSS tests. Since `escape()` and `hasOnAttribute()`
were already (correctly) extracted to `describe` scope, this block is the one
remaining duplication and is a maintenance hazard — a fix to the detection logic
must be applied in five places.
**Fix:** Extract a `describe`-scope helper, e.g.:
```typescript
function hasJavascriptUrl(root: Element): boolean {
    return Array.from(root.querySelectorAll("[href],[src]")).some(el =>
        (el.getAttribute("href") || "").toLowerCase().startsWith("javascript:") ||
        (el.getAttribute("src") || "").toLowerCase().startsWith("javascript:"));
}
```

### IN-04: `as unknown as number` cast on `coercibleSkipCount` is the established escape-hatch pattern but lacks a runtime guard note beyond the existing comment

**File:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts:710-713`
**Issue:** Per the project CLAUDE.md, `as Type` casts should be avoided without
runtime validation. Here `as unknown as number` is intentionally used to defeat
the TypeScript type for the characterization probe, and the surrounding comment
(lines 688-699) thoroughly explains why. This is acceptable for a deliberate
type-defeating probe, but it is the one place in the file that violates the
"no unguarded cast" guideline, so it is recorded here as Info for completeness —
no change required. The probe and its assertions are correct.
**Fix:** None required; the existing comment block is sufficient justification.
Optionally annotate the cast with a `// eslint-disable` if the linter flags it.

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
