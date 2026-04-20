# Phase 75: Per-Child Import State (GH #19) - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 5 (3 modified, 2 test modules extended)
**Analogs found:** 5 / 5

All five files are extensions of existing modules — every target has a strong in-repo analog (often the file itself). Patterns are extracted from current code; new code should mirror these conventions exactly.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/controller/controller_persist.py` | persist/model | batch (JSON round-trip) | self (existing `imported_file_names` + `stopped_file_names`) | exact (self-extension) |
| `src/python/controller/webhook_manager.py` | service | event-driven (queue drain + match) | self (existing `process()`) | exact (self-extension, signature widens) |
| `src/python/controller/controller.py` | controller | request-response + event-driven | self (`__check_webhook_imports` L708-758, `__execute_auto_delete` L777-860) | exact (self-extension) |
| `src/python/tests/unittests/test_controller/test_auto_delete.py` | test (unit) | request-response | self (28 cases, PR #18 `_make_safe_mock_file` + `_make_child` scaffolding) | exact (self-extension) |
| `src/python/tests/unittests/test_controller/test_controller_persist.py` | test (unit) | batch | self (`test_imported_file_names_roundtrip`, `test_backward_compatibility_no_imported_key`) | exact (self-extension) |

No file in this phase lacks an analog; RESEARCH.md fallback patterns are not needed.

## Pattern Assignments

### `src/python/controller/controller_persist.py` (persist, batch)

**Analog:** self — follow the conventions already used for `imported_file_names` and `stopped_file_names`.

**Pattern 1 — Key constant + field declaration** (L16-20, L47-49):

```python
# Keys
__KEY_DOWNLOADED_FILE_NAMES = "downloaded"
__KEY_EXTRACTED_FILE_NAMES = "extracted"
__KEY_STOPPED_FILE_NAMES = "stopped"
__KEY_IMPORTED_FILE_NAMES = "imported"
```

```python
# Track files that Sonarr has imported - used for import detection
# and preventing duplicate processing
self.imported_file_names: BoundedOrderedSet[str] = BoundedOrderedSet(
    maxlen=self._max_tracked_files
)
```

New `imported_children` differs: values are themselves `BoundedOrderedSet[str]` (per-root). Type annotation per D-01:
`self.imported_children: Dict[str, BoundedOrderedSet[str]] = {}`

Two bounds apply (D-02):
- Per-root set `maxlen` — planner's call, default **500** per context (separate from `self._max_tracked_files`). Suggest adding `DEFAULT_MAX_CHILDREN_PER_ROOT = 500` as a class constant near `DEFAULT_MAX_TRACKED_FILES` (L23).
- Global cap on number of root keys — reuse `self._max_tracked_files` (10000). Evict oldest root key on overflow using `OrderedDict`-style insertion order (the dict itself is ordered in Python 3.7+; on add of a new root past cap, `popitem(last=False)`).

**Pattern 2 — Backward-compat load in `from_str`** (L94, L124-133):

```python
# stopped_list is optional for backwards compatibility with old persist files
stopped_list = dct.get(ControllerPersist.__KEY_STOPPED_FILE_NAMES, [])
```

```python
# imported_list is optional for backwards compatibility with old persist files
imported_list = dct.get(ControllerPersist.__KEY_IMPORTED_FILE_NAMES, [])
for name in imported_list:
    evicted = persist.imported_file_names.add(name)
    if evicted:
        persist._logger.debug(
            "Evicted '{}' from imported files during load (limit: {})".format(
                evicted, persist._max_tracked_files
            )
        )
```

For `imported_children` follow the same `dct.get(__KEY_IMPORTED_CHILDREN, {})` shape. JSON shape on disk per D-03: top-level dict of root-name → list-of-child-names (lists, not sets, since JSON has no set type; use the same `.as_list()` / re-`add()` round-trip pattern as `imported_file_names`).

**Pattern 3 — `to_str` serialization** (L148-153):

```python
dct = dict()
dct[ControllerPersist.__KEY_DOWNLOADED_FILE_NAMES] = self.downloaded_file_names.as_list()
dct[ControllerPersist.__KEY_EXTRACTED_FILE_NAMES] = self.extracted_file_names.as_list()
dct[ControllerPersist.__KEY_STOPPED_FILE_NAMES] = self.stopped_file_names.as_list()
dct[ControllerPersist.__KEY_IMPORTED_FILE_NAMES] = self.imported_file_names.as_list()
return json.dumps(dct, indent=Constants.JSON_PRETTY_PRINT_INDENT)
```

For `imported_children`, build a nested dict via comprehension:
`dct[__KEY_IMPORTED_CHILDREN] = {root: bset.as_list() for root, bset in self.imported_children.items()}`

**Pattern 4 — Eviction stats** (L60-72):

Extend `get_eviction_stats()` to also report `imported_children_evictions` (sum across per-root sets) and `imported_children_root_count`. Mirror the existing keys: `'downloaded_evictions'`, `'extracted_evictions'`, `'stopped_evictions'`, `'imported_evictions'`, `'max_tracked_files'`.

---

### `src/python/controller/webhook_manager.py` (service, event-driven)

**Analog:** self — `process()` already drains the queue and matches via `name_to_root`. Signature widens from `List[str]` to `List[Tuple[str, str]]` per D-06.

**Pattern — current `process()` body** (L37-81):

```python
def process(self, name_to_root: Dict[str, str]) -> List[str]:
    newly_imported = []

    # Drain queue
    while not self.__import_queue.empty():
        try:
            source, file_name = self.__import_queue.get_nowait()
        except Empty:
            # Queue empty (race condition between empty() and get_nowait())
            break

        # Case-insensitive matching against root and child names
        root_name = name_to_root.get(file_name.lower())
        if root_name is not None:
            newly_imported.append(root_name)
            self.logger.info(
                "{} import detected: '{}' (matched SeedSyncarr file '{}')".format(
                    source, file_name, root_name
                )
            )
        else:
            self.logger.warning(
                "{} webhook file '{}' not found in SeedSyncarr model "
                "(checked {} names including children)".format(
                    source, file_name, len(name_to_root)
                )
            )

    return newly_imported
```

**Change for phase 75:**
- Return type: `List[Tuple[str, str]]` (also update `from typing import Dict, List` at L2 to add `Tuple`).
- Append `(root_name, file_name)` instead of just `root_name`. `file_name` as received is the "matched_name" — preserve original casing so downstream can use it as the child basename (per D-07 and code_context "store basenames as-received from the webhook"). When the enqueued `file_name` IS the root (case-insensitive equals `root_name`), it still flows through as the matched_name and the caller will treat `matched_name == root`.

**Ripple — callers of `process()`:**
- `src/python/controller/controller.py` L745 — `newly_imported = self.__webhook_manager.process(name_to_root)` — consumer must unpack tuples.
- `src/python/tests/unittests/test_controller/test_auto_delete.py` L45, L329, L343 — `self.mock_webhook_manager.process.return_value = []` / `["test_file.mkv"]` — update fixtures to tuples: `[("test_file.mkv", "test_file.mkv")]`.
- `src/python/tests/unittests/test_controller/test_controller_unit.py` L44, L1046, L1052, L1140 — same mock-return update. Test assertions on `imported_file_names` continue to pass because Window-2 still adds the root.
- `src/python/tests/unittests/test_controller/test_webhook_manager.py` — every existing case (L21-79+) asserts the flat `List[str]` shape; every existing assertion must be rewritten to tuple form (e.g. `self.assertEqual([("File.A", "File.A")], result)` at L28, `self.assertIn(("File.A", "File.A"), result)` at L44). Add at least one new case where the enqueued name is a child basename and the returned tuple is `(root, child)` with `matched_name != root_name`.

---

### `src/python/controller/controller.py` (controller, request-response + event-driven)

Two distinct edit sites.

#### Site A: `__check_webhook_imports` (L708-758) — Window-2 per-child write

**Analog:** the current Window-2 block (L749-753).

**Pattern — current Window-2 lock + mutation** (L747-753):

```python
if newly_imported:
    # Window 2: Update model import status for all newly imported files under single lock
    with self.__model_lock:
        for file_name in newly_imported:
            self.__persist.imported_file_names.add(file_name)
            self.logger.info("Recorded webhook import: '{}'".format(file_name))
            self._set_import_status(self.__model, file_name)
```

**Change for phase 75 (D-07):**
- Loop variable becomes `for root_name, matched_name in newly_imported:` (tuples from new `process()` return).
- Keep `self.__persist.imported_file_names.add(root_name)` unchanged (D-05 backward-compat).
- Add new mutation: insert `matched_name` into `self.__persist.imported_children[root_name]`, creating the per-root `BoundedOrderedSet` on first touch. Planner specifies the helper (inline `setdefault` or a `ControllerPersist.add_imported_child(root, child)` method — latter keeps cap/eviction logic colocated in persist).
- Stays inside the existing `with self.__model_lock:` — no new lock (D-07, code_context "`__model_lock` two-window pattern").
- Keep `self._set_import_status(self.__model, file_name)` called with `root_name` (UI badge is driven by root).

**Scheduler call at L756-758:** loop over unique `root_name`s from `newly_imported` tuples — current code iterates each entry; with tuples, de-duplicate if the same root appears twice (two child webhooks in one cycle). Simplest: `for root_name in {r for r, _ in newly_imported}: self.__schedule_auto_delete(root_name)`.

#### Site B: `__execute_auto_delete` (L777-860) — partial-coverage guard

**Analog:** the state-guard (L824-834) and pack-guard (L836-855) immediately preceding the insertion point.

**Pattern — existing state-guard** (L824-834):

```python
# State guard: do not delete a file that is mid-lifecycle. Mirrors
# __handle_delete_command so the Timer path cannot race an in-flight
# sync, queue, or extract when a re-download arrives between
# scheduling and firing (e.g., Deluge re-seed triggers a re-sync).
if file.state not in deletable_states:
    self.logger.info(
        "Auto-delete skipped for '{}': file is in state {}".format(
            file_name, str(file.state)
        )
    )
    return
```

**Pattern — existing pack-guard BFS** (L836-855):

```python
# Pack guard: when the root is a directory, walk every descendant
# and skip if ANY child is in an active state. Prevents wiping a
# season pack while a sibling episode is still being downloaded or
# extracted (Sonarr's per-episode webhook schedules the pack root).
if file.is_dir:
    unsafe_child = None
    frontier = collections.deque(file.get_children())
    while frontier:
        child = frontier.popleft()
        if child.state not in deletable_states:
            unsafe_child = child
            break
        frontier.extend(child.get_children())
    if unsafe_child is not None:
        self.logger.info(
            "Auto-delete skipped for '{}': child '{}' is in state {}".format(
                file_name, unsafe_child.name, str(unsafe_child.state)
            )
        )
        return
```

**Change for phase 75 (D-08, D-09, D-16):**

1. **Module-level video-extension constant** — add near the top of the `__execute_auto_delete` region (e.g. just above the `Controller` class, or as a class-level attribute near `_set_import_status`). Must be a `frozenset` of lowercase extensions with leading dot:

   ```python
   _VIDEO_EXTENSIONS = frozenset({'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.ts', '.wmv', '.flv', '.webm'})
   ```

   Comparison: `os.path.splitext(name)[1].lower() in _VIDEO_EXTENSIONS`. Note `import os` at L1-8 currently is **not** imported — planner must add `import os` to the imports block (L1-22) or use `name.rsplit('.', 1)` to avoid a new dependency. Prefer `os.path.splitext` (Python stdlib convention used elsewhere in the codebase; verify by searching `controller.py`).

2. **One-traversal extension of the pack-guard BFS** — per code_context "Extend the pack-guard BFS to also collect video basenames for the coverage check — one traversal." In a single BFS, both (a) check state for the pack-guard and (b) append to a `set[str]` of video basenames. On the break-early path the set is discarded; otherwise fall through to coverage check.

3. **Coverage guard — new third skip condition** (runs after state-guard and pack-guard, still under `__model_lock` since it reads `self.__persist.imported_children`):

   ```python
   # Coverage guard: pack roots with a directory on disk require every
   # on-disk video child to appear in imported_children[root]. A missing
   # child indicates Sonarr silently rejected the file; deleting now
   # would lose data. Grandfather: if no per-root entry exists, treat
   # as fully imported (D-14).
   if file.is_dir:
       imported_child_set = self.__persist.imported_children.get(file_name)
       if imported_child_set is not None:
           # on_disk_videos collected during the pack-guard BFS above
           missing = on_disk_videos - set(imported_child_set)
           if missing:
               missing_list = sorted(missing)
               shown = missing_list[:5]
               suffix = ""
               if len(missing_list) > 5:
                   suffix = " (+{} more)".format(len(missing_list) - 5)
               self.logger.info(
                   "Auto-delete skipped for '{}': partial import "
                   "({} of {} on-disk video children imported; missing: {}{})".format(
                       file_name,
                       len(on_disk_videos) - len(missing),
                       len(on_disk_videos),
                       shown,
                       suffix,
                   )
               )
               return
   ```

   Case sensitivity: both on-disk basename collection and `imported_child_set` membership should match by **lowercased** basename (code_context: "matching on file names is case-INSENSITIVE via `.lower()`"). Normalize on insertion in Site A (`matched_name.lower()`) AND on comparison here.

4. **Clear-on-success** (D-04) — after `self.__file_op_manager.delete_local(file)` at L859, remove the per-root entry. This is **outside** the lock; take `__model_lock` briefly for the pop:

   ```python
   self.__file_op_manager.delete_local(file)
   self.logger.info("Auto-deleted local file '{}'".format(file_name))
   with self.__model_lock:
       self.__persist.imported_children.pop(file_name, None)
   ```

---

### `src/python/tests/unittests/test_controller/test_auto_delete.py` (test, request-response)

**Analog:** self — PR #18 already established the fixture shape. Reuse `_make_safe_mock_file` (L105-111) and `_make_child` (L244-249).

**Pattern — safe mock file helper** (L105-111):

```python
def _make_safe_mock_file(self, state=ModelFile.State.DOWNLOADED, is_dir=False, children=None):
    """Helper: build a ModelFile mock that passes the state + pack guards."""
    mock_file = MagicMock(spec=ModelFile)
    mock_file.state = state
    mock_file.is_dir = is_dir
    mock_file.get_children.return_value = children or []
    return mock_file
```

**Pattern — child helper with name** (L244-249):

```python
def _make_child(self, name, state=ModelFile.State.DOWNLOADED, children=None):
    child = MagicMock(spec=ModelFile)
    child.name = name
    child.state = state
    child.get_children.return_value = children or []
    return child
```

**Pattern — existing pack-guard proceeds case (the closest shape for the new "all children imported" case)** (L273-279):

```python
def test_execute_proceeds_dir_when_all_children_safe(self):
    child_a = self._make_child("ep01.mkv", state=ModelFile.State.DOWNLOADED)
    child_b = self._make_child("ep02.mkv", state=ModelFile.State.EXTRACTED)
    mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
    self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
    self.controller._Controller__execute_auto_delete("Pack.S01")
    self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
```

**Pattern — controller access to persist in tests:**
`self.persist` is the live `ControllerPersist(max_tracked_files=100)` (L19 of `BaseAutoDeleteTestCase`), which is passed through `Controller(..., persist=self.persist, ...)` at L47. Seed `imported_children` directly via `self.persist.imported_children[...] = BoundedOrderedSet(...)` (or helper if added).

**New cases for phase 75 (D-19, six cases — add as a new `TestAutoDeleteCoverageGuard(BaseAutoDeleteTestCase)` class, or append to `TestAutoDeleteExecution`):**

1. `test_execute_proceeds_single_file_root_when_root_imported` — non-dir root, `imported_file_names` contains root, coverage check is skipped (D-11, `file.is_dir == False`), delete proceeds.
2. `test_execute_proceeds_dir_when_all_video_children_imported` — dir with `ep01.mkv`, `ep02.mkv`; `imported_children["Pack.S01"] = {"ep01.mkv", "ep02.mkv"}`; delete proceeds.
3. `test_execute_skips_dir_when_one_video_child_missing` — dir with `ep01.mkv`, `ep02.mkv`; `imported_children["Pack.S01"] = {"ep01.mkv"}`; delete skipped; assert INFO log contains `"partial import"` and lists `ep02.mkv`.
4. `test_execute_proceeds_dir_when_non_video_files_uncovered` — dir with `ep01.mkv`, `ep01.nfo`, `sample.txt`; `imported_children["Pack.S01"] = {"ep01.mkv"}`; delete proceeds (non-allowlisted extensions ignored per D-10).
5. `test_execute_proceeds_dir_when_no_imported_children_entry_legacy` — dir on disk, root in `imported_file_names`, no key in `imported_children` (grandfather per D-14); delete proceeds.
6. `test_execute_clears_imported_children_after_delete` — dir with all children covered; after successful delete, `"Pack.S01" not in self.persist.imported_children` (D-04).

Naming convention matches existing prefixes `test_execute_skips_...` and `test_execute_proceeds_...`.

Case-sensitivity test seed: lowercase child basenames in the seeded `imported_children` set (`"ep01.mkv"`) vs mixed-case in `_make_child("Ep01.MKV", ...)` — at least one case should verify the lowercasing comparison.

---

### `src/python/tests/unittests/test_controller/test_controller_persist.py` (test, batch)

**Analog:** self — `test_imported_file_names_roundtrip` (L195-203) and `test_backward_compatibility_no_imported_key` (L214-218).

**Pattern — existing round-trip test** (L195-212):

```python
def test_imported_file_names_roundtrip(self):
    """Test imported_file_names serialization roundtrip."""
    persist = ControllerPersist()
    persist.imported_file_names.add("import1")
    persist.imported_file_names.add("import2")
    persist.imported_file_names.add("import3")

    persist_actual = ControllerPersist.from_str(persist.to_str())
    self.assertEqual(persist.imported_file_names, persist_actual.imported_file_names)

def test_imported_file_names_in_to_str(self):
    """Test imported key appears in serialized output."""
    persist = ControllerPersist()
    persist.imported_file_names.add("file_a")
    persist.imported_file_names.add("file_b")
    dct = json.loads(persist.to_str())
    self.assertIn("imported", dct)
    self.assertEqual(["file_a", "file_b"], dct["imported"])
```

**Pattern — existing backward-compat test** (L214-218):

```python
def test_backward_compatibility_no_imported_key(self):
    """Test old persist files without imported key load successfully."""
    content = json.dumps({"downloaded": ["a"], "extracted": ["b"]})
    persist = ControllerPersist.from_str(content)
    self.assertEqual(0, len(persist.imported_file_names))
```

**New cases for phase 75 (D-20):**

1. `test_imported_children_roundtrip` — seed two roots with 2-3 children each, `to_str` → `from_str` → assert nested structure preserved (compare via `{root: persist.imported_children[root].as_list() for root in ...}`).
2. `test_imported_children_in_to_str` — after adds, `json.loads(persist.to_str())["imported_children"]` is a dict of `{root: [child, ...]}`.
3. `test_backward_compatibility_no_imported_children_key` — load a persist blob missing the new key; `persist.imported_children == {}`.
4. `test_imported_children_eviction_per_root` — seed a root with > per-root `maxlen` children, assert oldest child is evicted, newer retained. Mirrors `test_eviction_on_add` (L125-136).
5. `test_imported_children_partial_coverage_survives_restart` (D-20 canonical case) — build a persist with `imported_file_names = {"Pack.S01"}` and `imported_children = {"Pack.S01": {"ep01.mkv"}}` (partial), round-trip through `to_str`/`from_str`, then drive `__execute_auto_delete` on the rehydrated state and assert it skips. This may belong in `test_auto_delete.py` instead if the test requires a live controller — decide by whether the assertion is pure persist equality or full skip behavior. Per CONTEXT D-20, the intent is "Timer-fire still skips post-restart" so the test is closer to integration and should live in `test_auto_delete.py` with the persist loaded via `ControllerPersist.from_str(...)` then passed into the controller fixture.

Naming mirrors the existing `test_imported_*` and `test_backward_compatibility_*` prefixes.

---

## Shared Patterns

### Thread-safety: `__model_lock` two-window pattern
**Source:** `src/python/controller/controller.py` `__check_webhook_imports` (L725-758)
**Apply to:** Site A (per-child write). Do NOT widen the lock. Window 1 reads only (builds `name_to_root`), Window 2 mutates (`imported_file_names.add` + `_set_import_status` + new `imported_children[root].add`). `self.__webhook_manager.process(...)` and `self.__schedule_auto_delete(...)` remain outside the lock.

```python
with self.__model_lock:
    # Window 1: read-only build
    ...
# outside lock: queue/timer work
newly_imported = self.__webhook_manager.process(name_to_root)
if newly_imported:
    with self.__model_lock:
        # Window 2: mutations
        ...
```

### Skip-log phrasing
**Source:** `src/python/controller/controller.py` `__execute_auto_delete` (L829-834, L850-854)
**Apply to:** New coverage-guard log (D-16).

Existing two lines to pattern-match:
```
Auto-delete skipped for '{file_name}': file is in state {state}
Auto-delete skipped for '{file_name}': child '{child.name}' is in state {child.state}
```

New third line (D-16 shape):
```
Auto-delete skipped for '{file_name}': partial import ({N} of {M} on-disk video children imported; missing: {[child1, ...]}{"" or " (+K more)"})
```

Truncation: show first 5 in the list literal, append ` (+K more)` when > 5.

### JSON round-trip with backward-compat
**Source:** `src/python/controller/controller_persist.py` (L94, L124-133, L149-152)
**Apply to:** `imported_children` field in both persist and tests.

Key invariants:
- Read path: `dct.get(KEY, default)` — missing key is not an error.
- Write path: always serialized (no omit), so after first save the key exists.
- Eviction on load: when loaded data exceeds cap, evict oldest via repeated `.add()` (which enforces `maxlen` automatically).
- Logger debug message on eviction uses `persist._logger.debug(...)`.

### BFS over `ModelFile.get_children()`
**Source:** `src/python/controller/controller.py` L736-740 (`__check_webhook_imports`) and L842-848 (pack-guard)
**Apply to:** Site B coverage collection — extend the pack-guard traversal rather than add a second BFS.

```python
frontier = collections.deque(file.get_children())
while frontier:
    child = frontier.popleft()
    # existing pack-guard check here
    # NEW: if child is not a dir and has video extension, add basename to on_disk_videos
    frontier.extend(child.get_children())
```

Tests mock `get_children()` directly (see `_make_child` pattern above); no filesystem calls.

### WebhookManager mock return-value in tests
**Source:** `src/python/tests/unittests/test_controller/test_auto_delete.py` L45, L329, L343; `test_controller_unit.py` L44, L1046, L1052, L1140
**Apply to:** Every test that sets `mock_webhook_manager.process.return_value` — update shape from `List[str]` to `List[Tuple[str, str]]`.

Migration pattern (applied to each occurrence):
```python
# Before
self.mock_webhook_manager.process.return_value = ["test_file.mkv"]
# After
self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]
```

For child-named imports:
```python
self.mock_webhook_manager.process.return_value = [("Pack.S01", "ep01.mkv")]
```

## No Analog Found

None — all five target files extend existing modules with established in-repo patterns.

## Metadata

**Analog search scope:** `src/python/controller/`, `src/python/common/`, `src/python/tests/unittests/test_controller/`, `src/python/web/handler/`
**Key files read:** `controller_persist.py` (170 lines), `webhook_manager.py` (82 lines), `controller.py` L1-60 + L700-870 + L330-365 (targeted), `bounded_ordered_set.py` (204 lines), `test_auto_delete.py` (347 lines), `test_controller_persist.py` (229 lines), `test_controller_unit.py` L1030-1150 (targeted), `test_webhook_manager.py` L1-80 (targeted), `web/handler/webhook.py` L120-161 (targeted)
**Pattern extraction date:** 2026-04-20
