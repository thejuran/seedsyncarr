---
phase: 81-optional-fernet-encryption-at-rest
fixed_at: 2026-04-22T14:45:00Z
review_path: .planning/phases/81-optional-fernet-encryption-at-rest/81-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 81: Code Review Fix Report

**Fixed at:** 2026-04-22T14:45:00Z
**Source review:** .planning/phases/81-optional-fernet-encryption-at-rest/81-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Corrupted keyfile causes unhandled ValueError in encrypt_field and decrypt_field

**Files modified:** `src/python/common/encryption.py`
**Commit:** 6bf9b88
**Applied fix:** Added try/except ValueError handling to `encrypt_field` that wraps the error in `DecryptionError` with a message indicating keyfile corruption. Added `ValueError` to the existing except clause in `decrypt_field` alongside `InvalidToken`, so both corrupted-key and wrong-key cases are caught and wrapped in `DecryptionError`. The raw `ValueError` from the `Fernet()` constructor no longer escapes the module boundary.

### WR-02: from_str classmethod type annotation uses bare string instead of Type

**Files modified:** `src/python/common/config.py`
**Commit:** dae3b97
**Applied fix:** Changed `cls: "Config"` to `cls: Type["Config"]` on the `from_str` classmethod signature, matching the parent `Persist.from_str` which uses `Type[T_Serializable]`. The `Type` import was already present on line 7 of config.py, so no import changes were needed.

---

_Fixed: 2026-04-22T14:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
