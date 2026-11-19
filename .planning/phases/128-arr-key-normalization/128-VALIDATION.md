---
phase: 128
slug: arr-key-normalization
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-18
---

# Phase 128 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (unittest.TestCase style; WebTest for integration) |
| **Config file** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`, `fail_under = 88`) |
| **Quick run command** | `cd src/python && pytest -q -p no:cacheprovider tests/unittests/test_common/test_arr_api_key.py tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py tests/integration/test_web/test_handler/test_arr_key_parity.py` (the parity module exists from 128-04 onward; leave it out before then) |
| **Full suite command** | `cd src/python && pytest -q -p no:cacheprovider` + `ruff check src/python/` (repo root, whole tree). Phase gate: `cd src/python && poetry run pytest --cov -q` (≥ 88), which runs every test and so also serves as the full-suite run |
| **Estimated runtime** | quick < 15 s; full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run quick run command + `ruff check src/python/`
- **After every plan wave:** Run full `pytest -q -p no:cacheprovider` + whole-tree ruff
- **Before `/bm:verify-work`:** Full suite green, ruff clean, coverage ≥ 88
- **Max feedback latency:** 15 seconds (quick command)

---

## Per-Task Verification Map

Requirement → test map (from 128-RESEARCH.md §Validation Architecture). Run every command from `src/python`. Every Automated Command cell is a complete command that runs as written; a selector that matches zero tests counts as a failure.

| Requirement | Behavior | Test Type | Automated Command | Plan / Task | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|-------------|--------|
| ARR-01 | Padded key saved trimmed (Sonarr + Radarr) | unit + integration | `pytest -q -p no:cacheprovider tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py -k "arr_key and trimmed"` | 128-02 Task 1 | ✅ | ✅ green |
| ARR-01 / D-03 | Inner-invalid key → 400 "<Svc> API key contains invalid characters", stored unchanged, value not echoed | unit + integration | `pytest -q -p no:cacheprovider tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py -k "arr_key and invalid"` | 128-02 Task 1 | ✅ | ✅ green |
| ARR-01 / D-04 | Whitespace-only → 400 "Invalid request body", stored unchanged | unit + integration | `pytest -q -p no:cacheprovider tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py -k "arr_key and whitespace_only"` | 128-02 Task 1 | ✅ | ✅ green |
| ARR-01 / D-01 | Test Connection behavior unchanged after refactor | unit (existing) | `pytest -q -p no:cacheprovider tests/unittests/test_web -k "whitespace_stripped or newline_never"` | existing tests; re-run in 128-02 Task 2 | ✅ | ✅ green |
| ARR-01 / ARR-02 / D-01 | Shared rule table (trim + printable ASCII without space, NBSP rows pinned) | unit | `pytest -q -p no:cacheprovider tests/unittests/test_common/test_arr_api_key.py` | 128-01 Task 1 | ✅ | ✅ green |
| ARR-02 | In-memory padded key sent normalized by queue client (fail-before/pass-after) | unit | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_arr_queue.py -k padded` | 128-03 Task 1 | ✅ | ✅ green |
| ARR-02 | Padded vs trimmed key → same identity (no spurious gate reset) | unit | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_arr_queue.py -k identity` | 128-03 Task 1 | ✅ | ✅ green |
| ARR-02 | One rule across three paths: string-input parity over one real Config (Save, Test Connection, queue check) | integration | `pytest -q -p no:cacheprovider tests/integration/test_web/test_handler/test_arr_key_parity.py -k "all_three_paths or live_config"` | 128-04 Task 1 | ✅ | ✅ green |
| ARR-01 / ARR-03 | Null, empty and numeric input handled by each path's own guard (not parity) | integration | `pytest -q -p no:cacheprovider tests/integration/test_web/test_handler/test_arr_key_parity.py -k boundary_specific` | 128-04 Task 1 | ✅ | ✅ green |
| ARR-03 | Empty/invalid key → start_fetch None, no request, thread constructor not called | unit | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_arr_queue.py -k "invalid_key or missing_key"` | 128-03 Task 1 | ✅ | ✅ green |
| ARR-03 | Warn once per key token, debug after, warn again on change and after a valid key | unit | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_arr_queue.py -k "invalid_key and warn"` | 128-03 Task 1 | ✅ | ✅ green |
| ARR-03 | Gate holds `<code>_unavailable` with bad key, including after a valid key (cached evidence discarded) | unit | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_completion_gate.py -k bad_key` | 128-03 Task 1 | ✅ | ✅ green |
| ARR-03 | No key substring in any log line (queue client, gate, parity run) | unit + integration | `pytest -q -p no:cacheprovider tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/integration/test_web/test_handler/test_arr_key_parity.py -k "never_appears_in_logs or logs_reason_without_key or no_key_material"` | 128-03 Task 1, 128-04 Task 1 | ✅ | ✅ green |
| D-07 | Every secret_fields() prop → "<s>.<k> updated", value never echoed in success or refusal; refusal warning carries no value or exception text; non-secret keeps "set to" | unit + integration | `pytest -q -p no:cacheprovider tests/unittests/test_web/test_handler/test_config_handler.py tests/integration/test_web/test_handler/test_config.py -k secret` | 128-02 Task 1 | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `src/python/tests/unittests/test_common/test_arr_api_key.py` — rule table (None, "", whitespace-only, padded valid, inner space, tab, CR/LF, NUL, non-ASCII, NBSP padding and inner NBSP written as `\u00a0` escapes)
- [x] RED tests in existing files above; ARR-02 padded-key test recorded failing before the `enabled_targets` change
- [x] `poetry install --with dev` locally for the coverage gate (no framework install otherwise)

---

## Manual-Only Verifications

All phase behaviors have automated verification. (Live padded-key queue check on a release image is Phase 130's smoke test, out of scope here.)

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-11-19, verification map gate green (every row run, each selects at least one test and passes; whole-tree ruff clean; single-definition grep lists only common/arr_api_key.py and common/__init__.py). Coverage gate NOT reproduced locally: 86.47% (branch, commit 0b9d4e31) against fail_under 88, with the same local exclusions giving 86.39% at the phase base b79b06fb, so the phase raised coverage and did not cause the shortfall. Coverage on the Linux CI run is the authoritative gate result.

### Local gate run (macOS) and exclusions

`cd src/python && poetry run pytest --cov -q -p no:cacheprovider --ignore=tests/unittests/test_controller/test_extract --ignore=tests/unittests/test_controller/test_scan --ignore=tests/integration/test_lftp`
gave 1952 passed, 62 skipped, 12 failed; TOTAL 86.47%.

The excluded or failing modules run only on Linux CI. They do not import the arr code:
- `tests/unittests/test_controller/test_extract/`: hangs indefinitely on macOS
- `tests/unittests/test_controller/test_scan/`: macOS spawn cannot pickle MagicMock (fails at the phase base too)
- `tests/integration/test_lftp/` and `tests/unittests/test_ssh/test_sshcp.py` (11 failures): need the CI `testgroup` account
- `tests/unittests/test_system/test_scanner.py::test_scan_file_with_latin_chars` (1 failure): APFS illegal byte sequence

Their production modules (controller/extract, controller/scan, lftp/lftp.py, ssh/sshcp.py) account for the uncovered lines that push the local total below 88. Phase files: common/arr_api_key.py 100%, controller/arr_queue.py 98%, web/handler/config.py 97%.
