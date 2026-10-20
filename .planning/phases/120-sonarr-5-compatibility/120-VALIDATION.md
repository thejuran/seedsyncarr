---
phase: 120
slug: sonarr-5-compatibility
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-20
---

# Phase 120 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ^9.0.3 + pytest-timeout (60 s), unittest-style classes |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_sonarr5 tests/integration/test_web/test_handler/test_webhook.py tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py -q -p no:cacheprovider` |
| **Full suite command** | `cd src/python && poetry run pytest tests/unittests tests/integration -q -p no:cacheprovider` plus `ruff check src/python/` (whole tree; CI pins ruff 0.15.22) |
| **Estimated runtime** | ~5 seconds quick; full suite a few minutes |

---

## Sampling Rate

- **After every task commit:** quick run command + `ruff check src/python/`
- **After every plan wave:** full suite + ruff
- **Before `/bm:verify-work`:** full suite green, ruff clean, CI `unittests-python` and `lint-python` green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

Filled by the planner/executor from PLAN.md task IDs. Requirement → test map (from 120-RESEARCH.md):

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| SON5-01 | Captured Sonarr 5 status → success + recorded 5.x version; container-name private URL → documented error | unit | `pytest tests/unittests/test_sonarr5/test_sonarr5_system_status.py -q` | ❌ W0 | ⬜ pending |
| SON5-02 | Incomplete → `still_downloading` hold; complete (same downloadId) → released; no-match / API error / unrelated completed → hold kept | unit | `pytest tests/unittests/test_sonarr5/test_sonarr5_queue.py -q` | ❌ W0 | ⬜ pending |
| SON5-03 | Test event → 200, nothing imported; Download → exactly the correct file imported; HMAC enforced | unit + integration | `pytest tests/unittests/test_sonarr5/test_sonarr5_webhook.py tests/integration/test_web/test_handler/test_webhook.py -q` | ❌ W0 | ⬜ pending |
| SON5-04 | Manifest complete (tested 5.x build + scenario per fixture, all `source: live`); no keys/IPs/hostnames/personal paths; queue fixtures share downloadId | unit (hygiene) | `pytest tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py -q` | ❌ W0 | ⬜ pending |
| SON5-05 | Release decision recorded; if release: regression RED→GREEN, CI green, sandbox digest match | gate/manual | per release runbook | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/python/tests/fixtures/sonarr5/` with `manifest.json`
- [ ] `src/python/tests/unittests/test_sonarr5/__init__.py`, `fixtures.py`
- [ ] The four test modules above

*No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Test Connection success via Tailscale URL | SON5-01 | Needs live sandbox | 120-RESEARCH.md L1 |
| Live hold → release for one downloadId, both queue snapshots | SON5-02 | Needs live download | 120-RESEARCH.md L2 |
| Live Test event + real import webhook | SON5-03 | Needs live Sonarr 5 | 120-RESEARCH.md L3 |
| Exact-secret count = 0 on sanitized fixtures | SON5-04 | Uses real secrets; never committed | 120-RESEARCH.md L4 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
