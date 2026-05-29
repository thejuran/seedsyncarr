# Phase 98: Medium-Priority Angular Coverage - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 1 (extend in place)
**Analogs found:** 1 / 1 (same file is primary analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` | test | request-response (DOM) | itself (lines 300-338 for XSS; lines 29-42 for modal-read idiom) | exact |

Only one file is touched in this phase. All new test blocks are added to the existing 463-line spec. The analog for every new test is a block already in that same file.

---

## Pattern Assignments

### New `describe("XSS / escapeHtml coverage")` block (D-04 + D-03/D-05)

This nested `describe` does not exist yet. It is added inside the outer `describe("Testing confirm modal service", ...)` at line 5, after the existing tests, before the closing `});` at line 463.

---

#### A. TestBed providers setup

**Analog:** lines 8-16 of the spec — reuse with zero changes.

```typescript
// confirm-modal.service.spec.ts lines 8-16
beforeEach(() => {
    TestBed.configureTestingModule({
        providers: [
            ConfirmModalService
        ]
    });

    service = TestBed.inject(ConfirmModalService);
});
```

No `provideHttpClient` is needed. `RendererFactory2` is provided automatically by `BrowserDynamicTestingModule` (wired in `src/angular/src/test.ts`). The new `describe` block does NOT add its own `beforeEach`/`afterEach` — it relies entirely on the outer-scope ones already present at lines 8-23.

---

#### B. DOM teardown — reuse exactly

**Analog:** lines 18-23 of the spec.

```typescript
// confirm-modal.service.spec.ts lines 18-23
afterEach(() => {
    // Clean up any modals left in the DOM
    document.querySelectorAll(".modal").forEach(el => el.remove());
    document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
    document.body.classList.remove("modal-open");
});
```

The new XSS tests do NOT click any button (no `destroyModal` call), so the modal stays open until `afterEach` removes it. No additional cleanup is needed.

---

#### C. fakeAsync + tick() + querySelector modal-read pattern

**Analog:** lines 29-42 — the canonical modal-read idiom used by every other test in this file.

```typescript
// confirm-modal.service.spec.ts lines 29-42
it("should create modal with title and body", fakeAsync(() => {
    const options: ConfirmModalOptions = {
        title: "Test Title",
        body: "Test Body"
    };

    service.confirm(options);
    tick();

    const modal = document.querySelector(".modal");
    expect(modal).toBeTruthy();
    expect(modal!.querySelector(".modal-title")!.textContent).toBe("Test Title");
    expect(modal!.querySelector(".modal-body p")!.textContent).toBe("Test Body");
}));
```

Pattern rules extracted from this block:
- `service.confirm(options)` then `tick()` — one `tick()` is sufficient; the modal is in the DOM after this call.
- `document.querySelector(".modal")` — the modal element carries classes `modal fade show` (source lines 82-84); `.modal` matches it.
- All DOM reads happen after `tick()`.
- The XSS tests follow the same shape: call `service.confirm`, `tick()`, then assert on `document.querySelector(".modal")`.

---

#### D. Existing partial XSS assertion style — the idiom to supersede

**Analog:** lines 300-338 — the two existing partial XSS tests.

```typescript
// confirm-modal.service.spec.ts lines 300-320
it("should sanitize HTML in title and body to prevent XSS", fakeAsync(() => {
    const options: ConfirmModalOptions = {
        title: "<script>alert(\"xss\")</script>",
        body: "<img src=x onerror=alert(1)> test"
    };

    service.confirm(options);
    tick();

    const modal = document.querySelector(".modal");
    const modalTitle = modal!.querySelector(".modal-title");
    const modalBodyP = modal!.querySelector(".modal-body p");

    // The literal tag strings should appear as text content, not as injected elements
    expect(modalTitle!.textContent).toContain("<script>");
    expect(modalBodyP!.textContent).toContain("<img src=x onerror=alert(1)>");

    // No actual script or img elements should be injected inside the modal
    expect(modal!.querySelector("script")).toBeNull();
    expect(modal!.querySelector("img")).toBeNull();
}));
```

```typescript
// confirm-modal.service.spec.ts lines 322-338
it("should render HTML entities as literal text in body", fakeAsync(() => {
    const options: ConfirmModalOptions = {
        title: "Confirm",
        body: "Delete <b>file.txt</b> from server?"
    };

    service.confirm(options);
    tick();

    const modalBodyP = document.querySelector(".modal-body p");

    // The <b> tags should appear as literal text, not as a bold element
    expect(modalBodyP!.textContent).toContain("<b>file.txt</b>");

    // No actual <b> element should be created inside the modal body paragraph
    expect(modalBodyP!.querySelector("b")).toBeNull();
}));
```

**What these tests establish (keep):**
- `textContent.toContain("<script>")` — proves the tag chars rendered as visible text (browser-decoded).
- `querySelector("script")` is `null` — proves no parsed `<script>` element exists.
- `querySelector("img")` / `querySelector("b")` is `null` — proves no injected element exists.

**What D-03 adds on top (the superseding assertions):**
- `modal.innerHTML.toContain("&lt;script&gt;")` — proves entity encoding occurred (not silent stripping by the browser parser; `textContent` alone cannot distinguish between the two).
- `on*` attribute walk across `querySelectorAll("*")` — proves no event-handler attribute is present on any element in the modal subtree.
- `href`/`src` `javascript:` check — proves no injected anchor or script-src attribute escaped neutralization.
- Coverage of all six inputs (title, body, okBtn, cancelBtn, okBtnClass, cancelBtnClass) — lines 300-338 only cover title and body.

The D-06 default is to supersede these two tests with the fuller D-03 assertions while preserving the `textContent`-contains and `querySelector`-null idioms they establish.

---

#### E. `data-action` button selector pattern

**Analog:** lines 80, 97 — used to locate the ok/cancel buttons.

```typescript
// confirm-modal.service.spec.ts lines 80, 97
const okButton = document.querySelector("[data-action=\"ok\"]") as HTMLButtonElement;
const cancelButton = document.querySelector("[data-action=\"cancel\"]") as HTMLButtonElement;
```

The class-attribute payload tests (D-05 for `okBtnClass`/`cancelBtnClass`) will use this selector after `tick()` to access the rendered button and inspect its parsed attributes. Source lines 111-112 confirm the `data-action` attribute is injected directly from the template literal, not through `escapeHtml`, so the selector always resolves.

---

#### F. `escapeHtml` private-static access pattern (D-04)

**Analog:** CONTEXT.md code context + TypeScript runtime behavior — no prior occurrence in the spec to copy, but the pattern is:

```typescript
// Access pattern for private static method — idiomatic TypeScript test pattern
// (ConfirmModalService as any).escapeHtml(input)
const result = (ConfirmModalService as any).escapeHtml(input);
```

This casts the class constructor to `any`, bypassing TypeScript's compile-time `private` check. At runtime `escapeHtml` exists as a regular function on the class object. This is categorically different from the CLAUDE.md rule about value casts — the class constructor cannot be null, so no runtime guard is needed.

Recommended wrapper for the D-04 `describe` block (defined once, called in every `it`):

```typescript
function escape(s: string): string {
    return (ConfirmModalService as any).escapeHtml(s);
}
```

---

#### G. `on*` attribute walk helper (D-03)

No existing occurrence in the spec. The correct DOM API approach (CSS has no attribute-name prefix selector; `querySelectorAll("[on*=...]")` matches attribute *values*, not attribute *names*):

```typescript
// Define once at the top of the new describe block; used by every end-to-end it-block
function hasOnAttribute(root: Element): boolean {
    const allElements = Array.from(root.querySelectorAll("*"));
    allElements.push(root);
    for (const el of allElements) {
        for (let i = 0; i < el.attributes.length; i++) {
            if (el.attributes[i].name.startsWith("on")) {
                return true;
            }
        }
    }
    return false;
}
```

---

#### H. `innerHTML` entity-string assertion (D-03)

The distinction from `textContent`:
- `modal.innerHTML` — serialized inner HTML; entity references appear as literal strings (e.g. `&lt;`).
- `modal.textContent` — concatenated text nodes; browser-decoded (e.g. `<`).

Pattern for the entity-presence assertion:

```typescript
// After tick():
const modal = document.querySelector(".modal")!;
expect(modal.innerHTML).toContain("&lt;script&gt;");   // proves encoding, not stripping
expect(modal.innerHTML).toContain("&lt;/script&gt;");
```

Contrast with the existing idiom at line 314 which uses `textContent` — that idiom is correct for "visible text" assertions but is insufficient to prove that escaping occurred (a browser that silently stripped the tag would also pass a `textContent`-only assertion). Use `innerHTML` for entity checks, `textContent` for visible-text checks.

---

#### I. `javascript:` href/src assertion (D-03)

The modal template (source lines 100-116) contains no `<a>` or `<img>` elements in benign use. Any such element in the rendered modal after a payload is an injection artifact. Pattern:

```typescript
const anchors = Array.from(modal.querySelectorAll("[href],[src]"));
const hasJsUrl = anchors.some(el =>
    (el.getAttribute("href") || "").toLowerCase().startsWith("javascript:") ||
    (el.getAttribute("src") || "").toLowerCase().startsWith("javascript:")
);
expect(hasJsUrl).toBe(false);
```

---

#### J. Class-attribute context — `data-action` button located by selector, attribute inspected directly

**Analog for setup:** lines 208-224 — the existing custom-button-classes test.

```typescript
// confirm-modal.service.spec.ts lines 208-224
it("should use custom button classes", fakeAsync(() => {
    const options: ConfirmModalOptions = {
        title: "Test",
        body: "Test",
        okBtnClass: "btn btn-danger",
        cancelBtnClass: "btn btn-outline-secondary"
    };

    service.confirm(options);
    tick();

    const okButton = document.querySelector("[data-action=\"ok\"]");
    const cancelButton = document.querySelector("[data-action=\"cancel\"]");

    expect(okButton!.classList.contains("btn-danger")).toBe(true);
    expect(cancelButton!.classList.contains("btn-outline-secondary")).toBe(true);
}));
```

The D-05 class-attribute tests follow this exact call shape. The difference is the payload (`"btn\" onmouseover=\"alert(1)"` instead of `"btn btn-danger"`) and the assertions (no `onmouseover` attribute via the `hasOnAttribute` helper, plus `innerHTML.toContain("&quot;")` for the encoded `"`).

---

## Shared Patterns

### fakeAsync + tick() + document.querySelector(".modal")
**Source:** `confirm-modal.service.spec.ts` lines 29-42 (and repeated in every subsequent `fakeAsync` test)
**Apply to:** All six D-03/D-05 end-to-end tests

```typescript
service.confirm(options);
tick();
const modal = document.querySelector(".modal")!;
```

### afterEach DOM cleanup
**Source:** `confirm-modal.service.spec.ts` lines 18-23
**Apply to:** All new tests — inherited from outer `describe` scope, no duplication needed

### `data-action` selector for button access
**Source:** `confirm-modal.service.spec.ts` lines 80, 97, 147, 165, 183, 219, 348, 380, 427
**Apply to:** D-05 class-attribute tests that inspect parsed button attributes

---

## No Analog Found

All new test additions have a close analog in the existing spec. The two new helper functions
(`escape()` and `hasOnAttribute()`) have no prior occurrence in the spec but follow idiomatic
Jasmine/DOM patterns documented in RESEARCH.md.

| Item | Reason |
|------|--------|
| `escape()` wrapper for `(ConfirmModalService as any).escapeHtml` | No prior private-static access in this spec; pattern is standard TypeScript test practice, confirmed in CONTEXT.md |
| `hasOnAttribute(root)` helper | No prior `on*` attribute walk in this spec; CSS has no prefix-name selector, so this helper is the only correct approach |

---

## Key Decisions Carried Forward

| Decision | Pattern Implication |
|----------|---------------------|
| D-01: escape set is `&<>"'` only | D-04 backtick/U+2028/U+2029 test asserts identity (no escaping) — documents intentional omission |
| D-02: `skipCount` is numeric, exempt | One asserting test documents exemption; no `escapeHtml` call added to source |
| D-03: DOM + innerHTML string assertions | `querySelector("script")` null + `hasOnAttribute` + `innerHTML.toContain("&lt;...")` — all three layers per payload |
| D-04: direct `escapeHtml` unit test | `(ConfirmModalService as any).escapeHtml` wrapper; ordering test input `"<"` expects `"&lt;"` not `"&amp;lt;"` |
| D-05: all six inputs | Six separate `it` blocks (or one parameterized-style `it` per input group) — two HTML contexts require distinct payloads |
| D-06: extend existing file | One nested `describe("XSS / escapeHtml coverage")` block appended before line 463 closing `});` |

---

## Source Template (innerHTML sink — confirmed lines 100-116)

The template used in `createModal` at source lines 100-116 for planner reference:

```
<h5 class="modal-title" id="confirm-modal-title">${safeTitle}</h5>     ← element content
<p>${safeBody}</p>                                                       ← element content
<button type="button" class="${safeCancelBtnClass}" data-action="cancel">${safeCancelBtn}</button>   ← class attr + element content
<button type="button" class="${safeOkBtnClass}" data-action="ok">${safeOkBtn}</button>               ← class attr + element content
```

This confirms the two HTML contexts (element content vs double-quoted class attribute) and the exact selector paths (`[data-action="cancel"]`, `[data-action="ok"]`, `.modal-title`, `.modal-body p`) that the new tests use to locate rendered elements.

---

## Metadata

**Analog search scope:** `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` (single file, 463 lines — full read)
**Source file read:** `src/angular/src/app/services/utils/confirm-modal.service.ts` (192 lines — full read)
**Files scanned:** 2
**Pattern extraction date:** 2026-05-29
