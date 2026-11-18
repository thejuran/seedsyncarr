# Phase 128: Arr Key Normalization - Pattern Map

**Mapped:** 2026-11-18
**Files analyzed:** 9 (2 new, 7 modified)
**Analogs found:** 9 / 9

All paths below are relative to `src/python/` unless they start with `.planning/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `common/arr_api_key.py` (NEW) | utility | transform | `common/types.py` (`sanitize_log_value`) | exact |
| `common/__init__.py` (MOD) | config (barrel re-export) | n/a | itself, line 1 | exact |
| `web/handler/config.py` (MOD) | controller (bottle handler) | request-response | itself: `__handle_set_config` 304-344, `_test_arr_connection` 346-364 | exact (in-place) |
| `controller/arr_queue.py` (MOD) | service (HTTP client) | request-response / background worker | itself: `start_fetch` URL-skip 191-194, `enabled_targets` 164-176, `_key_token` 48-54 | exact (in-place) |
| `tests/unittests/test_common/test_arr_api_key.py` (NEW) | test | transform | `tests/unittests/test_common/test_types.py` | exact |
| `tests/unittests/test_controller/test_arr_queue.py` (MOD) | test | request-response | itself: `TestArrQueueTargets` 203-235, `test_start_fetch_rejects_non_http_url` 553-562 | exact |
| `tests/unittests/test_controller/test_completion_gate.py` (MOD) | test | event-driven (gate loop) | itself: `TestRealClientNonBlocking` 440-460 | exact |
| `tests/unittests/test_web/test_handler/test_config_handler.py` (MOD) | test | request-response | itself: `TestConfigHandlerSet` 65-187; `test_config_key_whitespace_stripped_before_header` 703-723 | exact |
| `tests/integration/test_web/test_handler/test_config.py` (MOD) | test (integration, WebTest) | request-response | itself: `test_get_secret_fields_always_blank` 21-38, `test_set_good` 40-71 | exact |

## Pattern Assignments

### `common/arr_api_key.py` (NEW, utility, transform)

**Analog:** `common/types.py` lines 17-58 (`sanitize_log_value`): a small, pure, dependency-free helper in `common/`, typed signature, docstring that cites the phase/decision IDs, module re-exported from `common/__init__.py`.

**Regex to move (verbatim, including the comment)** from `web/handler/config.py` lines 17-20:
```python
# Printable ASCII without space -- the only characters `requests` accepts in
# a header value without raising InvalidHeader, whose message would embed
# the raw key (122-14, CR-01).
_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")
```
Rename to public `ARR_API_KEY_CHARS`, extend the comment with "Shared by Save, Test Connection and the queue client (Phase 128, D-01)". Add `normalize_arr_api_key(raw: Any) -> str` (non-`str` -> `""`, else `.strip()`) and `is_valid_arr_api_key(key: str) -> bool` (`fullmatch(...) is not None`), as in RESEARCH.md Pattern 1. No imports other than `re` and `typing`. Must NOT import from `common.config` (keeps `common/__init__.py` import order safe).

**Do not** reuse `_URL_CHARS` (config.py line 25): same regex but different purpose; leave it in place.

---

### `common/__init__.py` (MOD, barrel)

**Analog:** line 1:
```python
from .types import overrides as overrides, sanitize_log_value as sanitize_log_value
```
Add one line in the same `X as X` re-export style (required so ruff does not flag unused re-exports):
```python
from .arr_api_key import ARR_API_KEY_CHARS as ARR_API_KEY_CHARS, normalize_arr_api_key as normalize_arr_api_key, is_valid_arr_api_key as is_valid_arr_api_key
```
Consumers then import from `common` exactly as `arr_queue.py` line 28 does: `from common import Context, sanitize_log_value`.

---

### `web/handler/config.py` (MOD, controller, request-response)

**Analog:** the file itself.

**Imports** (lines 1-15). `re` stays imported (still used by `_URL_CHARS`, `_HOSTNAME_RE`). Extend line 12:
```python
from common import Context, overrides, Config, ConfigError
```
to add `normalize_arr_api_key, is_valid_arr_api_key`. Delete `_API_KEY_CHARS` (lines 17-20); its only use is line 360.

**Test Connection refactor** (current lines 352-364), behaviour-preserving:
```python
        if not api_key or not api_key.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} API key is required".format(service_name)}),
                content_type="application/json"
            )

        api_key = api_key.strip()
        if not _API_KEY_CHARS.fullmatch(api_key):
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} API key contains invalid characters".format(service_name)}),
                content_type="application/json"
            )
```
Replace only the two middle lines with `api_key = normalize_arr_api_key(api_key)` / `if not is_valid_arr_api_key(api_key):`. Keep both error strings byte-identical.

**Save handler** (lines 304-344). Existing guard order to preserve:
1. body dict check (310-311) -> 400 "Invalid request body"
2. section/key isinstance check (319-320) -> 400 "Invalid request body"
3. empty value check (323-324) -> 400 "Invalid request body"
4. `value_str = str(value)` (326)
5. `has_section` / `has_property` 404s (329-337)
6. try `set_property` / except `ConfigError` -> 400 `str(e)` (338-344)

Insert the Arr-key branch between steps 5 and 6 (keeps 404 semantics for unknown section/key). Existing 400 refusal shape to copy:
```python
            return HTTPResponse(body="Invalid request body", status=400)
```
Existing success/error tail to modify (lines 338-344):
```python
        try:
            inner_config.set_property(key, value_str)
            return HTTPResponse(body="{}.{} set to {}".format(section, key, value_str))
        except ConfigError as e:
            return HTTPResponse(body=str(e), status=400)
```
D-07: for `(section, key)` in `{(attr, field) for (attr, field, _ini) in Config.secret_fields()}` return `"{}.{} updated"`. Compare against `attr` (lowercase), not `ini_section`. `Config` is the real class already imported at line 12, so this works when `self.__config` is a MagicMock in unit tests. Module-level constants follow the file's existing style: leading underscore, comment block above, e.g. `_ARR_KEY_PROPS = {("sonarr", "sonarr_api_key"): "Sonarr", ("radarr", "radarr_api_key"): "Radarr"}`.

**Source of truth for secrets:** `common/config.py` lines 671-700 (`Config.secret_fields()` classmethod, returns `(attr_lowercase, field_name, ini_section_TitleCase)`). Arr PROPs: lines 363 and 374 (`Checkers.null, Converters.null, secret=True`). Leave the PROPs unchanged (RESEARCH Pitfall 1).

---

### `controller/arr_queue.py` (MOD, service, request-response)

**Analog:** the file itself.

**Imports** (line 28):
```python
from common import Context, sanitize_log_value
```
Add `normalize_arr_api_key, is_valid_arr_api_key`.

**State init** (lines 155-162) — add `self.__key_skip_warned: Dict[str, str] = {}` alongside the other controller-thread-only dicts:
```python
    def __init__(self, context: Context, clock: Callable[[], float] = time.monotonic):
        self.__context = context
        self.__clock = clock
        self.logger = context.logger.getChild("ArrQueueClient")
        self.__fetches: Dict[str, _Fetch] = {}
        self.__results: Dict[str, Tuple[int, Optional[List[QueueRecord]]]] = {}
        self.__results_lock = threading.Lock()
        self.__fetch_seq = 0
```

**Normalize on read** (lines 164-176) — replace `config.sonarr.sonarr_api_key or ""` (line 171) and `config.radarr.radarr_api_key or ""` (line 175) with `normalize_arr_api_key(...)`:
```python
        if config.sonarr.enabled:
            targets.append(ArrTarget("Sonarr", "sonarr",
                                     config.sonarr.sonarr_url or "",
                                     config.sonarr.sonarr_api_key or ""))
```

**Skip pattern to mirror** (lines 191-194), the D-06 model. Put the key check immediately AFTER this block (RESEARCH Pitfall 5) and before the in-flight check at line 196:
```python
        scheme = urllib.parse.urlsplit(target.url).scheme.lower()
        if scheme not in ("http", "https"):
            self.logger.warning("%s queue check skipped: URL must use http or https", target.label)
            return None
```
Log with `%s` + `target.label` only. Never pass `target`, `target.api_key` or headers to a logger (`ArrTarget` is a NamedTuple whose repr includes `api_key`). Update the `start_fetch` docstring (lines 188-189, "Returns None without starting anything when ...") to name the key condition too.

**Opaque key token for warn-once** (lines 43-54):
```python
_KEY_TOKENS: Dict[str, str] = {}
_KEY_TOKENS_LOCK = threading.Lock()


def _key_token(api_key: str) -> str:
    with _KEY_TOKENS_LOCK:
        token = _KEY_TOKENS.get(api_key)
        if token is None:
            token = "k{}".format(len(_KEY_TOKENS) + 1)
            _KEY_TOKENS[api_key] = token
        return token
```
`ArrTarget.identity` (lines 65-72) tokenizes `self.api_key`, so once `enabled_targets` normalizes, padded and trimmed keys share an identity automatically. No change to `ArrTarget`.

**Worker** (lines 273-281) stays unchanged; it sends `target.api_key` as `X-Api-Key` (line 278) and logs exceptions by type name only.

**Module docstring** line 18 ("The api key, URL, request headers and response bodies are never logged.") already states the invariant; keep it true.

---

### `tests/unittests/test_common/test_arr_api_key.py` (NEW, test)

**Analog:** `tests/unittests/test_common/test_types.py` lines 1-4 (plain `unittest.TestCase`, import from the `common` barrel):
```python
import unittest

from common import overrides
from common import sanitize_log_value
```
Use `self.subTest(raw=...)` for the rule table (None, "", "   ", padded valid, inner space, tab, CR/LF, NUL, "clé", NBSP padding, inner NBSP).

---

### `tests/unittests/test_controller/test_arr_queue.py` (MOD, test)

**Analog:** the file itself.

**Fixtures** (lines 22-23, 171-185): `API_KEY = "s3cr3t-api-key-0123456789abcdef"`, `SONARR_URL`, `BaseArrQueueTestCase.setUp` with MagicMock `context.config` and `self.logger` returned from `context.logger.getChild`. The ARR-02 RED test must set `self.context.config.sonarr.sonarr_api_key = "  " + API_KEY + "\n"` and go through `self.client.enabled_targets()` (RESEARCH Pitfall 2).

**Helpers to reuse** (lines 135-168): `_response`, `_bind_exceptions`, `_log_text`, `_calls(logger, level)`, plus `settle` (line 92).

**Target-test analog** (lines 217-223), for the "padded and trimmed key have the same identity" test:
```python
    def test_enabled_target_with_blank_url_is_still_enabled(self):
        self.context.config.sonarr.sonarr_url = None
        self.context.config.sonarr.sonarr_api_key = None
        targets = self.client.enabled_targets()
        self.assertEqual(1, len(targets))
        self.assertEqual("", targets[0].url)
        self.assertEqual("", targets[0].api_key)
```

**Skip-test analog** (lines 553-562), for the ARR-03 invalid-key tests; it lives in `TestArrQueueFetch` (class-level `@patch("controller.arr_queue.requests")`, line 238):
```python
    def test_start_fetch_rejects_non_http_url(self, mock_requests):
        _bind_exceptions(mock_requests)
        before = threading.active_count()
        fid = self.client.start_fetch(ArrTarget("Sonarr", "sonarr", "ftp://x", API_KEY))
        self.assertIsNone(fid)
        self.assertEqual(before, threading.active_count())
        self.assertFalse(self.client.in_flight("sonarr"))
        mock_requests.get.assert_not_called()
        self.assertEqual(1, len(_calls(self.logger, "warning")))
        self.assertEqual(FETCH_IDLE, self.client.poll("sonarr").state)
```
The no-leak sweep pattern is `test_no_secret_in_logs` (line 569 onward). Note: the real test name is `..._non_http_url`, not `..._non_http_scheme` as RESEARCH says. `test_start_fetch_rejects_blank_url` (564-567) uses `("", "")` and must stay green, which it will because the URL check runs first.

---

### `tests/unittests/test_controller/test_completion_gate.py` (MOD, test)

**Analog:** `TestRealClientNonBlocking` (lines 440-460): a real `ArrQueueClient` + `CompletionGate` over a MagicMock config.
```python
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        url = "http://127.0.0.1:{}".format(self.port)
        cfg = self.context.config
        cfg.sonarr.enabled = True
        cfg.sonarr.sonarr_url = url
        cfg.sonarr.sonarr_api_key = "k"
        ...
        self.client = ArrQueueClient(self.context)
        self.gate = CompletionGate(self.context, self.client)
```
A bad-key test does not need the trickle server: use a plain URL, `sonarr_api_key = "   "`, radarr disabled, `@patch("controller.arr_queue.requests")`, then assert `self.gate.evaluate({ROOT: SIZE})[ROOT] == HOLD("sonarr_unavailable")` (`HOLD = Verdict.hold`, line 129; `ROOT`/`SIZE` lines 26-27), `requests.get` not called, `client.in_flight("sonarr")` False. Gate and client share one logger mock here, so assert on message content, not warning counts (RESEARCH Pitfall 4). Existing key `"k"` stays valid under the rule.

---

### `tests/unittests/test_web/test_handler/test_config_handler.py` (MOD, test)

**Analog for save tests:** `TestConfigHandlerSet` (lines 65-122):
```python
class TestConfigHandlerSet(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_context = MagicMock()
        self.handler = ConfigHandler(self.mock_config, self.mock_context)
    ...
    def test_set_valid_returns_200(self):
        self.mock_config.has_section.return_value = True
        mock_inner = MagicMock()
        mock_inner.has_property.return_value = True
        self.mock_config.lftp = mock_inner
        with patch('web.handler.config.bottle') as mock_bottle:
            mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "192.168.1.1"}
            response = self.handler._ConfigHandler__handle_set_config()
        self.assertEqual(200, response.status_code)
```
For Arr keys set `self.mock_config.sonarr = mock_inner`, then assert `mock_inner.set_property.assert_called_once_with("sonarr_api_key", "<trimmed>")` (copy `test_set_calls_set_property`, lines 84-92), or `mock_inner.set_property.assert_not_called()` on refusal, and `response.body` text.

**Locked-string convention** (lines 18-28): refusal messages are pinned as module-level literals, not imported from `config.py`. Add e.g. `SONARR_KEY_INVALID_MSG = "Sonarr API key contains invalid characters"` the same way.

**Test Connection pin** (lines 703-723, `test_config_key_whitespace_stripped_before_header`): must stay green unchanged after the refactor.

---

### `tests/integration/test_web/test_handler/test_config.py` (MOD, integration test)

**Analog:** the file itself. Base class import (line 3): `from tests.integration.test_web.test_web_app import BaseTestWebApp`. Real `Config` at `self.context.config`.

Set pattern (lines 40-47):
```python
    def test_set_good(self):
        self.assertEqual(None, self.context.config.general.debug)
        resp = self.test_app.post_json(
            "/server/config/set",
            {"section": "general", "key": "debug", "value": "True"}
        )
        self.assertEqual(200, resp.status_int)
        self.assertEqual(True, self.context.config.general.debug)
```
No-echo assertion pattern (lines 36-38, from `test_get_secret_fields_always_blank`):
```python
        self.assertNotIn("super-secret-value", str(resp.html))
        self.assertNotIn("super-token-value", str(resp.html))
```
For 400 cases use `post_json(..., expect_errors=True)` (WebTest) and check `resp.status_int == 400` plus the stored value unchanged. Loop over `Config.secret_fields()` (import `from common import Config`) for the D-07 sweep. Some secret props may have converters/checkers that reject arbitrary strings; use a value valid for each (all current secrets use `Converters.null`, per RESEARCH Pattern 2).

## Shared Patterns

### No secrets in logs
**Source:** `controller/arr_queue.py` line 193 (label-only `%s` warning), module docstring line 18; `.planning/phases/122-.../122-CONTEXT.md` D-14.
**Apply to:** `arr_queue.py` skip branch; any new log line in `config.py`.
Log `target.label` / `service_name` and fixed text only. Exception logging at network boundaries uses `type(e).__name__` only.

### Fixed-string HTTP refusals
**Source:** `web/handler/config.py` lines 311, 320, 324 (`HTTPResponse(body="Invalid request body", status=400)`).
**Apply to:** new save-path refusals. Bodies never interpolate `value`/`value_str` for Arr keys or any `secret_fields()` prop.

### Secret discovery
**Source:** `common/config.py` lines 671-700, `Config.secret_fields()`.
**Apply to:** D-07 response branch and the integration sweep test. Do not hard-code a secret list.

### Log-capture in tests
**Source:** `test_arr_queue.py` lines 154-168 (`_log_text`, `_calls`).
**Apply to:** all ARR-03 log assertions; sweep `("debug", "info", "warning", "error", "exception")` for a probe substring.

## Conventions

Derived with `gsd-tools verify conventions --derive --scope src/python`. The tool's axes are tuned for JS/TS and give noisy results for this Python tree, so the table is annotated with what the Python code actually does.

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| file-name casing | none (other 45 / snake 42 / camel 29) | 39% | 0.985 | contested hotspot (tool-level). Python modules are uniformly `snake_case.py`; the other variants come from non-Python files. Use `arr_api_key.py`. |
| identifier casing | none (camel 426 / Pascal 288 / CONSTANT 47) | 54% | 0.613 | contested hotspot (tool-level). Python follows PEP 8: `snake_case` functions, `PascalCase` classes, `UPPER_CASE` / `_UPPER_CASE` module constants. |
| export style | cjs | 100% | 0 | named contract (not meaningful for Python; for Python the convention is the `X as X` re-export in `common/__init__.py`) |
| import style | insufficient data | n/a | n/a | n/a. Python-specific axes: explicit imports (no wildcards) 100%, named contract; relative vs absolute 64% relative, contested. Match the file: `web/handler/*` uses absolute `from common import ...` plus relative `from ..web_app import ...`; `controller/arr_queue.py` uses absolute `from common import ...`. |

**Contested hotspots (author's choice):** the prototype intentional split is the CJS<->SDK dual resolver in the GSD tooling (`bin/lib/**` CJS `module.exports`/`require`, `sdk/src/**` ESM `export`/`import`). Each half is consistent within its own directory and contested only repo-wide. Here, the relative/absolute import split is the same kind of thing: it is consistent per directory, so match the local file's style rather than the repo-wide majority.

## No Analog Found

None. Every file has an in-place or same-directory analog.

## Metadata

**Analog search scope:** `src/python/common/`, `src/python/web/handler/`, `src/python/controller/`, `src/python/tests/unittests/{test_common,test_controller,test_web/test_handler}/`, `src/python/tests/integration/test_web/test_handler/`
**Files scanned:** 12
**Pattern extraction date:** 2026-11-18
