# Phase 122: Safety Acceptance and Logging Fixes - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** 19 (5 production code + 5 test files for LOG-01/LOG-02; 9 non-code artifacts for SAFE-01/SAFE-02)
**Analogs found:** 19 / 19 (every file has at least a role-match; 3 items noted under "No Analog Found" for the *new-tooling* slice that has only a partial existing precedent)

This phase ships almost no new code shape — it is dominated by one already-established logging pattern (`context.logger.getChild(...)`) and one already-established live-evidence/incident-record discipline from Phases 119/120. The job here is to point every file at its existing twin, not invent anything.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/web/handler/webhook.py` | controller (web handler) | request-response | `src/python/web/handler/server.py` | exact |
| `src/python/web/handler/controller.py` | controller (web handler) | request-response | `src/python/web/handler/server.py` | exact |
| `src/python/web/handler/config.py` | controller (web handler) | request-response | `src/python/web/handler/server.py` | exact |
| `src/python/web/rate_limit.py` | middleware (decorator factory) | request-response | `src/python/web/handler/server.py` (logger injection shape) + self (decorator shape unchanged) | role-match |
| `src/python/web/web_app_builder.py` | provider (DI wiring) | request-response | self — it already constructs `ServerHandler(context)` the same way | exact |
| `src/python/tests/unittests/test_web/test_webhook_handler.py` | test | request-response | `src/python/tests/unittests/test_web/test_handler/test_server_handler.py` | exact |
| `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` | test | request-response | `test_server_handler.py` | exact |
| `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` | test | request-response | `test_server_handler.py` | exact |
| `src/python/tests/unittests/test_web/test_rate_limit.py` | test | request-response | self (existing `TestRateLimitIndependentClosures` style) | role-match |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` | test (one call-site fix, not a new test) | request-response | `test_config_handler.py` | role-match |
| `src/python/controller/completion_gate.py` (`_clear_hold`) | service (controller business logic) | event-driven | `src/python/controller/controller.py` (`__defer_auto_delete` reason-qualified logging) | role-match |
| `src/python/tests/unittests/test_controller/test_completion_gate.py` | test | event-driven | `src/python/tests/unittests/test_controller/test_auto_delete_rearm.py` | role-match |
| `122-SAFE01-EVIDENCE.md` (new, phase dir) | doc (live evidence) | file-I/O | `119-REL03-EVIDENCE.md` §"Smoke test on NAS" + `120-SON5-EVIDENCE.md` | exact |
| sandbox teardown script (new, adapted, NAS-side) | script/utility | file-I/O | `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` | exact |
| synthetic webhook signer/capture helper (new, adapted, NAS-side) | utility | file-I/O + event-driven | `.planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py` + RESEARCH.md Pattern 3 | role-match |
| `.planning/debug/done-group-no-auto-delete.md` (modified) | doc (incident record) | file-I/O | itself (empty `fix:`/`verification:` fields) + `.planning/debug/resolved/webhook-import-delete-broken.md` (close-out shape) | role-match |
| `.planning/debug/extract-staging-autodel-rearm.md` (modified) | doc (incident record) | file-I/O | itself (existing A–H per-finding structure, extend to Bug 1/Bug 2/D–G table) | exact |
| `.planning/debug/resolved/<name>.md` (new, conditional on D-12 close) | doc | file-I/O | `.planning/debug/resolved/webhook-import-delete-broken.md` | exact |
| `.planning/ROADMAP.md` §Backlog (modified, carry D–G by name) | doc | file-I/O | existing `### Deferred: ...` entries | exact |

## Pattern Assignments

### `src/python/web/handler/webhook.py` (controller, request-response)

**Analog:** `src/python/web/handler/server.py` (the one handler in this package that already has the fix)

**The exact pattern to copy** (`src/python/web/handler/server.py:1-12`):
```python
from threading import Lock

from bottle import HTTPResponse

from common import Context, overrides
from ..web_app import IHandler, WebApp

class ServerHandler(IHandler):
    def __init__(self, context: Context):
        self.logger = context.logger.getChild("ServerActionHandler")
        self.__restart_lock = Lock()
        self.__request_restart = False
```

**Current (broken) state** (`src/python/web/handler/webhook.py:1-29`):
```python
import logging
...
from common import overrides, sanitize_log_value
from common.config import Config
from controller.webhook_manager import WebhookManager
from ..rate_limit import rate_limit
from ..web_app import IHandler, WebApp

logger = logging.getLogger(__name__)   # <-- "web.handler.webhook", no ancestor relation to "seedsyncarr"

class WebhookHandler(IHandler):
    def __init__(self, webhook_manager: WebhookManager, config: Config):
        self.__webhook_manager = webhook_manager
        self.__config = config
```

**Fix shape:** add `context: Context` as a constructor parameter (import `Context` from `common`, same as `server.py`), set `self.logger = context.logger.getChild("WebhookHandler")`, delete the module-level `logger = logging.getLogger(__name__)` line and the now-unused `import logging`, and replace every `logger.xxx(...)` call site in the class body with `self.logger.xxx(...)`. Call sites to update: `webhook.py:56` (`logger.warning` in `_make_require_secret_guard`), `:98`/`:103` (HMAC failures), `:142` (Test event — the D-15 regression target), `:149` (ignored event type), `:161` (missing source path).

**Rate-limit call site** needs `logger=self.logger` threaded through (see `rate_limit.py` pattern below):
```python
# web/handler/webhook.py add_routes, after the fix
web_app.add_post_handler(
    "/server/webhook/sonarr",
    self._make_require_secret_guard(
        rate_limit(max_requests=60, window_seconds=60.0, logger=self.logger)(self.__handle_sonarr_webhook)
    )
)
```

**D-14 secret-safety note:** every value interpolated into these lines is already either a fixed literal (`"Sonarr"`/`"Radarr"`) or passed through `sanitize_log_value` (`webhook.py:150`, `:164`) — no new sanitization needed, only a logger-target change.

---

### `src/python/web/handler/controller.py` (controller, request-response)

**Analog:** same `server.py` pattern as above.

**Current state** (`src/python/web/handler/controller.py:1-17, 57-62`):
```python
import logging
...
from ..web_app import IHandler, WebApp
from ..rate_limit import rate_limit

logger = logging.getLogger(__name__)
...
class ControllerHandler(IHandler):
    def __init__(self, controller: Controller, local_path: str = ""):
        self.__controller = controller
        self.__local_path_real: Path | None = (
            Path(os.path.realpath(local_path)) if local_path else None
        )
```

**Fix shape:** add `context: Context` to `__init__`, `self.logger = context.logger.getChild("ControllerHandler")`, drop the module logger. Call sites: `controller.py:194` (`logger.warning("Rejected path traversal attempt for: %s", repr(file_name))` — **note:** this one line uses `repr()` instead of `sanitize_log_value`, inconsistent with the rest of the codebase; pre-existing, out of this phase's scope per RESEARCH.md, but worth a one-line comment since this file is touched anyway), `:352` (bulk start), `:386` (bulk queue timing, DEBUG), `:428`/`:434` (bulk summary). Also thread `logger=self.logger` into the bulk-command `rate_limit(...)` call at `controller.py:73`.

**Call-site inventory to update** (constructors, found by grep): `web_app_builder.py` (1), `tests/unittests/test_web/test_handler/test_controller_handler.py` (4 `ControllerHandler(...)` constructions at lines 41, 182, 763, 872).

---

### `src/python/web/handler/config.py` (controller, request-response)

**Analog:** same `server.py` pattern.

**Current state** (`src/python/web/handler/config.py:1-20`):
```python
import logging
...
logger = logging.getLogger(__name__)

class ConfigHandler(IHandler):
    def __init__(self, config: Config):
        self.__config = config
```

**Fix shape:** add `context: Context`, `self.logger = context.logger.getChild("ConfigHandler")`. One call site matters for D-14: `config.py:198`:
```python
except Exception:
    logger.exception("Unexpected error testing %s connection", service_name)
    return HTTPResponse(
        body=json.dumps({"success": False, "error": "An unexpected error occurred"}),
        content_type="application/json"
    )
```
`service_name` is always the literal `"Sonarr"`/`"Radarr"`; the `api_key` travels only via the `X-Api-Key` header (`config.py:160`), never the URL, so `logger.exception`'s traceback (frames/lines only, no locals) cannot surface it. D-14 requires one pinning test that forces this path with a known test API key and asserts it is absent from the captured log — add it alongside the lighter "reaches `self.logger`" check.

**Call-site inventory:** `web_app_builder.py` (1), `test_config_handler.py` (6 constructions: lines 15, 33, 156, 278, 440, 478), `test_sonarr5_system_status.py` (1, line 48).

---

### `src/python/web/rate_limit.py` (middleware, request-response)

**Analog:** `server.py` for the logger-injection *idea*; the file's own existing decorator-factory shape for everything else (it stays a function, not a class — do not restructure to match `ServerHandler`).

**Current state** (`src/python/web/rate_limit.py:1-19, 36-39`):
```python
import logging
...
logger = logging.getLogger(__name__)


def rate_limit(max_requests: int, window_seconds: float) -> Callable[[Callable[_P, _R]], Callable[_P, _R | HTTPResponse]]:
    ...
    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R | HTTPResponse]:
        ...
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                ...
                if len(request_times) >= max_requests:
                    ...
                    logger.warning("Rate limit exceeded for %s", func.__name__)
                    return HTTPResponse(...)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Fix shape (lowest-risk, backward-compatible):** add an optional `logger: Optional[logging.Logger] = None` parameter; fall back to the existing module `logger` when not supplied. This keeps `status.py`'s unmodified call site (out of D-13's scope — it has no logger of its own) and every existing `test_rate_limit.py` call (`rate_limit(3, 60.0)(_handler)`) working unchanged:
```python
def rate_limit(
    max_requests: int,
    window_seconds: float,
    logger: Optional[logging.Logger] = None,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R | HTTPResponse]]:
    _logger = logger if logger is not None else globals()["logger"]
    ...
    _logger.warning("Rate limit exceeded for %s", func.__name__)
```
In-scope handlers pass `logger=self.logger` at their own `rate_limit(...)` call sites (`webhook.py`, `controller.py`, `config.py` — 4 call sites total across those three files).

---

### `src/python/web/web_app_builder.py` (provider, request-response)

**Analog:** itself — it already constructs one handler the right way.

**Current state** (`src/python/web/web_app_builder.py:27-35`):
```python
self.controller_handler = ControllerHandler(
    controller,
    local_path=context.config.lftp.local_path
)
self.server_handler = ServerHandler(context)
self.config_handler = ConfigHandler(context.config)
self.auto_queue_handler = AutoQueueHandler(auto_queue_persist)
self.status_handler = StatusHandler(context.status)
self.webhook_handler = WebhookHandler(webhook_manager, context.config)
```
`context` is already in scope in this constructor (it's `self.__context`'s source parameter). Copy `ServerHandler(context)`'s call shape for the other three: `ControllerHandler(controller, context, local_path=...)`, `ConfigHandler(context.config, context)` (or whatever parameter order the plan picks — **Claude's Discretion** per CONTEXT.md A2), `WebhookHandler(webhook_manager, context.config, context)`.

---

### `src/python/tests/unittests/test_web/test_handler/test_server_handler.py` → analog for all four handler test files

**This is the exact test shape to copy** (full file, current working tree):
```python
class TestServerHandler(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.handler = ServerHandler(self.mock_context)

    def test_restart_logs_info(self):
        self.handler._ServerHandler__handle_action_restart()
        self.handler.logger.info.assert_called()
        log_message = self.handler.logger.info.call_args[0][0]
        self.assertIn("restart", log_message.lower())

    def test_constructor_creates_child_logger(self):
        self.mock_context.logger.getChild.assert_called_once_with("ServerActionHandler")
```
For `test_webhook_handler.py` (D-15's fail-before/pass-after regression), the existing `TestWebhookHandlerRoutes.setUp` constructs the handler directly:
```python
# Source: current working tree, test_webhook_handler.py:99-102
def setUp(self):
    self.mock_webhook_manager = MagicMock()
    self.handler = WebhookHandler(self.mock_webhook_manager, _make_mock_config(""))
```
and the existing Test-event test:
```python
# test_webhook_handler.py:132-139
@patch('web.handler.webhook.request')
def test_test_event_returns_200_test_ok(self, mock_request):
    mock_request.content_length = -1
    mock_request.json = {"eventType": "Test"}
    response = self.handler._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)
    self.assertEqual(200, response.status_code)
    self.assertIn("Test OK", response.body)
    self.mock_webhook_manager.enqueue_import.assert_not_called()
```
After the fix, add a `self.mock_context = MagicMock()` + `WebhookHandler(self.mock_webhook_manager, _make_mock_config(""), self.mock_context)` setUp variant and extend this test (or add a sibling) with `self.handler.logger.info.assert_called_with(ANY)` / asserting the formatted message is `"Sonarr webhook test event received"` — this is D-15's literal assertion. Pre-fix, this assertion cannot even be written against the module logger — "the handler has no `.logger` attribute" is itself the RED state.

For `test_config_handler.py`/`test_controller_handler.py`, update every constructor call site (11 + 6 + 4 + 1 = across `test_webhook_handler.py`, `test_config_handler.py`, `test_controller_handler.py`, `test_sonarr5_system_status.py`) to pass a `mock_context`, and add one lighter test per file in `test_server_handler.py`'s `test_constructor_creates_child_logger` shape, e.g. `self.mock_context.logger.getChild.assert_called_once_with("ConfigHandler")`.

**No change needed:** `tests/integration/test_web/test_web_app.py` (`BaseTestWebApp`) — it already constructs `WebAppBuilder(self.context, ...)` with a real logger attached, and `root_logger.getChild("X")` resolves fine against its own `StreamHandler`.

---

### `src/python/tests/unittests/test_web/test_rate_limit.py`

**Analog:** self — existing structure already proves closures are independent per decorated function; extend it for the optional-logger parameter.

**Current shape** (`test_rate_limit.py:1-20`):
```python
class TestRateLimitUnderLimit(unittest.TestCase):
    def setUp(self):
        def _handler():
            return "OK"
        self.handler = rate_limit(3, 60.0)(_handler)

    @patch("web.rate_limit.time")
    def test_first_call_passes_through(self, mock_time):
        mock_time.time.return_value = 1000.0
        result = self.handler()
        self.assertEqual("OK", result)
```
Add one new test class asserting that a supplied `logger=` kwarg is used instead of the module default (e.g. patch a `MagicMock()` logger into `rate_limit(1, 60.0, logger=mock_logger)`, exceed the limit, assert `mock_logger.warning.assert_called()` and the module-level `logger.warning` was NOT called).

---

### `src/python/controller/completion_gate.py` (`_clear_hold`) (service, event-driven)

**Analog:** `src/python/controller/controller.py`'s `__defer_auto_delete` — the closest same-codebase precedent for "one logging chokepoint, several causes, each with its own exact wording," which is exactly LOG-02's shape (and was built in the same incident family, Phase 119's extract-staging/auto-delete-rearm fix).

**Reference pattern** (`src/python/controller/controller.py:1099-1130`):
```python
def __defer_auto_delete(self, file_name: str, reason: str, epoch: Optional[int] = None):
    with self.__auto_delete_lock:
        ...
        attempt = self.__auto_delete_rearms.get(file_name, 0) + 1
        if attempt > _AUTO_DELETE_MAX_REARMS:
            self.__auto_delete_rearms.pop(file_name, None)
            self.logger.warning(
                "Auto-delete given up for '{}' after {} deferrals; last reason: {}. "
                "Local copy left in place".format(
                    sanitize_log_value(file_name), _AUTO_DELETE_MAX_REARMS, reason
                )
            )
            return
        self.__auto_delete_rearms[file_name] = attempt
        delay = self.__arm_auto_delete_timer(file_name)
        self.logger.info(
            "Auto-delete deferred for '{}' (attempt {}/{}): {}; retrying in {} s".format(
                sanitize_log_value(file_name), attempt, _AUTO_DELETE_MAX_REARMS, reason, delay
            )
        )
```
The exact same "one method, a `reason` string parameter, `sanitize_log_value` on the only untrusted value, `.format()` wording" shape applies directly to `_clear_hold`.

**Current code to change** (`src/python/controller/completion_gate.py:203-208, 233-236, 413-416, 427-429`):
```python
# (2) No arr enabled — line 204-208
if not targets:
    verdicts = {name: Verdict.not_required() for name in candidates}
    for name in list(self._holds):
        if prune or name in candidates:
            self._clear_hold(name)          # must become "dropped" — no-arr reason
    return verdicts

# prune path — line 233-236
if prune:
    for name in list(self._holds):
        if name not in candidates:
            self._clear_hold(name)          # must become "dropped" — prune reason

# proof-based release in _record — line 413-416 (UNCHANGED, stays "cleared")
if not verdict.held:
    if previous is not None:
        self._clear_hold(name)
    return

# the single logging point today — line 427-429
def _clear_hold(self, name: str):
    if self._holds.pop(name, None) is not None:
        self.logger.info("Completion hold cleared for '%s'", sanitize_log_value(name))
```

**Recommended shape** (matches `__defer_auto_delete`'s reason-parameter idea, scaled down to 2 states):
```python
def _clear_hold(self, name: str, drop_reason: Optional[str] = None):
    if self._holds.pop(name, None) is not None:
        if drop_reason is None:
            self.logger.info("Completion hold cleared for '%s'", sanitize_log_value(name))
        else:
            self.logger.info("Completion hold dropped for '%s' (%s)", sanitize_log_value(name), drop_reason)
```
Call sites:
```python
self._clear_hold(name, drop_reason="no Sonarr/Radarr integration enabled")   # line ~208
self._clear_hold(name, drop_reason="no longer a queue candidate")            # line ~236
self._clear_hold(name)                                                        # line ~416, unchanged
```
`self.logger` is already `context.logger.getChild("CompletionGate")` (`completion_gate.py:128`) — this file is already on the correct side of the logger-tree fix; LOG-02 is pure wording, no wiring change.

---

### `src/python/tests/unittests/test_controller/test_completion_gate.py`

**Analog:** `GateTestBase` in the same file (no external analog needed — the harness already exists) + `test_auto_delete_rearm.py`'s message-filtering assertion style for the *shape* of asserting exact substrings.

**Existing harness to reuse unchanged** (`test_completion_gate.py:131-150`):
```python
class GateTestBase(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        self.client = FakeArrClient([_target(c) for c in self.CODES])
        self.client.responses = {c: [] for c in self.CODES}
        self.gate = CompletionGate(self.context, self.client, clock=lambda: self.clock.now)

    def info(self) -> List[str]:
        return [_fmt(c) for c in self.logger.info.call_args_list]
```

**Two existing tests to rename+flip** (`test_completion_gate.py:997-1002, 1038-1044`):
```python
# BEFORE (current, asserts the old single-message wording)
def test_hold_cleared_when_no_longer_candidate(self):
    _decide(self.gate, {ROOT: SIZE, "Other": 1})
    self.gate.evaluate({"Other": 1})
    self.assertEqual({"Other": "no_queue_entry"}, self.gate.holds)
    self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))

def test_no_targets_clears_existing_holds(self):
    _decide(self.gate, {ROOT: SIZE})
    self.client.targets = []
    verdict = self.gate.evaluate({ROOT: SIZE})[ROOT]
    self.assertEqual(Verdict.not_required(), verdict)
    self.assertEqual({}, self.gate.holds)
    self.assertEqual(1, sum(1 for line in self.info() if "hold cleared" in line))

# AFTER — rename + flip the assertion (D-18); this is the RED-before part: against today's
# code the string "hold dropped" never appears, so these two fail immediately pre-fix.
def test_hold_dropped_when_no_longer_candidate(self):
    ...
    self.assertEqual(1, sum(1 for line in self.info() if "hold dropped" in line))
    self.assertFalse(any("hold cleared" in line for line in self.info()))

def test_hold_dropped_when_no_arr_enabled(self):   # rename from test_no_targets_clears_existing_holds
    ...
    self.assertTrue(any("no Sonarr/Radarr integration enabled" in line for line in self.info()))
    self.assertFalse(any("hold cleared" in line for line in self.info()))
```
**Leave unchanged** — this is the other half of D-18's regression pair: `test_hold_cleared_when_proven` (`test_completion_gate.py:989-995`) must keep asserting `"hold cleared"` and never `"hold dropped"`.

**Message-filtering assertion style to mirror** (`test_auto_delete_rearm.py:55, 62, 176`):
```python
def _info_messages(self):
    return [str(c.args[0]) for c in self.controller.logger.info.call_args_list if c.args]
...
self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete deferred")])
```

---

### SAFE-01 evidence file (`122-SAFE01-EVIDENCE.md`, new)

**Analog:** `119-REL03-EVIDENCE.md` §"Smoke test on NAS" (Plan 119-10) and `120-SON5-EVIDENCE.md` §SON5-02 — both are the established "live NAS/sandbox acceptance evidence" shape for this repo: numbered milestones, app-clock timestamps with the host-clock-offset called out explicitly, verbatim log-line quoting, and a `curl`/`docker` command-then-output block style.

**Preconditions + redacted-command block style** (`119-REL03-EVIDENCE.md:586-656`):
````
Run 2026-10-15 06:45 to 07:09 -0500 (NAS `date`; app-log/UTC times below are NAS + 5 h).
...
DIGEST=sha256:b061d95a50aad29d00d623191bebbb61290195b7b5eea6ec53d0b99af98bb3de
IMG=ghcr.io/thejuran/seedsyncarr:1.7.5@sha256:b061d95a...
...
### Step 1: startup (D-16 path: both integrations disabled) and D-19 line
```
$ sudo /usr/local/bin/docker run -d --name seedsyncarr-smoke ...
...
set general/webhook_secret=<redacted> -> HTTP 200
...
```
````

**Milestone-with-log-quote style for a gated behavior** (`120-SON5-EVIDENCE.md:60-88`, §SON5-02 — the real-queue gate release D-04 says to *cite*, not re-capture):
````
1. **Incomplete, held.** `queue/details` at 15:57:14 host: `status=downloading`, ... Log:
   ```
   2026-10-20 16:55:50,109 - INFO - seedsyncarr.CompletionGate ... Completion hold for '...': Still downloading
   ```
...
3. **Released and queued only after completion.**
   ```
   2026-10-20 17:03:21,095 - INFO - seedsyncarr.CompletionGate ... Completion hold cleared for '...'
   ```
````
Use this exact numbered-milestone-plus-verbatim-log-block shape for every D-06/D-07 scenario; after LOG-02 ships, the quoted lines must show the new `dropped`/`cleared` split (per the Specific Ideas note in CONTEXT.md).

**Clock-discrepancy framing to reuse every time** (`120-CAPTURE-NOTES.md`, `119-REL03-EVIDENCE.md` throughout): state both clocks explicitly in each excerpt (app-log clock = NAS host clock + 1h, confirmed D-09).

---

### Sandbox teardown script (new, adapted)

**Analog:** `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` (full file read; copy its skeleton, extend for this phase's new restorables).

**Pattern to copy exactly** — read-last-wins `state.env` parsing (never sourced), per-item restore-then-verify-then-print, single `FAILED` accumulator, exit 0 only on a clean final line:
```bash
state_get() {
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }
...
if [ -z "$FAILED" ]; then
  echo "SANDBOX_RESTORED ok"
  exit 0
fi
echo "SANDBOX_RESTORED FAIL $FAILED"
exit 1
```
**Extend, do not rewrite, for this phase's new restorables** (per D-08/Pitfall 1): (a) `webhook_secret` restore-to-empty — the config API 400s on empty, so this item must `sed -i` `settings.cfg` directly and fold the restart into one already planned (D-02's end-of-phase image-pin restore, or D-06(d)'s restart scenario), then verify via `GET /server/config/get` after the restart, not before; (b) seedbox `~/v5test` synthetic dirs/archive removal (new — `120-teardown.sh` has no seedbox leg); (c) sandbox `/downloads` leftover removal; (d) the D-02 image-pin restore itself (`docker compose pull`/`up -d` back to the recorded `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:...` pin), read back and verified the same way `120-teardown.sh` verifies `sonarr_url`.
**Also copy the trap-ordering fix** `120-CAPTURE-NOTES.md:348` already found: `trap '[ "$OK" = 1 ] || bash "$D/teardown.sh"' EXIT INT TERM HUP` alone does not exit on a signal — set `trap 'exit 130' INT TERM HUP` **first**, then the conditional-teardown trap.

---

### Synthetic webhook construction (new, adapted)

**Analog:** `.planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py` (receiving side — O_EXCL/0600 private-file capture, stdlib-only, silenced request logging) + RESEARCH.md's own "Pattern 3: Synthetic HMAC-signed webhook" recipe (the signing side, not yet an existing script, but spec'd from the live handler code):

```bash
# RESEARCH.md Pattern 3 — template, adapt for this phase's D-04/D-06 scenarios
SECRET="$(dd if=/dev/urandom bs=18 count=1 2>/dev/null | base64)"
curl -s -X POST http://127.0.0.1:8801/server/config/set \
  -H "Content-Type: application/json" \
  -d "{\"section\":\"general\",\"key\":\"webhook_secret\",\"value\":\"${SECRET}\"}"
BODY='{"eventType":"Download","episodeFile":{"sourcePath":"/data/torrents/<SyntheticRoot>/child1.mkv"},...}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.*= //')
curl -s -X POST http://127.0.0.1:8801/server/webhook/sonarr \
  -H "Content-Type: application/json" -H "X-Webhook-Signature: ${SIG}" \
  -d "$BODY"
```
Field-shape source of truth: `src/python/tests/fixtures/sonarr5/webhook_download.json` (already sanitized, already proven live against Sonarr 5 in Phase 120) — only `eventType` and `episodeFile.sourcePath` / `movieFile.sourcePath` are read by the handler, so the rest of the fixture's fields can be omitted for synthetic bodies.
**Never**-print-the-secret discipline to copy from `120-webhook_sink.py`'s own docstring/comments: read into a `0600` var inside a `umask 077` area, never echoed, never committed.

---

### SAFE-02 incident records (`.planning/debug/done-group-no-auto-delete.md`, `extract-staging-autodel-rearm.md`)

**Analog:** both files are their own best analog — `done-group-no-auto-delete.md` already has a `## Resolution` block with `fix: ""` / `verification: ""` placeholders exactly where D-10 wants them filled:
```yaml
root_cause: |
  Two distinct defects, one per case. ...
fix: ""
verification: ""
files_changed: []
```
Fill `fix`/`verification` with the Phase 119 plan IDs and commits that actually shipped the per-child-evidence and mtime/queue-evidence fixes (cross-reference `119-VERIFICATION.md` / `119-04/05/06-SUMMARY.md`), per-finding, Case A and Case B separately.

`extract-staging-autodel-rearm.md` already has the richer structure D-10 asks for — a `## Resolution` block with populated `fix:`/`verification:` (commits already landed in 1.7.3), a `## Deep Review` section enumerating A–H with status prefixes (`APPLIED`, `DEFERRED`), and a `## Verification Plan` with an explicit `after_deploy:` checklist that is **literally this phase's D-07 scenario**:
```yaml
after_deploy: |
  1. Sync a rar-d release with auto_extract on. During unrar the release folder must show only
     the rars while <local_path>/.seedsyncarr-extracting/<release>/ grows; the UI must never list
     the dot-dir; the mkv appears in the release folder at full size only at the end.
  2. Trigger the arr import while the root is still EXTRACTING. Expect "Auto-delete deferred ...
     (attempt 1/24) ... retrying in 300 s", then "Auto-deleted local file ..." after extraction completes.
```
Build the per-finding table (Bug 1, Bug 2, D–G) by matching each `after_deploy` line item and each `optional_followups`/`recommended_now` entry (`A.`–`H.`) against the SAFE-01 evidence captured for D-07. D–G items that are not promoted stay `DEFERRED` and get carried **by name** to `.planning/ROADMAP.md`'s Backlog (see next entry).

**Close-out shape to copy** (`.planning/debug/resolved/webhook-import-delete-broken.md`, full file): frontmatter `status: resolved`, a `## Resolution` block with all four fields populated (`root_cause`, `fix`, `verification`, `files_changed`), filed under `.planning/debug/resolved/`. Per D-12, only move a record there once *every* finding is "verified fixed (evidence)" **and** the owner has confirmed operator cleanup — otherwise leave it in `.planning/debug/` with `status: fixes_verified_cleanup_pending` (a new status value for this repo's convention, not yet used elsewhere; consistent with the existing `awaiting_human_verify`/`diagnosed`/`resolved` vocabulary already in use across `.planning/debug/*.md`).

---

### `.planning/ROADMAP.md` §Backlog (carry D–G by name)

**Analog:** existing `### Deferred: ...` entries (`ROADMAP.md:152-166`):
```markdown
### Deferred: Residual import/restart recovery

compare current behavior and regression evidence with a specific unmatched-event or restart
failure scenario. Early episode credit, pending-notice revalidation and restart arm-on-commit
already shipped in Phase 119. Stop with a reproducible remaining gap or a documented no-fix
conclusion; do not rebuild delivered safeguards.
```
Add one entry per still-deferred item from `extract-staging-autodel-rearm.md`'s D–G list (D: `max_deferrals` config key, E: move staging helpers to `controller/extract/staging.py`, F: `sanitize_log_value` on archive-derived paths, G: additional cleanup/lock-order tests), each named explicitly (not folded into one line) per D-12.

## Shared Patterns

### Logger-tree fix (`context.logger.getChild(...)`)
**Source:** `src/python/web/handler/server.py:9-10`; root construction at `src/python/seedsyncarr.py:329-356` (`Constants.SERVICE_NAME = "seedsyncarr"` logger owns the real `StreamHandler`/`RotatingFileHandler`).
**Apply to:** `webhook.py`, `controller.py`, `config.py` (constructor), `rate_limit.py` (optional `logger` param), and every test file constructing these handlers.
```python
self.logger = context.logger.getChild("<ClassName>")
```
`context.logger.getChild("X")` returns `logging.getLogger("seedsyncarr.X")`, a true descendant that propagates up to the handlers already attached to `"seedsyncarr"`. The current `logging.getLogger(__name__)` (e.g. `"web.handler.webhook"`) has no such ancestor and propagates only to the unhandled root logger — this is the entire LOG-01 root cause.

### `sanitize_log_value` (CWE-117 log-injection guard)
**Source:** `common/types.py`, imported and used throughout `completion_gate.py` and `webhook.py` already (`from common import Context, sanitize_log_value`).
**Apply to:** every new `drop_reason`/log line touching an untrusted value (root/file names) in `completion_gate.py`; already applied in `webhook.py` for event type and release title — no new sanitization needed there, only a logger-target change.

### Reason-qualified single logging chokepoint
**Source:** `src/python/controller/controller.py:1099-1130` (`__defer_auto_delete`, `_AUTO_DELETE_MAX_REARMS`) — the same incident family (Phase 119/1.7.3) that LOG-02 is fixing the *wording* gap for.
**Apply to:** `completion_gate.py::_clear_hold` — one method, an optional `drop_reason` parameter, `.format()`/`%`-style wording, `sanitize_log_value` on the name.

### NAS sandbox teardown-on-exit discipline
**Source:** `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` + the trap-ordering fix documented in `120-CAPTURE-NOTES.md:348`.
**Apply to:** every SAFE-01 live session script (D-06 scenarios a–e, D-07 extraction+re-arm, teardown of synthetic seedbox/sandbox material per D-08).
```bash
trap 'exit 130' INT TERM HUP
trap '[ "$OK" = 1 ] || bash "$D/teardown.sh"' EXIT INT TERM HUP
```

### Live-evidence file shape (numbered milestones + verbatim log quoting + explicit dual-clock)
**Source:** `119-REL03-EVIDENCE.md` §"Smoke test on NAS", `120-SON5-EVIDENCE.md` §SON5-02.
**Apply to:** `122-SAFE01-EVIDENCE.md` for every D-06/D-07 scenario, and to the SAFE-02 reconciliation's evidence citations.

### Incident-record per-finding reconciliation + close rule
**Source:** `.planning/debug/extract-staging-autodel-rearm.md`'s own `## Deep Review` (A–H items with `APPLIED`/`DEFERRED` status prefixes) and `## Verification Plan` (`after_deploy:` checklist); close-out shape from `.planning/debug/resolved/webhook-import-delete-broken.md`.
**Apply to:** both SAFE-02 records; D-12's close rule (move to `resolved/` only when every finding is verified **and** owner-confirmed cleanup; otherwise `status: fixes_verified_cleanup_pending`).

## Conventions

Derived via the shared `verify conventions --derive` module (same one `bm-code-reviewer` uses), scoped to the directories this phase actually touches. `src/python/web` (4 of 5 LOG-01 code files) gave clean data; `src/python/controller` (LOG-02's `completion_gate.py`) gave clean data separately — both below. A repo-wide (`src/python`) run was discarded: it picks up generated `htmlcov/`/mkdocs `site/` JS artifacts and produces noise unrelated to this phase's hand-written code.

**Scope `src/python/web`** (23 files):

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| File-name casing | snake_case (below threshold) | 60.9% | 0.798 | contested hotspot |
| Identifier casing | Pascal | 100% | 0.0 | named contract |
| Export style | n/a — Python has no export-style axis | — | — | insufficient-data |
| Import style | n/a — Python has no import-style axis | — | — | insufficient-data |

**Scope `src/python/controller`** (28 files, includes `completion_gate.py`/`controller.py`):

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| File-name casing | snake_case | 75.0% | 0.667 | named contract |
| Identifier casing | Pascal | 82.5% | 0.530 | named contract |
| Export style | n/a | — | — | insufficient-data |
| Import style | n/a | — | — | insufficient-data |

Python-specific supplementary axes (closer analogs to "export/import style" than the JS-centric axes above, same tool run): `py-wildcard-import` is a **named contract** at 100% explicit (`from x import Y`, never `from x import *`) in both scopes — matches `CONVENTIONS.md`'s documented barrel-`__init__.py` re-export style. `py-import-relativity` is a **contested hotspot** in both scopes (relative imports dominant but below 70% in `src/python/web`; same pattern in `src/python/controller`) — match the importing file's existing local/relative-vs-package-absolute choice rather than imposing one project-wide.

**Contested hotspots (author's choice):** when an axis is contested (below 70% dominance), there is no single project-wide answer to defer to — match the file you are editing, not a global rule. The prototype example of an *intentionally* contested, not accidentally inconsistent, split is this tool's own host repo: the CJS↔SDK dual resolver, where `bin/lib/**` is CJS (`module.exports`/`require`) and `sdk/src/**` is ESM (`export`/`import`) — each half is internally consistent per-directory, contested only when measured repo-wide. `src/python/web`'s file-name-casing split (snake vs camel) is this repo's analog: it is driven by Bottle/stdlib file-module conventions (`snake_case.py`) coexisting with a handful of historically camelCase-named test/fixture files, not an unresolved style fight — match the directory you're in (handlers and their modules: snake_case; nothing in this phase's file list should introduce a new camelCase module name).

## No Analog Found

Files/tooling with no complete existing precedent in the repo (closest-available analog cited, but adaptation is required, not a straight copy):

| File / Tooling | Role | Data Flow | Reason |
|---|---|---|---|
| Synthetic HMAC webhook *signing* script (SAFE-01, D-04) | utility | event-driven | `120-webhook_sink.py` only covers the *receiving* side (a disposable capture sink); the signing/posting side is specified only as a shell recipe in RESEARCH.md Pattern 3, not yet an existing script in the repo — build it from that recipe, not from a prior script |
| `webhook_secret` empty-value restore path (SAFE-01 teardown extension) | script/utility | file-I/O | `120-teardown.sh` has no precedent for a config value the API refuses to restore (400 on empty) — Pitfall 1's `sed -i` + restart approach has no prior script analog in this repo; build it as a new teardown step, folded into an already-planned restart per D-08 |
| `status: fixes_verified_cleanup_pending` (SAFE-02 incident-record status value) | doc convention | file-I/O | Not yet used anywhere in `.planning/debug/*.md` (existing values: `diagnosed`, `awaiting_human_verify`, `resolved`); consistent in spirit with D-12's close rule but is a new value for this repo — introduce it rather than searching for a prior use |

## Metadata

**Analog search scope:** `src/python/web/`, `src/python/web/handler/`, `src/python/controller/` (`completion_gate.py`, `controller.py`), `src/python/tests/unittests/test_web/`, `src/python/tests/unittests/test_controller/`, `src/python/tests/unittests/test_sonarr5/`, `.planning/debug/`, `.planning/debug/resolved/`, `.planning/phases/119-safety-follow-ups-and-1-7-5-release/`, `.planning/phases/120-sonarr-5-compatibility/`, `.planning/ROADMAP.md`
**Files scanned:** ~35 (read directly) across the above directories
**Pattern extraction date:** 2026-10-21
