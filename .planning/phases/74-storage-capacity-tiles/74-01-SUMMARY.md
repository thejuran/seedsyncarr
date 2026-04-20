---
phase: 74-storage-capacity-tiles
plan: "01"
subsystem: backend
tags: [python, status, sse, serialization, storage]

# Dependency graph
requires: []
provides:
  - "StorageStatus inner class on Status model with four nullable byte-count properties"
  - "SerializeStatusJson.status() emits top-level 'storage' JSON block with all four fields as int-or-null"
  - "9 new unit tests covering defaults, round-trips, listener firing, copy, and reassign guard"
affects: [74-02, 74-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StorageStatus follows ServerStatus/ControllerStatus template: StatusComponent subclass, _create_property per field, None-init in __init__"
    - "Serializer storage block uses plain int passthrough (no str() wrap) — byte counts are numeric unlike timestamps"

key-files:
  created: []
  modified:
    - src/python/common/status.py
    - src/python/web/serialize/serialize_status.py
    - src/python/tests/unittests/test_common/test_status.py
    - src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py

key-decisions:
  - "StorageStatus slots in as a third component sibling to ServerStatus/ControllerStatus with zero new infrastructure"
  - "Four storage fields (local_total, local_used, remote_total, remote_used) all default to None; Plan 02 populates real values"
  - "Byte-count values pass through as int-or-null — no str() wrapping unlike datetime timestamps"

patterns-established:
  - "StorageStatus component template: StatusComponent subclass with _create_property + None-init"
  - "TDD RED/GREEN for each backend model + serializer task: failing test commit then implementation commit"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-04-20
---

# Phase 74 Plan 01: StorageStatus model + serializer storage block

**StorageStatus component on Status model with four nullable byte-count fields, serialized as `"storage"` block on existing SSE status stream — ready for Plan 02 to populate real values**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-20T01:07:44Z
- **Completed:** 2026-04-20T01:09:36Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `Status.StorageStatus` inner class with `local_total`, `local_used`, `remote_total`, `remote_used` — all nullable, all defaulting to `None`, wired via `__create_component` so the existing listener chain and `copy()` pick them up automatically
- Extended `SerializeStatusJson.status()` to emit a top-level `"storage"` dict with all four fields as `int | null` — no str() wrapping (byte counts are numeric, unlike timestamps)
- 9 new unit tests: 5 in `test_status.py` (defaults, round-trips, listeners, reassign guard, copy) + 4 in `test_serialize_status.py` (null-default + int round-trip per field); all 27 tests in both files pass

## Task Commits

Each task was committed atomically with TDD RED then GREEN:

1. **Task 1 RED: StorageStatus failing tests** - `562d71c` (test)
2. **Task 1 GREEN: StorageStatus implementation** - `a348a18` (feat)
3. **Task 2 RED: storage serialization failing tests** - `7a46086` (test)
4. **Task 2 GREEN: storage block in serializer** - `bf32674` (feat)

## Files Created/Modified

- `src/python/common/status.py` — Added `StorageStatus` inner class (lines 127-138), `storage = BaseStatus._create_property("storage")` registration, `self.storage = self.__create_component(Status.StorageStatus)` init
- `src/python/web/serialize/serialize_status.py` — Added 5 `__KEY_STORAGE*` constants and storage dict block in `status()` method
- `src/python/tests/unittests/test_common/test_status.py` — 5 new test methods: `test_storage_default_values`, `test_storage_property_values`, `test_storage_listeners`, `test_storage_cannot_replace_component`, `test_storage_copy_preserves_values`
- `src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py` — 4 new test methods: `test_storage_local_total`, `test_storage_local_used`, `test_storage_remote_total`, `test_storage_remote_used`

## Decisions Made

- Byte-count values are passed through as raw `int | None` — no `str()` wrapping — because they are numeric quantities, unlike `datetime.timestamp()` strings used for scan times. This matches the plan spec (D-08).
- No changes to `CompListener`, `copy()`, or any other Status machinery — the new component is picked up automatically by `dir(cls)` iteration in `copy()` and `__create_component`'s listener wiring.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `pytz` module was missing from the local Python 3.9 environment (pre-existing gap). Installed via `pip3 install pytz` so `test_serialize_status.py` could be collected. No code change required.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Backend SSE status stream already emits `"storage": {"local_total": null, "local_used": null, "remote_total": null, "remote_used": null}` on every event
- Plan 02 (scanner wiring) can now assign real values to `status.storage.*` and they will flow through to the frontend immediately
- Plan 03 (frontend) can begin consuming the `storage` block from the SSE JSON

---
*Phase: 74-storage-capacity-tiles*
*Completed: 2026-04-20*
