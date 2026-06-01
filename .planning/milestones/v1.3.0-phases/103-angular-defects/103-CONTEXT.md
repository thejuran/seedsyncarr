# Phase 103: Angular Defects - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

**Two Angular defect fixes this phase — both user-facing/client-side, no backend surface.**

1. **BUG-01** — `ConfirmModalService` (`src/angular/src/app/services/utils/confirm-modal.service.ts`) must render modal content with **no raw `innerHTML` sink**. Today it builds the whole dialog via `this.modalElement!.innerHTML = \`...\`` (lines 100-116) after pre-escaping six string inputs through a private `escapeHtml()`. Replace that with structural DOM construction via the already-injected `Renderer2` so escaping is **structural** (text nodes can't carry markup), not string-concatenation dependent. **Folds in** the deferred `skipCount` type-erasure hardening (`skipMessage`, lines 59-64) — coerce `skipCount` to a primitive number so a `toString()`-overriding object can no longer inject markup through that one un-escaped interpolation site.
2. **BUG-04** — The SSE `StreamDispatchService` (`src/angular/src/app/services/base/stream-service.registry.ts`) must never leave an orphaned subscription / EventSource when a reconnect fires in the **same tick** as a timeout (or an error). The prior subscription/EventSource must be torn down before its replacement is created, leaving **exactly one** active subscription.

Scope anchor from ROADMAP.md (Phase 103, lines 462-476) — fixed. Phases 101 (webhook + log-injection) and 102 (controller concurrency) are done and out of scope here. This is the **last phase of v1.3.0 slice 2**.

**Cross-cutting (locked by REQUIREMENTS.md):** COMPAT — no breaking changes to existing UI behavior or observable component APIs; CI green amd64+arm64 (Angular + E2E); Karma `check.global` floors (stmts/branches/fns/lines **83 / 68 / 79 / 83**) hold or rise; no client-visible behavior regression in confirm-modal or SSE reconnect; **no release/tag/version work** (the single `v1.3.0` tag is cut only after slice 4).
</domain>

<decisions>
## Implementation Decisions

### BUG-01 — ConfirmModal: eliminate the innerHTML sink
- **D-01 (build approach):** Build the modal DOM **imperatively with `Renderer2`** inside `createModal()` — `renderer.createElement` / `renderer.createText` / `renderer.appendChild` — in the **same service**, no new template file, no standalone component. Each user-supplied string (`title`, `body`, `okBtn`, `cancelBtn`) is appended as a **text node**, so `<script>`/`on*=`/`javascript:` payloads render inert without any escape call. This is the smallest diff that satisfies criterion #1 and keeps the existing focus-trap, keydown handler, backdrop, z-index styling, and `destroyModal()` logic untouched. (Standalone-component alternative considered and rejected — larger refactor, rewrites the spec's DOM queries, moves focus-trap; no benefit here.)
- **D-02 (escapeHtml becomes dead code):** Once content is built from text nodes, the private static `escapeHtml()` (lines 33-40) and the six `safe*` locals (lines 51-56) are **no longer needed for safety** — remove `escapeHtml()` and the pre-escaping. **However:** the slice-1 escapeHtml XSS regression suite (`confirm-modal.service.spec.ts`) asserts behavior through the *rendered DOM* (e.g. `expect(cancelButton.textContent).toContain("<script>")`, `expect(modal.querySelector("script")).toBeNull()`). Those DOM-level assertions must **still pass** under text-node rendering (they will — text nodes render `<script>` as literal text and create no `<script>` element). Any spec assertion that checks the *escaped string form* specifically (e.g. `modal.innerHTML` containing `&lt;script&gt;`) must be **updated** to the structural-equivalent assertion (the payload appears as inert text, querySelector finds no executable element) — escaping changed from entity-encoding to text-node structural, so the *mechanism* assertion changes while the *security outcome* assertion is preserved.
- **D-03 (button classes — attribute, not text):** `okBtnClass` / `cancelBtnClass` are applied as **class attributes** on the buttons, not text content. With `Renderer2`, split the class string and use `renderer.addClass()` per token (or `setAttribute('class', ...)`), which assigns the attribute value structurally — no HTML parsing, so the slice-1 attribute-breakout payload tests (`"btn\" onmouseover=\"alert(1)"`) stay neutralized (the value becomes a literal — possibly invalid — class token, never a new attribute). Default classes (`"btn btn-primary"` etc.) unchanged.

### BUG-01 fold-in — skipCount type-erasure hardening
- **D-04 (coerce to primitive number):** Coerce `skipCount` with `Number(options.skipCount)` into a local `const n` **before** the guard, and gate on `Number.isFinite(n) && n > 0` (replacing the current `if (options.skipCount && options.skipCount > 0)`). A `toString()`-overriding object then yields its `valueOf()` number (or `NaN` → guard fails), so no markup can flow into the skip message. The plural branch keys on `n === 1`. Combined with D-01's text-node rendering for the skip paragraph, the site is doubly safe (coercion + structural), but the explicit `Number()` makes the numeric contract unambiguous and is the canonical fix for the fold-in.
- **D-05 (UPDATE the slice-1 runtime-boundary probe — its deferral is now obsolete):** The slice-1 spec (`confirm-modal.service.spec.ts:690-720`) currently **PINS the un-hardened behavior** — a coercible `{valueOf: ()=>1, toString: ()=>"<img ...>"}` passed as `skipCount` injects an `<img>` element, with a comment stating "runtime hardening … deferred to v1.4.0. Do NOT modify confirm-modal.service.ts." **Phase 103 IS that hardening** (BUG-01 fold-in). The planner MUST update this test: after D-04, the same coercible object must produce **no `<img>`** — `expect(skipP.querySelector("img")).toBeNull()` — and the obsolete v1.4.0-deferral comment block is rewritten to describe the now-shipped coercion. This is an intended, in-scope test change, not a regression. (The companion D-02 "skipCount is exempt because it's a number" documenting test at lines 661-676 stays valid — a real numeric `skipCount: 3` still renders `"3 file…"`.)

### BUG-04 — SSE same-tick subscription teardown
- **D-06 (scope = audit + harden + regression-test, NOT rewrite):** Treat criterion #3 as "prove and tighten." The teardown machinery **already partly exists**: `createSseObserver()` calls `this._currentSubscription?.unsubscribe()` then nulls it at entry (lines 181-182), and the Observable teardown closes the prior EventSource (lines 225-228); `reconnectDueToTimeout()` closes `_currentEventSource` and re-arms a single `_reconnectTimer` (lines 142-164). **Audit** the three reconnect-arming paths — `reconnectDueToTimeout` (timeout), the subscription `error` handler (lines 243-260), and the implicit re-subscribe — for any window where two `createSseObserver` calls could be armed (double EventSource / orphaned subscription). Harden **only** where the audit finds a real gap; otherwise the change is the regression test plus any minimal ordering tightening.
- **D-07 (preferred hardening if a gap is confirmed — guard double reconnect-timer arming):** Both `reconnectDueToTimeout` and the `error` handler do `if (this._reconnectTimer) clearTimeout(...)` then re-arm. If the audit shows a same-tick timeout-then-error (or error-then-timeout) can leave two pending `createSseObserver` schedules or an EventSource opened without the prior one closed, close it by ensuring **single-flight reconnect** — clear-and-reset is already present, so the most likely real fix is guaranteeing `createSseObserver`'s entry teardown (unsubscribe + the Observable's `eventSource.close()`) covers every replacement path, and that `_currentEventSource` is closed before a new one is assigned at line 188. A dedicated `_reconnectPending`/single-flight boolean is the fallback if clear-and-reset proves insufficient. **Do not add state the audit doesn't justify.**
- **D-08 (preserve the slice-1 heartbeat-vs-timeout race test):** The slice-1 regression suite (`stream-service.registry.spec.ts:209-260`, `describe("heartbeat-vs-timeout race")`) asserts (a) a heartbeat arriving after the 30s boundary re-arms `_lastEventTime` and prevents a spurious reconnect — `createEventSource` called exactly once, no false disconnect — and (b) the no-heartbeat positive control where the timeout *does* reconnect (2 calls). Both MUST still pass. The **new** BUG-04 test asserts the same-tick collision invariant: when a reconnect and a timeout/error coincide in one fakeAsync frame, exactly **one** active EventSource/subscription remains (assert `createEventSource` call count and that no orphaned listener double-delivers). Add it as a sibling `it()` in that describe block or an adjacent one.

### Plan shape
- **D-09 (two independent plans, test-first each):** Split into **`103-01` (BUG-01)** and **`103-02` (BUG-04)** — different files, different specs, **no ordering dependency** (can be two waves or parallel). Each lands **test-first (red → green)**, reusing and updating the slice-1 regression suites named above. This keeps the Angular DOM-rendering change and the RxJS/EventSource lifecycle change in separate, independently-bisectable commit series. (Single combined plan rejected — mixes two unrelated concerns.)
- **D-10 (E2E / visual check depth):** The confirm modal is user-visible (UI hint = yes). Unit/Karma coverage (updated slice-1 suites + new assertions) is the primary gate; **no new heavy Playwright spec** is required for this phase. A targeted manual/Playwright smoke of the confirm modal happens during the **milestone-end walkthrough** (Phase 4), not as a new E2E file here. SSE reconnect is covered by the fakeAsync unit tests.

### Claude's Discretion
- Exact `Renderer2` element-construction helper structure in `createModal()` (inline vs a small private `buildModalContent()` helper) — as long as no `innerHTML`/`outerHTML`/`insertAdjacentHTML` assignment remains.
- Whether to keep or rename the now-safe `data-action="ok"/"cancel"` button hooks (keep them — `querySelector` wiring at lines 122-123 depends on them).
- Exact wording of the rewritten slice-1 probe comment (D-05).
- Whether the BUG-04 fix needs the `_reconnectPending` single-flight boolean (D-07) or whether tightening existing clear-and-reset suffices — decided by the audit.
- Whether the new BUG-04 test lives inside the existing `heartbeat-vs-timeout race` describe or a new sibling describe block.
</decisions>

<specifics>
## Specific Ideas

- BUG-01 is **partly mis-stated as "add Renderer2"** — `Renderer2` is *already injected* (line 17, 23-24) and used for backdrop/modal element creation and styling. The actual work is replacing the **one** `innerHTML` assignment (line 100) with text-node/structural construction, and deleting the now-redundant `escapeHtml` pre-escaping. Don't let the planner re-add `Renderer2` from scratch.
- BUG-04 is **partly already fixed** — `_currentSubscription?.unsubscribe()` teardown (lines 181-182) was added previously. The remaining work is auditing the same-tick collision invariant and pinning it with a test, not rebuilding the reconnect machinery.
- The slice-1 `skipCount` runtime-boundary probe explicitly says hardening is "deferred to v1.4.0" — **that deferral is now resolved by this phase.** Updating that test is in-scope and expected (D-05), not a surprise regression.
- Both fixes are test-first, reusing the slice-1 harnesses (the escapeHtml/skipCount DOM-assertion suite and the `heartbeat-vs-timeout race` fakeAsync suite).
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (source of truth)
- `.planning/REQUIREMENTS.md` — BUG-01 (line 16) + BUG-04 (line 19) full statements; phase mapping (lines 75-76, 87); Cross-Cutting Constraints (COMPAT, CI green amd64+arm64, Karma floors, no-release).
- `.planning/ROADMAP.md` §"Phase 103: Angular Defects" (lines 462-476) — phase goal + 4 success criteria (criterion #1 = no innerHTML sink; #2 = skipCount hardening; #3 = SSE same-tick teardown; #4 = COMPAT cross-cutting).
- `.planning/codebase/CONCERNS.md` — original Known-Bugs audit detail for BUG-01 (innerHTML XSS sink) and BUG-04 (SSE same-tick subscription leak).

### Code surfaces (read before implementing)
- `src/angular/src/app/services/utils/confirm-modal.service.ts`:
  - `escapeHtml()` lines 33-40 — **remove** once text-node rendering lands (D-02).
  - `createModal()` lines 42-168 — backdrop + modal element built via `Renderer2` (keep); **the `innerHTML` assignment at lines 100-116 is the sink to replace (D-01)**; `safe*` locals 51-56 removed; `skipMessage` 59-64 coerced + structural (D-04); button-click/focus-trap/keydown wiring 122-167 preserved (depends on `data-action` hooks + `.modal`/`.modal-body p` structure).
  - `destroyModal()` lines 170-190 — unchanged.
- `src/angular/src/app/services/base/stream-service.registry.ts` §`StreamDispatchService`:
  - `_currentEventSource` / `_currentSubscription` fields lines 78-79; `reconnectDueToTimeout()` 142-164 (timeout reconnect path); `createSseObserver()` 179-262 — **entry teardown 181-182 + Observable `eventSource.close()` 225-228** (existing); subscription `error` handler reconnect 243-260; EventSource assignment line 188. **BUG-04 audit + hardening target (D-06/D-07)**.
- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` — slice-1 escapeHtml XSS suite (DOM assertions to preserve, D-02) + skipCount exemption documenting test (lines 661-676, stays valid) + **runtime-boundary probe lines 690-720 to UPDATE (D-05)**.
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` §`describe("heartbeat-vs-timeout race")` lines 209-260 — slice-1 SSE race regression (preserve, D-08); add the new same-tick collision test here.
- `src/angular/src/app/tests/mocks/mock-stream-service.registry.ts` — mock EventSource/listeners harness used by the registry spec (reuse for the new BUG-04 test).

### Conventions
- `.planning/codebase/CONVENTIONS.md` — Angular: no raw `innerHTML` with user content (the rule BUG-01 enforces), `Renderer2` for DOM work, `===`/`== null` discipline, no functions/objects created in render, complete `useEffect`/observable cleanup.
- `.planning/codebase/TESTING.md` — Angular Karma + `fakeAsync`/`tick`/`discardPeriodicTasks` idiom (the SSE tests rely on it); regression tests tag the phase/issue ID in the title.

### No external specs
This phase is bug work against existing Angular code — no ADRs or feature specs beyond the requirements/roadmap above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`Renderer2` already wired** in `ConfirmModalService` (`rendererFactory.createRenderer(null, null)`, lines 23-24) and used for backdrop/modal element creation + styling — BUG-01 extends this to content, no new injection.
- **Slice-1 escapeHtml XSS DOM-assertion suite** (`confirm-modal.service.spec.ts`) — asserts security outcomes through the rendered DOM (`querySelector("script")` null, button `textContent` contains literal payload, no `on*` attribute, no `javascript:` URL). Reusable as the BUG-01 regression gate; mechanism-specific assertions updated per D-02.
- **Slice-1 `heartbeat-vs-timeout race` fakeAsync suite** (`stream-service.registry.spec.ts:209-260`) + **`mock-stream-service.registry.ts`** mock EventSource — directly reusable harness for the BUG-04 same-tick collision test.
- **`Number()` coercion + `Number.isFinite`** — standard primitive-coercion idiom for the skipCount fold-in (D-04).

### Established Patterns
- **`Renderer2` structural DOM construction** — the service already builds backdrop/modal via `createElement`/`addClass`/`setStyle`/`setAttribute`/`appendChild`; BUG-01 content build follows the same pattern with `createText` for user strings.
- **`fakeAsync` + `tick` + `discardPeriodicTasks`** — every SSE timing test uses it; the interval checker runs at `TIMEOUT_CHECK_INTERVAL_MS=5000`, timeout at `CONNECTION_TIMEOUT_MS=30000` (strict `>`), reconnect delay `STREAM_RETRY_INTERVAL_MS=3000`.
- **Single-subscription invariant via entry teardown** — `createSseObserver` unsubscribes the prior subscription before building a new Observable; the BUG-04 fix preserves/tightens this rather than introducing a new lifecycle model.

### Integration Points
- BUG-01 touches **only** `confirm-modal.service.ts` + its spec → COMPAT trivially holds (no public API change to `ConfirmModalOptions`; callers pass the same options). The `.modal`/`.modal-backdrop`/`data-action` DOM contract that callers and the focus-trap rely on is preserved.
- BUG-04 touches **only** `stream-service.registry.ts` + its spec (and reuses the existing mock) → no change to `IStreamService`, `StreamServiceRegistry`, or the provider factory; registered services unchanged.
- The two fixes are independent (different files, different requirements) — separate plans / separate waves, no ordering dependency (D-09).

### Tooling / gates
- Karma `coverageReporter.check.global` floors **83 / 68 / 79 / 83** (stmts/branches/fns/lines), set in Phase 100 — must hold or rise. Removing `escapeHtml` (dead code) and adding tests should not drop coverage; verify after.
- CI runs amd64 + arm64; Angular unit (Karma) + E2E (Playwright). No new E2E spec required (D-10).
</code_context>

<deferred>
## Deferred Ideas

- None new — discussion stayed within the BUG-01 / BUG-04 scope. (The slice-1 skipCount "v1.4.0 hardening" deferral is **resolved by this phase**, not re-deferred — see D-05.)
- Migrating `ConfirmModalService` to a full standalone `ConfirmModalComponent` (template-based) — considered for D-01 and rejected as out-of-scope refactor; could be a future cleanup phase if the modal grows, but not needed for the security fix.

### Reviewed Todos (not folded)
- `todo.match-phase 103` to be run by the planner; the two standing deferred todos (`webob-cgi-upstream-unblock`, `migrate-config-set-to-post-body`) are backend/upstream and unrelated to these Angular defects — do not fold.
</deferred>

---

*Phase: 103-angular-defects*
*Context gathered: 2026-05-31*
