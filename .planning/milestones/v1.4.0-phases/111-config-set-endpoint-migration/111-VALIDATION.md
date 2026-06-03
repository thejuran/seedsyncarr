---
phase: 111
phase_slug: config-set-endpoint-migration
date: 2026-06-02
source: extracted from 111-RESEARCH.md §"Validation Architecture"
---

# Phase 111: Config-Set Endpoint Migration — Validation Strategy (Nyquist Dimension 8)

> Derived from `111-RESEARCH.md` §"Validation Architecture" + §"Security Domain". This is the
> pre-execution test-coverage contract: what each CFG requirement is proved by, which tests are
> net-new (Wave 0 gaps), and the sampling rate at task / wave / phase boundaries.

## Test Framework

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

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Status |
|--------|----------|-----------|-------------------|--------|
| CFG-01 | POST with JSON body sets config | integration | `pytest .../test_config.py::TestConfigHandler::test_set_good -xvs` | migrated |
| CFG-01 | Angular sends POST not GET | Angular unit | `npm test` — `config.service.spec.ts` (renamed) | migrated |
| CFG-02 | OLD value-bearing GET path → 404 (route unregistered) | integration | `pytest .../test_config.py::TestConfigHandler::test_old_value_bearing_path_returns_404 -xvs` | **Wave 0 (net-new)** |
| CFG-02 | NEW bare path GET → 405 (POST-only route exists) | integration | `pytest .../test_config.py::TestConfigHandler::test_bare_path_get_returns_405 -xvs` | **Wave 0 (net-new)** |
| CFG-03 | E2E round-trip over POST | E2E | `make run-tests-e2e` — `settings-fields.spec.ts` persist tests | migrated |
| CFG-04 | On-disk format unchanged | integration | `pytest .../test_config.py::TestConfigHandler::test_set_good -xvs` (asserts value actually persisted) | migrated |
| D-06 | Empty value → 400 | integration | `pytest .../test_config.py::TestConfigHandler::test_set_empty_value -xvs` | migrated (status 404→400) |
| D-07 | Wrong content-type (None body) → 400 | integration | `pytest .../test_config.py::TestConfigHandler::test_set_malformed_body_wrong_content_type -xvs` | **Wave 0 (net-new)** |
| D-07 | Invalid JSON + `application/json` → 400 (bottle HTTPError) | integration | `pytest .../test_config.py::TestConfigHandler::test_set_invalid_json_correct_content_type -xvs` | **Wave 0 (net-new)** |
| D-07 | Absent required field → 400 | integration | `pytest .../test_config.py::TestConfigHandler::test_set_missing_required_field -xvs` | **Wave 0 (net-new)** |
| D-07 | Non-string `section` → 400 (not 500/DoS) | integration + unit | `pytest .../test_config.py::TestConfigHandler::test_set_non_string_section -xvs` ; `.../test_config_handler.py::TestConfigHandlerSet::test_set_non_string_section_returns_400 -xvs` | **Wave 0 (net-new)** |
| D-07 | Non-string `key` → 400 (not 500/DoS) | integration + unit | `pytest .../test_config.py::TestConfigHandler::test_set_non_string_key -xvs` ; `.../test_config_handler.py::TestConfigHandlerSet::test_set_non_string_key_returns_400 -xvs` | **Wave 0 (net-new)** |
| D-08 | Rate limit still 60/60s | unit | `pytest .../test_config_handler.py::TestConfigHandlerRateLimit -xvs` | migrated |

## Sampling Rate

- **Per task commit:** `cd src/python && poetry run pytest tests/integration/test_web/test_handler/test_config.py tests/unittests/test_web/test_handler/test_config_handler.py -v` + `ruff check src/python/`
- **Per wave merge:** `make run-tests-python` + `make run-tests-angular`
- **Phase gate:** Full suite green (`make run-tests-python` + `make run-tests-angular` + `make run-tests-e2e`) before `/gsd:verify-work`; Python `fail_under` ≥ 88 holds/rises; Karma floors 83/68/79/83 hold/rise; amd64 + arm64.

## Wave 0 Gaps (net-new tests required before/with implementation)

CFG-02 — legacy-route removal (split per FINDING 2: 404 on value-bearing path, 405 on bare path):
- [ ] `test_config.py::TestConfigHandler::test_old_value_bearing_path_returns_404` — OLD value-bearing GET path `/server/config/set/general/debug/True` → **404** (route unregistered); also POST to that value-bearing path is not 200
- [ ] `test_config.py::TestConfigHandler::test_bare_path_get_returns_405` — NEW bare path GET `/server/config/set` → **405** (POST-only route exists; NOT 404)

D-07 — malformed-body error surface:
- [ ] `test_config.py::TestConfigHandler::test_set_malformed_body_wrong_content_type` — wrong content-type → None body → 400
- [ ] `test_config.py::TestConfigHandler::test_set_invalid_json_correct_content_type` — body `"{bad json"` WITH `Content-Type: application/json` → **400** via bottle's built-in HTTPError (FINDING 3: confirms no handler code services this path)
- [ ] `test_config.py::TestConfigHandler::test_set_missing_required_field` — absent required field → 400

D-07 / FINDING 1 — non-string `section`/`key` type-confusion DoS (must be 400, never 500):
- [ ] `test_config.py::TestConfigHandler::test_set_non_string_section` — `section: ["general"]` → 400 AND explicitly NOT 500
- [ ] `test_config.py::TestConfigHandler::test_set_non_string_key` — `key: {"x": 1}` → 400 AND explicitly NOT 500
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_non_string_section_returns_400` — non-string section → 400; asserts the config lookup (`has_section`/`getattr`) was never reached
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_non_string_key_returns_400` — non-string key → 400; asserts the config lookup was never reached

Unit-level encoding-test replacements + None/non-dict guards:
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_with_slashes_through_body` — replaces obsolete `test_set_value_with_slashes` (preserve coverage, not delete)
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_with_spaces_through_body` — replaces obsolete `test_set_url_decodes_value` (verbatim value, no decode)
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_none_body_returns_400` — covers D-07 (None body from wrong content-type)
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_non_dict_body_returns_400` — covers D-07 (JSON array / non-object body → 400)

## Security Domain (ASVS L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Existing `before_request` Bearer-token hook — unchanged (path-based, method-agnostic) |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | Single-user tool |
| V5 Input Validation | Yes | Handler validates section/key/value from body; missing fields → 400; non-string section/key rejected with 400 BEFORE any config lookup (no TypeError/500) |
| V6 Cryptography | No | Transport change only; Fernet on-disk untouched (CFG-04) |

### Known Threat Patterns (STRIDE)

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Credentials in URL / access log | Info Disclosure (CWE-598) | **Eliminated this phase**: POST JSON body removes value from URL |
| Malformed JSON body → 500 | Tampering / DoS | Bottle auto-400 on invalid-JSON-with-correct-content-type (before the handler — RESEARCH §RQ-1 case 3); handler guards `None`/non-dict body |
| Non-string `section`/`key` → TypeError → 500 | Tampering / DoS | **FINDING 1**: `isinstance(section, str)` + `isinstance(key, str)` guard BEFORE any config lookup → 400, never 500. Pinned by `test_set_non_string_section`/`test_set_non_string_key` (integration, assert not-500) + unit equivalents (assert lookup never reached) |
| Body size exhaustion | DoS | Bottle `MEMFILE_MAX` caps body before `request.json` |
| Auth bypass via method change | Elevation of Privilege | `before_request` hook is path-based, not method-based — POST inherits same auth |
| Secret-present leak on GET response | Info Disclosure | SEC-02 preserved: `__handle_get_config` untouched (always serializes secret fields as `""`) |
