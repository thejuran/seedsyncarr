---
phase: 124
slug: model-stream-overflow-recovery
status: draft
nyquist_compliant: false
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

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| STRM-01 | Stalled consumer + >maxsize puts ⇒ drops; drained model diverges from server model (reproduction, recorded) | unit | `poetry run pytest tests/unittests/test_web/test_stream_queue.py tests/unittests/test_web/test_handler/test_stream_model_handler.py -v` | ✅ extend | ⬜ pending |
| STRM-02 | After overflow + resync, client-reconstructed model equals server model (RED before fix, GREEN after) | unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_handler.py -v` | ✅ extend | ⬜ pending |
| STRM-02 | Same convergence through real WSGI generator with stalled consumer | integration | `poetry run pytest tests/integration/test_web/test_handler/test_stream_model.py -v` | ✅ extend; ❌ W0 stall-capable helper | ⬜ pending |
| STRM-02 (D-03) | Resync atomic vs model mutations under `__model_lock` | unit | `poetry run pytest tests/unittests/test_controller/ -v` | ✅ extend | ⬜ pending |
| STRM-02 (D-04/D-05) | Drops coalesce to one snapshot; queue never exceeds maxsize | unit | `poetry run pytest tests/unittests/test_web/ -v` | ✅ extend | ⬜ pending |
| STRM-02 (D-06) | Status stream full-snapshot evidence (no code change) | existing unit | `poetry run pytest tests/unittests/test_web/test_handler/test_stream_status_handler.py -v` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/python/tests/helpers/wsgi_stream.py` — stall-capable generator helper (manual `next()` control) for the integration convergence test

---

## Manual-Only Verifications

All phase behaviors have automated verification (D-07: no NAS sandbox session).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
