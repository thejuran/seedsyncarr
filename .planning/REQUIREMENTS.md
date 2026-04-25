# Requirements: SeedSyncarr

**Defined:** 2026-04-24
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.2.0 Requirements

Requirements for Test & Quality Hardening milestone. Each maps to roadmap phases.

### Python Test Fixes

- [x] **PYFIX-01**: Fix `threading.Thread(target=_callback_sequence())` — target called instead of passed, concurrency never tested (C-01)
- [x] **PYFIX-02**: Fix assertion-less `test_init_skips_rate_limit_when_zero` — always passes regardless of behavior (C-02)
- [x] **PYFIX-03**: Fix temp file with credentials never deleted in `test_config.py:503` (W-01)
- [x] **PYFIX-04**: Fix temp file leaked on test failure in `test_config.py:413` (W-02)
- [x] **PYFIX-05**: Fix mock class vs instance confusion in `test_status_handler.py` (W-03)
- [ ] **PYFIX-06**: Fix group-writable permissions walked up to /tmp in `test_lftp.py:24` (W-04)
- [ ] **PYFIX-07**: Fix logger fixture handler leak and propagation in `conftest.py` (W-05)
- [ ] **PYFIX-08**: Fix implicit `unittest.mock.ANY` import via side effect across 3+ files (W-06)
- [ ] **PYFIX-09**: Fix resource leak — bare `open(os.devnull)` without context manager in 2 integration tests (W-07)
- [ ] **PYFIX-10**: Fix resource leak — bare `open()` in `create_large_file` helper (W-08)
- [ ] **PYFIX-11**: Add test for HTML-escaping token in meta tag — XSS prevention (M-01)
- [ ] **PYFIX-12**: Fix busy-wait race condition in scanner tests — add sleep + fix TOCTOU (M-02)
- [ ] **PYFIX-13**: Replace real `time.sleep` in unit tests with mock time or threading.Event (~4.5s saved per run) (M-03)
- [ ] **PYFIX-14**: Fix `TemporaryDirectory` cleanup — add `addCleanup(_tmpd.cleanup)` (M-04)
- [ ] **PYFIX-15**: Move implicit `import bottle` inside closures to module level (M-05)
- [ ] **PYFIX-16**: Fix logger handler leaked every test — add removeHandler in tearDown across 5 files (BUG-11/12)
- [ ] **PYFIX-17**: Replace `time.sleep` sync primitive in `test_job.py` with `job.join(timeout=5.0)` (PY-06)
- [ ] **PYFIX-18**: Add sleep to ~25 busy-wait loops in `test_lftp.py` to prevent 100% CPU (PY-04)
- [ ] **PYFIX-19**: Fix conditional assertion that silently skips in `test_job_status_parser_components.py:199` (PY-05)

### Python Test Architecture

- [ ] **PYARCH-01**: Convert conftest fixtures to importable helpers or adopt pytest-style tests (A-01)
- [ ] **PYARCH-02**: Consolidate duplicated `BaseControllerTestCase` and `BaseAutoDeleteTestCase` base classes (A-02)
- [ ] **PYARCH-03**: Move misclassified integration test `tests/unittests/test_lftp/test_lftp.py` to integration directory (A-03)
- [ ] **PYARCH-04**: Document coverage gaps — modules without dedicated tests (ActiveScanner, WebAppJob, WebAppBuilder, scan_fs) (A-04)
- [ ] **PYARCH-05**: Document private-API coupling via name-mangling as accepted trade-off (A-05)
- [ ] **PYARCH-06**: Extract duplicated INI strings in config encryption tests to shared constant (A-06)

### Angular Test Fixes

- [ ] **ANGFIX-01**: Add `discardPeriodicTasks()` for never-completing observable in fakeAsync zone (ANG-10)
- [ ] **ANGFIX-02**: Fix double-cast hiding nullable type — use `ViewFileFilterCriteria | undefined` (ANG-04)
- [ ] **ANGFIX-03**: Fix `view-file.service.spec.ts` missing subscription teardown (BUG-09)
- [ ] **ANGFIX-04**: Fix subscription leaks in `notification.service.spec.ts` — 7 occurrences (ANG-01)
- [ ] **ANGFIX-05**: Fix signal-derived observable subscription leaks in `file-selection.service.spec.ts` (ANG-02)
- [ ] **ANGFIX-06**: Fix EventEmitter leak + non-null assertion in `transfer-row.component.spec.ts` (ANG-03)
- [ ] **ANGFIX-07**: Add `expect(result).toBeDefined()` guards where optional chaining masks test gaps (ANG-05)

### E2E Test Fixes

- [ ] **E2EFIX-01**: Fix `innerHTML()` vs `innerText()` in autoqueue page object (BUG-01)
- [ ] **E2EFIX-02**: Fix `beforeEach` calling API before `navigateTo()` in `settings-error.spec.ts` (BUG-02)
- [ ] **E2EFIX-03**: Replace `waitForTimeout(500)` hard-coded delay with proper Playwright wait (BUG-04)
- [ ] **E2EFIX-04**: Fix `beforeAll` seed context bypassing CSP fixture (BUG-03)
- [ ] **E2EFIX-05**: Replace deprecated `:has-text()` pseudo-class with `locator.filter({ hasText })` (E2E-02)
- [ ] **E2EFIX-06**: Add HTTP response checking for rate-limit config calls in dashboard spec (E2E-04)
- [ ] **E2EFIX-07**: Deduplicate `_escapeRegex` helper — extract to shared utility (ARCH)

### E2E Infrastructure

- [ ] **E2EINFRA-01**: Initialize `SERVER_UP`/`SCAN_DONE` variables before polling loops in `run_tests.sh` (BUG-05)
- [ ] **E2EINFRA-02**: Add `condition: service_healthy` to configure→myapp dependency in compose (BUG-06)
- [ ] **E2EINFRA-03**: Replace `sleep 2` race after restart with wait-for-down-then-up pattern (BUG-07)
- [ ] **E2EINFRA-04**: Replace bare `except:` with specific exception types in `parse_status.py` (BUG-08)
- [ ] **E2EINFRA-05**: Add `__main__` guard to `parse_status.py` (PY-10)

### Test Coverage Gaps

- [ ] **COVER-01**: Add SSE streaming integration tests — evaluate `httpx` AsyncClient or thin WSGI harness (GAP-01)
- [ ] **COVER-02**: Add Logs page E2E coverage — page object + specs for load, render, auto-scroll (GAP-02)
- [ ] **COVER-03**: Add Settings form fields E2E coverage — remote host, encryption toggle, save/persist (GAP-03)
- [ ] **COVER-04**: Add webhook end-to-end test — Sonarr/Radarr POST through web layer to controller (GAP-04)
- [ ] **COVER-05**: Add `DeleteRemoteProcess` unit tests — SSH command construction, error handling, deletion paths (GAP-05)
- [ ] **COVER-06**: Add `ActiveScanner` dedicated test file — scan scheduling, result aggregation (GAP-06)

### CI Security

- [ ] **CISEC-01**: Restrict workflow-level permissions to `contents: read`, add per-job write permissions only where needed (SEC-06)
- [ ] **CISEC-02**: Pin GitHub Actions to SHA hashes with version comments (SEC-07)
- [ ] **CISEC-03**: Add `publish-docker-image` to `publish-github-release` needs chain (BUG-13)
- [ ] **CISEC-04**: Add registry-based Docker build cache for Python test images in CI

### Docker Test Security

- [ ] **DOCKSEC-01**: Remove test user from root group — create dedicated group if needed (SEC-03)
- [ ] **DOCKSEC-02**: Lock SSH password and disable `PasswordAuthentication` in remote test container (SEC-01)
- [ ] **DOCKSEC-03**: Lock SSH password and disable `PasswordAuthentication` in Python test container (SEC-02)
- [ ] **DOCKSEC-04**: Run sshd as non-root in test containers (SEC-04)
- [ ] **DOCKSEC-05**: Generate ephemeral SSH key pair at Docker build time (SEC-05)
- [ ] **DOCKSEC-06**: Change `StrictHostKeyChecking no` to `accept-new` in Python test container (SEC-08)

### E2E CSP & Platform

- [ ] **PLAT-01**: Add Playwright console listener / `securitypolicyviolation` event that fails on CSP violations (CSP todo)
- [ ] **PLAT-02**: Fix arm64 Unicode sort order failures in dashboard E2E specs (arm64 todo)

### Rate Limiting

- [ ] **RATE-01**: Add reusable rate-limiting decorator for HTTP endpoints
- [ ] **RATE-02**: Apply rate limiting to `/server/config/set` endpoint
- [ ] **RATE-03**: Apply rate limiting to `/server/config/test/*` endpoints
- [ ] **RATE-04**: Apply rate limiting to `/server/status` endpoint

### Tooling

- [ ] **TOOL-01**: Tighten `js-nosql-injection-where` Semgrep rule — add MongoDB context constraint (Shield)
- [ ] **TOOL-02**: Tighten `js-xss-eval-user-input` Semgrep rule — exclude arrow/named function callbacks (Shield)

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### API Improvements

- **API-01**: Migrate `/server/config/set` from GET-path to POST-body (SEC-09 + E2E-06)

### Test Infrastructure

- **INFRA-01**: Remove `PYTHONWARNINGS` cgi filter once webob drops stdlib cgi import (upstream blocked)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| webob/cgi warning filter removal | Blocked on upstream webob 2.0 release (PR #466 open) |
| `/server/config/set` POST migration | Backend API contract change, separate milestone |
| New feature development | Quality-only milestone |
| Coverage percentage targets | Fix known issues, don't chase arbitrary numbers |
| Python test type hints (PY-13) | Style preference, not correctness |
| karma.conf.js random:true (ANG-08) | Risk of introducing CI flakes |
| parameterized→pytest.mark migration (PY-15) | Style preference, extra dependency |
| publish-docs Python version alignment | Cosmetic consistency |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PYFIX-01 | Phase 87 | Complete |
| PYFIX-02 | Phase 87 | Complete |
| PYFIX-03 | Phase 87 | Complete |
| PYFIX-04 | Phase 87 | Complete |
| PYFIX-05 | Phase 87 | Complete |
| PYFIX-06 | Phase 87 | Pending |
| PYFIX-07 | Phase 87 | Pending |
| PYFIX-08 | Phase 87 | Pending |
| PYFIX-09 | Phase 87 | Pending |
| PYFIX-10 | Phase 87 | Pending |
| PYFIX-11 | Phase 88 | Pending |
| PYFIX-12 | Phase 88 | Pending |
| PYFIX-13 | Phase 88 | Pending |
| PYFIX-14 | Phase 88 | Pending |
| PYFIX-15 | Phase 88 | Pending |
| PYFIX-16 | Phase 88 | Pending |
| PYFIX-17 | Phase 88 | Pending |
| PYFIX-18 | Phase 88 | Pending |
| PYFIX-19 | Phase 88 | Pending |
| PYARCH-01 | Phase 89 | Pending |
| PYARCH-02 | Phase 89 | Pending |
| PYARCH-03 | Phase 89 | Pending |
| PYARCH-04 | Phase 89 | Pending |
| PYARCH-05 | Phase 89 | Pending |
| PYARCH-06 | Phase 89 | Pending |
| ANGFIX-01 | Phase 90 | Pending |
| ANGFIX-02 | Phase 90 | Pending |
| ANGFIX-03 | Phase 90 | Pending |
| ANGFIX-04 | Phase 90 | Pending |
| ANGFIX-05 | Phase 90 | Pending |
| ANGFIX-06 | Phase 90 | Pending |
| ANGFIX-07 | Phase 90 | Pending |
| E2EFIX-01 | Phase 91 | Pending |
| E2EFIX-02 | Phase 91 | Pending |
| E2EFIX-03 | Phase 91 | Pending |
| E2EFIX-04 | Phase 91 | Pending |
| E2EFIX-05 | Phase 91 | Pending |
| E2EFIX-06 | Phase 91 | Pending |
| E2EFIX-07 | Phase 91 | Pending |
| PLAT-01 | Phase 91 | Pending |
| PLAT-02 | Phase 91 | Pending |
| E2EINFRA-01 | Phase 92 | Pending |
| E2EINFRA-02 | Phase 92 | Pending |
| E2EINFRA-03 | Phase 92 | Pending |
| E2EINFRA-04 | Phase 92 | Pending |
| E2EINFRA-05 | Phase 92 | Pending |
| CISEC-01 | Phase 93 | Pending |
| CISEC-02 | Phase 93 | Pending |
| CISEC-03 | Phase 93 | Pending |
| CISEC-04 | Phase 93 | Pending |
| DOCKSEC-01 | Phase 93 | Pending |
| DOCKSEC-02 | Phase 93 | Pending |
| DOCKSEC-03 | Phase 93 | Pending |
| DOCKSEC-04 | Phase 93 | Pending |
| DOCKSEC-05 | Phase 93 | Pending |
| DOCKSEC-06 | Phase 93 | Pending |
| COVER-01 | Phase 94 | Pending |
| COVER-04 | Phase 94 | Pending |
| COVER-05 | Phase 94 | Pending |
| COVER-06 | Phase 94 | Pending |
| COVER-02 | Phase 95 | Pending |
| COVER-03 | Phase 95 | Pending |
| RATE-01 | Phase 96 | Pending |
| RATE-02 | Phase 96 | Pending |
| RATE-03 | Phase 96 | Pending |
| RATE-04 | Phase 96 | Pending |
| TOOL-01 | Phase 96 | Pending |
| TOOL-02 | Phase 96 | Pending |

**Coverage:**
- v1.2.0 requirements: 68 total
- Mapped to phases: 68
- Unmapped: 0

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after roadmap creation -- all 68 requirements mapped to phases 87-96*
