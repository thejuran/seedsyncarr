# Phase 111: Config-Set Endpoint Migration - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 9 files (1 backend handler, 2 Python test files, 2 Angular service files, 1 Angular spec, 1 bash E2E setup script, 2 Playwright TypeScript files)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/web/handler/config.py` | route handler | request-response | `src/python/web/handler/webhook.py` | exact (same POST+`request.json` pattern) |
| `src/python/tests/integration/test_web/test_handler/test_config.py` | integration test | request-response | `src/python/tests/integration/test_web/test_handler/test_webhook.py` | exact (same `post_json` webtest helper) |
| `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` | unit test | request-response | `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` (own `TestConfigHandlerGet` class + `TestConfigHandlerRateLimit`) | role-match (existing class structure to mirror) |
| `src/angular/src/app/services/utils/rest.service.ts` | HTTP transport utility | request-response | `src/angular/src/app/services/utils/rest.service.ts` (own `delete` method) | self (extend existing `post` signature) |
| `src/angular/src/app/services/settings/config.service.ts` | data service | request-response | `src/angular/src/app/services/settings/config.service.ts` (own `testSonarrConnection` / `testRadarrConnection`) | self (replace inline URL-build + sendRequest with `_restService.post(url, body)`) |
| `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts` | Angular unit test | request-response | `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts` (own GET-path expectations to migrate) | self (migrate `expectOne` URL strings) |
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | E2E setup script | request-response | `src/docker/test/e2e/configure/setup_seedsyncarr.sh:34` (the `-X POST` restart call) | exact (inline exemplar in the same file) |
| `src/e2e/tests/settings.page.ts` | E2E page object | request-response | `src/e2e/tests/fixtures/seed-state.ts:45-57` (`expectOk` POST dispatch) | role-match (same `page.request.post` API) |
| `src/e2e/tests/fixtures/seed-state.ts` | E2E test fixture | request-response | `src/e2e/tests/fixtures/seed-state.ts:45-57` (own `expectOk` POST dispatch) | self (replace GET constant with inline `page.request.post`) |

Note: `src/e2e/tests/dashboard.page.spec.ts` (lines 277, 308) contains two inline `page.request.get` calls that must also be updated; they follow the same `page.request.post` pattern as `settings.page.ts` and are classified as E2E spec (role: test, data flow: request-response).

---

## Pattern Assignments

### `src/python/web/handler/config.py` (route handler, request-response)

**Analog:** `src/python/web/handler/webhook.py`

**Imports pattern** (`config.py:1-16` — current; `unquote` import must be removed after migration):
```python
# CURRENT (config.py:1-16):
import json
import ipaddress
import logging
import socket
from urllib.parse import urlparse, urljoin, unquote   # <-- remove 'unquote' after migration

import requests
import bottle
from bottle import HTTPResponse

from common import overrides, Config, ConfigError
from ..web_app import IHandler, WebApp
from ..serialize import SerializeConfig
from ..rate_limit import rate_limit
```

**Route registration pattern — REMOVE and REPLACE** (`config.py:25-29`):
```python
# REMOVE (config.py:25-29):
# The regex allows slashes in values
web_app.add_handler(
    "/server/config/set/<section>/<key>/<value:re:.+>",
    rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
)

# ADD (mirroring webhook.py:40):
web_app.add_post_handler(
    "/server/config/set",
    rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
)
```

**`add_post_handler` registration pattern analog** (`src/python/web/handler/webhook.py:40`):
```python
web_app.add_post_handler("/server/webhook/sonarr", self._make_require_secret_guard(rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)))
```

**`add_post_handler` implementation** (`src/python/web/web_app.py:187-188`):
```python
def add_post_handler(self, path: str, handler: Callable):
    self.post(path)(handler)
```

**Core POST body-parsing pattern** (`webhook.py:128-135` — the in-repo precedent to mirror verbatim):
```python
# Parse JSON body
try:
    body = request.json
except (ValueError, json.JSONDecodeError):
    return HTTPResponse(status=400, body="Invalid JSON")

if not body:
    return HTTPResponse(status=400, body="Empty body")
```

**New `__handle_set_config` handler shape** (replacing `config.py:92-105`):
```python
def __handle_set_config(self) -> HTTPResponse:
    # No path params — all fields from JSON body (D-01/D-03)
    try:
        body = bottle.request.json
    except (ValueError, json.JSONDecodeError):
        return HTTPResponse(body="Invalid request body", status=400)

    if not body or not isinstance(body, dict):
        return HTTPResponse(body="Invalid request body", status=400)

    section = body.get("section")
    key = body.get("key")
    value = body.get("value")

    if not section or not key:
        return HTTPResponse(body="Invalid request body", status=400)

    # D-06: missing-or-empty value is 400 (was 404 route-miss under GET regex)
    if value is None or str(value) == "":
        return HTTPResponse(body="Invalid request body", status=400)

    value_str = str(value)

    # Preserve existing validation status codes (D-05)
    if not self.__config.has_section(section):
        return HTTPResponse(
            body="There is no section '{}' in config".format(section), status=404
        )
    inner_config = getattr(self.__config, section)
    if not inner_config.has_property(key):
        return HTTPResponse(
            body="Section '{}' in config has no option '{}'".format(section, key), status=404
        )
    try:
        inner_config.set_property(key, value_str)
        return HTTPResponse(body="{}.{} set to {}".format(section, key, value_str))
    except ConfigError as e:
        return HTTPResponse(body=str(e), status=400)
```

**Key deletion:** The `unquote(value)` call at `config.py:94` is deleted entirely. After deletion, verify that `unquote` is no longer imported (it is not used elsewhere in this file — `urlparse` and `urljoin` remain for `_validate_url` and `_sanitize_redirect_location`). Remove `unquote` from the `from urllib.parse import` line or ruff will flag `F401` and fail the CI lint gate (RESEARCH.md Pitfall 7).

---

### `src/python/tests/integration/test_web/test_handler/test_config.py` (integration test, request-response)

**Analog:** `src/python/tests/integration/test_web/test_handler/test_webhook.py`

**Imports pattern** (`test_config.py:1-3` — current; `quote` import removed after migration):
```python
# CURRENT (test_config.py:1-3):
import json
from urllib.parse import quote   # <-- remove after migration (no longer used)

from tests.integration.test_web.test_web_app import BaseTestWebApp
```

**`post_json` webtest helper** (`test_webhook.py:24-33` — exact pattern to copy):
```python
# Success path (test_webhook.py:29):
resp = self.test_app.post_json("/server/webhook/sonarr", body)
self.assertEqual(200, resp.status_int)

# Error path (test_webhook.py:40):
resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
```

**Migration pattern for each existing set test** — replace `test_app.get(url)` with `test_app.post_json(url, body)`:

```python
# BEFORE (test_config.py:43-45):
def test_set_good(self):
    self.assertEqual(None, self.context.config.general.debug)
    resp = self.test_app.get("/server/config/set/general/debug/True")
    self.assertEqual(200, resp.status_int)

# AFTER (mirroring test_webhook.py:29):
def test_set_good(self):
    self.assertEqual(None, self.context.config.general.debug)
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": "general", "key": "debug", "value": "True"}
    )
    self.assertEqual(200, resp.status_int)
    self.assertEqual(True, self.context.config.general.debug)
```

**`test_set_empty_value` — intentional 404→400 status change** (`test_config.py:92-102` — current):
```python
# BEFORE (current test_config.py:92-96):
def test_set_empty_value(self):
    self.assertEqual(None, self.context.config.lftp.remote_path)
    resp = self.test_app.get("/server/config/set/lftp/remote_path/", expect_errors=True)
    self.assertEqual(404, resp.status_int)   # <-- route-miss artifact

# AFTER (D-06 — empty value is now body-validation 400):
def test_set_empty_value(self):
    # D-06: empty value is now 400 (was 404 under GET route-miss; intentional refinement)
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": "lftp", "key": "remote_path", "value": ""},
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)
```

**New tests to add** (D-07 malformed body, D-02 route removal — currently zero coverage):
```python
def test_set_malformed_body_wrong_content_type(self):
    # D-07: wrong content-type → bottle.request.json returns None → 400
    resp = self.test_app.post(
        "/server/config/set",
        params="not-json",
        content_type="text/plain",
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)

def test_set_missing_required_field(self):
    # D-07: absent required field → 400
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": "general", "key": "debug"},  # no 'value'
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)

def test_get_old_path_returns_404_or_405(self):
    # D-02: old GET route is removed; bare GET to the POST-only path returns 405
    resp = self.test_app.get(
        "/server/config/set/general/debug/True",
        expect_errors=True
    )
    self.assertIn(resp.status_int, (404, 405))
```

---

### `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` (unit test, request-response)

**Analog:** Same file's `TestConfigHandlerGet` class and the existing `TestConfigHandlerRateLimit` class pattern. Also `test_config_handler.py:372-403` for rate-limit test structure.

**Existing `TestConfigHandlerSet` calling convention** (`test_config_handler.py:36-90` — current, calling handler with path-param args):
```python
# CURRENT (passes path params as positional args):
response = self.handler._ConfigHandler__handle_set_config("lftp", "remote_address", quote("192.168.1.1"))
```

**New calling convention** — handler takes no args; mock `bottle.request.json`:
```python
# AFTER — mock bottle.request for all TestConfigHandlerSet tests:
with patch('web.handler.config.bottle') as mock_bottle:
    mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "192.168.1.1"}
    response = self.handler._ConfigHandler__handle_set_config()
```

**Migrated `test_set_valid_returns_200`** (`test_config_handler.py:36-42`):
```python
# BEFORE:
def test_set_valid_returns_200(self):
    self.mock_config.has_section.return_value = True
    mock_inner = MagicMock()
    mock_inner.has_property.return_value = True
    self.mock_config.lftp = mock_inner
    response = self.handler._ConfigHandler__handle_set_config("lftp", "remote_address", quote("192.168.1.1"))
    self.assertEqual(200, response.status_code)

# AFTER:
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

**Encoding tests to REPLACE** (`test_config_handler.py:76-90` — both removed; replaced with raw-value tests):
```python
# REMOVE: test_set_url_decodes_value (line 76-82) — unquote no longer exists
# REMOVE: test_set_value_with_slashes (line 84-90) — double-encode no longer exists

# ADD: raw-value-through-body replacements (D-04, D-11):
def test_set_raw_value_with_spaces_through_body(self):
    # Replaces test_set_url_decodes_value: value arrives verbatim in body, no URL decode
    self.mock_config.has_section.return_value = True
    mock_inner = MagicMock()
    mock_inner.has_property.return_value = True
    self.mock_config.lftp = mock_inner
    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = {"section": "lftp", "key": "remote_path", "value": "/path/with spaces"}
        self.handler._ConfigHandler__handle_set_config()
    mock_inner.set_property.assert_called_once_with("remote_path", "/path/with spaces")

def test_set_raw_value_with_slashes_through_body(self):
    # Replaces test_set_value_with_slashes: slashes arrive verbatim in body, no URL decode
    self.mock_config.has_section.return_value = True
    mock_inner = MagicMock()
    mock_inner.has_property.return_value = True
    self.mock_config.lftp = mock_inner
    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = {"section": "lftp", "key": "remote_path", "value": "/remote/path/to/dir"}
        self.handler._ConfigHandler__handle_set_config()
    mock_inner.set_property.assert_called_once_with("remote_path", "/remote/path/to/dir")
```

**New unit tests for D-07 body validation:**
```python
def test_set_none_body_returns_400(self):
    # D-07: no body / wrong content-type → bottle.request.json returns None
    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = None
        response = self.handler._ConfigHandler__handle_set_config()
    self.assertEqual(400, response.status_code)

def test_set_non_dict_body_returns_400(self):
    # D-07: JSON array body (valid JSON, wrong type)
    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = ["not", "a", "dict"]
        response = self.handler._ConfigHandler__handle_set_config()
    self.assertEqual(400, response.status_code)
```

**Rate-limit test — calling convention change** (`test_config_handler.py:376-403`):
```python
# BEFORE (passes keyword args matching old path params):
response = rate_limited(section="lftp", key="key{}".format(i), value="val")

# AFTER: no args; mock bottle.request per call:
with patch('web.handler.config.bottle') as mock_bottle:
    mock_bottle.request.json = {"section": "lftp", "key": "key{}".format(i), "value": "val"}
    response = rate_limited()
```

---

### `src/angular/src/app/services/utils/rest.service.ts` (HTTP transport utility, request-response)

**Analog:** Same file's `delete` method (`rest.service.ts:71-77`) — identical `pipe(map/catchError/shareReplay)` chain; the extension adds an optional `body?` parameter.

**Current `post` signature** (`rest.service.ts:58-64`):
```typescript
public post(url: string): Observable<WebReaction> {
    return this._http.post(url, null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

**`delete` method to mirror** (`rest.service.ts:71-77`):
```typescript
public delete(url: string): Observable<WebReaction> {
    return this._http.delete(url, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

**New signature with optional body** (D-10 — existing callers unaffected; `body ?? null` preserves null for the four no-body callers):
```typescript
public post(url: string, body?: object): Observable<WebReaction> {
    return this._http.post(url, body ?? null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

**Four existing callers confirmed unaffected** (all pass only `url`):
- `model-file.service.ts:61` — `this._restService.post(url)`
- `model-file.service.ts:74` — `this._restService.post(url)`
- `model-file.service.ts:87` — `this._restService.post(url)`
- `server-command.service.ts:26` — `this._restService.post(this.RESTART_URL)`

---

### `src/angular/src/app/services/settings/config.service.ts` (data service, request-response)

**Analog:** Same file's `testSonarrConnection` / `testRadarrConnection` methods (`config.service.ts:88-97`) which call `_restService.sendRequest(url)` — the migrated `set()` switches from `sendRequest(url)` to `post(url, body)`.

**`CONFIG_SET_URL` constant to DELETE** (`config.service.ts:20-22`):
```typescript
// DELETE entirely:
private readonly CONFIG_SET_URL =
    (section: string, option: string, value: string): string =>
        `/server/config/set/${section}/${option}/${value}`;
```

**Current `set()` transport block to REPLACE** (`config.service.ts:65-68`):
```typescript
// CURRENT (config.service.ts:65-68) — DELETE these three lines:
const valueEncoded = encodeURIComponent(encodeURIComponent(valueStr));
const url = this.CONFIG_SET_URL(section, option, valueEncoded);
const obs = this._restService.sendRequest(url);
```

**Replacement (D-04/D-10 — raw value in JSON body, no encoding)**:
```typescript
// AFTER — single line replaces three (D-04: no encodeURIComponent):
const obs = this._restService.post("/server/config/set", {section, key: option, value: valueStr});
```

**Preserved unchanged** — pre-flight validation block (`config.service.ts:52-63`) and optimistic local update (`config.service.ts:69-79`):
```typescript
// UNCHANGED — pre-flight guards (config.service.ts:52-63):
if (!currentConfig || !currentConfig.has(section as keyof IConfig) || ...) {
    return new Observable<WebReaction>(observer => { ... });
} else if (valueStr.length === 0) {
    return new Observable<WebReaction>(observer => { ... });
} else {
    // <-- only the transport block inside here changes
}

// UNCHANGED — optimistic update on success (config.service.ts:69-79):
obs.pipe(takeUntil(this.destroy$)).subscribe({
    next: reaction => {
        if (reaction.success) {
            const config = this._config.getValue();
            if (!config) { return; }
            const newConfig = new Config(config.updateIn([section, option], (_) => value));
            this._config.next(newConfig);
        }
    }
});
return obs;
```

---

### `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts` (Angular unit test, request-response)

**Analog:** Same file — own existing `httpMock.expectOne(url).flush(...)` pattern (`config.service.spec.ts:56`, `92`, `121`).

**Current `expectOne` pattern** (`config.service.spec.ts:193-195` — the GET URL to replace):
```typescript
// CURRENT (config.service.spec.ts:193):
httpMock.expectOne("/server/config/set/general/debug/true").flush("{}");
```

**Replacement patterns after migration:**
```typescript
// AFTER — URL-only match (consistent with existing spec style):
httpMock.expectOne("/server/config/set").flush("{}");

// AFTER — stricter: method + URL matcher (optional enhancement):
httpMock.expectOne(req => req.method === "POST" && req.url === "/server/config/set").flush("{}");
```

**All `expectOne` lines that reference the old GET URL pattern** (`config.service.spec.ts:193`, `204`, `206`, `210`, `212`, `214`, `218`, `220`, `222`, `226`, `228`, `299`):
Each of these lines matches a pattern like `"/server/config/set/section/option/encoded_value"` and must change to `"/server/config/set"` (the bare POST URL).

**Test descriptions to rename:**
- `"should send a GET on a set config option"` (line 180) → `"should send a POST on a set config option"`
- `"should send correct GET requests on setting config options"` (line 198) → `"should send correct POST requests on setting config options"`

---

### `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (E2E setup script, request-response)

**Analog:** `setup_seedsyncarr.sh:34` — the existing `-X POST` restart call in the same file:
```bash
# EXISTING POST exemplar to mirror (setup_seedsyncarr.sh:34):
curl -sSf -X POST "http://myapp:8800/server/command/restart" \
  || { echo "ERROR: failed to restart app" >&2; exit 1; }
```

**All 11 GET calls to replace** (`setup_seedsyncarr.sh:8-32`). Migration pattern:
```bash
# BEFORE (setup_seedsyncarr.sh:8-9):
curl -sSf "http://myapp:8800/server/config/set/general/debug/true" \
  || { echo "ERROR: failed to set general/debug" >&2; exit 1; }

# AFTER (mirrors restart call at line 34; adds -H Content-Type + -d body):
curl -sSf -X POST \
  -H 'Content-Type: application/json' \
  -d '{"section":"general","key":"debug","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set general/debug" >&2; exit 1; }
```

**Double-encoded path values become plain strings** (D-04/D-12):
```bash
# BEFORE (setup_seedsyncarr.sh:12-13):
curl -sSf "http://myapp:8800/server/config/set/lftp/local_path/%252Fdownloads" \
  || { echo "ERROR: failed to set lftp/local_path" >&2; exit 1; }

# AFTER — plain value in JSON body (no %252F encoding):
curl -sSf -X POST \
  -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"local_path","value":"/downloads"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/local_path" >&2; exit 1; }

# Similarly, setup_seedsyncarr.sh:27-28 (%252Fhome%252Fremoteuser%252Ffiles → /home/remoteuser/files):
curl -sSf -X POST \
  -H 'Content-Type: application/json' \
  -d '{"section":"lftp","key":"remote_path","value":"/home/remoteuser/files"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set lftp/remote_path" >&2; exit 1; }
```

**Full inventory of the 11 GET calls** (lines, section/key/value, and any encoding):

| Line | Section | Key | Current encoded value | Plain value in body |
|------|---------|-----|----------------------|---------------------|
| 8 | general | debug | true | `"true"` |
| 10 | general | verbose | true | `"true"` |
| 12 | lftp | local_path | `%252Fdownloads` | `"/downloads"` |
| 14 | lftp | remote_address | remote | `"remote"` |
| 16 | lftp | remote_username | `${REMOTE_USERNAME}` | `"${REMOTE_USERNAME}"` |
| 19 | lftp | use_ssh_key | true | `"true"` |
| 23 | lftp | remote_password | unused-ssh-key-auth | `"unused-ssh-key-auth"` |
| 25 | lftp | remote_port | 1234 | `"1234"` |
| 27 | lftp | remote_path | `%252Fhome%252Fremoteuser%252Ffiles` | `"/home/remoteuser/files"` |
| 29 | autoqueue | patterns_only | true | `"true"` |
| 31 | autoqueue | enabled | true | `"true"` |

---

### `src/e2e/tests/settings.page.ts` (E2E page object, request-response)

**Analog:** `src/e2e/tests/fixtures/seed-state.ts:45-57` — the `expectOk` function that already dispatches `page.request.post(url)` for POST calls:
```typescript
// seed-state.ts:45-57 — existing POST dispatch pattern:
async function expectOk(page: Page, url: string, method: 'POST' | 'DELETE' | 'GET'): Promise<void> {
    let res;
    if (method === 'POST') {
        res = await page.request.post(url);
    } else if (method === 'DELETE') {
        res = await page.request.delete(url);
    } else {
        res = await page.request.get(url);
    }
    if (!res.ok()) {
        throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
    }
}
```

**Current GET helper pattern** (`settings.page.ts:14-21` — all 7 helpers follow this shape):
```typescript
async enableSonarr(): Promise<void> {
    const response = await this.page.request.get(
        '/server/config/set/sonarr/enabled/true'
    );
    if (!response.ok()) {
        throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
    }
}
```

**POST replacement pattern** (D-13 — `page.request.post` with `data` object, no encoding):
```typescript
async enableSonarr(): Promise<void> {
    const response = await this.page.request.post(
        '/server/config/set',
        { data: { section: 'sonarr', key: 'enabled', value: 'true' } }
    );
    if (!response.ok()) {
        throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
    }
}
```

**All 7 helpers to migrate** (locations in `settings.page.ts`):
1. `enableSonarr` (line 14) — `sonarr/enabled/true`
2. `setSonarrUrl` (line 23) — `sonarr/sonarr_url/${encodeURIComponent(url)}`
3. `setSonarrApiKey` (line 35) — `sonarr/sonarr_api_key/${encodeURIComponent(key)}`
4. `disableSonarr` (line 58) — `sonarr/enabled/false`
5. `setRemoteAddress` (line 69) — `lftp/remote_address/${encodeURIComponent(address)}`
6. `setUseSshKey` (line 78) — `lftp/use_ssh_key/${encodeURIComponent(String(enabled))}`
7. `setRemoteScanInterval` (line 87) — `controller/interval_ms_remote_scan/${encodeURIComponent(ms)}`

**Stale comment to DELETE** (`settings.page.ts:32-34`):
```typescript
// DELETE this comment block:
// NOTE: the key value appears as a plain path segment in server access logs
// because the backend config/set endpoint is GET-only. Always pass obviously-synthetic
// strings (e.g. 'test-FAKE-not-real-0000') — never realistic-looking credentials.
```

---

### `src/e2e/tests/fixtures/seed-state.ts` (E2E test fixture, request-response)

**Analog:** Same file — own `expectOk` + `queueFile`/`stopFile` caller pattern (`seed-state.ts:75-88`).

**`CONFIG_SET` constant to DELETE** (`seed-state.ts:26-27`):
```typescript
// DELETE (seed-state.ts:26-27):
const CONFIG_SET = (section: string, key: string, value: string) =>
    `/server/config/set/${section}/${key}/${encodeURIComponent(value)}`;
```

**`setRateLimit` caller to REPLACE** (`seed-state.ts:71-73`):
```typescript
// CURRENT (seed-state.ts:71-73):
async function setRateLimit(page: Page, bytesPerSec: string): Promise<void> {
    await expectOk(page, CONFIG_SET('lftp', 'rate_limit', bytesPerSec), 'GET');
}

// AFTER — inline page.request.post directly (simpler than restructuring expectOk):
async function setRateLimit(page: Page, bytesPerSec: string): Promise<void> {
    const res = await page.request.post('/server/config/set', {
        data: { section: 'lftp', key: 'rate_limit', value: bytesPerSec }
    });
    if (!res.ok()) {
        throw new Error(`setRateLimit failed: ${res.status()} ${await res.text()}`);
    }
}
```

**Error-throw pattern to mirror** (`seed-state.ts:54-56`):
```typescript
// Mirror this error pattern from expectOk:
if (!res.ok()) {
    throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
}
```

---

### `src/e2e/tests/dashboard.page.spec.ts` (E2E spec — two inline calls, request-response)

**Analog:** `settings.page.ts` post-migration helpers — `page.request.post(url, { data: {...} })`.

**Two inline GET calls to replace** (`dashboard.page.spec.ts:277`, `308`):
```typescript
// BEFORE (line 277):
const throttleResp = await page.request.get('/server/config/set/lftp/rate_limit/100');
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);

// AFTER:
const throttleResp = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '100' }
});
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);

// BEFORE (line 308):
const restoreResp = await page.request.get('/server/config/set/lftp/rate_limit/0');
if (!restoreResp.ok()) throw new Error(`rate_limit restore failed: ${restoreResp.status()}`);

// AFTER:
const restoreResp = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '0' }
});
if (!restoreResp.ok()) throw new Error(`rate_limit restore failed: ${restoreResp.status()}`);
```

---

## Shared Patterns

### POST body guard (belt-and-suspenders)
**Source:** `src/python/web/handler/webhook.py:128-135`
**Apply to:** `config.py` `__handle_set_config`
```python
try:
    body = request.json
except (ValueError, json.JSONDecodeError):
    return HTTPResponse(status=400, body="Invalid JSON")

if not body:
    return HTTPResponse(status=400, body="Empty body")
```
Note: bottle raises `HTTPError(400)` on invalid JSON before calling the handler, so the `try/except` is belt-and-suspenders. The `if not body:` guard is essential for the wrong-content-type case where `request.json` returns `None` silently.

### Webtest `post_json` helper
**Source:** `src/python/tests/integration/test_web/test_handler/test_webhook.py:29`
**Apply to:** All migrated set-config integration tests in `test_config.py`
```python
resp = self.test_app.post_json("/server/webhook/sonarr", body)               # 200 path
resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)  # 4xx path
```

### Playwright `page.request.post` with data
**Source:** In-repo POST dispatch at `src/e2e/tests/fixtures/seed-state.ts:48`; Playwright `^1.48.0` API
**Apply to:** All `settings.page.ts` helpers, `seed-state.ts:setRateLimit`, `dashboard.page.spec.ts:277+308`
```typescript
const res = await page.request.post('/server/config/set', {
    data: { section: '...', key: '...', value: '...' }
});
// data object: Playwright auto-serializes to JSON + sets Content-Type: application/json
```

### Angular `_restService.post(url, body)` body-carrying call
**Source:** `src/angular/src/app/services/utils/rest.service.ts:58-64` (extended)
**Apply to:** `config.service.ts:set()` transport block
```typescript
const obs = this._restService.post("/server/config/set", {section, key: option, value: valueStr});
// HttpClient serializes body as JSON; existing WebReaction pipeline unchanged
```

---

## No Analog Found

All files in scope have close analogs. No entries in this section.

---

## Critical Pitfall Index

The following pitfalls from RESEARCH.md map directly to specific pattern assignments above:

| Pitfall | File | Pattern Section | Guard |
|---------|------|-----------------|-------|
| `bottle.request.json` returns None on wrong Content-Type (→ 500 if unguarded) | `config.py` | "Core POST body-parsing pattern" | `if not body or not isinstance(body, dict): return HTTPResponse(400)` |
| `test_set_empty_value` 404→400 must be commented as intentional | `test_config.py` | "`test_set_empty_value` intentional 404→400" | Add `# D-06:` comment in the test |
| `seed-state.ts:setRateLimit` uses `CONFIG_SET` constant — must be updated | `seed-state.ts` | "`setRateLimit` caller to REPLACE" | Delete `CONFIG_SET`; inline `page.request.post` |
| `dashboard.page.spec.ts` lines 277, 308 are inline — not in a page object | `dashboard.page.spec.ts` | "Two inline GET calls to replace" | Grep `config/set` across full `src/e2e/` tree as final check |
| Rate-limit unit test passes keyword args matching old path params | `test_config_handler.py` | "Rate-limit test calling convention change" | Call `rate_limited()` with no args; mock `bottle.request.json` |
| `unquote` import left orphaned → `F401` ruff lint failure | `config.py` | "Key deletion" note | Remove `unquote` from `from urllib.parse import` line |

---

## Metadata

**Analog search scope:** `src/python/web/handler/`, `src/python/tests/`, `src/angular/src/app/services/`, `src/angular/src/app/tests/`, `src/docker/test/e2e/configure/`, `src/e2e/tests/`
**Files read:** 11 source files
**Pattern extraction date:** 2026-06-02
