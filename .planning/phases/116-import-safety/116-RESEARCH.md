# Phase 116: Import Safety - Research

**Researched:** 2026-10-08
**Domain:** Python controller logic: webhook import matching (`name_to_root`) and the auto-delete coverage guard
**Confidence:** HIGH (all findings come from reading the code in this repo plus a live probe of current behavior; there are no external libraries)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Import-side ambiguity rejection (Controller.__check_webhook_imports / WebhookManager.process)
- **D-01:** The lookup key is the lowercased basename; the lookup VALUE is the set of complete, case-preserving model paths (root + relative path) that carry that basename. Lowercase only the key — never the stored path — so case-distinct files at different paths remain distinct candidates (owner note).
- **D-02:** A webhook name resolving to exactly ONE distinct path proceeds exactly as today (record, badge, evidence gate, arm auto-delete). Repeated references to the same complete path are deduplicated and are not ambiguous.
- **D-03:** A webhook name resolving to TWO OR MORE distinct paths is ambiguous and rejected — whether the paths are in different releases, roots differing only by case, a root name equal to a child basename elsewhere, or repeated basenames inside one release (`Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv`). Rejection = no `imported_file_names` entry, no `add_imported_child`, no `downloaded_file_names` commit, no import badge, no auto-delete timer.
- **D-04:** Accepted consequence (owner-confirmed): a pack containing distinct files with the same basename can never be fully covered and is never auto-deleted; it stays on disk for manual removal. Cost is disk space, never lost media.

#### Delete-time duplicate-basename guard (AutoDeleteManager.run_bfs_and_coverage)
- **D-05:** Add a guard at deletion time: if a root's BFS finds two or more distinct file paths whose basenames are equal case-insensitively, auto-delete is skipped (pack left untouched) with a log line explaining why. This applies regardless of persisted state — including legacy (pre-1.7.4) `imported_children` records that would otherwise read as "fully covered", and the D-14 grandfather path (no per-root entry).
- **D-06:** The guard's skip is retriable/non-terminal in the same way as the existing `partial_coverage` skip unless research finds the deferral/re-arm budget makes a terminal reason more appropriate — planner's call, but it must never delete.
- **D-07:** Mandatory regression test: a legacy persist where `imported_children[root]` already contains the duplicated basename (i.e. "fully covered") must NOT override the guard — the pack is not deleted.

#### Logging (no UI)
- **D-08:** Log warning only — no UI badge/notification in this patch. The import-rejection warning includes: the webhook filename, the candidate releases (roots), and an explicit statement that no import credit or automatic cleanup was authorized. For duplicates within one pack, include the distinct relative paths so the ambiguity is visible.
- **D-09:** All logged names/paths go through `sanitize_log_value` (CWE-117), matching existing import logging.

### Claude's Discretion
- Exact data structure for the multi-path lookup and where dedup happens (controller vs WebhookManager), provided `WebhookManager.process` keeps returning only unambiguous matches.
- Log wording and level beyond the content required by D-08; the delete-time skip may log at info like other skip reasons or warning — pick consistently.

### Deferred Ideas (OUT OF SCOPE)
- UI surfacing of rejected ambiguous imports (badge/notification) — new capability, future phase.
- Path-aware import matching (map webhook source paths to model paths) so duplicate-name packs could be safely covered — out of scope (path-mapping redesign).
- Backlog 999.1 (accept import whose payload size equals remote size) — stays parked.
- Reviewed todo `2026-04-21-webob-cgi-upstream-unblock.md` — unrelated, not folded.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMPORT-01 | A webhook name matching more than one distinct model path (across releases, roots differing only by case, root name = child basename elsewhere, repeated basenames in one release) is rejected: no imported record, no per-child coverage credit, no badge, no auto-delete timer, one sanitized warning naming candidate roots | Pattern 1 (multi-path lookup built in Window 1), Pattern 2 (rejection inside `WebhookManager.process`, return contract unchanged), Pattern 3 (delete-time guard for legacy and grandfathered records), Pitfall 1 (bug reproduced live) |
| IMPORT-02 | A webhook name matching exactly one distinct path (including repeated references to that path) behaves exactly as before | Pattern 2 keeps the `List[(root_name, matched_name)]` return contract, so the evidence gate, persist writes, badge and timer code in Window 2 stay unchanged; preservation tests listed in the Validation Architecture section |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

There is no project `./CLAUDE.md`. The `.claude/skills/` and `.agents/skills/` folders only contain `aidesigner-frontend`, which does not apply to this Python-only phase. These rules come from the user's global CLAUDE.md and memory:

- **Security (absolute):** never log sensitive data; sanitize every logged value that comes from a webhook or remote scanner (`sanitize_log_value`, CWE-117). This matches D-09.
- **Code quality:** follow existing codebase patterns (two lock windows, the skip-reason tuple, single-underscore storage in collaborators, `.format()` style logging).
- **Exceptions:** never swallow an exception silently. The existing `except ModelError: logger.debug(...)` in Window 1 is the established pattern; keep it.
- **CI lint gap (memory):** CI runs `ruff check src/python/` on the whole tree as a separate gate from pytest. Build verification for this phase must run ruff on the whole tree.
- **Division of labor:** technical choices (data shape, terminal vs retriable) are the planner's/executor's to make. Product-visible consequences (which packs auto-delete) must be stated plainly. See Open Question 1.

## Summary

The defect is real and reproduces with current code. A throwaway probe test (since removed) drove `Controller.process()` with a real `WebhookManager`. With two releases each containing `sample.mkv`, a `sample.mkv` webhook credited `Rel.B` and armed its auto-delete Timer. With `Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv`, a `movie.mkv` webhook wrote `imported_children = {'Pack': ['movie.mkv']}`. At delete time `run_bfs_and_coverage` collapses both discs into one lowercased basename `{'movie.mkv'}`, so the pack reads as fully covered and would be deleted. [VERIFIED: local probe run against main @ f6548f7]

The fix touches three spots. Each one leaves the surrounding contracts unchanged:
1. **Window 1 in `Controller.__check_webhook_imports`** builds `Dict[str, Dict[str, str]]`: lowercased basename → {case-preserving relative path → root name}. The inner dict is keyed by full path, so it de-duplicates (D-01, D-02). Compute paths by carrying the path string through the BFS. Do not use `ModelFile.full_path`.
2. **`WebhookManager.process`** takes the new shape. For one distinct path it appends `(root, matched_name)` exactly as today. For two or more it logs one sanitized warning and appends nothing. The return type `List[Tuple[str, str]]` is unchanged, so the evidence gate, persist writes, badge and timer code in Window 2 need **zero edits** (IMPORT-02 "exactly as before" holds by construction).
3. **`AutoDeleteManager.run_bfs_and_coverage`** records each on-disk video's relative path while it traverses. After the unsafe-child check and **before** the coverage check, it returns a skip if any lowercased video basename maps to two or more paths. That runs before any look at `imported_children`, so legacy "fully covered" records and the D-14 grandfather path cannot get past it (D-05, D-07).

**Primary recommendation:** Do the dedup and rejection inside `WebhookManager.process`, with `Dict[str, Dict[str, str]]` as the lookup. Make the delete-time guard a **terminal** skip reason, `duplicate_basename`, handled exactly like `bfs_limit` (no re-arm, clear the counter, pop `imported_children`), logged as a WARNING. Limit the guard to video-extension files, the same set coverage uses. Prove fail-before/pass-after with end-to-end controller tests (`enqueue_import` → `Controller.process()` on a real `Model`), because they don't depend on the lookup's data shape.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Build basename→paths lookup from the model | API / Backend (Controller, Window 1 under `__model_lock`) | — | Only Controller owns `__model` and `__model_lock`; two-window discipline |
| Ambiguity decision + rejection warning | API / Backend (`WebhookManager.process`) | — | Already the sole matcher; holds `source`/`provenance` needed for the log line; keeps "process returns only unambiguous matches" contract (Discretion) |
| Evidence gate, persist writes, badge, timer arm | API / Backend (Controller, Window 2) | Database / Storage (`ControllerPersist`) | Unchanged; consumes the unchanged return contract |
| Delete-time duplicate guard | API / Backend (`AutoDeleteManager.run_bfs_and_coverage`) | Controller `__execute_auto_delete` (skip-reason handling) | BFS already lives there; guard must precede coverage and is independent of persist |
| Persist format | Database / Storage | — | No change (out of scope); `imported_children` stays lowercased basenames |

## Standard Stack

No new dependencies. This phase only changes existing Python code.

| Component | Version (verified locally) | Purpose |
|-----------|---------------------------|---------|
| Python (poetry venv) | 3.12.12 | Runtime; CI also uses 3.12 [VERIFIED: `poetry run python --version`] |
| pytest | 9.1.1 (pyproject `^9.0.3`, `timeout = 60`) | Test runner [VERIFIED: `poetry run pytest --version`] |
| ruff | CI pins 0.15.22; local poetry venv has 0.15.9 | Whole-tree lint gate [VERIFIED: `.github/workflows/ci.yml` L91, `poetry run ruff --version`] |
| stdlib `collections.deque`, `os.path.splitext` | — | Already used by both BFS sites |

## Package Legitimacy Audit

Not applicable. This phase installs no external packages. **Packages removed:** none. **Packages flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
Sonarr/Radarr POST ──> web/handler/webhook.py
                         │  basename(episodeFile/movieFile.sourcePath) only
                         v
                  WebhookManager.enqueue_import(source, name, provenance)  [web thread, Queue]
                         │
 Controller.process() ── __check_webhook_imports()
   │
   ├─ Window 1 (under __model_lock): BFS every root, carrying rel_path
   │     name_to_paths[basename.lower()][rel_path(case-preserved)] = root_name
   │
   ├─ WebhookManager.process(name_to_paths)        [no lock]
   │     for each queued name:
   │       candidates = name_to_paths.get(name.lower())
   │       ├─ none        -> WARNING "not found" (unchanged)
   │       ├─ 1 path      -> append (root, name) + INFO "import detected" (unchanged)
   │       └─ >=2 paths   -> WARNING "ambiguous ... candidate roots ... paths ...
   │                          no import credit or automatic cleanup authorized"; append nothing
   │     returns List[(root, matched_name)]  (unambiguous only)
   │
   └─ Window 2 (unchanged): evidence gate -> downloaded commit -> imported_file_names
         -> add_imported_child (WR-01) -> import badge -> accepted_roots -> __schedule_auto_delete

Timer fires ─> Controller.__execute_auto_delete(root)
   ├─ disabled / dry-run / not in model / not downloaded  -> terminal (unchanged)
   ├─ root state not deletable                            -> retriable (unchanged)
   └─ is_dir -> AutoDeleteManager.run_bfs_and_coverage(file, root, states)
         BFS (node limit) carrying rel_path
           ├─ > limit               -> (True, "bfs_limit")          terminal
           ├─ unsafe child          -> (True, "unsafe_child")       retriable
           ├─ NEW: video basename seen at >=2 paths
           │                        -> (True, "duplicate_basename") terminal, WARNING w/ paths
           ├─ imported_children[root] present and missing videos
           │                        -> (True, "partial_coverage")   retriable
           └─ else                  -> (False, "", on_disk_videos)  -> delete_local
```

### Recommended file touch list
```
src/python/controller/controller.py          # Window 1 lookup build; terminal-reason branch; docstrings
src/python/controller/webhook_manager.py     # process(): new param shape, ambiguity rejection + warning
src/python/controller/auto_delete_manager.py # BFS carries rel_path; duplicate_basename guard; docstring/constant comment
src/python/tests/unittests/test_controller/test_webhook_manager.py   # migrate fixtures to new shape + new unit tests
src/python/tests/unittests/test_controller/test_controller_unit.py   # 3 lookup-shape tests (L1095-1146) updated
src/python/tests/unittests/test_controller/test_auto_delete.py       # end-to-end regressions + guard + D-07
src/python/tests/unittests/test_controller/test_auto_delete_rearm.py # terminal-skip test for duplicate_basename
```

### Pattern 1: Multi-path lookup built in Window 1 (D-01, D-02)
**What:** Carry the case-preserving relative path through the BFS. Key the inner dict by that path so a repeated reference to the same path collapses to one entry.
**Why carry the path instead of using `ModelFile.full_path`:** `full_path` walks `parent` pointers. `ModelPipeline._set_import_status` (`controller/model_pipeline.py` L121-141) shallow-copies only one level of children and reparents only them, so grandchildren keep pointing at the old child object. Names don't change, so the string probably still comes out right, but the result depends on parent-pointer integrity. Also, the delete-time tests use `MagicMock(spec=ModelFile)` children with no parent chain, where `full_path` returns a MagicMock. Carrying the path through the BFS works in both places. [VERIFIED: codebase read]
**Uniqueness guarantee:** `Model.__files` is a dict keyed by root name, and `ModelFile.add_child` raises on a duplicate sibling name (case-sensitive) (`model/file.py` L294-304). So each relative path names exactly one node, and `Movie.mkv` / `movie.mkv` siblings remain two distinct paths. [VERIFIED: codebase read]

```python
# Source: adapted from existing controller.py L557-571
# lowercased basename -> {case-preserving relative path -> root model file name}
name_to_paths: Dict[str, Dict[str, str]] = {}
with self.__model_lock:
    for root_name in self.__model.get_file_names():
        name_to_paths.setdefault(root_name.lower(), {})[root_name] = root_name
        try:
            root_file = self.__model.get_file(root_name)
            if root_file.is_dir:
                frontier = collections.deque((c, root_name) for c in root_file.get_children())
                while frontier:
                    child, parent_path = frontier.popleft()
                    child_path = parent_path + "/" + child.name
                    name_to_paths.setdefault(child.name.lower(), {})[child_path] = root_name
                    frontier.extend((g, child_path) for g in child.get_children())
        except ModelError:
            self.logger.debug(...)  # unchanged
newly_imported = self.__webhook_manager.process(name_to_paths)
```
Use an explicit `"/"` join, not `os.path.join`. These are display and identity keys, not filesystem paths.

### Pattern 2: Ambiguity rejection inside `WebhookManager.process` (D-03, D-08, D-09)
**Signature:** `process(self, name_to_paths: Dict[str, Dict[str, str]]) -> List[Tuple[str, str]]`. The return type is **unchanged**, so Controller Window 2 and every test that mocks `process.return_value = [(root, name)]` keep working (about 15 tests in test_auto_delete.py, test_controller_unit.py and test_controller.py). [VERIFIED: grep]

```python
candidates = name_to_paths.get(file_name.lower())
safe_file_name = sanitize_log_value(file_name)
if not candidates:
    # unchanged "not found" warning; len(name_to_paths) still = number of distinct names
elif len(candidates) == 1:
    root_name = next(iter(candidates.values()))
    newly_imported.append((root_name, file_name))
    # unchanged INFO line (consider sanitizing root_name too -- see Pitfall 5)
else:
    roots = sorted(set(candidates.values()))
    paths = sorted(candidates.keys())
    self.logger.warning(
        "{} webhook import '{}' is ambiguous: matches {} distinct SeedSyncarr paths "
        "in release(s) {} ({}); no import credit or automatic cleanup authorized ({})".format(
            source, safe_file_name, len(paths),
            _fmt_capped([sanitize_log_value(r) for r in roots]),
            _fmt_capped([sanitize_log_value(p) for p in paths]),
            sanitize_log_value(provenance)))
```
- Emit exactly one warning per queued webhook event (success criterion 1).
- Always log the relative paths, not only for single-pack cases. That covers the within-pack requirement in D-08 and makes cross-release cases clearer too.
- Cap the path list (for example, the first 10 plus "(+N more)"), the same way the partial-coverage log caps at 5 (auto_delete_manager.py L163-167). A crafted model could otherwise produce a huge log line.
- **Nothing is appended for an ambiguous match.** That alone guarantees there is no `imported_file_names` entry, no `add_imported_child`, no `downloaded_file_names` commit, no badge and no timer. All of those happen only in Window 2 for returned tuples.

### Pattern 3: Delete-time duplicate guard (D-05, D-07)
Keep the path alongside each node in `run_bfs_and_coverage`'s BFS, and record paths for video leaves only:
```python
video_paths: Dict[str, List[str]] = {}         # lowercased basename -> rel paths
frontier = collections.deque((c, c.name) for c in file.get_children())
...
    child, rel_path = frontier.popleft()
    ...
    if not child.is_dir and ext in _VIDEO_EXTENSIONS:
        lower = child.name.lower()
        on_disk_videos.add(lower)
        video_paths.setdefault(lower, []).append(rel_path)
    frontier.extend((g, rel_path + "/" + g.name) for g in grandchildren)
# after the unsafe_child return, BEFORE reading imported_children:
dupes = {b: p for b, p in video_paths.items() if len(p) > 1}
if dupes:
    self.logger.warning("Auto-delete skipped for '{}': {} video basename(s) appear at more than one "
                        "path in this release ({}); per-file import coverage cannot be proven. "
                        "Local copy left in place for manual removal".format(...sanitized, capped...))
    return True, "duplicate_basename", None
```
- **Placement:** after `unsafe_child` and before `imported_children.get(...)`. This is the only placement that applies "regardless of persisted state" (D-05). Both the legacy-covered case and the grandfather case (`imported_child_bset is None`) get caught.
- **Node-limit accounting is unchanged.** Paths are carried alongside the same nodes, so there is no extra traversal.
- **Video-only scope:** see Open Question 1 and Assumption A1.

### Pattern 4: Skip-reason handling in `__execute_auto_delete`. Recommendation: TERMINAL
Today (controller.py L819-830) `bfs_limit` is the only terminal reason. It pops `imported_children[root]`, clears the re-arm counter, and returns. Every other reason goes through `_AUTO_DELETE_DEFER_REASONS` into `__defer_auto_delete`. That re-arms up to `_AUTO_DELETE_MAX_REARMS = 24` times, about 2 h at the default 300 s delay, then logs a give-up WARNING.

| Option | Consequence |
|--------|-------------|
| Retriable (like `partial_coverage`) | The condition comes from the pack's structure on disk and does not clear up while you wait. Result: 24 pointless re-fires, each re-running the BFS under `__model_lock`; 24 INFO "deferred" lines plus the guard's own 24 lines; then a misleading "given up after 24 deferrals" WARNING. Never deletes, but it's noisy. |
| **Terminal (like `bfs_limit`)** (recommended) | One clear WARNING and no re-arm. The re-arm counter is cleared. The `imported_children[root]` pop clears out the stale or poisoned legacy record. Safety does not depend on that record: the guard runs before coverage on every firing. A later webhook import can still re-arm, and the guard runs again. |

Recommendation: terminal. Implement by changing `if reason == "bfs_limit":` to `if reason in _AUTO_DELETE_TERMINAL_SKIPS:` with `_AUTO_DELETE_TERMINAL_SKIPS = frozenset({"bfs_limit", "duplicate_basename"})`, and update the `__execute_auto_delete` docstring, the `run_bfs_and_coverage` docstring, and the `_AUTO_DELETE_BFS_NODE_LIMIT` comment, which currently lists the terminal and retriable sets. Could duplicates appear only while a pack is still syncing? Possibly, but while any child is mid-lifecycle the earlier `unsafe_child` path returns first (retriable), and the BFS `break`s before the duplicate check runs. So the terminal guard only fires once the pack is fully settled. Log level: WARNING. It is terminal and needs manual action, the same as `bfs_limit`. This follows the rule "terminal skip → warning, retriable skip → info". [VERIFIED: codebase read, controller.py L682-711, L819-830; auto_delete_manager.py L119-144]

### Anti-Patterns to Avoid
- **Fixing it only on the delete side, or only on the import side.** Both are needed. The import-side fix stops new poisoned records and wrong-release credit. The delete-side guard neutralizes legacy persist and the grandfather path (D-07).
- **Lowercasing the stored path.** That would merge `Movie.mkv` and `movie.mkv` at different paths into one candidate (D-01 violation).
- **Detecting duplicates after the `on_disk_videos` set collapse.** The set loses the information. Record paths before collapsing.
- **Changing `process()`'s return shape** (for example, adding an "ambiguous" status). It would ripple into Window 2 and about 15 mocked tests for no benefit. Ambiguity is logged and dropped inside `process`.
- **Building the lookup outside `__model_lock`,** or calling `process` inside it. Keep the two-window discipline (tests at test_controller_unit.py L1155-1199 pin it).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log-injection escaping | custom replace chains | `common.sanitize_log_value` | Covers C0 + DEL + CRLF; tests already pin it (Plan 101-04) |
| Path uniqueness | separate dedup set + list | inner `dict` keyed by rel path | Dict key collapse *is* the D-02 dedup |
| Terminal-skip handling | a new branch duplicating pop/clear/return | extend the existing `bfs_limit` branch to a reason set | One code path for terminal semantics |
| Legacy persist fixture | hand-written JSON | `ControllerPersist.from_str(json.dumps({... "imported_children": {"Pack": ["movie.mkv"]}}))` or `to_str()`→`from_str()` round-trip (pattern at test_auto_delete.py L382-405) | Exercises the real loader |

## Runtime State Inventory

This is a behavior fix, not a rename, but it interacts with persisted state:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing `controller.persist` on NAS may hold legacy `imported_children[root]` entries already "fully covered" by a collapsed duplicate basename (exact count unknown) | **Code only:** the delete-time guard neutralizes them on the next Timer fire. No data migration (persist format change is out of scope). |
| Live service config | None. Sonarr/Radarr webhook config unchanged (verified: handler enqueues `basename(sourcePath)` only, web/handler/webhook.py L180-213) | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None (no package/name change) | None |

Pending in-memory Timers are not persisted; after a restart nothing is armed until a new webhook arrives.

## Common Pitfalls

### Pitfall 1: The collapse at delete time (root cause of D-05)
**What goes wrong:** `on_disk_videos` is a `set` of lowercased basenames, so `Disc1/movie.mkv` and `Disc2/movie.mkv` become one entry, and one imported child covers both.
**Confirmed:** the live probe produced `imported_children == {'Pack': ['movie.mkv']}` from a single webhook. [VERIFIED: local probe]
**Avoid:** detect duplicates from `video_paths` before relying on the set.

### Pitfall 2: Fail-before tests that fail for the wrong reason
**What goes wrong:** new `test_webhook_manager.py` tests written against the new `Dict[str, Dict[str, str]]` shape fail against old code with shape errors (`AttributeError`/wrong value types), not because of the defect. That is weak REL-01 gate-1 evidence.
**Avoid:** use **end-to-end controller tests** as the gate evidence. Build a real `Model` with `ModelFile` trees, use a real `WebhookManager(self.mock_context)` passed into `Controller(...)`, call `enqueue_import(...)`, then `Controller.process()`. These don't depend on the lookup's shape and were shown to fail on current code for the right reason. Delete-guard tests that call `__execute_auto_delete` directly also don't depend on the shape.

### Pitfall 3: Existing tests pinned to the old lookup shape
`test_controller_unit.py` L1095-1146 (three tests) assert `call_args["file.a"] == "File.A"`. All 14 tests in `test_webhook_manager.py` build `Dict[str, str]` fixtures. These must be migrated in the same commit as the implementation. Add a small helper, for example `_lookup({"file.a": {"File.A": "File.A"}})`, or a builder from `(root, path)` pairs, to keep the churn readable. Do not weaken their assertions.

### Pitfall 4: Guard scope collides with common pack layouts (product impact)
If the guard checks **all** files, packs with repeated non-video basenames would never auto-delete again, even with full, unambiguous imports. Examples: RARBG-style `Subs/<episode>/2_English.srt`, Blu-ray `Disc1/BDMV/index.bdmv` + `Disc2/BDMV/index.bdmv`. That would break IMPORT-02 ("exact behavior"). Coverage only ever looks at `_VIDEO_EXTENSIONS`, so non-video duplicates cannot create false coverage. Limiting the guard to video files closes the defect with no collateral damage. See Open Question 1.

### Pitfall 5: Unsanitized root name in an existing log line
`WebhookManager.process`'s "import detected" INFO line formats `root_name` unsanitized (webhook_manager.py L95-99). Root names come from the remote scanner. D-09 says all logged names go through `sanitize_log_value`. Fix it while editing this function. The existing exact-string test still passes because sanitizing a clean name returns it unchanged.

### Pitfall 6: Per-pack duplicates of `sample.mkv`
Packs like `E01/Sample/sample.mkv` + `E02/Sample/sample.mkv` will now hit the terminal guard. Today they already fail `partial_coverage` whenever an `imported_children` entry exists, because Sonarr never imports samples. So the only behavior that changes is the grandfather path (no per-root entry). That path is now reachable only for legacy roots, since the handler sends only `basename(sourcePath)`. This is within D-04's accepted cost: disk space, never lost media.

### Pitfall 7: "Same path twice" must not become ambiguity
Use the dict-keyed inner map so the same path collapses. If a naive implementation builds a `list`, it would count the same path twice and reject it. Test this case explicitly at both levels: a unit test (lookup containing one path) and an end-to-end test (the same name enqueued twice → one root accepted, one Timer, via the existing `accepted_roots` set).

## Code Examples

### End-to-end regression harness (verified working on current code)
```python
# Source: probe executed 2026-10-08 against main; base classes from tests/unittests/test_controller
from controller import Controller
from controller.webhook_manager import WebhookManager
from model import ModelFile
from tests.unittests.test_controller.test_auto_delete import BaseAutoDeleteTestCase

def _leaf(name, size=50):
    f = ModelFile(name, False); f.remote_size = size; f.local_size = size; return f

def _pack(name, *children):
    root = ModelFile(name, True); root.remote_size = 100; root.local_size = 100
    for c in children: root.add_child(c)
    return root

class TestAmbiguousWebhookImport(BaseAutoDeleteTestCase):
    def setUp(self):
        super().setUp()
        self.wm = WebhookManager(self.mock_context)          # real matcher
        self.controller = Controller(context=self.mock_context, persist=self.persist,
                                     webhook_manager=self.wm)
        self._make_controller_started()                       # from BaseControllerTestCase

    def test_two_releases_sharing_sample_mkv_are_untouched(self):
        m = self.controller._Controller__model
        m.add_file(_pack("Rel.A", _leaf("ep.a.mkv"), _leaf("sample.mkv")))
        m.add_file(_pack("Rel.B", _leaf("ep.b.mkv"), _leaf("sample.mkv")))
        before = self.persist.to_str()
        self.wm.enqueue_import("Sonarr", "sample.mkv")
        self.controller.process()
        self.assertEqual(before, self.persist.to_str())                 # no persist change
        self.assertEqual({}, dict(self.controller._Controller__pending_auto_deletes))
        # badge: model files keep ImportStatus.NONE; one warning naming both roots
```
Current code fails this test: it credits `Rel.B` and arms its timer.
Notes: `BaseAutoDeleteTestCase.tearDown` cancels pending Timers. Read the WebhookManager logger as `self.mock_context.logger.getChild.return_value` (the same MagicMock as the controller's logger child). Assert on `.warning.call_args_list` contents, not on the exact call count across the shared mock.

### D-07 legacy "fully covered" record cannot override the guard
```python
# In a TestAutoDeleteExecution subclass (helpers _make_child/_make_safe_mock_file exist)
legacy = ControllerPersist.from_str(json.dumps({
    "downloaded": ["Pack.S01"], "extracted": [], "stopped": [],
    "imported": ["Pack.S01"], "imported_children": {"Pack.S01": ["movie.mkv"]},
}), max_tracked_files=100)
self.controller._Controller__persist = legacy
self.controller._Controller__auto_delete_mgr._persist = legacy   # collaborator holds its own ref
d1 = self._make_child("Disc1", children=[self._make_child("movie.mkv")])
d2 = self._make_child("Disc2", children=[self._make_child("movie.mkv")])
pack = self._make_safe_mock_file(is_dir=True, children=[d1, d2])
self.controller._Controller__model.get_file = MagicMock(return_value=pack)
self.controller._Controller__execute_auto_delete("Pack.S01")
self.mock_file_op_manager.delete_local.assert_not_called()
```
**Watch out:** `AutoDeleteManager` stores its own `_persist` reference (auto_delete_manager.py L55-57). The existing rehydration test (test_auto_delete.py L382-405) swaps only `_Controller__persist`. That works there by coincidence, because both persists show partial coverage. For D-07 you must **also** swap `_Controller__auto_delete_mgr._persist`, or (simpler) seed `self.persist.add_imported_child("Pack.S01", "movie.mkv")` on the shared instance and add a separate `from_str` round-trip assertion. If you skip this, the test passes for the wrong reason (the D-14 grandfather path). The attribute is `self.__auto_delete_mgr` (controller.py L227), reachable as `_Controller__auto_delete_mgr`. Also add a grandfather variant (no `imported_children` entry) and confirm it is not deleted either. In `from_str`, `downloaded` and `extracted` are required keys. `stopped`, `imported`, `imported_children` and `absent_since` are optional (`dct.get`), and a pre-1.7.4 file is exactly this shape. [VERIFIED: controller_persist.py L137-215]

## State of the Art (in-repo history)

| Old Approach | Current Approach | When | Impact |
|--------------|------------------|------|--------|
| releaseTitle/series.title fallback names enqueued | Only `basename(sourcePath)` enqueued | pre-1.7.3 (webhook.py L153-213) | Root-level webhook matches now occur only for single-file roots; WR-01/D-14 grandfather path is mostly legacy |
| One-shot skip on retriable reasons | Bounded re-arm (`_AUTO_DELETE_MAX_REARMS = 24`) | incident 2026-09-16 | Terminal vs retriable choice now matters for log noise |
| Imports recorded with no evidence | Evidence gate (downloaded or complete local copy) | incident 2026-08-21 | Ambiguity rejection sits *before* the gate (inside `process`), so rejected names never commit to `downloaded_file_names` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The delete-time guard should cover video-extension files only (the coverage set), not every file | Pattern 3, Pitfall 4 | If the owner intends all files: RARBG `Subs/` and multi-disc BDMV packs stop auto-deleting (disk-space cost only). If video-only is wrong in some way: none found, because non-video files never contribute to coverage |
| A2 | Terminal (not retriable) is the right consequence for `duplicate_basename` | Pattern 4 | If retriable is chosen instead: same safety, about 2 h of repeated BFS and around 50 extra log lines per pack, then a give-up warning |
| A3 | Duplicate video basenames inside a settled pack do not resolve on their own over time | Pattern 4 | If they could (for example a transient extraction artifact), terminal would leave a pack that a retry would have deleted. Disk-space cost only, and a later webhook re-arms |

## Open Questions

1. **Guard scope: video files only or all files?** (product decision, needs owner confirmation)
   - What we know: D-05 says "two or more distinct file paths whose basenames are equal". Coverage only considers `.mkv/.mp4/.avi/.m4v/.mov/.ts/.wmv/.flv/.webm`.
   - Plain-terms tradeoff: "all files" also blocks auto-delete for common season packs that have a subtitle folder per episode with identically named `.srt` files, and for multi-disc Blu-ray rips. That is extra disk the user cleans up by hand, and no added safety, because those files can't fool the coverage check. "Video only" blocks exactly the packs where the defect can occur.
   - Recommendation: video only. The planner should note it as a decision the owner confirms, or treat it as already within D-05's intent ("the collapse that lets one import cover two discs").
2. **Terminal vs retriable (D-06):** research recommends terminal (Pattern 4). This is the planner's call per D-06.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| poetry venv (Python) | tests | ✓ | 3.12.12 | — |
| pytest | tests | ✓ | 9.1.1 | — |
| ruff | lint gate | ✓ (version drift) | 0.15.9 local vs 0.15.22 CI pin | `pip install ruff==0.15.22` in a scratch venv, or rely on CI `lint-python` job |
| Docker daemon | `make run-tests-python` (CI-equivalent full suite) | ✗ (daemon not running) | client 29.4.3 | Host run `poetry run pytest tests/unittests` and compare against the known host-only failure baseline (below); CI `unittests-python` is authoritative |

**Host-only baseline failures on main (pre-existing, unrelated, env-specific):** 21 failed + 3 errors in `test_ssh/test_sshcp.py` (11), `test_controller/test_extract/test_extract_process.py` (6), `test_controller/test_scan/test_scanner_process.py` (3 failed + 3 errors), `test_system/test_scanner.py` (1). Everything else passes, 1385 tests. [VERIFIED: local run, 76 s] The phase gate on the host is "no new failures compared with this exact set" plus a green CI run.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + unittest.TestCase classes; `pytest-timeout` 60 s |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (`pythonpath = ["."]`) |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_controller/test_webhook_manager.py tests/unittests/test_controller/test_auto_delete.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_controller/test_controller.py -q -p no:cacheprovider` (~1-2 s; 274 pass on main for the first four) |
| Full suite command | CI-equivalent: `make run-tests-python` (Docker, `pytest -v -p no:cacheprovider`). Host: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` (~76 s; compare against host baseline) |
| Lint gate | `cd src/python && poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/` (whole tree; `poetry -C src/python run ruff check src/python/` from repo root fails with E902 path error, so use the absolute path). CI runs `ruff check src/python/` with ruff 0.15.22 |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Fails on main? | File |
|--------|----------|-----------|----------------|------|
| IMPORT-01 | Two releases each with `sample.mkv` → no persist change (`to_str()` equal), no timer, both roots `ImportStatus` unchanged, one warning naming both roots | e2e controller | YES (verified) | test_auto_delete.py (new class) ❌ Wave 0 |
| IMPORT-01 | Roots differing only by case (`Movie.mkv` + `movie.mkv` single-file roots) → rejected | e2e controller | YES | same ❌ |
| IMPORT-01 | Root `sample.mkv` (single file) + `Rel.A/sample.mkv` → rejected | e2e controller | YES | same ❌ |
| IMPORT-01 | `Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv`, webhook `movie.mkv` → rejected; no `imported_children["Pack"]`; warning lists both relative paths | e2e controller | YES (verified) | same ❌ |
| IMPORT-01 | Delete-time: pack with duplicate video basenames + legacy `imported_children` "fully covered" → not deleted (D-07) | unit (`__execute_auto_delete`) | YES | test_auto_delete.py ❌ |
| IMPORT-01 | Delete-time: same pack, no `imported_children` entry (D-14 grandfather) → not deleted | unit | YES | test_auto_delete.py ❌ |
| IMPORT-01 | `duplicate_basename` is terminal: no re-arm, counter cleared, no "deferred" log, one WARNING | unit | YES (new behavior) | test_auto_delete_rearm.py ❌ |
| IMPORT-01 | Duplicate non-video basenames (`Subs/E01/2_English.srt` ×2) do NOT trigger the guard (if A1 confirmed) | unit | passes both (preservation) | test_auto_delete.py ❌ |
| IMPORT-01 | Ambiguous warning sanitizes CR/LF in webhook name, roots and paths | unit (WebhookManager) | n/a (new) | test_webhook_manager.py ❌ |
| IMPORT-02 | Unique child name → recorded, `imported_children` set, badge IMPORTED, timer armed exactly as before | e2e controller | passes both (preservation) | test_auto_delete.py ❌ |
| IMPORT-02 | Same name enqueued twice → one root accepted, one timer, no ambiguity warning | e2e controller | passes both (guards against list-based regressions) | test_auto_delete.py ❌ |
| IMPORT-02 | Lookup with one path → match; existing 14 WebhookManager tests migrated to new shape, assertions intact | unit | n/a (shape) | test_webhook_manager.py (migrate) |
| IMPORT-02 | Window 1 lookup contains root + nested child paths (migrated L1095-1146 tests) | unit | n/a (shape) | test_controller_unit.py (migrate) |

### Fail-before / pass-after procedure (REL-01 gate 1)
1. **RED commit:** add only the new e2e controller tests and the delete-guard tests (they don't depend on the lookup shape) to `main`'s code. Run the quick command and save the output: each targeted regression must FAIL with an assertion failure (not an ImportError or TypeError). Preservation tests must PASS.
2. **GREEN commit(s):** implement Patterns 1-4, migrate the shape-dependent tests, add the WebhookManager unit tests. Run the quick command (all pass) and the full host suite (no new failures beyond the baseline), then whole-tree ruff.
3. Record both outputs in the plan SUMMARY as the REL-01 gate-1 evidence for Phase 118.

### Sampling Rate
- **Per task commit:** quick run command plus `ruff check` on the whole tree
- **Per wave merge:** full host suite compared with the baseline
- **Phase gate:** full suite green in CI (`unittests-python` + `lint-python`) before `/bm:verify-work`

### Wave 0 Gaps
- [ ] New e2e test class with real `WebhookManager` + real `Model` trees (helpers `_leaf`/`_pack`). No shared fixture exists yet; put it in test_auto_delete.py or a new `test_import_ambiguity.py` under `tests/unittests/test_controller/` (auto-discovered)
- [ ] Legacy-persist fixture via `ControllerPersist.from_str` (or a shared-instance seed). Mind the `AutoDeleteManager._persist` reference (see the D-07 example)
- No framework install needed

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (webhook HMAC auth unchanged) | — |
| V4 Access Control | indirectly | Deletion authorization: auto-delete armed only on unambiguous evidence (this phase) |
| V5 Input Validation | yes | Webhook file name used only as a case-folded dict key; never as a filesystem path |
| V7 Error Handling & Logging | yes | `sanitize_log_value` on webhook name, provenance, root names, relative paths (D-09); cap logged list length |
| V6 Cryptography | no | — |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| Crafted/colliding webhook name arms deletion of the wrong release | Tampering / Elevation | Ambiguity rejection (Pattern 2) + delete-time guard (Pattern 3) |
| Log forging via CRLF in names/paths | Repudiation | `sanitize_log_value` on every interpolated value |
| Log flooding via huge candidate lists | DoS (minor) | Cap paths/roots shown, "+N more" suffix |

## Sources

### Primary (HIGH confidence, codebase at main @ f6548f7)
- `src/python/controller/controller.py` L25-38, L537-650, L682-867: lookup build, Window 2, defer/terminal skip handling
- `src/python/controller/webhook_manager.py`: `process` contract and log lines
- `src/python/controller/auto_delete_manager.py`: BFS, `on_disk_videos` collapse, coverage, D-14
- `src/python/model/file.py` L287-316: `full_path`, `add_child` sibling-uniqueness
- `src/python/controller/model_pipeline.py` L121-141: one-level reparenting in `_set_import_status`
- `src/python/web/handler/webhook.py` L153-213: only `basename(sourcePath)` is enqueued
- Tests: `tests/unittests/test_controller/{base.py, test_webhook_manager.py, test_controller_unit.py L1069-1199, test_auto_delete.py, test_auto_delete_rearm.py}`
- `.github/workflows/ci.yml` (ruff 0.15.22 pin; `make run-tests-python`), `src/docker/test/python/Dockerfile` L60, `src/python/pyproject.toml`
- Live probe: temporary e2e test reproduced both defects (file removed; working tree clean)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new deps; versions read from the local venv and the CI file
- Architecture: HIGH, every integration point read; the return contract was preserved deliberately
- Pitfalls: HIGH for 1-3, 5 and 7 (verified in code or by the probe); MEDIUM for 4 and 6 (real-world pack layouts are based on domain knowledge, see A1)

**Research date:** 2026-10-08
**Valid until:** 2026-11-07 (stable internal code; re-check if controller.py changes before planning)
