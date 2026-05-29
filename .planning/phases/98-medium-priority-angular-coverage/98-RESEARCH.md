# Phase 98: Medium-Priority Angular Coverage - Research

**Researched:** 2026-05-29
**Domain:** Jasmine/Karma unit testing — XSS coverage for a private-static HTML-escape helper and its downstream innerHTML sink
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Escape-set scope (trivial-fix window):** Do NOT expand the escape set beyond `&<>"'`.
Both HTML contexts in use (element content, double-quoted class attribute) are fully protected by
this set. Backtick, U+2028, U+2029, and null byte are NOT XSS-exploitable in these contexts.
The test documents this reasoning so the omission reads as intentional, not an oversight.

**D-02 — skipMessage exemption:** `skipMessage` (lines 59-64) is the one un-escaped
interpolation site. It interpolates only `options.skipCount` (a TypeScript `number`) and a
literal `"s"` — no attacker-controlled string can reach it. Do NOT route `skipCount` through
`escapeHtml`. The test asserts the value is numeric and documents why the site is exempt.

**D-03 — "No executable markup" assertions:** Assert via the parsed DOM AND via raw innerHTML
string:
- `modalElement.querySelector("script")` is null for every attacker payload.
- No element in the modal subtree carries an `on*` event-handler attribute (walk attributes,
  assert none start with "on").
- No `href`/`src` attribute value contains `javascript:`.
- String-assert raw `innerHTML` contains the escaped entities (e.g. `&lt;script&gt;`) — proves
  neutralization into inert text, not silent stripping.

**D-04 — Direct escapeHtml unit test:** Assert each metacharacter maps to its entity:
`&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`, `"`→`&quot;`, `'`→`&#039;`. Include an ordering test
confirming `&`-first replacement does not double-escape entity ampersands it produces.

**D-05 — All six inputs:** Cover attacker payloads in all six escaped inputs individually:
`title`, `body`, `okBtn`, `cancelBtn`, `okBtnClass`, `cancelBtnClass`. Class-attribute inputs
need attribute-breakout payloads distinct from element-content payloads.

**D-06 — Extend existing spec file:** Use the existing spec's standalone TestBed pattern.
Extend `confirm-modal.service.spec.ts`, do not create a parallel file. Supersede the two
partial XSS tests at lines 300 and 322.

### Claude's Discretion

- Exact test function names and `describe` block grouping.
- Whether to assert `on*`-attribute absence via a helper walking `querySelectorAll("*")` vs a
  flat attribute scan — default to whichever reads cleanest.
- Whether to keep, extend, or supersede the two existing partial XSS tests (lines 300, 322) —
  default to superseding with the fuller D-03/D-05 assertions while preserving any unique
  assertion they make.

### Deferred Ideas (OUT OF SCOPE)

- Expanding escape set to backtick/U+2028/U+2029/null-byte.
- Routing `skipCount` through `escapeHtml`.
- Any `innerHTML`→Renderer2 refactor (v1.4.0 if ever).
- Any bug surfaced that exceeds the trivial-fix window (>10 net lines, public-API change,
  observable-behavior change) → v1.4.0, with a STATE.md entry.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVMED-04 | `confirm-modal.service.ts` `escapeHtml` is covered end-to-end for XSS — every metacharacter (`&<>"'`), attacker payloads in title/body/button labels/classes, resulting `innerHTML` has no executable markup, no bypass call site (`src/angular/src/app/services/utils/confirm-modal.service.ts:33-40`) | D-01 through D-06 fully map to the four coverage points; existing spec harness is directly reusable. |
</phase_requirements>

---

## Summary

Phase 98 adds full end-to-end XSS coverage for `ConfirmModalService.escapeHtml` in a single
plan (98-01). The source under test is a 192-line Angular service that builds modal HTML via a
direct `innerHTML` assignment (line 100). The only sanitization layer between caller-supplied
strings and that innerHTML sink is the `private static escapeHtml` method (lines 33-40), which
escapes five metacharacters (`& < > " '`) in the correct ampersand-first order. All six
attacker-influenceable inputs (`title`, `body`, `okBtn`, `okBtnClass`, `cancelBtn`,
`cancelBtnClass`) pass through this helper before interpolation. The one non-escaped
interpolation site (`skipMessage`, lines 59-64) is safe because it interpolates only a TypeScript
`number`, not a string.

The existing 463-line spec already has a full `fakeAsync` + `TestBed` harness and two partial
XSS tests (lines 300-338) that establish the `textContent`+`querySelector` idiom. The new tests
extend this harness without any setup changes — `ConfirmModalService` has no HTTP dependency, so
no `provideHttpClient` is needed. The plan supersedes the two partial XSS tests with fuller D-03
assertions and adds D-04/D-05 coverage.

The Karma coverage reporter is configured for HTML output only (`karma.conf.js` lines 23-26);
no `check.global` thresholds exist yet (those are Phase 100, RATCHET-02). Adding these tests
will improve `confirm-modal.service.ts` branch and statement coverage but cannot trip a coverage
threshold that does not yet exist.

**Primary recommendation:** Extend the existing spec with one new `describe` block containing
five `it` blocks covering D-04 (direct `escapeHtml` unit test) and D-03/D-05 (end-to-end DOM
assertions for each of the six inputs), then supersede the two existing partial XSS tests.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML escaping of user-supplied strings | Frontend service (Angular) | — | `escapeHtml` is a private static helper inside a browser-side service; no server is involved |
| innerHTML assignment / modal rendering | Frontend service (Angular) | — | `createModal` builds the modal DOM directly in the browser via `innerHTML`; Angular template compilation / DI is not used for this output |
| XSS test assertions | Jasmine/Karma test runner | Chrome (headless) parser | DOM assertions depend on the browser HTML parser running after `innerHTML` assignment — Chrome headless is the execution context in CI |

---

## Standard Stack

No new packages are introduced by this phase. All test infrastructure is already installed.

### Core (already installed)
| Library | Version | Purpose | Confirmed |
|---------|---------|---------|-----------|
| jasmine-core | ^6.2.0 | Test framework | [VERIFIED: package.json] |
| karma | ^6.4.4 | Test runner | [VERIFIED: package.json] |
| karma-chrome-launcher | ^3.2.0 | Headless Chrome execution | [VERIFIED: package.json] |
| karma-coverage | ^2.2.1 | Istanbul coverage reporting | [VERIFIED: package.json] |
| @angular/core (testing) | ^21.2.14 | `TestBed`, `fakeAsync`, `tick` | [VERIFIED: package.json] |

### Package Legitimacy Audit

> No new packages are installed by this phase. This section is present for completeness.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | No new installs — this phase extends an existing spec file only |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Test caller (Jasmine it-block)
        |
        | service.confirm(options)   [end-to-end path]
        v
ConfirmModalService.createModal()
        |
        | ConfirmModalService.escapeHtml(input)   [×6]
        v
safe* variables (escaped strings)
        |
        | template literal → this.modalElement!.innerHTML = `...`
        v
Browser HTML parser (Chrome headless / Karma)
        |
        +---> Rendered DOM subtree (document.querySelector(".modal"))
                    |
                    +--- DOM assertions (querySelector, querySelectorAll, innerHTML string)
                    |         [D-03: script null, no on*, no javascript:, entity strings]
                    |
                    +--- Direct escapeHtml unit test
                              (ConfirmModalService as any).escapeHtml(input)
                              [D-04: metacharacter→entity, &-first ordering]
```

### Existing Project Structure (relevant portion)

```
src/angular/src/app/
├── services/utils/
│   └── confirm-modal.service.ts        # source under test (lines 33-40, 51-56, 59-64, 100-116)
└── tests/unittests/services/utils/
    └── confirm-modal.service.spec.ts   # EXTEND THIS FILE (463 lines, do not create parallel)
```

### Pattern 1: TestBed Setup (existing — no changes needed)

The existing spec uses a minimal `TestBed.configureTestingModule` with only `ConfirmModalService`
in `providers`. `ConfirmModalService` uses `RendererFactory2`, which is provided automatically by
`BrowserDynamicTestingModule` (injected by `test.ts` via `getTestBed().initTestEnvironment`).
No `provideHttpClient` is needed — the service has no HTTP dependency.

```typescript
// Source: existing confirm-modal.service.spec.ts:8-16 [VERIFIED: codebase read]
beforeEach(() => {
    TestBed.configureTestingModule({
        providers: [
            ConfirmModalService
        ]
    });
    service = TestBed.inject(ConfirmModalService);
});
```

**Nothing about this setup changes for the new XSS tests.** The same `service` reference is
used; the same `fakeAsync` + `tick()` pattern activates the modal.

### Pattern 2: DOM Teardown (existing — reuse exactly)

The existing `afterEach` cleans up all modal artifacts reliably:

```typescript
// Source: existing confirm-modal.service.spec.ts:18-23 [VERIFIED: codebase read]
afterEach(() => {
    document.querySelectorAll(".modal").forEach(el => el.remove());
    document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
    document.body.classList.remove("modal-open");
});
```

This is sufficient. The new XSS tests do not click any button (modal stays open), so `destroyModal`
is not called — the `afterEach` cleanup is what removes the modal. No focus-restoration side
effects occur in the new tests because no button is clicked and `destroyModal` is not triggered.

**Note:** The `setTimeout(() => cancelButton.focus(), 0)` in `createModal` (line 167) fires after
`tick()`. Existing tests that check `document.activeElement` call `tick()` a second time. The XSS
tests do not care about focus — one `tick()` call after `service.confirm(options)` is sufficient
to have the modal in the DOM.

### Pattern 3: Accessing private static `escapeHtml` (D-04)

`escapeHtml` is `private static`. The established project pattern (confirmed in CONTEXT.md
code context and confirmed viable by TypeScript's runtime behavior) is a type cast:

```typescript
// [VERIFIED: CONTEXT.md code context + TypeScript runtime semantics]
const result = (ConfirmModalService as any).escapeHtml(input);
```

This is idiomatic for testing private helpers in Angular/TypeScript projects. The cast
bypasses the TypeScript compiler's access check without any runtime overhead. The global
`CLAUDE.md` rule "Never use `as Type` casts without runtime validation" refers to
casting values to specific types to avoid null errors — casting the class itself to `any` to
call a private method in a test is a distinct, well-accepted pattern. The method is pure and
deterministic; no runtime validation concern applies.

### Pattern 4: "No executable markup" DOM assertions (D-03)

**String assertion on raw innerHTML** (proves entity encoding, not silent browser stripping):
```typescript
// [ASSUMED: standard DOM API — innerHTML returns the serialized string of the subtree]
const modal = document.querySelector(".modal")!;
expect(modal.innerHTML).toContain("&lt;script&gt;");
```

**`on*` attribute walk** — cleanest approach is a helper function defined once in the new
`describe` block:
```typescript
// [ASSUMED: standard DOM API — getAttribute, Element.attributes]
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

This is preferable to `querySelectorAll("[on*]")` which is not a valid CSS attribute-name
prefix selector in standard browsers. Walking `element.attributes` is the correct approach.

**`javascript:` in href/src** — the modal template contains no `<a>` or `<img>`/`<script>`
elements in benign use, so any such element in the rendered modal is itself an injection
artifact. A targeted check:
```typescript
// [ASSUMED: standard DOM API]
const anchors = Array.from(modal.querySelectorAll("[href],[src]"));
const hasJsUrl = anchors.some(el =>
    (el.getAttribute("href") || "").toLowerCase().startsWith("javascript:") ||
    (el.getAttribute("src") || "").toLowerCase().startsWith("javascript:")
);
expect(hasJsUrl).toBe(false);
```

### Anti-Patterns to Avoid

- **Asserting only `textContent`:** The existing partial XSS test at line 314 asserts
  `textContent.toContain("<script>")` — this passes even if the browser parser strips the
  tag without encoding it (benign stripping would also make `querySelector("script")` return
  null). D-03 requires the additional `innerHTML.toContain("&lt;script&gt;")` assertion to
  prove entity encoding, not stripping.
- **`querySelectorAll("[onfoo]")` for on* detection:** CSS attribute selectors match exact
  attribute names, not prefixes. Use the `attributes` loop pattern above.
- **Re-using the modal from a previous test:** The `afterEach` cleans up, but if a test
  function omits `tick()` after `service.confirm()`, the modal may not be in the DOM yet.
  Always call `tick()` before querying the DOM.
- **Forgetting the `&`-first ordering test:** The ordering test in D-04 must use an input
  containing `<` (not just `&`) and assert the output is `&lt;` (five chars), not
  `&amp;lt;` (eight chars). The test proves the already-introduced `&` in `&amp;` is not
  re-escaped by the `&` replacement.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `on*` attribute prefix selector | `querySelectorAll("[on*=]")` | `element.attributes` loop | CSS has no prefix-name selector; `[on*=...]` matches attribute *values* containing "on", not attribute *names* starting with "on" |
| Private static access | Reflection via `Object.getOwnPropertyDescriptor` | `(Class as any).method()` | Type cast to `any` is idiomatic, zero overhead, readable |

---

## Common Pitfalls

### Pitfall 1: innerHTML string-assertion returns entity-decoded text in some contexts
**What goes wrong:** `modal.innerHTML` returns the serialized *inner* HTML, which includes
entity references as literal strings (e.g. `&lt;`). `modal.textContent` returns the decoded
text (e.g. `<`). The test at line 314 correctly uses `textContent` to assert the rendered
visible text. D-03's string assertion on entity presence must use `.innerHTML`, not
`.textContent`.
**Why it happens:** `innerHTML` serializes the DOM back to HTML (preserving entities); `textContent`
concatenates text nodes (browser-decoded).
**How to avoid:** Use `modal.innerHTML` for `toContain("&lt;")` checks; use
`element.textContent` for "visible text" checks.
**Warning signs:** A test asserting `modal.innerHTML.toContain("<script>")` (decoded form)
that passes — that would mean the tag was injected, not escaped.

### Pitfall 2: `tick()` timing and `setTimeout(0)` for focus
**What goes wrong:** `createModal` schedules `cancelButton.focus()` via `setTimeout(..., 0)`
(line 167). Calling `tick()` once advances the microtask queue and renders the modal, but
also fires the `setTimeout(0)` callback. If a test then queries `document.activeElement`, it
gets the cancel button even if focus was not the intent of the test.
**Why it happens:** `fakeAsync` + `tick()` flushes all pending timers with delay ≤ the tick
value, including `setTimeout(0)`.
**How to avoid:** The XSS tests do not assert on focus, so this is a non-issue for D-03/D-04/D-05.
If a future test needs to query `document.activeElement` for a non-focus reason after opening
the modal, this behavior is expected and correct.

### Pitfall 3: `onfoo` as attribute value vs attribute name in assertion
**What goes wrong:** Writing `expect(modal.innerHTML).not.toContain(" on")` — this would
false-positive on any element with a text node containing "on" (e.g. a cancel button labelled
"Cancel action"). The assertion must check attribute *names*, not innerHTML substrings.
**Why it happens:** Payload like `" onmouseover="alert(1)` gets escaped to `&quot;
onmouseover=&quot;alert(1)` — the string "on" still appears in `innerHTML` as part of
inert text.
**How to avoid:** Use the `element.attributes` loop helper (see Pattern 4). It checks parsed
attribute names on the rendered DOM, not raw HTML string content.

### Pitfall 4: Browser parser behavior on attribute-context payloads
**What goes wrong:** The payload `" onmouseover="alert(1)` injected into
`class="${safeCancelBtnClass}"` — if `"` were NOT escaped, the parser would create an
attribute `onmouseover` on the button element. With `escapeHtml` escaping `"` to `&quot;`,
the full payload becomes part of the `class` attribute value (inert). The `on*` attribute
walk confirms this.
**Why it happens:** Chrome's HTML parser (used by Karma/headless Chrome) handles attribute
breakout exactly as specified by the HTML5 parsing algorithm — `&quot;` inside a
double-quoted attribute value is decoded to `"` in the attribute value text but does NOT
close the attribute.
**How to avoid:** The DOM assertion is the correct ground truth — after `innerHTML` assignment,
inspect the *parsed* DOM, not the raw string. A raw `innerHTML` string check is a secondary
confirmation that escaping occurred; the DOM attribute walk is the primary XSS proof.

### Pitfall 5: `skipMessage` assertion — don't over-test
**What goes wrong:** Adding `escapeHtml` assertions to the `skipCount` path. The `skipCount`
interpolation is `${options.skipCount}` — TypeScript enforces this is `number | undefined`.
Numbers cannot contain HTML metacharacters. The existing tests at lines 253-298 already
exercise `skipCount` rendering; no new XSS assertion is needed for it.
**How to avoid:** Confirm via D-02 — document in a comment that the site is exempt and why,
then move on. Do not route numbers through `escapeHtml`.

---

## Code Examples

### D-04: Direct metacharacter + ordering unit test

```typescript
// [VERIFIED: based on escapeHtml source lines 33-40, codebase read]
describe("escapeHtml (private static unit)", () => {
    function escape(s: string): string {
        return (ConfirmModalService as any).escapeHtml(s);
    }

    it("should escape each metacharacter to its HTML entity", () => {
        expect(escape("&")).toBe("&amp;");
        expect(escape("<")).toBe("&lt;");
        expect(escape(">")).toBe("&gt;");
        expect(escape("\"")).toBe("&quot;");
        expect(escape("'")).toBe("&#039;");
    });

    it("should replace & first so entity ampersands are not double-escaped", () => {
        // Input contains raw '<'; after escaping: '&lt;' (not '&amp;lt;')
        expect(escape("<")).toBe("&lt;");
        // Input contains raw '&'; after escaping: '&amp;'
        expect(escape("&")).toBe("&amp;");
        // Combined: '<&>' becomes '&lt;&amp;&gt;'
        expect(escape("<&>")).toBe("&lt;&amp;&gt;");
    });

    it("should handle a combined attacker payload correctly", () => {
        expect(escape("<script>alert(\"xss\")</script>"))
            .toBe("&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;");
    });

    it("should document that backtick, U+2028, U+2029, and null byte are not escaped " +
       "(not exploitable in element-content or double-quoted-attribute contexts)", () => {
        // Backtick: not a metacharacter in either HTML context used by this service.
        // This service uses only: element content (h5, p, button text)
        // and double-quoted class attributes. Backtick closes neither.
        expect(escape("`")).toBe("`");
        // U+2028 (line separator) and U+2029 (paragraph separator): not HTML metacharacters.
        expect(escape("\u2028")).toBe("\u2028");
        expect(escape("\u2029")).toBe("\u2029");
        // Null byte: not exploitable in these contexts; browser strips/ignores it.
        expect(escape(" ")).toBe(" ");
    });
});
```

### D-03 / D-05: End-to-end DOM assertions for element-content inputs

```typescript
// [VERIFIED: based on existing spec pattern lines 300-320, codebase read]
it("should produce no executable markup when title contains a script payload", fakeAsync(() => {
    service.confirm({ title: "<script>alert(1)</script>", body: "x" });
    tick();

    const modal = document.querySelector(".modal")!;

    // DOM assertion: no parsed script element
    expect(modal.querySelector("script")).toBeNull();
    // DOM assertion: no on* attributes anywhere in the subtree
    expect(hasOnAttribute(modal)).toBe(false);
    // String assertion: payload is encoded as entities, not stripped
    expect(modal.innerHTML).toContain("&lt;script&gt;");
    expect(modal.innerHTML).toContain("&lt;/script&gt;");
}));
```

### D-03 / D-05: End-to-end DOM assertions for class-attribute inputs

```typescript
// [VERIFIED: based on source line 111-112 (class="${safeCancelBtnClass}"), codebase read]
it("should neutralize an attribute-breakout payload in cancelBtnClass", fakeAsync(() => {
    service.confirm({
        title: "t",
        body: "b",
        cancelBtnClass: "btn\" onmouseover=\"alert(1)"
    });
    tick();

    const modal = document.querySelector(".modal")!;
    const cancelBtn = modal.querySelector("[data-action=\"cancel\"]")!;

    // DOM assertion: the button has no onmouseover attribute
    expect(cancelBtn.getAttribute("onmouseover")).toBeNull();
    // DOM assertion: no on* attributes in the entire modal
    expect(hasOnAttribute(modal)).toBe(false);
    // String assertion: the quote was encoded, keeping the payload inside the class value
    expect(modal.innerHTML).toContain("&quot;");
}));
```

### D-02: skipMessage bypass-audit assertion

```typescript
// [VERIFIED: source lines 59-64, codebase read]
it("should document that skipCount interpolation is exempt from escapeHtml " +
   "because skipCount is a TypeScript number (not an attacker-controlled string)", fakeAsync(() => {
    service.confirm({ title: "t", body: "b", skipCount: 3 });
    tick();

    const modal = document.querySelector(".modal")!;
    const skipP = modal.querySelectorAll(".modal-body p")[1]!;

    // The value rendered is the numeric literal '3', not a string from attacker input.
    // TypeScript type: number | undefined — numbers cannot contain HTML metacharacters.
    expect(skipP.textContent).toContain("3 files will be skipped");
    // No injected elements from the skipCount path
    expect(modal.querySelector("script")).toBeNull();
    expect(hasOnAttribute(modal)).toBe(false);
}));
```

---

## Research Findings by Investigation Area

### Area 1: `escapeHtml` access pattern (D-04)

[VERIFIED: codebase read, CONTEXT.md code context]

`escapeHtml` is declared `private static` at line 33. The method is accessible in tests via
`(ConfirmModalService as any).escapeHtml(input)`. This pattern is already described in CONTEXT.md
code context as the canonical approach. TypeScript `private` is compile-time only; the method
exists on the class constructor as a regular function at runtime.

The TypeScript `as any` cast here is on the class constructor, not on a value that could be null.
This is categorically different from the global CLAUDE.md rule about value casts — no runtime
validation is needed because calling a class method cannot fail due to null.

### Area 2: TestBed, fakeAsync, and DOM harness patterns

[VERIFIED: codebase read — spec lines 1-24]

- `TestBed.configureTestingModule` with `providers: [ConfirmModalService]` is sufficient.
  No HTTP providers needed.
- `BrowserDynamicTestingModule` (injected by `test.ts`) provides `RendererFactory2`, which the
  service constructor requires.
- `fakeAsync` + one `tick()` is sufficient to have the modal in the DOM after `service.confirm()`.
- `afterEach` at lines 18-23 cleans up `".modal"`, `".modal-backdrop"`, and `body.modal-open`
  class. This is the exact teardown pattern to reuse.
- Modal query: `document.querySelector(".modal")` — the modal element has class `modal fade show`
  (line 83-84 of service).
- The `setTimeout(() => cancelButton.focus(), 0)` fires during `tick()`. XSS tests that do not
  assert focus are unaffected.

### Area 3: Two HTML contexts and canonical attacker payloads

[VERIFIED: source lines 100-116, codebase read]

**Context A — Element content** (title, body, okBtn, cancelBtn):
```html
<h5 class="modal-title" id="confirm-modal-title">${safeTitle}</h5>
<p>${safeBody}</p>
<button ... >${safeCancelBtn}</button>
<button ... >${safeOkBtn}</button>
```
Relevant payloads:
- `<script>alert(1)</script>` — tests `<` and `>` escaping
- `<img src=x onerror=alert(1)>` — tests `<` / `>` and unquoted `onerror`
- `&amp;lt;` — tests that `&` is escaped first (regression: reorder would yield `&amp;lt;`)
- `'test'` — tests single-quote escaping (less critical in element content, but in scope)

**Context B — Double-quoted class attribute** (okBtnClass, cancelBtnClass):
```html
<button type="button" class="${safeCancelBtnClass}" data-action="cancel">
<button type="button" class="${safeOkBtnClass}" data-action="ok">
```
Relevant payloads:
- `" onmouseover="alert(1)` — attribute-value breakout via `"` injection; `escapeHtml`
  converts `"` to `&quot;`, keeping the payload inside the class value
- `"><script>alert(1)</script><b class="` — injection that attempts to close the attribute
  AND the tag; both `"` and `<`/`>` are escaped
- `btn btn-danger" onclick="evil()` — direct event-handler injection attempt

### Area 4: `on*` attribute absence assertion cleanly in Jasmine

[VERIFIED: DOM API specification — ASSUMED for browser-specific behavior details]

The correct approach is walking `element.attributes` rather than using a CSS selector. CSS has no
prefix-name selector syntax. `querySelectorAll("[onfoo]")` would only match elements with an
attribute literally named `onfoo`, not a wildcard over attribute names starting with `on`.

The helper function pattern (defined once in the new describe block, used by multiple `it` blocks)
is the cleanest Jasmine approach. Jasmine itself has no built-in attribute-name assertion utility.

Chrome headless (used by KarmaCI) parses `innerHTML` using the full HTML5 parsing algorithm.
After parsing, event-handler attributes appear as named attributes on the DOM element — they are
not stored as raw strings. `el.attributes[i].name` returns the lowercase attribute name as
specified.

### Area 5: `&`-first ordering regression test determinism

[VERIFIED: source lines 34-39, codebase read]

The replacement chain is:
1. `& → &amp;`
2. `< → &lt;`
3. `> → &gt;`
4. `" → &quot;`
5. `' → &#039;`

If step 1 is reordered to run after step 2, then `<` → `&lt;` and then `&lt;` → `&amp;lt;`
(double-escape). The deterministic regression test:
- Input: `"<"` (one char, U+003C)
- Expected: `"&lt;"` (five chars)
- NOT expected: `"&amp;lt;"` (eight chars — the double-escape artifact)

This is fully deterministic; there are no async or timer concerns in `escapeHtml`.

### Area 6: Karma/Angular version and spec setup currency

[VERIFIED: package.json, karma.conf.js, test.ts, angular.json — all codebase reads]

- Angular: `^21.2.14` (confirmed). Angular 21 uses `BrowserDynamicTestingModule` for Karma
  tests — no zoneless / standalone-component spec module change required for this service.
- Jasmine: `^6.2.0` (`jasmine-core`), `~5.1.0` (`karma-jasmine`).
- Karma: `^6.4.4` with `karma-chrome-launcher ^3.2.0`.
- The existing spec does NOT use `provideHttpClient` — correct, because `ConfirmModalService`
  has no HTTP dependency. The new tests do not introduce any new imports.
- `TestBed.configureTestingModule({ providers: [ConfirmModalService] })` with
  `BrowserDynamicTestingModule` (from `test.ts` `initTestEnvironment`) is the current post-v1.1.2
  pattern for this service and requires no change.

### Area 7: Coverage mechanics and threshold risk

[VERIFIED: karma.conf.js lines 23-26, v1.3.0-COVERAGE-BASELINE.md — codebase reads]

- `karma.conf.js` `coverageReporter` block has only `type: 'html'` and `dir: 'coverage/'`.
  There is NO `check.global` block. No Karma coverage thresholds will trip.
- Baseline (pre-Phase 97): Angular statements 83.34%, branches 69.01%, functions 79.73%,
  lines 84.21%. No per-file floors exist (explicitly excluded from v1.3.0 per REQUIREMENTS.md).
- Adding the Phase 98 tests will increase `confirm-modal.service.ts` coverage for the
  `escapeHtml` branch (currently zero direct tests for the helper) and for various inputs to
  `createModal`. This will nudge global Angular numbers upward, but the magnitude is small
  relative to the 2018-statement total.
- The ratchet thresholds are Phase 100 (RATCHET-02). Phase 98 cannot fail a threshold because
  none exist.

### Area 8: Trivial-fix window — deferred characters analysis

[VERIFIED: source lines 33-40, 100-116 — codebase read; HTML5 spec knowledge — ASSUMED]

The service's two HTML contexts:

**Element content:** Characters that could be exploited here require `<` or `>` to inject a
tag, or `&` to construct an entity sequence. The escape set `&<>"'` fully covers this context.
- Backtick: not a metacharacter in element content. Cannot close a tag or inject attributes.
- U+2028 / U+2029: these are JavaScript line-terminator characters relevant in `<script>` blocks
  and JSON. In element content (text nodes), they are rendered as whitespace-like characters by
  browsers; they do not affect HTML parsing. NOT exploitable here.
- Null byte (U+0000): browsers normalize null bytes in HTML parsing (replacing with U+FFFD or
  ignoring). The service has no `<script>` sink, so null byte injection is not exploitable.

**Double-quoted class attribute:** Characters that could be exploited here require `"` to close
the attribute value, or `>` to close the tag. The escape set covers both. Backtick cannot close
a double-quoted attribute. U+2028/U+2029 and null byte cannot close an attribute value.

D-01 conclusion is correct: no expansion needed. The documenting test (in D-04) makes the
intentional omission explicit.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Jasmine 6.2 + Karma 6.4.4 |
| Config file | `src/angular/karma.conf.js` (no changes needed) |
| Quick run command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` |
| Full suite command | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COVMED-04 | `escapeHtml` maps each of `& < > " '` to correct entity | unit | quick run command above | ✅ (extend existing) |
| COVMED-04 | `&`-first ordering does not double-escape entity ampersands | unit | quick run command above | ✅ (extend existing) |
| COVMED-04 | All six inputs produce no executable markup (DOM assertion) | integration (end-to-end within unit test) | quick run command above | ✅ (extend existing) |
| COVMED-04 | Class-attribute breakout payload (`" onmouseover=...`) is neutralized | integration | quick run command above | ✅ (extend existing) |
| COVMED-04 | `skipCount` site is numeric-only, exempt from escaping (documented) | unit | quick run command above | ✅ (extend existing) |
| COVMED-04 | No bypass call site — all six inputs routed through `escapeHtml` | code audit (test + comment) | N/A — static verification, documented in test | ✅ |

### Sampling Rate
- **Per task commit:** quick run command (spec file only — fast, ~5s)
- **Phase gate:** full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new spec files, no new
config, no framework installs.

---

## Open Questions

1. **Supersede vs fold existing partial XSS tests (lines 300-338)**
   - What we know: The test at line 300 asserts `textContent.toContain("<script>")` and
     `querySelector("script") null`; the test at line 322 asserts `textContent.toContain("<b>...`
     and `querySelector("b") null`. Both are `title`/`body` only.
   - What's unclear: Whether any assertion in lines 300-338 is unique and not covered by the
     fuller D-03 suite.
   - Recommendation: Supersede both. The D-03 assertions for `title` and `body` are strict
     supersets of lines 300-338 (they add `innerHTML` entity-string check and `on*`/`javascript:`
     DOM walk). If the planner wants belt-and-suspenders, extend them in-place rather than
     removing them — but the CONTEXT.md default is supersession.

2. **Separate `describe` block or inline within the outer `describe`**
   - What we know: The outer `describe` is "Testing confirm modal service"; no nested `describe`
     blocks exist in the current 463-line spec.
   - Recommendation: Add one nested `describe("XSS / escapeHtml coverage")` block containing
     the D-04 unit tests and D-03/D-05 end-to-end tests. This groups the new work cleanly
     without disturbing the flat structure of the existing tests.

---

## State of the Art

| Old Approach | Current Approach | Relevance to Phase 98 |
|--------------|------------------|----------------------|
| Angular module-based TestBed (pre-v1.1.2) | Standalone-component / provider pattern | This service is not a component — no change needed; existing setup is already current |
| Custom HTML escaping via hand-written replace chains | DomSanitizer / Renderer2 text nodes | The service uses hand-written replace — testing it correctly is this phase's job; migration is v1.4.0 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `(ConfirmModalService as any).escapeHtml(input)` is the correct TypeScript private-static access pattern in this codebase's test style | Area 1, Code Examples | Low — CONTEXT.md explicitly documents this pattern; it is standard TypeScript test practice |
| A2 | U+2028/U+2029 in element content are not exploitable in Chrome's HTML parser | Area 8 | Low — these are text-node characters; no HTML parser treats them as tag boundaries. Only exploitable in `<script>` context (none present) |
| A3 | `element.attributes[i].name` returns lowercase attribute names for `onerror`, `onmouseover`, etc. | Area 4 | Low — HTML5 spec mandates lowercase attribute names from HTML parser; confirmed by standard DOM spec |
| A4 | The `on*` attribute walk helper pattern is the correct approach for asserting no event-handler attributes | Area 4 | Low — no CSS prefix-name selector alternative exists; this is the only correct DOM API approach |

**All critical claims (TestBed setup, source structure, Karma config, coverage thresholds,
escapeHtml implementation) were verified directly from the codebase.**

---

## Environment Availability

> Step 2.6 applies: this phase runs `ng test` with ChromeHeadlessCI.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Angular CLI / Karma | ✓ | (project has node_modules installed) | — |
| Chrome / ChromeHeadless | Karma browser | ✓ | Used in CI per karma.conf.js + baseline measurement | — |
| Angular CLI (`ng test`) | Running the spec | ✓ | ^21.2.12 per package.json | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

---

## Sources

### Primary (HIGH confidence)
- `src/angular/src/app/services/utils/confirm-modal.service.ts` — source under test, full read
- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` — full read of 463 lines
- `.planning/phases/98-medium-priority-angular-coverage/98-CONTEXT.md` — locked decisions D-01..D-06
- `src/angular/karma.conf.js` — coverage reporter config, confirmed no `check.global`
- `src/angular/package.json` — Angular 21.2.14, jasmine-core 6.2.0, karma 6.4.4
- `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` — Angular baseline numbers, confirmed no thresholds
- `src/angular/src/test.ts` — BrowserDynamicTestingModule init, confirms test environment
- `src/angular/src/tsconfig.spec.json` — confirms spec includes all `**/*.spec.ts`

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — COVMED-04 acceptance statement
- `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` — Phase 98 plan spec

### Tertiary (LOW confidence)
- HTML5 parsing spec behavior for U+2028/U+2029 in element content — ASSUMED from training
  knowledge; not verified via external tool call. Risk is low (standard browser behavior, not
  edge case).

---

## Metadata

**Confidence breakdown:**
- TestBed/fakeAsync harness patterns: HIGH — verified directly from existing spec
- escapeHtml access pattern: HIGH — verified from source + CONTEXT.md
- HTML context analysis (element content vs class attribute): HIGH — verified from source lines 100-116
- Coverage threshold risk: HIGH — verified from karma.conf.js + baseline doc (no thresholds)
- `on*` attribute walk approach: HIGH — verified from DOM API spec knowledge; CSS selector
  limitation is definitive
- Trivial-fix window analysis (backtick/U+2028): MEDIUM — HTML5 spec knowledge from training;
  the conclusion aligns with D-01's locked decision

**Research date:** 2026-05-29
**Valid until:** 60 days — this is a pure test-extension phase on a stable source file;
no external API or package version concerns.
