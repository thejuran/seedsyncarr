# Phase 124: Model-Stream Overflow Recovery - Research

**Researched:** 2026-10-26
**Domain:** Server-sent events (SSE) backpressure recovery, Python threading/locking, bounded in-memory queues
**Confidence:** HIGH

## Summary

This phase is a small, self-contained fix inside code that already exists and is already read
end-to-end in CONTEXT.md. There is no new library to evaluate and no new architecture to design —
the research question is entirely "how do the existing pieces fit together, and what is the
smallest correct way to wire a fourth piece (resync) into them." All claims below are grounded in
direct reads of the five files CONTEXT.md names as canonical, plus the project's own test
harnesses, which already contain the exact test patterns this phase needs (mocked-`Controller`
unit tests, a real-`Controller`-with-real-lock integration base class, and a raw-WSGI-generator
SSE harness).

The threading model is confirmed: `WebAppJob.setup()` runs Bottle under Paste's
`httpserver.serve(..., start_loop=False)` + `serve_forever()`, which dispatches each HTTP
connection to its own worker thread and writes each `yield`ed SSE chunk directly to that
connection's socket (`MyWSGIHandler.wsgi_write_chunk`). A stalled/throttled browser tab causes
TCP backpressure, which blocks that chunk's `socket.send()`, which blocks the generator at its
`yield` statement inside `WebApp.__web_stream`, which blocks further calls to
`ModelStreamHandler.get_value()` for that connection only. The Controller's own thread (separate,
unaffected) keeps mutating the model and calling `listener.file_added/removed/updated` →
`StreamQueue.put()` for every registered listener, so the stalled tab's queue — and only that
tab's queue — fills to `maxsize` (1000) and starts dropping. This is consistent with
CONCERNS.md's own description of `__web_stream` as "per connection," and confirms the premise in
CONTEXT.md's `<domain>` section is accurate: no recovery mechanism exists today for the model
stream, unlike the status stream (see D-06 evidence below).

The fix needs exactly three code changes: (1) a `clear()` method on `StreamQueue` to discard a
listener's backlog without touching `dropped_count`; (2) one new `Controller` method that runs an
arbitrary no-arg callback *and* takes the current model snapshot inside the same `__model_lock`
critical section — **not** a method typed to know about `StreamQueue`, to avoid a layering
violation (`controller` must not import from `web`); (3) a small state machine in
`ModelStreamHandler.get_value()` that detects a drop via `get_dropped_count()` delta, coalesces
repeated drops into one pending resync (D-04), and emits a fresh `model-init` in place of the next
stale incremental event. The frontend needs no change — `ModelFileService.parseEvent`'s
`model-init` branch unconditionally replaces the whole `Immutable.Map`, confirmed by direct read.

**Primary recommendation:** Add `StreamQueue.clear()` + one generic `Controller.resync_model_files(discard_backlog: Callable[[], None]) -> List[ModelFile]` method that wraps `discard_backlog(); return self.__get_model_files()` inside the existing `__model_lock`, then call it from `ModelStreamHandler.get_value()` passing `self.model_listener.clear` as the callback. Do not re-call `get_model_files_and_add_listener` for the resync — it would re-add the listener (harmlessly idempotent, but confusing) and does not discard the backlog, so the atomicity contract would not actually hold.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSE connection / HTTP streaming loop | API / Backend (`WebApp.__web_stream`, Paste httpserver) | — | Owns the generator, the socket write, and therefore the backpressure that causes the stall |
| Model mutation + locking | API / Backend (`Controller`, `Model`) | — | `__model_lock` is the single source of truth for "is the model consistent right now"; only Controller can grant atomic access to it |
| Overflow detection + bounded buffering | API / Backend (`StreamQueue`, `WebResponseModelListener`) | — | Per-connection, per-tab state; already bounded at 1000 events, already counts drops |
| Atomic discard-backlog + snapshot (resync) | API / Backend, split across `Controller` (lock owner) and `web.handler.stream_model` (listener/queue owner) | — | Neither side can do it alone: the web layer has no access to `__model_lock`, and `Controller` must not import `StreamQueue` — hence a callback-based bridge, not a new cross-layer type |
| Client-side model reconciliation on `model-init` | Browser / Client (`ModelFileService`) | — | Already correct (full-map replace); D-02 relies on this being unchanged |
| Idle-timeout reconnect fallback | Browser / Client (`StreamDispatchService`, 30s) | — | Existing safety net, not the primary recovery mechanism per D-02 (rejected: visible 3s empty list + resets status/log streams) |

## Project Constraints

No project-level `./CLAUDE.md` exists in this repository (only the user's global
`~/.claude/CLAUDE.md`, which is process/security guidance, not codebase-specific). No
`.claude/skills/` or `.agents/skills/` directory contains project-specific rules for this phase.
The relevant project conventions instead live in the codebase itself and in prior phases'
established test patterns, both captured below.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRM-01 | Overflow is reproduced at the model-stream boundary; if an existing recovery guarantee is found, record it and close with no code change | Confirmed via code read: no recovery guarantee exists for the model stream today (unlike the status stream — see D-06 evidence, "Code Examples" and "Common Pitfalls"). The threading-model analysis above (Paste httpserver blocking-write backpressure) explains *why* `StreamQueue` actually fills under a stalled consumer, and "Validation Architecture" gives the exact reproduction test shape (put > maxsize without draining, assert divergence) |
| STRM-02 | After overflow, the slow client converges to the server's current state with bounded buffering; producer atomicity alone does not count | "Code Examples" gives the concrete `StreamQueue.clear()` + `Controller.resync_model_files()` + `ModelStreamHandler.get_value()` design that satisfies D-02/D-03/D-04/D-05; "Don't Hand-Roll" explains why a new cross-layer type would be wrong; "Common Pitfalls" covers the race conditions a naive implementation would hit |

</phase_requirements>

## Standard Stack

**No new dependencies.** This phase only touches code already in the repository, using only the
Python standard library primitives already in use (`queue.Queue`, `threading.Lock`,
`typing.Callable`). No `npm install` / `pip install` / `poetry add` is needed, so the Package
Legitimacy Audit section is not applicable and is omitted.

| Component | Already present | Role in this phase |
|-----------|-----------------|---------------------|
| `src/python/web/utils.py` → `StreamQueue` | Yes [VERIFIED: codebase, `src/python/web/utils.py:10-96`] | Add `clear()`; already has `get_dropped_count()`, `get_queue_size()`, `get_maxsize()` |
| `src/python/web/handler/stream_model.py` → `WebResponseModelListener`, `ModelStreamHandler` | Yes [VERIFIED: codebase, `src/python/web/handler/stream_model.py:1-74`] | `WebResponseModelListener` inherits `StreamQueue`, so it gets `clear()` for free; `ModelStreamHandler.get_value()` is where detection + resync logic goes |
| `src/python/controller/controller.py` → `Controller` | Yes [VERIFIED: codebase, `src/python/controller/controller.py:192,448,506-531`] | Add one new method next to `get_model_files_and_add_listener` (line 516), reusing `self.__model_lock` and the existing private `__get_model_files()` helper |
| `src/python/web/serialize/serialize_model.py` → `SerializeModel` | Yes [VERIFIED: codebase] | `SerializeModel.model(files)` already produces the exact `model-init` SSE payload; reuse unchanged for the resync snapshot |
| `src/angular/.../model-file.service.ts` | Yes, unchanged | `model-init` already does a full-map replace unconditionally (see Code Examples) |

## Architecture Patterns

### System Architecture Diagram

```
Controller thread (owns __model_lock)                 Web-server thread (one per SSE connection)
──────────────────────────────────────                ───────────────────────────────────────────
scan/lftp/webhook results
        │
        ▼
Model.add_file/remove_file/update_file   (holds __model_lock while notifying)
        │
        ▼
listener.file_added/removed/updated  ──────put()────▶  StreamQueue (bounded, maxsize=1000)
 (one WebResponseModelListener per tab)                        │
        │                                                      │  blocked here if the
        │ (queue full ⇒ drop oldest,                            │  tab's socket write
        │  dropped_count += 1,                                 │  is backpressured
        │  logged every 100th drop)                             ▼
        │                                              ModelStreamHandler.get_value()
        │                                                      │
        │                                   ┌──────────────────┴──────────────────┐
        │                                   │ dropped_count changed since last     │
        │                                   │ check?  → resync_pending = True      │
        │                                   └──────────────────┬──────────────────┘
        │                                                      │ yes
        │                                                      ▼
        │                                   Controller.resync_model_files(listener.clear)
        │                                   ── acquire __model_lock ──
        └──────────────────────────────────▶│  listener.clear()  (discard stale backlog) │
                                             │  files = __get_model_files() (fresh snapshot)│
                                             ── release __model_lock ──
                                                                      │
                                                                      ▼
                                             SerializeModel.model(files) → "model-init" SSE event
                                                                      │
                                                                      ▼
                                             yield (socket write) ──▶ EventSource ──▶
                                             ModelFileService.parseEvent("model-init", …)
                                             → Immutable.Map fully replaced (no frontend change)
```

### Recommended change footprint
```
src/python/web/utils.py                              # + StreamQueue.clear()
src/python/controller/controller.py                  # + resync_model_files(discard_backlog)
src/python/web/handler/stream_model.py               # ModelStreamHandler.get_value(): detect + resync
src/python/tests/unittests/test_web/test_stream_queue.py            # STRM-01 repro + clear() tests
src/python/tests/unittests/test_controller/test_controller.py       # D-03 atomicity test (real lock, real thread)
src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py  # coalescing, warning, bounded-buffering
src/python/tests/integration/test_web/test_handler/test_stream_model.py        # fails-before/passes-after E2E-in-process
```

### Pattern: generic lock-bridge method instead of a cross-layer type
**What:** `Controller.resync_model_files` takes a `Callable[[], None]`, not a `StreamQueue` or
`WebResponseModelListener`. It knows nothing about the web layer's types.
**When to use:** Any time code outside `controller/` needs an operation to be atomic with respect
to a model mutation, but the operation itself (discarding a queue) is a concern that belongs to
the caller's layer, not to `Controller`.
**Example:**
```python
# controller/controller.py — new method, next to get_model_files_and_add_listener (line 516)
def resync_model_files(self, discard_backlog: Callable[[], None]) -> List[ModelFile]:
    """
    Atomically discards a listener's queued backlog and returns a fresh snapshot
    of the current model files (D-03). `discard_backlog` runs while __model_lock
    is held, so no model mutation — and therefore no new listener event — can
    happen between the discard and the snapshot. The caller is responsible for
    having already registered its listener (this does not call add_listener).
    """
    with self.__model_lock:
        discard_backlog()
        return self.__get_model_files()
```
```python
# web/utils.py — StreamQueue.clear()
def clear(self) -> None:
    """
    Discard all currently queued events without affecting dropped_count.
    Safe to call concurrently with get_next_event() only if the caller is
    the sole consumer (true here: resync runs on the same thread that would
    otherwise call get_next_event()).
    """
    while True:
        try:
            self.__queue.get(block=False)
        except Empty:
            return
```
```python
# web/handler/stream_model.py — ModelStreamHandler.get_value()
def get_value(self) -> Optional[str]:
    if self.initial_model_files is not None:
        files = self.initial_model_files
        self.initial_model_files = None
        return self.serialize.model(files)

    dropped_now = self.model_listener.get_dropped_count()
    if dropped_now != self._last_seen_dropped:
        self._resync_pending = True

    if self._resync_pending:
        self._resync_pending = False
        files = self.controller.resync_model_files(self.model_listener.clear)
        # Re-read AFTER the snapshot so any drop that raced with the resync
        # itself (between the read above and the lock acquisition inside
        # resync_model_files) is absorbed into THIS snapshot instead of
        # triggering an immediate second resync (D-04: at most one pending).
        self._last_seen_dropped = self.model_listener.get_dropped_count()
        self._resync_count += 1
        if self._resync_count % 100 == 1:
            self.logger.warning(
                "Model stream resynced after overflow (dropped_total={})".format(dropped_now)
            )
        return self.serialize.model(files)

    event = self.model_listener.get_next_event()
    if event is not None:
        return self.serialize.update_event(event)
    return None
```
This is a proposed implementation sketch synthesized from the verified code above, not a quote
from an existing file — label it as such when planning, and expect the exact field names
(`_last_seen_dropped`, `_resync_pending`, `_resync_count`, `self.logger`) to be set up in
`ModelStreamHandler.__init__`.

### Anti-Patterns to Avoid
- **Discarding the backlog outside `__model_lock`:** if `listener.clear()` runs before (or
  without) acquiring the lock, a mutation that lands in the gap between the clear and the
  snapshot is not reflected in the snapshot and its event was already discarded — a genuine miss.
  D-03 is only satisfied if the discard and the snapshot happen inside the *same* lock acquisition.
- **Giving `Controller` a method typed to accept `StreamQueue`/`WebResponseModelListener`:**
  `controller/` currently has zero imports from `web/` (only `web/` imports from `controller/`).
  A method like `def resync(self, listener: WebResponseModelListener)` inverts that dependency.
  The `Callable[[], None]` bridge avoids this entirely.
- **Time-based rate limiting of the resync itself:** D-05 explicitly rejects this; coalescing is a
  state flag (`_resync_pending`), not a cooldown timer.
- **Re-adding the listener via `get_model_files_and_add_listener` for the resync:** `Model.add_listener`
  is idempotent (`if listener not in self.__listeners: ...`, `src/python/model/model.py:62-64`), so
  calling it again is technically safe, but it does not discard the backlog and its name implies a
  fresh registration, which this is not. A dedicated method is clearer and is the only one that
  actually combines "discard" and "snapshot."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic "snapshot of current state + mutate per-caller state" under a shared lock | A second lock scoped to the web layer, or `queue.queue` internal-deque reaching-in | `Controller.resync_model_files(discard_backlog)` reusing the existing `__model_lock` | A second lock can't prevent races with the *first* lock the producer actually holds; reaching into `Queue`'s private deque is fragile across Python versions and unnecessary — `get(block=False)` in a loop is already safe and documented |
| "At most one pending unit of work" coalescing | A debounce timer / cooldown window | A single `bool` flag re-armed by comparing `get_dropped_count()` deltas | D-04 explicitly wants no time-based rate limit; a boolean flag is simpler, has zero extra memory, and is exactly "fold into the same snapshot" |
| Reconstructing "what the client would have seen" for a test | A parallel implementation of the Angular reducer logic in Python from scratch | Parse the exact JSON strings `SerializeModel.model()`/`update_event()` already produce, and apply the same three rules `ModelFileService.parseEvent` uses (`model-init` replaces; `model-added` no-ops if key exists; `model-removed`/`model-updated` no-op if key is absent) in ~15 lines of test helper code | Keeps the test honest about the actual wire format instead of asserting against Python `ModelFile` objects that never cross the wire |

**Key insight:** every piece this phase needs (bounded queue, drop counter, atomic lock-protected
snapshot, full-replace client reducer) already exists in the codebase in a form one step short of
what D-02/D-03/D-04 ask for. The job is wiring, not invention.

## Common Pitfalls

### Pitfall 1: Checking the resync condition after pulling the next event, not before
**What goes wrong:** If `get_value()` calls `self.model_listener.get_next_event()` before checking
for a pending resync, the first `get_value()` call after a detected drop still returns one stale
backlog event (built from pre-overflow state) instead of the fresh snapshot, and the stale event
reaches the frontend as (e.g.) a `model-removed` for a file the fresh snapshot will shortly also
omit — harmless here specifically because `ModelFileService` no-ops unknown removals, but it is
fragile and defeats the "no event-bus redesign, smallest mechanism" intent.
**Why it happens:** the natural place to add the check is wherever feels convenient; the existing
method already has an early-return for `initial_model_files`, inviting a second early-return
appended at the end instead of right after the first one.
**How to avoid:** the resync check must be the second gate in `get_value()`, strictly before the
`get_next_event()` call (see Code Examples).
**Warning signs:** a test that asserts "no stale added/removed/updated events are observed between
a drop and its model-init" fails if the ordering is wrong.

### Pitfall 2: Treating `get_model_files_and_add_listener` as the resync primitive
**What goes wrong:** it is tempting to just call the existing method again from
`ModelStreamHandler` since it already does "lock + snapshot." But it does not discard the
listener's backlog, so stale events already in the queue are delivered *after* the fresh
model-init, producing exactly the duplicate/ghost behavior D-03 forbids (mitigated only by the
frontend's dedup logic, which is not a substitute for a real fix per D-05's "producer atomicity
alone is not accepted").
**How to avoid:** use the new `resync_model_files(discard_backlog)` method instead; it is a
superset (discard + snapshot) of what the existing method does (add + snapshot).

### Pitfall 3: Simulating "a stalled consumer" by never calling the WSGI generator at all
**What goes wrong:** the existing integration helper `collect_sse_chunks()`
(`src/python/tests/helpers/wsgi_stream.py:29-50`) calls `list(web_app(environ, start_response))`,
which drains the generator continuously until `web_app.stop()` fires. It cannot express "produce
N events, then stall N iterations, then resume" — using it unmodified for the overflow
reproduction test will never actually overflow the queue, because nothing is produced fast enough
relative to the 10ms/100ms poll loop to outrun a continuously-draining consumer.
**Why it happens:** it is the only existing SSE-generator test helper, so it is the natural
starting point to copy.
**How to avoid:** either (a) reproduce at the `WebResponseModelListener`/`StreamQueue` level
directly — call `.file_added()` (or `.put()`) more than `maxsize` times without ever calling
`get_next_event()`, which is exactly what "stalled consumer" means from the producer's point of
view and needs no WSGI machinery at all — or (b) add a small new integration helper that gets the
raw generator object (`gen = web_app(environ, start_response)`) and manually calls `next(gen)` a
controlled number of times, pausing between calls while a background `Timer` thread floods
`model_listener.file_added(...)`. Option (a) is simpler, deterministic, and sufficient for D-01's
"recorded, repeatable" requirement; option (b) is closer to the literal production mechanism and
is worth adding if the team wants the roadmap's "fails before, passes after" test to exercise the
full SSE/HTTP path. Both are legitimate; this is explicitly Claude's Discretion per CONTEXT.md.

### Pitfall 4: Coalescing logic that re-triggers immediately after its own resync
**What goes wrong:** if `_last_seen_dropped` is captured *before* calling
`resync_model_files` (at the moment the drop was first noticed) rather than *after* (once the
snapshot is actually taken), any further drop that races in during the brief window between the
two reads looks like "a new drop since last check" on the very next `get_value()` call, firing a
second resync immediately — not wrong, but it means more than one snapshot can be sent for what is
really a single stall event, weakening the "at most one pending snapshot" intent of D-04 (even
though peak memory never exceeds the bound, since the extra snapshot is sent immediately, not
buffered).
**How to avoid:** re-read `get_dropped_count()` once more immediately after
`resync_model_files()` returns and use that value as the new baseline (see Code Examples).

### Pitfall 5: Log line includes a value that needs sanitizing
**What goes wrong:** the codebase has an established CWE-117 log-injection discipline
(`sanitize_log_value`, exercised in `TestAutoDeleteLogSanitization`,
`src/python/tests/unittests/test_controller/test_controller_unit.py` area and
`controller.py:820/841/229`) for any log line that embeds a file name. The new resync warning (D-08)
currently only needs a count, which is safe as-is — but if a future edit adds a file/path name to
that log line, it must go through `sanitize_log_value` like every other such site in this
codebase.
**How to avoid:** keep the warning to counts only, or sanitize if a name is ever added.

### Pitfall 6: Coverage gate (`fail_under = 88`) on the new branches
**What goes wrong:** the new `if self._resync_pending:` branch, the `% 100 == 1` rate-limit
branch, and `StreamQueue.clear()`'s loop-until-`Empty` all need direct test coverage or the
whole-tree coverage gate can regress below 88% (branch coverage is enabled:
`[tool.coverage.run] branch = true`, `src/python/pyproject.toml:83-95`).
**How to avoid:** the required tests in "Validation Architecture" below already cover every new
branch; don't skip the "coalescing" and "rate-limited warning" cases specifically.

## Code Examples

See "Architecture Patterns" above for the three proposed implementation sketches
(`StreamQueue.clear()`, `Controller.resync_model_files()`, `ModelStreamHandler.get_value()`).

### Existing atomic-snapshot pattern to mirror (verified)
```python
# src/python/controller/controller.py:516-531 — the pattern this phase extends
def get_model_files_and_add_listener(self, listener: IModelListener):
    """
    Adds a listener and returns the current state of model files in one atomic operation
    This guarantees that model update events are not missed or duplicated for the clients
    """
    with self.__model_lock:
        self.__model.add_listener(listener)
        model_files = self.__get_model_files()
    return model_files
```

### Existing test pattern for real-lock concurrency (verified, reuse directly for D-03)
```python
# src/python/tests/unittests/test_controller/test_controller_unit.py (TestRootLifecycleResetCallback)
def test_callback_does_not_take_model_lock(self):
    """Both pipeline call sites hold the model lock; re-taking it would deadlock."""
    lock = self.controller._Controller__model_lock
    with lock:
        worker = threading.Thread(
            target=self.controller._on_root_lifecycle_reset, args=("X", "under lock"), daemon=True
        )
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive(), "callback blocked on the model lock")
```
Adapt this exact shape for D-03: hold `__model_lock` externally in the test, start a thread calling
`controller.resync_model_files(some_listener.clear)`, assert it blocks until the lock is released,
then assert the files it returns reflect every mutation made before the lock was released and none
made after.

### Existing mocked-Controller unit test harness (verified, use for `ModelStreamHandler` tests)
```python
# src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py
class TestModelStreamHandler(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock(spec=Controller)
        self.handler = ModelStreamHandler(self.mock_controller)
```
`MagicMock(spec=Controller)` will need `self.mock_controller.resync_model_files.return_value = [...]`
stubbed once the new method exists; `spec=Controller` means the mock will raise
`AttributeError` if the method name doesn't match the real signature — a useful guard against typos.

### Existing raw-WSGI-generator harness (verified, base for the integration test)
```python
# src/python/tests/helpers/wsgi_stream.py:29-50
def collect_sse_chunks(web_app, path: str = "/server/stream", stop_after_s: float = 0.5):
    environ = make_wsgi_environ(path=path)
    Timer(stop_after_s, web_app.stop).start()
    ...
    chunks = list(web_app(environ, start_response))
    return response_started, chunks
```
```python
# src/python/tests/integration/test_web/test_handler/test_stream_model.py — existing producer pattern
def send_updates():
    assert self.model_listener is not None, "listener not set before Timer fired"
    self.model_listener.file_added(added_file)
    ...
Timer(0.5, send_updates).start()
collect_sse_chunks(self.web_app, stop_after_s=2.0)
```
For an overflow reproduction/convergence test at this level, replace the single `send_updates()`
Timer with one that calls `file_added` > `maxsize` times, and replace `collect_sse_chunks` with a
variant that does not drain continuously (see Pitfall 3).

### Evidence that the status stream is already self-healing (D-06, verified)
```python
# src/python/web/handler/stream_status.py:16-18
class StatusListener(IStatusListener, StreamQueue[Status]):
    def notify(self):
        self.put(self.__status.copy())   # <- a FULL status snapshot, every notify()
```
Each queued event is already a complete snapshot (not a delta), so a drop simply means an older
snapshot was discarded — the next successfully-delivered snapshot (whether the next `notify()` or,
after `get_value()`'s `first_run` branch, the client's own `self.status.copy()` on connect) is
always fully current. No code change is needed for the status stream; this is the literal
evidence D-06 asks to be recorded.

### Evidence the frontend needs no change (D-02, verified)
```typescript
// src/angular/src/app/services/files/model-file.service.ts:136-161
if (name === this.EVENT_INIT) {
    const parsed: ModelFileJson[] = JSON.parse(data);
    const newFiles: ModelFile[] = [];
    for (const file of parsed) { newFiles.push(ModelFile.fromJson(file)); }
    const newMap = Immutable.Map<string, ModelFile>(newFiles.map(value => ([value.name, value])));
    this._files.next(newMap);   // <- unconditional full replace, works identically on a 2nd model-init
}
```

## State of the Art

Not applicable in the usual "library version drift" sense — this is a same-codebase fix with no
external dependency to track. The one relevant "state of the art" fact is architectural, not
version-based: the project already standardized on "full-replace on init, ignore/no-op on
unknown-key delta" as its client-side reconciliation strategy (see `model-file.service.ts`), and
on "bounded queue, drop-oldest, count-and-log" as its server-side backpressure strategy (see
`StreamQueue`). This phase's job is to close the one gap between those two existing strategies
(the model stream lacks a resync trigger that the status stream gets "for free" from always
sending full snapshots).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Paste's `httpserver.serve()` dispatches each HTTP connection to its own worker thread with a blocking per-connection socket write, which is *why* a stalled client blocks the generator at `yield` and lets the queue fill | Summary, Architecture Patterns diagram | If Paste instead used a single-threaded event loop or async I/O, the stall-causes-blocking-write-causes-generator-pause mechanism would need re-verification; however, the *reproduction test itself* (Pitfall 3, option a: call `.file_added()` > maxsize times without draining) does not depend on this assumption at all — it reproduces the overflow directly at the queue boundary regardless of the WSGI server's exact threading model, so STRM-01/STRM-02 are not blocked by this assumption even if it turns out subtly wrong. A direct read of the installed `paste/httpserver.py` source would resolve it but was not reachable in this research session (an unrelated sandbox policy blocked a `find /` traversal outside the project directory) |

**If this table is empty:** N/A — one assumption logged above, and it is explicitly non-blocking
for test design because the recommended reproduction test (Pitfall 3) does not rely on it.

## Open Questions (RESOLVED)

1. **Should the integration-level "fails-before/passes-after" test (roadmap criterion 3) exercise the real WSGI generator, or is the `StreamQueue`/`ModelStreamHandler`-level reproduction sufficient?**
   - What we know: the `StreamQueue`-level reproduction (Pitfall 3, option a) is simpler,
     deterministic, and already satisfies "recorded, repeatable test" for STRM-01. The existing
     integration harness (`collect_sse_chunks`) cannot express a stall without modification.
   - What's unclear: whether the owner/plan-checker will consider a unit-level reproduction +
     unit-level convergence test sufficient proof, or want at least one test that goes through the
     actual WSGI generator and SSE serialization for full-fidelity "fails before, passes after"
     evidence (closer to the literal production path).
   - Recommendation: plan for both — a fast, deterministic unit-level pair
     (`test_stream_queue.py` reproduction + `test_stream_model_handler.py` convergence with a
     mocked Controller) as the primary D-07(a)/(b) evidence, plus one new integration test using a
     modified `wsgi_stream.py` helper (manual `next()` control) as higher-fidelity confirmation.
     This is explicitly flagged as Claude's Discretion in CONTEXT.md ("Test placement and
     harness... whether a frontend spec is added"), so the plan should pick one primary location
     and treat the other as supporting evidence, not duplicate required coverage.
   - RESOLVED: both. Unit-level convergence tests are the primary evidence (124-03 Task 1:
     `TestModelStreamConvergence` with a real Controller, plus `TestModelStreamHandlerResync` with a
     mocked Controller), and one integration-level WSGI stalled-consumer test
     (`test_stalled_consumer_converges_after_overflow`, 124-03 Task 2) confirms the same convergence
     through the real generator and SSE serialization. Both are committed RED before the fix.

2. **Exact log-message cadence for D-08's "rate-limited like the existing `StreamQueue overflow` warning."**
   - What we know: the existing pattern is count-based modulo (`dropped_count % 100 == 1`), not
     time-based, and D-05 explicitly forbids time-based rate limiting for the recovery mechanism
     itself.
   - What's unclear: whether the new warning's modulo should count *resyncs* (as sketched above,
     `_resync_count % 100 == 1` — likely to fire rarely, since one resync can absorb many drops) or
     reuse the *existing* `dropped_count` modulo directly (which would fire far more often, since
     drops accumulate faster than resyncs).
   - Recommendation: count resyncs, not drops — a resync is the user-visible event worth logging
     ("this tab's model was resynced"), and drops are already logged by `StreamQueue.put()` itself.
     Left as Claude's Discretion in CONTEXT.md ("Log message wording").
   - RESOLVED: count resyncs. The D-08 warning is rate-limited by resync count in the existing
     `% 100 == 1` style (`self._resync_count % 100 == 1`, so resyncs 1, 101, 201... log), counts only,
     no file names (124-03 Task 3; asserted by `test_resync_warning_rate_limited_by_resync_count`).

## Environment Availability

Skipped — this phase has no external runtime dependencies beyond what Phases 121-123 already
rely on (Python 3.11-3.12, Poetry, pytest, ruff, Docker for CI's `make run-tests-python`), all of
which are already verified working in this repository's CI and in the current working tree
(confirmed via `src/python/pyproject.toml` and `.github/workflows/ci.yml` reads above). No new
tool, service, or package is introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `>=9.0.3` (+ `pytest-timeout`, `pytest-cov`) [VERIFIED: codebase, `src/python/pyproject.toml:27-30,69-71`] |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (60s timeout, `/tmp` cache dir) |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_web/ tests/unittests/test_controller/ -v` |
| Full suite command | `make run-tests-python` (Docker, what CI runs) — local-only full run: `cd src/python && poetry run pytest` |
| Lint gate (separate from pytest, whole tree) | `ruff check src/python/` (pinned `ruff==0.15.22` in CI, `.github/workflows/ci.yml:91`) |
| Coverage gate | `fail_under = 88`, branch coverage on (`src/python/pyproject.toml:91-95`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRM-01 | Stalled consumer + >maxsize puts ⇒ `StreamQueue` drops oldest events and `get_dropped_count() > 0`, and a naive drain-after-overflow diverges from the producer's true current state | unit | `poetry run pytest tests/unittests/test_web/test_stream_queue.py -v` | ✅ extend existing file |
| STRM-01 | Same reproduction reconstructed through `WebResponseModelListener`/`ModelStreamHandler` (so the evidence is tied to the model stream boundary specifically, not just the generic queue) | unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_handler.py -v` | ✅ extend existing file |
| STRM-02 | After overflow + resync, the client-reconstructed model (parsed from the exact `SerializeModel` JSON payloads) equals the server's current model — fails before the fix, passes after | unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_handler.py -v` | ✅ extend existing file |
| STRM-02 | Same convergence proven through the real WSGI generator + real SSE serialization (higher fidelity; addresses Open Question 1) | integration | `poetry run pytest tests/integration/test_web/test_handler/test_stream_model.py -v` | ✅ extend existing file; ❌ needs a new stall-capable `wsgi_stream.py` helper variant (Wave 0 gap) |
| STRM-02 (D-03) | `resync_model_files(discard_backlog)` is atomic w.r.t. model mutations: a thread holding `__model_lock` blocks a concurrent resync call; the resulting snapshot never misses a mutation made before lock release and never re-delivers one already in the snapshot | unit | `poetry run pytest tests/unittests/test_controller/test_controller.py -v` | ✅ extend existing file (reuse `BaseControllerTestCase` + the `test_callback_does_not_take_model_lock` thread pattern) |
| STRM-02 (D-04) | Multiple drops before a resync is processed fold into exactly one resync/snapshot (no back-to-back double-resync for a single stall) | unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_handler.py -v` | ✅ extend existing file |
| STRM-02 (D-05) | Queue size never exceeds `maxsize` under sustained stall; at most one pending-resync flag exists per handler (not a growing collection) | unit | `poetry run pytest tests/unittests/test_web/test_stream_queue.py -v` and `test_stream_model_handler.py -v` | ✅ extend existing files |
| STRM-02 (D-06) | Status stream evidence recorded (no code change) | unit/documentation | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_status_handler.py -v` (existing tests already cover `StatusListener.notify()` full-snapshot behavior; no new test required, just cite it) | ✅ existing file, no change needed |

### Sampling Rate
- **Per task commit:** targeted file(s) above, e.g. `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_handler.py -v`
- **Per wave merge:** `cd src/python && poetry run pytest` (full local suite) + `ruff check src/python/` (whole tree, separate gate)
- **Phase gate:** `make run-tests-python` (Docker, matches CI exactly) + whole-tree `ruff check src/python/` green before `/bm:verify-work`, per the established CI-gate pattern from Phases 122/123 (STATE.md)

### Wave 0 Gaps
- [ ] `src/python/tests/helpers/wsgi_stream.py` — needs a new helper (or an inline test variant)
  that returns the raw generator object and lets the test control `next()` manually, instead of
  `collect_sse_chunks`'s continuous `list(...)` drain — only needed if the plan includes the
  integration-level convergence test (Open Question 1). Not needed for the unit-level tests, which
  are sufficient on their own for STRM-01/STRM-02.
- [ ] No new fixtures, frameworks, or `conftest.py` changes needed — `BaseControllerTestCase`
  (`src/python/tests/unittests/test_controller/base.py`) and `MagicMock(spec=Controller)`
  (`src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py`) already cover
  every harness this phase needs.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | `/server/stream` is already auth-exempt by design (`WebApp._AUTH_EXEMPT_PATHS`, EventSource cannot send custom headers) — unchanged by this phase |
| V3 Session Management | No | No session state introduced; per-connection listener state already exists |
| V4 Access Control | No | No new endpoint, no new access-controlled resource |
| V5 Input Validation | No | No new user-controlled input; the resync path only reads the Controller's own trusted in-memory model |
| V6 Cryptography | No | Not applicable |
| (Resource exhaustion / DoS, not a numbered ASVS category here but directly relevant) | Yes | This phase *is* the fix for a bounded-memory guarantee: keep per-tab worst case at one capped `StreamQueue` (1000 events) + one in-flight snapshot (D-04), never unbounded, never time-based retry accumulation |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded memory growth from a slow/malicious client that never drains its stream (CWE-400) | Denial of Service | Already partially mitigated by `StreamQueue`'s `maxsize=1000` drop-oldest behavior; this phase must preserve that bound while adding resync state, and must not let repeated drops accumulate more than one pending snapshot per tab (D-04/D-05) |
| Log injection via an attacker-controlled string reaching a log line (CWE-117) | Tampering | Not newly introduced here (the resync warning logs only counts), but any future edit that adds a file/path name to that log line must route through `sanitize_log_value`, matching the existing `AutoDeleteLogSanitization` convention in this codebase |

## Sources

### Primary (HIGH confidence — direct codebase reads)
- `src/python/web/utils.py:1-96` — `StreamQueue` (bounded, drop-oldest, `get_dropped_count`, `get_queue_size`, `get_maxsize`)
- `src/python/web/handler/stream_model.py:1-74` — `WebResponseModelListener`, `ModelStreamHandler.setup/get_value/cleanup`
- `src/python/web/handler/stream_status.py:1-48` — `StatusListener`, `StatusStreamHandler` (D-06 evidence)
- `src/python/web/web_app.py:50-298` — `WebApp.__web_stream` (one value per handler per iteration, 10ms/100ms poll, 15s heartbeat), `_AUTH_EXEMPT_PATHS`
- `src/python/web/web_app_job.py:1-84` — Paste `httpserver.serve(..., start_loop=False)` + `serve_forever()`, `MyWSGIHandler.wsgi_write_chunk` (threading-model basis for A1)
- `src/python/controller/controller.py:192,448,495-531` — `__model_lock`, `add_model_listener`, `remove_model_listener`, `get_model_files_and_add_listener`, `__get_model_files`
- `src/python/model/model.py:40-76` — `Model.add_listener` (idempotent), `Model.remove_listener`
- `src/python/model/file.py:87-120` — `ModelFile.__eq__` (deep, excludes timestamp/parent/frozen)
- `src/python/web/serialize/serialize_model.py:1-113` — `SerializeModel.model()`, `update_event()`
- `src/python/controller/memory_monitor.py:1-210` — `register_stream_queue` exists but has no call site outside its own definition (confirmed via grep); per-connection `StreamQueue`s are not currently wired into it
- `src/angular/src/app/services/files/model-file.service.ts:116-201` — `parseEvent` (full replace on `model-init`; no-op on unknown-key add/remove/update)
- `src/angular/src/app/services/base/stream-service.registry.ts:54-170` — `StreamDispatchService` 30s idle-timeout reconnect (existing fallback, unchanged)
- `src/python/tests/unittests/test_web/test_stream_queue.py` — existing `StreamQueue` unit tests and conventions
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` — existing mocked-`Controller` harness for `ModelStreamHandler`
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` + `src/python/tests/helpers/wsgi_stream.py` — existing raw-WSGI-generator SSE test harness
- `src/python/tests/unittests/test_controller/base.py` (`BaseControllerTestCase`) + `src/python/tests/unittests/test_controller/test_controller_unit.py` (`test_callback_does_not_take_model_lock`) — existing real-lock, real-thread Controller test pattern
- `src/python/pyproject.toml:27-30,69-95` — pytest/coverage config, `fail_under = 88`
- `.github/workflows/ci.yml:36-94` — CI job structure, `ruff==0.15.22` pin, `make run-tests-python`
- `Makefile:80-139`, `docs/DEVELOPMENT.md:43-57` — local/CI test commands
- `.planning/codebase/CONCERNS.md` — `DEFER-STREAMQUEUE` (producer-side non-atomicity, already bounded/counted/logged) and "SSE stream is a busy-poll loop" (per-connection generator confirmation)
- `.planning/phases/124-model-stream-overflow-recovery/124-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` (Phase 124 section)

### Secondary (MEDIUM confidence)
- None used beyond the primary codebase reads above — this phase needed no external library
  research.

### Tertiary (LOW confidence)
- None — Assumption A1 (Paste httpserver threading model) is logged separately in the Assumptions
  Log rather than here, since it is grounded in a direct read of this repo's own
  `web_app_job.py` wiring plus well-established Paste library behavior, and is explicitly flagged
  as non-blocking for the recommended test design.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every class/method cited was read directly in this session
- Architecture: HIGH — the lock-bridge design (`Callable[[], None]`) was derived from a direct read of the existing `__model_lock` usage and the project's own import-direction convention (`web` → `controller`, never the reverse)
- Pitfalls: HIGH — each pitfall traces to a specific race condition or layering issue found by tracing the actual lock/thread model, not generic advice
- Validation architecture: HIGH — every test file and harness pattern cited was read directly; the one gap (a stall-capable WSGI helper) is explicitly flagged, not assumed to exist

**Research date:** 2026-10-26
**Valid until:** No external-library staleness risk (internal-only fix); re-verify only if `controller.py`'s lock structure or `StreamQueue`/`ModelStreamHandler` change before this phase is planned/executed.
