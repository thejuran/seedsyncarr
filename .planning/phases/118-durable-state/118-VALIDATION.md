---
phase: 118
slug: durable-state
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-08
---

# Phase 118 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `118-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest-timeout 60s/test, `unittest.TestCase` classes) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_common/test_persist.py tests/unittests/test_common/test_config.py tests/unittests/test_seedsyncarr.py -q -p no:cacheprovider` |
| **Full suite command** | Host part 1: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py`; host part 2: those four files individually under `perl -e 'alarm 60; exec @ARGV'` (baseline 21 failed / 3 errors, must be unchanged); authority: CI `unittests-python` |
| **Lint** | `poetry run ruff check src/python/` and `uvx ruff@0.15.22 check src/python/` (whole tree) |
| **Estimated runtime** | quick ~10 s; host part 1 ~2–4 min |

---

## Sampling Rate

- **After every task commit:** quick run + `poetry run ruff check src/python/`
- **After every plan wave:** host part 1 + ruff (both versions)
- **Before `/bm:verify-work`:** full suite green; CI green on the tag commit
- **Max feedback latency:** ~10 seconds (quick run)

---

## Per-Task Verification Map

Task IDs are filled in by the planner; requirement → command mapping is fixed.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| PERSIST-01 | Serialization failure → original intact, no temp, raises | unit (RED) | `pytest tests/unittests/test_common/test_persist.py -q -k serialization` | ❌ W0 | ⬜ pending |
| PERSIST-01 | Write failure (lone surrogate) → same | unit (RED) | `-k write_failure` | ❌ W0 | ⬜ pending |
| PERSIST-01 | File fsync failure → same | unit (RED) | `-k file_fsync` | ❌ W0 | ⬜ pending |
| PERSIST-01 | Replace failure → same | unit (RED) | `-k replace_failure` | ❌ W0 | ⬜ pending |
| PERSIST-01 | Temp-creation failure → same | unit (RED) | `-k temp_creation` | ❌ W0 | ⬜ pending |
| PERSIST-01 | Failure with no pre-existing target → dir empty | unit | `-k no_existing_target` | ❌ W0 | ⬜ pending |
| PERSIST-01 | Interrupt (`ServiceExit`) mid-write cleans up, original intact | unit | `-k interrupt` | ❌ W0 | ⬜ pending |
| PERSIST-02 | Success → content + `0600` + no temp left | unit | existing `test_to_file_*` + `-k no_temp_after_success` | partial ✅ | ⬜ pending |
| PERSIST-02 | Dir fsync failure → committed, logged on `seedsyncarr.Persist`, no raise | unit (RED) | `-k directory_fsync` | ❌ W0 | ⬜ pending |
| PERSIST-02 | Temp created in target dir | unit | `-k same_directory` | ❌ W0 | ⬜ pending |
| PERSIST-01/02 | Three real persist types round-trip via new `to_file` | unit (preservation) | `test_config.py::test_to_file`, `test_seedsyncarr.py` re-encrypt tests, controller/auto-queue persist tests | ✅ | ⬜ pending |
| REL-01 g1 | All 116 + 117 + 118 RED regressions fail-before/pass-after on release SHA | regression | `pytest -v -k "<names>"`; evidence → `118-REL01-EVIDENCE.md` | ✅ | ⬜ pending |
| REL-01 g2 | Full suite + whole-tree ruff | suite | above; CI green on merge/tag commit | ✅ | ⬜ pending |
| REL-01 g3 | Image smoke: startup, status, settings persist, restart | manual-scripted | RESEARCH Smoke Test Recipe | n/a | ⬜ pending |
| REL-01 g4 | NAS `:1.7.4` same digest, config loads, clean scan after any error | manual-scripted | RESEARCH NAS Deploy Recipe steps 3–5 | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] RED tests in `src/python/tests/unittests/test_common/test_persist.py` (new class, e.g. `TestPersistAtomicWrite`), committed **before** the fix; RED run recorded against the pre-fix SHA in `118-REL01-EVIDENCE.md`
- No framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Release image smoke test | REL-01 | Needs the published `:1.7.4` image and a Docker host | RESEARCH Smoke Test Recipe (NAS port 8801) |
| NAS deploy same digest + scanner recovery | REL-01 | Production deploy on owner hardware | RESEARCH NAS Deploy Recipe steps 3–5 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
