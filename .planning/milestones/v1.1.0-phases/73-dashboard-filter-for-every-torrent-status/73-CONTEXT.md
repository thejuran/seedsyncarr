# Phase 73: Dashboard filter for every torrent status - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the dashboard transfer-table segment filter so every operationally-meaningful `ViewFile.Status` is reachable as a sub-button. Today 5 of 8 statuses are filterable (`DOWNLOADING`/`QUEUED`/`EXTRACTING` under Active; `STOPPED`/`DELETED` under Errors); this phase adds the 3 missing ones (`DEFAULT`, `DOWNLOADED`, `EXTRACTED`) into the existing drill-down segment-filter pattern, and introduces URL-query-param persistence for the active filter selection.

**Out of scope:** WAITING_FOR_IMPORT filter (backend doesn't set it yet — see Deferred); IMPORTED filter; multi-select / chip pattern; new search/sort capabilities; persistence of search query or page number; Storage tile changes (Phase 74); any backend or `ViewFileService` changes.

</domain>

<decisions>
## Implementation Decisions

### Status coverage
- **D-01:** Add 3 new filterable statuses to the dashboard segment filter: `ViewFile.Status.DEFAULT`, `ViewFile.Status.DOWNLOADED`, `ViewFile.Status.EXTRACTED`. After this phase, all 8 `ViewFile.Status` values are reachable.
- **D-02:** Skip the `ImportStatus.WAITING_FOR_IMPORT` filter for now — the enum exists as a structural placeholder and is never set by backend code, so the button would always show 0 results. See Deferred Ideas.
- **D-03:** User-facing labels for the 3 new sub-buttons:
  - `DEFAULT` → **"Pending"**
  - `DOWNLOADED` → **"Downloaded"**
  - `EXTRACTED` → **"Extracted"**

### Information architecture
- **D-04:** Add one new top-level parent segment **"Done"** as a sibling of Active and Errors. Final segment-filter layout:
  - `All` (terminal)
  - `Active v` — sub-buttons: **Pending, Syncing, Queued, Extracting** (4 subs; Pending is new)
  - `Done v` — sub-buttons: **Downloaded, Extracted** (new parent, 2 subs)
  - `Errors v` — sub-buttons: **Failed, Deleted** (unchanged)
- **D-05:** **Pending** lives under Active (it represents pre-queue idle state — files seen by the scanner but not yet acted on, conceptually adjacent to the in-flight statuses).
- **D-06:** **"Done"** parent, when clicked without a sub-selection, filters to `DOWNLOADED ∪ EXTRACTED` (same group-OR semantics that Active and Errors already use in `segmentedFiles$`).

### Filter pattern
- **D-07:** Preserve the existing single-select drill-down pattern from `docs/superpowers/specs/2026-04-15-drilldown-segment-filters-design.md` exactly. State stays `activeSegment: "all" | "active" | "done" | "errors"` + `activeSubStatus: ViewFile.Status | null` (just one new segment value). No multi-select, no all/none toggles, no chip migration.
- **D-08:** State-transition semantics for the new "Done" parent are identical to Active/Errors: click expands; click again collapses to All; click a sibling parent switches groups; click a sub selects only that status; click the parent while a sub is selected collapses to All.

### Persistence
- **D-09:** Persist active filter via **URL query params**. On `onSegmentChange` / `onSubStatusChange`, write `?segment=<segment>&sub=<status>` (omit `sub` when no sub-status selected; omit both when `segment === 'all'`). On component init, read the query params and hydrate `activeSegment` + `activeSubStatus` before the first `filterState$.next()`.
- **D-10:** Use `Router.navigate` with `queryParamsHandling: 'merge'` so the persistence write doesn't clobber any other params present in the URL.
- **D-11:** Invalid query-param values (segment not in the enum, or `sub` that doesn't belong to the named segment) silently fall back to `segment=all` with no error toast. Page state is **not** persisted (resets to 1 on filter change as today, per existing `combineLatest`). Search `nameFilter` is **not** persisted in this phase.

### Carry-forward (locked from prior phases)
- **D-12:** Filter changes continue to **clear file selection** (Phase 72 D-04 — wired into the existing `filterState$` reset flow in `TransferTableComponent`).
- **D-13:** Filter changes continue to **reset page to 1** via the existing `combineLatest` flow at `transfer-table.component.ts:95-98`.
- **D-14:** Mobile (<768px): the new "Done" parent + its sub-buttons follow the **existing** mobile visibility rule — hidden along with the rest of `.segment-filters`. No new mobile-specific layout in this phase.
- **D-15:** Visual treatment of the new "Done" parent and its sub-buttons uses the **identical SCSS tokens and classes** from the locked drill-down design spec (`.btn-segment`, `.btn-segment--parent-active`, `.btn-segment--parent-expanded`, `.btn-sub`, `.btn-sub.active`, `.accent-dot`, `.segment-divider`). No new design tokens.

### Claude's Discretion
- Exact string values used in the URL (e.g., `?sub=downloaded` literal-enum-string, vs kebab-case, vs short codes). Recommend literal enum-string to match `ViewFile.Status` values directly — zero mapping layer.
- Whether to insert "Pending" as the first or last sub-button under Active. Recommend first (left-most) since it's the pre-queue state, reading left-to-right matches workflow order: Pending → Queued → Syncing → Extracting.
- Whether to add or update unit tests for the new query-param hydration code (recommended) vs leaving testing entirely to E2E.
- Exact wording of any updated `@input` JSDoc / TS-doc.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design contract — extend, don't redesign
- `docs/superpowers/specs/2026-04-15-drilldown-segment-filters-design.md` — The drill-down state machine, SCSS token table, and class names. Phase 73 extends this spec with one new parent ("Done") + one new sub under Active ("Pending"). Every visual decision must match the tokens listed in that spec.

### Upstream todo
- `.planning/todos/completed/2026-04-17-add-dashboard-filter-for-every-torrent-status.md` — Original problem statement ("filter by every possible status"), candidate ideas (chips, persistence, all/none toggles), the persistence ask that's being honored as URL params.

### Adjacent prior-phase context
- `.planning/phases/72-restore-dashboard-file-selection-and-action-bar/72-CONTEXT.md` — Phase 72 D-04 mandates that any filter change clears selection. Phase 73 must preserve that wiring.

### Code artifacts to modify
- `src/angular/src/app/pages/files/transfer-table.component.ts` — Add `'done'` to the `activeSegment` union; extend `segmentedFiles$` with a Done branch (`status === DOWNLOADED || status === EXTRACTED`); add Pending case under the existing Active branch; add query-param hydration on init + write on `onSegmentChange` / `onSubStatusChange`.
- `src/angular/src/app/pages/files/transfer-table.component.html` — Add the "Done" parent button + its expand block (Downloaded, Extracted sub-buttons); add "Pending" sub-button to the Active expand block. Mirror the chevron-down/up + `accent-dot` markup already used by Active/Errors.
- `src/angular/src/app/pages/files/transfer-table.component.scss` — No new tokens. Verify the existing `.btn-segment` / `.btn-sub` classes apply cleanly to the new buttons.

### Status enum (don't change)
- `src/angular/src/app/services/files/view-file.ts:90-100` — `ViewFile.Status` enum (8 values). Phase 73 reads from this enum but does not modify it.

### Tests
- Unit tests for `TransferTableComponent` filter logic — extend with cases for `segment=done`, `sub=downloaded`, `sub=extracted`, `sub=default` (Pending), and URL hydration / write-back.
- `src/e2e/tests/dashboard.page.spec.ts` — Existing tests (Phase 72) cover selection clearing on filter change and pagination behavior; add page-object selectors and basic E2E coverage for the new Done parent + Pending sub.
- `src/e2e/tests/dashboard.page.ts` — Page-object selectors need new entries for the Done parent button, the Done sub-buttons, and the Pending sub-button.

### Project-level rules
- `.planning/PROJECT.md` — Constraints (dark-only, Deep Moss + Amber palette, no SVG icons except already-approved Phosphor caret-up/caret-down, text-only buttons, system fonts).
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md` — "Port AIDesigner HTML identically, no approximations." For Phase 73 this means: every new sub-button must reuse the existing `.btn-sub` SCSS class verbatim — no per-instance overrides.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`TransferTableComponent.filterState$`** — Already a `BehaviorSubject<{segment, subStatus, page}>` that drives both `segmentedFiles$` and selection-clear / page-reset side effects. New segment value `'done'` plugs into the existing `combineLatest` and switch-on-segment logic with no structural change.
- **`segmentedFiles$` switch** — Already filters Active / Errors / All. Adding a Done branch is a single new case.
- **`.btn-segment` + `.btn-sub` SCSS classes** — Locked styling kit; new "Done" parent and "Pending"/"Downloaded"/"Extracted" subs reuse them as-is.
- **Phosphor `ph-caret-down` / `ph-caret-up` icons** — Already wired into Active and Errors parent buttons; the new "Done" parent uses the same markup.
- **Chevron rotate + `--parent-expanded` / `--parent-active` class machinery** — Already in template; the new parent uses the identical conditional classes.

### Established Patterns
- **Single-source filter state in component** (per locked drill-down spec): no service-side filter state. Phase 73 keeps this — the URL query params are the persistence layer, not a new service.
- **Selection clears on any filter change** (Phase 72 D-04): wired into the `filterState$` reset flow. New segment 'done' inherits this for free.
- **Page resets on filter change** via the existing `combineLatest` at `transfer-table.component.ts:95-98`. New segment 'done' inherits this for free.
- **Mobile responsive rule** for `.segment-filters`: the entire filter group is hidden below 768px. The new parent + subs inherit this — no new mobile-specific styling.
- **OnPush + signal-based selection** (M007 + Phase 72): keep the same change-detection contract. Query-param read on init must happen before the first `filterState$.next()` to avoid a flash of "All".

### Integration Points
- **`Router` + `ActivatedRoute`** — New dependencies on `TransferTableComponent` to read/write query params. `ActivatedRoute.queryParamMap` for hydration on init; `Router.navigate([], { queryParams, queryParamsHandling: 'merge' })` for write-back.
- **Template insertion sites** — One new `@if (activeSegment === 'done')` block after the existing Errors block; one new `<button class="btn-sub">` for Pending inside the existing Active `@if` block.
- **Test wiring** — `dashboard.page.ts` page-object gains four new selectors (Done parent, Downloaded sub, Extracted sub, Pending sub). `dashboard.page.spec.ts` keeps Phase 72's selection-clearing assertion working under the new filter values.

</code_context>

<specifics>
## Specific Ideas

- "Pending" lives **first** under Active (recommended), so the sub-buttons read left-to-right in workflow order: Pending → Syncing → Queued → Extracting.
- URL persistence is for the **filter state**, not the whole table state. Page number and search input deliberately stay session-only — keeps the URL short, and matches the user's framing in the source todo (which only asked for "filters" to persist).
- Invalid URL params (typo'd or stale link) silently fall back to All. No toast, no console warning. The user's intent on a stale link is "show me the dashboard"; degrading to All is the predictable safe default.
- WAITING_FOR_IMPORT was explicitly considered and pulled out — adding a filter button that always shows 0 results would be a confusing dead UI. Re-add it together with the backend logic that actually sets the status (future phase).

</specifics>

<deferred>
## Deferred Ideas

- **WAITING_FOR_IMPORT filter + backend wiring** — Add the "Awaiting Import" sub-button (likely under Done) only when the backend `*arr` webhook handler actually transitions files to `WAITING_FOR_IMPORT`. Future phase.
- **IMPORTED filter** — `ImportStatus.IMPORTED` as a filter dimension. Skipped this phase because the row badge already conveys it and DOWNLOADED/EXTRACTED filters cover the operationally interesting "find me what's done" use case.
- **Multi-select chip pattern with all/none toggles** — Considered (todo's hint); rejected to preserve the locked drill-down spec from 2026-04-15.
- **Filter sub-button counts** ("Syncing (3)") — Not requested; no current precedent in the segment filter; would compete visually with the amber accent dot. Re-evaluate if users complain about not knowing whether a status is empty before clicking.
- **URL persistence for `nameFilter` (search) and page number** — Out of scope for this phase. Filter-only persistence is the smallest meaningful win; search/page persistence is a separate UX concern.
- **Browser back/forward as filter navigation** — Falls out of URL persistence "for free" via Angular Router, but it's a behavior worth E2E-testing in a follow-up.

</deferred>

---

*Phase: 73-dashboard-filter-for-every-torrent-status*
*Context gathered: 2026-04-19*
