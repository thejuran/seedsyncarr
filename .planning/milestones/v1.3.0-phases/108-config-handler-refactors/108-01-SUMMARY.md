---
phase: 108-config-handler-refactors
plan: "01"
subsystem: config
tags: [config, secrets, encryption, refactor, declarative, arch-02]
dependency_graph:
  requires: []
  provides: [Config.secret_fields discovery API, secret=True PropMetadata flag]
  affects: [src/python/common/config.py, src/python/seedsyncarr.py]
tech_stack:
  added: []
  patterns: [TDD RED/GREEN, per-class prop_addon_map filter, declarative secret discovery]
key_files:
  created: []
  modified:
    - src/python/common/config.py
    - src/python/seedsyncarr.py
    - src/python/tests/unittests/test_common/test_config.py
decisions:
  - D-01: secret=True added to ONLY 5 PROPs; ini_section derived structurally from subclass.__name__
  - D-02: _SECRET_FIELD_PATHS fully removed, no alias; Config.secret_fields() classmethod replaces it
  - Config.secret_fields() iterates all 9 mapped sections (not hardcoded 4) via _section_map list
  - InnerConfig._iter_secret_field_names() applies per-class filter using same pattern as as_dict:194
  - Encrypt loop repointed in Task 1 (required for F2 Fernet round-trip test to achieve GREEN)
requirements: [ARCH-02]
metrics:
  duration: "8m"
  completed: "2026-06-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 108 Plan 01: ARCH-02 Declarative Config Secret Discovery Summary

Config secret-field discovery is now fully declarative. Each of the five secret PROPs carries `secret=True`; the encrypt/decrypt code paths discover secret fields dynamically from property metadata via `Config.secret_fields()`, which replaced the hand-maintained `_SECRET_FIELD_PATHS` tuple that has been deleted entirely.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for secret_fields() discovery API | 1b736ca | test_config.py (+4 tests) |
| GREEN (Task 1) | PropMetadata secret flag + 5 PROP declarations + secret_fields() + loops repointed | 126ad92 | config.py |
| Task 2 | Delete _SECRET_FIELD_PATHS tuple + repoint seedsyncarr startup loop | 7f6c0ba | config.py, seedsyncarr.py, test_config.py |

## What Was Built

### InnerConfig.PropMetadata (config.py)
- Added `secret: bool = False` field to `__init__` signature
- Type-annotated per project conventions

### InnerConfig._create_property (config.py)
- Added `secret: bool = False` keyword argument, threaded into PropMetadata construction
- `PROP = InnerConfig._create_property` alias continues to work unchanged for all existing non-secret callers

### InnerConfig._iter_secret_field_names() (config.py)
- New classmethod yields field names for properties of THIS class where `prop_addon.secret is True`
- Applies the per-class filter (`my_property_to_name_map` + `__prop_addon_map` iteration) inherited from `as_dict` line 194 — prevents shared global `__prop_addon_map` cross-contamination (F3)
- Identity check `secret is True` per project rule (not truthy test)

### Config.secret_fields() classmethod (config.py)
- Iterates ALL nine mapped sections in declaration order: General, Lftp, Controller, Web, AutoQueue, Sonarr, Radarr, AutoDelete, Encryption
- Derives `ini_section` structurally from `subclass.__name__` (codex-verified: always equals TitleCase section name)
- Derives `attr` from the explicit `_section_map` list (e.g., "general", "lftp")
- Returns `list[tuple[str, str, str]]` of `(attr_lowercase, field_name, ini_section_titlecase)` — same 3-tuple shape as the removed tuple
- Encryption.enabled is never emitted because its PROP stays `secret=False` (T-81-02-07)
- A future `secret=True` field in ANY section (Controller, Web, AutoQueue, AutoDelete, Encryption) is auto-discovered with zero edits to this method (F1)

### Five secret=True PROP declarations (config.py)
- `Config.General.webhook_secret` — `secret=True`
- `Config.General.api_token` — `secret=True`
- `Config.Lftp.remote_password` — `secret=True`
- `Config.Sonarr.sonarr_api_key` — `secret=True`
- `Config.Radarr.radarr_api_key` — `secret=True`
- Exactly 5; `Encryption.enabled` stays at default `secret=False`

### Consumer site repointing (config.py, seedsyncarr.py)
- `from_str` site 1: `has_existing_ciphertext` any-generator
- `from_str` site 2: keyfile-gone record-errors loop
- `from_str` site 3: decrypt loop
- `to_str` site 4: encrypt loop
- `seedsyncarr.py` site 5: `_reencrypt_plaintext_if_needed` loop
- All five loop BODIES kept byte-identical; only the iterable was swapped

### _SECRET_FIELD_PATHS removed (config.py, seedsyncarr.py)
- Module-level tuple and its comment block deleted (D-02)
- `from common.config import _SECRET_FIELD_PATHS` import deleted from seedsyncarr.py
- No same-named alias or shim created

### New tests (test_config.py — TestSecretFieldDiscovery class)
- `test_discovery_iterates_all_sections_returns_exactly_five_real_triples` (F1): asserts all 9 sections iterated, exactly 5 triples returned with correct values
- `test_encryption_enabled_not_discovered` (T-81-02-07): Encryption.enabled absent from discovery output
- `test_secret_field_on_unmapped_subclass_not_discovered` (F3): throwaway DummyInnerConfig secret PROP does NOT appear in real discovery — cross-contamination guard works
- `test_secret_field_round_trips_through_fernet` (F2, criterion #2): injected temp `secret=True` PROP in Config.General is auto-discovered AND round-trips through real `to_str`/`from_str` Fernet path without modifying any other file

## Verification Results

| Check | Result |
|-------|--------|
| `grep -c "secret=True" src/python/common/config.py` | 5 |
| `! rg -n "_SECRET_FIELD_PATHS" src/python --glob "*.py"` | PASSED (zero matches) |
| `git diff --exit-code src/python/web/serialize/serialize_config.py` | CLEAN |
| `poetry run pytest tests/unittests/test_common/test_config.py -q` | 31 passed |
| `poetry run pytest tests/unittests/test_common/test_config.py tests/integration/test_web/test_handler/test_controller.py -q` | 36 passed |
| `make run-tests-python` (full suite) | 1339 passed, 62 skipped, 0 failed |

## Deviations from Plan

### Auto-addressed: Encrypt/decrypt loops repointed in Task 1 (not Task 2)

**Found during:** Task 1 GREEN step (F2 Fernet round-trip test)

**Issue:** The F2 test exercises the real `to_str` → `from_str` Fernet path. The `to_str` encrypt loop and `from_str` decrypt loops still referenced `_SECRET_FIELD_PATHS` at RED time. This meant the injected `secret=True` PROP was discovered by `secret_fields()` but NOT encrypted on serialization or decrypted on reload — making F2 impossible to pass without also repointing the loops.

**Fix:** Repointed all four `config.py` consumer sites (3 in `from_str`, 1 in `to_str`) to `Config.secret_fields()` during the GREEN step of Task 1. Task 2 then handled the seedsyncarr.py repointing and tuple deletion as planned. The outcome is identical — all six sites are now repointed, the tuple is deleted — just consolidated across Task 1 GREEN + Task 2 commits rather than purely in Task 2.

**Impact:** No behavioral change. Plan outcome fully achieved.

## Threat Model Coverage

| Threat | Status |
|--------|--------|
| T-108-01-01 (discovery drops a secret field) | Mitigated — F1 test asserts exactly 5 triples; Fernet suite stays green |
| T-108-01-02 (over-encryption of non-secret field) | Mitigated — exactly 5 secret=True PROP declarations confirmed by grep |
| T-108-01-03 (Encryption.enabled wrongly discoverable) | Mitigated — T-81-02-07 test asserts Encryption.enabled absent |
| T-108-01-05 (redaction path accidentally coupled) | Mitigated — serialize_config.py untouched, git diff clean |
| T-108-01-06 (cross-contamination via shared __prop_addon_map) | Mitigated — F3 negative test asserts unmapped subclass PROP never leaks |
| T-108-01-04 (iterator swap changes loop body) | Accepted-after-verify — loop bodies byte-identical, Fernet suite green |
| T-108-01-SC (package installs) | N/A — no new packages |

## Known Stubs

None — all discovery, encryption, and decryption paths are fully wired. No placeholders.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The refactor only changes the internal iteration mechanism for an existing encrypt/decrypt feature.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/python/common/config.py | FOUND |
| src/python/seedsyncarr.py | FOUND |
| src/python/tests/unittests/test_common/test_config.py | FOUND |
| .planning/milestones/v1.3.0-phases/108-config-handler-refactors/108-01-SUMMARY.md | FOUND |
| Commit 1b736ca (RED tests) | FOUND |
| Commit 126ad92 (GREEN implementation) | FOUND |
| Commit 7f6c0ba (Task 2 — delete tuple + repoint seedsyncarr) | FOUND |
