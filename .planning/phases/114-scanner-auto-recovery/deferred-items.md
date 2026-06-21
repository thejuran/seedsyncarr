# Phase 114 — Deferred / Out-of-Scope Items

Logged during execution per the scope-boundary rule (do NOT fix issues unrelated to the current task's changes).

## Pre-existing environment-only test failures (bare macOS host)

Discovered while running the full `tests/unittests` suite during 114-02 execution. None of these
touch the files modified by 114-02 (`seedsyncarr.py`, `common/error.py`, `test_seedsyncarr.py`) and
all are unchanged from the plan's base commit. They are environmental: the canonical CI/dev runner is
`make run-tests-python`, which runs the suite **inside the project's Docker test container** where the
required Unix accounts/groups, Linux `fork` start-method, and ext4 filename semantics are present.

| Test file | Count | Cause (host-only) |
|-----------|-------|-------------------|
| `tests/unittests/test_ssh/test_sshcp.py` | 11 FAILED | `setUp` calls `grp.getgrnam("testgroup")` → `KeyError` — the `testgroup` group / `seedsyncarrtest` account exist only in the Docker test image. |
| `tests/unittests/test_controller/test_scan/test_scanner_process.py` | 3 FAILED + 3 ERROR | macOS default `spawn` start-method can't pickle `MagicMock` (`_pickle.PicklingError`) / teardown `NoneType.terminate` — tests assume Linux `fork`. |
| `tests/unittests/test_controller/test_extract/test_extract_process.py` | 6 FAILED | Same `spawn` vs `fork` multiprocessing-pickling environment gap. |
| `tests/unittests/test_system/test_scanner.py::test_scan_file_with_latin_chars` | 1 FAILED | macOS APFS rejects a Latin-1 byte sequence in a filename (`OSError [Errno 92] Illegal byte sequence`); Linux/Docker ext4 accepts it. |

**Action:** None taken (out of scope for 114-02). These pass under `make run-tests-python` (Docker). The
114-02 scoped suites — `test_seedsyncarr.py` (40 tests) and `test_common/test_error.py` (13 tests) — are
fully green on this host, and `ruff check src/python/` is clean.
