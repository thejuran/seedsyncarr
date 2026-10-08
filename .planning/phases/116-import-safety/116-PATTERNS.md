# Phase 116: Import Safety - Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 7 (3 source modified, 4 test modified; optional new test module)
**Analogs found:** 7 / 7 (every file is modified in place; its analog is itself plus a sibling block in the same file)

All paths below are relative to `src/python/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `controller/controller.py` (Window 1 lookup build, terminal-skip branch, docstrings, new `_AUTO_DELETE_TERMINAL_SKIPS` constant) | service (controller orchestrator) | event-driven (queue drain) + transform | self: L554-574 (Window 1), L819-830 (`bfs_limit` branch), L25-38 (module constants) | exact |
| `controller/webhook_manager.py` (`process()` new param shape + ambiguity rejection) | service (matcher) | request-response over a queue (transform) | self: L44-96 (`process`), L38-42 (sanitized logging) | exact |
| `controller/auto_delete_manager.py` (BFS carries rel path, `duplicate_basename` guard) | service (collaborator) | transform (tree traversal) | self: L105-180 (BFS + partial_coverage capped log) | exact |
| `tests/unittests/test_controller/test_webhook_manager.py` (migrate 14 fixtures + new ambiguity/sanitize tests) | test | unit | self: L10-165 | exact |
| `tests/unittests/test_controller/test_controller_unit.py` (migrate 3 lookup-shape tests L1095-1146) | test | unit (call_args inspection) | self: L1095-1146 | exact |
| `tests/unittests/test_controller/test_auto_delete.py` (new e2e ambiguity class + guard tests + D-07 legacy) | test | e2e controller / unit | `TestAutoDeleteIntegration` L436-474, `TestAutoDeleteCoverageGuard` L265-376, `TestAutoDeletePersistRehydration` L379-406 | exact |
| `tests/unittests/test_controller/test_auto_delete_rearm.py` (terminal `duplicate_basename` test) | test | unit | `test_bfs_limit_is_terminal_and_does_not_rearm` L160-175, `_assert_terminal` L242-246 | exact |
| (optional) `tests/unittests/test_controller/test_import_ambiguity.py` | test | e2e controller | `test_auto_delete.py` `BaseAutoDeleteTestCase` L11-38 | role-match |

`tests/unittests/test_controller/test_controller.py` does NOT reference `name_to_root` or `process.call_args[0][0]` (grep verified) -- no migration needed there.

## Pattern Assignments

### `controller/controller.py` (controller service, event-driven + transform)

**Imports already present** (L1-4, L20-21) -- no new imports needed:
```python
import collections
from typing import Dict, List, Optional, Tuple
...
from common import Context, AppError, MultiprocessingLogger, sanitize_log_value
from model import ModelError, ModelFile, Model, ModelDiff, IModelListener
```

**Module-constant pattern** (L25-38) -- add `_AUTO_DELETE_TERMINAL_SKIPS` next to these, same comment style:
```python
_AUTO_DELETE_MAX_REARMS = 24

# Human-readable deferral reasons for AutoDeleteManager's retriable skip codes
# (its own log line already carries the child name / missing basenames).
_AUTO_DELETE_DEFER_REASONS = {
    "unsafe_child": "a child is still in an active state",
    "partial_coverage": "not every on-disk video child has been imported yet",
}
```

**Window 1 lookup build -- code to replace** (`__check_webhook_imports`, file L554-574):
```python
        # Window 1: Build name-to-root lookup under lock
        # lowercased name -> root model file name
        # Includes both root names and all child file names
        name_to_root = {}
        with self.__model_lock:
            for root_name in self.__model.get_file_names():
                name_to_root[root_name.lower()] = root_name
                try:
                    root_file = self.__model.get_file(root_name)
                    if root_file.is_dir:
                        # BFS over children to collect all child names
                        frontier = collections.deque(root_file.get_children())
                        while frontier:
                            child = frontier.popleft()
                            name_to_root[child.name.lower()] = root_name
                            frontier.extend(child.get_children())
                except ModelError:
                    self.logger.debug("ModelError looking up '{}' for webhook mapping".format(sanitize_log_value(root_name)))

        # Process outside lock -- webhook_manager only touches its own thread-safe Queue
        newly_imported = self.__webhook_manager.process(name_to_root)
```
Change: frontier holds `(child, parent_path)` tuples; store `name_to_paths.setdefault(name.lower(), {})[case_preserved_path] = root_name`; join with literal `"/"`; keep the `except ModelError: self.logger.debug(...)` and keep `process()` OUTSIDE the lock (RESEARCH Pattern 1 snippet). Also update the method docstring (L537-553: "Window 1 (read): build name_to_root dict").

**Window 2 -- DO NOT EDIT** (L576-640). It consumes `List[(root_name, matched_name)]`; the evidence gate (L591-616), `imported_file_names.add` (L618), WR-01 `add_imported_child` guard (L632-633), badge `_set_import_status` (L642), and `accepted_roots` + `__schedule_auto_delete` (L648-650) are all reached only for returned tuples, so rejecting inside `process()` covers all of D-03.

**Terminal-skip branch -- code to generalize** (`__execute_auto_delete`, file L819-830):
```python
            elif file.is_dir:
                skip, reason, _on_disk_videos = self.__auto_delete_mgr.run_bfs_and_coverage(
                    file, file_name, deletable_states
                )
                if skip:
                    if reason == "bfs_limit":
                        # Terminal skip: Timer does not re-arm. Clear the
                        # per-child entry so imported_children isn't stranded
                        # on a permanently-oversized pack. All other skip paths
                        # are retriable and leave the entry intact.
                        self.__persist.imported_children.pop(file_name, None)
                        self.__clear_auto_delete_rearms(file_name)
                        return
                    defer_reason = _AUTO_DELETE_DEFER_REASONS.get(reason, reason)
```
Change `reason == "bfs_limit"` to `reason in _AUTO_DELETE_TERMINAL_SKIPS`; update the inline comment and the `__execute_auto_delete` docstring "Terminal skips (... BFS node limit)" list (L732-735).

---

### `controller/webhook_manager.py` (matcher service, queue drain + transform)

**Imports** (L1-4) -- already sufficient (`Dict, List, Tuple`, `sanitize_log_value`):
```python
from queue import Queue, Empty
from typing import Dict, List, Tuple

from common import Context, sanitize_log_value
```

**Core matching loop -- code to change** (L65-96):
```python
        newly_imported = []

        # Drain queue
        while not self.__import_queue.empty():
            try:
                source, file_name, provenance = self.__import_queue.get_nowait()
            except Empty:
                # Queue empty (race condition between empty() and get_nowait())
                break

            # Case-insensitive matching against root and child names
            root_name = name_to_root.get(file_name.lower())
            # Sanitize webhook-supplied file_name for log output (CWE-117). ...
            safe_file_name = sanitize_log_value(file_name)
            if root_name is not None:
                newly_imported.append((root_name, file_name))
                self.logger.info(
                    "{} import detected: '{}' (matched SeedSyncarr file '{}'; {})".format(
                        source, safe_file_name, root_name, sanitize_log_value(provenance)
                    )
                )
            else:
                self.logger.warning(
                    "{} webhook file '{}' not found in SeedSyncarr model "
                    "(checked {} names including children)".format(
                        source, safe_file_name, len(name_to_root)
                    )
                )

        return newly_imported
```
Changes:
- Param `name_to_paths: Dict[str, Dict[str, str]]`; return type unchanged.
- `candidates = name_to_paths.get(file_name.lower())` -> three branches: none (unchanged "not found" warning, `len(name_to_paths)` keeps exact test string L81-87), exactly 1 (`root_name = next(iter(candidates.values()))`, append + unchanged INFO line, but wrap `root_name` in `sanitize_log_value` -- Pitfall 5), >=2 (one WARNING with sanitized name, sorted roots, sorted capped paths, sanitized provenance, and the phrase "no import credit or automatic cleanup authorized"; append nothing).
- Update docstring L45-64 (Args + "Returns ... only unambiguous matches").

**Sanitized logging pattern** (L38-42) -- apply to every interpolated value in the new warning:
```python
        safe_file_name = sanitize_log_value(file_name)
        self.logger.info("{} webhook import enqueued: '{}' ({})".format(
            source, safe_file_name, sanitize_log_value(provenance)))
```

**List-cap pattern to reuse** (from `auto_delete_manager.py` L163-167):
```python
                missing_list = sorted(missing)
                shown = missing_list[:5]
                suffix = ""
                if len(missing_list) > 5:
                    suffix = " (+{} more)".format(len(missing_list) - 5)
```

---

### `controller/auto_delete_manager.py` (collaborator service, tree-traversal transform)

**Imports** (L1-6) -- add `Dict, List` to the typing import:
```python
import collections
import os
from typing import Optional, Set, Tuple

from common import sanitize_log_value
from model import ModelFile
```

**Constants** (L9-26): reuse `_VIDEO_EXTENSIONS` (L14-17) for the guard scope (D-05a); update the `_AUTO_DELETE_BFS_NODE_LIMIT` comment (L19-25) that enumerates terminal vs retriable skips to add `duplicate_basename` as terminal.

**BFS -- code to change** (L105-140):
```python
        on_disk_videos: Set[str] = set()
        unsafe_child = None
        frontier = collections.deque(file.get_children())
        nodes_visited = 0

        while frontier:
            nodes_visited += 1
            if nodes_visited > _AUTO_DELETE_BFS_NODE_LIMIT:
                ...
                return True, "bfs_limit", None

            child = frontier.popleft()
            if child.state not in deletable_states:
                unsafe_child = child
                break
            ...
            grandchildren = child.get_children()
            if not child.is_dir:
                ext = os.path.splitext(child.name)[1].lower()
                if ext in _VIDEO_EXTENSIONS:
                    on_disk_videos.add(child.name.lower())
            frontier.extend(grandchildren)
```
Change: frontier holds `(child, rel_path)` starting `(c, c.name)`; video leaves also `video_paths.setdefault(lower, []).append(rel_path)`; extend with `(g, rel_path + "/" + g.name)`. Node accounting unchanged. Do not use `ModelFile.full_path` (MagicMock children in tests have no parent chain).

**Skip-return + log pattern to copy for the guard** (L142-150 unsafe_child; L113-122 bfs_limit WARNING):
```python
        if unsafe_child is not None:
            self.logger.info(
                "Auto-delete skipped for '{}': child '{}' is in state {}".format(
                    sanitize_log_value(file_name),
                    sanitize_log_value(unsafe_child.name),
                    str(unsafe_child.state),
                )
            )
            return True, "unsafe_child", None
```
Insert the new `duplicate_basename` block AFTER this (L150) and BEFORE `imported_child_bset = self._persist.imported_children.get(file_name)` (L158) so neither legacy coverage nor the D-14 grandfather path (`imported_child_bset is None`) can bypass it. Log at WARNING ("Auto-delete skipped for '{}': ..."), sanitize root + every path, cap the list with the L163-167 pattern. Return `True, "duplicate_basename", None`. Update the Returns section of the docstring (L85-93).

**Collaborator storage rule** (L51-53): single-underscore attributes only; logger is the caller's logger (L57-64), so test assertions read `self.controller.logger.warning`.

---

### `tests/unittests/test_controller/test_webhook_manager.py` (unit test)

**Fixture to migrate** (L10-19):
```python
    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.manager = WebhookManager(context=self.mock_context)
        # name_to_root: lowercased name -> root model file name
        self.name_to_root = {
            "file.a": "File.A",
            "file.b": "File.B",
            "file.c": "File.C",
        }
```
New shape: `{"file.a": {"File.A": "File.A"}, ...}`. Inline fixtures at L91-94, L101-104, L113-116 (`"episode.s01e01.mkv": "ShowDir"` -> `{"ShowDir/Episode.S01E01.mkv": "ShowDir"}`) and L157 (`{raw_name.lower(): "File.A"}`) also migrate. Add a small builder helper as suggested in RESEARCH Pitfall 3. Keep every assertion string verbatim (e.g. L83-86 "checked 3 names including children", L106-108 info line).

**Sanitization test pattern to copy for the ambiguity warning** (L127-140):
```python
        crlf_name = "File.A\r\ninjected"
        self.manager.enqueue_import("Sonarr", crlf_name)
        call_args = self.manager.logger.info.call_args_list
        self.assertTrue(call_args, "Expected at least one logger.info call")
        logged_msg = call_args[-1][0][0]
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in log output")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in log output")
        self.assertIn("\\r", logged_msg, "Escaped \\r token must appear in log output")
        self.assertIn("\\n", logged_msg, "Escaped \\n token must appear in log output")
```
Use `self.manager.logger.warning.call_args_list` and put CR/LF into the name, a root, and a path.

---

### `tests/unittests/test_controller/test_controller_unit.py` (unit test, call_args inspection)

**Analog to migrate** (L1095-1146; the three `test_webhook_name_lookup_*` tests):
```python
        self.controller.process()
        call_args = self.mock_webhook_manager.process.call_args[0][0]
        # Root name should be in the lookup
        self.assertIn("showdir", call_args)
        self.assertEqual("ShowDir", call_args["showdir"])
        # Child names should map back to root name
        self.assertIn("episode.s01e01.mkv", call_args)
        self.assertEqual("ShowDir", call_args["episode.s01e01.mkv"])
```
New assertions: `call_args["episode.s01e01.mkv"] == {"ShowDir/Episode.S01E01.mkv": "ShowDir"}`, root entry `{"ShowDir": "ShowDir"}`, nested `{"ShowDir/Season 1/Episode.S01E01.mkv": "ShowDir"}`. Model-building pattern (real `ModelFile` + `add_child` + `_Controller__model.add_file`) at L1110-1121 is reusable. Lock-discipline tests at L1155-1199 (`TestControllerWebhookThreadSafety`) must stay green untouched.

---

### `tests/unittests/test_controller/test_auto_delete.py` (e2e controller + unit)

**Base class to extend** (L11-38) -- `BaseAutoDeleteTestCase` enables auto-delete, seeds `downloaded_file_names` (`"Pack.S01"` etc.), cancels Timers in `tearDown`. For the e2e class, re-create the controller with a real `WebhookManager(self.mock_context)` (RESEARCH "End-to-end regression harness") the same way L20-24 does:
```python
        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.mock_webhook_manager,
        )
```

**Started-controller helper** (`base.py` L56-63, also duplicated at test_auto_delete.py L439-446):
```python
    def _make_controller_started(self):
        self.controller._Controller__started = True
        self.mock_scan_manager.pop_latest_results.return_value = (None, None, None)
        self.mock_lftp_manager.status.return_value = None
        self.mock_file_op_manager.pop_extract_statuses.return_value = None
        self.mock_file_op_manager.pop_completed_extractions.return_value = []
        self.mock_model_builder.has_changes.return_value = False
```

**Evidence-gate preservation pattern** (L1024-1033) -- model the IMPORT-02 "unique name imports exactly as before" test on this:
```python
        f = ModelFile("release.mkv", False)
        f.remote_size = 1000
        self.controller._Controller__model.add_file(f)
        self.persist.downloaded_file_names.add("release.mkv")

        self._process_with_import("release.mkv")

        self.assertIn("release.mkv", self.persist.imported_file_names)
        self.assertIn("release.mkv", self.controller._Controller__pending_auto_deletes)
```
For the e2e versions, give real `ModelFile` leaves `remote_size`/`local_size` (or seed `downloaded_file_names`) so the evidence gate passes; otherwise a rejection test passes for the wrong reason.

**Delete-guard unit pattern** (`TestAutoDeleteCoverageGuard`, L285-294, with helpers `_make_child` L223-232 and `_make_safe_mock_file` L84-90):
```python
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        self.persist.add_imported_child("Pack.S01", "ep02.mkv")
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
```
Duplicate-video case: `d1 = self._make_child("Disc1", children=[self._make_child("movie.mkv")])`, same for `Disc2`; assert `delete_local.assert_not_called()`. Non-video preservation (D-05a): copy L319-335 (`test_execute_proceeds_dir_when_non_video_files_uncovered`) with two `Subs/E0x/English.srt` leaves and covered `.mkv`s -> delete proceeds. Grandfather variant: copy L337-349 (`..._no_imported_children_entry_legacy`) with duplicate discs -> not deleted.

**D-07 legacy persist pattern** (`TestAutoDeletePersistRehydration`, L382-401):
```python
        serialized = self.persist.to_str()
        rehydrated = ControllerPersist.from_str(serialized, max_tracked_files=100)
        # Swap the controller's persist for the rehydrated copy
        self.controller._Controller__persist = rehydrated
```
Pitfall: `AutoDeleteManager` holds its own `_persist` (auto_delete_manager.py L55). For D-07 also set `self.controller._Controller__auto_delete_mgr._persist = rehydrated`, or seed the shared `self.persist` and assert the round-trip separately. Otherwise the test passes via the grandfather path.

**Log-assertion pattern** (L306-314): build `[str(call) for call in self.controller.logger.<level>.call_args_list]` and filter by substring rather than exact counts (the logger mock is shared across controller/WebhookManager child loggers).

---

### `tests/unittests/test_controller/test_auto_delete_rearm.py` (unit)

**Terminal-skip analog** (L160-175):
```python
    def test_bfs_limit_is_terminal_and_does_not_rearm(self):
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_file(is_dir=True, children=[child_a, child_b])
        self._set_model_file(mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        self._rearms()["Pack.S01"] = 3

        with patch("controller.auto_delete_manager._AUTO_DELETE_BFS_NODE_LIMIT", 1):
            self._fire("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertNotIn("Pack.S01", self._pending())
        self.assertNotIn("Pack.S01", self._rearms())
        self.assertNotIn("Pack.S01", self.persist.imported_children)
        self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete deferred")])
```
Copy for `duplicate_basename` (Disc1/Disc2 `movie.mkv`, no patch needed), plus assert one WARNING via `self._warning_messages()` (L56-57). Or add it to `TestAutoDeleteTerminalSkipsDoNotRearm` using `_assert_terminal` (L242-246). Helpers available: `_make_file` L26-31, `_make_child` L33-39, `_set_model_file` L41-42, `_fire` L44-45.

## Shared Patterns

### Log sanitization (CWE-117, D-09)
**Source:** `common.sanitize_log_value`; usage in `controller/webhook_manager.py` L38-42, `controller/auto_delete_manager.py` L113-116, L144-147
**Apply to:** every name, root, relative path, and provenance in the new ambiguity WARNING and the new `duplicate_basename` WARNING; also the existing unsanitized `root_name` in webhook_manager.py L85.

### Log message style
**Source:** all three source files
**Apply to:** new log lines. `.format()` (not f-strings), single-quoted interpolated names, prefix "Auto-delete skipped for '{}': ..." for delete-side skips. Terminal skip -> `logger.warning` (bfs_limit L113); retriable -> `logger.info` (L143, L168).

### Capped list in logs
**Source:** `controller/auto_delete_manager.py` L163-167
**Apply to:** both new warnings (paths and roots lists); "(+N more)" suffix.

### Skip-reason tuple contract
**Source:** `controller/auto_delete_manager.py` L85-93 docstring, L122/L150/L178 returns
**Apply to:** new guard returns `(True, "duplicate_basename", None)`; controller routes it via a terminal reason set rather than `_AUTO_DELETE_DEFER_REASONS`.

### Two-window lock discipline
**Source:** `controller/controller.py` L547-553 docstring, L558 / L581
**Apply to:** Window 1 lookup build stays inside `with self.__model_lock:`; `self.__webhook_manager.process(...)` stays outside. Pinned by `TestControllerWebhookThreadSafety` (test_controller_unit.py L1152+).

### Test naming and structure
**Source:** all test files
**Apply to:** new tests. `unittest.TestCase` subclasses, `test_<behavior>` snake_case names with a docstring citing the decision ID (e.g. "D-07 ..."), name-mangled private access (`self.controller._Controller__model`, `_Controller__execute_auto_delete`, `_Controller__pending_auto_deletes`, `_Controller__auto_delete_mgr`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (e2e harness with a real `WebhookManager` inside `Controller`) | test fixture | e2e | Every existing controller test uses `MagicMock()` for the webhook manager (base.py L40-42). Build it from `BaseAutoDeleteTestCase` (test_auto_delete.py L11-38) + the RESEARCH "End-to-end regression harness" snippet (`_leaf`/`_pack` helpers on real `ModelFile`). |

## Conventions

Derived via `gsd-tools verify conventions --derive --scope src/python/controller` (25 files).

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| File-name casing | snake_case | 72% | 0.714 | named contract |
| Identifier casing (classes) | PascalCase | 89% | 0.392 | named contract |
| Export style | n/a (Python) | -- | -- | insufficient data |
| Import style | n/a (JS axis); Python: explicit imports 100% (named contract); relative vs absolute 64% relative | 64% | 0.943 | contested hotspot |

**Contested hotspots (author's choice):** Python import relativity is split by intent: intra-package imports inside `controller/` are relative (`from .auto_delete_manager import ...`, controller.py L9-19) while cross-package imports are absolute (`from common import ...`, `from model import ...`). Match the local style of the file being edited; do not normalize. Repo-wide, the prototype intentional split is the CJS<->SDK dual resolver (`bin/lib/**` CJS `module.exports`/`require`, `sdk/src/**` ESM `export`/`import`) -- each half internally consistent per directory; not relevant to this Python-only phase.

## Metadata

**Analog search scope:** `src/python/controller/`, `src/python/tests/unittests/test_controller/`
**Files scanned:** 8 (controller.py, webhook_manager.py, auto_delete_manager.py, controller_persist.py, base.py, test_webhook_manager.py, test_auto_delete.py, test_auto_delete_rearm.py, test_controller_unit.py excerpt)
**Pattern extraction date:** 2026-10-08
**Verification gates (from RESEARCH):** quick pytest set in RESEARCH "Validation Architecture"; whole-tree `ruff check /Users/julianamacbook/seedsyncarr/src/python/` (CI lint gate is separate from pytest).
