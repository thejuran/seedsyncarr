# Phase 74: Storage capacity tiles - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Add disk-capacity awareness to the **Remote Storage** and **Local Storage** dashboard tiles. When capacity data is available the tile shows percentage used + total + used breakdown + capacity-driven progress bar; when unavailable it falls back to the existing tracked-bytes display. Backend introduces a `StorageStatus` component on the existing `Status` model, fed by `shutil.disk_usage()` (local) and `df -B1 <remote_path>` over the existing SSH session (remote), and piggybacked onto the existing SSE status stream.

**Out of scope:** Download Speed and Active Tasks tiles (no changes); new SSE event types or endpoints; Lidarr/Readarr support; capacity history / trends / sparklines; multi-mount enumeration; user-configurable thresholds; new E2E coverage (SSH unfakeable in E2E); per-file capacity attribution; alert/notification on threshold breach beyond the in-tile color shift.

</domain>

<decisions>
## Implementation Decisions

### Tile layout & slots
- **D-01:** Capacity-mode main row uses **`stat-value = '65%'`** + **`stat-unit = 'of 1.86 TB'`** — percentage is the headline, total contextualizes. The "used" detail moves to a new sub-line.
- **D-02:** "Used" detail renders as a **new sub-line below the progress bar** — same visual slot pattern as Download Speed's `Peak: …` and Active Tasks' badges.
- **D-03:** Progress bar fill in capacity mode = **`used / total * 100`** (matches design spec; replaces the current "remote vs local tracked share" semantic for these two tiles when capacity is present).
- **D-04:** Tile **header is unchanged** — keep `fa-cloud` / `fa-database` watermarks + amber stat-icon + "Remote Storage" / "Local Storage" labels. Mode change is silent.

### Number formatting
- **D-05:** Percentage precision = **integer only** (`'65%'`, not `'65.3%'`). Matches design spec example. No adaptive precision in the high-fill range.
- **D-06:** Total in `stat-unit` slot = **existing `FileSizePipe` with 2 decimals** (e.g., `'of 1.86 TB'`). No new format pipeline; auto-scales unit (B/KB/MB/GB/TB).
- **D-07:** "Used" sub-line = **`fileSize:2 + literal 'used'`** (e.g., `'120.50 GB used'`). Same precision as the total so the two figures align visually.
- **D-08:** **No new bytes-vs-bibytes convention.** Backend ships raw bytes from `df -B1` / `shutil.disk_usage`; the existing `FileSizePipe` formats them. Whatever base the pipe currently uses is what these tiles use.

### Threshold warnings
- **D-09:** Progress bar **color shifts at capacity thresholds**. Bar fill stays in the tile's normal color when usage is low; switches to **warning** at **≥80%**, switches to **danger** at **≥95%**. Number text stays neutral; only the bar's fill color reacts.
- **D-10:** **Reuse existing semantic tokens** (Bootstrap `warning` / `danger` variants — same family as the `badge-failed` styling already used on file rows). **No new design tokens** for this phase.
- **D-11:** Threshold transitions are pure SCSS / template binding (e.g., `[class.stat-progress-fill--warning]="pct >= 80 && pct < 95"`). No theme-token additions, no new SCSS variables.

### Refresh & failure UX
- **D-12:** Remote `df` runs **once per remote scan cycle**, piggybacked on the existing SSH session that the scan already establishes. No separate timer. No throttling beyond the spec's >1% change check before re-pushing on the SSE stream.
- **D-13:** Local `shutil.disk_usage()` runs **on local scan cycle** (inline, near-instant). Same >1% gate before notifying.
- **D-14:** **Cold-load behavior:** tiles render in the **existing tracked-bytes fallback** until the SSE stream delivers a non-null `(total, used)` pair, then flip to capacity mode. No skeleton, no `'0%'` placeholder, no `'—'` / `'N/A'` text.
- **D-15:** **Per-tile independent fallback** — Remote tile and Local tile each evaluate their own `(total, used)` pair. If `remote_total` is null the Remote tile falls back to tracked-bytes while the Local tile happily shows capacity, and vice versa. No "both-or-nothing" coupling.
- **D-16:** **`df` parse failures = silent fallback + `WARN`-level log.** If the `df -B1` output doesn't match the expected format, leave `remote_total` / `remote_used` as `None` and log the parse error at WARN. Mirrors the silent-fallback pattern Phase 73 established for invalid URL params. No retry, no error toast, no `error_msg` plumbing.

### Claude's Discretion
- Exact regex / string-split strategy used to parse `df -B1` output.
- Exact selector/CSS-class names used to switch between fallback and capacity templates inside `stats-strip.component.html` (`@if (stats.remoteCapacityTotal !== null) { … }` is the obvious shape but the planner can refine).
- Whether the threshold computation lives in the template (`pct >= 80`) or in a derived `DashboardStats` field (`remoteCapacityState: 'normal' | 'warn' | 'danger'`).
- Where the `>1%` change check lives (controller before assigning the `StorageStatus` properties, vs inside the property setter). Either is spec-compliant; pick whichever has the lighter test surface.
- Whether the SCSS warning/danger fill classes are added to the existing `stat-progress-fill` rule set or scoped to a new modifier (e.g., `.stat-progress-fill--capacity`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design contract — port exactly, don't redesign
- `docs/superpowers/specs/2026-04-15-storage-capacity-tiles-design.md` — Architecture (Approach A, dedicated `StorageStatus` component), data sources (`shutil.disk_usage` / `df -B1`), SSE piggyback delivery, >1% change-gate, fallback rule, security note. Every backend / serialization / frontend-interface change in this phase derives from this doc.

### Adjacent prior-phase context
- `.planning/phases/73-dashboard-filter-for-every-torrent-status/73-CONTEXT.md` — Phase 73 introduced the URL-param silent-fallback pattern. Phase 74 reuses the same "silent fallback + don't shout" instinct for `df` parse failures.

### Backend code artifacts to modify
- `src/python/common/status.py` — Add `StorageStatus` inner class to `Status` (mirroring `ServerStatus` / `ControllerStatus` pattern at lines 105–125); register `storage = BaseStatus._create_property("storage")` and initialize via `__create_component(Status.StorageStatus)` at lines 130–140.
- `src/python/web/serialize/serialize_status.py` — Extend `SerializeStatusJson.status()` to emit the `storage` block (`local_total`, `local_used`, `remote_total`, `remote_used`, all nullable).
- Controller scan path (`src/python/controller/scan_manager.py` and the remote scanner it owns at `local_path_to_scan_script` / `remote_path_to_scan_script` — see `scan_manager.py:42–52`) — wire local `shutil.disk_usage(config.lftp.local_path)` after each local scan, and `df -B1 <config.lftp.remote_path>` via `Sshcp.shell()` after each remote scan (same SSH instance the scan uses; see `delete_process.py:37,47` for the `Sshcp(host=…).shell("…")` call shape).

### Frontend code artifacts to modify
- `src/angular/src/app/services/server/server-status.ts` — Extend `IServerStatus` and `ServerStatusJson` with a `storage` block (camelCase on the interface, snake_case on the JSON DTO); wire snake→camel mapping in `fromJson`. Defaults all four fields to `null`.
- `src/angular/src/app/services/files/dashboard-stats.service.ts` — Add `remoteCapacityTotal`, `remoteCapacityUsed`, `localCapacityTotal`, `localCapacityUsed` (each `number | null`) to `DashboardStats` and `ZERO_STATS`. Inject `ServerStatusService`; merge with `ViewFileService.files` via `combineLatest` so capacity flows from the status stream while counts/speeds keep flowing from the file list.
- `src/angular/src/app/pages/files/stats-strip.component.html` — Wrap the Remote and Local card bodies in an `@if (stats.remoteCapacityTotal !== null)` / `@if (stats.localCapacityTotal !== null)` switch: capacity branch renders the `'65%'` / `'of 1.86 TB'` / `'120.50 GB used'` shape per D-01..D-07; else branch keeps today's tracked-bytes markup verbatim. No changes to Download Speed or Active Tasks cards.
- `src/angular/src/app/pages/files/stats-strip.component.scss` — Add capacity-mode progress-fill modifiers that map to existing semantic Bootstrap `warning` / `danger` colors per D-10/D-11. No new design tokens.

### Existing patterns to mirror (don't reinvent)
- `src/python/common/status.py:105–125` — `ServerStatus` / `ControllerStatus` are the templates for `StorageStatus` (declare properties via `StatusComponent._create_property`, initialize to `None` in `__init__`).
- `src/python/controller/delete/delete_process.py:32–47` — Canonical `Sshcp(host=…, …).shell(cmd)` invocation shape, including `shlex.quote` for any user-controlled path. The remote-path passed to `df` comes from config (`config.lftp.remote_path`) so quoting still applies.
- `src/angular/src/app/pages/files/stats-strip.component.html:14–20` — Existing `stat-progress-track` / `stat-progress-fill` markup pattern; capacity mode keeps the same wrapper, only the `[style.width.%]` formula and conditional class change.

### Tests
- Backend: `StorageStatus` setter / listener notification, `SerializeStatusJson.status()` with and without storage values, `df -B1` output parser (happy path, malformed output, empty output), controller scan integration verifying capacity is collected without breaking the existing scan flow.
- Frontend: `ServerStatus.fromJson` storage parsing + null defaults; `DashboardStatsService` `combineLatest` merging (file list change without status change preserves capacity, status change without file change preserves counts); `StatsStripComponent` capacity-mode rendering, fallback-mode rendering, threshold-color application at 79/80/94/95 boundaries, independent per-tile fallback.
- **No new E2E.** SSH `df` cannot be faked in the E2E harness; the existing dashboard E2E coverage from Phase 72/73 must continue to pass with the additional null-default capacity fields in the status JSON.

### Project-level rules
- `.planning/PROJECT.md` — Dark-only Deep Moss + Amber palette, no SVG icons, system fonts, Bootstrap-class-driven styling, "no functional regressions". Threshold-color choice (D-09/D-10) honors these by reusing semantic Bootstrap variant tokens already used elsewhere in the dashboard.
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md` — "Port AIDesigner HTML identically, no approximations." For Phase 74 this means: the spec's percentage / used / total layout (spec §"Frontend — Tile Display") and the spec's data-shape decisions (spec §"Backend — Data Model" / "Backend — Serialization") are ported exactly, not approximated.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`Status` / `StatusComponent` pattern** (`src/python/common/status.py:80–175`) — Thread-safe property + listener machinery already used by `ServerStatus` and `ControllerStatus`. `StorageStatus` slots in with zero new infrastructure.
- **Existing SSE status stream** — `StatusStreamHandler` already serializes the full `Status` on every change; adding the `storage` block to `SerializeStatusJson.status()` makes it flow without new event plumbing.
- **`Sshcp.shell()` invocation pattern** (`src/python/controller/delete/delete_process.py:37,47`) — Synchronous SSH command shape with `shlex.quote` for path arguments. `df -B1 $(shlex.quote(remote_path))` reuses the same idiom.
- **`FileSizePipe`** — Already used throughout the stats strip for byte→human formatting. D-06/D-07 reuse it as-is; no new format helper.
- **`combineLatest` pattern from Phase 73** — `transfer-table.component.ts` already merges multiple streams into `filterState$`. `DashboardStatsService` adopts the same pattern to merge `ViewFileService.files` with `ServerStatusService.status`.
- **`stat-progress-track` / `stat-progress-fill` markup** (`stats-strip.component.html:14–20`) — Reuse the wrapper; capacity mode only swaps the width formula and adds a conditional warning/danger modifier class.

### Established Patterns
- **`>1% change gate before SSE push** — Spec-mandated, lives controller-side before the property setter is called (or inside the setter — Claude's discretion D-15). Prevents SSE flood while keeping the listener semantics simple.
- **Per-tile independent rendering** — Each stat card already evaluates its own data (`stats.remoteTrackedBytes`, `stats.localTrackedBytes`, etc.). D-15 keeps this contract: each tile reads its own pair from `DashboardStats`.
- **Silent fallback for upstream surprises** — Established in Phase 73 for invalid URL filter params. Phase 74 applies the same instinct to malformed `df` output (D-16).
- **Bootstrap semantic tokens for state** — `success` / `warning` / `danger` already drive badge and icon colors elsewhere. D-10 stays inside this vocabulary for capacity threshold colors.

### Integration Points
- **`Status` initialization site** — `Status.__init__` registers `server` and `controller` components; add `storage` here.
- **Controller scan finishers** — Local-scan completion path needs a `shutil.disk_usage` call; remote-scan completion path needs an extra `df -B1` call on the same `Sshcp` instance before the session is released.
- **`StatusStreamHandler` output** — No code change; the new fields ride along once `SerializeStatusJson.status()` includes them.
- **`DashboardStatsService` constructor** — Inject `ServerStatusService`, swap the bare `viewFileService.files.subscribe` for a `combineLatest([files, serverStatusService.status])` pipeline.
- **`stats-strip.component.html` Remote and Local cards (lines 3–41)** — The two `<div class="stat-card">` blocks each gain an `@if` capacity branch with the new layout per D-01..D-07.

</code_context>

<specifics>
## Specific Ideas

- The percentage is the **headline** in capacity mode — both because the design spec says so and because the seedsync user-facing question this phase answers is "am I about to fill the disk?", which only "X%" answers at a glance.
- Thresholds at **80% warn / 95% danger** are intentionally wide. Seedboxes routinely sit in the 70–85% band; tighter thresholds would cry wolf. 95% is the "act now or downloads will stall" line.
- The **silent-fallback rule for `df` failures** mirrors Phase 73's URL-param fallback. The user's intent on a flaky remote is "show me the dashboard"; degrading to tracked-bytes is the predictable safe default.
- Cold-load **never shows `0%`** — that misleads the user into thinking the disk is empty when really we just haven't received the first SSE payload yet. Fallback mode → capacity mode is the only legal transition.
- The new `(total, used)` pair for each side is checked **independently per tile**; one bad SSH `df` parse must not nuke the local-disk percentage.

</specifics>

<deferred>
## Deferred Ideas

- **Capacity history / trend sparkline** — out of scope; would need backend retention of (timestamp, capacity) tuples.
- **User-configurable threshold percentages** — punt; the 80/95 split is a sensible default. Revisit only if multiple users complain.
- **Notification / toast when crossing a threshold** — out of scope. The progress-bar color shift is the only signal this phase ships.
- **Multi-mount enumeration** (`/mnt/seedbox`, `/mnt/library`, …) — defer; current scan path is single-mount per side. Revisit when LFTP supports multi-target syncs.
- **E2E coverage of capacity rendering** — explicitly deferred per design spec (SSH `df` cannot be faked in E2E); rely on unit tests + manual verification on a live install.
- **`df` retry-on-parse-failure** — considered, rejected. One retry per scan adds plumbing for a vanishingly rare case; next scan cycle is already a free retry.
- **Surfacing `df` failures via `Status.ServerStatus.error_msg`** — rejected for this phase; would require deciding which side "owns" the field and how to clear it. Silent fallback + log is enough.

</deferred>

---

*Phase: 74-storage-capacity-tiles*
*Context gathered: 2026-04-19*
