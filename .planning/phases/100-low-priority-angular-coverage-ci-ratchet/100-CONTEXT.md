# Phase 100: Low-Priority Angular Coverage + CI Ratchet - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Two parts, three plans:

1. **One targeted regression test per Low-priority Angular gap** from CONCERNS.md (no full-path sweep — these are narrow safety nets over already-correct code, same tier shape as Phase 99):
   - **COVLOW-03 (100-01)** — SSE timeout reconnection race: a heartbeat arriving in the *same fakeAsync tick* as `checkConnectionTimeout` fires must NOT trigger a spurious reconnect and must NOT create a double subscription. (`stream-service.registry.ts:111-164`, specifically `checkConnectionTimeout` 124-137 and `reconnectDueToTimeout` 142-164.)
   - **COVLOW-04 (100-02)** — `auth.interceptor.ts` token rotation: meta tag set → request carries token → meta tag changes → `_resetAuthInterceptorCache()` called → next request carries the *new* token. Documents the implicit page-reload coupling. (`auth.interceptor.ts:7-17, 39-42`.)

2. **CI coverage ratchet (RATCHET-02, 100-03)** — bump pytest + Karma coverage thresholds upward in a single commit, comparing against the v1.3.0 baseline anchor, and record before/after numbers in ROADMAP.md + RETROSPECTIVE.md.

This is the **last phase of v1.3.0**. Out of scope: any non-trivial bug fix surfaced by these tests (→ v1.4.0, per the carried trivial-fix policy); the `innerHTML→Renderer2` redesign (v1.4.0); lowering any threshold.
</domain>

<decisions>
## Implementation Decisions

The design spec (`docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` §"Phase 100 — Low-Priority Angular Coverage + CI Ratchet" + the global "Cross-cutting concerns", "Tier policy", "Trivial-fix policy", "Phase shape" sections) functions as a locked SPEC: the files under test, the one-test-per-plan shape, the three plans (100-01 SSE, 100-02 auth, 100-03 ratchet), the trivial-fix window, the fakeAsync+tick SSE pattern, the `provideHttpClient()` interceptor pattern, and the baseline-anchored ratchet are already fixed there. The decisions below resolve the HOW gray areas the spec left open. **User delegated all four gray areas to Claude's recommendation** ("take your recs for all"), carrying the Phase 97/98/99 precedent forward verbatim.

### COVLOW-03 — SSE race assertion shape (100-01)
- **D-01:** Drive the test through the existing `fakeAsync` + `MockEventSource` harness in `stream-service.registry.spec.ts` (the `createMockEventSource` spy on `EventSourceFactory.createEventSource`, `tick()`, `discardPeriodicTasks()`). Construct the race by: (a) `onopen` to seed `_lastEventTime`; (b) `tick(CONNECTION_TIMEOUT_MS + jitter)` to push elapsed *just past* the 30s timeout; (c) fire a heartbeat `ping` listener (which sets `_lastEventTime = Date.now()`) in the same fakeAsync frame *before* advancing to the next `TIMEOUT_CHECK_INTERVAL_MS` (5s) boundary, so the next `checkConnectionTimeout` sees a fresh `_lastEventTime` and the elapsed check (`elapsed > CONNECTION_TIMEOUT_MS`) is false.
- **D-02:** The **binding assertions** (all three): (a) **no spurious reconnect** — `EventSourceFactory.createEventSource` call count is unchanged across the contested tick (one initial connect, no second connect from `reconnectDueToTimeout`'s `STREAM_RETRY_INTERVAL_MS` timer); (b) **no double subscription** — only one live `MockEventSource` / one `_currentSubscription`, i.e. the prior subscription wasn't torn down and re-created (assert via the createEventSource call count == 1 AND the registered-service `notifyDisconnected` was NOT called on the contested tick); (c) **services not falsely disconnected** — `mockService.connectedSeq` contains no spurious `false` entry from the heartbeat-saved tick. The contrast case (heartbeat does NOT arrive → timeout DOES fire → reconnect happens, createEventSource called a 2nd time after `STREAM_RETRY_INTERVAL_MS`) is included as the paired positive control so the test proves the race guard, not merely that nothing happens. Discretion: exact `tick()` values and whether the contrast case is a second `it()` or an assertion block within one `it()`.

### COVLOW-04 — Auth rotation test realism (100-02)
- **D-03:** Prove rotation through the **`_resetAuthInterceptorCache()` seam** (the documented `@internal` reset helper), NOT by simulating a real page reload. Sequence in one `it()`: `setupWithMeta("token-v1")` → fire request → assert `Bearer token-v1`; mutate the meta tag content to `"token-v2"` → call `_resetAuthInterceptorCache()` → fire a second request → assert `Bearer token-v2`. This is the exact seam the spec names ("`_resetAuthInterceptorCache` called, next request carries new token") and the existing spec's `should cache the token...` test (lines 94-114) already proves the *negative* (no reset → stale token), so 100-02 is its mirror positive. Reuse the existing `setupWithMeta` helper and `afterEach` cleanup verbatim.
- **D-04:** Document the **implicit page-reload coupling** as a code comment in the test (not as a behavior change): production has no in-app caller of `_resetAuthInterceptorCache`; token rotation is realized only by a full page reload (triggered in practice by `version-check.service.ts`), which re-instantiates the module and resets `tokenRead`. The test pins the *mechanism* that a reload relies on; it does NOT add an in-app rotation path (that would be a feature, → out of scope). No `version-check.service.ts` wiring is added or asserted — just the comment naming the coupling, matching the spec's "Documents the implicit page-reload coupling".

### RATCHET-02 — Karma threshold mechanics (100-03)
- **D-05:** `karma.conf.js` currently has **no** `coverageReporter.check.global` block and no coverage-gated CI invocation. The ratchet must **add** the `check.global` block (statements / branches / functions / lines) to `coverageReporter`, AND ensure the threshold is actually enforced in CI — verify during planning whether CI runs `ng test --code-coverage` (or `--no-watch --code-coverage --browsers=ChromeHeadlessCI`) and wire the coverage flag into the CI test invocation if it is not already enforcing. Adding numbers to a `check` block that CI never exercises with `--code-coverage` would be a silent no-op; the plan must confirm the gate actually bites. The `coverageReporter` also needs an `lcovonly`/`text-summary` reporter type alongside the existing `html` so the check runs headlessly. Exact reporter list is Claude's discretion; the requirement is that a sub-threshold run fails CI.
- **D-06:** Python ratchet target is **`[tool.coverage.report] fail_under`** in `src/python/pyproject.toml` (currently `84`), NOT a `[tool.pytest.ini_options]` `--cov-fail-under` (the spec's parenthetical guessed the latter; the repo uses the former — confirmed at `pyproject.toml:88`). Bump `fail_under` to the new floor. Both ratchets (Python `fail_under` + Karma `check.global`) land in **one commit** so a failed gate has a single obvious revert target (spec mandate).

### RATCHET-02 — Floor calibration strategy (100-03)
- **D-07:** Set each ratcheted threshold to **floor(measured "now" coverage) minus a small safety margin**, not exactly at the measured number. Concretely: take the post-Phase-99 measured coverage (re-measure at plan time against current HEAD, do NOT reuse a stale number), then set the threshold a hair below it — round down to a whole number and subtract a ~0.5–1% jitter buffer (Python is line-only; Angular sets all four of statements/branches/functions/lines independently). Rationale: the spec's own risk table flags "coverage ratchet bites unrelated PRs" and prescribes that a legitimate change dropping >0.1% from the new floor re-opens the floor decision. A threshold pinned *exactly* at measured coverage guarantees the very next PR with any trivial uncovered line fails — the margin makes the ratchet monotonic-upward (it still raises the bar substantially above the old 84) without being brittle. The floor decision (the chosen margin and resulting numbers) is logged in PROJECT.md Key Decisions per the spec's monotonic-ratchet rule. Discretion: exact margin within the ~0.5–1% band, per layer.
- **D-08:** Before/after numbers recorded in **both** `.planning/ROADMAP.md` (the v1.3.0 "Coverage Ratchet — Before / After" table, already stubbed with "TBD (Phase 100)") **and** the v1.3.0 entry in `.planning/RETROSPECTIVE.md`. "Before" = the v1.3.0 baseline anchor (`v1.3.0-COVERAGE-BASELINE.md`, captured Phase 97 against main HEAD); "After" = the re-measured post-Phase-99 number. The ratchet compares against the baseline anchor, not whatever is in CI config at that moment (spec mandate).

### Trivial-fix posture (carried from Phase 97/98/99)
- **D-09 [informational]:** Carry the posture forward verbatim: a clear, small fix (≤10 net non-blank/non-comment lines, no public-API change, no observable-behavior change) surfaced by a red test lands in-scope as a green commit *after* its red test; borderline cases default to deferring to v1.4.0 with a one-line STATE.md deferred-items entry referencing the documenting test. These are LOW-priority gaps over code that already behaves correctly (the SSE guard re-reads `_lastEventTime` per check; the interceptor reset helper already exists), so **no fix is anticipated** — pure regression nets. A test going green on first run is the expected outcome.

### Claude's Discretion
- Exact `it()`/`describe` names, the concrete `tick()` values and jitter for 100-01, and whether the SSE contrast case is a separate `it()`.
- The exact Karma reporter list and the precise safety-margin within the ~0.5–1% band per layer (D-07).
- Whether 100-03 also bumps the `[tool.pytest.ini_options]` addopts if a `--cov-fail-under` is discovered there too (defensive — keep both in sync if both exist).
- Whether to re-measure Angular coverage via `ng test --code-coverage --watch=false --browsers=ChromeHeadlessCI` locally or rely on the CI run; either is acceptable so long as the "now" number is fresh, not stale.
</decisions>

<specifics>
## Specific Ideas

- **100-01 is specifically the race, not the timeout.** The existing spec already covers reconnect-on-error (`should disconnect on error`, `should send events after reconnect`, lines 180-207). COVLOW-03 is the *subtle timing* case the existing tests miss: heartbeat and timeout-check landing in the same frame. The guard under test is that `checkConnectionTimeout` re-reads `_lastEventTime` (line 130) every check, so a heartbeat that updated it (line 204) wins the race. Without this test, a refactor that snapshotted `_lastEventTime` once per interval, or moved the `_lastEventTime = 0` reset earlier, would silently re-introduce spurious reconnects.
- **100-02 is the mirror of the existing cache test.** `should cache the token and not re-read meta tag on each request` (lines 94-114) proves stale-by-design without a reset. 100-02 proves fresh-after-reset — same setup, the one added step being `_resetAuthInterceptorCache()` between the two requests. The pair fully documents the cache lifecycle.
- **The Karma `check.global` block is NET-NEW.** This is the one place the spec's wording ("bump ... thresholds") undersells the work: there is nothing to bump yet — the block must be authored and CI must be confirmed to invoke coverage. Treat 100-03 as "establish the Angular gate + raise the Python floor," not "tweak two numbers."
- **Python `fail_under` is at `pyproject.toml:88` under `[tool.coverage.report]`**, currently `84`. Baseline measured ~85.19% (host/provisional, excludes the real-lftp integration suite — per the ROADMAP ratchet table note). The "now" re-measure must use the same exclusion conditions as the baseline so before/after are comparable.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (locked requirements)
- `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` §"Phase 100 — Low-Priority Angular Coverage + CI Ratchet" (plans 100-01/02/03) plus the global "Cross-cutting concerns" (coverage baseline, test isolation patterns, CI ratchet mechanics), "Tier policy", "Trivial-fix policy", "Phase shape", and "Success criteria" sections. MUST read before planning.
- `.planning/REQUIREMENTS.md` — COVLOW-03, COVLOW-04, RATCHET-02 acceptance statements + traceability table.
- `.planning/codebase/CONCERNS.md` §"Test Coverage Gaps" → "`auth.interceptor.ts` token-missing path" and "SSE timeout reconnection paths" (the original audit with file:line refs, risk notes, and the "exercised by e2e" / "page-reload coupling" annotations).

### Baseline anchor (the ratchet's "before")
- `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` — Python + Angular line/branch/function numbers captured in Phase 97 against main HEAD. The ratchet (D-08) compares against THIS, not live CI config.

### Source under test
- `src/angular/src/app/services/base/stream-service.registry.ts` — `StreamDispatchService`: `checkConnectionTimeout` (124-137), `reconnectDueToTimeout` (142-164), `_lastEventTime` updates in the heartbeat listener (203-207) and event listeners (193-194), `createSseObserver` subscription teardown (179-262). (COVLOW-03)
- `src/angular/src/app/services/utils/auth.interceptor.ts` — `getApiToken` cache (7-17), `authInterceptor` (24-33), `_resetAuthInterceptorCache` (39-42). (COVLOW-04)

### Ratchet targets
- `src/python/pyproject.toml` — `[tool.coverage.report] fail_under = 84` (line 88). Bump to new floor. (RATCHET-02)
- `src/angular/karma.conf.js` — `coverageReporter` block (23-26); ADD `check.global` here. (RATCHET-02)
- `.planning/ROADMAP.md` — v1.3.0 "Coverage Ratchet — Before / After" table (stubbed "TBD (Phase 100)"). Fill after/before. (RATCHET-02)
- `.planning/RETROSPECTIVE.md` — add v1.3.0 retro entry with before/after numbers, following the existing retro template. (RATCHET-02)
- `.planning/PROJECT.md` — Key Decisions table: log the floor/margin decision (D-07). (RATCHET-02)

### Existing test patterns to extend
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` — `fakeAsync` + `MockEventSource` harness, `discardPeriodicTasks()` idiom, existing reconnect tests (180-207). Extend with the heartbeat-vs-timeout race test. (COVLOW-03)
- `src/angular/src/app/tests/mocks/mock-event-source.ts` — `createMockEventSource` / `MockEventSource` (listeners map, `onopen`/`onerror`, `addEventListener` spy). Reuse. (COVLOW-03)
- `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` — `setupWithMeta` helper, `provideHttpClient(withInterceptors([...]))` + `provideHttpClientTesting()`, `afterEach` meta cleanup, the cache test (94-114) to mirror. Extend with the rotation test. (COVLOW-04)

**Path note:** the design spec writes Angular test paths loosely; the real layout is `src/angular/src/app/tests/unittests/services/...`. Use the real paths above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `stream-service.registry.spec.ts` already wires `StreamDispatchService` under `fakeAsync` with a `MockEventSource` spy, `MockStreamService` implementations tracking `connectedSeq`/`eventList`, and the `tick()` + `discardPeriodicTasks()` pattern needed to drive both the 5s `TIMEOUT_CHECK_INTERVAL_MS` and the 30s `CONNECTION_TIMEOUT_MS` deterministically. 100-01 extends this file directly.
- `auth.interceptor.spec.ts`'s `setupWithMeta(content)` builds/removes the `<meta name="api-token">` tag and calls `_resetAuthInterceptorCache()`; the `afterEach` verifies `httpMock` and cleans the tag. 100-02 reuses both verbatim and adds one rotation `it()`.
- `pyproject.toml` `[tool.coverage.report]` already enforces `fail_under` + `branch = true` — the ratchet bumps an existing, exercised gate (Python side is a number change). The Angular side is net-new (no `check.global` exists).

### Established Patterns
- SSE tests are `fakeAsync`-only with virtual time (`tick`) — NEVER real timers (spec's test-isolation mandate, and the existing spec follows it). Heartbeat/timeout are driven by `tick(ms)` against the known `CONNECTION_TIMEOUT_MS=30000` / `TIMEOUT_CHECK_INTERVAL_MS=5000` / `STREAM_RETRY_INTERVAL_MS=3000` constants.
- Interceptor tests use the functional-interceptor harness (`provideHttpClient(withInterceptors([authInterceptor]))` + `HttpTestingController`), post-v1.1.2 `provideHttpClient()` migration. Module-level cache state means `_resetAuthInterceptorCache()` in setup/teardown is mandatory for isolation.
- Coverage ratchet is monotonic-increase-only; any floor decision (and the chosen safety margin) is logged in PROJECT.md Key Decisions (spec + project convention).

### Integration Points
- COVLOW-03 is self-contained in `StreamDispatchService`; the assertion surface is the `EventSourceFactory.createEventSource` spy call count + `MockStreamService.connectedSeq`.
- COVLOW-04 is self-contained in the interceptor module + a DOM meta tag; the assertion surface is `HttpTestingController` request headers.
- RATCHET-02 (100-03) consumes the v1.3.0 baseline anchor and the post-Phase-99 "now" measurement; it closes the milestone (the ROADMAP table and RETROSPECTIVE entry are the milestone's coverage record). The two test plans (100-01/02) raise the "now" number that 100-03 ratchets against, so 100-03 must run after 100-01/02 land.
</code_context>

<deferred>
## Deferred Ideas

- Adding an **in-app token-rotation path** (a production caller of `_resetAuthInterceptorCache`, or moving auth to short-lived session cookies per CONCERNS.md's hardened-mode recommendation) — out of scope; a feature/redesign, not a regression test. → v1.4.0 (Known Bugs + Security) if ever prioritized.
- `innerHTML → Renderer2` modal redesign and mandatory-webhook-secret — already slated for v1.4.0 per the spec's "Future milestones" table; not this phase.
- Coalescing consecutive SSE `UPDATED` events / switching the timeout checker to a condition variable — performance improvements noted in CONCERNS.md, unrelated to the regression net. → backlog.
- Any bug surfaced by these tests exceeding the trivial-fix window (>10 net lines, public-API change, or observable-behavior change) → v1.4.0, with a one-line STATE.md deferred-items entry referencing the documenting test (per D-09). None anticipated.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — Python/upstream; unrelated to this Angular + CI phase.
- `2026-04-24-migrate-config-set-to-post-body` — API contract change, separate milestone; unrelated.
</deferred>

---

*Phase: 100-low-priority-angular-coverage-ci-ratchet*
*Context gathered: 2026-05-29*
