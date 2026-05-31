# Phase 98: Medium-Priority Angular Coverage - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add **full end-to-end XSS coverage** for the single Medium-priority Angular test gap from CONCERNS.md:

- `ConfirmModalService.escapeHtml` (`src/angular/src/app/services/utils/confirm-modal.service.ts:33-40`) — the only sanitization layer between caller-supplied strings and the `innerHTML` assignment at line 100.

The `escapeHtml` helper escapes `&<>"'` and is applied to all six attacker-influenceable inputs (`title`, `body`, `okBtn`, `okBtnClass`, `cancelBtn`, `cancelBtnClass`) at lines 51-56 before they are interpolated into the modal template. This phase proves, by test, that:
1. Every documented metacharacter is escaped.
2. Attacker payloads in any of the six inputs produce no executable markup in the resulting `innerHTML`.
3. There is no bypass call site — no attacker-controlled string reaches `innerHTML` without passing through `escapeHtml`.

Single plan (98-01), test-only work. Same trivial-fix policy as Phase 97. The Low-priority Angular gaps (SSE timeout, auth interceptor) and the CI threshold ratchet are NOT in this phase — they are Phase 100.
</domain>

<decisions>
## Implementation Decisions

The design spec (`docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md`, "Phase 98 — Medium-Priority Angular Coverage" section) functions as a locked SPEC for this phase — the file under test, the four coverage points, the trivial-fix window, and the standalone-component spec isolation pattern are already fixed there. The decisions below resolve the HOW gray areas the spec left open. User delegated all gray areas to Claude's recommendation, carrying forward the Phase 97 precedent ("same as 97 — take your recs").

### Escape-set scope (trivial-fix window)
- **D-01:** Do NOT expand the escape set beyond the documented `&<>"'`. Rationale: all six attacker-controllable inputs interpolate into one of two HTML contexts only — **element content** (`safeTitle` in `<h5>`, `safeBody` in `<p>`, `safeOkBtn`/`safeCancelBtn` in button text) or a **double-quoted class attribute** (`safeOkBtnClass`/`safeCancelBtnClass` in `class="..."`). In both contexts the documented set is sufficient: escaping `<`/`>` prevents tag injection in element content, and escaping `"` prevents attribute-value breakout in the double-quoted class attribute. Backtick, U+2028, U+2029, and null byte are NOT XSS-exploitable in these contexts (no `<script>`/template-literal sink reaches them in the rendered DOM, no unquoted attribute, no `javascript:` URL sink). Per the Phase 97 D-05 borderline-defer posture, the escape set stays a no-op change. The test documents this reasoning so the absence of backtick/U+2028 escaping reads as intentional, not an oversight.

### skipMessage interpolation site (bypass audit)
- **D-02:** `skipMessage` (`confirm-modal.service.ts:59-64`) is the one interpolation site that does NOT pass through `escapeHtml`. It is **safe and stays as-is**: it interpolates only `options.skipCount`, a TypeScript `number`, guarded by `if (options.skipCount && options.skipCount > 0)`, alongside a literal `"s"` pluralization. No attacker-controlled string can reach it. This satisfies success-criterion #3 ("no bypass call site") — a "bypass" means an *attacker string* reaching `innerHTML` un-escaped, and none does. Do NOT route `skipCount` through `escapeHtml` (it is a number; escaping would be a no-op and add misleading noise implying string risk). There is nothing to fix or defer here — the test asserts the value is numeric and documents why the site is exempt.

### Test depth — "no executable markup"
- **D-03:** Assert absence of executable markup via the **parsed DOM**, not just string matching:
  - `modalElement.querySelector("script")` is `null` for every attacker payload.
  - No element in the modal subtree carries an `on*` event-handler attribute (iterate attributes, assert none start with `on`).
  - No `href`/`src` attribute value contains `javascript:`.
  - AND string-assert the raw `innerHTML` contains the **escaped entities** (e.g. `&lt;script&gt;`) — proving the payload was neutralized into inert text, not stripped by the browser parser (which would pass a script-absence check even without escaping).
- **D-04:** Direct unit test of `escapeHtml` output asserting each metacharacter maps to its entity: `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`, `"`→`&quot;`, `'`→`&#039;`. Include an ordering test (input containing a raw `<`) confirming `&`-first replacement does NOT double-escape the entity ampersands it just produced (i.e. `<` yields `&lt;`, not `&amp;lt;`).

### Coverage breadth — all six inputs
- **D-05:** Cover attacker payloads in **all six** escaped inputs individually, not just `title`/`body` (the existing spec only covers those two): `title`, `body`, `okBtn`, `cancelBtn`, `okBtnClass`, `cancelBtnClass`. The class-attribute inputs need their own payloads (e.g. `" onmouseover="alert(1)` attempting attribute breakout) since they interpolate into a different HTML context than the text inputs.

### Test isolation
- **D-06:** Use the existing `confirm-modal.service.spec.ts` standalone-component spec pattern (post-v1.1.2 `provideHttpClient()` migration — though this service needs no HTTP). Extend the existing file rather than create a parallel one; the file already has `fakeAsync` modal-lifecycle scaffolding and two partial XSS tests (lines 300, 322) to build on. New tests strengthen and extend, existing partial XSS tests may be folded/superseded.

### Claude's Discretion
- Exact test function names and `describe` block grouping.
- Whether to assert the `on*`-attribute absence via a helper that walks `querySelectorAll("*")` vs a flat attribute scan — default to whichever reads cleanest.
- Whether to keep, extend, or supersede the two existing partial XSS tests (lines 300, 322) — default to superseding with the fuller D-03/D-05 assertions while preserving any unique assertion they make.
</decisions>

<specifics>
## Specific Ideas

- The `escapeHtml` ordering matters: `&` is replaced first (line 35) so that the `&` introduced by subsequent replacements (`&lt;`, `&gt;`, `&quot;`, `&#039;`) is not itself re-escaped. A regression that reordered these would double-escape. D-04's ordering test guards this specifically.
- Two HTML contexts to exercise: element content (`<h5>${safeTitle}</h5>`, `<p>${safeBody}</p>`, `>${safeOkBtn}<`) and double-quoted attribute (`class="${safeOkBtnClass}"`). The classic attribute-breakout payload `" onmouseover="alert(1)` is neutralized because `escapeHtml` converts the `"` to `&quot;`, keeping the injected text inside the attribute value.
- The existing test at line 314 asserts `textContent` contains the literal `<script>` (i.e. the browser rendered it as text, not markup) and line 318 asserts `querySelector("script")` is null. D-03 extends this pattern to all six inputs plus the `on*=`/`javascript:` checks the spec mandates.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (locked requirements)
- `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` — Full v1.3.0 design. **Phase 98 content is in the "Phase 98 — Medium-Priority Angular Coverage" section** (plan 98-01), plus the global "Tier policy", "Trivial-fix policy", and "Phase shape" sections. MUST read before planning.
- `.planning/REQUIREMENTS.md` — COVMED-04 acceptance statement (line 19) and traceability (line 64).
- `.planning/codebase/CONCERNS.md` §"Test Coverage Gaps" → "`confirm-modal.service.ts` XSS escape logic" (lines 291-294) — original audit that catalogued this gap with file:line refs.

### Source under test
- `src/angular/src/app/services/utils/confirm-modal.service.ts` — `escapeHtml` (lines 33-40), the six `safe*` interpolations (lines 51-56), the `skipMessage` exemption (lines 59-64), and the `innerHTML` assignment (lines 100-116).

### Existing test patterns to extend
- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` — existing 463-line spec with `fakeAsync` modal scaffolding and two partial XSS tests (lines 300, 322) to extend/supersede.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `confirm-modal.service.spec.ts` already has full `TestBed` + `fakeAsync` setup, a modal-creation helper pattern, and asserts against `document.querySelector(".modal")` — directly reusable for the XSS payload tests.
- Two existing partial XSS tests (lines 300-338) establish the `textContent`-contains-literal + `querySelector("script")`-is-null assertion idiom.

### Established Patterns
- `escapeHtml` is a `private static` pure function — testable directly via a cast (`(ConfirmModalService as any).escapeHtml(...)`) for the D-04 metacharacter/ordering unit test, OR end-to-end through `confirm()` for the D-03/D-05 DOM assertions. Both layers are in scope.
- Modal is built by direct `innerHTML` assignment (line 100), NOT Angular template binding — so Angular's built-in contextual auto-escaping does NOT apply. `escapeHtml` is the sole guard. This is precisely why the gap is Medium and not Low.
- Post-v1.1.2 specs use `provideHttpClient()` / standalone patterns; this service has no HTTP dependency, so the spec's existing `TestBed.configureTestingModule` minimal setup is sufficient.

### Integration Points
- `escapeHtml` output feeds the `innerHTML` sink at line 100. The DOM assertions (D-03) must read the *rendered* modal (`document.querySelector(".modal")`) to prove neutralization end-to-end, not just inspect the helper's string return.
- COVMED-04 is the last Medium-priority gap; Phases 99-100 cover the Low-priority gaps and the CI ratchet that consumes the v1.3.0 baseline captured in Phase 97.
</code_context>

<deferred>
## Deferred Ideas

- Expanding the `escapeHtml` set to backtick/U+2028/U+2029/null-byte — explicitly NOT done (D-01); not exploitable in the two HTML contexts this service uses. If a future caller interpolates into a `<script>` block, unquoted attribute, or `javascript:` URL, revisit — that would be a new sink and its own concern.
- Routing `skipMessage`/`skipCount` through `escapeHtml` — NOT done (D-02); the value is numeric and the change would be a misleading no-op. Any structural refactor of the `innerHTML`-building approach (e.g. moving to Angular template binding / `Renderer2` text nodes to remove the `innerHTML` sink entirely) is a larger redesign → v1.4.0 if ever pursued, with a STATE.md entry.
- Any bug surfaced by these tests that exceeds the trivial-fix window (>10 net lines, public-API change, or observable-behavior change) → v1.4.0, with a one-line STATE.md deferred-items entry referencing the documenting test (per Phase 97 D-05 posture).

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — Python/upstream; unrelated to this Angular phase.
- `2026-04-24-migrate-config-set-to-post-body` — API contract change, separate milestone; unrelated.
</deferred>

---

*Phase: 98-medium-priority-angular-coverage*
*Context gathered: 2026-05-29*
