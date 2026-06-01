# Phase 103: Angular Defects - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 4 (2 service files modified, 2 spec files modified)
**Analogs found:** 4 / 4 (all files are self-analog — modifications to existing files, patterns extracted from within each file)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/services/utils/confirm-modal.service.ts` | service / DOM builder | request-response | Self (lines 66–98: existing Renderer2 backdrop/shell construction) | exact — same file, extend existing pattern |
| `src/angular/src/app/services/base/stream-service.registry.ts` | service / event-driven | event-driven | Self (lines 179–182: existing `createSseObserver` entry teardown) | exact — same file, extend existing teardown |
| `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` | test | request-response | Self (lines 425–768: XSS/escapeHtml describe block; DOM-assertion helpers) | exact — update existing tests in-place |
| `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` | test | event-driven | Self (lines 209–262: `heartbeat-vs-timeout race` describe block + fakeAsync harness) | exact — add sibling test in existing describe region |

---

## Pattern Assignments

### `confirm-modal.service.ts` (service, DOM builder)

**Primary change:** Replace `this.modalElement!.innerHTML = \`...\`` (lines 100–116) with a
`private buildModalContent()` helper (or inline block) that uses `renderer.createElement` /
`renderer.createText` / `renderer.appendChild` — the same API already used on lines 66–98.
Remove `escapeHtml()` (lines 33–40) and the six `safe*` locals (lines 51–56).
Add `Number()` coercion for `skipCount` (replace lines 59–64).

---

#### Analog: Renderer2 structural construction — backdrop (lines 66–78)

This is the direct model for every `createElement` / `addClass` / `setStyle` / `setAttribute` /
`appendChild` call in the new content tree.

```typescript
// confirm-modal.service.ts lines 66-78 — backdrop creation (READ-ONLY REFERENCE)
this.backdropElement = this.renderer.createElement("div");
this.renderer.addClass(this.backdropElement, "modal-backdrop");
this.renderer.addClass(this.backdropElement, "fade");
this.renderer.addClass(this.backdropElement, "show");
this.renderer.setStyle(this.backdropElement, "position", "fixed");
this.renderer.setStyle(this.backdropElement, "top", "0");
this.renderer.setStyle(this.backdropElement, "left", "0");
this.renderer.setStyle(this.backdropElement, "width", "100%");
this.renderer.setStyle(this.backdropElement, "height", "100%");
this.renderer.setStyle(this.backdropElement, "z-index", "1050");
this.renderer.appendChild(document.body, this.backdropElement);
```

---

#### Analog: Renderer2 structural construction — modal shell (lines 81–98)

Shows `setAttribute` for non-class attributes (`tabindex`, `role`, `aria-modal`,
`aria-labelledby`). The new content tree must use `setAttribute` the same way for
`data-action="ok"` / `data-action="cancel"` on the buttons, and `id="confirm-modal-title"`
on the `<h5>`.

```typescript
// confirm-modal.service.ts lines 81-98 — modal shell creation (READ-ONLY REFERENCE)
this.modalElement = this.renderer.createElement("div");
this.renderer.addClass(this.modalElement, "modal");
this.renderer.addClass(this.modalElement, "fade");
this.renderer.addClass(this.modalElement, "show");
this.renderer.setStyle(this.modalElement, "position", "fixed");
this.renderer.setStyle(this.modalElement, "top", "0");
this.renderer.setStyle(this.modalElement, "left", "0");
this.renderer.setStyle(this.modalElement, "width", "100%");
this.renderer.setStyle(this.modalElement, "height", "100%");
this.renderer.setStyle(this.modalElement, "display", "block");
this.renderer.setStyle(this.modalElement, "z-index", "1055");
this.renderer.setStyle(this.modalElement, "overflow-y", "auto");
this.renderer.setAttribute(this.modalElement, "tabindex", "-1");
this.renderer.setAttribute(this.modalElement, "role", "dialog");
this.renderer.setAttribute(this.modalElement, "aria-modal", "true");
this.renderer.setAttribute(this.modalElement, "aria-labelledby", "confirm-modal-title");
```

---

#### Pattern: `createText` for user strings (NEW — extends existing Renderer2 usage)

Every user-supplied string (`title`, `body`, `okBtn`, `cancelBtn`) must use this idiom.
`renderer.createText(s)` returns a DOM `Text` node. Text nodes are never parsed as HTML by
the browser — a payload `<script>alert(1)</script>` stored in a Text node renders as literal
characters and creates no child elements. Pass the raw (un-escaped) user string.

```typescript
// Pattern to apply — extends lines 66-98 style to content nodes
const h5 = this.renderer.createElement("h5");
this.renderer.addClass(h5, "modal-title");
this.renderer.setAttribute(h5, "id", "confirm-modal-title");
this.renderer.appendChild(h5, this.renderer.createText(options.title));  // TEXT NODE — raw string
this.renderer.appendChild(modalHeader, h5);

const bodyP = this.renderer.createElement("p");
this.renderer.appendChild(bodyP, this.renderer.createText(options.body));  // TEXT NODE — raw string
this.renderer.appendChild(modalBody, bodyP);
```

**Critical invariant:** Do NOT call `escapeHtml()` before `createText()`. `createText("&lt;script&gt;")` would render as the literal characters `&lt;script&gt;` visible to the user — the escaping step is harmful here, not protective.

---

#### Pattern: button classes via `addClass` / `setAttribute` (D-03)

```typescript
// For each button, apply class string structurally — no HTML parsing
// Option A: setAttribute (simpler, one call, adequate since Renderer2 bypasses HTML parser)
this.renderer.setAttribute(okButton, "class", okBtnClass);

// Option B: split and addClass per token
okBtnClass.split(" ").filter(c => c.length > 0)
    .forEach(c => this.renderer.addClass(okButton, c));

// data-action hook MUST be set so querySelector wiring at lines 122-123 survives
this.renderer.setAttribute(okButton, "type", "button");
this.renderer.setAttribute(okButton, "data-action", "ok");
this.renderer.setAttribute(cancelButton, "type", "button");
this.renderer.setAttribute(cancelButton, "data-action", "cancel");
```

---

#### Pattern: `skipCount` numeric coercion (D-04)

Replaces lines 59–64. `Number()` calls `valueOf()` on the argument and returns a primitive
`number`. A `toString()`-overriding object can no longer inject markup because `n` is a
primitive after `Number()`, and `${n}` in a template literal calls `Number.prototype.toString`,
not any custom `toString`.

```typescript
// Replace lines 59-64 with:
const n = Number(options.skipCount);
if (Number.isFinite(n) && n > 0) {
    const plural = n === 1 ? "" : "s";
    const skipP = this.renderer.createElement("p");
    this.renderer.addClass(skipP, "text-muted");
    this.renderer.addClass(skipP, "small");
    this.renderer.addClass(skipP, "mt-2");
    // n is a primitive number — `${n}` calls Number.prototype.toString, safe
    this.renderer.appendChild(skipP, this.renderer.createText(
        `${n} file${plural} will be skipped (not eligible for this action)`
    ));
    this.renderer.appendChild(modalBody, skipP);
}
```

---

#### Pattern: `appendChild` ordering constraint

The new content tree (modal-dialog → modal-content → header/body/footer) must be fully
assembled and appended to `this.modalElement` **before** the `querySelector` calls at
lines 122–123 run. The existing code calls `this.renderer.appendChild(document.body, this.modalElement)`
at line 118, then immediately queries. Mirror this: append the built subtree to
`this.modalElement` **before** line 118 runs.

```typescript
// Lines 118-123 (UNCHANGED — must still work after content tree is in place)
this.renderer.appendChild(document.body, this.modalElement);
this.renderer.addClass(document.body, "modal-open");

const cancelButton = this.modalElement!.querySelector("[data-action=\"cancel\"]") as HTMLElement;
const okButton = this.modalElement!.querySelector("[data-action=\"ok\"]") as HTMLElement;
```

---

### `stream-service.registry.ts` (service, event-driven)

**Primary change:** Add `this._currentSubscription?.unsubscribe(); this._currentSubscription = null;`
at the **top** of `reconnectDueToTimeout()` (before line 144), mirroring the identical teardown
already present at `createSseObserver()` entry (lines 181–182).

---

#### Analog: existing entry teardown in `createSseObserver` (lines 179–182)

This is the direct model for the BUG-04 fix. The same two-line pattern must be copied to the
top of `reconnectDueToTimeout()`.

```typescript
// confirm-modal.service.ts lines 179-182 — existing entry teardown (READ-ONLY REFERENCE)
private createSseObserver(): void {
    // Tear down previous subscription to prevent stale event delivery
    this._currentSubscription?.unsubscribe();
    this._currentSubscription = null;
    // ...
}
```

---

#### Analog: existing `reconnectDueToTimeout` structure (lines 142–163)

The fix inserts two lines at the top of this method; the rest is unchanged.

```typescript
// stream-service.registry.ts lines 142-163 — BEFORE fix (READ-ONLY REFERENCE)
private reconnectDueToTimeout(): void {
    // Close the current EventSource if it exists
    if (this._currentEventSource) {
        this._currentEventSource.close();
        this._currentEventSource = null;
    }

    // Reset last event time to prevent immediate re-trigger
    this._lastEventTime = 0;

    // Notify all services of disconnection
    for (const service of this._services) {
        this._zone.run(() => {
            service.notifyDisconnected();
        });
    }

    // Reconnect after a short delay
    if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
    }
    this._reconnectTimer = setTimeout(() => { this.createSseObserver(); }, this.STREAM_RETRY_INTERVAL_MS);
}
```

**Fix to apply — add these two lines at the very top of `reconnectDueToTimeout()`:**
```typescript
this._currentSubscription?.unsubscribe();
this._currentSubscription = null;
```

**Why:** Without this, `_currentSubscription` stays live for the 3000ms window between
`reconnectDueToTimeout()` scheduling the reconnect and `createSseObserver()` running. If
the now-closed EventSource fires `onerror` in that window (some implementations do this on
`.close()`), the subscription's `error` handler fires, schedules a second `createSseObserver`
timer, and `createEventSource` is called twice — once from the timeout path and once from the
error path.

---

#### Analog: error handler teardown pattern (lines 243–260)

The error handler is the other reconnect-arming path. Its clear-and-reset pattern is the model
for understanding why the fix goes in `reconnectDueToTimeout` (not here — the error handler
already nulls `_currentEventSource` at line 247 before scheduling; the gap is that it cannot
null `_currentSubscription` because it IS the subscription callback).

```typescript
// stream-service.registry.ts lines 243-260 — error handler (READ-ONLY REFERENCE)
error: err => {
    this._logger.error("Error in stream: %O", err);

    // Clear the EventSource reference
    this._currentEventSource = null;

    // Notify all services of disconnection
    for (const service of this._services) {
        this._zone.run(() => {
            service.notifyDisconnected();
        });
    }

    if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
    }
    this._reconnectTimer = setTimeout(() => { this.createSseObserver(); }, this.STREAM_RETRY_INTERVAL_MS);
}
```

---

### `confirm-modal.service.spec.ts` (test)

**Three groups of changes:**

1. **Remove** the `escape()` helper (lines 431–434) and the four direct `escapeHtml` unit tests (lines 466–507) — these call `(ConfirmModalService as any).escapeHtml` which will no longer exist.
2. **Update** mechanism-specific assertions (those checking `modal.innerHTML` for entity-encoded form like `&lt;script&gt;` or `&quot;`) — replace with the outcome-based equivalents already present in the same test (see table in RESEARCH.md §Spec Assertion Analysis).
3. **Invert** the D-05 runtime-boundary probe (lines 690–720) — from asserting `img` IS created to asserting it IS NOT created.

---

#### Analog: outcome-based DOM assertion pattern (lines 525–547)

This is the canonical pattern all updated/new assertions must follow. It shows the four
assertion layers (no script element, no on-attribute, no javascript: URL, textContent check).
The `modal.innerHTML.toContain("&lt;script&gt;")` lines (543–544) are the mechanism-specific
ones that must be removed or replaced.

```typescript
// confirm-modal.service.spec.ts lines 525-547 — title XSS test (READ-ONLY REFERENCE)
it("should produce no executable markup when title contains a script payload",
    fakeAsync(() => {
        service.confirm({
            title: "<script>alert(\"xss\")</script>",
            body: "safe body"
        });
        tick();

        const modal = document.querySelector(".modal")!;
        const modalTitle = modal.querySelector(".modal-title")!;

        // (a) No parsed script element
        expect(modal.querySelector("script")).toBeNull();
        // (b) No on* event-handler attribute anywhere in the subtree
        expect(hasOnAttribute(modal)).toBe(false);
        // (c) No javascript: URL
        expect(hasJavascriptUrl(modal)).toBe(false);
        // (d) MECHANISM assertion — targets entity-encoding; REMOVE after text-node migration
        expect(modal.innerHTML).toContain("&lt;script&gt;");
        expect(modal.innerHTML).toContain("&lt;/script&gt;");
        // Outcome assertion — survives unchanged (text nodes render payload as visible text)
        expect(modalTitle.textContent).toContain("<script>");
    }));
```

**After BUG-01:** Remove lines `expect(modal.innerHTML).toContain("&lt;script&gt;")` and
`expect(modal.innerHTML).toContain("&lt;/script&gt;")` from this and all parallel tests.
The `textContent` and `querySelector` assertions remain. See RESEARCH.md §Spec Assertion
Analysis for the complete per-line table.

---

#### Analog: `hasOnAttribute` / `hasJavascriptUrl` helpers (lines 440–461)

These helpers are defined in the `describe("XSS / escapeHtml coverage")` scope. They are
outcome-based (DOM attribute walk, not string check) and survive unchanged. New assertions
should continue using them.

```typescript
// confirm-modal.service.spec.ts lines 440-461 — helper functions (READ-ONLY REFERENCE)
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

function hasJavascriptUrl(root: Element): boolean {
    return Array.from(root.querySelectorAll("[href],[src]")).some(el =>
        (el.getAttribute("href") || "").toLowerCase().startsWith("javascript:") ||
        (el.getAttribute("src") || "").toLowerCase().startsWith("javascript:")
    );
}
```

---

#### Analog: D-05 probe to invert (lines 690–720)

The existing test (lines 690–720) is the target for D-05. Its structure (fakeAsync,
`confirm({..., skipCount: coercibleObject})`, `tick()`, `querySelector(".modal")`,
`querySelectorAll(".modal-body p")[1]`) must be preserved. Only the assertion and comment
block change.

```typescript
// confirm-modal.service.spec.ts lines 690-720 — BEFORE inversion (READ-ONLY REFERENCE)
it("should pin the runtime behavior of skipCount when a caller defeats the " +
   "TypeScript number type with a coercible object ...",
    fakeAsync(() => {
        const coercibleSkipCount = {
            valueOf: (): number => 1,
            toString: (): string => "<img src=x onerror=\"alert(1)\">"
        } as unknown as number;

        service.confirm({ title: "t", body: "b", skipCount: coercibleSkipCount });
        tick();

        const modal = document.querySelector(".modal")!;
        const skipP = modal.querySelectorAll(".modal-body p")[1]!;

        // OLD assertion (un-hardened behavior) — INVERT this:
        expect(skipP.querySelector("img")).not.toBeNull();   // ← CHANGE to .toBeNull()
        expect(skipP.textContent).toContain("files will be skipped");
    }));
```

**After D-05 update:** the assertion becomes `expect(skipP.querySelector("img")).toBeNull()`
and `expect(skipP.textContent).toContain("1 file will be skipped")` (singular, because
`Number({valueOf:()=>1})` = `1`, and `n === 1` is `true`). The comment block is rewritten
to describe the now-shipped coercion (remove v1.4.0-deferral language).

---

#### Analog: D-02 companion test (lines 661–676) — UNCHANGED

This test confirms a real numeric `skipCount: 3` still renders correctly. It is the model
for what the D-05 probe should look like after inversion (same assertion style, real
number path).

```typescript
// confirm-modal.service.spec.ts lines 661-676 — stays valid, no changes (READ-ONLY REFERENCE)
it("should leave skipCount interpolation un-escaped because skipCount is a " +
   "TypeScript number, not an attacker-controlled string ...", fakeAsync(() => {
    service.confirm({ title: "t", body: "b", skipCount: 3 });
    tick();

    const modal = document.querySelector(".modal")!;
    const skipP = modal.querySelectorAll(".modal-body p")[1]!;

    expect(skipP.textContent).toContain("3 file");
    expect(skipP.textContent).toContain("will be skipped");
    expect(modal.querySelector("script")).toBeNull();
    expect(hasOnAttribute(modal)).toBe(false);
}));
```

---

### `stream-service.registry.spec.ts` (test)

**Primary change:** Add a new `describe("BUG-04 same-tick reconnect collision")` block
(or a sibling `it()` inside `heartbeat-vs-timeout race`) asserting that when timeout teardown
fires and then `onerror` fires, exactly one `createEventSource` call results.

---

#### Analog: `heartbeat-vs-timeout race` describe block (lines 209–262)

This is the **complete** model for the new BUG-04 test. Reuse the same:
- `(dispatchService as any).startTimeoutChecker()` call
- `mockEventSource.onopen!(new Event("connected"))` + `tick()` to seed `_lastEventTime`
- `tick(35001)` to advance past the timeout boundary
- `expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(N)` assertion
- `discardPeriodicTasks()` cleanup

```typescript
// stream-service.registry.spec.ts lines 209-262 — heartbeat-vs-timeout describe (READ-ONLY REFERENCE)
describe("heartbeat-vs-timeout race", () => {
    it("heartbeat after timeout boundary re-arms _lastEventTime and prevents spurious reconnect", fakeAsync(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (dispatchService as any).startTimeoutChecker();
        mockEventSource.onopen!(new Event("connected"));
        tick();

        tick(30001);

        mockEventSource.listeners.get("ping")!(new Event("ping"));

        tick(5000);

        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1);
        expect(mockService1.connectedSeq).not.toContain(false);
        expect(mockService2.connectedSeq).not.toContain(false);
        discardPeriodicTasks();
    }));

    it("without heartbeat, timeout fires and reconnect occurs (positive control)", fakeAsync(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (dispatchService as any).startTimeoutChecker();
        mockEventSource.onopen!(new Event("connected"));
        tick();

        tick(35001);

        expect(mockService1.connectedSeq).toContain(false);
        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1);

        tick(3001);
        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2);
        discardPeriodicTasks();
    }));
});
```

---

#### Pattern: BUG-04 same-tick collision test structure (NEW — mirrors heartbeat-vs-timeout)

Add as a sibling `describe` block immediately after the `heartbeat-vs-timeout race` describe
(after line 262). The setup (`startTimeoutChecker`, `onopen`, initial `tick`) is identical.
The key sequence is: advance past timeout so `reconnectDueToTimeout` fires AND unsubscribes
`_currentSubscription`, then fire `onerror` on the same `mockEventSource` to verify the
error handler does NOT schedule a second reconnect (because `_currentSubscription` is already
null after the fix).

```typescript
// New describe block — add after line 262 (after the closing }); of heartbeat-vs-timeout race)
describe("BUG-04 same-tick reconnect collision", () => {
    it("BUG-04 — timeout teardown followed by onerror in same tick leaves exactly one active EventSource",
        fakeAsync(() => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (dispatchService as any).startTimeoutChecker();
            mockEventSource.onopen!(new Event("connected"));
            tick();

            // Advance past timeout → reconnectDueToTimeout() fires:
            //   - _currentSubscription unsubscribed + nulled (BUG-04 fix)
            //   - _currentEventSource closed + nulled
            //   - reconnect timer armed (T+3000ms)
            tick(35001);
            expect(mockService1.connectedSeq).toContain(false);

            // Simulate the closed EventSource firing onerror (some browsers do this on .close()).
            // With the fix: _currentSubscription is null, so observable.subscribe error handler
            // is no longer live — onerror fires on the closed EventSource but no new timer is armed.
            // Without the fix: error handler would fire, schedule a SECOND createSseObserver.
            mockEventSource.onerror!(new Event("error"));
            tick();

            // Advance past retry interval — only ONE reconnect timer should fire
            tick(3001);

            // Initial (1) + exactly one reconnect (2) = 2 total
            // If the bug is present, this would be 3 (initial + timeout reconnect + error reconnect)
            expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2);
            discardPeriodicTasks();
        }));
});
```

---

#### Analog: MockEventSource (mock-event-source.ts lines 1–59)

The `MockEventSource` used by the existing suite is the mock harness for the new test. No new
mock file is needed. The new test uses the same `mockEventSource` variable populated by the
`beforeEach` spy on `EventSourceFactory.createEventSource` (lines 51–55 of the spec).

```typescript
// src/angular/src/app/tests/mocks/mock-event-source.ts lines 6-59 — REUSED AS-IS
// Key properties used in new BUG-04 test:
//   mockEventSource.onopen   — seed _lastEventTime
//   mockEventSource.onerror  — fire error after timeout teardown
//   mockEventSource.close()  — already spied; confirms EventSource was closed
```

---

## Shared Patterns

### fakeAsync + tick + discardPeriodicTasks idiom
**Source:** `stream-service.registry.spec.ts` — used throughout
**Apply to:** All SSE-related tests (existing heartbeat tests + new BUG-04 test)

```typescript
// stream-service.registry.spec.ts lines 1, 43-69 — test setup and fakeAsync idiom
import {discardPeriodicTasks, fakeAsync, TestBed, tick} from "@angular/core/testing";

beforeEach(fakeAsync(() => {
    // ... TestBed.configureTestingModule ...
    dispatchService.onInit();
    tick();
    discardPeriodicTasks();
}));

// Every it() that touches timers ends with discardPeriodicTasks()
```

### `(service as any).privateMethod()` for private method access in tests
**Source:** `stream-service.registry.spec.ts` lines 212, 241 (`(dispatchService as any).startTimeoutChecker()`)
**Apply to:** BUG-04 new test (same pattern for `startTimeoutChecker`)

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(dispatchService as any).startTimeoutChecker();
```

### querySelector + textContent + classList DOM assertion style
**Source:** `confirm-modal.service.spec.ts` — used throughout the XSS suite (lines 525–768)
**Apply to:** All confirm-modal spec assertions; the outcome assertions survive BUG-01 unchanged

```typescript
// Canonical DOM assertion idiom — query, then check content/attribute/structure
const modal = document.querySelector(".modal")!;
const modalTitle = modal.querySelector(".modal-title")!;
expect(modal.querySelector("script")).toBeNull();           // structural outcome
expect(hasOnAttribute(modal)).toBe(false);                  // attribute walk
expect(modalTitle.textContent).toContain("<script>");       // visible text outcome
expect(okButton.getAttribute("onmouseover")).toBeNull();    // specific attribute
```

### Renderer2 injection pattern
**Source:** `confirm-modal.service.ts` lines 17–25
**Apply to:** BUG-01 changes — Renderer2 is already injected; no new injection needed

```typescript
// confirm-modal.service.ts lines 17-25 — already in place, do not re-add
private renderer: Renderer2;

constructor(rendererFactory: RendererFactory2) {
    this.renderer = rendererFactory.createRenderer(null, null);
}
```

---

## No Analog Found

All four files are modifications of existing files with self-referential analogs. No file
lacks a concrete pattern source in the codebase.

---

## Metadata

**Analog search scope:** `src/angular/src/app/services/`, `src/angular/src/app/tests/`
**Files read:** 6 (confirm-modal.service.ts, stream-service.registry.ts, confirm-modal.service.spec.ts, stream-service.registry.spec.ts, mock-event-source.ts, 103-CONTEXT.md + 103-RESEARCH.md)
**Pattern extraction date:** 2026-05-31
