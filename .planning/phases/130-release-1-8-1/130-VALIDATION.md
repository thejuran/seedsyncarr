---
phase: 130
slug: release-1-8-1
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-20
---

# Phase 130 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 130-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x via Poetry; Karma + Jasmine (Angular); Playwright e2e (CI); `node --test` (release-metadata verifier) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]`; `src/angular` Karma config; `.github/workflows/ci.yml` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py tests/unittests/test_controller/test_arr_queue.py tests/integration/test_web/test_handler/test_arr_key_parity.py tests/unittests/test_common/test_arr_api_key.py -q -p no:cacheprovider` |
| **Full suite command** | Local (macOS ignores): `cd src/python && poetry run pytest tests/unittests tests/integration -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py --ignore=tests/integration/test_lftp` + `ruff check src/python/`; authority: PR CI |
| **Estimated runtime** | ~180 seconds local full suite |

---

## Sampling Rate

- **After every task commit:** quick run command; whole-tree `ruff check src/python/` for any Python-touching commit; for the Angular lock commit `npm ci && npm run lint` + bundle identity check
- **After every plan wave:** local full suite + `make run-tests-angular` + packaging check + `node scripts/verify-release-metadata.mjs 1.8.1`
- **Before `/bm:verify-work`:** release PR CI and tag CI all green; smoke and deploy verdict tables all PASS; owner confirmations recorded
- **Max feedback latency:** 180 seconds (local); CI is the authority

---

## Per-Task Verification Map

| Req / SC | Behavior | Test Type | Automated Command / Evidence | File Exists | Status |
|----------|----------|-----------|-----------------------------|-------------|--------|
| REL-07 SC1 (ARR) | Padded-key regression present and green | unit + integration | `poetry run pytest "tests/unittests/test_controller/test_arr_queue.py::TestArrQueueFetch::test_padded_in_memory_key_is_sent_normalized" tests/integration/test_web/test_handler/test_arr_key_parity.py -q -p no:cacheprovider`; fail-before cited from 128-VERIFICATION.md | ✅ | ⬜ pending |
| REL-07 SC1 (WEB) | Cleanup isolation regression present and green | unit | `poetry run pytest tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider`; fail-before cited from 129-VERIFICATION.md | ✅ | ⬜ pending |
| REL-07 SC1 | Full suite, ruff, Angular, e2e, release CI | CI | `ruff check src/python/`; `gh pr checks <release PR>`; tag run jobs all success | ✅ | ⬜ pending |
| REL-07 SC1 | Release metadata | script | `node scripts/verify-release-metadata.mjs 1.8.1` | ✅ | ⬜ pending |
| REL-07 SC2 | soupsieve ≥4.0.0 in lock; not shipped | script | `grep -A1 '^name = "soupsieve"' src/python/poetry.lock`; image import check | ✅ | ⬜ pending |
| REL-07 SC2 | minimatch fixed; UI bundle unchanged | script | `npm ls minimatch --all`; bundle sha256 identity vs 1.8.0; diff limited to `package-lock.json` | ✅ | ⬜ pending |
| REL-07 SC2 | Alerts triaged and surfaced | API + owner | alert count before → after; D-07 list + owner reply recorded | evidence | ⬜ pending |
| REL-08 SC3 | Smoke by exact digest | manual-live | SMOKE evidence verdict table | evidence | ⬜ pending |
| REL-08 SC4 | Prod by same digest; scan + queue check + owner | manual-live | DEPLOY evidence verdict table | evidence | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Smoke harness prep (`130-teardown.sh` from `126-teardown.sh`, `bash -n` + `shellcheck`) happens at the start of the smoke plan.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sandbox smoke (setup, padded-key queue check on sonarr-v4 + radarr, container + in-app restart clean shutdown, one real transfer) | REL-08 | Needs live NAS, seedbox, arr instances | Per smoke plan; evidence in 130-SMOKE-EVIDENCE.md |
| Production deploy (same digest, scan, queue check, wud restore, owner confirm) | REL-08 | Live production | Per deploy plan; evidence in 130-DEPLOY-EVIDENCE.md |
| Owner checkpoints (pre-tag, pre-prod) | REL-07, REL-08 | Product decision | Verbatim owner replies recorded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
