---
phase: 81-optional-fernet-encryption-at-rest
plan: 01
subsystem: security
tags: [python, cryptography, fernet, encryption, keyfile, sec-02]

requires:
  - phase: 80-small-cleanups-dependabot-arm64-enum
    provides: clean Python dependency baseline (pyproject.toml, poetry.lock)

provides:
  - common/encryption.py: Fernet primitive module (5 public symbols)
  - test_encryption.py: 8-test suite for the encryption primitive
  - cryptography>=44.0.0,<47 pinned in pyproject.toml (both dependency blocks) and regenerated poetry.lock

affects:
  - 81-02: config.py widening imports from common.encryption
  - 81-03: seedsyncarr.py startup hook imports from common.encryption

tech-stack:
  added:
    - cryptography>=44.0.0,<47 (PyCA Fernet: AES-128-CBC + HMAC-SHA256)
  patterns:
    - Atomic O_EXCL keyfile creation (stricter than persist.py write-then-chmod, justified for private key)
    - Tighten-on-read 0600 chmod matching persist.py:from_file:43
    - DecryptionError(AppError) wraps InvalidToken at module boundary (T-81-01-03, T-81-01-04)
    - is_ciphertext discriminator: cheapest-gate-first ordering (falsy -> len < 100 -> prefix -> b64) per T-81-01-05

key-files:
  created:
    - src/python/common/encryption.py
    - src/python/tests/unittests/test_common/test_encryption.py
  modified:
    - src/python/pyproject.toml
    - src/python/poetry.lock

key-decisions:
  - "Atomic O_EXCL create (0o600 mode arg) for keyfile first-time path — keyfile never exists at loose permissions even one syscall"
  - "Tighten-on-read for existing keyfile matches persist.py:40-45 exactly"
  - "DecryptionError wraps InvalidToken — raw PyCA exception never escapes module boundary (T-81-01-03/04)"
  - "poetry lock used (--no-update not supported on installed poetry version) — other pins preserved"
  - "cryptography range >=44.0.0,<47 with PEP 440 specifier in poetry (not caret) to allow 45.x/46.x patches"

patterns-established:
  - "Atomic exclusive-create file open: os.open(path, O_WRONLY|O_CREAT|O_EXCL, 0o600) for private keys"
  - "is_ciphertext gate ordering: falsy check, len check, prefix check, b64 decode — O(1) gates before O(n)"
  - "DecryptionError(AppError) with fixed error message string — no token/key material in message"

requirements-completed:
  - SEC-02

duration: 56min
completed: 2026-04-22
---

# Phase 81 Plan 01: Fernet Primitive Module Summary

**Fernet primitive wrappers in common/encryption.py: keyfile O_EXCL create/load-tighten at 0600, is_ciphertext discriminator, encrypt_field/decrypt_field with DecryptionError boundary, plus 8-test suite and cryptography>=44,<47 dependency**

## Performance

- **Duration:** 56 min
- **Started:** 2026-04-22T16:39:41Z
- **Completed:** 2026-04-22T17:35:21Z
- **Tasks:** 3
- **Files modified:** 4 (pyproject.toml, poetry.lock, encryption.py, test_encryption.py)

## Accomplishments

- `common/encryption.py` created with 5 public symbols: `load_or_create_key`, `is_ciphertext`, `encrypt_field`, `decrypt_field`, `DecryptionError`
- 8 unit tests in `TestEncryption` all green; covers SEC-02 #1a (#5a): keyfile 0600 creation, tighten-on-load, round-trip encrypt/decrypt, discriminator accept/reject, wrong-key and corrupt-token error containment
- `cryptography>=44.0.0,<47` added to both `[project.dependencies]` and `[tool.poetry.dependencies]`; `poetry.lock` regenerated and `poetry check` exits 0

## Public Surface of common/encryption.py

| Symbol | Signature | Purpose |
|--------|-----------|---------|
| `DecryptionError` | `class DecryptionError(AppError)` | Domain exception; wraps `InvalidToken` at module boundary |
| `load_or_create_key` | `(keyfile_path: str) -> bytes` | Atomically creates 44-byte Fernet key at 0600; tightens on subsequent loads |
| `is_ciphertext` | `(s: str) -> bool` | Fast discriminator: falsy/len/prefix/b64 gates in O(1)-first order |
| `encrypt_field` | `(key: bytes, plaintext: str) -> str` | Returns str-typed Fernet token |
| `decrypt_field` | `(key: bytes, token: str) -> str` | Decrypts token; raises `DecryptionError` on failure |

## Task Commits

1. **Task 1: Add cryptography dependency** — `c85ffc4` (chore)
2. **Task 2: Create common/encryption.py** — `e5747d7` (feat)
3. **Task 3: Create test_encryption.py** — `5b35421` (test)

## Files Created/Modified

- `src/python/common/encryption.py` — new Fernet primitive module (130 lines)
- `src/python/tests/unittests/test_common/test_encryption.py` — 8-test TestEncryption class (110 lines)
- `src/python/pyproject.toml` — cryptography>=44.0.0,<47 added to both dependency blocks
- `src/python/poetry.lock` — regenerated with cryptography + transitive deps (cffi, pycparser)

## Decisions Made

**Deliberate deviation: Atomic O_EXCL first-create vs. persist.py write-then-chmod**

`persist.py:to_file` uses the two-step write-then-chmod idiom. For the keyfile first-create path, `load_or_create_key` uses `os.open(keyfile_path, O_WRONLY | O_CREAT | O_EXCL, 0o600)` instead. Rationale: a private Fernet key must never exist at looser permissions even for a single syscall window (threat model T-81-01-01). The existing-keyfile read branch matches `persist.py:40-45` exactly (chmod on every load, swallow OSError for Windows best-effort per T-81-01-07). This deviation is documented as a block comment in `encryption.py` above `load_or_create_key`.

**poetry lock (not --no-update)**

`poetry lock --no-update` is not supported on the installed poetry version. Fallback `poetry lock` was used; other pins were preserved in the output lock file. `poetry check` exits 0 confirming consistency.

**cryptography range with PEP 440 (not caret) in poetry block**

The `[tool.poetry.dependencies]` entry uses `cryptography = ">=44.0.0,<47"` rather than `^44.0.0`. The caret form would forbid 45.x and 46.x patches; the range form is what RESEARCH §5 and §15 A6 explicitly require.

## Deviations from Plan

None - plan executed exactly as written. The `poetry lock` fallback (vs `--no-update`) is an execution detail matching the plan's explicit fallback instruction ("if the project does not support `--no-update`... fall back to `poetry lock`").

## Issues Encountered

- `poetry lock --no-update` not supported on installed poetry version → used `poetry lock` per plan's explicit fallback
- Local machine runs Python 3.9.6 system python; poetry transparently switched to python3.12 (3.12.12) per project pin `>=3.11,<3.13`
- Local pytest version (8.4.2) from Python 3.9 env emits `PytestConfigWarning: Unknown config option: timeout` — pre-existing, out-of-scope; CI runs in project venv where `pytest-timeout` is installed

## Version-Range Notes on poetry.lock Transitive Deps

`poetry lock` added/updated the following transitive deps for `cryptography`:
- `cffi` (C foreign function interface — cryptography's C extension depends on it)
- `pycparser` (C parser — transitive dep of cffi)

These are pinned in `poetry.lock` and installed automatically. No user action needed.

## User Setup Required

None — no external service configuration required. The `cryptography` package will be installed automatically via `poetry install` on the next Docker rebuild or CI run.

## Next Phase Readiness

- `common/encryption.py` exports the full 5-symbol surface; plans 02 and 03 can import directly via `from common.encryption import ...`
- All 8 encryption unit tests are green
- `cryptography>=44.0.0,<47` is in the lockfile; Docker rebuild picks it up automatically
- SEC-02 #1a (keyfile 0600 creation) and #5a (keyfile permission test) are closed at the primitive level; higher-level criteria (#1b, #2, #3a, #3b, #4, #5b) are addressed in plans 02 and 03

---
*Phase: 81-optional-fernet-encryption-at-rest*
*Completed: 2026-04-22*

## Self-Check: PASSED

- FOUND: src/python/common/encryption.py
- FOUND: src/python/tests/unittests/test_common/test_encryption.py
- FOUND: src/python/pyproject.toml
- FOUND: src/python/poetry.lock
- FOUND: .planning/phases/81-optional-fernet-encryption-at-rest/81-01-SUMMARY.md
- FOUND commit: c85ffc4 (chore: cryptography dependency)
- FOUND commit: e5747d7 (feat: common/encryption.py)
- FOUND commit: 5b35421 (test: test_encryption.py)
