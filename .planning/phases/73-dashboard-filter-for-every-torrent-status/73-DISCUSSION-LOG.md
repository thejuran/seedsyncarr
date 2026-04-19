# Phase 73: Dashboard filter for every torrent status - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `73-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 73-dashboard-filter-for-every-torrent-status
**Areas discussed:** Status coverage scope, Information architecture, Filter pattern, Persistence, WAITING_FOR_IMPORT handling

---

## Status coverage scope

### Q1: Which statuses must become reachable as filters?

| Option | Description | Selected |
|--------|-------------|----------|
| All 8 ViewFile.Status only | Add DEFAULT, DOWNLOADED, EXTRACTED to existing 5. ImportStatus stays as row badge / not filterable. | |
| All 8 + ImportStatus axis | Adds IMPORTED and WAITING_FOR_IMPORT as filters too. Recommended only if WAITING_FOR_IMPORT actually fires today. | |
| All 8 + only WAITING_FOR_IMPORT | Adds the 3 missing ViewFile.Status plus the operationally interesting WAITING_FOR_IMPORT filter. | ✓ |

**User's choice:** All 8 + only WAITING_FOR_IMPORT (later revised — see WAITING_FOR_IMPORT handling)

### Q2: What should each newly-exposed status be labeled?

| Option | Description | Selected |
|--------|-------------|----------|
| Idle / Synced / Extracted / Awaiting Import | Most consistent with current vocabulary ("Syncing" verb already in UI). | |
| Pending / Downloaded / Extracted / Awaiting Import | Closer to the underlying enum names. | ✓ |
| Available / Done / Unpacked / Pending Import | More user-outcome-focused. | |

**User's choice:** Pending / Downloaded / Extracted / Awaiting Import

---

## Information architecture

### Q3: How should the new statuses be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| Add "Done" parent + Pending under Active | All / Active (Pending, Syncing, Queued, Extracting) / Done (Downloaded, Extracted, Awaiting Import) / Errors. 4 parents total. | ✓ |
| Add "Pending" + "Done" + "Imports" | 5 parents: All / Pending / Active / Done / Imports / Errors. Each concern cleanly separated. | |
| Add "Done" only; Pending under Active; Awaiting under Done | Same as option 1 — preview was identical. | |

**User's choice:** Add "Done" parent + Pending under Active
**Notes:** Preview-rendered layout: `All | Active v | Done v | Errors v` with Active expanding to `Pending Syncing Queued Extracting`, Done expanding to `Downloaded Extracted Awaiting Import`, Errors expanding to `Failed Deleted`.

---

## Filter pattern

### Q4: Should multiple sub-statuses be combinable, or stay one at a time?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay single-select drill-down | One sub-status at a time. Identical to today's pattern. Preserves the locked design spec. | ✓ |
| Multi-select within a parent group | Within an expanded group, user can toggle multiple subs simultaneously. | |
| Multi-select across groups via chips | Replace sub-buttons with toggleable status chips. Biggest UX change — abandons the drill-down spec. | |

**User's choice:** Stay single-select drill-down

---

## Persistence

### Q5: Should the active filter persist across browser sessions?

| Option | Description | Selected |
|--------|-------------|----------|
| URL query params | Filter state in URL. Survives refresh, shareable, browser back/forward navigates filters. | ✓ |
| localStorage | Browser-private remembered choice. Doesn't survive across browsers/devices. | |
| Session-only (no persistence) | Current behavior — refresh resets to All. | |

**User's choice:** URL query params

---

## WAITING_FOR_IMPORT handling

### Q6: WAITING_FOR_IMPORT is currently a structural placeholder — backend never sets it. How to handle this in Phase 73?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship the filter button anyway | Add "Awaiting Import" sub-button now even though it'll always show 0 results. UI is ready for whenever the backend lands. | |
| Drop Awaiting Import from this phase | Skip WAITING_FOR_IMPORT filter — ship only the 3 missing ViewFile.Status. Defer to a future phase that also wires the backend. | ✓ |
| Ship + add backend wiring as part of this phase | Expand scope: implement the backend logic that sets WAITING_FOR_IMPORT. Largest scope. | |

**User's choice:** Drop Awaiting Import from this phase
**Notes:** This revises Q1 — final coverage is the 3 missing ViewFile.Status only (Pending, Downloaded, Extracted). The Done parent ships with 2 sub-buttons (Downloaded, Extracted), not 3. Awaiting Import deferred to a future phase that also wires the backend.

---

## Claude's Discretion

- Exact URL query-param string values (literal enum-string vs kebab-case vs short codes) — recommended literal enum-string for zero mapping layer.
- Whether to insert "Pending" first or last under Active — recommended first (workflow reading order).
- Whether to add unit tests for query-param hydration vs leaving to E2E only — recommended unit tests.
- Exact wording of any updated TS-doc / JSDoc.

## Deferred Ideas

- WAITING_FOR_IMPORT filter + backend wiring (future phase that lands the import-tracking logic).
- IMPORTED filter (row badge already covers it).
- Multi-select chip pattern with all/none toggles (rejected to preserve locked drill-down spec).
- Filter sub-button counts (no precedent; would compete with amber accent dot).
- URL persistence for `nameFilter` (search) and page number (out of scope; filter-only is the smallest meaningful win).
- E2E coverage for browser back/forward as filter navigation (falls out of URL persistence "for free"; worth follow-up testing).
