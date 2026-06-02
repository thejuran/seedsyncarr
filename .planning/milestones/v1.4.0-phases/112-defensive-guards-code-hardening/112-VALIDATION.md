---
phase: 112
slug: defensive-guards-code-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-02
---

# Phase 112 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `112-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `poetry run pytest tests/unittests/test_common/test_app_process.py tests/unittests/test_seedsyncarr.py tests/unittests/test_controller/test_delete_process.py -v` |
| **Full suite command** | `poetry run pytest tests/ -v --cov --cov-report=term-missing` |
| **Lint gate** | `poetry run ruff check .` (whole-tree from `src/python/`) |
| **Estimated runtime** | ~60 seconds (quick), full suite minutes |

---

## Sampling Rate

- **After every task commit:** `poetry run ruff check . && poetry run pytest tests/unittests/test_common/test_app_process.py tests/unittests/test_seedsyncarr.py tests/unittests/test_controller/test_delete_process.py -v`
- **After every plan wave:** `poetry run pytest tests/ --cov --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite green + coverage `fail_under` ≥ 88 + ruff clean
- **GUARD-04 special gate:** the AppProcess test file must pass under **both** `fork` and `spawn` start methods (spawn is the macOS default; fork is the Linux/CI default — CI amd64 + arm64 covers fork).
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Requirement | Wave | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|------|----------|-----------|-------------------|-------------|--------|
| GUARD-04 | impl | `test_process_with_long_running_thread_terminates_properly` passes under spawn (root cause = `threading.Thread` in subclass; fix = `AppProcess.__getstate__`/`__setstate__` stripping Thread instances) | unit | `poetry run pytest tests/unittests/test_common/test_app_process.py -v` | ✅ | ⬜ pending |
| GUARD-04 | impl | All AppProcess tests pass under fork too (Linux default) | unit | CI amd64 + arm64 container | ✅ (CI) | ⬜ pending |
| GUARD-02 | 0 | Accept-any-caller warning does NOT fire when `webhook_require_secret=True` | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py -v` | ❌ W0 | ⬜ pending |
| GUARD-02 | 0 | 503 warning DOES fire when `webhook_require_secret=True` + empty secret | unit | same | ❌ W0 | ⬜ pending |
| GUARD-01 | 0 | Prominence prefix visible in api-token warning text; existing `assertEqual(3, ...)` count preserved (default `require_secret=False`) | unit | same | ✅ (extend existing) | ⬜ pending |
| GUARD-03 | 0 | `DeleteLocalProcess` `rmtree` failure produces a log record and does NOT raise (best-effort) | unit | `poetry run pytest tests/unittests/test_controller/test_delete_process.py -v` | ❌ W0 | ⬜ pending |
| GUARD-06 | 0 | Legacy `~/.seedsync` fallback warning is emitted (reaches operator) when the fallback triggers | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py -v` | ❌ W0 | ⬜ pending |
| GUARD-05 | impl | `.orchestrator.json` and `.playwright-mcp/` not present in `git status` | manual | `git status` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_seedsyncarr.py` — add GUARD-02 matrix tests (2 new: accept-any-caller suppressed + 503 warning fires when `require_secret=True` and secret empty)
- [ ] `tests/unittests/test_seedsyncarr.py` — add GUARD-06 fallback-warning test (1 new: warning emitted when `~/.seedsync` fallback triggers)
- [ ] `tests/unittests/test_controller/test_delete_process.py` — add `DeleteLocalProcess` failure-path tests (GUARD-03: rmtree raises → log record observed, no exception out of `run_once`)

*GUARD-04's red test already exists (`test_app_process.py:175`) — it is the green-target, not a Wave 0 stub. GUARD-01 extends existing tested warnings.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tooling artifacts ignored | GUARD-05 | Repo-hygiene state, not runtime behavior | Run `git status`; confirm neither `.orchestrator.json` nor `.playwright-mcp/` appears as untracked |
| arm64 CI parity | GUARD-04 (COMPAT) | Local macOS cannot run arm64 Linux container build (QEMU blocked, NAS-QEMU) | Confirmed by CI matrix on push, not locally |

---

## Validation Sign-Off

- [ ] All tasks have an automated verify or a Wave 0 test dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING test references (GUARD-02 ×2, GUARD-06 ×1, GUARD-03 ×N)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
