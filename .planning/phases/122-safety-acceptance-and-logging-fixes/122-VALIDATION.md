---
phase: 122
slug: safety-acceptance-and-logging-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-21
---

# Phase 122 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ^9.0.3 (unittest.TestCase style), pytest-timeout 60 s/test |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_handler/test_controller_handler.py tests/unittests/test_web/test_rate_limit.py tests/unittests/test_controller/test_completion_gate.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests -p no:cacheprovider -q` AND `ruff check src/python/` (separate CI gate, whole tree) |
| **Estimated runtime** | quick ~15 s; full ~90 s |

---

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** full suite command + ruff
- **Before `/bm:verify-work`:** full suite green, PR CI green, SAFE-01 evidence complete, SAFE-02 records updated
- **Max feedback latency:** 90 seconds (unit); live checks are evidence-based, not timed

---

## Per-Task Verification Map

Filled in by the planner and executor per task; the requirement-level map is below.

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| LOG-01 | Webhook Test event logs `<source> webhook test event received` at INFO under the app logger (red before, green after) | unit | `pytest tests/unittests/test_web/test_webhook_handler.py -x` | ❌ W0 (assertion to add) | ⬜ pending |
| LOG-01 | controller/config handler + rate_limit lines reach the app logger child | unit | `pytest tests/unittests/test_web/test_handler/test_controller_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_rate_limit.py -q` | ❌ W0 | ⬜ pending |
| LOG-01 | No newly visible line logs secrets/tokens/bodies (D-14) | desk-check + grep | review table in plan summary | N/A | ⬜ pending |
| LOG-02 | Proof-based release logs "cleared", not "dropped" | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k proven -x` | ✅ | ⬜ pending |
| LOG-02 | Prune + no-arr paths log "dropped (<reason>)", not "cleared" (red before, green after) | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k "dropped or no_targets" -x` | ❌ W0 (rename+flip 2 tests) | ⬜ pending |
| SAFE-01 | D-06 (a)–(e) and D-07 scenarios pass on the sandbox `:dev@sha256` build | live evidence | evidence file `122-SAFE01-EVIDENCE.md` | N/A | ⬜ pending |
| SAFE-02 | Both incident records carry per-finding status; close rule D-12 applied | desk-check | grep for status table rows in both records | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_web/test_webhook_handler.py`: fail-before/pass-after Test-event INFO assertion
- [ ] `tests/unittests/test_web/test_handler/test_controller_handler.py`, `test_config_handler.py`: logger-reach checks; update constructor call sites for new `context` param
- [ ] `tests/unittests/test_web/test_rate_limit.py`: supplied logger is used
- [ ] `tests/unittests/test_controller/test_completion_gate.py`: rename+flip `test_hold_cleared_when_no_longer_candidate`, `test_no_targets_clears_existing_holds` to "dropped"
- [ ] `tests/unittests/test_sonarr5/test_sonarr5_system_status.py`: update `ConfigHandler(...)` call site

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extraction staging, early credit, arm-on-commit, revalidation, restart persistence, Waiting hold + one-shot release on a running build | SAFE-01 | Requires live sandbox, seedbox transfer and real timing | Per plan tasks; record log excerpts, timestamps, file state in `122-SAFE01-EVIDENCE.md` |
| Sandbox pin restored to `:1.7.6`, `webhook_secret` and synthetic material restored/removed | SAFE-01 (D-02, D-08) | Live infra state | Fresh-session check printing restored pin and empty secret length, no probe files |
| Remaining production cleanup confirmed by owner | SAFE-02 (D-11, D-12) | Owner-only action | Owner confirms checklist items |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
