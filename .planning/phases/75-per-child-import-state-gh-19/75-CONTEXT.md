# Phase 75: Per-Child Import State (GH #19) - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Data-loss bug fix. Extend auto-delete's Timer-fire guard so that a pack root
is skipped whenever any on-disk video child is absent from a per-root imported
set. Webhook processing, `ControllerPersist`, and `__execute_auto_delete` all
grow per-(root, child) awareness; the state-guard and pack-guard added by PR #18
remain and run first. No UI, no new user-facing features.

GH #19 is the canonical spec for the problem. FIX-02 is the milestone requirement.

</domain>

<decisions>
## Implementation Decisions

### Data Shape & Persistence

- **D-01:** Per-child state lives in `ControllerPersist` as
  `imported_children: Dict[str, BoundedOrderedSet[str]]` — keys are root model
  file names, values are bounded sets of imported child basenames. Per-root
  eviction prevents one noisy multi-season release from evicting another pack's
  still-needed entries.
- **D-02:** Two bounds apply: a per-root `maxlen` on the `BoundedOrderedSet` of
  children (planner to propose a number — 500 is a reasonable starting point),
  and a global cap on the number of root keys tracked (reuse
  `DEFAULT_MAX_TRACKED_FILES = 10000`, evicting the oldest root when exceeded).
- **D-03:** JSON serialization adds a new top-level key (e.g.
  `"imported_children"`) alongside `imported`. Read path is backward-compatible:
  missing key → empty dict. Matches `ControllerPersist.from_str` conventions
  already used for `stopped_file_names` and `imported_file_names`.
- **D-04:** On successful `__execute_auto_delete` (delete actually dispatched),
  the root's entry is removed from `imported_children`. Keeps persist small,
  avoids stale data, and makes restart semantics obvious.
- **D-05:** `imported_file_names.add(root)` is preserved exactly as-is per
  GH #19's backward-compat requirement. It still drives `_set_import_status`
  and the UI badge.

### Webhook Matching & Child Capture

- **D-06:** `WebhookManager.process(name_to_root)` return type changes to emit
  both the root name and the matched child name — e.g.
  `List[Tuple[str, str]]` of `(root, matched_name)`. When the match key IS the
  root, `matched_name == root`.
- **D-07:** In `__check_webhook_imports`, for each `(root, child)` returned:
  add `root` to `imported_file_names` (unchanged) AND add `child` to
  `imported_children[root]`. Both mutations happen inside the existing
  Window-2 `__model_lock` scope — no new lock.

### Coverage Check at Timer-Fire

- **D-08:** `__execute_auto_delete` gains a third skip condition that runs
  AFTER the state-guard and pack-guard already landed by PR #18:
  1. For directory roots: BFS every descendant; collect the set of basenames
     whose extension is in a video allowlist (see D-09).
  2. Compare against `imported_children[root]` (empty set if key missing).
  3. If any allowlisted basename is missing → log INFO and return without
     deleting.
- **D-09:** Video allowlist is a module-level `frozenset` constant in
  `controller.py` near `__execute_auto_delete`. Initial membership:
  `{'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.ts', '.wmv', '.flv', '.webm'}`.
  Comparison is case-insensitive on the extension. Planner may revise the
  exact set — but the decision is "video-only allowlist, hardcoded, no config
  surface."
- **D-10:** Files NOT in the allowlist (`.nfo`, `.srt`, `.sub`, `.idx`, `.ass`,
  `.txt`, sample files, etc.) are IGNORED for coverage. Sonarr intentionally
  skips these, so requiring them would permanently strand real-world packs.
- **D-11:** Single-file roots (non-directory) continue to key on the root
  name itself — `imported_file_names.add(root)` is sufficient, no per-child
  logic needed. The coverage check only engages when `file.is_dir`.

### Safety Timeout & Rearm

- **D-12:** No safety timeout. If coverage stays partial, the pack is
  NEVER auto-deleted by the Timer. User must manually delete or fix the
  Sonarr import. Matches FIX-02's "err fully on the side of not losing data"
  intent. Simpler code, explicit contract.
- **D-13:** Rearm behavior is unchanged from today: only a new webhook
  calling `__schedule_auto_delete(root)` resets the Timer. No per-cycle
  recheck, no restart-time rearm. The persisted `imported_children` survives
  restart so next webhook's scheduling operates on the restored state.

### Legacy Persist Migration

- **D-14:** Roots present in `imported_file_names` but absent from
  `imported_children` (either because they were recorded pre-upgrade OR
  because the user's persist file has never seen this phase's code) are
  **grandfathered as fully imported**. The coverage check returns "all
  present" when the per-root entry is missing. Preserves today's cleanup
  behavior on already-tracked roots. Known tradeoff: the original GH #19
  bug can replay ONCE for packs that were mid-import at upgrade. Acceptable
  per GH #19's stated default.
- **D-15:** No purge, no migration script, no schema version bump. Fresh
  key defaults to `{}` on first load after upgrade.

### Diagnostic Surface

- **D-16:** Skip logs are INFO level, one line per skipped Timer-fire.
  Format along the lines of `Auto-delete skipped for 'ROOT': partial import
  (N of M on-disk video children imported; missing: [child1, child2, ...])`.
  Missing list truncated to first 5 + `(+K more)` suffix when larger.
- **D-17:** No WARNING escalation, no log dedup by coverage signature, no
  new counter or metric. Matches the existing PR #18 skip-log pattern exactly.
- **D-18:** No UI changes. `import_status` is not extended with a PARTIAL
  flag. Surfacing partial-import state in the UI is explicitly deferred
  (see Deferred Ideas).

### Testing

- **D-19:** Unit tests cover (per phase success criteria #4):
  - single-file root where root-name imported → delete proceeds;
  - multi-episode directory where all video children imported → delete proceeds;
  - multi-episode directory where one video child is missing from
    `imported_children[root]` → skip + log;
  - directory with allowlisted videos plus non-allowlisted files (`.nfo`,
    sample) where only videos are covered → delete proceeds;
  - legacy grandfather: root in `imported_file_names`, no key in
    `imported_children`, directory on disk → delete proceeds (documented
    behavior);
  - post-delete: `imported_children[root]` is gone after a successful
    Timer-fire.
- **D-20:** Restart rehydration test: load a persist file containing
  `imported_children` with partial coverage, confirm Timer-fire still skips
  post-restart. Covers phase success criteria #4's "post-restart rehydration."

### Claude's Discretion

- Exact per-root `maxlen` value for the `BoundedOrderedSet[str]` (D-02).
  Default 500 unless planner finds a reason to diverge.
- Exact extension list in the video allowlist (D-09). Video-only, hardcoded
  in `controller.py`; planner picks the concrete membership.
- Naming of the new persist key (`imported_children` vs `imported_child_names`
  vs similar). Match existing style.
- Log-line phrasing and truncation threshold (D-16). Planner to pattern-match
  the existing PR #18 skip logs.
- Whether `WebhookManager.process` returns `List[Tuple[str, str]]` or a
  dataclass — equivalent semantically (D-06).

### Folded Todos

_None — no pending todos in the project inbox match this phase's scope._

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### GitHub issue and prior fix
- `https://github.com/thejuran/seedsyncarr/issues/19` — GH #19: canonical spec
  for the Sonarr silent-reject bug, proposed approach, edge cases,
  acceptance criteria. **Authoritative for this phase.**
- `.planning/debug/resolved/seedsyncarr-predelete.md` — full debug investigation
  that produced PR #18 and filed GH #19. Explains WHY the state-guard and
  pack-guard are insufficient for the silent-reject case.
- `src/python/controller/controller.py` §`__execute_auto_delete`
  (lines 777-860) — the function being extended. State-guard and pack-guard
  already in place from PR #18 — keep both, add partial-coverage guard after.
- `src/python/controller/controller.py` §`__check_webhook_imports`
  (lines 708-758) — webhook processing + name_to_root build + auto-delete
  scheduling. Add per-child persist mutation in Window 2.
- `src/python/controller/controller.py` §`__schedule_auto_delete`
  (lines 760-775) — Timer rearm on repeat webhook. Unchanged.

### Persist and webhook infrastructure
- `src/python/controller/webhook_manager.py` — `WebhookManager.process()`
  signature extends to return (root, matched_name) tuples.
- `src/python/controller/controller_persist.py` — add `imported_children`
  field, update `from_str` / `to_str`, preserve backward-compat on load.
- `src/python/common/bounded_ordered_set.py` — the `BoundedOrderedSet[T]`
  generic reused per-root. Existing `DEFAULT_MAXLEN = 10000` stays as the
  global root-key cap.
- `src/python/web/handler/webhook.py` §`_extract_sonarr_title` (lines 131-161)
  — upstream title extraction. No changes; the basename of
  `episodeFile.sourcePath` is what feeds `name_to_root` lookup.

### Related requirement docs
- `.planning/REQUIREMENTS.md` §FIX-02 — the milestone requirement this phase
  satisfies.
- `.planning/ROADMAP.md` §"Phase 75: Per-Child Import State (GH #19)" — goal,
  dependencies, success criteria.

### Existing test module to extend
- `src/python/tests/unittests/test_controller/test_auto_delete.py` — all new
  unit tests land here alongside the 28 existing cases from PR #18. The
  `safe-state mock helper` introduced in PR #18 should be reused; extend
  it where needed for per-child scenarios.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `common.BoundedOrderedSet[T]` — already generic; instantiate as
  `BoundedOrderedSet[str]` per root with a configurable `maxlen`.
- `ControllerPersist` JSON round-trip pattern — adding a new key follows the
  same shape used for `stopped_file_names` and `imported_file_names`
  (backward-compat via `dct.get(KEY, default)`).
- BFS-over-`get_children()` helper pattern — already used in TWO places:
  `__check_webhook_imports` (name_to_root build) and the PR #18 pack guard in
  `__execute_auto_delete`. Extend the pack-guard BFS to also collect video
  basenames for the coverage check — one traversal.
- `__model_lock` two-window pattern — Window 1 reads, Window 2 mutates. New
  per-child writes go in Window 2 under the same lock.
- `self.logger.info(...)` skip-log pattern — PR #18 established the exact
  phrasing template. Follow it.

### Established Patterns
- Model reads under `__model_lock`; subprocess dispatch (e.g. `delete_local`)
  OUTSIDE the lock. Do not widen the lock across any new work.
- `ModelFile` is frozen/immutable after add — safe to use a captured
  reference after lock release.
- Persist serialization is case-sensitive on keys; matching on file names
  is case-INSENSITIVE via `.lower()` keys in `name_to_root`. Per-child
  matching follows the same convention: store basenames as-received from
  the webhook (already lowercased at lookup time).
- `enumerate on-disk via BFS`: the children iteration MUST come from
  `ModelFile.get_children()` (model, not filesystem) — consistent with
  `__check_webhook_imports` line 736.

### Integration Points
- Webhook flow: `WebhookHandler._extract_sonarr_title` → Queue →
  `WebhookManager.process` → `__check_webhook_imports` → persist mutation
  + `__schedule_auto_delete` → Timer → `__execute_auto_delete`. All per-child
  work threads through this same chain.
- Persist is loaded once at controller init and saved whenever mutated
  through the existing save path — no new save-hook needed.
- Tests live in `tests/unittests/test_controller/test_auto_delete.py` and
  `tests/unittests/test_controller/test_controller_persist.py`. Persist
  round-trip tests extend the latter.

</code_context>

<specifics>
## Specific Ideas

- Log line phrasing mirrors the PR #18 skip lines:
  - State-guard (existing): `Auto-delete skipped for 'X': file is in state Y`
  - Pack-guard (existing):  `Auto-delete skipped for 'X': child 'Y' is in state Z`
  - Coverage-guard (NEW):   `Auto-delete skipped for 'X': partial import
    (N of M on-disk video children imported; missing: [...])`
- The victim releases from the resolved debug doc
  (`Big.Train.S02.WEB-DL.DDP2.0.H.264-squalor`,
  `Hearts.and.Bones.S01`, `The.Long.Shadow.S01`,
  `Jaaaaam.S01.PAL.DVDRip.AAC2.0.x264-kingqueen`) are real-world test
  inputs the planner may consider when constructing fixture pack
  structures.

</specifics>

<deferred>
## Deferred Ideas

- **UI badge for partial-import state.** Extending `import_status` with a
  `PARTIAL_IMPORT` flag and surfacing it in the Angular UI is net-new
  user-facing feature work. v1.1.1 is explicitly scoped as "no net-new
  features." Candidate for a future milestone if operators want visibility
  into stalled packs.
- **Config-driven video extension list.** Hardcoded allowlist is fine for
  v1.1.1. If users start hitting obscure formats, open an issue and promote
  to a config surface in a later phase.
- **Safety timeout / fall-through for partial coverage.** Explicitly
  rejected for this phase (D-12). If real-world usage shows legitimate
  never-completing imports causing disk-fill problems, revisit with data.
- **Observability (counter / metric for blocked-delete-count).** Would be
  useful for operators diagnosing stuck packs, but out of scope per D-17.
  Could land in a later test-infra or observability phase.
- **Clear on-model-drop.** Option 3 from the Data-shape question (clear
  per-child entries when root is removed from model, e.g., on user-invoked
  DELETE_LOCAL). Not captured in D-04's clear-on-Timer-success path. If
  persist growth becomes an issue, add this hook into
  `__handle_delete_command`.

### Reviewed Todos (not folded)

_None — no pending todos were reviewed for this phase._

</deferred>

---

*Phase: 75-per-child-import-state-gh-19*
*Context gathered: 2026-04-20*
