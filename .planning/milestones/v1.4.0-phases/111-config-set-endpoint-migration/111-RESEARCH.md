# Phase 111: Config-Set Endpoint Migration - Research

**Researched:** 2026-06-02
**Domain:** Backend (Bottle/Python), Angular (HttpClient/RestService), E2E (Playwright + bash curl)
**Confidence:** HIGH — all findings sourced from live codebase inspection; no training-data assumptions.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** New route is bare `POST /server/config/set` — no path parameters. All three fields
  (`section`, `key`, `value`) in the JSON body. Registered via `WebApp.add_post_handler`.
- **D-02:** Legacy `GET /server/config/set/<section>/<key>/<value:re:.+>` route removed entirely
  — both the `web_app.add_handler(...)` registration block and all GET-path test assumptions.
  After removal: GET on the old path → 404 (no route); GET on bare path → 405 (POST route exists,
  GET doesn't). Either is acceptable per CFG-02.
- **D-03:** Request body is JSON `{"section": "...", "key": "...", "value": ...}`. Handler reads
  via `bottle.request.json`. `value` is coerced to string for `set_property`.
- **D-04:** Drop double-encoding entirely. Angular sends the raw value in the body; backend uses it
  directly. `unquote` call deleted; both `encodeURIComponent` calls deleted.
- **D-05:** Preserve existing validation status codes: unknown section → 404; unknown key → 404;
  `ConfigError` → 400 with existing message; valid set → 200 with existing body.
- **D-06:** Missing-or-empty `value` field → 400 (malformed input). Whitespace-only continues to
  surface existing `ConfigError` 400. `test_set_empty_value` updated 404→400.
- **D-07:** Malformed POST input (not JSON, not object, absent required field) → generic 400 with
  short client-safe message. Internal detail logged server-side only.
- **D-08:** Keep `rate_limit(max_requests=60, window_seconds=60.0)` wrapping the POST handler.
- **D-09:** Auth posture unchanged — route stays behind the same auth the GET route had.
- **D-10:** `RestService` needs a body-carrying POST variant. Existing `RestService.post(url)` sends
  `null` body. `ConfigService.set` pre-flight validation (unknown section/option guard, blank-value
  guard) and optimistic local `_config.next(...)` update on success are preserved unchanged.
- **D-11:** All set-config tests move GET→POST. Python `fail_under ≥ 88` holds or rises; Karma
  floors hold or rise. Two encoding tests (`test_set_url_decodes_value`,
  `test_set_value_with_slashes`) are **replaced** by raw-value-through-body tests.
- **D-12:** E2E setup script — all 11 `curl -sSf "…/server/config/set/…"` GET calls become
  `curl -sSf -X POST -H 'Content-Type: application/json' -d '{"section":…,"key":…,"value":…}'
  "…/server/config/set"` calls. Pattern mirrors the existing `/server/command/restart` call at
  line 34.
- **D-13:** Playwright page objects — `settings.page.ts` (7+ `page.request.get(…)` helpers) and
  any other spec hitting the endpoint (`settings-fields.spec.ts`, `fixtures/seed-state.ts`,
  `dashboard.page.spec.ts`) switch to
  `page.request.post('/server/config/set', { data: {section, key, value} })`. Stale comment at
  `settings.page.ts:33` removed.

### Claude's Discretion

- Exact name/signature of new body-carrying Angular POST helper (extend `RestService.post` to
  take optional body vs add `postJson`).
- Precise generic 400 message strings for malformed-body cases (D-07), provided they leak no
  internals.
- Whether backend reads body via `bottle.request.json` directly or with a small guarded helper.
- Exact test-helper for body POST in the webtest integration suite.
- Whether the unknown-but-present field detail (D-07) distinguishes "not an object" from "missing
  field" in its 400 message — both are 400.

### Deferred Ideas (OUT OF SCOPE)

- Dual-support GET+POST — explicitly rejected per D-4 / REQUIREMENTS.md "Out of Scope".
  Must not be built.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | Client sets config via POST JSON body; no credential values in URL path segments | D-01/D-03/D-04 confirmed implementable with existing `add_post_handler` + `bottle.request.json` |
| CFG-02 | Legacy GET path fully removed → 404/405 | D-02 confirmed: remove `add_handler` call at `config.py:26-29`; bottle auto-405 on method mismatch |
| CFG-03 | Settings page saves end-to-end; Angular ConfigService + E2E updated; round-trips + persists | D-10/D-12/D-13 mapped to exact file/line locations; `RestService.post` extension pattern confirmed |
| CFG-04 | On-disk config format (plaintext + Fernet) unchanged; no migration step | Confirmed: only transport layer changes; `Config.set_property` untouched |
</phase_requirements>

---

## Summary

Phase 111 is a focused, three-layer transport change. The core insight is that all the plumbing already exists — `add_post_handler`, `bottle.request.json`, `RestService.post`, `page.request.post` — and the webhook handler (which went through the identical GET→POST JSON-body migration earlier) is the in-repo canonical pattern to mirror at every layer.

**Blast radius (exact):** 1 backend handler file + its 2 test files, 2 Angular service files + 1 spec, 1 bash setup script, and 4 E2E TypeScript files. No database, no config format, no shared infrastructure changes.

**Primary recommendation:** Pattern every change after the existing webhook handler migration. At the Python layer, `bottle.request.json` returns `None` on wrong content-type (not an error) — the guard pattern `if not body:` (as used in `webhook.py:134` and `controller.py:223`) is the correct approach. At the Angular layer, extend `RestService.post` to accept an optional body parameter rather than adding a new method, keeping all existing callers unaffected. At the E2E layer, `page.request.post(url, { data: {...} })` is the documented Playwright JSON-body API and the `curl` restart call at `setup_seedsyncarr.sh:34` is the exact shell pattern to mirror.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP route registration | Backend (Bottle/Python) | — | `WebApp.add_post_handler` is the registration point; no frontend involvement |
| Request body parsing + validation | Backend (Bottle/Python) | — | `bottle.request.json` + handler validation; client sends, backend owns validation |
| Transport encoding (client side) | Angular Frontend | — | `ConfigService.set` builds body; `RestService` sends it |
| E2E config seeding | E2E test infrastructure | Bash setup script | Both must be updated together; they bootstrap the same server state |
| On-disk config persistence | Backend (Config/Python) | — | `Config.set_property` / Fernet — untouched by this phase |

---

## Standard Stack

No new packages installed. This phase uses only existing dependencies.

| Layer | Library | Version (pinned) | Role |
|-------|---------|-----------------|------|
| Python backend | `bottle` | `^0.13.4` (installed: 0.13.4) | HTTP routing + `request.json` parsing |
| Python tests | `webtest` | `^3.0.7` | `test_app.post_json()` for integration tests |
| Angular | `@angular/common/http` | Angular 21 | `HttpClient.post(url, body, opts)` |
| E2E | `@playwright/test` | `^1.48.0` | `page.request.post(url, { data })` |

[VERIFIED: live codebase — `src/python/pyproject.toml`, `src/e2e/package.json`]

**Installation:** None required.

---

## Package Legitimacy Audit

Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Client (Angular ConfigService.set)
  │  builds {section, key, value} body
  │  calls RestService.postJson(url, body)  ← new variant
  │  _http.post('/server/config/set', body, {responseType: 'text'})
  │
  ▼
Bottle WebApp — before_request hook
  ├─ Host header check (general.allowed_hostname)
  └─ Bearer token auth (api_token, or allow if unconfigured)
  │
  ▼
rate_limit(60, 60.0) wrapper ← method-agnostic; wraps inner fn
  │
  ▼
ConfigHandler.__handle_set_config()  ← POST, no path params
  ├─ bottle.request.json  → dict or None (None if wrong content-type or empty)
  ├─ guard: if not body or not isinstance(body, dict) → 400
  ├─ extract section / key / value; absent fields → 400
  ├─ config.has_section(section)  → False: 404
  ├─ inner_config.has_property(key) → False: 404
  ├─ inner_config.set_property(key, value) → ConfigError: 400
  └─ success: 200 "section.key set to value"
  │
  ▼
Config.set_property  [UNCHANGED — on-disk Fernet/plaintext format preserved]
```

### Recommended Project Structure (unchanged)

```
src/python/web/handler/
├── config.py           # Route reg changed; handler rewritten; unquote import deleted
└── ...
src/python/tests/
├── integration/test_web/test_handler/test_config.py    # GET→POST_JSON
└── unittests/test_web/test_handler/test_config_handler.py  # GET→POST; encoding tests replaced
src/angular/src/app/services/
├── utils/rest.service.ts          # post(url) → post(url, body?)
└── settings/config.service.ts    # CONFIG_SET_URL removed; set() builds body + calls postJson
src/angular/src/app/tests/unittests/services/settings/
└── config.service.spec.ts         # expectOne(POST url with body matcher)
src/docker/test/e2e/configure/
└── setup_seedsyncarr.sh           # 11 GET curls → POST JSON curls
src/e2e/tests/
├── settings.page.ts               # 7 page.request.get → page.request.post with data
├── settings-fields.spec.ts        # uses SettingsPage helpers — no direct config/set calls
├── fixtures/seed-state.ts         # CONFIG_SET helper + setRateLimit → POST
└── dashboard.page.spec.ts         # 2 inline page.request.get → page.request.post
```

---

## Research Findings by Question

### RQ-1: Bottle `request.json` behavior (D-03, D-07)

**Source:** `bottle.py:BaseRequest.json` property, inspected in the project's poetry venv at
`/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/bottle.py`
[VERIFIED: live file inspection]

```python
@property
def json(self):
    """ If the Content-Type header is application/json or application/json-rpc,
        this property holds the parsed content of the request body. Only requests
        smaller than MEMFILE_MAX are processed to avoid memory exhaustion.
        Invalid JSON raises a 400 error response.
    """
    ctype = self.environ.get('CONTENT_TYPE', '').lower().split(';')[0]
    if ctype in ('application/json', 'application/json-rpc'):
        b = self._get_body_string(self.MEMFILE_MAX)
        if not b: return None
        try:
            return json_loads(b)
        except (ValueError, TypeError):
            raise HTTPError(400, 'Invalid JSON')
    return None
```

**Key behaviors — all confirmed:**

1. **Wrong or missing `Content-Type`** (e.g., `text/plain`, no header): `request.json` returns `None`
   silently — it does NOT raise. The handler's `if not body:` guard catches this case and returns 400.

2. **Valid JSON, valid `Content-Type`**: returns the parsed Python object (dict, list, etc.).

3. **Invalid JSON with `Content-Type: application/json`**: bottle raises `HTTPError(400, 'Invalid JSON')`
   internally. This surfaces as a 400 to the client. The handler never sees this — bottle handles it
   before calling the route function. The planner does NOT need to wrap `request.json` in a try/except
   for JSON parse failures; bottle handles those itself.

4. **Empty body with `Content-Type: application/json`**: returns `None` (the `if not b: return None`
   branch). The `if not body:` guard catches this → 400.

**Implication for D-07 guard pattern** — the handler needs exactly two guards:
```python
body = bottle.request.json
if not body or not isinstance(body, dict):
    return HTTPResponse(body="Bad request", status=400)
```
(bottle already handles invalid-JSON → 400 automatically via HTTPError raise; the handler only needs
to guard for None/wrong-type body.)

**Existing in-repo pattern** (`webhook.py:128-135`, `controller.py:213-228`) [VERIFIED: codebase]:
```python
try:
    body = request.json
except (ValueError, json.JSONDecodeError):
    return HTTPResponse(status=400, body="Invalid JSON")
if not body:
    return HTTPResponse(status=400, body="Empty body")
```
The webhook handler wraps in `try/except (ValueError, json.JSONDecodeError)` as a belt-and-suspenders
guard. Since bottle raises `HTTPError` (not `ValueError`) on bad JSON, this try/except is effectively
unreachable for JSON parse failures — but it mirrors the existing pattern. The planner may choose to
follow the webhook pattern verbatim (belt-and-suspenders) or rely on bottle's built-in HTTPError.
Either is correct; consistency with webhook.py (which is the same in-repo precedent) is preferred.

### RQ-2: webtest body-POST helper (D-11)

**Source:** `src/python/tests/integration/test_web/test_handler/test_webhook.py` — the in-repo
integration tests for the webhook POST handler [VERIFIED: codebase]

```python
# Confirmed usage pattern in this repo (test_webhook.py:29, 40, 48, etc.):
resp = self.test_app.post_json("/server/webhook/sonarr", body)
resp = self.test_app.post_json("/server/webhook/sonarr", body, expect_errors=True)
```

`test_app.post_json(url, dict)` is the **confirmed** webtest helper for posting a JSON body. It:
- Serializes the dict as JSON
- Sets `Content-Type: application/json`
- Returns a webtest response with `.status_int`, `.html`, etc.
- With `expect_errors=True`, does not raise on 4xx/5xx — required for testing 400/404 paths.

**webtest 405 behavior:** When a POST route exists at `/server/config/set` and a GET request is sent
to the same path, bottle returns **405 Method Not Allowed** (because the route exists but the method
doesn't match). webtest surfaces this as `resp.status_int == 405`. When the old path
(`/server/config/set/section/key/value`) is hit with GET after the route is deleted, bottle returns
**404** (route not found). Tests asserting D-02 should cover both paths.

**Integration test migration pattern:**
```python
# Before (GET)
resp = self.test_app.get("/server/config/set/general/debug/True")

# After (POST JSON) — directly mirroring test_webhook.py
resp = self.test_app.post_json("/server/config/set", {"section": "general", "key": "debug", "value": "True"})
self.assertEqual(200, resp.status_int)
```

### RQ-3: Angular RestService extension (D-10)

**Source:** `src/angular/src/app/services/utils/rest.service.ts:58-64` and all callers [VERIFIED: codebase]

Current `RestService.post(url: string)` signature sends `null` body:
```typescript
public post(url: string): Observable<WebReaction> {
    return this._http.post(url, null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

**All callers of `RestService.post` (exhaustive, verified):**
- `model-file.service.ts:61` — `this._restService.post(url)` (queue)
- `model-file.service.ts:74` — `this._restService.post(url)` (stop)
- `model-file.service.ts:87` — `this._restService.post(url)` (extract)
- `server-command.service.ts:26` — `this._restService.post(this.RESTART_URL)` (restart)

All four existing callers pass only `url` — no body argument. An optional `body?` parameter is the
clean extension:

```typescript
public post(url: string, body?: object): Observable<WebReaction> {
    return this._http.post(url, body ?? null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

`body ?? null` preserves existing behavior for the four callers that pass no body — `HttpClient.post`
sends `null` (no body, no `Content-Type`). When a body object is passed, Angular's `HttpClient`
automatically sets `Content-Type: application/json` and serializes the body.

**`responseType: 'text'` compatibility:** The response-type option applies to the _response_ body,
not the request body. Sending a JSON request body while receiving a text response is fully supported
by `HttpClient`. The existing `WebReaction` pipeline (map/catchError/shareReplay) is unaffected.

**ConfigService.set change:** Replace:
```typescript
const valueEncoded = encodeURIComponent(encodeURIComponent(valueStr));
const url = this.CONFIG_SET_URL(section, option, valueEncoded);
const obs = this._restService.sendRequest(url);
```
With:
```typescript
const obs = this._restService.post("/server/config/set", {section, key: option, value: valueStr});
```
`CONFIG_SET_URL` constant (lines 20-22) is deleted. `sendRequest` call replaced by `post` with body.
All other logic in `set()` (pre-flight guards, optimistic update on success) is unchanged.

**Note on BulkCommandService:** `src/angular/src/app/services/server/bulk-command.service.ts:118`
already uses `this._http.post(url, body)` directly (not via RestService) — confirms that Angular's
HttpClient JSON body POST is an established in-repo pattern. BulkCommandService is not affected by
this phase.

### RQ-4: Playwright `page.request.post` with JSON body (D-13)

**Source:** Playwright `^1.48.0` documentation pattern; in-repo usage at
`src/e2e/tests/fixtures/seed-state.ts:48` and `dashboard.page.spec.ts:257` [VERIFIED: codebase]

Playwright's `APIRequestContext.post(url, options)` accepts:
```typescript
await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '100' }
});
```
When `data` is an object, Playwright automatically serializes it as JSON and sets
`Content-Type: application/json`. [ASSUMED from Playwright docs — consistent with CONTEXT.md D-13 language]

**Settings.page.ts migration pattern (confirmed 7 helpers to update):**
```typescript
// Before (GET, with encodeURIComponent)
const response = await this.page.request.get('/server/config/set/sonarr/enabled/true');

// After (POST JSON, no encoding)
const response = await this.page.request.post('/server/config/set', {
    data: { section: 'sonarr', key: 'enabled', value: 'true' }
});
```

**seed-state.ts CONFIG_SET helper:** The current constant on line 26-27 builds a GET URL:
```typescript
const CONFIG_SET = (section: string, key: string, value: string) =>
    `/server/config/set/${section}/${key}/${encodeURIComponent(value)}`;
```
This is used by `setRateLimit` (line 72) which calls `expectOk(page, CONFIG_SET(...), 'GET')`.
The `expectOk` helper already dispatches based on method (lines 45-56). Migration: change
`CONFIG_SET` to a function that returns `{url, body}` or restructure `setRateLimit` to call
`page.request.post` directly with a data object.

**dashboard.page.spec.ts lines 277 and 308** — two inline `page.request.get` calls for rate_limit
throttle/restore that bypass settings.page.ts and seed-state.ts helpers. Both must be updated
directly.

### RQ-5: Rate-limit decorator compatibility (D-08)

**Source:** `src/python/web/rate_limit.py` [VERIFIED: codebase]

```python
def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R | HTTPResponse:
    with lock:
        now = time.time()
        # ... sliding window logic ...
    return func(*args, **kwargs)
```

The `rate_limit` decorator is **completely method-agnostic**. It wraps any callable; it does not
inspect `bottle.request.method` or URL structure. The wrapped function receives whatever args
bottle passes through route matching. For the new POST handler with no path params, bottle calls
`__handle_set_config()` with no positional args — the decorator's `*args`/`**kwargs` pass-through
works identically.

The existing unit test `test_set_config_rate_limited_at_60_per_60s` in
`test_config_handler.py:376-403` calls the wrapped handler with keyword args
`(section="lftp", key="key{}".format(i), value="val")`. Under the new POST signature (no path
params), the handler takes no args — the test must be updated to call the rate-limited handler
with no args (but with `bottle.request` mocked to provide a JSON body).

### RQ-6: Auth/redaction posture (D-09)

**Source:** `src/python/web/web_app.py:83-141` — `before_request` hook [VERIFIED: codebase]

The auth hook runs on **all** `/server/*` requests before any handler function executes. It checks:
1. Host header (if `general.allowed_hostname` configured)
2. Paths exempt from Bearer auth: `/server/stream`, `/server/status`, `/server/webhook/` prefix
3. Bearer token validation

`/server/config/set` is **not** in `_AUTH_EXEMPT_PATHS` or `_AUTH_EXEMPT_PREFIXES`. Changing the
method from GET to POST does NOT affect the `before_request` hook — it is path-based, not method-based.
The new POST route inherits identical auth behavior from the hook. No code change needed in
`web_app.py`.

**SEC-02 redaction (config GET):** The secret-redaction behavior is in `__handle_get_config` and
`SerializeConfig.config`. The config-set route is a separate handler. This phase only modifies
`__handle_set_config` and its route registration — `__handle_get_config`, `SerializeConfig`, and
the redaction tests are untouched. [VERIFIED: config.py:87-90]

### RQ-7: Coverage risk and encoding test replacement (D-11)

**Lines currently covered only by GET-path tests** (will need new POST-path coverage):

**In `test_config.py` (integration):**
- `config.py:26-29` — route registration block (removed; no longer needs covering; replaced by
  new `add_post_handler` registration line)
- `config.py:92-105` — `__handle_set_config` body (currently covered by 7 `test_app.get` calls;
  will be covered by equivalent `test_app.post_json` calls)
- `config.py:94` — `unquote(value)` (DELETED entirely — no replacement needed; this line ceases to
  exist)

**In `test_config_handler.py` (unit):**
- `test_set_url_decodes_value` (line 76-82) — tests the `unquote()` behavior (section/key are plain;
  value is `quote("/path/with spaces")`; asserts `set_property` called with unquoted value).
  **Replaced by:** a raw-value test that passes a value with spaces directly in the JSON body and
  asserts `set_property` is called with the raw (non-decoded) string.
- `test_set_value_with_slashes` (line 84-90) — tests that double-encoded slashes survive the URL
  decode. **Replaced by:** a test that passes `"/remote/path/to/dir"` directly in the JSON body
  and asserts it reaches `set_property` verbatim.

**New coverage needed (D-07 malformed-body paths — currently zero coverage):**
- Body is `None` / wrong content-type → 400
- Body is a non-dict JSON value (e.g., JSON array `[]`) → 400
- Body missing required field (`section`, `key`, or `value`) → 400
- Non-string `section`/`key` (array/object/number) → 400, never 500 (FINDING 1)
- Invalid JSON with `application/json` → 400 via bottle's HTTPError (FINDING 3)
- Legacy route removal (FINDING 2 — split, not "either"): OLD value-bearing GET path `/server/config/set/general/debug/True` → **404**; NEW bare GET `/server/config/set` → **405**

These new tests add lines that did not exist before — they can only raise coverage. The planner should
confirm `fail_under ≥ 88` holds by ensuring every new handler line is covered.

**Karma (Angular) coverage risk:** The existing `config.service.spec.ts` currently asserts GET URLs
like `httpMock.expectOne("/server/config/set/general/debug/true")`. After migration these assertions
must change to match a POST with a JSON body. `HttpTestingController.expectOne` can match by URL
string alone (the POST to `/server/config/set`) — the body assertion requires `match` with a
predicate or `expectOne({ method: 'POST', url: '/server/config/set' })`. The test file covers all
the branches in `ConfigService.set`; migrating the transport should not reduce branch coverage.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON body parsing with error handling | Custom JSON parse logic | `bottle.request.json` | Bottle handles content-type check, JSON decode, and invalid-JSON 400 automatically |
| JSON POST in webtest | `test_app.post(url, params=json.dumps(...), content_type='application/json')` | `test_app.post_json(url, dict)` | `post_json` is the webtest canonical helper; confirmed in-repo precedent (test_webhook.py) |
| Angular JSON request body | `HttpHeaders` + manual JSON.stringify | `HttpClient.post(url, body, {responseType: 'text'})` | HttpClient serializes object bodies as JSON and sets Content-Type automatically |
| Playwright JSON POST | `page.request.post(url, { body: JSON.stringify(...), headers: {'Content-Type': 'application/json'} })` | `page.request.post(url, { data: {...} })` | `data` option auto-serializes and sets Content-Type |
| Rate limiting | New per-method rate limit logic | Existing `rate_limit(60, 60.0)` decorator | Method-agnostic; wraps POST handler identically |

---

## Common Pitfalls

### Pitfall 1: `bottle.request.json` returning None silently on wrong Content-Type

**What goes wrong:** If a client POSTs without `Content-Type: application/json` (e.g., form-encoded
or plain text), `bottle.request.json` returns `None` without raising or logging. If the handler does
not guard for `None`, it will `KeyError` or `AttributeError` on `body.get("section")` — resulting
in a 500, not a 400.
**Root cause:** Bottle's `request.json` is content-type-gated. Wrong content-type = silently None.
**How to avoid:** Always guard with `if not body or not isinstance(body, dict): return HTTPResponse(status=400)` immediately after reading `request.json`. This is the pattern in webhook.py and controller.py.
**Warning signs:** A test that posts with wrong content-type and expects 400 but gets 500.

### Pitfall 2: `test_set_empty_value` status code change (D-06) — must be intentional

**What goes wrong:** The existing integration test asserts `404` for the empty-value case:
```python
resp = self.test_app.get("/server/config/set/lftp/remote_path/", expect_errors=True)
self.assertEqual(404, resp.status_int)
```
Under the new POST handler, empty `value` in the body → 400 (D-06). If the planner updates the
test to assert 400 but forgets the documented rationale, a future reviewer may flag it as wrong.
**How to avoid:** Add a comment in the test explaining the intentional 404→400 refinement per D-06.

### Pitfall 3: Angular `config.service.spec.ts` `expectOne` URL matching

**What goes wrong:** After migration, `httpMock.expectOne("/server/config/set/general/debug/true")`
will fail — the request is now a POST to `/server/config/set` with no URL params. If tests are not
updated to match the POST URL (and optionally the body), Angular's `HttpTestingController` throws
`Error: Expected one matching request for criteria "/server/config/set/general/debug/true", found none.`
**How to avoid:** Update `httpMock.expectOne` to match `"/server/config/set"` (the POST URL) or use
a request-matcher predicate that asserts both the URL and the body fields.
**Warning signs:** All Angular spec tests in the "should send correct GET requests" test fail.

### Pitfall 4: `seed-state.ts` `setRateLimit` helper — inline GET call, not via SettingsPage

**What goes wrong:** `seed-state.ts:71-73` has `setRateLimit` calling `expectOk(page, CONFIG_SET(...), 'GET')`.
The `CONFIG_SET` constant builds a GET URL. This is separate from the `settings.page.ts` helpers.
If only `settings.page.ts` is updated and `seed-state.ts` is forgotten, the E2E rate-limit seeding
will break — affecting the STOPPED seed scenario and any test relying on it.
**How to avoid:** Update both `seed-state.ts` (lines 26-27 constant + line 72 caller) and
`settings.page.ts` in the same commit.

### Pitfall 5: `dashboard.page.spec.ts` inline `page.request.get` calls (lines 277, 308)

**What goes wrong:** These two calls are NOT in a page object or fixture — they are inline in the
spec body. They will break as soon as the GET route is removed. They are easy to miss in a code
search that only looks at `settings.page.ts` and `seed-state.ts`.
**How to avoid:** After updating page objects, grep for `config/set` across the entire `src/e2e/`
tree as a final check: `grep -rn "config/set" src/e2e/`

### Pitfall 6: Rate-limit unit test calling convention change

**What goes wrong:** `test_set_config_rate_limited_at_60_per_60s` calls the wrapped handler with
keyword args `(section=..., key=..., value=...)` because the GET handler took path params. The
new POST handler takes no args. If the test is migrated to keyword-arg calls, Python raises
`TypeError: __handle_set_config() got unexpected keyword argument`.
**How to avoid:** Update the rate-limit unit test to: (a) mock `bottle.request` with a `.json`
property returning the desired dict, and (b) call `rate_limited()` with no arguments.

### Pitfall 7: The `unquote` import may be left orphaned

**What goes wrong:** `config.py:5` imports `from urllib.parse import urlparse, urljoin, unquote`.
After deleting `unquote(value)` from `__handle_set_config`, if `unquote` is not used elsewhere
in the file, ruff will flag it as `F401 imported but unused` — failing the CI lint gate.
**How to avoid:** After deleting the `unquote` call, check whether `unquote` is used anywhere
else in `config.py`. If not, remove it from the `from urllib.parse import ...` line. (Currently
`urlparse` and `urljoin` are used in `_validate_url` and `_sanitize_redirect_location` — those
stay. Only `unquote` needs removal.)
**Warning signs:** `ruff check src/python/` reports `F401` for `unquote`.

---

## Code Examples

### Pattern 1: Backend POST handler (mirroring webhook.py)

```python
# Source: src/python/web/handler/webhook.py:128-138 (in-repo precedent)
# and bottle venv inspection for request.json behavior
def __handle_set_config(self) -> HTTPResponse:
    try:
        body = bottle.request.json
    except (ValueError, json.JSONDecodeError):
        return HTTPResponse(body="Invalid request body", status=400)

    if not body or not isinstance(body, dict):
        return HTTPResponse(body="Invalid request body", status=400)

    section = body.get("section")
    key = body.get("key")
    value = body.get("value")

    # FINDING 1: reject non-string/empty section|key BEFORE any config lookup —
    # a truthy non-string would reach has_section/getattr/has_property (str-expecting)
    # and raise TypeError → uncaught 500/DoS.
    if not isinstance(section, str) or not section or not isinstance(key, str) or not key:
        return HTTPResponse(body="Invalid request body", status=400)

    # value="" is the D-06 case — treat as 400
    if value is None or str(value) == "":
        return HTTPResponse(body="Invalid request body", status=400)

    value_str = str(value)

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

**Route registration change** (config.py lines 26-29, replacing GET with POST):
```python
# REMOVE:
# web_app.add_handler(
#     "/server/config/set/<section>/<key>/<value:re:.+>",
#     rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
# )

# ADD:
web_app.add_post_handler(
    "/server/config/set",
    rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
)
```

### Pattern 2: Integration test (mirroring test_webhook.py)

```python
# Source: src/python/tests/integration/test_web/test_handler/test_webhook.py:29
def test_set_good(self):
    self.assertEqual(None, self.context.config.general.debug)
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": "general", "key": "debug", "value": "True"}
    )
    self.assertEqual(200, resp.status_int)
    self.assertEqual(True, self.context.config.general.debug)

def test_set_empty_value(self):
    # D-06: empty value is now 400 (was 404 under GET route-miss; intentional refinement)
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": "lftp", "key": "remote_path", "value": ""},
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)

def test_set_malformed_body_wrong_content_type(self):
    # D-07: wrong content-type → bottle.request.json returns None → 400
    resp = self.test_app.post(
        "/server/config/set",
        params="not-json",
        content_type="text/plain",
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)

def test_set_invalid_json_correct_content_type(self):
    # D-07 / FINDING 3: malformed JSON WITH application/json → bottle's own
    # HTTPError(400) fires before the handler. No handler code services this path.
    resp = self.test_app.post(
        "/server/config/set",
        params='{bad json',
        content_type="application/json",
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)

def test_set_non_string_section(self):
    # FINDING 1: non-string section → 400, NEVER 500 (no TypeError/DoS)
    resp = self.test_app.post_json(
        "/server/config/set",
        {"section": ["general"], "key": "debug", "value": "True"},
        expect_errors=True
    )
    self.assertEqual(400, resp.status_int)
    self.assertNotEqual(500, resp.status_int)

def test_old_value_bearing_path_returns_404(self):
    # D-02 / FINDING 2: the OLD value-bearing path is unregistered → GET = exactly 404.
    # (405 would mean a value-bearing route shape survived under another method.)
    resp = self.test_app.get(
        "/server/config/set/general/debug/True",
        expect_errors=True
    )
    self.assertEqual(404, resp.status_int)

def test_bare_path_get_returns_405(self):
    # D-02 / FINDING 2: the NEW bare path is POST-only → GET = exactly 405 (not 404).
    resp = self.test_app.get("/server/config/set", expect_errors=True)
    self.assertEqual(405, resp.status_int)
```

### Pattern 3: Unit test (handler called directly, bottle.request mocked)

```python
# Source: src/python/tests/unittests/test_web/test_handler/test_controller_handler.py:151-156
# (in-repo pattern for mocking bottle.request.json in unit tests)
from unittest.mock import patch, MagicMock

def test_set_valid_returns_200(self):
    self.mock_config.has_section.return_value = True
    mock_inner = MagicMock()
    mock_inner.has_property.return_value = True
    self.mock_config.lftp = mock_inner

    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = {"section": "lftp", "key": "remote_address", "value": "192.168.1.1"}
        response = self.handler._ConfigHandler__handle_set_config()

    self.assertEqual(200, response.status_code)

def test_set_raw_value_with_slashes_through_body(self):
    # Replaces test_set_value_with_slashes (D-04: no URL decode, value arrives verbatim)
    self.mock_config.has_section.return_value = True
    mock_inner = MagicMock()
    mock_inner.has_property.return_value = True
    self.mock_config.lftp = mock_inner

    with patch('web.handler.config.bottle') as mock_bottle:
        mock_bottle.request.json = {"section": "lftp", "key": "remote_path", "value": "/remote/path/to/dir"}
        self.handler._ConfigHandler__handle_set_config()

    mock_inner.set_property.assert_called_once_with("remote_path", "/remote/path/to/dir")
```

### Pattern 4: Angular RestService extension

```typescript
// Source: src/angular/src/app/services/utils/rest.service.ts:58-64 (current)
// Extended per D-10; existing callers unaffected (body defaults to null)
public post(url: string, body?: object): Observable<WebReaction> {
    return this._http.post(url, body ?? null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

```typescript
// Source: src/angular/src/app/services/settings/config.service.ts:65-68 (current set())
// Replace double-encode + sendRequest with direct post
const obs = this._restService.post("/server/config/set", {section, key: option, value: valueStr});
```

### Pattern 5: Angular spec migration (HttpTestingController)

```typescript
// Source: src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts:193
// Before:
httpMock.expectOne("/server/config/set/general/debug/true").flush("{}");

// After (POST to bare URL, body not asserted by default — can use matcher if needed):
httpMock.expectOne("/server/config/set").flush("{}");
// OR with method+url matcher for stricter assertion:
httpMock.expectOne(req => req.method === "POST" && req.url === "/server/config/set").flush("{}");
```

### Pattern 6: E2E curl (setup_seedsyncarr.sh)

```bash
# Source: src/docker/test/e2e/configure/setup_seedsyncarr.sh:34 (the POST exemplar to mirror)
# Before:
curl -sSf "http://myapp:8800/server/config/set/general/debug/true" \
  || { echo "ERROR: failed to set general/debug" >&2; exit 1; }

# After (mirrors restart call at line 34):
curl -sSf -X POST \
  -H 'Content-Type: application/json' \
  -d '{"section":"general","key":"debug","value":"true"}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set general/debug" >&2; exit 1; }

# Double-encoded path values become plain strings in the body:
# Before: curl -sSf "http://myapp:8800/server/config/set/lftp/local_path/%252Fdownloads"
# After:  -d '{"section":"lftp","key":"local_path","value":"/downloads"}'
```

### Pattern 7: Playwright page.request.post with data

```typescript
// Source: Playwright ^1.48.0 — page.request.post with data option
// Before (settings.page.ts, e.g. enableSonarr):
const response = await this.page.request.get('/server/config/set/sonarr/enabled/true');

// After:
const response = await this.page.request.post('/server/config/set', {
    data: { section: 'sonarr', key: 'enabled', value: 'true' }
});

// seed-state.ts setRateLimit:
// Before: await expectOk(page, CONFIG_SET('lftp', 'rate_limit', bytesPerSec), 'GET');
// After: call page.request.post directly (or update expectOk to handle data payload)
const res = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: bytesPerSec }
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GET with path params (`/config/set/section/key/value`) | POST with JSON body (`/config/set`) | Phase 111 (this phase) | Credentials removed from URL path, access logs, browser history |
| Double `encodeURIComponent` on Angular side + `unquote` on Python side | Raw value in JSON body | Phase 111 | Encoding foot-gun eliminated; values arrive verbatim |
| Route regex `<value:re:.+>` prevents empty values (→ 404) | Handler guards check empty value (→ 400) | Phase 111 | More correct semantics: empty is a validation failure, not a route miss |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Playwright `page.request.post(url, { data: obj })` auto-sets `Content-Type: application/json` | RQ-4, Pattern 7 | If Playwright does not auto-set content-type, backend `bottle.request.json` returns None → 400; tests fail; fix: add `headers: {'Content-Type': 'application/json'}` to the options |

**All other claims in this research are VERIFIED via live codebase inspection or bottle venv file reading.**

---

## Open Questions (RESOLVED)

1. **Angular `config.service.spec.ts` body assertion granularity**
   - What we know: `httpMock.expectOne(url)` matches by URL string; for POST it matches the POST to `/server/config/set`.
   - What's unclear: Whether the planner wants body-field assertions (`req.body.section === "general"`) in the spec, or URL-only is sufficient.
   - Recommendation: URL-only matching is consistent with the existing spec style (which never asserted URL params beyond the full URL string); body assertion is a discretionary enhancement.

2. **`seed-state.ts` CONFIG_SET helper refactor shape**
   - What we know: The helper currently returns a URL string; `expectOk` dispatches on method string.
   - What's unclear: Whether to (a) convert `CONFIG_SET` to return `{url, body}` and update `expectOk`, or (b) inline `page.request.post` calls directly at each call site.
   - Recommendation: Since `setRateLimit` is the only consumer of `CONFIG_SET`, inline the call directly in `setRateLimit` and delete the `CONFIG_SET` constant — simpler than restructuring `expectOk`.

---

**Resolutions (locked during Phase 111 planning revision):**

- **Q1 (spec body-assertion granularity):** RESOLVED — use URL-only `expectOne('/server/config/set')` matching per the existing spec style for the bulk of migrated tests, PLUS at least one mandatory body-shape assertion (`expect(req.request.body).toEqual({section, key, value})`) on a migrated test to pin the `{section, key, value}` contract. See Plan 02 Task 3 acceptance criteria (the body-shape assertion is required, not optional).
- **Q2 (`seed-state.ts` CONFIG_SET helper refactor shape):** RESOLVED — inline `page.request.post` directly in `setRateLimit`; the `CONFIG_SET` constant is deleted (single consumer, so restructuring `expectOk` is unwarranted). See Plan 03 Task 2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| bottle 0.13.4 | Backend handler | ✓ | 0.13.4 (pinned) | — |
| webtest 3.0.7+ | Integration tests | ✓ | `^3.0.7` (pinned) | — |
| @playwright/test | E2E tests | ✓ | `^1.48.0` (pinned) | — |
| Angular HttpClient | Angular service | ✓ | Angular 21 | — |

All dependencies confirmed available. No install step required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest `^9.0.3` + webtest `^3.0.7` |
| Python config | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Python quick run | `cd src/python && poetry run pytest tests/integration/test_web/test_handler/test_config.py tests/unittests/test_web/test_handler/test_config_handler.py -v` |
| Python full suite | `make run-tests-python` (containerized) + `ruff check src/python/` |
| Angular framework | Karma `^6.4.4` + Jasmine |
| Angular config | `src/angular/karma.conf.js` |
| Angular quick run | `cd src/angular && npm test` |
| E2E framework | Playwright `^1.48.0` |
| E2E full run | `make run-tests-e2e` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | POST with JSON body sets config | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_good -xvs` | ✅ (migrated) |
| CFG-01 | Angular sends POST not GET | Angular unit | `npm test` — `config.service.spec.ts` "should send a GET on a set config option" → renamed | ✅ (migrated) |
| CFG-02 | GET path → 404/405 | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_get_old_path_returns_404 -xvs` | ❌ Wave 0 |
| CFG-03 | E2E round-trip over POST | E2E | `make run-tests-e2e` — `settings-fields.spec.ts` persist tests | ✅ (migrated) |
| CFG-04 | On-disk format unchanged | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_good -xvs` (verifies value actually persisted) | ✅ (migrated) |
| D-06 | Empty value → 400 | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_empty_value -xvs` | ✅ (migrated, status changes 404→400) |
| D-07 | Malformed body → 400 | integration + unit | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_malformed_body -xvs` | ❌ Wave 0 |
| D-08 | Rate limit still 60/60s | unit | `pytest tests/unittests/test_web/test_handler/test_config_handler.py::TestConfigHandlerRateLimit -xvs` | ✅ (migrated) |

### Sampling Rate

- **Per task commit:** `cd src/python && poetry run pytest tests/integration/test_web/test_handler/test_config.py tests/unittests/test_web/test_handler/test_config_handler.py -v` + `ruff check src/python/`
- **Per wave merge:** `make run-tests-python` + `make run-tests-angular`
- **Phase gate:** Full suite green (`make run-tests-python` + `make run-tests-angular` + `make run-tests-e2e`) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_get_old_path_returns_404` — covers CFG-02 (D-02 route removal)
- [ ] `tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_malformed_body` — covers D-07 (wrong content-type → 400)
- [ ] `tests/integration/test_web/test_handler/test_config.py::TestConfigHandler::test_set_missing_fields` — covers D-07 (absent required field → 400)
- [ ] `tests/unittests/test_web/test_handler/test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_with_slashes_through_body` — replaces `test_set_value_with_slashes`
- [ ] `tests/unittests/test_web/test_handler/test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_decoded_through_body` — replaces `test_set_url_decodes_value`
- [ ] `tests/unittests/test_web/test_handler/test_config_handler.py::TestConfigHandlerSet::test_set_none_body_returns_400` — covers D-07 (None body)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Existing `before_request` Bearer token hook — unchanged |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | Single-user tool |
| V5 Input Validation | Yes | Handler validates section/key/value from body; missing fields → 400 |
| V6 Cryptography | No | Transport change only; Fernet on-disk untouched |

### Known Threat Patterns for this migration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credentials in URL / access log | Info Disclosure | **This phase eliminates it**: POST JSON body removes value from URL |
| Malformed JSON body causing 500 | Tampering / DoS | Bottle auto-400 on invalid JSON; handler guards None body |
| Body size exhaustion | DoS | Bottle `MEMFILE_MAX` caps body size before `request.json` processing |
| Auth bypass via method change | Elevation of Privilege | `before_request` hook is path-based, not method-based — POST inherits same auth |

---

## Sources

### Primary (HIGH confidence — live codebase inspection)

- `src/python/web/handler/config.py` — route registration, `__handle_set_config` implementation
- `src/python/web/web_app.py` — `add_post_handler`, `before_request` auth hook
- `src/python/web/rate_limit.py` — decorator implementation (method-agnostic confirmed)
- `src/python/web/handler/webhook.py` — canonical in-repo JSON body POST handler pattern
- `src/python/web/handler/controller.py:213-228` — second in-repo JSON body pattern
- `src/python/tests/integration/test_web/test_handler/test_config.py` — all 7 GET-based set tests
- `src/python/tests/integration/test_web/test_handler/test_webhook.py` — `post_json` usage (confirmed helper)
- `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` — encoding tests to replace
- `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py:145-156` — `patch('web.handler.config.bottle')` / `mock_request.json` unit-test pattern
- `src/angular/src/app/services/utils/rest.service.ts` — `post()` current signature + all callers confirmed
- `src/angular/src/app/services/settings/config.service.ts` — `CONFIG_SET_URL`, `set()` double-encode flow
- `src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts` — all spec expectations (GET URLs to migrate)
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — all 11 GET calls + restart POST exemplar
- `src/e2e/tests/settings.page.ts` — 7 helpers + stale comment at line 33
- `src/e2e/tests/fixtures/seed-state.ts` — `CONFIG_SET` constant + `setRateLimit` caller
- `src/e2e/tests/dashboard.page.spec.ts:277,308` — 2 inline `page.request.get` calls
- `src/python/pyproject.toml` — webtest `^3.0.7`, bottle `^0.13.4`
- `src/e2e/package.json` — `@playwright/test: ^1.48.0`
- bottle venv `bottle.py:BaseRequest.json` property — confirmed behavior for None/invalid/wrong-content-type cases
- `.planning/milestones/v1.4.0-phases/111-config-set-endpoint-migration/111-CONTEXT.md` — locked decisions D-01..D-13

### Secondary (MEDIUM confidence)

- Playwright `^1.48.0` docs — `page.request.post(url, { data })` auto-sets `Content-Type: application/json` [A1 — verified against Playwright API contract by version match; tagged ASSUMED only for the auto-header behavior]

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Backend implementation: HIGH — bottle behavior confirmed from venv source; in-repo patterns from webhook.py/controller.py
- Angular implementation: HIGH — all callers of `RestService.post` exhaustively located; extension pattern clear
- Integration test helper: HIGH — `post_json` confirmed from in-repo test_webhook.py usage
- E2E curl pattern: HIGH — restart call at `setup_seedsyncarr.sh:34` is exact exemplar
- Playwright `data` option: MEDIUM — one assumption (A1) about auto-Content-Type; low-risk

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable stack, 30-day validity)
