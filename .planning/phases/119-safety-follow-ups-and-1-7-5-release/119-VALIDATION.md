---
phase: 119
slug: safety-follow-ups-and-1-7-5-release
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-14
---

# Phase 119 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 (unittest.TestCase style), pytest-timeout 60 s; Angular Karma/Jasmine (CI Docker); Playwright e2e (CI) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_transfer_state_safety.py tests/unittests/test_controller/test_import_ambiguity.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py` (authority: CI `unittests-python`) |
| **Lint** | `ruff check src/python/` (whole tree, ruff 0.15.22) |
| **Estimated runtime** | quick ~1 s; full ~60–120 s |

---

## Sampling Rate

- **After every task commit:** quick run command + `ruff check src/python/`
- **After every plan wave:** full suite command + ruff
- **Before `/bm:verify-work`:** CI green (python, angular, lint, e2e, packaging-verify); each targeted regression shown red before its fix (REL-03)
- **Max feedback latency:** 120 s

---

## Per-Task Verification Map

Task IDs are filled in by the planner; this map is per requirement (from 119-RESEARCH.md §Validation Architecture).

| Requirement | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-------------|----------|------------|-----------|-------------------|-------------|--------|
| XFER-06 | Stale prompt after timeout never yields trusted `[]`; resync then real status | lftp command injection (hex nonce only) | unit, RED first | `pytest tests/unittests/test_lftp/test_lftp_resync.py -q` | ❌ W0 | ⬜ |
| XFER-06 | Unsynced + resync fail → status None, queue raises, submitted set untouched | — | unit | same + `test_lftp_manager.py` | ❌ / ✅ | ⬜ |
| DEL-01 | Timer + status None + submitted root → defers; after successful status → deletes | — | unit, RED first | `pytest tests/unittests/test_controller/test_auto_delete_rearm.py -q -k submitted` | ✅ extend | ⬜ |
| DEL-01 | Submitted set thread-safe snapshot | — | unit | `pytest tests/unittests/test_controller/test_lftp_manager.py -q -k lock` | ✅ extend | ⬜ |
| IMP-01 / R10 | Temp file forced on even when config False (both modes); old key loads, ignored; setting removed from UI | — | unit + Angular | `pytest ... test_lftp_manager.py test_scan_manager.py -q -k temp` + CI angular | ✅ extend | ⬜ |
| IMP-02 | Arr client: shape validation, unavailable on errors/non-200/bad JSON, size cap, timeouts, no key in logs | key leak, log injection, DoS | unit (mock `requests.get`) | `pytest tests/unittests/test_controller/test_arr_queue.py -q` | ❌ W0 | ⬜ |
| IMP-02 | Gate verdict matrix: proven / still downloading / no entry / ambiguous / unavailable; strong identity (outputPath basename == root); multi-arr (D-17: one arr down, other proves → release; uncertain → hold); both disabled → stability path (D-16); backoff growth/reset; one fetch per arr per cycle | — | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -q` | ❌ W0 | ⬜ |
| IMP-02 | Obsession replay: holds while downloading, queues after completed; hold_reason in model; no cooldown stamp while held | — | unit, RED first | `pytest tests/unittests/test_controller/test_auto_queue.py -q -k completion` | ✅ extend | ⬜ |
| IMP-02 / R6 | USER queue unverified → needs-confirmation; with flag → submitted once; flag not persisted; WARNING log on manual release | gate bypass | unit | `pytest ... test_controller_unit.py test_web/test_handler/test_controller_handler.py -q -k release` | ✅ extend | ⬜ |
| IMP-02 / R5 | hold_reason serialized; model diff on reason change; log only on reason change/clear | — | unit | `pytest ... test_serialize_model.py test_model_builder.py -q -k hold` | ✅ extend | ⬜ |
| IMP-02 / R5–R6 | UI: Waiting badge + reason; confirm → re-dispatch with flag | — | Angular unit | CI `make run-tests-angular` | ✅ extend | ⬜ |
| IMP-03 | Days of Hope replay: early credit, immediate persist, no timer, restart round trip, arm-on-commit, coverage passes | — | unit, RED first | `pytest tests/unittests/test_controller/test_import_credit.py -q` | ❌ W0 | ⬜ |
| IMP-03 | Ambiguous basename still rejected; foreign dir never credited; credit alone never deletes | — | unit | same + `test_import_ambiguity.py` | ✅ extend | ⬜ |
| REL-02 | No `./` members, twine check, clean-venv install, `seedsyncarr --help` | — | CI job + local | `python -m build && twine check dist/* && <member-check> && pip install dist/*.whl` | ❌ W0 | ⬜ |
| REL-03 | Full suite, ruff, CI green; release-image smoke (startup, real transfer, import visibility + webhook, auto-cleanup, settings persistence, restart, held item visible); NAS digest + scan recovery | — | manual/CI | 118-style runbook | ✅ precedent | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_lftp/test_lftp_resync.py` — fake-stream harness (XFER-06)
- [ ] `tests/unittests/test_controller/test_arr_queue.py` — real-shape QueueResource fixtures (IMP-02)
- [ ] `tests/unittests/test_controller/test_completion_gate.py` (IMP-02)
- [ ] `tests/unittests/test_controller/test_import_credit.py` (IMP-03)
- [ ] `tests/unittests/test_controller/base.py` — CompletionGate patcher defaulting to PROVEN
- [ ] CI `verify-python-package` job (REL-02)
- [ ] e2e `seed-state.ts` release flag / gate stub

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Release-image smoke | REL-03 | Needs real seedbox + arr + NAS | Pull exact `:1.7.5`; startup; real transfer (observe `.lftp` then rename); import visibility + webhook; auto-cleanup; settings persistence; restart; held item shows Waiting + reason when arr unreachable |
| NAS deploy verification | REL-03 | Production host | Pin compose `:1.7.5`; RepoDigests == published digest; successful scan after any startup scanner error; arr reachable (no steady-state holds) |
| PyPI publication | REL-02 | External registry | Tag CI publish succeeds; `pip install seedsyncarr==1.7.5` in clean venv |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
