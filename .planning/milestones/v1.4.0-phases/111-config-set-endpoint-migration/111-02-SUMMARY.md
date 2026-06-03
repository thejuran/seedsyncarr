---
phase: 111-config-set-endpoint-migration
plan: "02"
subsystem: angular-client
tags: [security, http-contract, config, angular, credential-exposure, cfg-01, cfg-03]
completed: "2026-06-02"
duration_minutes: 30

dependency_graph:
  requires:
    - "Plan 01: POST /server/config/set handler (backend POST contract)"
  provides:
    - "RestService.post(url, body?) — optional JSON body POST, four no-body callers unaffected"
    - "ConfigService.set posts {section, key, value} as JSON body to /server/config/set (CFG-01 client side)"
    - "config.service.spec.ts asserts POST contract with mandatory body-shape assertion"
  affects:
    - "Plan 03: E2E setup script + Playwright page objects (downstream consumers)"

tech_stack:
  added: []
  patterns:
    - "body ?? null in RestService.post preserves null-body callers while enabling JSON-body callers"
    - "httpMock.expectOne(r => r.method === 'POST' && r.url === '/server/config/set') method+URL matcher"
    - "expect(req.request.body).toEqual({section, key, value}) mandatory body-shape assertion"

key_files:
  modified:
    - src/angular/src/app/services/utils/rest.service.ts
    - src/angular/src/app/services/settings/config.service.ts
    - src/angular/src/app/tests/unittests/services/settings/config.service.spec.ts

decisions:
  - "Extend RestService.post (not add postJson) — keeps all callers on one method per RESEARCH recommendation; body ?? null preserves four existing no-body callers"
  - "Method+URL matcher form httpMock.expectOne(r => r.method === 'POST' && r.url === '/server/config/set') chosen for all migrated tests — stronger than URL-only, pins the POST contract against accidental GET regression"
  - "Mandatory body-shape assertion applied on the first migrated test (should send a POST on a set config option) with expect(req.request.body).toEqual({section: 'general', key: 'debug', value: 'true'})"

metrics:
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
  tests_migrated: 12
  coverage_stmts: "84.3%"
  coverage_branches: "69.4%"
  coverage_fns: "80.45%"
  coverage_lines: "85.15%"
---

# Phase 111 Plan 02: Config-Set Angular Client Migration Summary

**One-liner:** Angular ConfigService.set now POSTs {section, key, value} as a JSON body to the bare /server/config/set URL — credentials no longer appear in the request URL, closing the client side of CFG-01.

## What Was Built

The Angular client was migrated to match the POST contract established by Plan 01. Three files were modified across three tasks, each committed atomically.

### Task 1: RestService.post extended with optional JSON body (commit 3c27e17)

The `post` method signature changed from `post(url: string)` to `post(url: string, body?: object)`:

```typescript
public post(url: string, body?: object): Observable<WebReaction> {
    return this._http.post(url, body ?? null, {responseType: "text"}).pipe(
        map(this.handleSuccess(url)),
        catchError(this.handleError(url)),
        shareReplay(1)
    );
}
```

The `body ?? null` pattern preserves exact prior behavior (null body, no Content-Type header) for the four existing callers that pass only `url`. When a body object is supplied, `HttpClient.post` auto-serializes it as JSON and sets `Content-Type: application/json`. The WebReaction pipeline is unchanged.

**Four existing no-body callers verified unaffected:**
- `model-file.service.ts:61` — `this._restService.post(url)` (queue)
- `model-file.service.ts:74` — `this._restService.post(url)` (stop)
- `model-file.service.ts:87` — `this._restService.post(url)` (extract)
- `server-command.service.ts:26` — `this._restService.post(this.RESTART_URL)` (restart)

### Task 2: ConfigService.set transport block rewritten (commit e07fed2)

The `CONFIG_SET_URL` template constant was deleted entirely. The transport block inside the `else` branch changed from three lines to one:

```typescript
// BEFORE (deleted):
const valueEncoded = encodeURIComponent(encodeURIComponent(valueStr));
const url = this.CONFIG_SET_URL(section, option, valueEncoded);
const obs = this._restService.sendRequest(url);

// AFTER:
const obs = this._restService.post("/server/config/set", {section, key: option, value: valueStr});
```

The field name mapping is `key: option` — the body field is `key` (per the CFG-01 contract), populated from the method's `option` parameter.

**Preserved unchanged (D-10):**
- Pre-flight validation block: unknown section/option guard and blank-value guard (lines 49-59)
- Optimistic `_config.next(newConfig)` local update on success (lines 63-75)
- `getConfig`, `testSonarrConnection`, `testRadarrConnection` (all use `sendRequest` for GET, unrelated)

No `encodeURIComponent` call remains in `config.service.ts`. The URL carries only `/server/config/set` — no credential-bearing path segments (CFG-01 / D-04).

### Task 3: config.service.spec.ts migrated to POST expectations (commit bad07ab)

All 12 `expectOne` calls that referenced value-bearing GET URLs were migrated:

**Test descriptions renamed:**
- `"should send a GET on a set config option"` → `"should send a POST on a set config option"`
- `"should send correct GET requests on setting config options"` → `"should send correct POST requests on setting config options"`

**Matcher form used for all migrated tests:**
```typescript
httpMock.expectOne(r => r.method === "POST" && r.url === "/server/config/set")
```
This method+URL form pins the POST contract — any accidental regression to GET would immediately fail these tests (stronger than URL-only matching).

**Mandatory body-shape assertion (pinned in the first migrated test):**
```typescript
const req = httpMock.expectOne(r => r.method === "POST" && r.url === "/server/config/set");
expect(req.request.body).toEqual({section: "general", key: "debug", value: "true"});
req.flush("{}");
```

**Pre-flight guard tests (lines ~231, ~251, ~267):** Unchanged. They assert no HTTP request is issued (the `set()` call returns a local Observable without calling RestService). `httpMock.verify()` in `afterEach` enforces this.

**Karma result:**
```
611 SUCCESS
Statements   : 84.3%  (>= 83 floor — held)
Branches     : 69.4%  (>= 68 floor — held)
Functions    : 80.45% (>= 79 floor — held)
Lines        : 85.15% (>= 83 floor — held)
```

## Deviations from Plan

None — the plan executed exactly as written. All acceptance criteria were met on first attempt.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The change is a transport-layer migration of an existing endpoint call.

- T-111-02-01 (credential in URL): fully mitigated — `CONFIG_SET_URL` deleted, both `encodeURIComponent` calls deleted, value travels only in the POST JSON body
- T-111-02-02 (four no-body callers broken): mitigated — `body ?? null` preserves null-body behavior; Karma 611/611 confirms no regression

## Known Stubs

None — `ConfigService.set` is fully wired to `RestService.post` which calls `HttpClient.post`. The transport is end-to-end.

## Self-Check: PASSED
