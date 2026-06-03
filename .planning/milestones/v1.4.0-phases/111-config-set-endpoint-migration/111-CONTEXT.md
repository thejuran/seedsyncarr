# Phase 111: Config-Set Endpoint Migration - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

> The user dismissed the gray-area discussion (same signal as Phase 110), indicating
> comfort with spec-grounded defaults rather than re-deciding mechanics the requirements
> (CFG-01..04) and design-spec decision D-4 already constrain. The decisions below are
> therefore **locked defaults** grounded in REQUIREMENTS.md (CFG-01..04), the approved
> design spec (D-4), the Phase 110 finding HR-01, and direct reading of the three named
> code surfaces. The planner/researcher implement to these.

<domain>
## Phase Boundary

The **one breaking HTTP-contract change** of the v1.4.0 milestone: migrate
`/server/config/set` from a **GET request with credential-bearing URL path segments** to a
**POST request with a JSON body** (`{section, key, value}`), and **fully delete** the legacy
GET path (hard cutover — no dual-support). After this phase, no config value (including
`lftp/remote_password`) ever travels in a URL, so credentials stop landing in server access
logs, browser history, and reverse-proxy logs.

Spans three layers, all named in finding HR-01:
- **Backend** — `src/python/web/handler/config.py` (the route + handler) and its tests.
- **Angular** — `src/angular/src/app/services/settings/config.service.ts` (`ConfigService.set`)
  and the supporting `RestService`, plus the service spec.
- **E2E** — `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (11 `curl` config-set calls)
  and the Playwright page objects (`src/e2e/tests/settings.page.ts` and any other spec that
  hits `/server/config/set/...`).

**On-disk persisted config format is UNCHANGED (CFG-04).** This is a transport-layer change
only — `Config.set_property`, the persist format (plaintext + Fernet-encrypted), and config
loading are all untouched. No user migration step.

**No release/tag/version work** — the single `v1.4.0` tag is a milestone-end action on branch
`launch-hardening` after the NAS walkthrough + CI green + maintainer sign-off, never inside a
phase.

</domain>

<decisions>
## Implementation Decisions

### Endpoint path shape (HTTP contract)
- **D-01:** The new route is a **bare `POST /server/config/set`** — *no* path parameters.
  All three fields (`section`, `key`, `value`) travel in the JSON request body. This satisfies
  CFG-01/CFG-02 maximally: nothing credential-bearing appears in the URL at all (not even the
  section/key). Registered via the existing `WebApp.add_post_handler` (`web_app.py:187`).
- **D-02:** The legacy `GET /server/config/set/<section>/<key>/<value:re:.+>` route is
  **removed entirely** — both the `web_app.add_handler(...)` registration block
  (`config.py:26-29`) and the GET-path assumptions in tests. After removal, a `GET` to the old
  path returns bottle's default **404** (route no longer registered); a `GET` to the new bare
  path returns **405** (method not allowed — POST route exists, GET doesn't). Either is an
  acceptable "credential-leaking path is gone" signal per CFG-02. Dual-support GET+POST is
  **explicitly rejected** (REQUIREMENTS.md "Out of Scope"; design-spec D-4).

### Request body & parsing
- **D-03:** Request body is JSON: `{"section": "...", "key": "...", "value": ...}`. The handler
  reads it via bottle's parsed JSON body (`bottle.request.json`). `value` is accepted as sent
  and coerced to its string form for `set_property` (matching today's behavior where the handler
  ultimately hands a string to `inner_config.set_property`). Note the field name in the body is
  `key` (CFG-01's contract wording), mapping to what the handler internally calls the property
  name — keep the public body contract as `{section, key, value}`.
- **D-04 (drop double-encoding entirely):** The GET path's double-encode dance exists **only**
  to survive URL path segments — Angular did `encodeURIComponent(encodeURIComponent(value))`
  (`config.service.ts:66`) and the backend did `unquote(value)` (`config.py:94`) on top of
  bottle's own path decode. With a JSON body there is **no URL encoding at all**: Angular sends
  the **raw** value in the body, and the backend uses it **directly** — the `unquote` call and
  both `encodeURIComponent` calls are deleted. This is the cleanest correct outcome and removes
  a long-standing foot-gun.

### Validation & status-code contract (preserve observable behavior — CFG-04 spirit)
- **D-05:** Preserve the existing **validation status codes** so already-supported behavior is
  unchanged:
  - Missing/unknown `section` → **404** (`config.py:96-97`, "There is no section ...").
  - Missing/unknown `key` → **404** (`config.py:99-100`, "Section ... has no option ...").
  - `set_property` raises `ConfigError` (e.g. whitespace-only value, out-of-range int) → **400**
    with the existing message (e.g. `"Bad config: Lftp.remote_path is empty"`).
  - Valid set → **200** with the existing `"{section}.{key} set to {value}"` body.
- **D-06 (empty-value case — the one semantic that *must* be handled explicitly):** Under the
  GET route, an **empty** value was a **404** because the `<value:re:.+>` regex refused to match
  an empty segment (route miss), so the handler never ran (integration test `test_set_empty_value`
  asserts 404 for `.../remote_path/` and 400 for `.../remote_path/%20%20`). With a JSON body the
  regex is gone, so the handler now receives the empty/missing value directly. **Decision:**
  treat a missing-or-empty `value` field as a **400 validation error** (it is malformed input,
  not a missing route), and let whitespace-only continue to surface the existing `ConfigError`
  **400**. The empty-value integration test is **updated from 404→400** as an intentional,
  documented contract refinement — empty value is now a body-validation failure, which is more
  correct than the old route-miss artifact. (Whitespace-only stays 400, unchanged.)

### Malformed-body robustness
- **D-07:** Malformed POST input returns a **generic 400** with a short client-safe message;
  any internal detail is logged server-side, never returned to the client (per global code-quality
  rules — no internal errors/stack traces to end users). Covered cases: body is not valid JSON,
  body is not a JSON object, or a required field (`section`/`key`/`value`) is absent. Missing
  `section`/`key` that *are* present-but-unknown keep their **404** per D-05; absent fields are
  **400** (malformed request, distinct from "well-formed request naming a thing that doesn't
  exist").

### Rate-limiting & cross-cutting parity
- **D-08:** Keep the existing per-route rate-limit decorator `rate_limit(max_requests=60,
  window_seconds=60.0)` wrapping the new POST handler — same protection as the GET route had
  (`config.py:28`). Over-limit → generic 429 (unchanged middleware behavior).
- **D-09:** Auth posture is unchanged — the config-set route stays behind the same auth the
  GET route had; this phase changes the HTTP method/body, not the authn/authz model.

### Angular client
- **D-10:** `RestService` needs a **body-carrying POST** for config-set. The existing
  `RestService.post(url)` sends a `null` body (`rest.service.ts:58-64`); add (or extend to) a
  variant that sends a JSON object body with `Content-Type: application/json`. `ConfigService.set`
  builds `{section, key: option, value}` and posts it — its existing **pre-flight validation**
  (unknown section/option guard, blank-value guard at `config.service.ts:52-63`) and its
  **optimistic local `_config.next(...)` update on success** (`:71-77`) are preserved unchanged.
  Only the transport (URL-building + double-encode → JSON body POST) changes.

### Test migration surface (all must move GET→POST, none deleted)
- **D-11:** Update every test that exercised the GET path to the POST contract, keeping coverage
  equivalent or better (Python `fail_under` ≥ 88 must hold or rise; Karma floors hold or rise):
  - `tests/integration/test_web/test_handler/test_config.py` — ~7 set-config methods
    (`test_set_good`, `test_set_missing_section`, `test_set_missing_option`, `test_set_bad_value`,
    `test_set_empty_value` [404→400 per D-06], `test_set_whitespace`, slash-value case) move from
    `test_app.get(".../config/set/...")` to `test_app.post_json(...)` (or equivalent body POST).
  - `tests/unittests/test_web/test_handler/test_config_handler.py` — `test_set_*` methods
    (`test_set_valid_returns_200`, `test_set_calls_set_property`,
    `test_set_missing_section_returns_404`, `test_set_missing_key_returns_404`,
    `test_set_config_error_returns_400`, and the two encoding tests
    `test_set_url_decodes_value` / `test_set_value_with_slashes`). The two **encoding tests are
    replaced** by raw-value-through-body tests (no decode step exists anymore — D-04).
  - Add **new** coverage for the malformed-body paths (D-07) and the bare-path-GET-rejection
    (D-02) so the new contract's error surface is pinned.
  - `config.service.spec.ts` (Angular) — update to assert a POST with the JSON body, not a GET URL.

### E2E migration surface
- **D-12:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — all **11** `curl -sSf
  "…/server/config/set/<seg>/<seg>/<seg>"` GET calls become `curl -sSf -X POST -H
  'Content-Type: application/json' -d '{"section":...,"key":...,"value":...}'
  "…/server/config/set"` calls. The `/server/command/restart` call already uses `-X POST`
  (line 34) as the in-repo pattern to mirror. The `%252F…` double-encoded path values become
  plain string values in the JSON body (e.g. `local_path` = `/downloads`, no encoding).
- **D-13:** Playwright page objects — `src/e2e/tests/settings.page.ts` (7+
  `page.request.get('/server/config/set/...')` helpers) and any other spec hitting the endpoint
  (`settings-fields.spec.ts`, `fixtures/seed-state.ts`, `dashboard.page.spec.ts` per grep)
  switch to `page.request.post('/server/config/set', { data: {section, key, value} })`. The stale
  inline comment at `settings.page.ts:33` ("because the backend config/set endpoint is GET-only")
  is **removed/corrected** — it is now POST-only.

### Claude's Discretion
- The exact name/signature of the new body-carrying Angular POST helper (extend `RestService.post`
  to take an optional body vs add `postJson`) — planner picks the cleaner fit for existing callers.
- The precise generic 400 message strings for malformed-body cases (D-07), provided they leak no
  internals.
- Whether the backend reads the body via `bottle.request.json` directly or with a small guarded
  helper — provided invalid-JSON yields a clean 400, not a 500.
- The exact test-helper for body POST in the webtest integration suite (`post_json` vs
  `post(..., content_type=...)`), provided the asserted status/behaviour contract in D-05/D-06 holds.
- Whether the unknown-but-present field detail (D-07) distinguishes "not an object" from "missing
  field" in its message — both are 400; granularity is the planner's call.

</decisions>

<specifics>
## Specific Ideas

- The animating concern is **credentials-in-URLs** (HR-01, CRITICAL). The success test a hostile
  reader applies: `grep -r "config/set"` should no longer reveal any path that carries a value —
  and an access-log line for a config save should show only `POST /server/config/set`, never a
  password. Keep that the north star: nothing sensitive in the URL, ever.
- This is the **only** change in the milestone that warrants the minor version bump (breaking HTTP
  contract) — so a clean, total cutover (GET fully gone) is the point. A half-migration that leaves
  the GET path alive would be exactly what the finding flags.
- The backend POST plumbing already exists (`add_post_handler`, `add_delete_handler`) and the
  Angular `RestService.post`/`delete` already exist — this is a *use the existing rails* change,
  not new infrastructure.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope (the locked acceptance contract)
- `.planning/REQUIREMENTS.md` — **CFG-01** (POST JSON body; no credentials in URL/logs), **CFG-02**
  (legacy GET path fully removed → 404/405), **CFG-03** (Settings page saves end-to-end over POST;
  Angular `ConfigService` + E2E setup/page-objects updated; round-trips + persists across reload),
  **CFG-04** (on-disk config format unchanged — plaintext + Fernet — no user migration). Also the
  "Out of Scope" row rejecting dual-support GET+POST.
- `.planning/ROADMAP.md` §"Phase 111: Config-Set Endpoint Migration" — phase goal + CFG-01..04 mapping.
- `docs/superpowers/specs/2026-06-02-launch-hardening-design.md` — approved design spec; **D-4**
  (hard cutover, POST only, GET deleted) is the governing decision for this phase.

### Discovery input (the finding this phase fixes)
- `.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md` §HR-01
  (CRITICAL — config-set credentials travel as URL path segments). Names the exact three locations
  and confirms the E2E setup script as the current integration pattern. Disposition: FOLD → Phase 111.

### Audit baseline (cross-reference, do NOT mutate)
- `.planning/codebase/CONCERNS.md` §Security Considerations / SEC-09 — the prior-art entry for this
  issue. Owned by `/gsd:map-codebase`; cross-reference only.
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md` — for the handler-registration
  convention (`add_*_handler`) and the webtest integration-test patterns the migrated tests follow.

### Code surfaces (the blast radius — read before planning task breakdown)
- `src/python/web/handler/config.py:22-105` — route registration + `__handle_set_config` (the core change).
- `src/python/web/web_app.py:184-191` — `add_handler` / `add_post_handler` / `add_delete_handler`.
- `src/angular/src/app/services/settings/config.service.ts:20-82` — `CONFIG_SET_URL` + `set()`.
- `src/angular/src/app/services/utils/rest.service.ts:41-77` — `sendRequest` (GET), `post`, `delete`.
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh:8-32` — the 11 config-set curl calls.
- `src/e2e/tests/settings.page.ts` (+ `settings-fields.spec.ts`, `fixtures/seed-state.ts`,
  `dashboard.page.spec.ts`) — Playwright config-set request helpers.
- `src/python/tests/integration/test_web/test_handler/test_config.py` &
  `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` — the test contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **POST/DELETE rails already exist.** `WebApp.add_post_handler` (`web_app.py:187`) and
  `add_delete_handler` (`:190`) are present and used elsewhere — the migration registers the new
  route through `add_post_handler`, no new framework plumbing.
- **Angular `RestService.post`/`delete` exist** (`rest.service.ts:58-77`) with the same
  `handleSuccess`/`handleError`/`shareReplay` pipeline as `sendRequest` — extend the POST to carry
  a JSON body; the WebReaction contract is unchanged for `ConfigService` callers.
- **`/server/command/restart` is the in-repo `-X POST` curl exemplar** (`setup_seedsyncarr.sh:34`)
  — the migrated config-set curl calls mirror its shape (add `-H Content-Type` + `-d` body).
- **The rate-limit decorator is reusable as-is** (`rate_limit(60, 60.0)`, `config.py:28`).

### Established Patterns
- Handlers are thin: validate → call `Config`/`inner_config` → return `HTTPResponse` with a status.
  The migrated handler keeps this shape; only the input acquisition (body vs path params) changes.
- The integration suite uses `webtest`'s `test_app.get(...)`; the POST migration uses the
  body-POST equivalent (`post_json` / `post(..., content_type="application/json")`) — confirm the
  exact helper from the webtest version in use during planning.
- Status-code contract is asserted explicitly in tests (200/400/404) — preserve those assertions
  except the single documented empty-value 404→400 refinement (D-06).

### Integration Points
- `ConfigService.set` is called from the Settings UI; its pre-flight guards and optimistic local
  update are the integration contract with the rest of the Angular app — preserved (D-10).
- The E2E setup script bootstraps the *whole* E2E suite's config state; if its config-set calls
  break, every downstream Playwright test fails — so the script + page-object migration (D-12/D-13)
  is on the critical path for CFG-03's "saves end-to-end" + CI-green requirement.

</code_context>

<deferred>
## Deferred Ideas

- **None new in scope.** Dual-support GET+POST is explicitly rejected (REQUIREMENTS.md Out of Scope
  / D-4), not deferred — it must not be built.

### Reviewed Todos (folded)
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.6, area: security) — **folded**: this
  todo *is* Phase 111. Its substance is fully captured by CFG-01..04 and the decisions above; the
  todo can be closed when Phase 111 completes.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.6, area: testing) — **not folded.** This is
  DEFER-WEBOB (REQUIREMENTS.md "Future Requirements") — blocked on an upstream webob release,
  unrelated to the config-set transport change. Stays deferred.

</deferred>

---

*Phase: 111-config-set-endpoint-migration*
*Context gathered: 2026-06-02*
