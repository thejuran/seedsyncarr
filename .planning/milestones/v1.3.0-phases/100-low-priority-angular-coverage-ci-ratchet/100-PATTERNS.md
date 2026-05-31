# Phase 100: Low-Priority Angular Coverage + CI Ratchet — Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 6 (2 spec extensions, 2 config patches, 1 toml bump, 3 doc updates)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` | test (extend) | event-driven | Same file — existing `fakeAsync` reconnect tests (lines 180–207) | exact |
| `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` | test (extend) | request-response | Same file — existing cache test (lines 94–114) | exact |
| `src/angular/karma.conf.js` | config (patch) | — | Same file — existing `coverageReporter` block (lines 23–26) | exact (net-new block added) |
| `src/docker/test/angular/Dockerfile` | config (patch) | — | Same file — existing CMD (lines 31–33) | exact (flag added) |
| `src/python/pyproject.toml` | config (patch) | — | Same file — `[tool.coverage.report] fail_under` at line 88 | exact (number bump) |
| `.planning/ROADMAP.md`, `.planning/RETROSPECTIVE.md`, `.planning/PROJECT.md` | doc (patch) | — | Existing ROADMAP table (lines 302–310), RETROSPECTIVE entries (lines 4–77), PROJECT.md Key Decisions table (lines 360–399) | exact |

---

## Pattern Assignments

### `stream-service.registry.spec.ts` — EXTEND with SSE heartbeat-vs-timeout race (100-01)

**Analog:** Same file, `describe("Testing stream dispatch service")` block.

**Harness bootstrap pattern** (lines 43–69) — the `beforeEach` that sets up the spy, MockEventSource, and service, then calls `discardPeriodicTasks()`:

```typescript
beforeEach(fakeAsync(() => {
    TestBed.configureTestingModule({
        providers: [
            LoggerService,
            StreamDispatchService
        ]
    });

    spyOn(EventSourceFactory, "createEventSource").and.callFake(
        (url: string) => {
            mockEventSource = createMockEventSource(url);
            return mockEventSource as unknown as EventSource;
        }
    );
    mockService1 = new MockStreamService();
    mockService2 = new MockStreamService();
    spyOn(mockService1, "getEventNames").and.returnValue(["event1a", "event1b"]);
    spyOn(mockService2, "getEventNames").and.returnValue(["event2a", "event2b"]);

    dispatchService = TestBed.inject(StreamDispatchService);

    dispatchService.registerService(mockService1);
    dispatchService.registerService(mockService2);
    dispatchService.onInit();
    tick();
    discardPeriodicTasks();   // ← kills the setInterval; new tests must re-arm it
}));
```

**Critical re-arm pattern** — the `beforeEach` discards the periodic task; tests requiring the interval must restart it via private access:

```typescript
// At the TOP of any it() that needs the timeout checker interval:
(dispatchService as any).startTimeoutChecker();
```

This is consistent with the existing private-access pattern at spec line 152:
```typescript
(dispatchService as any)._eventNameToServiceMap.delete("event1a");
```

**`onopen` seed pattern** (lines 172–178) — required before advancing time; without it `_lastEventTime === 0` and the guard bails:

```typescript
it("should call connect on open", fakeAsync(() => {
    mockEventSource.onopen!(new Event("connected"));
    tick();
    expect(mockService1.connectedSeq).toEqual([true]);
    expect(mockService2.connectedSeq).toEqual([true]);
    discardPeriodicTasks();
}));
```

**Error-then-reconnect `tick()` pattern** (lines 189–207) — the closest analog for multi-step time advancement with `discardPeriodicTasks()` at the end:

```typescript
it("should send events after reconnect", fakeAsync(() => {
    mockEventSource.onopen!(new Event("connected"));
    tick();
    mockEventSource.onerror!(new Event("bad event"));
    tick(4000);
    mockEventSource.onopen!(new Event("connected"));
    tick();
    mockEventSource.listeners.get("event1a")!(<MessageEvent>{data: "data1a"});
    tick();
    expect(mockService1.eventList).toEqual([["event1a", "data1a"]]);
    discardPeriodicTasks();
}));
```

**Listener-fire pattern** — how to fire a named listener from `mockEventSource.listeners`:

```typescript
// Fire a named event listener (used in multiple existing tests):
mockEventSource.listeners.get("event1a")!(<MessageEvent>{data: "data1a"});
tick();

// Fire the heartbeat listener (same mechanism, different key):
mockEventSource.listeners.get("ping")!(new Event("ping"));
// No tick() between this and the subsequent tick() — same fakeAsync frame
```

**`discardPeriodicTasks()` placement rule** — every `it()` that calls `startTimeoutChecker()` must end with `discardPeriodicTasks()`, mirroring lines 73, 90, 139, 169, 177, 186, 206.

**New test structure to build (100-01)** — based on the Research tick-sequence derivation:

Two `it()` blocks inside a nested `describe`:

```typescript
describe("heartbeat-vs-timeout race", () => {
    it("heartbeat in same frame as timeout boundary prevents spurious reconnect", fakeAsync(() => {
        (dispatchService as any).startTimeoutChecker();
        mockEventSource.onopen!(new Event("connected"));
        tick();

        // Advance 30001ms: 6 interval checks fire (T=5000..30000), none reconnect
        // (elapsed > 30000 is strict; at T=30000 elapsed=30000, NOT > 30000)
        tick(30001);

        // Fire heartbeat in the same fakeAsync frame — no tick() separating
        // _lastEventTime is now updated to ~30001ms (virtual time)
        mockEventSource.listeners.get("ping")!(new Event("ping"));

        // Advance to next interval boundary (T=35000ms)
        // elapsed = 35000 - 30001 = 4999ms < 30000ms → NO reconnect
        tick(5000);

        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1);
        expect(mockService1.connectedSeq).not.toContain(false);
        expect(mockService2.connectedSeq).not.toContain(false);
        discardPeriodicTasks();
    }));

    it("without heartbeat, timeout fires and reconnect occurs (positive control)", fakeAsync(() => {
        (dispatchService as any).startTimeoutChecker();
        mockEventSource.onopen!(new Event("connected"));
        tick();

        // Advance 35001ms: at T=35000 elapsed=35000 > 30000 → reconnectDueToTimeout fires
        tick(35001);

        expect(mockService1.connectedSeq).toContain(false);
        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1); // reconnect timer pending

        // Advance past STREAM_RETRY_INTERVAL_MS=3000ms
        tick(3001);
        expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2); // reconnect happened
        discardPeriodicTasks();
    }));
});
```

**MockEventSource API surface used** (from `src/angular/src/app/tests/mocks/mock-event-source.ts`):

```typescript
// Direct onopen call (synchronous in fakeAsync)
mockEventSource.onopen!(new Event("connected"));

// Fire named listener
mockEventSource.listeners.get("ping")!(new Event("ping"));

// Listener existence already asserted in existing spec line 89:
expect(mockEventSource.listeners.has("ping")).toBe(true);
```

---

### `auth.interceptor.spec.ts` — EXTEND with token rotation test (100-02)

**Analog:** Same file, `"should cache the token and not re-read meta tag on each request"` (lines 94–114).

**`setupWithMeta` helper** (lines 11–38) — reuse verbatim; do NOT call `_resetAuthInterceptorCache()` again before the first request (it is already called inside `setupWithMeta` at line 27):

```typescript
function setupWithMeta(content: string | null): void {
    const existing = document.querySelector("meta[name=\"api-token\"]");
    if (existing) { existing.remove(); }

    if (content !== null) {
        const meta = document.createElement("meta");
        meta.setAttribute("name", "api-token");
        meta.setAttribute("content", content);
        document.head.appendChild(meta);
    }

    _resetAuthInterceptorCache();   // ← already resets cache; do NOT call again before req1

    TestBed.configureTestingModule({
        providers: [
            provideHttpClient(withInterceptors([authInterceptor])),
            provideHttpClientTesting(),
        ]
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
}
```

**`afterEach` cleanup** (lines 40–48) — reuse verbatim; do NOT duplicate:

```typescript
afterEach(() => {
    httpMock.verify();
    const meta = document.querySelector("meta[name=\"api-token\"]");
    if (meta) { meta.remove(); }
    _resetAuthInterceptorCache();
});
```

**Mirror analog** — the negative case (lines 94–114) proves stale-by-design without reset; the new test is its mirror positive (with reset):

```typescript
it("should cache the token and not re-read meta tag on each request", () => {
    setupWithMeta("cached-token");

    httpClient.get("/api/first", {responseType: "text"}).subscribe();
    const req1 = httpMock.expectOne("/api/first");
    expect(req1.request.headers.get("Authorization")).toBe("Bearer cached-token");
    req1.flush("ok");

    // Change the meta tag WITHOUT resetting cache → stale token (negative case)
    const meta = document.querySelector("meta[name=\"api-token\"]");
    if (meta) { meta.setAttribute("content", "new-token"); }

    httpClient.get("/api/second", {responseType: "text"}).subscribe();
    const req2 = httpMock.expectOne("/api/second");
    expect(req2.request.headers.get("Authorization")).toBe("Bearer cached-token"); // stale
    req2.flush("ok");
});
```

**New test structure to build (100-02)** — mirror of the above with one added step (`_resetAuthInterceptorCache()` between requests):

```typescript
it("should serve new token after _resetAuthInterceptorCache is called (token rotation)", () => {
    // Production coupling note:
    // _resetAuthInterceptorCache has no production caller in this codebase.
    // Token rotation is realized by a full page reload: the user navigates to /
    // or reloads, the browser re-fetches index.html, the Angular module re-instantiates,
    // and cachedToken / tokenRead reset to null / false. This test pins the mechanism
    // that a page reload relies on.

    setupWithMeta("token-v1");

    httpClient.get("/api/first", {responseType: "text"}).subscribe();
    const req1 = httpMock.expectOne("/api/first");
    expect(req1.request.headers.get("Authorization")).toBe("Bearer token-v1");
    req1.flush("ok");

    // Simulate token rotation: meta tag updated, cache reset
    const meta = document.querySelector("meta[name=\"api-token\"]");
    if (meta) { meta.setAttribute("content", "token-v2"); }
    _resetAuthInterceptorCache();   // ← the intentional mid-test reset (not a setup call)

    httpClient.get("/api/second", {responseType: "text"}).subscribe();
    const req2 = httpMock.expectOne("/api/second");
    expect(req2.request.headers.get("Authorization")).toBe("Bearer token-v2");
    req2.flush("ok");
});
```

**Import pattern** (lines 1–5) — both `_resetAuthInterceptorCache` and `authInterceptor` are already imported; no new imports needed for 100-02:

```typescript
import {TestBed} from "@angular/core/testing";
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {authInterceptor, _resetAuthInterceptorCache} from "../../../../services/utils/auth.interceptor";
```

---

### `src/angular/karma.conf.js` — PATCH: replace `coverageReporter` block (100-03)

**Analog:** Same file, existing `coverageReporter` block (lines 23–26).

**Current state** (lines 23–26) — single reporter, no `check.global`:

```javascript
coverageReporter: {
    type: 'html',
    dir: 'coverage/'
},
```

**Target state** — multi-reporter array plus `check.global` (values are TBD until post-100-01/02 re-measurement; fill in per D-07: `floor(measured) - 1`):

```javascript
coverageReporter: {
    dir: 'coverage/',
    reporters: [
        { type: 'html', subdir: '.' },
        { type: 'text-summary' }
    ],
    check: {
        global: {
            statements: XX,   // floor(post-100-02 measured statements%) - 1
            branches:   XX,   // floor(post-100-02 measured branches%) - 1
            functions:  XX,   // floor(post-100-02 measured functions%) - 1
            lines:      XX    // floor(post-100-02 measured lines%) - 1
            // emitWarning: false  ← omit entirely (defaults to false; never set true)
        }
    }
},
```

Verified against `src/angular/node_modules/karma-coverage/docs/configuration.md` (v2.2.1 installed): `reporters` array syntax and `check.global` keys (`statements`, `branches`, `functions`, `lines`) are documented features.

The `text-summary` reporter is mandatory: it emits the 4-line summary to stdout headlessly so the `check` block actually runs and fails the process with a non-zero exit code when below threshold.

---

### `src/docker/test/angular/Dockerfile` — PATCH: add `--code-coverage` to CMD (100-03)

**Analog:** Same file, CMD at lines 31–33.

**Current state** (lines 31–33):

```dockerfile
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false"]
```

**Target state** — add `--code-coverage` as the final flag:

```dockerfile
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false", \
     "--code-coverage"]
```

This is a mandatory companion change to the `karma.conf.js` `check.global` block. Without `--code-coverage`, Istanbul instrumentation does not run, no coverage data is emitted, and the `check.global` threshold is a silent no-op.

Both files must land in the same commit (D-06 mandate: one revert target).

---

### `src/python/pyproject.toml` — PATCH: bump `fail_under` (100-03)

**Analog:** Same file, `[tool.coverage.report]` section at lines 87–88.

**Current state** (lines 87–88):

```toml
[tool.coverage.report]
fail_under = 84
```

**Target state** — bump to `floor(post-Phase-99 measured line%) - 1` (exact value TBD; re-measure via `make coverage-python` before writing):

```toml
[tool.coverage.report]
fail_under = 85   # TBD: floor(now) - 1; fill after re-measure
```

Note: `[tool.pytest.ini_options]` addopts at lines 69–77 has NO `--cov` or `--cov-fail-under` (confirmed). Only `[tool.coverage.report] fail_under` needs bumping (D-06 is confirmed correct).

---

### `.planning/ROADMAP.md` — PATCH: fill TBD rows in Coverage Ratchet table (100-03)

**Analog:** Same file, Coverage Ratchet table at lines 302–310.

**Current state** (lines 306–310):

```markdown
| Layer | Threshold | Before | After |
|-------|-----------|--------|-------|
| Python (`--cov-fail-under`) | line | 85.19% measured (floor 84); host/provisional — excludes real-lftp integration suite | TBD (Phase 100) |
| Angular (Karma `coverageReporter.check.global`) | statements / branches / functions / lines | 83.34% / 69.01% / 79.73% / 84.21% (no Karma global threshold configured yet) | TBD (Phase 100) |
```

**Target state** — replace both "TBD (Phase 100)" cells with re-measured post-100-01/02 numbers and the chosen floor values.

---

### `.planning/RETROSPECTIVE.md` — ADD v1.3.0 entry (100-03)

**Analog:** Existing milestone entries — v1.1.2 (lines 5–36) and v1.2.0 (lines 39–78).

**Entry template shape** (mirror of v1.1.2 and v1.2.0 entries):

```markdown
## Milestone: v1.3.0 — Test Coverage Gaps

**Shipped:** 2026-05-XX
**Phases:** 4 | **Plans:** 9

### What Was Built
- [bullet list: tests added, coverage numbers before/after, CI ratchet outcome]

### What Worked
- [bullet list]

### What Was Inefficient
- [bullet list]

### Patterns Established
- [bullet list]

### Key Lessons
1. [numbered lessons]
```

The `### Coverage` subsection (if added) follows the same 4-column table shape used in `## Cross-Milestone Trends` → `### Cumulative Quality` (lines 94–99):

```markdown
| Milestone | Python Tests | Angular Tests | E2E Specs | Python Coverage |
```

---

### `.planning/PROJECT.md` — ADD floor-decision row to Key Decisions table (100-03)

**Analog:** Same file, Key Decisions table at lines 360–399. Every row follows this shape:

```markdown
| Decision text | Rationale sentence | ✓ Good |
```

**New row to add** (D-07 mandate — log floor and margin):

```markdown
| Angular Karma coverage floor: statements/branches/functions/lines set at floor(measured)-1 | ~0.5–1% jitter buffer prevents brittle failures on trivial uncovered lines while still raising bar substantially above baseline | ✓ Good |
| Python fail_under bumped from 84 to floor(measured)-1 (Phase 100 re-measure) | Monotonic ratchet against post-v1.3.0 measured coverage; margin absorbs measurement variance | ✓ Good |
```

---

## Shared Patterns

### fakeAsync + discardPeriodicTasks discipline
**Source:** `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` lines 67–68 and every `it()` ending.
**Apply to:** 100-01 both `it()` blocks.

Every `it()` that calls `startTimeoutChecker()` must end with `discardPeriodicTasks()`. Angular throws "1 timer(s) still in the queue" if a `setInterval` is left running at the end of a `fakeAsync` test. The outer `beforeEach` already handles the `onInit`-started interval; tests that re-arm via `startTimeoutChecker()` must clean up independently.

```typescript
// Mandatory at end of every it() that calls startTimeoutChecker():
discardPeriodicTasks();
```

### HttpTestingController flush discipline
**Source:** `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` lines 53–57 and `afterEach` line 41.
**Apply to:** 100-02 `it()` block.

Every `httpMock.expectOne()` result must be flushed (`req.flush(...)`) before the test ends. `httpMock.verify()` in `afterEach` (line 41) catches any unflushed requests and fails the test. Pattern:

```typescript
httpClient.get("/api/first", {responseType: "text"}).subscribe();
const req1 = httpMock.expectOne("/api/first");
expect(req1.request.headers.get("Authorization")).toBe("Bearer token-v1");
req1.flush("ok");   // ← mandatory; verify() in afterEach will catch if omitted
```

### Private-field access via `as any`
**Source:** `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` line 152.
**Apply to:** 100-01 `startTimeoutChecker()` call.

```typescript
// Existing use at line 152:
(dispatchService as any)._eventNameToServiceMap.delete("event1a");

// New use (same pattern):
(dispatchService as any).startTimeoutChecker();
```

### Karma `coverageReporter` with `check.global`
**Source:** `src/angular/node_modules/karma-coverage/docs/configuration.md` (v2.2.1 installed).
**Apply to:** `karma.conf.js` patch in 100-03.

The `check` block only evaluates when `--code-coverage` is passed to `ng test`. The `text-summary` reporter type is required for headless output. Do NOT set `emitWarning: true` (would make the gate silently non-fatal).

---

## No Analog Found

All files in scope have either an exact analog (the same file being extended/patched) or a verified reference in the installed package documentation. No file requires falling back to RESEARCH.md patterns alone.

---

## Metadata

**Analog search scope:** `src/angular/src/app/tests/unittests/services/`, `src/angular/`, `src/docker/test/angular/`, `src/python/`, `.planning/`
**Files read:** 10 source/config files + CONTEXT.md + RESEARCH.md
**Pattern extraction date:** 2026-05-29
