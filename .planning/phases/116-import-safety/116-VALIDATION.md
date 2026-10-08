---
phase: 116
slug: import-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-08
---

# Phase 116 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 116-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + unittest.TestCase classes; pytest-timeout 60 s |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_controller/test_webhook_manager.py tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_import_ambiguity.py -q -p no:cacheprovider` |
| **Full suite command** | Host: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` (compare against host baseline: 21 failed / 3 errors pre-existing, unrelated); CI: `make run-tests-python` |
| **Lint gate** | `cd src/python && poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/` (whole tree) |
| **Estimated runtime** | ~2 s quick; ~76 s full host |

---

## Sampling Rate

- **After every task commit:** quick run command + whole-tree ruff
- **After every plan wave:** full host suite, no new failures vs baseline
- **Before `/bm:verify-work`:** full suite green in CI (`unittests-python` + `lint-python`)
- **Max feedback latency:** ~80 seconds

---

## Per-Task Verification Map

| Behavior | Requirement | Test Type | Fails on main? | Status |
|----------|-------------|-----------|----------------|--------|
| Two releases each with `sample.mkv` → no persist change, no timer, badges unchanged, one warning naming both roots | IMPORT-01 | e2e controller | YES | ⬜ pending |
| Roots differing only by case → rejected | IMPORT-01 | e2e controller | YES | ⬜ pending |
| Root `sample.mkv` + `Rel.A/sample.mkv` → rejected | IMPORT-01 | e2e controller | YES | ⬜ pending |
| `Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv` → rejected; no `imported_children["Pack"]`; warning lists both relative paths | IMPORT-01 | e2e controller | YES | ⬜ pending |
| Delete-time: duplicate video basenames + legacy "fully covered" `imported_children` → not deleted (seed `AutoDeleteManager._persist`, not just controller copy) | IMPORT-01 | unit | YES | ⬜ pending |
| Delete-time: duplicate video basenames, no `imported_children` entry (D-14) → not deleted | IMPORT-01 | unit | YES | ⬜ pending |
| Duplicate-basename skip is terminal: no re-arm, counter cleared, one WARNING | IMPORT-01 | unit | YES | ⬜ pending |
| Duplicate subtitle/metadata basenames alone (`Subs/E01/English.srt` ×2, `.nfo` per disc) do NOT block deletion | IMPORT-01 (D-05a) | unit | passes both | ⬜ pending |
| Ambiguous warning sanitizes CR/LF in name, roots, paths | IMPORT-01 | unit | new | ⬜ pending |
| Unique child → recorded, badge, timer exactly as before | IMPORT-02 | e2e controller | passes both | ⬜ pending |
| Same name enqueued twice → one accepted root, one timer, no ambiguity warning | IMPORT-02 | e2e controller | passes both | ⬜ pending |
| Existing WebhookManager / Window-1 lookup tests migrated to new shape, assertions intact | IMPORT-02 | unit | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New e2e test class with real `WebhookManager` + real `Model` trees (helpers for leaf/pack construction) under `src/python/tests/unittests/test_controller/`
- [ ] Legacy-persist fixture seeding the SAME persist instance held by `AutoDeleteManager._persist`
- [ ] RED evidence: targeted regressions committed first and shown failing (assertion failures) against pre-fix code

---

## Manual-Only Verifications

All phase behaviors have automated verification. Release-image smoke test and NAS deploy belong to REL-01 (Phase 118).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 80s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
