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
| CFG-02 | GET path → 404/405 | integration | `pytest .../test_config.py::TestConfigHandler::test_get_old_path_returns_404 -xvs` | **Wave 0 (net-new)** |
| CFG-03 | E2E round-trip over POST | E2E | `make run-tests-e2e` — `settings-fields.spec.ts` persist tests | migrated |
| CFG-04 | On-disk format unchanged | integration | `pytest .../test_config.py::TestConfigHandler::test_set_good -xvs` (asserts value actually persisted) | migrated |
| D-06 | Empty value → 400 | integration | `pytest .../test_config.py::TestConfigHandler::test_set_empty_value -xvs` | migrated (status 404→400) |
| D-07 | Malformed body → 400 | integration + unit | `pytest .../test_config.py::TestConfigHandler::test_set_malformed_body -xvs` | **Wave 0 (net-new)** |
| D-08 | Rate limit still 60/60s | unit | `pytest .../test_config_handler.py::TestConfigHandlerRateLimit -xvs` | migrated |

## Sampling Rate

- **Per task commit:** `cd src/python && poetry run pytest tests/integration/test_web/test_handler/test_config.py tests/unittests/test_web/test_handler/test_config_handler.py -v` + `ruff check src/python/`
- **Per wave merge:** `make run-tests-python` + `make run-tests-angular`
- **Phase gate:** Full suite green (`make run-tests-python` + `make run-tests-angular` + `make run-tests-e2e`) before `/gsd:verify-work`; Python `fail_under` ≥ 88 holds/rises; Karma floors 83/68/79/83 hold/rise; amd64 + arm64.

## Wave 0 Gaps (net-new tests required before/with implementation)

- [ ] `test_config.py::TestConfigHandler::test_get_old_path_returns_404` — covers CFG-02 (D-02 route removal → 404/405)
- [ ] `test_config.py::TestConfigHandler::test_set_malformed_body` — covers D-07 (wrong content-type / invalid JSON → 400)
- [ ] `test_config.py::TestConfigHandler::test_set_missing_fields` — covers D-07 (absent required field → 400)
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_with_slashes_through_body` — replaces obsolete `test_set_value_with_slashes` (preserve coverage, not delete)
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_raw_value_decoded_through_body` — replaces obsolete `test_set_url_decodes_value`
- [ ] `test_config_handler.py::TestConfigHandlerSet::test_set_none_body_returns_400` — covers D-07 (None body from wrong content-type)

## Security Domain (ASVS L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Existing `before_request` Bearer-token hook — unchanged (path-based, method-agnostic) |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | Single-user tool |
| V5 Input Validation | Yes | Handler validates section/key/value from body; missing fields → 400 |
| V6 Cryptography | No | Transport change only; Fernet on-disk untouched (CFG-04) |

### Known Threat Patterns (STRIDE)

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Credentials in URL / access log | Info Disclosure (CWE-598) | **Eliminated this phase**: POST JSON body removes value from URL |
| Malformed JSON body → 500 | Tampering / DoS | Bottle auto-400 on invalid JSON; handler guards `None`/non-dict body |
| Body size exhaustion | DoS | Bottle `MEMFILE_MAX` caps body before `request.json` |
| Auth bypass via method change | Elevation of Privilege | `before_request` hook is path-based, not method-based — POST inherits same auth |
| Secret-present leak on GET response | Info Disclosure | SEC-02 preserved: `__handle_get_config` untouched (always serializes secret fields as `""`) |
