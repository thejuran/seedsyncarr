---
phase: 119
slug: safety-follow-ups-and-1-7-5-release
status: approved
nyquist_compliant: true
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

Task IDs reference `{plan}-T{n}` in the 119-NN-PLAN.md files. Wave 0 test files are created inside plans 01/04/05/06 Task 1 (RED-first), so `wave_0_complete` stays false until those tasks land.

| Task ID | Requirement | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|---------|-------------|----------|------------|-----------|-------------------|-------------|--------|
| 119-01-T1 | XFER-06 | RED: fake pty stream shows a stale prompt becoming a trusted empty job list | lftp command injection (hex nonce only) | unit, RED first | `pytest tests/unittests/test_lftp/test_lftp_resync.py -q` | ❌ W0 (created by this task) | ⬜ |
| 119-01-T2 | XFER-06 | GREEN: synced flag + nonce sentinel resync; status None / queue raises while unsynced; submitted set untouched | same | unit | `pytest tests/unittests/test_lftp tests/unittests/test_controller/test_lftp_manager.py -q` | ✅ after T1 | ⬜ |
| 119-02-T1 | REL-02 | hatch `only-include` fix; member-path checker rejects `./` members; non-strict `twine check` | — | script + local | `python -m build && twine check dist/* && <member-check>` | ❌ W0 (created by this task) | ⬜ |
| 119-02-T2 | REL-02 | `verify-python-package` CI job gates publish-pypi / build-docker-image; clean-venv install + `seedsyncarr --help` | — | CI job | CI workflow run on push | ❌ W0 (created by this task) | ⬜ |
| 119-03-T1 | DEL-01 | RED: Timer fires on a submitted-unobserved root with status unavailable; lock-contract tests; barrier-controlled two-thread delete-vs-queue overlap tests (`test_queue_refused_while_auto_delete_holds_root`, `test_auto_delete_defers_while_queue_submission_holds_root`, `test_manual_delete_local_refused_while_auto_delete_holds_root`, `test_reservation_released_on_every_timer_path`); RootReservations contract | T-119-42, T-119-43 | unit, RED first | `pytest tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_root_reservation.py -q -k "submitted or lock or before_lftp or reservation or holds_root"` | ✅ extend / ❌ W0 `test_root_reservation.py` | ⬜ |
| 119-03-T2 | DEL-01 | GREEN: lock-protected submitted set, add-before-queue ordering, Timer guard, per-root reservation held by the Timer through delete_local and by CommandProcessor across QUEUE/DELETE_LOCAL (defer / 409 / AUTO skip on conflict) | T-119-42, T-119-43 | unit | same + `test_auto_delete.py test_transfer_state_safety.py test_controller_unit.py` | ✅ after T1 | ⬜ |
| 119-04-T1 | IMP-02 | ArrQueueClient: QueueRecord normalization, malformed records preserved as `valid=False` (never dropped), unattributable record rejects the snapshot, unavailable on errors/non-200/bad JSON, streamed read with per-chunk 8 MiB cap, HTTP on a daemon worker (one in flight per target) behind a NON-BLOCKING `start_fetch`/`poll`/`abandon` handoff (leaf lock; no join/sleep/wait on the controller thread) with a 20 s poll-side overrun that abandons blocked reads and discards late results by fetch id (`test_fetch_oversized_chunked_response_aborts_at_cap`, `test_fetch_slow_trickle_exceeds_deadline_worker_side`, `test_fetch_deadline_covers_connect_phase`, `test_poll_before_completion_is_pending_and_nonblocking`, real-socket `test_poll_reports_overrun_without_blocking_real_socket` (every poll < 100 ms while blocked), `test_start_fetch_refused_while_prior_worker_alive_and_late_result_discarded`, `test_abandon_discards_outstanding_fetch_result`), `response.close()` on every path, `ArrTarget.identity`, no key/fingerprint in logs | key leak, log injection, DoS, T-119-44, T-119-49, T-119-53 | unit (mock `requests.get` + fake clock; ThreadingHTTPServer on 127.0.0.1 for the two transport tests) | `pytest tests/unittests/test_controller/test_arr_queue.py -q` | ❌ W0 (created by this task) | ⬜ |
| 119-04-T2 | IMP-02 | RED (test commit first, ModuleNotFoundError) then GREEN: CompletionGate verdict matrix (proven / still downloading / no entry / ambiguous / unavailable), strong identity, mixed valid/malformed matching records never PROVEN, lifecycle-scoped proof cache (live evidence first; same-name same-size re-grab overrides; cache unused while any arr unavailable; `invalidate` drops + fences PER TARGET on snapshot generations — `test_invalidate_then_verdict_before_refresh_deadline_requires_fresh_fetch`, `test_fence_blocks_absence_cache_while_target_in_backoff`, `test_stale_pre_invalidation_snapshot_never_proves`; a fresh responding arr proves alone after invalidation — `test_fresh_proof_from_responding_arr_after_invalidation_while_other_unavailable`; configuration identity (code, url, key fingerprint) reset incl. abandoning in-flight fetches — `test_url_change_same_service_clears_snapshots_and_backoff`, `test_url_change_abandons_in_flight_fetch_and_never_applies_its_result`), multi-arr D-17 before and after invalidation, both-disabled D-16, backoff growth/reset, one fetch START per arr per cycle, non-blocking evaluate/verdict with provisional holds while a first/forced fetch is pending (`test_evaluate_never_blocks_on_pending_fetch`, `test_two_stalled_targets_do_not_block_controller` — real client + trickle server, `test_pending_result_applied_on_later_evaluate`, `test_overrun_pending_fetch_becomes_unavailable_hold_with_backoff`, `test_verdict_is_nonblocking_and_returns_provisional_hold_for_fenced_pending_target`) | T-119-44, T-119-45, T-119-48, T-119-53, T-119-54, T-119-55 | unit, RED first | `pytest tests/unittests/test_controller/test_completion_gate.py -q` | ❌ W0 (created by this task) | ⬜ |
| 119-05-T1 | IMP-03 | RED: Days of Hope replay and IMP-03 contract tests (early credit, no timer, restart round trip, foreign dir never credited) plus pending-notice lifecycle regressions: discard on USER requeue cannot credit the new attempt, revalidation against new ambiguity / changed path / root removal, stale lifecycle generation never credits | T-119-50, T-119-51 | unit, RED first | `pytest tests/unittests/test_controller/test_import_credit.py -q` | ❌ W0 (created by this task) | ⬜ |
| 119-05-T2 | IMP-03 | GREEN: child credit, `_PendingNotice` bound to resolved path + root lifecycle generation and revalidated each cycle before either acceptance path, `_discard_pending_notices` from `__process_commands` on USER QUEUE, arm-on-commit, immediate atomic persist (D-20); ambiguous basename still rejected; credit alone never deletes | T-119-50, T-119-51 | unit | same + `test_import_ambiguity.py` | ✅ after T1 | ⬜ |
| 119-06-T1 | IMP-01 / IMP-02 | RED: Obsession replay in the sweep, forced-temp contract (both modes, old key loads/ignored), execution-time gate and release-flag tests; `base.py` CompletionGate patcher defaulting to PROVEN | gate bypass | unit, RED first | `pytest tests/unittests/test_controller/test_auto_queue.py -q -k completion` + `test_lftp_manager.py test_scan_manager.py -k temp` | ✅ extend / ❌ W0 patcher | ⬜ |
| 119-06-T2 | IMP-01 / IMP-02 | GREEN: temp files forced on, gate constructed in Controller, sweep gated before the cooldown stamp | — | unit | same | ✅ after T1 | ⬜ |
| 119-06-T3 | IMP-02 / R6 | GREEN: CommandProcessor re-check taken INSIDE the root reservation (`test_gate_recheck_runs_inside_root_reservation`); proof consumed after submission (`test_proof_consumed_on_successful_submission`); re-queue after an interrupted transfer re-authorized by a fresh single-arr proof with the real gate behind the patcher (`test_requeue_after_submission_reproves_from_responding_arr_while_other_unavailable`, with `process()` < 0.1 s while the forced refresh is pending); USER queue while evidence is still in flight → 428 immediately, no controller block, succeeds on the next click (`test_user_queue_returns_428_immediately_while_fetch_pending`); USER queue unverified → needs-confirmation (428); with flag → submitted once; flag not persisted; WARNING log on manual release | gate bypass, T-119-46, T-119-47, T-119-54 | unit | `pytest ... test_controller_unit.py test_web/test_handler/test_controller_handler.py -q -k "release or proof or reservation"` | ✅ extend | ⬜ |
| 119-07-T1 | IMP-02 / R5 | `ModelFile.hold_reason` + `ModelBuilder.set_hold_reasons` applied to DEFAULT roots; model diff on reason change | — | unit | `pytest ... test_model_builder.py -q -k hold` | ✅ extend | ⬜ |
| 119-07-T2 | IMP-02 / R5 | Holds fed through ModelPipeline; `hold_reason` serialized; log only on reason change/clear; one `on_lifecycle_reset` callback into `Controller._on_root_lifecycle_reset` invalidates (fences) the proof AND discards pending import notices on the same-name re-grab lifecycle reset and on root REMOVED diffs (`test_controller_unit.py` lifecycle/apply-diff classes assert both) | T-119-45, T-119-52 | unit | `pytest ... test_serialize_model.py test_controller_unit.py -q -k "hold or lifecycle or invalidate or removed"` | ✅ extend | ⬜ |
| 119-08-T1 | IMP-02 / R5 | UI: hold plumbing model-file → view-file → transfer-row; Waiting badge, secondary style, reason label + title; five exact labels | XSS (interpolation only) | Angular unit | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` (CI `make run-tests-angular` authority) | ✅ extend | ⬜ |
| 119-08-T2 | IMP-02 / R6 | UI: 428 → confirm (verbatim text) → one-shot re-dispatch with `release_unverified: true` for the 428 files only; cancel sends nothing | gate bypass | Angular unit | same | ✅ extend | ⬜ |
| 119-12-T1 | IMP-01 / R10 | `use_temp_file` toggle removed from Settings, config key retained; e2e seed `queueFile` sends `?release_unverified=true` | — | Angular unit + e2e tsc | `grep` gates + `cd src/e2e && npx tsc --noEmit -p tsconfig.json` | ✅ extend | ⬜ |
| 119-12-T2 | IMP-01 / IMP-02 / R10 | Docs: `use_temp_file` ignored/always on; Completion verification subsection with five labels, verbatim confirm text, D-16 limitation | docs over-promise | grep gate | `grep -c 'Transfer and release this item anyway' docs/CONFIGURATION.md` == 1 | ✅ extend | ⬜ |
| 119-09-T1 | REL-02 / REL-03 | 1.7.5 version bumps, Dependabot #93/#123/#124 roll-in (D-21), CHANGELOG/notes | — | CI | push → CI green (python, angular, lint, e2e, packaging-verify) | ✅ | ⬜ |
| 119-09-T2 | REL-03 | Gate evidence: each targeted regression shown RED before its fix, GREEN after (five RED commits incl. `test(119-04)`), with the codex adversarial regressions from rewrites 1-3 (delete-vs-queue barrier, same-name same-size re-grab, mixed valid/malformed records, proof consumed on submission, invalidate-then-verdict fence, URL/key identity reset, bounded streamed fetch (cap + worker deadline + real-socket non-blocking poll/overrun), controller never blocks on a stalled arr (gate + two-stalled-targets + CommandProcessor 428-immediately), fresh single-arr proof after invalidation under D-17 (gate + CommandProcessor), pending-notice discard on USER requeue, pending-notice revalidation, lifecycle reset of both caches) named individually; full suite; ruff 0.15.22; packaging; CI green | — | unit + CI | full suite command + `ruff check src/python/` | ✅ | ⬜ |
| 119-09-T3 | REL-03 | Owner approval checkpoint to publish 1.7.5 | — | manual | checkpoint:decision | — | ⬜ |
| 119-10-T1 | REL-02 / REL-03 | wud pause, tag v1.7.5, tag CI (Docker/GitHub/PyPI), PyPI verified, digest recorded | — | CI + registry | `pip install seedsyncarr==1.7.5` in clean venv; `gh run` status | ✅ | ⬜ |
| 119-10-T2 | REL-03 | Smoke on the exact `:1.7.5` digest (startup, real transfer with `.lftp`, webhook import, auto-cleanup, settings, restart, held item + manual release) | — | manual (see table below) | 118-style runbook | ✅ precedent | ⬜ |
| 119-10-T3 | REL-03 | Owner go-ahead for the production deploy | — | manual | checkpoint:human-verify | — | ⬜ |
| 119-11-T1 | REL-03 | NAS deploy by digest with verified backups; startup/scan/arr reachability/persist; wud restore | — | manual (see table below) | `ssh nas` digest compare + log scan | ✅ precedent | ⬜ |
| 119-11-T2 | REL-03 | Owner confirmation of the deployed 1.7.5 | — | manual | checkpoint:human-verify | — | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_lftp/test_lftp_resync.py` — fake-stream harness (XFER-06, 119-01-T1)
- [ ] `tests/unittests/test_controller/test_arr_queue.py` — real-shape QueueResource fixtures + local ThreadingHTTPServer trickle harness (IMP-02, 119-04-T1)
- [ ] `tests/unittests/test_controller/test_completion_gate.py` — `FakeArrClient` (reused by 119-06) + real-client stalled-target tests (IMP-02, 119-04-T2)
- [ ] `tests/unittests/test_controller/test_import_credit.py` (IMP-03, 119-05-T1)
- [ ] `tests/unittests/test_controller/test_root_reservation.py` (DEL-01, 119-03-T1)
- [ ] `tests/unittests/test_controller/base.py` — CompletionGate patcher defaulting to PROVEN (119-06-T1)
- [ ] CI `verify-python-package` job (REL-02, 119-02-T2)
- [ ] e2e `seed-state.ts` release flag (119-12-T1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Release-image smoke | REL-03 | Needs real seedbox + arr + NAS | Pull exact `:1.7.5`; startup; real transfer (observe `.lftp` then rename); import visibility + webhook; auto-cleanup; settings persistence; restart; held item shows Waiting + reason when arr unreachable |
| NAS deploy verification | REL-03 | Production host | Pin compose `:1.7.5`; RepoDigests == published digest; successful scan after any startup scanner error; arr reachable (no steady-state holds) |
| PyPI publication | REL-02 | External registry | Tag CI publish succeeds; `pip install seedsyncarr==1.7.5` in clean venv |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (checkpoint tasks in 119-09/10/11 are manual by design; every auto task has an `<automated>` gate)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (created RED-first inside 119-01/02/04/05/06 Task 1)
- [x] No watch-mode flags (`--watch=false` on Angular; pytest `-p no:cacheprovider`)
- [x] Feedback latency < 120s (quick run ~1 s; Angular headless and full suite within budget)
- [x] `nyquist_compliant: true` set in frontmatter
- [ ] `wave_0_complete: true` — set after 119-01/02/03/04/05/06 Task 1 land

**Approval:** approved 2026-10-14 for planning (execution evidence pending)
