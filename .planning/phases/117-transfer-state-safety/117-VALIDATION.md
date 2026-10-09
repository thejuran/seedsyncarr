---
phase: 117
slug: transfer-state-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-08
---

# Phase 117 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `117-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + unittest.TestCase; pytest-timeout 60s |
| **Config file** | `src/python/pyproject.toml` (`fail_under = 88`) |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_model_builder.py tests/unittests/test_controller/test_transfer_state_safety.py tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh --ignore=tests/unittests/test_controller/test_extract --ignore=tests/unittests/test_controller/test_scan --ignore=tests/unittests/test_system` (host); CI `make run-tests-python` |
| **Lint gate** | `cd src/python && poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/` (whole tree) |
| **Estimated runtime** | ~5 seconds (quick), ~60 seconds (host full) |

---

## Sampling Rate

- **After every task commit:** quick run command + whole-tree ruff
- **After every plan wave:** host full suite (no new failures vs baseline)
- **Before `/bm:verify-work`:** CI `unittests-python` (integration + coverage ≥ 88) and `lint-python` green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled by the planner per task; requirement→test mapping (from research):

| Requirement | Behavior | Test Type | Automated Command | File Exists | Fails on old code? |
|-------------|----------|-----------|-------------------|-------------|--------------------|
| XFER-01 | pget (no data) → pget / mirror header; `\chunk` (no data) → mirror / `\chunk`; mirror-empty → "Getting file list" header | unit | `pytest tests/unittests/test_lftp/test_job_status_parser.py -q` | ✅ file / ❌ tests | YES |
| XFER-01 | Existing parser fixtures unchanged | unit | `pytest tests/unittests/test_lftp -q` | ✅ | passes both |
| XFER-02 | Composed parse error mid-download → protection kept, no QUEUE/EXTRACT/delete | composed | `pytest tests/unittests/test_controller/test_transfer_state_safety.py -q` | ❌ W0 | YES |
| XFER-02 | `Lftp.kill` on unavailable raises `LftpJobStatusParserError` | unit | `pytest tests/unittests/test_lftp/test_lftp_status_contract.py -q` | ❌ W0 | new |
| XFER-03 | Failures 1..MAX → None; MAX+1 raises; success resets; empty → [] clears | unit + composed | contract file + safety file | ❌ W0 | YES / preservation |
| XFER-04 | Failed remote scans spanning window → not queued; D-03/D-04 cases; UI fields unchanged | unit + composed | `pytest tests/unittests/test_controller/test_auto_queue.py -q` + safety file + serializer test | ✅ / ❌ | YES |
| XFER-05 | Failed local scans spanning window → gate holds; D-05 both cases | unit + composed | auto_queue + safety file | ❌ | YES |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_lftp/test_lftp_status_contract.py` — B2 boundary + kill-on-None
- [ ] `tests/unittests/test_controller/test_transfer_state_safety.py` — composed B2 downstream + composed B3
- [ ] `tests/unittests/test_controller/test_auto_queue.py` — new-field None init in setUps; `_set_scan(failed=)`; `_cycle` success clock
- [ ] `117-REL01-EVIDENCE.md` — RED section (old code + test-only commit), later GREEN section

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Integration counter tests flipped `[]`→`None` | XFER-03 | Require CI Docker (lftp binary + ssh) | Confirm CI `unittests-python` green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
