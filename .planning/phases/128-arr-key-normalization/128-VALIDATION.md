---
phase: 128
slug: arr-key-normalization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-18
---

# Phase 128 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (unittest.TestCase style; WebTest for integration) |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`, `fail_under = 88`) |
| **Quick run command** | `cd src/python && pytest -q -p no:cacheprovider tests/unittests/test_common/test_arr_api_key.py tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py` |
| **Full suite command** | `cd src/python && pytest -q -p no:cacheprovider` + `ruff check src/python/` (repo root, whole tree) + `cd src/python && poetry run pytest --cov` (≥ 88) |
| **Estimated runtime** | quick < 15 s; full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run quick run command + `ruff check src/python/`
- **After every plan wave:** Run full `pytest -q -p no:cacheprovider` + whole-tree ruff
- **Before `/bm:verify-work`:** Full suite green, ruff clean, coverage ≥ 88
- **Max feedback latency:** 15 seconds (quick command)

---

## Per-Task Verification Map

Filled by the planner/executor from PLAN.md tasks. Requirement → test map (from 128-RESEARCH.md §Validation Architecture):

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| ARR-01 | Padded key saved trimmed (Sonarr + Radarr) | integration | `pytest tests/integration/test_web/test_handler/test_config.py -k arr_key -q` | ✅ file / ❌ tests | ⬜ pending |
| ARR-01 / D-03 | Inner-invalid key → 400 "<Svc> API key contains invalid characters", stored unchanged, value not echoed | unit + integration | `pytest tests/unittests/test_web/test_handler/test_config_handler.py -k arr_key -q` | ✅ / ❌ | ⬜ pending |
| ARR-01 / D-04 | Whitespace-only → 400 "Invalid request body", stored unchanged | unit + integration | same | ✅ / ❌ | ⬜ pending |
| ARR-01 / D-01 | Test Connection behavior unchanged after refactor | unit (existing) | `pytest tests/unittests/test_web -k "whitespace_stripped or newline_never" -q` | ✅ | ⬜ pending |
| ARR-02 | In-memory padded key sent normalized by queue client (fail-before/pass-after) | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k padded -q` | ✅ / ❌ | ⬜ pending |
| ARR-02 | Padded vs trimmed key → same identity (no spurious gate reset) | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k identity -q` | ✅ / ❌ | ⬜ pending |
| ARR-02 | One rule across three paths | unit | `pytest tests/unittests/test_common/test_arr_api_key.py -q` | ❌ W0 | ⬜ pending |
| ARR-03 | Empty/invalid key → start_fetch None, no request | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k "invalid_key or missing_key" -q` | ✅ / ❌ | ⬜ pending |
| ARR-03 | Warn once per key token, debug after, warn again on change | unit | same | ✅ / ❌ | ⬜ pending |
| ARR-03 | Gate holds `<code>_unavailable` with bad key | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k bad_key -q` | ✅ / ❌ | ⬜ pending |
| ARR-03 | No key substring in any log line | unit | covered in arr_queue tests | ✅ / ❌ | ⬜ pending |
| D-07 | Every secret_fields() prop → "<s>.<k> updated", value never echoed; non-secret keeps "set to" | integration | `pytest tests/integration/test_web/test_handler/test_config.py -k secret -q` | ✅ / ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/python/tests/unittests/test_common/test_arr_api_key.py` — rule table (None, "", whitespace-only, padded valid, inner space, tab, CR/LF, NUL, non-ASCII, NBSP padding)
- [ ] RED tests in existing files above; ARR-02 padded-key test recorded failing before the `enabled_targets` change
- [ ] `poetry install --with dev` locally for the coverage gate (no framework install otherwise)

---

## Manual-Only Verifications

All phase behaviors have automated verification. (Live padded-key queue check on a release image is Phase 130's smoke test, out of scope here.)

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
