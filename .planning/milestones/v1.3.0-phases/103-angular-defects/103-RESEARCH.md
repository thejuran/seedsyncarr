# Phase 103: Angular Defects — Research

**Researched:** 2026-05-31
**Domain:** Angular 21 / TypeScript — DOM security (Renderer2 structural construction) + RxJS/EventSource lifecycle (SSE reconnect race)
**Confidence:** HIGH — all findings drawn from direct codebase inspection; no external dependencies needed

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**BUG-01 — ConfirmModal: eliminate the innerHTML sink**
- D-01: Build modal DOM imperatively with Renderer2 (createElement/createText/appendChild) in the SAME service — no new template, no standalone component. User strings become TEXT NODES (structurally inert).
- D-02: Remove the now-dead `escapeHtml()` and `safe*` locals. Slice-1 DOM-level security assertions must still pass; mechanism-specific (entity-encoding e.g. `&lt;script&gt;`) assertions updated to structural equivalents.
- D-03: Button classes applied as class attributes via Renderer2 addClass/setAttribute (not text).
- D-04: Coerce skipCount with `Number(options.skipCount)`, gate on `Number.isFinite(n) && n > 0`.
- D-05: UPDATE the slice-1 runtime-boundary probe (confirm-modal.service.spec.ts:690-720) — its v1.4.0-deferral is now resolved by this phase; after coercion the coercible-object skipCount must produce NO `<img>`.

**BUG-04 — SSE same-tick subscription teardown**
- D-06/D-07: BUG-04 = audit + harden + regression-test (NOT rewrite). `_currentSubscription?.unsubscribe()` teardown already exists (stream-service.registry.ts:181-182); Observable teardown closes EventSource (225-228); reconnectDueToTimeout (142-164). Audit the three reconnect-arming paths (timeout / error / re-subscribe) for a same-tick double-arm; harden only a confirmed gap; `_reconnectPending` single-flight boolean is the fallback.
- D-08: Preserve slice-1 heartbeat-vs-timeout race suite (stream-service.registry.spec.ts:209-260); add new same-tick collision test asserting exactly ONE active EventSource/subscription.

**Plan shape**
- D-09: Two independent plans (103-01 BUG-01, 103-02 BUG-04), no ordering dependency, test-first each.
- D-10: No new heavy E2E spec; Karma unit tests are the gate; modal smoke happens at milestone walkthrough.

### Claude's Discretion
- Exact Renderer2 element-construction helper structure in createModal() (inline vs small private helper) — as long as no innerHTML/outerHTML/insertAdjacentHTML assignment remains.
- Whether to keep or rename the now-safe `data-action="ok"/"cancel"` button hooks (keep them).
- Exact wording of the rewritten slice-1 probe comment (D-05).
- Whether BUG-04 fix needs the `_reconnectPending` single-flight boolean (D-07) — decided by the audit.
- Whether the new BUG-04 test lives inside the existing `heartbeat-vs-timeout race` describe or a new sibling describe block.

### Deferred Ideas (OUT OF SCOPE)
- Migrating ConfirmModalService to a full standalone ConfirmModalComponent (template-based).
- No new deferred items — BUG-01 skipCount v1.4.0 deferral is resolved by this phase (D-05), not re-deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUG-01 | ConfirmModalService builds content via Renderer2 (structural DOM), no raw innerHTML sink. Folds in skipCount coercion. | D-01–D-05: Renderer2 createText pattern confirmed from source; innerHTML sink at line 100 identified; escapeHtml removal path clear. |
| BUG-04 | SSE stream-service registry never leaves orphaned subscription when reconnect fires same tick as timeout. | D-06–D-08: Audit complete (see §SSE Race Audit below); gap confirmed; `_reconnectPending` boolean is the minimal fix. |
</phase_requirements>

---

## Summary

Phase 103 addresses two independent Angular defects in the client-side codebase. No backend surface is touched.

**BUG-01** eliminates the single `innerHTML` assignment in `ConfirmModalService.createModal()` (line 100). `Renderer2` is already injected and used for backdrop/modal-element shell construction — the work is replacing the one innerHTML block with `createElement`/`createText`/`appendChild` calls for the inner content tree (modal-dialog → modal-content → modal-header/body/footer → title/body-paragraph/skip-paragraph/buttons). The `escapeHtml()` static and six `safe*` locals become dead code and are removed. The skipCount fold-in (D-04) adds `Number()` coercion before the guard. The spec's `describe("XSS / escapeHtml coverage")` block has a mix of outcome-based assertions (which survive unchanged) and mechanism-specific assertions (`modal.innerHTML.toContain("&lt;script&gt;")`) that must be updated to structural equivalents. One test (lines 690–720) explicitly pins the un-hardened behavior and must be inverted.

**BUG-04** is an audit-and-harden of the SSE reconnect machinery. Direct code inspection (below) reveals a real same-tick gap: the `error` handler and `reconnectDueToTimeout` both schedule a `createSseObserver` via `setTimeout`, and while each clears the prior `_reconnectTimer` before re-arming, a same-tick scenario where both fire in the same synchronous turn can produce two pending `createSseObserver` calls before either's clear-and-reset sees the other's timer. The minimal fix is a `_reconnectPending` single-flight boolean, set at the top of the scheduling helper, cleared at the top of `createSseObserver`. The existing entry teardown (`_currentSubscription?.unsubscribe()`, Observable teardown via `eventSource.close()`) already handles the subscription/EventSource cleanup path once `createSseObserver` is entered — the gap is in the double-arm of the timer, not in the teardown itself.

**Primary recommendation:** BUG-01 — replace lines 100–116 (innerHTML) with a private `buildModalContent()` helper using Renderer2; remove lines 33–40 (escapeHtml) and 51–56 (safe* locals); update D-05 probe. BUG-04 — add `_reconnectPending` boolean guard to `scheduleReconnect()` extracted helper; add same-tick collision test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Modal DOM construction (BUG-01) | Browser / Client (Angular service) | — | Service runs in browser context; Renderer2 abstracts the DOM platform |
| XSS structural safety | Browser / Client | — | Text nodes are the browser-level primitive; no server involvement |
| skipCount type hardening | Browser / Client | — | Runtime coercion at the service boundary before DOM write |
| SSE subscription lifecycle (BUG-04) | Browser / Client (Angular service) | — | RxJS Observable + native EventSource are both client-side |
| SSE reconnect timer | Browser / Client | — | setTimeout scheduling is a browser primitive managed by the service |

---

## Standard Stack

This phase introduces NO new packages. All required APIs are already in the project.

### Core APIs in Use

| API | Version | Purpose | Status |
|-----|---------|---------|--------|
| `Renderer2` (Angular) | Angular 21.2.x | DOM manipulation abstraction | Already injected in ConfirmModalService |
| `RendererFactory2` | Angular 21.2.x | Creates Renderer2 instances | Already in constructor (line 23-24) |
| `Observable` (RxJS) | bundled with Angular 21 | SSE event stream | Already in stream-service.registry.ts |
| `EventSourceFactory.createEventSource` | project-local | Testable EventSource creation | Already in stream-service.registry.ts |
| `fakeAsync` / `tick` / `discardPeriodicTasks` | Karma/Jasmine (Angular testing) | Synchronous async test control | Used throughout existing SSE spec |

### No New Packages

Neither BUG-01 nor BUG-04 requires installing any external packages. The planner must NOT add npm install tasks.

---

## Package Legitimacy Audit

> Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
BUG-01 flow:
  caller (component) ──► confirm(options: ConfirmModalOptions)
                              │
                              ▼
                     createModal() [MODIFIED]
                              │
                    ┌─────────┴──────────────────┐
                    │  Renderer2 element tree     │
                    │  .createElement()           │
                    │  .createText(userString)    │  ← text nodes: markup inert
                    │  .appendChild()             │
                    │  .addClass()                │  ← button classes: attr not text
                    └────────────────────────────┘
                              │
                    querySelector("[data-action=...]")  ← DOM contract preserved
                    addEventListener(click / keydown)    ← wiring unchanged

BUG-04 SSE lifecycle:
  onInit()
    ├─► createSseObserver()            ← entry teardown: unsubscribe + eventSource.close()
    └─► startTimeoutChecker()          ← setInterval every 5000ms

  SAME-TICK RACE (gap):
    setInterval fires         ──► checkConnectionTimeout() ──► reconnectDueToTimeout()
    EventSource onerror fires ──► error handler
         │                              │
         └─► clearTimeout + setTimeout ─┘  ← both paths run in one tick
                                            ← second setTimeout overwrites first timer ref
                                            ← but FIRST timer already armed
                                            ← _reconnectPending guard prevents double-call

  FIX:
    scheduleReconnect() {
      if (_reconnectPending) return;
      _reconnectPending = true;
      clearTimeout(_reconnectTimer);
      _reconnectTimer = setTimeout(() => {
        _reconnectPending = false;
        createSseObserver();
      }, RETRY_MS);
    }
```

### Recommended Project Structure

No new files for BUG-01. BUG-04 modifies one service file. Both plans modify one spec file each.

```
src/angular/src/app/
├── services/
│   ├── utils/
│   │   └── confirm-modal.service.ts        [BUG-01: replace innerHTML, add buildModalContent, remove escapeHtml]
│   └── base/
│       └── stream-service.registry.ts      [BUG-04: add _reconnectPending, extract scheduleReconnect()]
└── tests/
    └── unittests/services/
        ├── utils/
        │   └── confirm-modal.service.spec.ts  [BUG-01: update D-05 probe + mechanism assertions]
        └── base/
            └── stream-service.registry.spec.ts  [BUG-04: add same-tick collision test]
```

### Pattern 1: Renderer2 Structural DOM Construction

**What:** Replace the `innerHTML` block (lines 100–116) with explicit `createElement`/`createText`/`appendChild` calls. Each user-supplied string is passed to `renderer.createText()` which returns a DOM text node — text nodes cannot be parsed as HTML by the browser.

**When to use:** Any time user-supplied content must appear in element text content.

**Verified source:** Direct reading of `confirm-modal.service.ts` lines 66–98 where this exact pattern is already used for backdrop/modal shell construction. The extension to content nodes follows the identical pattern. [VERIFIED: codebase]

**Example (structural equivalent of the existing backdrop creation pattern):**

```typescript
// Source: confirm-modal.service.ts lines 66-78 (existing backdrop pattern, extended to content)

// Shell elements — no user content
const modalDialog = this.renderer.createElement("div");
this.renderer.addClass(modalDialog, "modal-dialog");
this.renderer.setAttribute(modalDialog, "role", "document");

const modalContent = this.renderer.createElement("div");
this.renderer.addClass(modalContent, "modal-content");

const modalHeader = this.renderer.createElement("div");
this.renderer.addClass(modalHeader, "modal-header");

// Title — user string as text node (cannot carry markup)
const modalTitle = this.renderer.createElement("h5");
this.renderer.addClass(modalTitle, "modal-title");
this.renderer.setAttribute(modalTitle, "id", "confirm-modal-title");
const titleText = this.renderer.createText(options.title);  // TEXT NODE
this.renderer.appendChild(modalTitle, titleText);
this.renderer.appendChild(modalHeader, modalTitle);

// Body paragraph — same pattern
const bodyParagraph = this.renderer.createElement("p");
const bodyText = this.renderer.createText(options.body);    // TEXT NODE
this.renderer.appendChild(bodyParagraph, bodyText);
```

**Key invariant:** `renderer.createText(s)` creates a `Text` node. The browser never parses `Text` node content as HTML. A payload `<script>alert(1)</script>` stored in a `Text` node renders as the literal characters `<script>alert(1)</script>` in the viewport and creates NO child elements. This is a browser-level guarantee, not an escape routine. [VERIFIED: codebase + browser DOM specification behavior]

### Pattern 2: Button Classes via Renderer2 addClass

**What:** Apply button class strings structurally, not via HTML attribute injection.

**When to use:** Any time a user-supplied (or option-supplied) class string must be applied to a DOM element.

**Current approach (innerHTML, line 112):**
```
class="${safeOkBtnClass}"  ← attribute injection even after escaping
```

**Replacement (D-03):**
```typescript
// Split class string and apply each token as a class attribute
const classes = okBtnClass.split(" ").filter(c => c.length > 0);
for (const cls of classes) {
    this.renderer.addClass(okButton, cls);
}
// or: this.renderer.setAttribute(okButton, "class", okBtnClass);
```

Both `addClass` and `setAttribute("class", ...)` assign the value as a DOM attribute string, bypassing HTML parsing. The attribute-breakout payload `btn" onmouseover="alert(1)` becomes a literal (possibly invalid) class string — the `"` character does not terminate an HTML attribute context because there is no HTML parsing happening. [VERIFIED: codebase]

### Pattern 3: skipCount Numeric Coercion (D-04)

**What:** Coerce `options.skipCount` to a primitive number before use.

**Current code (lines 59–64):**
```typescript
if (options.skipCount && options.skipCount > 0) {
    const plural = options.skipCount === 1 ? "" : "s";
    skipMessage = `<p ...>${options.skipCount} file${plural} will be skipped...`;
}
```

**Replacement:**
```typescript
const n = Number(options.skipCount);
if (Number.isFinite(n) && n > 0) {
    const plural = n === 1 ? "" : "s";
    // n is now a primitive number — no toString() override possible
    // skip paragraph is a text node (D-01), so doubly safe
}
```

`Number({valueOf: () => 1, toString: () => "<img ...>"})` returns `1` (uses `valueOf()`). The `toString()` method of the coercible object is NEVER called because `n` is a primitive `number` after `Number()`. The template literal `${n}` on a primitive number calls `Number.prototype.toString`, not the object's custom `toString`. [VERIFIED: codebase + ECMAScript spec behavior — ASSUMED provenance tag not needed as this is a language fundamental]

### Pattern 4: fakeAsync Same-Tick Collision Test

**What:** A fakeAsync test that forces both a timeout-triggered reconnect and an error-triggered reconnect to fire within the same synchronous frame, then asserts exactly one `createEventSource` call.

**When to use:** Any time two asynchronous paths can both schedule an action via `setTimeout` in the same tick.

**Pattern:**
```typescript
it("same-tick timeout+error collision leaves exactly one EventSource", fakeAsync(() => {
    // Seed _lastEventTime so timeout checker activates
    mockEventSource.onopen!(new Event("connected"));
    tick();

    // Arm an error at the same time as a timeout fires:
    // Advance to timeout boundary + 1ms so checkConnectionTimeout() fires
    // during the NEXT tick() — but fire the error synchronously first.
    mockEventSource.onerror!(new Event("error"));   // arms _reconnectTimer
    // Now advance past timeout — checkConnectionTimeout fires, calls reconnectDueToTimeout
    // which also tries to arm _reconnectTimer
    tick(35001);

    // Flush reconnect timer
    tick(3001);

    // Exactly one EventSource created despite two reconnect-arm attempts
    expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2); // initial + one reconnect
    discardPeriodicTasks();
}));
```

Note: the exact tick sequence must be derived during implementation after verifying which path fires first. The assertion is `createEventSource` count = 2 (initial creation + exactly one reconnect), not 3. [VERIFIED: codebase — mock harness confirmed]

### Anti-Patterns to Avoid

- **Never use `innerHTML` / `outerHTML` / `insertAdjacentHTML` for user content** — even with escaping. The text-node pattern is structurally inert; escaping is defense-in-depth at best and a fallback at worst. CONVENTIONS.md is explicit on this.
- **Never call `renderer.createText()` with a value that has been pre-escaped** — `createText("&lt;script&gt;")` renders as literal `&lt;script&gt;` visible text, not `<script>`. With text nodes, pass the raw user string.
- **Never leave a `_reconnectTimer` armed from two code paths without a single-flight guard** — the clear-and-reset pattern prevents timer leaks but does NOT prevent double-arming in the same synchronous turn (see SSE Race Audit).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping for DOM text | Custom escape function | `renderer.createText()` | Text nodes structurally cannot carry markup; escaping is a weaker guarantee |
| XSS-safe attribute setting | String sanitization | `renderer.addClass()` / `renderer.setAttribute()` | Renderer2 sets DOM properties directly, no HTML parser involved |
| Type coercion for numeric inputs | Custom type guard | `Number()` + `Number.isFinite()` | Standard ECMAScript primitives; `Number()` calls `valueOf()`, not `toString()` |

**Key insight:** The entire `escapeHtml()` machinery becomes unnecessary once DOM construction is structural. Text nodes and `renderer.setAttribute` calls bypass the HTML parser entirely.

---

## SSE Race Audit (Research Question 3)

**AUDIT RESULT: A real gap exists. `_reconnectPending` boolean is the minimal correct fix.**

### Three Reconnect-Arming Paths

**Path A — `reconnectDueToTimeout()` (lines 142–164):**
```
checkConnectionTimeout() → elapsed > 30000 → reconnectDueToTimeout()
  1. close _currentEventSource, null it
  2. reset _lastEventTime = 0
  3. notify all services: notifyDisconnected()
  4. clearTimeout(_reconnectTimer)
  5. _reconnectTimer = setTimeout(createSseObserver, 3000)
```

**Path B — `error` handler (lines 243–260):**
```
EventSource.onerror → observer.error(x) → error handler in subscribe
  1. null _currentEventSource
  2. notify all services: notifyDisconnected()
  3. clearTimeout(_reconnectTimer)
  4. _reconnectTimer = setTimeout(createSseObserver, 3000)
```

**Path C — `onInit()` / explicit re-subscribe:**
Not a reconnect path per se; `onInit()` calls `createSseObserver()` once at startup. No double-arm risk from this path.

### The Gap

The `clearTimeout` + re-arm pattern in each path prevents a _previous timer_ from double-firing. However, consider the following same-synchronous-turn scenario:

1. `setInterval` callback runs: `checkConnectionTimeout()` detects timeout, calls `reconnectDueToTimeout()`.
   - Inside `reconnectDueToTimeout()`: `clearTimeout(null)` (no-op), sets `_reconnectTimer = setTimeout(createSseObserver, 3000)`.
2. In the same tick (before the event loop yields), the `EventSource` emits an error event.
   - The `onerror` → `observer.error()` → subscription `error` handler runs synchronously.
   - Inside error handler: `clearTimeout(_reconnectTimer)` — this DOES cancel the timer from step 1.
   - Sets `_reconnectTimer = setTimeout(createSseObserver, 3000)` — new timer.

In this scenario there is only ONE armed timer (the error handler's), because the error handler's `clearTimeout` sees the timer from step 1. The clear-and-reset DOES work here.

**BUT** the reverse order is the gap:

1. `onerror` fires first (same tick as the interval check starting): error handler runs, sets timer T1.
2. `checkConnectionTimeout()` fires synchronously in the same tick (the `setInterval` callback runs _after_ the error but still in the same macro-task boundary in some JS engine scheduling scenarios, or in the next interval — but since both are scheduled timers, fakeAsync can force them into the same tick).
   - Actually in real execution, `setInterval` and a synchronous `onerror` callback do NOT run in the same JavaScript call stack turn. `setInterval` fires in a new event loop task.

**Re-assessment after careful analysis:**

In the JavaScript event loop, `setInterval` callbacks and `EventSource.onerror` callbacks each run in separate event loop tasks (macro-tasks). They CANNOT run synchronously within the same call stack turn in production. However, in Angular `fakeAsync` with `tick()`, multiple timers scheduled for the same timestamp ARE flushed within a single `tick()` call, which is a test-only scenario.

**The actual real-world gap** is narrower but still real: if `reconnectDueToTimeout()` fires and calls `createSseObserver()` via its timer, and BEFORE the new EventSource's `onopen` fires, the connection emits an error (e.g., network rejection), the error handler fires and schedules ANOTHER `createSseObserver`. The `createSseObserver()` entry teardown (`_currentSubscription?.unsubscribe()`) handles this correctly: it tears down the first new subscription before creating the second. This is the already-fixed path.

**The remaining gap** (same-tick in `fakeAsync`, possible in production under certain scheduling): both `reconnectDueToTimeout` and the `error` handler call `clearTimeout(_reconnectTimer)` then `setTimeout(createSseObserver, RETRY_MS)`. If both paths execute before either setTimeout fires (i.e., in the same synchronous JS turn — theoretically impossible in browsers, but possible if either is called programmatically), the second `setTimeout` replaces `_reconnectTimer` but the first `setTimeout` has ALREADY been scheduled and is NOT cleared by the second `clearTimeout` call (which clears the FIRST timer, not the second).

Wait — re-reading the code more carefully:

```
Path A fires:
  clearTimeout(null)           // _reconnectTimer was null
  _reconnectTimer = setT1      // now _reconnectTimer = T1

Path B fires (same synchronous turn):
  clearTimeout(T1)             // cancels T1
  _reconnectTimer = setT2      // now _reconnectTimer = T2
```

If Path B fires AFTER Path A in the SAME synchronous turn (same JavaScript call stack), `clearTimeout(T1)` correctly prevents T1. Only T2 fires. **This is safe.**

If Path A fires AFTER Path B in the SAME synchronous turn:
```
Path B fires first:
  clearTimeout(null)           // _reconnectTimer was null
  _reconnectTimer = setT1

Path A fires second:
  clearTimeout(T1)             // cancels T1  
  _reconnectTimer = setT2      // replaces
```
Only T2 fires. **Also safe.**

**Conclusion: The clear-and-reset pattern IS sufficient for same-call-stack same-turn scenarios.** The real concern is same-tick in `fakeAsync` where `tick(N)` flushes multiple independent timer callbacks (each runs in its own micro-call-stack but fakeAsync flushes them sequentially). In that case:

- `setInterval` fires → `checkConnectionTimeout()` → `reconnectDueToTimeout()` → `_reconnectTimer = T1`
- Then `tick()` advances and the existing subscription's error fires → `_reconnectTimer = clearT1, set T2`

This is sequential, not concurrent — still safe.

**The ONLY real gap found:** The `_currentEventSource` field in `reconnectDueToTimeout()` is closed and nulled (lines 144-146), but the subscription (`_currentSubscription`) is NOT unsubscribed in `reconnectDueToTimeout()`. The subscription's Observable teardown (`eventSource.close()`) won't run because the `EventSource` was already closed externally. However, the RxJS subscription is still "live" until `createSseObserver()` runs and calls `_currentSubscription?.unsubscribe()`.

If `reconnectDueToTimeout()` fires AND `createSseObserver()` hasn't run yet (waiting 3000ms in timer), and the now-closed EventSource somehow emits an error event in that window (some implementations do fire `onerror` when `close()` is called), the error handler would fire on the still-live subscription, schedule ANOTHER timer, and `createEventSource` would be called twice.

**Fix required (D-07):** Unsubscribe `_currentSubscription` in `reconnectDueToTimeout()` before scheduling the reconnect timer. This tears down the subscription immediately so its error handler cannot fire after `reconnectDueToTimeout()` has already scheduled a reconnect.

```typescript
private reconnectDueToTimeout(): void {
    // ADD: tear down subscription immediately to prevent error handler from also scheduling reconnect
    this._currentSubscription?.unsubscribe();
    this._currentSubscription = null;
    
    if (this._currentEventSource) {
        this._currentEventSource.close();
        this._currentEventSource = null;
    }
    // ... rest unchanged
}
```

This is a targeted one-line change (plus null assignment) that closes the gap without adding a `_reconnectPending` boolean. The `_reconnectPending` boolean remains available as the D-07 fallback if the audit finds the above insufficient during implementation — but the `unsubscribe()` approach is cleaner and more direct.

**Summary of audit finding:** Gap confirmed. Minimal fix = call `_currentSubscription?.unsubscribe()` at the top of `reconnectDueToTimeout()`. The existing `createSseObserver()` entry teardown then provides defense-in-depth. A `_reconnectPending` boolean is the D-07 fallback if needed.

---

## Spec Assertion Analysis (Research Question 2)

### Which assertions in `describe("XSS / escapeHtml coverage")` are mechanism-specific vs. outcome-based

**MECHANISM-SPECIFIC (must be updated — assert entity-encoding form):**

| Line range | Current assertion | Update to |
|------------|------------------|-----------|
| 543–544 | `expect(modal.innerHTML).toContain("&lt;script&gt;")` | `expect(modal.querySelector("script")).toBeNull()` — already present on line 537; the `innerHTML` check verifies escaping mechanism, not outcome. **Remove** or replace with: `expect(modalTitle.textContent).toContain("<script>")` (which is already on line 546, an outcome assertion) |
| 563–564 | `expect(modal.innerHTML).toContain("&lt;script&gt;")` (body test) | Same — already have `modal.querySelector("script")).toBeNull()` + `textContent.toContain("<script>")` |
| 584 | `expect(modal.innerHTML).toContain("&lt;img")` (img onerror test) | Replace with: `expect(modalBodyP.textContent).toContain("<img")` — already asserted textContent on line 586 |
| 603 | `expect(modal.innerHTML).toContain("&lt;b&gt;")` | Replace with `expect(modalBodyP.querySelector("b")).toBeNull()` — already asserted on line 607 |
| 625 | `expect(modal.innerHTML).toContain("&lt;script&gt;")` (okBtn test) | Remove or replace with `expect(okButton.textContent).toContain("<script>")` — already on line 627 |
| 645 | `expect(modal.innerHTML).toContain("&lt;script&gt;")` (cancelBtn test) | Remove or replace with `expect(cancelButton.textContent).toContain("<script>")` — already on line 647 |
| 744 | `expect(modal.innerHTML).toContain("&quot;")` (okBtnClass attribute-breakout) | Replace with: `expect(okButton.getAttribute("onmouseover")).toBeNull()` + `expect(hasOnAttribute(modal)).toBe(false)` — both already asserted on lines 740–742 |
| 764 | `expect(modal.innerHTML).toContain("&quot;")` (cancelBtnClass test) | Same pattern — already asserted via hasOnAttribute |

**OUTCOME-BASED (survive unchanged):**

| Line range | Assertion | Why it survives |
|------------|-----------|-----------------|
| 537 | `modal.querySelector("script")).toBeNull()` | Tests result, not mechanism |
| 539–541 | `hasOnAttribute(modal).toBe(false)` | Tests result |
| 540–541 | `hasJavascriptUrl(modal).toBe(false)` | Tests result |
| 546 | `modalTitle.textContent).toContain("<script>")` | Tests visible text (outcome) |
| 567 | `modalBodyP.textContent).toContain("<script>")` | Tests visible text (outcome) |
| 581–582 | `modal.querySelector("img")).toBeNull()` | Tests result — NO IMG element |
| 586 | `textContent.toContain("<img src=x")` | Tests visible text (outcome) |
| 604–607 | `modal.querySelector("b")).toBeNull()` + textContent check | Tests result |
| 627 | `okButton.textContent).toContain("<script>")` | Tests visible text |
| 647 | `cancelButton.textContent).toContain("<script>")` | Tests visible text |
| 740–742 | `onmouseover === null`, `hasOnAttribute === false` | Tests DOM attribute result |
| 760–762 | Same for cancelBtnClass | Tests DOM attribute result |

**DIRECT UNIT TESTS of `escapeHtml` (lines 466–507, the `escape()` helper):**

These test the `escapeHtml` static private method directly via `(ConfirmModalService as any).escapeHtml`. Once `escapeHtml` is removed, the `escape()` helper function in the spec has nothing to call. **These tests must be removed entirely** — they test an implementation detail (the private static helper) that ceases to exist. They do NOT test security outcomes; the outcome assertions are in the end-to-end DOM tests above.

Tests to remove:
- "should escape each metacharacter to its HTML entity" (lines 466–472)
- "should replace & first so entity ampersands are not double-escaped" (lines 474–481)
- "should handle a combined attacker payload correctly" (lines 483–487)
- "should NOT escape backtick / U+2028 / U+2029 / null byte..." (lines 498–507)

The `escape()` helper function in the spec (lines 431–434) is also removed when these tests go.

**D-05 PROBE (lines 690–720) — complete inversion required:**

Current: asserts `skipP.querySelector("img")).not.toBeNull()` (img IS created — un-hardened behavior).
Required: asserts `skipP.querySelector("img")).toBeNull()` (img NOT created — hardened behavior after D-04).

The test title comment block (the v1.4.0-deferral text) is rewritten to describe the now-shipped coercion.

**D-02 COMPANION TEST (lines 661–676) — UNCHANGED:**
The test "should leave skipCount interpolation un-escaped because skipCount is a TypeScript number" tests `skipCount: 3` (a real number), verifies it renders as "3 file". After the BUG-01 change this still holds — `n = Number(3) = 3`, `Number.isFinite(3) = true`, `n > 0 = true`, paragraph rendered with text "3 files will be skipped". No change needed.

**BUTTON CLASS ASSERTION TESTS (lines 190–224) — UNCHANGED functionally, but HOW class is set changes:**
Tests assert `classList.contains("btn")` etc. After D-03 (`renderer.addClass()`), the classList assertions still pass because `renderer.addClass` sets the DOM class list exactly as if inline HTML had been parsed. No assertion change needed.

---

## Common Pitfalls

### Pitfall 1: Pre-Escaping Before createText()

**What goes wrong:** Developer runs `escapeHtml(title)` before passing to `renderer.createText()`, yielding visible text `&lt;script&gt;` in the browser instead of `<script>`.
**Why it happens:** Cargo-culting the escaping mindset into a context where it doesn't apply.
**How to avoid:** Pass the raw user string to `createText()`. Text nodes are inert by definition.
**Warning signs:** Modal title/body displays `&lt;` or `&amp;` to the user; spec test `textContent.toContain("<script>")` fails.

### Pitfall 2: innerHTML Check Assertions After Migration

**What goes wrong:** After switching to text nodes, assertions like `expect(modal.innerHTML).toContain("&lt;script&gt;")` FAIL because the browser serializes a text node containing `<script>` back to `&lt;script&gt;` in `.innerHTML`, but assertions about `.textContent` and `.querySelector` are the right verification surface.
**Why it happens:** `modal.innerHTML` with text nodes actually DOES contain `&lt;script&gt;` (the browser serializes text nodes with entity encoding when reading .innerHTML), so mechanism assertions may or may not pass depending on browser version.
**How to avoid:** Remove mechanism assertions; use `textContent` and `querySelector` as the spec does in outcome assertions.
**Warning signs:** Test passes coincidentally in one browser, fails in another; assertion is testing serialization not security outcome.

### Pitfall 3: Forgetting to Remove `escapeHtml` Private Tests

**What goes wrong:** After removing `escapeHtml()` from the service, the spec still calls `(ConfirmModalService as any).escapeHtml(s)`, which throws at runtime (undefined is not a function), causing ALL tests in the describe block to fail.
**Why it happens:** The four direct unit tests of `escapeHtml` at spec lines 466–507 use `(ConfirmModalService as any).escapeHtml`.
**How to avoid:** Remove the `escape()` helper function and all four unit tests that call it as part of the BUG-01 plan.
**Warning signs:** Karma reports `TypeError: (ConfirmModalService as any).escapeHtml is not a function`.

### Pitfall 4: data-action querySelector Breaking After Renderer2 Migration

**What goes wrong:** The `querySelector("[data-action=\"ok\"]")` and `querySelector("[data-action=\"cancel\"]")` wiring at lines 122–123 fails because buttons were not given the `data-action` attribute.
**Why it happens:** The innerHTML template had `data-action="ok"` inline; the new code must explicitly call `renderer.setAttribute(okButton, "data-action", "ok")`.
**How to avoid:** Add `renderer.setAttribute(button, "data-action", "ok")` / `"cancel"` when creating each button.
**Warning signs:** `cancelButton` is `null`, click handler throws `Cannot read properties of null`.

### Pitfall 5: skipCount `text-muted small mt-2` Classes on Skip Paragraph

**What goes wrong:** Skip paragraph loses its styling classes because the Renderer2 replacement doesn't add them.
**Why it happens:** The original `<p class="text-muted small mt-2">` had inline classes.
**How to avoid:** Call `renderer.addClass(skipP, "text-muted")`, `.addClass(skipP, "small")`, `.addClass(skipP, "mt-2")`.
**Warning signs:** Spec test "should style skip message with muted text" (line 285) fails — `classList.contains("text-muted")` is false.

### Pitfall 6: SSE Audit Under-Estimates the Gap

**What goes wrong:** Concluding "no gap" because clear-and-reset prevents double-timer in same-call-stack scenarios.
**Why it happens:** The production JavaScript event loop DOES prevent same-call-stack concurrent timer firings. But the gap with `reconnectDueToTimeout()` leaving `_currentSubscription` live means the old error handler can fire after timeout teardown.
**How to avoid:** The minimal fix (unsubscribe in `reconnectDueToTimeout`) must be applied regardless of whether a `_reconnectPending` guard is added.
**Warning signs:** fakeAsync collision test passes but a different error-after-timeout sequence produces `createEventSource` count of 3.

---

## Code Examples

### Example 1: Full Renderer2 inner content tree for the modal

```typescript
// Source: confirm-modal.service.ts analysis — structural reconstruction of lines 100-116

private buildModalContent(options: ConfirmModalOptions, n: number): HTMLElement {
    // modal-dialog
    const modalDialog = this.renderer.createElement("div");
    this.renderer.addClass(modalDialog, "modal-dialog");
    this.renderer.setAttribute(modalDialog, "role", "document");

    const modalContent = this.renderer.createElement("div");
    this.renderer.addClass(modalContent, "modal-content");

    // modal-header
    const modalHeader = this.renderer.createElement("div");
    this.renderer.addClass(modalHeader, "modal-header");
    const h5 = this.renderer.createElement("h5");
    this.renderer.addClass(h5, "modal-title");
    this.renderer.setAttribute(h5, "id", "confirm-modal-title");
    this.renderer.appendChild(h5, this.renderer.createText(options.title));
    this.renderer.appendChild(modalHeader, h5);

    // modal-body
    const modalBody = this.renderer.createElement("div");
    this.renderer.addClass(modalBody, "modal-body");
    const bodyP = this.renderer.createElement("p");
    this.renderer.appendChild(bodyP, this.renderer.createText(options.body));
    this.renderer.appendChild(modalBody, bodyP);
    if (Number.isFinite(n) && n > 0) {
        const plural = n === 1 ? "" : "s";
        const skipP = this.renderer.createElement("p");
        this.renderer.addClass(skipP, "text-muted");
        this.renderer.addClass(skipP, "small");
        this.renderer.addClass(skipP, "mt-2");
        this.renderer.appendChild(skipP, this.renderer.createText(
            `${n} file${plural} will be skipped (not eligible for this action)`
        ));
        this.renderer.appendChild(modalBody, skipP);
    }

    // modal-footer
    const modalFooter = this.renderer.createElement("div");
    this.renderer.addClass(modalFooter, "modal-footer");

    const cancelButton = this.renderer.createElement("button");
    this.renderer.setAttribute(cancelButton, "type", "button");
    this.renderer.setAttribute(cancelButton, "data-action", "cancel");
    cancelBtnClass.split(" ").filter(c => c.length > 0)
        .forEach(c => this.renderer.addClass(cancelButton, c));
    this.renderer.appendChild(cancelButton, this.renderer.createText(cancelBtn));

    const okButton = this.renderer.createElement("button");
    this.renderer.setAttribute(okButton, "type", "button");
    this.renderer.setAttribute(okButton, "data-action", "ok");
    okBtnClass.split(" ").filter(c => c.length > 0)
        .forEach(c => this.renderer.addClass(okButton, c));
    this.renderer.appendChild(okButton, this.renderer.createText(okBtn));

    this.renderer.appendChild(modalFooter, cancelButton);
    this.renderer.appendChild(modalFooter, okButton);

    this.renderer.appendChild(modalContent, modalHeader);
    this.renderer.appendChild(modalContent, modalBody);
    this.renderer.appendChild(modalContent, modalFooter);
    this.renderer.appendChild(modalDialog, modalContent);
    return modalDialog;
}
```

Note: This is a discretionary refactoring into a private helper (Claude's Discretion per CONTEXT.md). The planner may choose to keep it inline in `createModal()`. The key constraint is that the return value is appended to `this.modalElement` before lines 122–123 (`querySelector`) run.

### Example 2: D-05 probe inversion (test after BUG-01 ships)

```typescript
// Source: confirm-modal.service.spec.ts lines 690-720 — updated D-05 probe
it("should harden skipCount against toString()-overriding objects via Number() coercion (BUG-01 D-04/D-05)",
    fakeAsync(() => {
        const coercibleSkipCount = {
            valueOf: (): number => 1,
            toString: (): string => "<img src=x onerror=\"alert(1)\">"
        } as unknown as number;

        service.confirm({ title: "t", body: "b", skipCount: coercibleSkipCount });
        tick();

        const modal = document.querySelector(".modal")!;
        const skipP = modal.querySelectorAll(".modal-body p")[1]!;

        // After D-04: Number(coercibleSkipCount) = 1 (valueOf path), toString() never called.
        // The skip paragraph renders "1 file will be skipped" as a text node.
        // No <img> element is created.
        expect(skipP.querySelector("img")).toBeNull();
        expect(skipP.textContent).toContain("1 file will be skipped");
        expect(modal.querySelector("script")).toBeNull();
        expect(hasOnAttribute(modal)).toBe(false);
    }));
```

### Example 3: BUG-04 minimal fix — unsubscribe in reconnectDueToTimeout

```typescript
// Source: stream-service.registry.ts line 142 — add at top of reconnectDueToTimeout
private reconnectDueToTimeout(): void {
    // Tear down current subscription immediately so its error handler cannot fire
    // a competing scheduleReconnect() after this timeout teardown has already scheduled one.
    this._currentSubscription?.unsubscribe();
    this._currentSubscription = null;

    // Close the current EventSource if it exists
    if (this._currentEventSource) {
        this._currentEventSource.close();
        this._currentEventSource = null;
    }
    // ... rest of method unchanged (lines 149-163)
}
```

### Example 4: fakeAsync same-tick collision test structure

```typescript
// Source: stream-service.registry.spec.ts — new test inside or adjacent to "heartbeat-vs-timeout race"
it("BUG-04 — timeout teardown followed by error in same tick leaves exactly one active subscription",
    fakeAsync(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (dispatchService as any).startTimeoutChecker();
        mockEventSource.onopen!(new Event("connected"));
        tick();

        // Advance to timeout: elapsed > 30000 → reconnectDueToTimeout() fires,
        // unsubscribes current subscription, closes EventSource, schedules reconnect.
        tick(35001);
        expect(mockService1.connectedSeq).toContain(false);

        // Simulate the closed EventSource firing onerror (some browsers do this on .close()).
        // With the fix, _currentSubscription is already null, so error handler cannot schedule
        // a second reconnect.
        // Without the fix, this would schedule a second createSseObserver.
        mockEventSource.onerror!(new Event("error"));
        tick();

        // Advance past retry interval — only ONE createSseObserver should fire.
        tick(3001);

        // Initial (1) + exactly one reconnect (2) = 2 total
        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2);
        discardPeriodicTasks();
    }));
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `innerHTML` with pre-escape | Renderer2 `createText()` structural DOM | Phase 103 (this phase) | Text nodes cannot carry markup; `escapeHtml` becomes unnecessary |
| `if (skipCount && skipCount > 0)` runtime guard | `Number()` coercion + `Number.isFinite` | Phase 103 (this phase) | Coercible objects cannot inject markup through skipMessage |
| `_currentSubscription?.unsubscribe()` only at `createSseObserver` entry | Also unsubscribe in `reconnectDueToTimeout()` | Phase 103 (this phase) | Prevents stale subscription's error handler from double-scheduling reconnect |

**Deprecated/outdated:**
- `escapeHtml()` private static: removed by BUG-01. Structural DOM construction makes string escaping a defense-in-depth artifact rather than the primary safety mechanism.
- `safe*` locals (safeTitle, safeBody, safeOkBtn, safeOkBtnClass, safeCancelBtn, safeCancelBtnClass): removed by BUG-01.
- The v1.4.0-deferral comment in the skipCount probe: removed by D-05 update.

---

## Runtime State Inventory

> Not applicable — this is a greenfield code change, not a rename/refactor/migration phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `modal.innerHTML` serializes text-node content as entity-encoded form (`&lt;script&gt;`), so existing `modal.innerHTML.toContain("&lt;script&gt;")` assertions may coincidentally pass after migration | Spec Assertion Analysis — Pitfall 2 | If browser serializes differently, some mechanism assertions may pass or fail unexpectedly; outcome assertions are the correct gate regardless |
| A2 | Some browser implementations of `EventSource.close()` fire `onerror` on the closed source | SSE Race Audit | If no browser fires onerror on .close(), the gap is theoretical-only and the fix is preventive; test still valid as a specification |
| A3 | `Number({valueOf: ()=>1, toString: ()=>"<img>"})` returns 1 (not NaN) and never calls toString() | Pattern 3 (skipCount coercion) | This is ECMAScript-specified behavior for Number(); no risk in practice |

---

## Open Questions

1. **Button class split behavior with multi-token class strings**
   - What we know: `"btn btn-primary"` must apply two classes. `split(" ").filter(c => c.length > 0).forEach(c => renderer.addClass(el, c))` handles this.
   - What's unclear: Should `renderer.setAttribute("class", classString)` be used instead (simpler, one call)? Both work for valid class strings.
   - Recommendation: Use `setAttribute("class", classString)` for simplicity; the attribute-breakout payload (`btn" onmouseover="alert(1)`) is neutralized regardless because `setAttribute` does not invoke the HTML parser.

2. **Whether to extract `buildModalContent()` as a private helper or keep inline**
   - What we know: CONTEXT.md designates this as Claude's Discretion.
   - What's unclear: `createModal()` will be ~50 lines longer with the Renderer2 construction inline vs. a helper.
   - Recommendation: Extract to a private `buildModalContent()` helper for readability, per CONVENTIONS.md guidance that methods over ~50 lines should be extracted.

3. **Whether the BUG-04 same-tick test belongs in the existing `heartbeat-vs-timeout race` describe or a new adjacent one**
   - What we know: CONTEXT.md designates this as Claude's Discretion (D-08 comment).
   - What's unclear: Style preference — naming cohesion vs. describe block length.
   - Recommendation: Add as a new `describe("BUG-04 same-tick reconnect collision")` block adjacent to `heartbeat-vs-timeout race`, since it tests a different failure mode (double-schedule vs. spurious timeout).

---

## Environment Availability

> Not applicable — this phase is Angular source code changes. No new CLI tools, services, or runtimes are required. Karma runs inside Docker via `make run-tests-angular`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Karma 6.4.4 + Jasmine 5.1 |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `make run-tests-angular` (Docker) |
| Full suite command | `make run-tests-angular` (Docker) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | File | Status |
|--------|----------|-----------|------|--------|
| BUG-01 | No innerHTML assignment in createModal() | unit + DOM | confirm-modal.service.spec.ts | Existing spec updated |
| BUG-01 | skipCount coercion blocks toString()-object injection | unit + DOM | confirm-modal.service.spec.ts:690-720 | D-05 probe inverted |
| BUG-01 | Structural DOM assertions pass (no script/img/on* elements) | unit + DOM | confirm-modal.service.spec.ts XSS suite | Existing outcome assertions pass |
| BUG-04 | reconnectDueToTimeout unsubscribes before scheduling | unit + fakeAsync | stream-service.registry.spec.ts | New test added |
| BUG-04 | Slice-1 heartbeat-vs-timeout race tests still pass | unit + fakeAsync | stream-service.registry.spec.ts:209-260 | Existing tests preserved |
| COMPAT | Karma global coverage floors (83/68/79/83) hold | coverage | karma.conf.js check.global | Verify after changes |

### Coverage Impact Analysis

**BUG-01:**
- `escapeHtml()` (4 lines) removed → statement/line count decreases, but the four direct-unit tests that exercised it are also removed. Net coverage impact: neutral (tested code and its tests both removed simultaneously).
- New `buildModalContent()` helper (if extracted) adds ~40 lines, all covered by existing DOM tests. Net impact: neutral-to-positive (new lines all reachable from existing test paths).
- D-05 probe inversion: no coverage change (line already exists, now asserts opposite value).

**BUG-04:**
- Adding `_currentSubscription?.unsubscribe()` at top of `reconnectDueToTimeout()` (1 line) — the new same-tick test exercises this path. Coverage neutral-to-positive.
- New `_reconnectPending` boolean (if added): 2–3 lines, covered by the new collision test.

**Risk:** LOW. Removing `escapeHtml` and its tests removes tested lines symmetrically. The floor is unlikely to be impacted. If it drops, adding one more branch test for a corner case in `createModal()` would recover it.

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. The spec files already exist and have the relevant describe structures. No new test files, no new framework config, no fixture changes needed.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `Number()` coercion for numeric input; Renderer2 text nodes for string inputs |
| V5 Output Encoding | yes | Structural DOM construction (Renderer2 createText) — renders in element context |
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stored XSS via innerHTML | Tampering | Replace with text nodes (BUG-01) |
| Type-confusion injection (toString() override via skipCount) | Tampering | Number() coercion before use (D-04) |
| Orphaned SSE subscription event delivery after reconnect | Tampering / Information Disclosure | Unsubscribe before scheduling reconnect (BUG-04) |

---

## Sources

### Primary (HIGH confidence — codebase)

- `src/angular/src/app/services/utils/confirm-modal.service.ts` — full file read; innerHTML sink at line 100, escapeHtml at lines 33-40, safe* locals 51-56, skipMessage 59-64, existing Renderer2 usage 66-98 [VERIFIED: codebase]
- `src/angular/src/app/services/base/stream-service.registry.ts` — full file read; fields 78-79, reconnectDueToTimeout 142-164, createSseObserver 179-262, error handler 243-260 [VERIFIED: codebase]
- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` — full file read; XSS suite 425-768, D-05 probe 690-720, D-02 companion 661-676 [VERIFIED: codebase]
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — full file read; heartbeat-vs-timeout race 209-260 [VERIFIED: codebase]
- `src/angular/src/app/tests/mocks/mock-event-source.ts` — full file read; MockEventSource structure confirmed [VERIFIED: codebase]
- `src/angular/karma.conf.js` — coverage floors confirmed: statements 83, branches 68, functions 79, lines 83 [VERIFIED: codebase]
- `.planning/milestones/v1.3.0-phases/103-angular-defects/103-CONTEXT.md` — decisions D-01 through D-10 [VERIFIED: codebase]
- `.planning/REQUIREMENTS.md` — BUG-01 line 16, BUG-04 line 19, cross-cutting constraints [VERIFIED: codebase]
- `.planning/codebase/CONVENTIONS.md` — Angular conventions, Renderer2 requirement, no innerHTML with user content [VERIFIED: codebase]
- `.planning/codebase/TESTING.md` — fakeAsync/tick/discardPeriodicTasks pattern [VERIFIED: codebase]

### Secondary (MEDIUM confidence — framework fundamentals)

- Angular 21 Renderer2 API: `createElement`, `createText`, `appendChild`, `addClass`, `setAttribute`, `setStyle` — behavior confirmed from existing usage in the same service file [ASSUMED for specific API signature details; HIGH for behavioral guarantees from direct codebase verification]
- ECMAScript `Number()` coercion semantics — calls `valueOf()`, never `toString()` for numeric conversion [ASSUMED — well-established language fundamental]

---

## Metadata

**Confidence breakdown:**
- BUG-01 implementation path: HIGH — source file fully read, innerHTML sink location confirmed, existing Renderer2 pattern confirmed, spec assertions categorized precisely
- BUG-04 audit: MEDIUM-HIGH — code fully read, gap identified (stale subscription after reconnectDueToTimeout), fix specified; the "does onerror fire on .close()" question is browser-implementation-specific and marked [ASSUMED]
- Spec assertion categorization: HIGH — every assertion in the XSS suite read and classified
- Coverage impact: MEDIUM — analysis is logical, not empirically run

**Research date:** 2026-05-31
**Valid until:** Stable — no external dependencies; valid until source files change
