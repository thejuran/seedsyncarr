---
phase: 39-critical-security-chain
plan: 02
subsystem: security
tags: [pickle, json, deserialization, cwe-502, rce, remote-scanner, systemfile, scan-pipeline]

# Dependency graph
requires:
  - phase: 39-critical-security-chain
    provides: phase context and security chain plan
provides:
  - SystemFile.to_dict() and from_dict() for JSON round-trip serialization
  - scan_fs.py outputs JSON list via json.dumps instead of pickle
  - remote_scanner.py deserializes via json.loads + SystemFile.from_dict instead of pickle.loads
  - All remote scanner tests updated to use JSON-encoded mock data
affects:
  - 39-critical-security-chain (remaining plans that reference scan pipeline)
  - future plans modifying remote scanner or scan_fs

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "to_dict/from_dict pattern on domain objects for safe JSON serialization"
    - "json.dumps over SSH stdout for structured data transfer (replaces binary pickle)"

key-files:
  created: []
  modified:
    - src/python/system/file.py
    - src/python/scan_fs.py
    - src/python/controller/scan/remote_scanner.py
    - src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py

key-decisions:
  - "Replace pickle with JSON across the full remote scan pipeline to eliminate CWE-502 RCE vector"
  - "Use to_dict/from_dict methods on SystemFile rather than a separate serializer module"
  - "Error message updated from 'Invalid pickled data' to 'Invalid scan data' (format-agnostic)"

patterns-established:
  - "to_dict/from_dict: domain objects self-serialize for JSON transport"

requirements-completed: [SEC-07]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 39 Plan 02: JSON Migration (Pickle RCE Elimination) Summary

**Replaced pickle serialization with JSON across the full remote scan pipeline (scan_fs.py, remote_scanner.py, SystemFile) to eliminate the CWE-502 arbitrary code execution vector.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T00:53:21Z
- **Completed:** 2026-02-24T00:55:06Z
- **Tasks:** 2 of 2
- **Files modified:** 4

## Accomplishments
- Added `to_dict()` and `from_dict()` methods to `SystemFile` for safe JSON serialization with full round-trip fidelity (name, size, is_dir, timestamps, children)
- Migrated `scan_fs.py` from `pickle.dumps` + `sys.stdout.buffer.write` to `json.dumps` + `sys.stdout.write`
- Migrated `remote_scanner.py` from `pickle.loads` to `json.loads` + `SystemFile.from_dict`, with appropriate error handling for `JSONDecodeError`, `KeyError`, `TypeError`, `ValueError`
- Updated all 14 remote scanner unit tests to return `json.dumps([]).encode()` instead of `pickle.dumps([])`; all 14 pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add JSON serialization to SystemFile and migrate scan_fs output** - `108018f` (feat)
2. **Task 2: Migrate remote_scanner.py to JSON and update all tests** - `abef04a` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `src/python/system/file.py` - Added `to_dict()` and `from_dict()` methods to SystemFile
- `src/python/scan_fs.py` - Replaced `import pickle` / `pickle.dumps` with `import json` / `json.dumps`
- `src/python/controller/scan/remote_scanner.py` - Replaced `import pickle` / `pickle.loads` with `import json` / `json.loads` + `SystemFile.from_dict`
- `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` - Replaced `import pickle` / `pickle.dumps([])` with `import json` / `json.dumps([]).encode()`

## Decisions Made
- Used `to_dict`/`from_dict` as instance/class methods on `SystemFile` directly — keeps serialization co-located with the model, no separate serializer module needed
- Error message changed from `"Invalid pickled data"` to `"Invalid scan data"` to be format-agnostic and future-proof
- `out_str = out.decode('utf-8') if isinstance(out, bytes) else out` handles both bytes and str SSH output defensively

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CWE-502 pickle RCE vector fully eliminated from the remote scan pipeline
- SystemFile now has a clean JSON serialization interface for any future transport needs
- All 14 remote scanner tests pass with JSON-based mock data

---
*Phase: 39-critical-security-chain*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: src/python/system/file.py
- FOUND: src/python/scan_fs.py
- FOUND: src/python/controller/scan/remote_scanner.py
- FOUND: src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py
- FOUND: .planning/phases/39-critical-security-chain/39-02-SUMMARY.md
- FOUND commit: 108018f (feat: JSON serialization in SystemFile and scan_fs)
- FOUND commit: abef04a (feat: JSON migration in remote_scanner and tests)
