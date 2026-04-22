---
phase: 81-optional-fernet-encryption-at-rest
plan: 03
subsystem: security
tags: [python, cryptography, fernet, encryption, startup, documentation, sec-02]

requires:
  - phase: 81-02
    provides: config.py Config.Encryption + set_keyfile_path + _SECRET_FIELD_PATHS + _decrypt_errors + from_str/to_str hooks

provides:
  - seedsyncarr.py: __FILE_SECRETS_KEY constant, Config.set_keyfile_path() call in __init__, _create_default_config encryption.enabled=False, _reencrypt_plaintext_if_needed() static method, _emit_decrypt_warnings() static method, run() wired with both hooks
  - test_seedsyncarr.py: test_decrypt_failure_emits_warning + test_decrypt_warning_does_not_raise + test_enable_existing_plaintext_reencrypts (SEC-02 #3a/#5b coverage)
  - docs/CONFIGURATION.md: [Encryption] section in INI example + ### [Encryption] subsection + Keyfile operations prose

affects:
  - SEC-02: all 5 success criteria now have automated test coverage

tech-stack:
  added: []
  patterns:
    - _reencrypt_plaintext_if_needed() factored static method (keeps __init__ clean, enables direct testing)
    - _emit_decrypt_warnings() mirrors _emit_startup_warnings() contract (log-only, never raises, getattr fallback)
    - Local imports inside re-encrypt block (is_ciphertext + _SECRET_FIELD_PATHS) — keeps startup hot path narrow

key-files:
  modified:
    - src/python/seedsyncarr.py
    - src/python/tests/unittests/test_seedsyncarr.py
    - docs/CONFIGURATION.md

key-decisions:
  - "_reencrypt_plaintext_if_needed factored into static method — allows direct unit testing without mocking full __init__; __init__ calls it via self.context.config after logger setup; run() invokes it at the top before _emit_startup_warnings"
  - "re-encrypt hook in run() not __init__ — logger + context are not available until run() is reached; symmetric placement with _emit_startup_warnings"
  - "Local imports for is_ciphertext + _SECRET_FIELD_PATHS inside the method body — narrows the startup hot path; module has no side-effect imports per RESEARCH T-81-03-08"
  - "test_enable_existing_plaintext_reencrypts uses configparser.write to manually inject enabled=True into a plaintext-valued settings.cfg — closest to the real 'user edits settings.cfg and restarts' scenario without full __init__ mock"

requirements-completed:
  - SEC-02

duration: 5min
completed: 2026-04-22
---

# Phase 81 Plan 03: Startup Hooks + Tests + CONFIGURATION.md Summary

**Startup seam wired in seedsyncarr.py: keyfile path injection, _reencrypt_plaintext_if_needed() and _emit_decrypt_warnings() static methods; 3 new SEC-02 tests; [Encryption] section in CONFIGURATION.md — SEC-02 end-to-end complete**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-22T18:34:53Z
- **Completed:** 2026-04-22T18:40:00Z
- **Tasks:** 3
- **Files modified:** 3 (seedsyncarr.py, test_seedsyncarr.py, docs/CONFIGURATION.md)

## Accomplishments

- `seedsyncarr.py` wired with all 5 required hooks: `__FILE_SECRETS_KEY` constant, `Config.set_keyfile_path()` in `__init__`, `config.encryption.enabled = False` in `_create_default_config`, `_reencrypt_plaintext_if_needed()` and `_emit_decrypt_warnings()` static methods, both called from `run()` at startup
- 3 new test methods all green: `test_decrypt_failure_emits_warning`, `test_decrypt_warning_does_not_raise`, `test_enable_existing_plaintext_reencrypts` — all 3 map to SEC-02 criteria #3a and #5b
- `docs/CONFIGURATION.md` updated with `[Encryption]` in INI example + `### [Encryption]` subsection + Keyfile operations prose covering backup, manual-edit flow, live flag flips, rotation scope, and decrypt failure warnings
- All 48 phase 81 tests (encryption.py, config.py, seedsyncarr.py) green
- Pre-existing test failures in `test_app_process.py`, `test_multiprocessing_logger.py`, `test_scanner_process.py` confirmed pre-existing (multiprocessing/pickling macOS Python 3.12 issue) — out of scope

## Exact Insertion Points in seedsyncarr.py (post-edit line numbers)

| Symbol | Line |
|--------|------|
| `__FILE_SECRETS_KEY = "secrets.key"` | 30 |
| `Config.set_keyfile_path(...)` in `__init__` | 43 |
| `config.encryption.enabled = False` in `_create_default_config` | 353 |
| `_reencrypt_plaintext_if_needed(...)` call in `run()` | 112–115 |
| `_emit_startup_warnings(...)` call in `run()` | 118 |
| `_emit_decrypt_warnings(...)` call in `run()` | 121 |
| `_reencrypt_plaintext_if_needed` static method | 390–414 |
| `_emit_decrypt_warnings` static method | 416–429 |

## Task 1: _reencrypt_plaintext_if_needed Factoring Decision

**Factored into static method (recommended approach chosen).**

The plan gave two options: (a) inline the re-encrypt block in `__init__`/`run()` or (b) factor into `_reencrypt_plaintext_if_needed(config, config_path, logger)`. Option (b) was chosen because:

1. `run()` stays readable — one descriptive call instead of 8 lines of inline code
2. The static method is directly testable in `TestSeedsyncarrReencrypt` without needing to mock the entire `__init__` chain
3. Matches the existing `_emit_startup_warnings` / `_emit_decrypt_warnings` pattern (all startup side-effects as named static helpers)

## Test Method → SEC-02 Criterion Mapping

| Test | SEC-02 Criterion | Validation Task ID |
|------|------------------|--------------------|
| `test_decrypt_failure_emits_warning` | #5b — clear startup warning on decrypt failure | 81-03-02 |
| `test_decrypt_warning_does_not_raise` | #5b — warning is advisory-only (never raises) | 81-03-02 |
| `test_enable_existing_plaintext_reencrypts` | #3a — startup re-encrypt of plaintext | 81-03-01 |

## Full SEC-02 Criteria Coverage (all 5)

| Criterion | Test | Plan |
|-----------|------|------|
| #1 (keyfile 0600 + 5 secrets encrypted on first enable) | `test_keyfile_is_0600` + `test_enable_new_install_encrypts_on_write` | 81-01 / 81-02 |
| #2 (transparent decrypt on load) | `test_from_file_enabled_decrypts` | 81-02 |
| #3a (startup re-encrypt of plaintext) | `test_enable_existing_plaintext_reencrypts` | **81-03** |
| #3b (plaintext install with flag disabled works unchanged) | `test_encryption_disabled_by_default` | 81-02 |
| #4 (disable → restore plaintext) | `test_disable_restores_plaintext` | 81-02 |
| #5a (keyfile permissions) | `test_keyfile_is_0600` | 81-01 |
| #5b (clear startup warning on decrypt failure) | `test_decrypt_failure_emits_warning` | **81-03** |

## CONFIGURATION.md Changes

The plan's suggested text was used verbatim with no operator-facing rewording. Both changes:
1. INI example block: `[Encryption]\nenabled = False` appended before closing fence (line 67)
2. `### [Encryption]` subsection added after `### [AutoDelete]` with settings table + Keyfile operations bullets (line 155)

## Task Commits

1. **Task 1: Wire keyfile injection + re-encrypt hook + decrypt warnings** — `324f171`
2. **Task 2: Add 3 tests (decrypt-warning + no-raise + re-encrypt)** — `c4bda69`
3. **Task 3: Document [Encryption] section in CONFIGURATION.md** — `d04d4d6`

## Deviations from Plan

None — plan executed exactly as written. The `_reencrypt_plaintext_if_needed` factoring was the plan's recommended approach (Task 2 behavior note: "If Task 1 factored the re-encrypt logic into `_reencrypt_plaintext_if_needed` (strongly recommended)...").

## Known Stubs

None. All hooks are wired to real implementations. No placeholder data flows.

## Threat Flags

None. All 9 STRIDE threats in the plan's threat model (T-81-03-01 through T-81-03-09) are mitigated as described. No new security surface introduced beyond the plan's scope.

---
*Phase: 81-optional-fernet-encryption-at-rest*
*Completed: 2026-04-22*

## Self-Check: PASSED

- FOUND: src/python/seedsyncarr.py
- FOUND: src/python/tests/unittests/test_seedsyncarr.py
- FOUND: docs/CONFIGURATION.md
- FOUND: .planning/phases/81-optional-fernet-encryption-at-rest/81-03-SUMMARY.md
- FOUND commit: 324f171 (feat: seedsyncarr.py hooks)
- FOUND commit: c4bda69 (test: 3 new SEC-02 tests)
- FOUND commit: d04d4d6 (docs: CONFIGURATION.md [Encryption] section)
