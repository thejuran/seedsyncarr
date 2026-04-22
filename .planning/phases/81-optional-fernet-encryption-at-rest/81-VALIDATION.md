---
phase: 81
slug: optional-fernet-encryption-at-rest
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + unittest.TestCase (project uses unittest classes via pytest runner) |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (lines 71-78) |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests/test_common/test_encryption.py tests/unittests/test_common/test_config.py -x` |
| **Full suite command** | `make run-tests-python` (root Makefile) — runs the full Python suite in Docker |
| **Estimated runtime** | ~5 seconds (quick) / ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd src/python && poetry run pytest tests/unittests/test_common/test_encryption.py tests/unittests/test_common/test_config.py -x`
- **After every plan wave:** Run `cd src/python && poetry run pytest tests/unittests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green (`make run-tests-python`)
- **Max feedback latency:** 5 seconds (quick) / 60 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 81-01-01 | 01 | 1 | SEC-02 #1a / #5a | V6 / V8 | Keyfile generated with 0600 perms; only owner can read | unit | `poetry run pytest tests/unittests/test_common/test_encryption.py::TestEncryption::test_keyfile_is_0600 -x` | ❌ W0 | ⬜ pending |
| 81-01-02 | 01 | 1 | SEC-02 (discriminator) | V5 | `is_ciphertext` correctly distinguishes Fernet tokens from plaintext | unit | `poetry run pytest tests/unittests/test_common/test_encryption.py::TestEncryption::test_is_ciphertext -x` | ❌ W0 | ⬜ pending |
| 81-02-01 | 02 | 2 | SEC-02 #1b | V6 / V8 | 5 secrets encrypted in place on first enable | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_enable_new_install_encrypts_on_write -x` | ❌ W0 | ⬜ pending |
| 81-02-02 | 02 | 2 | SEC-02 #2 | V6 | Read path transparently decrypts; callers see plaintext | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_from_file_enabled_decrypts -x` | ❌ W0 | ⬜ pending |
| 81-02-03 | 02 | 2 | SEC-02 #3b | V14 | Plaintext install with flag disabled works unchanged (backward compat) | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_encryption_disabled_by_default -x` | ❌ W0 | ⬜ pending |
| 81-02-04 | 02 | 2 | SEC-02 #4 | V14 | Disable → restore plaintext (round-trip preserves 5 values) | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_disable_restores_plaintext -x` | ❌ W0 | ⬜ pending |
| 81-03-01 | 03 | 3 | SEC-02 #3a | V8 | Plaintext detected on startup → re-encrypted in place | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_enable_existing_plaintext_reencrypts -x` | ❌ W0 | ⬜ pending |
| 81-03-02 | 03 | 3 | SEC-02 #5b | V5 | Decrypt failure surfaces a clear startup warning | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py::TestSeedsyncarr::test_decrypt_failure_emits_warning -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs above are indicative; planner will assign final IDs in PLAN.md files.*

---

## Wave 0 Requirements

- [ ] `src/python/tests/unittests/test_common/test_encryption.py` — stubs for SEC-02 #1a / #5a and `is_ciphertext` discriminator correctness.
- [ ] 5 new test methods in `src/python/tests/unittests/test_common/test_config.py` — stubs for SEC-02 #1b, #2, #3a, #3b, #4.
- [ ] 1 new test method in `src/python/tests/unittests/test_seedsyncarr.py` — stub for SEC-02 #5b (startup warning).
- [ ] No framework install needed; `pytest` + `cryptography` are already dev deps.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-platform keyfile permissions (Windows) | SEC-02 #1 | `os.chmod(0o600)` is a no-op on Windows; POSIX semantics not guaranteed | Automated tests skip on `sys.platform == 'win32'`. If Windows support becomes a target, run `icacls secrets.key` to confirm ACL restricts to owner; out of scope for this phase per research A5. |
| Keyfile backup documentation | SEC-02 (operator guidance) | Docs text is not automatable | Confirm `docs/configuration.md` (or equivalent) gains a clear "your `secrets.key` is critical; back it up" note before phase sign-off. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (full) / < 5s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
