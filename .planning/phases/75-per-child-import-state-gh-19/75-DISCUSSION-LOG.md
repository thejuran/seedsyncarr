# Phase 75: Per-Child Import State (GH #19) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 75-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 75 — Per-Child Import State (GH #19)
**Areas discussed:** Data shape, Coverage scope, Safety timeout, Legacy migration, Diagnostic surface

---

## Data shape

### Q1: How should per-child import state be structured in ControllerPersist?

| Option | Description | Selected |
|--------|-------------|----------|
| Dict[root → BoundedOrderedSet[child]] | Per-root bounded set; eviction is scoped to the root. A noisy multi-season release cannot evict another pack's children. JSON: `{"imported_children": {"RootA": ["ep1.mkv", ...]}}`. Requires per-root maxlen and a separate global cap on number of roots tracked. | ✓ |
| Flat BoundedOrderedSet[Tuple[root, child]] | One global LRU across all (root, child) pairs. Matches existing BoundedOrderedSet usage exactly. One noisy pack can evict another's entries. | |
| Dict[root → Set[child]] + global cap on pairs | Plain sets per root with a global pair-count guard enforced at add-time. More code, no clear win. | |

**User's choice:** Dict[root → BoundedOrderedSet[child]]
**Notes:** Per-root eviction wins on correctness — no cross-pack interference.

### Q2: When a root's pack is fully deleted, should its per-child entries be cleared?

| Option | Description | Selected |
|--------|-------------|----------|
| Clear on successful delete | After `__execute_auto_delete` proceeds, drop the per-root entry. Keeps persist small, avoids re-checking dead roots on restart. | ✓ |
| Keep entries; rely on bounded eviction | Never clear explicitly — let the bounded set evict over time. | |
| Clear on delete AND on model drop | Also clear when the root disappears from the model. Most correct, a bit more wiring. | |

**User's choice:** Clear on successful delete
**Notes:** Option 3's model-drop clear noted as a Deferred Idea — can be added later if persist growth proves a problem.

---

## Coverage scope

### Q3: Which on-disk children must appear in the imported set before auto-delete proceeds?

| Option | Description | Selected |
|--------|-------------|----------|
| Video-ext allowlist | Only video extensions count toward coverage. Sidecars (.nfo, .srt, .sub, .idx, .ass, .txt), samples, and non-video junk are ignored. Pragmatic — Sonarr intentionally ignores these too. | ✓ |
| Strict — every on-disk file | Every file under the root must be imported. Safest-by-default but would strand real-world releases forever. | |
| Media-ext allowlist + music/audio | Video allowlist plus audio. Lidarr is Out of Scope per PROJECT.md. | |
| Strict + configurable ignore patterns | Default strict with config overrides. PROJECT.md values minimal config. | |

**User's choice:** Video-ext allowlist
**Notes:** Matches Sonarr's actual import behavior; avoids the permanent-block failure mode.

### Q4: Where does the exclusion logic live?

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level constant in controller.py | `VIDEO_EXTENSIONS = frozenset({...})` near `__execute_auto_delete`. Simple, testable, no new files. | ✓ |
| New helper in common/ | `common/media_extensions.py` with `is_video(path)`. YAGNI — one call site. | |
| Config-driven | Read from `[AutoDelete]` section. Most flexibility, adds config surface. | |

**User's choice:** Module-level constant in controller.py
**Notes:** Minimal-abstraction style preferred. Config surface deferred.

---

## Safety timeout

### Q5: When coverage stays partial for a long time, should auto-delete eventually fall through?

| Option | Description | Selected |
|--------|-------------|----------|
| Block forever — no timeout | If any on-disk video is missing from the imported set, skip+log every Timer-fire. Never auto-delete. User must intervene. | ✓ |
| Safety timeout (e.g. 24h) | After N hours of partial coverage, log WARNING and proceed. Reintroduces the exact failure mode this phase exists to prevent. | |
| Timer reschedules instead of firing | Reschedule Timer on partial coverage. More code, unclear win. | |

**User's choice:** Block forever — no timeout
**Notes:** Err fully on the side of not losing data, per FIX-02's stated intent.

### Q6: If auto-delete is skipped, does the Timer get re-armed by any signal?

| Option | Description | Selected |
|--------|-------------|----------|
| Only by a new webhook | Matches today's behavior — `__schedule_auto_delete(root)` cancels-and-rearms. No new mechanism. | ✓ |
| Rearm on every controller cycle | Re-check on every `process()` iteration for roots with partial coverage. | |
| One-shot rearm on restart | At startup, rebuild Timers for roots with persisted imported-children. | |

**User's choice:** Only by a new webhook
**Notes:** Simplest and most predictable. If Sonarr never retries, pack sits until user intervention — acceptable.

---

## Legacy migration

### Q7: How should pre-existing imported_file_names entries behave post-upgrade?

| Option | Description | Selected |
|--------|-------------|----------|
| Grandfather as fully-imported | Root in imported_file_names but absent from per-child dict → treat as fully imported. Preserves today's delete behavior on already-tracked roots. | ✓ |
| Force re-verification | Missing entries treated as partial-coverage — block until re-import. Risks stalling cleanup on restart. | |
| One-time purge on upgrade | Clear imported_file_names on first startup. Loses legitimate imported state. | |
| Grandfather only if root gone from disk | Most correct, most code. | |

**User's choice:** Grandfather as fully-imported
**Notes:** GH #19's stated default. Known tradeoff: the bug can replay once for packs mid-import at upgrade. Acceptable.

---

## Diagnostic surface

### Q8: When auto-delete is skipped due to partial child coverage, how loud should the log be?

| Option | Description | Selected |
|--------|-------------|----------|
| INFO level, single line per skip | Matches the existing PR #18 skip-log pattern. One line per skipped Timer-fire, missing list truncated to first 5 + count. | ✓ |
| WARNING level | Flags ops attention but produces log spam on every webhook rearm. | |
| INFO once per (root, coverage-signature), then DEBUG | Quieter for stalled packs, more code. | |

**User's choice:** INFO level, single line per skip
**Notes:** Consistency with PR #18's state-guard and pack-guard skip logs.

### Q9: Should the UI expose partial-import state to the user?

| Option | Description | Selected |
|--------|-------------|----------|
| No UI change this phase | Logs only. Keep this phase narrowly scoped to the data-loss fix. | ✓ |
| Add partial-import flag to import_status | Extend `_set_import_status` with PARTIAL_IMPORT. User-facing feature — violates milestone scope. | |
| Expose via controller status / metric | Counter for blocked-delete-count. No UI work, pure observability. Not required by FIX-02. | |

**User's choice:** No UI change this phase
**Notes:** v1.1.1 is explicitly "no net-new features" per PROJECT.md. UI badge noted as deferred idea.

---

## Claude's Discretion

- Exact per-root `maxlen` value for `BoundedOrderedSet[str]` (planner to propose).
- Exact membership of the video-extension allowlist.
- Naming of the new persist key (`imported_children` vs `imported_child_names` etc.).
- Exact phrasing and truncation threshold of the coverage-skip log line.
- Whether `WebhookManager.process` returns `List[Tuple[str, str]]` or a small dataclass.

## Deferred Ideas

- UI badge for partial-import state (feature work, wrong milestone).
- Config-driven video extension list (hardcoded is fine for v1.1.1).
- Safety timeout / fall-through for partial coverage (rejected this phase).
- Observability counter / metric for blocked-delete-count (out of scope).
- Clear per-child entries on model drop / user-invoked DELETE_LOCAL (nice-to-have).
