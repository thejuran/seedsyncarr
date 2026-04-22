---
phase: 81-optional-fernet-encryption-at-rest
plan: 02
subsystem: security
tags: [python, cryptography, fernet, encryption, config, sec-02]

requires:
  - phase: 81-01
    provides: common/encryption.py Fernet primitive module (load_or_create_key, is_ciphertext, encrypt_field, decrypt_field, DecryptionError)

provides:
  - config.py: Config.Encryption inner class + [Encryption] section in from_dict/as_dict + encrypt/decrypt hooks in from_str/to_str + Config.set_keyfile_path classmethod + _SECRET_FIELD_PATHS module tuple + _decrypt_errors collection
  - test_config.py: 6 new test methods covering SEC-02 criteria #1b/#2/#3b/#4 + golden-string update for [Encryption] section

affects:
  - 81-03: seedsyncarr.py startup hook reads config._decrypt_errors and calls Config.set_keyfile_path before from_file

tech-stack:
  added: []
  patterns:
    - Serialization-seam encrypt/decrypt (hooks in from_str/to_str — callers see plaintext)
    - Backward-compatible optional INI section (enabled=False default when [Encryption] absent)
    - Pitfall 8.4 guard (refuse new key when keyfile missing + existing ciphertext)
    - Class-level keyfile path injection via set_keyfile_path classmethod (test isolation)
    - TestConfig setUp/tearDown keyfile isolation (T-81-02-09)

key-files:
  modified:
    - src/python/common/config.py
    - src/python/tests/unittests/test_common/test_config.py

key-decisions:
  - "encryption.enabled is None on fresh Config() — falsy, so to_str skips encrypt; tests that call to_file must explicitly set enabled=False to match golden string"
  - "Pitfall 8.4 guard: if keyfile absent AND any 5 fields are ciphertext-shaped, skip load_or_create_key and record all ciphertext fields as _decrypt_errors"
  - "to_str raises ConfigError (not silent no-op) when encryption.enabled=True but _keyfile_path is None (T-81-02-05)"
  - "TestConfig setUp/tearDown added to all TestConfig tests — keyfile temp dir created/destroyed per test, Config._keyfile_path reset to None in tearDown"

requirements-completed:
  - SEC-02

duration: 20min
completed: 2026-04-22
---

# Phase 81 Plan 02: Config.Encryption + Serialization-Seam Encrypt/Decrypt Summary

**Config.Encryption inner class + _SECRET_FIELD_PATHS + set_keyfile_path + from_str/to_str Fernet hooks with Pitfall 8.4 guard + 6 SEC-02 test methods (criteria #1b, #2, #3b, #4) in test_config.py**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-22T17:48:40Z
- **Completed:** 2026-04-22T18:08:40Z
- **Tasks:** 3
- **Files modified:** 2 (config.py, test_config.py)

## Accomplishments

- `Config.Encryption(IC)` inner class with single `enabled` field; mirrors AutoDelete pattern
- `_SECRET_FIELD_PATHS` module tuple with exactly 5 entries (General.webhook_secret, General.api_token, Lftp.remote_password, Sonarr.sonarr_api_key, Radarr.radarr_api_key)
- `Config.set_keyfile_path(cls, path)` classmethod for test isolation and startup injection
- `Config._decrypt_errors` instance list (empty on clean loads; populated on DecryptionError or Pitfall 8.4)
- `Config._keyfile_path = None` class-level attr
- `from_str` decrypt hook: post-config_dict, pre-from_dict; Pitfall 8.4 guard; plaintext fallback
- `to_str` encrypt hook: post-as_dict, pre-serialization loop; raises ConfigError when keyfile missing
- Backward-compat `[Encryption]` branch in `from_dict` (enabled=False default when section absent)
- `as_dict` appends `"Encryption"` key
- 6 new test methods all green; golden string updated with `[Encryption]\nenabled = False`
- All 21 tests in test_config.py pass

## Exact Line Numbers in config.py (post-plan state)

| Symbol | Line |
|--------|------|
| `_SECRET_FIELD_PATHS` tuple | 19–27 |
| `Config.Encryption` inner class | 350–356 |
| `Config._keyfile_path` class attr | 360 |
| `Config.set_keyfile_path` classmethod | 378–383 |
| `self._decrypt_errors` in `__init__` | 375 |
| `from_str` decrypt hook start | 418 |
| `to_str` encrypt hook start | 473 |

## Golden-String Addition for test_to_file

Two lines appended to the golden string (after `[AutoDelete]` block):

```
[Encryption]
enabled = False
```

`config.encryption.enabled = False` was also added to the `test_to_file` config builder to match (since `Config()` initializes `enabled=None`, which would serialize as `None` not `False`).

## Other Tests Requiring Golden-String Update

Only `test_to_file` required a golden-string update. No other test in test_config.py performs a full-INI string comparison.

## Task Commits

1. **Task 1: Config.Encryption inner class + _SECRET_FIELD_PATHS + set_keyfile_path + _decrypt_errors** — `6f489d2`
2. **Task 2: Widen from_str/to_str with encrypt/decrypt hooks** — `25ba8b4`
3. **Task 3: 6 SEC-02 test methods + golden-string update** — `ee4c733`

## SEC-02 Criteria Coverage

| Criterion | Test | Status |
|-----------|------|--------|
| #1b — 5 secrets encrypted in to_str output | `test_enable_new_install_encrypts_on_write` | Covered |
| #2 — from_str transparently decrypts | `test_from_file_enabled_decrypts` | Covered |
| #3b — backward compat (no [Encryption] section) | `test_encryption_disabled_by_default` | Covered |
| #4 — enable→disable round-trip | `test_disable_restores_plaintext` | Covered |
| plaintext-fallback on read | `test_from_str_enabled_with_plaintext_falls_back` | Covered |
| ConfigError when keyfile path None | `test_to_str_raises_when_enabled_without_keyfile_path` | Covered |
| #3a (startup re-encrypt) | deferred to plan 03 | Deferred |
| #5b (decrypt warning) | deferred to plan 03 | Deferred |

## _keyfile_path Reset in tearDown

`Config.set_keyfile_path(None)` is called in `TestConfig.tearDown`. Confirmed: every TestConfig test runs after setUp (which sets keyfile) and tearDown (which resets to None). No cross-test class-level pollution.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All 5 secret field paths are wired to real Fernet encrypt/decrypt. No placeholder data flows.

## Threat Flags

None. All 5 STRIDE threats in the plan's threat model (T-81-02-01 through T-81-02-05) are mitigated as described. No new security surface introduced beyond the plan's scope.

---
*Phase: 81-optional-fernet-encryption-at-rest*
*Completed: 2026-04-22*

## Self-Check: PASSED

- FOUND: src/python/common/config.py
- FOUND: src/python/tests/unittests/test_common/test_config.py
- FOUND: .planning/phases/81-optional-fernet-encryption-at-rest/81-02-SUMMARY.md
- FOUND commit: 6f489d2 (Task 1 — Config.Encryption + _SECRET_FIELD_PATHS)
- FOUND commit: 25ba8b4 (Task 2 — from_str/to_str encrypt/decrypt hooks)
- FOUND commit: ee4c733 (Task 3 — 6 SEC-02 test methods + golden-string update)
