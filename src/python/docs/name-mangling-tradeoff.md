# Name-Mangling in Python Tests: Accepted Trade-Off

Documented: 2026-04-25
Phase: 89 (PYARCH-05)

## What Is Name-Mangling?

Python name-mangling transforms attributes with double-underscore prefix (e.g., `self.__field`) into `_ClassName__field` at the class level. Tests that access `obj._ClassName__field` are coupling to the private API surface.

## Current Usage

154 name-mangling references across 4 test files:

| Pattern | Count | Test File(s) | What It Accesses |
|---------|-------|-------------|------------------|
| `_Controller__` | 144 | test_controller.py, test_controller_unit.py, test_auto_delete.py | Controller internal state: `__model`, `__model_lock`, `__started`, `__pending_auto_deletes`, `__command_queue`, `__lftp_manager`, `__context`, `__persist`, `__active_downloading_file_names`, `__schedule_auto_delete`, `__execute_auto_delete` |
| `_ControllerHandler__` | 10 | test_controller_handler.py | ControllerHandler private methods: `__handle_action_queue`, `__handle_action_extract`, `__handle_action_delete_local`, `__handle_action_delete_remote`, `__handle_bulk_command` |

## Why This Is Accepted

1. **No public API alternative:** The Controller class exposes limited public methods. Testing internal state transitions (e.g., verifying that a timer was scheduled for auto-delete, or that the model was updated correctly) requires access to private attributes.

2. **Test-only coupling:** Name-mangling access is confined to test files. Production code does not use cross-class name-mangling.

3. **Refactoring cost vs. benefit:** Wrapping every private attribute in a test-visible property would add boilerplate to production code purely for testability, violating encapsulation for the wrong reason.

4. **Established pattern:** This pattern has been stable across 9 milestones of development. The private API surface has not changed in ways that broke tests.

## Risk

If Controller internals are renamed, these tests will fail with `AttributeError`. This is considered an acceptable early-warning signal rather than a defect -- it forces test updates when internal structure changes.

## Decision

**Status:** Accepted trade-off. No action required.
**Decided:** Phase 89 (PYARCH-05)
**Revisit trigger:** If Controller undergoes major internal refactoring, consider adding test-visible properties.
