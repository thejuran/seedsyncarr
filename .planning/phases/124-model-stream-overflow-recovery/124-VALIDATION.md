---
phase: 124
slug: model-stream-overflow-recovery
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-26
---

# Phase 124 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.3 (+ pytest-timeout, pytest-cov) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_web/ tests/unittests/test_controller/ -v` |
| **Full suite command** | `make run-tests-python` (Docker, matches CI); local: `cd src/python && poetry run pytest` |
| **Lint gate** | `ruff check src/python/` (whole tree, separate CI gate) |
| **Estimated runtime** | ~60 seconds (quick), several minutes (full Docker) |

---

## Sampling Rate

- **After every task commit:** Run the targeted test file(s) for that task
- **After every plan wave:** Run `cd src/python && poetry run pytest` + `ruff check src/python/`
- **Before `/bm:verify-work`:** `make run-tests-python` + whole-tree ruff must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Req | Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-----|----------|-----------|-------------------|-------------|--------|
| 124-01-01 | 01 | 1 | STRM-01 | Wire-format client reducer + non-draining `open_sse_stream` helper (Wave 0 stall-capable harness) | unit (smoke) | `poetry run python -c "from tests.helpers.model_stream_client import ...; from tests.helpers.wsgi_stream import open_sse_stream ..."` | ❌ W0 creates `model_stream_client.py`; extends `wsgi_stream.py` | ⬜ pending |
| 124-01-02 | 01 | 1 | STRM-01 (D-01, D-06) | Stalled consumer + >maxsize puts ⇒ drops; drained model diverges (recorded reproduction); status stream full-snapshot evidence | unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_overflow.py -v && ruff check src/python/` | ❌ W0 creates `test_stream_model_overflow.py` | ⬜ pending |
| 124-02-01 | 02 | 2 | STRM-02 (D-03, D-05) | RED: `StreamQueue.clear()`, bounded sustained stall, `resync_model_files` atomic under `__model_lock` | unit (RED, exit code 1 required) | `pytest test_stream_queue.py test_controller_unit.py -k "clear or Resync"` must exit exactly 1; `-k sustained_stall` passes | ✅ extend | ⬜ pending |
| 124-02-02 | 02 | 2 | STRM-02 (D-03) | GREEN: clear() + resync_model_files; controller does not import web | unit | `poetry run pytest tests/unittests/test_web/test_stream_queue.py tests/unittests/test_controller/ -q && poetry run pytest -q -x && ruff check src/python/` | ✅ extend | ⬜ pending |
| 124-03-01 | 03 | 3 | STRM-02 (D-02, D-04, D-05, D-07b, D-08) | RED unit-level: real-Controller convergence, coalescing, bounded, rate-limited warning | unit (RED, exit code 1 required) | `pytest test_stream_model_overflow.py test_stream_model_handler.py -k "Convergence or Resync"` must exit exactly 1; pre-existing handler tests pass | ✅ extend | ⬜ pending |
| 124-03-02 | 03 | 3 | STRM-02 (D-07b) | RED WSGI-level: stalled consumer through real generator + SSE serialization | integration (RED, exit code 1 required) | `pytest tests/integration/test_web/test_handler/test_stream_model.py -k stalled_consumer` must exit exactly 1; `-k "not stalled_consumer"` passes | ✅ extend (uses W0 `open_sse_stream`) | ⬜ pending |
| 124-03-03 | 03 | 3 | STRM-02 (D-02, D-03, D-04, D-05, D-08) | GREEN: resync gate in `ModelStreamHandler.get_value()`; all RED tests pass | unit + integration | `poetry run pytest tests/unittests/test_web/ tests/unittests/test_controller/ tests/integration/test_web/test_handler/test_stream_model.py -q && ruff check src/python/` | ✅ | ⬜ pending |
| 124-03 plan gate | 03 | 3 | STRM-01, STRM-02 | Full suite + CI-equivalent | full | `poetry run pytest` (coverage >= 88) + `ruff check src/python/` + `make run-tests-python` (Docker; if unavailable locally, recorded, never claimed) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/python/tests/helpers/wsgi_stream.py` — stall-capable generator helper (manual `next()` control) for the integration convergence test (delivered by 124-01 Task 1)

---

## Manual-Only Verifications

All phase behaviors have automated verification (D-07: no NAS sandbox session).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (planned in 124-01 Task 1; `wave_0_complete` flips when executed)
- [x] No watch-mode flags
- [x] Feedback latency < 60s (task-level gates are targeted pytest + ruff; Docker full suite is the plan-level gate)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
