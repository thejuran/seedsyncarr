# Phase 100: Low-Priority Angular Coverage + CI Ratchet — Research

**Researched:** 2026-05-29
**Domain:** Angular fakeAsync testing (SSE race) + functional HTTP interceptor testing + karma-coverage threshold enforcement + CI wiring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Drive SSE test through the existing `fakeAsync` + `MockEventSource` harness in `stream-service.registry.spec.ts` (the `createMockEventSource` spy on `EventSourceFactory.createEventSource`, `tick()`, `discardPeriodicTasks()`). Construct the race by: (a) `onopen` to seed `_lastEventTime`; (b) `tick(CONNECTION_TIMEOUT_MS + jitter)` to push elapsed just past the 30s timeout; (c) fire a heartbeat `ping` listener in the same fakeAsync frame *before* advancing to the next `TIMEOUT_CHECK_INTERVAL_MS` boundary, so the next `checkConnectionTimeout` sees a fresh `_lastEventTime` and the elapsed check is false.

**D-02:** Three binding assertions: (a) no spurious reconnect — `EventSourceFactory.createEventSource` call count unchanged across the contested tick; (b) no double subscription — only one live `MockEventSource` (createEventSource count == 1 AND `notifyDisconnected` NOT called); (c) services not falsely disconnected — `connectedSeq` contains no spurious `false`. Contrast case (no heartbeat → timeout fires → reconnect) included as paired positive control.

**D-03:** Prove rotation through the `_resetAuthInterceptorCache()` seam. Sequence: `setupWithMeta("token-v1")` → fire request → assert `Bearer token-v1`; mutate meta tag → call `_resetAuthInterceptorCache()` → fire second request → assert `Bearer token-v2`. Reuse existing `setupWithMeta` helper and `afterEach` verbatim.

**D-04:** Document the implicit page-reload coupling as a code comment in the test only. No in-app rotation path added.

**D-05:** `karma.conf.js` has NO existing `check.global` block — must ADD it plus wire `--code-coverage` into the CI Dockerfile CMD so the gate actually bites.

**D-06:** Python ratchet target is `[tool.coverage.report] fail_under` in `src/python/pyproject.toml` (currently `84`). NOT a `[tool.pytest.ini_options]` addopts. Both ratchets land in one commit.

**D-07:** Set each threshold at `floor(measured-now) - ~0.5–1% jitter buffer`. Re-measure fresh against current HEAD. Floor decision logged in PROJECT.md Key Decisions.

**D-08:** Before/after in `.planning/ROADMAP.md` "Coverage Ratchet — Before / After" table + v1.3.0 entry in `.planning/RETROSPECTIVE.md`. "Before" = `v1.3.0-COVERAGE-BASELINE.md`. "After" = re-measured post-Phase-99 numbers.

**D-09 [informational]:** No fix anticipated — pure regression nets. Both tests expected to go green on first run.

### Claude's Discretion

- Exact `it()`/`describe` names, the concrete `tick()` values and jitter for 100-01, and whether the SSE contrast case is a separate `it()`.
- The exact Karma reporter list and the precise safety-margin within the ~0.5–1% band per layer.
- Whether 100-03 also bumps any `--cov-fail-under` in `[tool.pytest.ini_options]` addopts if discovered (defensive).
- Whether to re-measure Angular coverage locally or rely on CI run.

### Deferred Ideas (OUT OF SCOPE)

- In-app token-rotation path (production caller of `_resetAuthInterceptorCache`).
- `innerHTML → Renderer2` modal redesign.
- Coalescing SSE `UPDATED` events / timeout checker condition variable.
- Any bug fix > 10 net lines, public-API change, or observable-behavior change.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVLOW-03 | SSE timeout reconnection race has a regression test in `stream-service.registry.spec.ts` | SSE race mechanics fully mapped (§SSE Race Mechanics); exact `tick()` sequence specified |
| COVLOW-04 | `auth.interceptor.ts` token-missing / rotation path has a regression test | Interceptor test seam confirmed (§Auth Rotation Seam); `version-check.service.ts` coupling clarified |
| RATCHET-02 | pytest + Karma thresholds ratcheted up, before/after recorded in ROADMAP.md + RETROSPECTIVE.md | CI wiring gap identified (§CI Wiring — Critical Gap); karma-coverage `check.global` syntax verified; Python `fail_under` location confirmed |
</phase_requirements>

---

## Summary

Phase 100 adds two Angular regression tests and raises CI coverage thresholds. The research confirms all three plans are executable with no blocking unknowns, but surfaces one critical gap: the Angular CI job currently runs `ng test --browsers ChromeHeadless --watch=false` **without** `--code-coverage`, meaning a `check.global` block in `karma.conf.js` would be a silent no-op until the Dockerfile CMD is amended. Plan 100-03 must patch both files.

For 100-01, the `fakeAsync` + `MockEventSource` harness is fully capable of reproducing the heartbeat-vs-timeout race deterministically. The key insight is that the outer `beforeEach` discards the periodic tasks (the `setInterval`) after `onInit`, so the new test must restart the timeout checker via `(dispatchService as any).startTimeoutChecker()` before advancing time. All timing constants are `private readonly` fields — tests must hard-code the ms values (30000, 5000, 3000). The contrast case (no-heartbeat → reconnect fires) is straightforward to add as a second `it()` in the same nested describe.

For 100-02, the seam is clean: the existing `setupWithMeta` / `afterEach` helpers handle all the boilerplate. The one subtlety is that `setupWithMeta` already calls `_resetAuthInterceptorCache()` at setup time, so the new test's mid-test cache reset via the same function is just a second call — already proven safe by the teardown code in `afterEach`.

**Primary recommendation:** 100-01 uses a nested `describe` (or inline `startTimeoutChecker` call) to keep the `setInterval` live; 100-02 is a single `it()` mirror of the existing cache test; 100-03 patches `karma.conf.js` (multi-reporter array + `check.global`) AND the Angular test Dockerfile CMD (`--code-coverage` flag), then bumps `fail_under` in `pyproject.toml`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSE heartbeat / timeout race (COVLOW-03) | Frontend (Angular service) | — | `StreamDispatchService` is a pure Angular service; test lives entirely in the Angular unit layer |
| Auth token caching / rotation (COVLOW-04) | Frontend (Angular interceptor) | Backend (Bottle injects meta tag) | The cache lives in the Angular module; the token source is the server-rendered HTML |
| Coverage threshold enforcement (RATCHET-02) | CI layer | Local dev (karma-coverage in Docker) | Thresholds must fail the CI job, not just emit a warning |

---

## Standard Stack

No new packages are installed by this phase. All required tools are already present:

| Tool / Library | Version (installed) | Purpose |
|---------------|---------------------|---------|
| `karma-coverage` | 2.2.1 | Istanbul coverage collection + threshold enforcement |
| `@angular/build` (Karma builder) | Existing | `ng test --code-coverage` flag support |
| `pytest-cov` | ^7.1.0 | Python coverage; `fail_under` in `pyproject.toml` |
| `jasmine` / `fakeAsync` | Angular testing | Virtual time control for SSE race test |

[VERIFIED: node_modules/karma-coverage/package.json — v2.2.1 installed]
[VERIFIED: src/python/pyproject.toml — pytest-cov ^7.1.0, fail_under = 84 at line 88]

## Package Legitimacy Audit

No new packages are installed in this phase. The package legitimacy gate is not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
100-01 SSE race test
  fakeAsync test body
    → dispatchService.onInit()        (starts setInterval + SSE observer)
    → (dispatchService as any).startTimeoutChecker()  [if re-arming after beforeEach discards]
    → mockEventSource.onopen!(...)    (seeds _lastEventTime = Date.now())
    → tick(30001)                     (6 interval checks fire, none reconnect; elapsed ≤ 30000)
    → fire "ping" listener            (updates _lastEventTime to 30001ms, same fakeAsync frame)
    → tick(5000)                      (next check fires; elapsed = 4999ms < 30000ms → NO reconnect)
    → assert: createEventSource.calls.count() === 1
    → assert: connectedSeq has no false
    → discardPeriodicTasks()

  contrast case (positive control):
    → (reset service state)
    → mockEventSource.onopen!(...)    (seeds _lastEventTime)
    → tick(35001)                     (at T=35000ms: elapsed = 35000 > 30000 → reconnect fires)
    → assert: connectedSeq contains false
    → tick(3001)                      (reconnect timer: createSseObserver fires)
    → assert: createEventSource.calls.count() === 2
    → discardPeriodicTasks()

100-02 auth rotation test
  setupWithMeta("token-v1")           (creates meta tag + calls _resetAuthInterceptorCache)
    → httpClient.get("/api/first")    → assert "Bearer token-v1"
    → mutate meta tag to "token-v2"
    → _resetAuthInterceptorCache()    (seam: resets cachedToken=null, tokenRead=false)
    → httpClient.get("/api/second")   → assert "Bearer token-v2"

100-03 ratchet
  Re-measure Python:  make coverage-python  (host, same exclusion: no lftp suite)
  Re-measure Angular: docker run with --code-coverage flag (or local ng test --code-coverage)
  Edit: karma.conf.js → add multi-reporter array + check.global block
  Edit: src/docker/test/angular/Dockerfile → add --code-coverage to CMD
  Edit: src/python/pyproject.toml → bump fail_under to new floor
  Document: ROADMAP.md Before/After table, RETROSPECTIVE.md v1.3.0 entry, PROJECT.md Key Decisions
```

### Recommended Project Structure

Tests extend existing files — no new files are created:

```
src/angular/src/app/tests/unittests/services/base/
└── stream-service.registry.spec.ts   ← ADD nested describe + 2 it() blocks (COVLOW-03)

src/angular/src/app/tests/unittests/services/utils/
└── auth.interceptor.spec.ts           ← ADD 1 it() block (COVLOW-04)

src/angular/
└── karma.conf.js                      ← REPLACE coverageReporter block (RATCHET-02)

src/docker/test/angular/
└── Dockerfile                         ← ADD --code-coverage to CMD (RATCHET-02)

src/python/
└── pyproject.toml                     ← BUMP fail_under at line 88 (RATCHET-02)

.planning/
├── ROADMAP.md                         ← FILL TBD rows in Coverage Ratchet table (RATCHET-02)
├── RETROSPECTIVE.md                   ← ADD v1.3.0 retro entry (RATCHET-02)
└── PROJECT.md                         ← ADD floor-decision row to Key Decisions (RATCHET-02)
```

---

## SSE Race Mechanics (COVLOW-03) — Detailed Findings

[VERIFIED: src/angular/src/app/services/base/stream-service.registry.ts — read in session]
[VERIFIED: src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts — read in session]
[VERIFIED: src/angular/src/app/tests/mocks/mock-event-source.ts — read in session]

### Constants (all `private readonly` — not exported; tests must hard-code)

| Constant | Value | Location |
|----------|-------|----------|
| `CONNECTION_TIMEOUT_MS` | 30000 | `stream-service.registry.ts:66` |
| `TIMEOUT_CHECK_INTERVAL_MS` | 5000 | `stream-service.registry.ts:69` |
| `STREAM_RETRY_INTERVAL_MS` | 3000 | `stream-service.registry.ts:58` |
| `HEARTBEAT_EVENT` | `"ping"` | `stream-service.registry.ts:61` |

### The Race Guard Under Test

`checkConnectionTimeout()` (lines 124–137) re-reads `_lastEventTime` fresh on every interval invocation:

```typescript
const elapsed = Date.now() - this._lastEventTime;
if (elapsed > this.CONNECTION_TIMEOUT_MS) { this.reconnectDueToTimeout(); }
```

The heartbeat listener (lines 203–207) updates `_lastEventTime = Date.now()`. In fakeAsync, `Date.now()` advances with each `tick(ms)` call.

A heartbeat fired in the *same fakeAsync frame* (no `tick()` separating the listener call from the subsequent `tick()`) updates `_lastEventTime` to the current virtual time before the next interval check observes it. This is what the test must reproduce.

### The `beforeEach` / `discardPeriodicTasks` Problem

The **outer** `beforeEach` (lines 43–69 of the spec) calls:
1. `dispatchService.onInit()` → starts `setInterval(checkConnectionTimeout, 5000)` + `createSseObserver()`
2. `tick()` → flushes microtasks / zero-delay callbacks
3. `discardPeriodicTasks()` → **kills the setInterval**

After the outer `beforeEach` completes, NO periodic interval is running. The new heartbeat-race test must re-arm the interval. Two viable approaches:

**Approach A (recommended — inline re-arm):** Call `(dispatchService as any).startTimeoutChecker()` at the top of the new `it()` to restart the interval. This keeps the test inside the existing `describe` block without duplicating setup.

**Approach B (nested describe):** Add a `describe("heartbeat-vs-timeout race", ...)` block with its own `beforeEach` that does NOT call `discardPeriodicTasks()`. Requires duplicating the `createMockEventSource` spy setup and `TestBed.configureTestingModule` call — more boilerplate but isolates the timing-sensitive setup.

Approach A is simpler and consistent with the existing pattern of accessing private internals via `as any` (line 152 of spec already does this).

### Exact `tick()` Sequence for the Heartbeat-Saves Test

```
Initial state (after outer beforeEach):
  _lastEventTime = 0
  createEventSource call count = 1 (from onInit's createSseObserver)
  interval: DISCARDED

Test body:
  (dispatchService as any).startTimeoutChecker()  // restart interval
  mockEventSource.onopen!(new Event("connected"))  // seeds _lastEventTime = Date.now()
  tick()                                            // allow NgZone.run callbacks to flush

  // Advance 30001ms. The interval fires at T=5000, 10000, 15000, 20000, 25000, 30000.
  // At each firing: elapsed = check_time - 0 = check_time ≤ 30000ms. 
  // The guard is elapsed > 30000 (strict), so elapsed = 30000 is NOT > 30000. No reconnect.
  tick(30001)

  // NOW: virtual time = 30001ms. _lastEventTime = time-of-onopen ≈ 0ms.
  // Elapsed if checked NOW = ~30001ms > 30000ms — WOULD reconnect.
  // Fire the heartbeat in the same frame (no tick between).
  mockEventSource.listeners.get("ping")!(new Event("ping"))
  // _lastEventTime is now updated to ~30001ms.

  // Advance to next interval boundary (T=35000ms).
  tick(5000)
  // Interval fires at T=35000ms. elapsed = 35000 - 30001 = 4999ms < 30000ms. NO reconnect.

  // Assertions
  expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1) // no spurious reconnect
  expect(mockService1.connectedSeq).not.toContain(false)                 // no notifyDisconnected
  expect(mockService2.connectedSeq).not.toContain(false)

  discardPeriodicTasks()
```

**Note on `onopen` timing:** `onopen` is set at `stream-service.registry.ts:209`. When `onopen!()` is called directly in the test, it executes synchronously. The `_lastEventTime = Date.now()` assignment at line 212 uses fakeAsync virtual time, which is `0ms + any ticks so far`. The outer `beforeEach` does NOT call `onopen`, so `_lastEventTime` starts at `0` when the new test begins (after `startTimeoutChecker()` is called).

**Important:** After `tick()` following `onopen`, the `NgZone.run()` callbacks for `notifyConnected` flush. At this point `connectedSeq` for both services gains a `true`. The subsequent `not.toContain(false)` assertion checks the full sequence after the race ticks — correct because it asserts no `false` was ever pushed.

### Exact `tick()` Sequence for the Contrast Case (Positive Control)

The contrast case proves that WITHOUT the heartbeat, the timeout DOES fire and a reconnect occurs.

```
  // Start fresh (new describe block or after resetting state)
  (dispatchService as any).startTimeoutChecker()
  mockEventSource.onopen!(new Event("connected"))
  tick()

  // Advance 35001ms — passes the T=35000ms interval check:
  // At T=35000: elapsed = 35000 > 30000 → reconnectDueToTimeout() fires:
  //   - currentEventSource.close()
  //   - notifyDisconnected() on all services → connectedSeq gains false
  //   - schedules setTimeout(createSseObserver, 3000)
  tick(35001)

  expect(mockService1.connectedSeq).toContain(false)       // disconnect happened
  expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(1) // reconnect timer pending

  // Advance past STREAM_RETRY_INTERVAL_MS=3000ms:
  tick(3001)
  // createSseObserver fires → createEventSource called again
  expect(EventSourceFactory.createEventSource).toHaveBeenCalledTimes(2) // reconnect happened

  discardPeriodicTasks()
```

**Structure recommendation:** Make this a second `it()` inside the same nested describe block (or after the heartbeat-saves `it()`). A second `it()` gets a fresh `beforeEach` (outer) and a fresh `startTimeoutChecker()` call. The `EventSourceFactory.createEventSource` spy is reset by `beforeEach` each time.

### MockEventSource API Surface Used

From `mock-event-source.ts`:
- `mockEventSource.onopen`: `((ev: Event) => void) | null` — call directly: `mockEventSource.onopen!(new Event("connected"))`
- `mockEventSource.listeners`: `Map<string, EventListener>` — fire heartbeat: `mockEventSource.listeners.get("ping")!(new Event("ping"))`
- `mockEventSource.onerror`: `((ev: Event) => void) | null` — used in existing contrast tests
- `mockEventSource.close`: spy — confirm called on reconnect if needed (optional assertion)

The `ping` listener is registered at `stream-service.registry.ts:203` via `eventSource.addEventListener(this.HEARTBEAT_EVENT, ...)`, so `mockEventSource.listeners.has("ping")` is `true` after `onInit()` (confirmed by existing test at line 89: `expect(mockEventSource.listeners.has("ping")).toBe(true)`).

### `discardPeriodicTasks()` Placement

**Rules:**
1. Every `fakeAsync` test that starts a `setInterval` (via `startTimeoutChecker()`) MUST call `discardPeriodicTasks()` at the end of the test body, or Angular will throw "1 timer(s) still in the queue."
2. The outer `beforeEach` already calls `discardPeriodicTasks()` for the initial `onInit` interval. Tests that call `startTimeoutChecker()` inside their body must call it again at the end of their own body.
3. The `setTimeout` for `reconnectDueToTimeout` / reconnect is handled by the `tick(3001)` in the contrast case — ticking past it causes it to fire and it is consumed.

---

## Auth Rotation Seam (COVLOW-04) — Detailed Findings

[VERIFIED: src/angular/src/app/services/utils/auth.interceptor.ts — read in session]
[VERIFIED: src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts — read in session]

### The `setupWithMeta` Helper

`setupWithMeta(content)` (lines 11–38 of spec):
1. Removes any existing `meta[name="api-token"]` from DOM
2. Creates and appends a new `<meta name="api-token" content="${content}">` if `content !== null`
3. Calls `_resetAuthInterceptorCache()` — resets `cachedToken = null; tokenRead = false`
4. Runs `TestBed.configureTestingModule(...)` with the interceptor
5. Injects `HttpClient` and `HttpTestingController`

The `afterEach` (lines 40–48): calls `httpMock.verify()`, removes the meta tag, calls `_resetAuthInterceptorCache()`.

### New Test Structure (COVLOW-04)

```typescript
it("should serve new token after _resetAuthInterceptorCache is called (token rotation)", () => {
    // Production coupling note:
    // _resetAuthInterceptorCache has no production caller in this codebase.
    // Token rotation in production is realized by a full page reload: the Bottle server
    // re-serves index.html with a fresh <meta name="api-token"> on each GET /. The SPA
    // module is re-instantiated, resetting cachedToken and tokenRead to their initial values.
    // This test pins the mechanism that the page-reload path relies on.

    setupWithMeta("token-v1");

    // First request: should use token-v1
    httpClient.get("/api/first", {responseType: "text"}).subscribe();
    const req1 = httpMock.expectOne("/api/first");
    expect(req1.request.headers.get("Authorization")).toBe("Bearer token-v1");
    req1.flush("ok");

    // Simulate token rotation: server updates the meta tag and signals reload.
    // In production this would be a full page reload; here we use the @internal seam.
    const meta = document.querySelector("meta[name=\"api-token\"]");
    if (meta) { meta.setAttribute("content", "token-v2"); }
    _resetAuthInterceptorCache();

    // Second request: must carry the NEW token
    httpClient.get("/api/second", {responseType: "text"}).subscribe();
    const req2 = httpMock.expectOne("/api/second");
    expect(req2.request.headers.get("Authorization")).toBe("Bearer token-v2");
    req2.flush("ok");
});
```

This is the **mirror** of the existing `"should cache the token and not re-read meta tag on each request"` test (lines 94–114). That test proves: meta change WITHOUT reset → stale token. This test proves: meta change WITH reset → fresh token.

### The Version-Check Service — Coupling Clarification

[VERIFIED: src/angular/src/app/services/utils/version-check.service.ts — read in session]

**Important correction from CONCERNS.md text:** `version-check.service.ts` does NOT trigger a page reload. It checks GitHub for a newer release and shows a notification banner — no `window.location.reload()` call exists in the Angular source. The CONCERNS.md entry states "token rotation triggers a page reload via `version-check.service.ts` in practice" — this is an imprecise description of the coupling.

The **actual coupling** is:
- The Bottle server (`web_app.py:219–228`) injects `<meta name="api-token">` into every `GET /` response (the SPA shell)
- Token rotation in production means the user/admin changes the api_token in Settings and then manually navigates to (or reloads) the page
- On reload, the browser re-fetches `index.html`, the Angular module re-instantiates, `cachedToken` and `tokenRead` reset to `null`/`false`, and the next HTTP request reads the fresh meta tag

**D-04 code comment must name this accurate mechanism**, not reference `version-check.service.ts` as the trigger. The comment should say: "production has no in-app caller of `_resetAuthInterceptorCache`; token rotation is realized by a full page reload (user navigates to `/` or reloads), which re-instantiates the Angular module and resets the cache."

---

## CI Wiring — THE Critical Unknown (RATCHET-02) — Detailed Findings

[VERIFIED: .github/workflows/ci.yml — read in session]
[VERIFIED: src/docker/test/angular/Dockerfile — read in session]
[VERIFIED: src/angular/karma.conf.js — read in session]
[VERIFIED: src/angular/node_modules/karma-coverage/docs/configuration.md — read in session]

### Current State (Confirmed)

| Item | Current State |
|------|--------------|
| `karma.conf.js` `coverageReporter` | `{ type: 'html', dir: 'coverage/' }` — single reporter, no `check.global` |
| Dockerfile CMD | `["node", "...", "test", "--browsers", "ChromeHeadless", "--watch=false"]` — **no `--code-coverage`** |
| CI Angular job | `make run-tests-angular` → `docker-compose up` → Dockerfile CMD |
| `[tool.coverage.report] fail_under` | `84` at `src/python/pyproject.toml:88` |
| `[tool.pytest.ini_options]` addopts | No `--cov` or `--cov-fail-under` here (confirmed at lines 69–77) |

### Why the Gate Is Currently Silent

The `coverageReporter.check.global` block is only evaluated when coverage IS collected (i.e., when `ng test --code-coverage` is passed). Without `--code-coverage`, coverage instrumentation does not run, no coverage data is emitted, and no threshold check occurs. Adding `check.global` to `karma.conf.js` without also adding `--code-coverage` to the CI Dockerfile CMD would be a complete silent no-op.

### Required Changes (Both Are Mandatory for the Gate to Bite)

**Change 1: `src/angular/karma.conf.js`** — Replace the `coverageReporter` block with a multi-reporter array plus `check.global`:

```javascript
coverageReporter: {
    dir: 'coverage/',
    reporters: [
        { type: 'html', subdir: '.' },
        { type: 'text-summary' }
    ],
    check: {
        global: {
            statements: XX,   // floor(post-Phase-99 measured) - margin
            branches: XX,
            functions: XX,
            lines: XX
        }
    }
}
```

The `text-summary` reporter emits the 4-line coverage summary to stdout — visible in CI logs headlessly and required for the `check` block to actually run and fail the process if below threshold.

[VERIFIED: karma-coverage 2.2.1 docs (installed) — `reporters` array syntax + `check.global` block are documented features]

**Change 2: `src/docker/test/angular/Dockerfile`** — Add `--code-coverage` to the CMD:

```dockerfile
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false", \
     "--code-coverage"]
```

**Note on arm64 vs amd64:** The `unittests-angular` CI job runs ONLY on `ubuntu-latest` (amd64). The arm64 runner is used only for E2E tests. The Dockerfile already handles arm64 vs amd64 Chrome installation (Chromium for arm64, google-chrome-stable for amd64) — this is for the build environment, not for the unit test runner. No matrix changes are needed for RATCHET-02.

**Note on `[tool.pytest.ini_options]` addopts:** There is NO `--cov` or `--cov-fail-under` in the `addopts` at `pyproject.toml:69–77`. The Python coverage gate is solely `[tool.coverage.report] fail_under = 84`. D-06 is correct: bump only that one number. No defensive sync is needed.

### Re-Measurement Commands

**Python (CONTAINER-INCLUSIVE — THIS is the authoritative ratchet source):**
```bash
# The ratchet "before"/"now" MUST come from a CONTAINER-INCLUSIVE run that INCLUDES the
# real-lftp integration suite (the host has no `lftp` binary / `sshd`). Per the baseline
# mandate (v1.3.0-COVERAGE-BASELINE.md lines 85-91), the host-only number is PROVISIONAL —
# NOT the authoritative ratchet source. Run pytest with --cov INSIDE the test container
# (which has lftp + sshd) by overriding the CMD on a one-off run.
#
# The compose `tests` service mounts /src READ-ONLY (compose.yml:13) and WORKDIR is /src/.
# pytest-cov writes its `.coverage` data file to CWD by default, which would FAIL on the
# read-only mount — redirect it off the mount with `-e COVERAGE_FILE=/tmp/.coverage`
# (the -e flag goes BEFORE the service name in `docker compose run`). Use
# --cov-report=term-missing (stdout); do NOT use --cov-report=html (it would also write /src).
make tests-python && docker compose -f src/docker/test/python/compose.yml run --rm \
  -e COVERAGE_FILE=/tmp/.coverage tests \
  pytest --cov --cov-report=term-missing -p no:cacheprovider
# Capture the printed TOTAL line %. This container-inclusive number is the ratchet source
# and the honest "before" (expected >= the provisional host 85.19% since the real-lftp suite
# adds covered lines).
```

**Python (host — PROVISIONAL sanity reference ONLY, NOT the ratchet source):**
```bash
# The repo-root `make coverage-python` target is HOST-only / provisional: it EXCLUDES the
# real-lftp integration suite (no lftp binary / sshd on the host). It is acceptable as a
# cross-check only and MUST NOT be used to set the floor.
make coverage-python   # run FROM THE REPO ROOT — there is NO src/python/Makefile, so
                       # `cd src/python && make coverage-python` would FAIL (no Makefile).
# WARNING: do NOT treat this host number as "correct" / "matching" / authoritative — it is
# provisional and excludes the lftp suite. The container-inclusive run above is authoritative.
```

**Angular (headless, with coverage):**
```bash
# Option A: locally via Docker (matches CI exactly)
make run-tests-angular  # after patching Dockerfile CMD with --code-coverage
# Coverage summary printed to stdout by text-summary reporter

# Option B: locally without Docker
cd src/angular && ng test --code-coverage --watch=false --browsers=ChromeHeadlessCI
# Requires Chrome installed locally
```

The baseline document specifies: "Before" = `v1.3.0-COVERAGE-BASELINE.md` numbers (Python 85.19%; Angular Stmts 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%). "After" = post-Phase-99+100-01+100-02 measurement. Because Phase 99 added Python tests and Phases 100-01/02 add Angular tests, the "now" number is higher than the baseline for both languages.

### Python Ratchet Floor Calculation

Baseline floor: `84`. Measured baseline: `85.19%` (host/provisional, excludes lftp suite). After Phases 97–100 (all Python + Angular tests added), the Python coverage is expected to be at or above `85.19%`. The ratchet sets `fail_under` to `floor(now_measured) - margin`.

Example (if post-Phase-99 Python = 86%): `fail_under = floor(86) - 1 = 85`. This is a meaningful raise from 84 and includes the ~0.5–1% jitter buffer.

### Angular Ratchet Floor Calculation

Baseline numbers: Stmts 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%. After 100-01 and 100-02 add coverage of the SSE registry and auth interceptor rotation paths, all four metrics will rise slightly. Set each threshold to `floor(measured) - 1`.

Example: if post-100-02 Angular = Stmts 84.1% / Branches 70.2% / Functions 80.5% / Lines 85.0%:
```
statements: 83
branches:   69
functions:  79
lines:      84
```

---

## Common Pitfalls

### Pitfall 1: `check.global` Without `--code-coverage`

**What goes wrong:** Adding the `check` block to `karma.conf.js` but not adding `--code-coverage` to the Dockerfile CMD. CI continues to pass regardless of coverage.
**Why it happens:** The karma configuration is evaluated, but coverage instrumentation never runs, so no coverage data exists for the check to evaluate.
**How to avoid:** Modify BOTH files in the same commit (D-06 mandate: one commit for both ratchets).
**Warning signs:** CI passes after the commit but the `text-summary` reporter output is absent from CI logs.

### Pitfall 2: `setInterval` Already Discarded Before Heartbeat Race Test

**What goes wrong:** Test calls `tick(30001)` expecting interval callbacks to fire, but the outer `beforeEach` already called `discardPeriodicTasks()`, so no interval is running. `checkConnectionTimeout` is never called. The test passes trivially (no reconnect because no timeout check runs).
**Why it happens:** The outer `beforeEach` at line 68 calls `discardPeriodicTasks()` to clean up after `onInit`.
**How to avoid:** Call `(dispatchService as any).startTimeoutChecker()` at the start of the test to re-arm the interval. Verify by checking that the contrast case (no heartbeat) DOES see a reconnect — if the interval is dead, the contrast case also passes trivially with 0 reconnects, which is wrong.
**Warning signs:** Both the heartbeat-saves and no-heartbeat cases show `createEventSource.calls.count() === 1`.

### Pitfall 3: `_lastEventTime` Starts at 0 (Not at `Date.now()`)

**What goes wrong:** Test calls `tick(30001)` without calling `onopen` first. `_lastEventTime` stays `0`. `checkConnectionTimeout` hits the guard `if (this._lastEventTime === 0) { return; }` at line 125 and bails without reconnecting. No reconnect in the contrast case either.
**Why it happens:** The spec's outer `beforeEach` does NOT call `mockEventSource.onopen`. It only does `tick()` and `discardPeriodicTasks()`. The `onopen` call must be explicit in the new test.
**How to avoid:** Always call `mockEventSource.onopen!(new Event("connected")); tick();` before advancing time in the race tests.
**Warning signs:** Contrast case (no heartbeat) shows no reconnect despite `tick(35001)`.

### Pitfall 4: Auth Test — `setupWithMeta` Already Calls `_resetAuthInterceptorCache`

**What goes wrong:** Test writer adds an extra `_resetAuthInterceptorCache()` before the first request, disrupting the test invariant.
**Why it happens:** `setupWithMeta` already calls it (line 27 of spec). The test body's mid-test call (after mutating the meta tag) is the INTENTIONAL second reset — the one that proves rotation.
**How to avoid:** Only call `_resetAuthInterceptorCache()` once in the test body, after mutating the meta tag content, just before the second request.

### Pitfall 5: Karma `check` Block Uses `emitWarning: true` by Default

**What goes wrong:** Coverage is below threshold but CI still passes because `emitWarning` defaults to `false` in newer karma-coverage versions, but is documented as a possible override.
**Why it happens:** Old configurations sometimes set `emitWarning: true` to avoid CI failures.
**How to avoid:** Do NOT set `emitWarning: true` in the new `check.global` block. Omit it entirely (defaults to `false`) or explicitly set `emitWarning: false`.

### Pitfall 6: Stale `now` Number (Using Baseline Instead of Re-Measuring)

**What goes wrong:** Setting thresholds based on the Phase 97 baseline (85.19% Python, 83.34%/69.01%/79.73%/84.21% Angular) without re-measuring after Phases 97–100 tests land.
**Why it happens:** The baseline was captured before any v1.3.0 test work; it is the "Before" anchor, not the "now" number.
**How to avoid:** Run `make coverage-python` and the Angular coverage command after 100-01/02 are committed, THEN set the thresholds.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage threshold enforcement | Custom CI script checking coverage output | `karma-coverage` `check.global` block | Built-in, fails the karma process with non-zero exit code, works with `ng test` |
| Virtual time in SSE tests | Real `setTimeout` / `setInterval` | `fakeAsync` + `tick()` | Non-deterministic, flaky on slow CI; project mandate (spec + existing tests) |
| HTTP interceptor test | Real HTTP requests | `provideHttpClient(withInterceptors([...]))` + `HttpTestingController` | Angular's test harness; existing tests already use it |

---

## Code Examples

### karma.conf.js — New `coverageReporter` Block

```javascript
// Source: karma-coverage 2.2.1 docs (installed) + confirmed config syntax
coverageReporter: {
    dir: 'coverage/',
    reporters: [
        { type: 'html', subdir: '.' },
        { type: 'text-summary' }
    ],
    check: {
        global: {
            statements: 83,   // PLACEHOLDER — fill with floor(measured) - 1 after re-measure
            branches:   68,   // PLACEHOLDER
            functions:  79,   // PLACEHOLDER
            lines:      83    // PLACEHOLDER
        }
    }
}
```

[VERIFIED: karma-coverage 2.2.1 node_modules/karma-coverage/docs/configuration.md — `check.global` block with `statements`, `branches`, `functions`, `lines` keys]

### Dockerfile CMD Patch

```dockerfile
# Before
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false"]

# After
CMD ["node", "/app/node_modules/@angular/cli/bin/ng.js", "test", \
     "--browsers", "ChromeHeadless", \
     "--watch=false", \
     "--code-coverage"]
```

[VERIFIED: src/docker/test/angular/Dockerfile — read in session; CMD confirmed]

### pyproject.toml `fail_under` Bump

```toml
# Before (pyproject.toml line 88)
[tool.coverage.report]
fail_under = 84

# After
[tool.coverage.report]
fail_under = 85   # PLACEHOLDER — fill with floor(measured) - 1 after re-measure
```

[VERIFIED: src/python/pyproject.toml:87–88 — `[tool.coverage.report]` section confirmed]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `HttpClientTestingModule` (pre-v1.1.2) | `provideHttpClient(withInterceptors([...]))` + `provideHttpClientTesting()` | v1.1.2 migration | New test (100-02) uses the current pattern — existing spec already correct |
| Single `type: 'html'` in `coverageReporter` | Multi-reporter array with `check.global` | Phase 100 (this phase) | Enables CI-enforced coverage gate |
| `fail_under = 84` (floor set at v1.2.0) | Raised to new floor (Phase 100) | Phase 100 (this phase) | Monotonic ratchet; raises from 84 to ~85+ |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `ping` listener is always in `mockEventSource.listeners` after `onInit` | SSE Race Mechanics | If the listener isn't registered (e.g., `HEARTBEAT_EVENT` registration happens only under certain conditions), the heartbeat-fires step silently does nothing. Mitigation: the existing test at spec line 89 already asserts `listeners.has("ping") === true`. |
| A2 | `Date.now()` in fakeAsync advances exactly with `tick(ms)` increments | SSE Race Mechanics | If fakeAsync's `Date.now()` patching doesn't advance linearly, the `elapsed` calculation is wrong. Mitigation: this is standard Angular fakeAsync behavior — [ASSUMED] based on well-known framework behavior, not re-verified via docs in this session. |
| A3 | The post-Phase-99 Python coverage will be above 85% (making a `fail_under = 85` ratchet viable) | Ratchet Floor | If Phase 97–99 tests raised coverage by less than expected and "now" is < 85%, the floor calculation changes. Mitigation: D-07 is clear — set at `floor(now) - 1`, whatever `now` is; the exact number is not locked until re-measurement. |
| A4 | `version-check.service.ts` is NOT the production trigger of token rotation (correction to CONCERNS.md text) | Auth Rotation Seam | If there IS a reload path via `version-check.service.ts` that was overlooked, the D-04 comment would be incomplete. Mitigation: all Angular source files were searched for `window.location.reload()`, `location.reload()`, and similar — none found. The CONCERNS.md text appears to be imprecise. |

**If this table is empty:** Not applicable — 4 assumptions are logged above.

---

## Open Questions

1. **Post-Phase-99 "now" coverage numbers**
   - What we know: Baseline is Python 85.19% / Angular Stmts 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21%. Phases 97–100 add new tests.
   - What's unclear: Exact "now" numbers won't be known until after 100-01/02 are committed and a fresh measurement is run.
   - Recommendation: Plan 100-03 must run the measurement as its first task, before writing the threshold values.

2. **Whether `ng test --code-coverage` in the Dockerfile changes build time materially**
   - What we know: Istanbul instrumentation adds ~20–40% overhead to test runs. The CI Angular job has a `timeout-minutes: 15`.
   - What's unclear: Whether the added instrumentation time would approach the 15-minute limit.
   - Recommendation: The existing test suite has 599 tests; instrumentation overhead is unlikely to be a CI timeout concern. Low risk.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | 100-03 (Angular CI test) | ✓ | 29.4.3 | — |
| Node.js / npm | 100-03 (local Angular test option) | ✓ | 25.9.0 / 11.12.1 | Docker |
| Poetry / pytest | 100-03 (Python re-measure) | ✓ | 2.3.4 / 9.0.3 | — |
| Chrome (headless) | Angular unit tests | ✓ (via Docker) | Installed in test container | — |
| `ng` CLI | 100-01, 100-02 local run | ✗ (not in PATH) | — | Run via Docker (`make run-tests-angular`) |

**Missing dependencies with no fallback:** None — all required tooling is available via Docker.
**Missing dependencies with fallback:** `ng` CLI not in host PATH; all Angular test runs go through Docker.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Angular) | Karma + Jasmine (Angular CLI managed) |
| Config file | `src/angular/karma.conf.js` |
| Quick run command (Angular, Docker) | `make run-tests-angular` |
| Full suite command (Angular, with coverage) | `make run-tests-angular` after patching Dockerfile |
| Framework (Python) | pytest + pytest-cov |
| Config file (Python) | `src/python/pyproject.toml` |
| Quick run command (Python) | `cd src/python && poetry run pytest -x -q` |
| Coverage command (Python) | `make coverage-python` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COVLOW-03 | Heartbeat in same tick as timeout check → no spurious reconnect, no double subscription | unit (fakeAsync) | `make run-tests-angular` | Extends existing ✓ |
| COVLOW-03 (contrast) | No heartbeat → timeout fires → reconnect occurs | unit (fakeAsync) | `make run-tests-angular` | Extends existing ✓ |
| COVLOW-04 | Token rotation via `_resetAuthInterceptorCache()` → next request carries new token | unit | `make run-tests-angular` | Extends existing ✓ |
| RATCHET-02 | CI fails when Angular coverage drops below `check.global` thresholds | CI gate | `make run-tests-angular` (after patching Dockerfile + karma.conf.js) | ❌ Wave 0 for karma.conf.js + Dockerfile patch |
| RATCHET-02 | CI fails when Python line coverage drops below `fail_under` | CI gate | `make coverage-python` | ✓ (already enforced) |

### Sampling Rate

- **Per task commit:** `make run-tests-angular` (covers 100-01 and 100-02 Angular tests)
- **Per plan merge:** `make run-tests-angular` + `make coverage-python`
- **Phase gate:** Full suite green (Angular + Python) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/angular/karma.conf.js` — must ADD `check.global` block (RATCHET-02); existing file has no coverage check
- [ ] `src/docker/test/angular/Dockerfile` — must ADD `--code-coverage` to CMD (RATCHET-02)
- [ ] Re-measure coverage numbers — required before writing threshold values in Plan 100-03

*(Existing test files `stream-service.registry.spec.ts` and `auth.interceptor.spec.ts` exist and are extended in-place — no new spec files to create.)*

---

## Security Domain

The ASVS categories most relevant to this phase:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes (indirectly) | auth.interceptor.ts — Bearer token correctly rotated; test documents the rotation mechanism |
| V5 Input Validation | No | Tests are pure unit tests; no user input flows |
| V6 Cryptography | No | No crypto changes |
| V3 Session Management | No | Token is stateless Bearer; no session |

No new security-relevant behavior is added. The tests document existing behavior (D-04: code comment only).

---

## Sources

### Primary (HIGH confidence)

- `src/angular/src/app/services/base/stream-service.registry.ts` — constants, `checkConnectionTimeout`, `reconnectDueToTimeout`, `_lastEventTime` update locations — read in session
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — existing harness, `beforeEach` flow, `discardPeriodicTasks` pattern — read in session
- `src/angular/src/app/tests/mocks/mock-event-source.ts` — `MockEventSource` API surface — read in session
- `src/angular/src/app/services/utils/auth.interceptor.ts` — `getApiToken`, `authInterceptor`, `_resetAuthInterceptorCache` — read in session
- `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` — `setupWithMeta`, `afterEach`, cache test (lines 94–114) — read in session
- `src/angular/karma.conf.js` — current `coverageReporter` (no `check.global`), `ChromeHeadlessCI` custom launcher — read in session
- `src/docker/test/angular/Dockerfile` — CMD without `--code-coverage` confirmed — read in session
- `.github/workflows/ci.yml` — `unittests-angular` job invokes `make run-tests-angular`; no `--code-coverage` flag — read in session
- `src/python/pyproject.toml:87–88` — `[tool.coverage.report] fail_under = 84`; no `--cov-fail-under` in addopts — read in session
- `src/angular/node_modules/karma-coverage/docs/configuration.md` — `check.global` block syntax, `reporters` array syntax — read in session (v2.2.1 installed)
- `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` — baseline numbers, measurement methodology, Phase 100 follow-up requirements — read in session
- `src/angular/src/app/services/utils/version-check.service.ts` — confirms NO `window.location.reload()` call; the service only checks GitHub for newer versions — read in session

### Secondary (MEDIUM confidence)

- Bash grep on entire Angular source for `reload`/`location.reload` — no results — confirms no programmatic page reload anywhere in the SPA

### Tertiary (LOW confidence — see Assumptions Log)

- Angular `fakeAsync` / `Date.now()` patching behavior — [ASSUMED] standard behavior not re-verified against Angular docs in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed installed
- SSE race mechanics: HIGH — source + spec read; tick sequence derived from actual code logic
- Auth rotation seam: HIGH — interceptor source + spec read; `version-check.service.ts` coupling clarified
- CI wiring (THE critical finding): HIGH — Dockerfile, ci.yml, karma.conf.js all confirmed
- Ratchet floor calibration: MEDIUM — "now" numbers are ASSUMED pending re-measurement; methodology is HIGH confidence

**Research date:** 2026-05-29
**Valid until:** 2026-06-12 (stable framework / tooling; re-verify if karma-coverage or Angular CLI is upgraded before Phase 100 executes)
