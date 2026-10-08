# Phase 116: Import Safety - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning

<domain>
## Phase Boundary

A Sonarr/Radarr webhook import can never be credited to the wrong release or satisfy per-child coverage for a file that was not imported, so auto-delete is only ever armed — and only ever executes — on an unambiguous basis. Unambiguous imports keep today's exact behavior. Requirements IMPORT-01, IMPORT-02. Python-only; no UI work, no on-disk persist format change, no path-mapping redesign.

</domain>

<decisions>
## Implementation Decisions

### Import-side ambiguity rejection (Controller.__check_webhook_imports / WebhookManager.process)
- **D-01:** The lookup key is the lowercased basename; the lookup VALUE is the set of complete, case-preserving model paths (root + relative path) that carry that basename. Lowercase only the key — never the stored path — so case-distinct files at different paths remain distinct candidates (owner note).
- **D-02:** A webhook name resolving to exactly ONE distinct path proceeds exactly as today (record, badge, evidence gate, arm auto-delete). Repeated references to the same complete path are deduplicated and are not ambiguous.
- **D-03:** A webhook name resolving to TWO OR MORE distinct paths is ambiguous and rejected — whether the paths are in different releases, roots differing only by case, a root name equal to a child basename elsewhere, or repeated basenames inside one release (`Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv`). Rejection = no `imported_file_names` entry, no `add_imported_child`, no `downloaded_file_names` commit, no import badge, no auto-delete timer.
- **D-04:** Accepted consequence (owner-confirmed): a pack containing distinct files with the same basename can never be fully covered and is never auto-deleted; it stays on disk for manual removal. Cost is disk space, never lost media.

### Delete-time duplicate-basename guard (AutoDeleteManager.run_bfs_and_coverage)
- **D-05:** Add a guard at deletion time: if a root's BFS finds two or more distinct file paths whose basenames are equal case-insensitively, auto-delete is skipped (pack left untouched) with a log line explaining why. This applies regardless of persisted state — including legacy (pre-1.7.4) `imported_children` records that would otherwise read as "fully covered", and the D-14 grandfather path (no per-root entry).
- **D-06:** The guard's skip is retriable/non-terminal in the same way as the existing `partial_coverage` skip unless research finds the deferral/re-arm budget makes a terminal reason more appropriate — planner's call, but it must never delete.
- **D-07:** Mandatory regression test: a legacy persist where `imported_children[root]` already contains the duplicated basename (i.e. "fully covered") must NOT override the guard — the pack is not deleted.

### Logging (no UI)
- **D-08:** Log warning only — no UI badge/notification in this patch. The import-rejection warning includes: the webhook filename, the candidate releases (roots), and an explicit statement that no import credit or automatic cleanup was authorized. For duplicates within one pack, include the distinct relative paths so the ambiguity is visible.
- **D-09:** All logged names/paths go through `sanitize_log_value` (CWE-117), matching existing import logging.

### Claude's Discretion
- Exact data structure for the multi-path lookup and where dedup happens (controller vs WebhookManager), provided `WebhookManager.process` keeps returning only unambiguous matches.
- Log wording and level beyond the content required by D-08; the delete-time skip may log at info like other skip reasons or warning — pick consistently.

</decisions>

<specifics>
## Specific Ideas

- Owner-specified regression cases (from spec + discussion): two releases each containing `sample.mkv`; roots differing only by case; root name equal to a child basename elsewhere; `Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv` webhook `movie.mkv` (rejected, coverage unsatisfied for both); unique name imports and arms exactly as before; same path referenced twice = one match; legacy "fully covered" `imported_children` cannot override the delete-time guard.
- Each targeted regression must be shown to FAIL against the pre-fix code and PASS after (REL-01 gate 1).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone design
- `docs/superpowers/specs/2026-10-08-safety-patch-design.md` — approved design spec (Phase A section); authoritative fix contract and regression list
- `.planning/REQUIREMENTS.md` — IMPORT-01, IMPORT-02, REL-01
- `.planning/ROADMAP.md` §"Phase 116: Import Safety" — goal, success criteria, owner planning notes

### Code under change
- `src/python/controller/controller.py` — `__check_webhook_imports` (name_to_root build ~L554-574; evidence gate + persist writes + auto-delete scheduling ~L576-640)
- `src/python/controller/webhook_manager.py` — `WebhookManager.process` (lookup + log)
- `src/python/controller/auto_delete_manager.py` — `run_bfs_and_coverage` (on_disk_videos basename set; coverage guard; D-14 grandfather)
- `src/python/controller/controller_persist.py` — `imported_children` / `add_imported_child`

### Existing tests to extend
- `src/python/tests/unittests/test_controller/test_webhook_manager.py`
- `src/python/tests/unittests/test_controller/test_controller.py` / `test_controller_unit.py`
- `src/python/tests/unittests/test_controller/test_auto_delete.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sanitize_log_value` — required for every logged webhook/remote-sourced name.
- BFS traversal pattern in `__check_webhook_imports` and `run_bfs_and_coverage` (bounded by `_AUTO_DELETE_BFS_NODE_LIMIT` at delete time).

### Established Patterns
- `name_to_root` is built under `__model_lock` (Window 1) and consumed outside it; keep the two-window locking discipline.
- Auto-delete skips return `(skip, reason, on_disk_videos)`; `partial_coverage`/`unsafe_child` are retriable, `bfs_limit` terminal (caller pops `imported_children`).
- `on_disk_videos` is currently a set of lowercased basenames — the collapse that lets one import cover two discs; the delete-time guard must detect duplicates BEFORE that collapse.
- WR-01: root-level matches don't record a child; D-14: no per-root entry ⇒ grandfathered as fully imported.

### Integration Points
- `Controller.__check_webhook_imports` → `WebhookManager.process(name_to_root)` → returns `(root_name, matched_name)` list.
- `Controller.__execute_auto_delete` → `AutoDeleteManager.run_bfs_and_coverage` skip reasons → deferral/re-arm budget.

</code_context>

<deferred>
## Deferred Ideas

- UI surfacing of rejected ambiguous imports (badge/notification) — new capability, future phase.
- Path-aware import matching (map webhook source paths to model paths) so duplicate-name packs could be safely covered — out of scope (path-mapping redesign).
- Backlog 999.1 (accept import whose payload size equals remote size) — stays parked.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` — keyword-only match on "import"; unrelated (upstream webob dependency).

</deferred>

---

*Phase: 116-import-safety*
*Context gathered: 2026-10-08*
