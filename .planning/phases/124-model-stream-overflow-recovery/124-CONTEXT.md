# Phase 124: Model-Stream Overflow Recovery - Context

**Gathered:** 2026-10-26
**Status:** Ready for planning

<domain>
## Phase Boundary

When a browser tab's server-side model-stream queue overflows (a stalled or slow SSE consumer, so the bounded `StreamQueue` drops events), that tab's file list must converge back to the server's current model. Buffering stays bounded. Requirements: STRM-01 (reproduce first; if an existing recovery guarantee already exists, record it and close with no code change) and STRM-02 (convergence with bounded buffering; producer atomicity alone does not count). No event-bus redesign. Only the model (file-list) stream is in scope.

Pre-discussion code reading (still to be confirmed by the STRM-01 reproduction): no recovery guarantee exists today.
- `StreamQueue.put` (`src/python/web/utils.py`) drops the oldest event on overflow and only counts/logs it.
- `ModelStreamHandler` (`src/python/web/handler/stream_model.py`) sends `model-init` once at connect, and never again.
- The frontend (`src/angular/src/app/services/files/model-file.service.ts`) logs and ignores UPDATED/REMOVED events for unknown files, and rejects ADDED for files it already has. So a dropped ADDED leaves a file missing and a dropped REMOVED leaves a ghost, until the tab reconnects.
- A reconnect only happens after 30 s with no events (`stream-service.registry.ts`), which doesn't occur while updates keep flowing.
</domain>

<decisions>
## Implementation Decisions

### Reproduction first (STRM-01)
- **D-01:** Before proposing any fix, reproduce the overflow at the model-stream boundary with a recorded, repeatable automated test: a stalled consumer, more than `maxsize` model events produced, and dropped events. Record the observed outcome, i.e. whether the consumer's reconstructed model diverges from the server model. If it unexpectedly shows an existing recovery guarantee, record the evidence and close STRM-02 with no code change (roadmap criterion 2).

### Catch-up mechanism (STRM-02)
- **D-02:** Recovery is a **fresh snapshot on the same connection**. When the server detects that a tab's model queue dropped events, it discards that tab's stale backlog and re-sends a full `model-init` with the current model on the existing SSE connection. The frontend already replaces its whole list on `model-init`, so no frontend change is expected. Rejected alternative: closing the stream to force a reconnect, because the list visibly empties for about 3 s and the status/log streams reset.
- **D-03:** The resync must not introduce a miss/duplicate race. The "discard backlog and take snapshot" step must be atomic with respect to model updates, in the same way `Controller.get_model_files_and_add_listener` (`src/python/controller/controller.py:516`) holds the model lock. Events produced after the snapshot must be delivered, and events already reflected in it must not be re-applied.
- **D-04:** **At most one pending snapshot per tab.** Further drops before the pending snapshot is delivered fold into that same snapshot. Worst-case memory per stalled tab = one capped queue (1000 events) + one model snapshot. Copies never pile up. No time-based rate limit.
- **D-05:** Bounded buffering is a hard requirement and must be asserted by a test (queue never exceeds `maxsize`; at most one snapshot pending). Producer-side atomicity (the DEFER-STREAMQUEUE lock in `StreamQueue.put`) is not the recovery mechanism. Claude may include it as incidental hardening if the fix touches `put()`.

### Scope of streams
- **D-06:** **Model (file-list) stream only.** For the status stream, record evidence that it is self-healing (each event is a full status snapshot, so a later event replaces a dropped one). Don't change it. Dropped log-stream lines are out of scope (see Deferred).

### Proof of done
- **D-07:** **Automated tests only, with no NAS sandbox session** (the change is web-server-only and doesn't touch transfers, imports or deletes). Required tests: (a) the STRM-01 reproduction test from D-01; (b) a convergence test that fails before the fix and passes after: stalled consumer → overflow → drain → the consumer's reconstructed model equals the server's current model; (c) a bounded-buffering test per D-05. Python unit tests and CI must pass, including whole-tree `ruff check src/python/`.

### Visibility
- **D-08:** **Silent to the user, server log only.** No UI notice or toast. The server logs a warning when a tab is resynced, rate-limited like the existing `StreamQueue overflow` warning, so NAS log forensics can see it.

### Claude's Discretion
- Exact detection mechanics (drop flag / dropped-count delta on the listener, where the check lives in `ModelStreamHandler.get_value`).
- Whether the DEFER-STREAMQUEUE lock is folded in (D-05).
- Test placement and harness (extend `test_stream_queue.py` / `test_handler` vs. new file), and whether a frontend spec is added to confirm a repeated `model-init` replaces the list (it is expected to already work).
- Log message wording.

</decisions>

<specifics>
## Specific Ideas

- The typical real-world trigger is a backgrounded or throttled tab during a busy scan, when many model updates arrive at once.
- "Fails before, passes after" is mandatory for the convergence test (roadmap criterion 3), consistent with the test-first pattern from Phases 122/123.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/ROADMAP.md` §"Phase 124: Model-Stream Overflow Recovery" — goal and 4 success criteria
- `.planning/REQUIREMENTS.md` — STRM-01, STRM-02; Out of Scope row "Event-bus redesign"
- `.planning/codebase/CONCERNS.md` §"`StreamQueue.put` drop-oldest is not atomic under concurrent producers (DEFER-STREAMQUEUE)" and §"SSE stream is a busy-poll loop"

### Code
- `src/python/web/utils.py` — `StreamQueue` (bounded, drop-oldest, `get_dropped_count`)
- `src/python/web/handler/stream_model.py` — `WebResponseModelListener`, `ModelStreamHandler` (`setup`, `get_value`, `cleanup`)
- `src/python/web/web_app.py` — `__web_stream` loop (one value per handler per iteration, 10/100 ms sleeps, 15 s heartbeat)
- `src/python/controller/controller.py:516` — `get_model_files_and_add_listener` (atomic snapshot + listener pattern to reuse)
- `src/python/web/handler/stream_status.py` — status stream (evidence for D-06)
- `src/python/controller/memory_monitor.py` — StreamQueue stats reporting (size/dropped/maxsize)
- `src/angular/src/app/services/files/model-file.service.ts` — `model-init` replaces the whole map; add/update/remove handling of unknown files
- `src/angular/src/app/services/base/stream-service.registry.ts` — reconnect/idle-timeout behaviour

### Existing tests
- `src/python/tests/unittests/test_web/test_stream_queue.py`
- `src/python/tests/unittests/test_web/test_handler/`
- `src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SerializeModel.model(files)`: already produces the `model-init` payload; reuse it for the resync snapshot.
- `Controller.get_model_files_and_add_listener`: the atomic snapshot pattern under `__model_lock`. The resync needs an equivalent atomic "snapshot + reset listener backlog".
- `StreamQueue.get_dropped_count()`: an existing signal that drops occurred.

### Established Patterns
- One `ModelStreamHandler` + `WebResponseModelListener` per SSE connection, so per-tab state lives on the handler/listener.
- Drop warnings are rate-limited (`% 100 == 1`); follow the same style for the resync warning.
- Test-first RED→GREEN for reliability fixes (Phases 122/123).

### Integration Points
- `ModelStreamHandler.get_value()` is where a pending resync would be emitted, in place of the next incremental event.
- `web_app.__web_stream`: unchanged loop; the handler returns the snapshot string like the initial `model-init`.
</code_context>

<deferred>
## Deferred Ideas

- Log-stream (`stream_log.py`) dropped lines under overflow: lost log lines on the Logs page. A different mechanism (no "current state" to re-send). Backlog candidate if it is ever observed to matter.
- UI notice when the file list resyncs: rejected for now (D-08).
- SSE busy-poll → event-driven wakeups (CONCERNS.md): performance, not this phase.
</deferred>

---

*Phase: 124-model-stream-overflow-recovery*
*Context gathered: 2026-10-26*
