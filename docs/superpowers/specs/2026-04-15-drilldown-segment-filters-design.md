# Drill-down Segment Filters

**Date:** 2026-04-15
**Status:** Approved
**Component:** `TransferTableComponent` (`transfer-table.component.ts/html/scss`)
**Mockup:** `/tmp/filter-mockup.html` (AIDesigner run `16d38a0c`)

## Summary

Replace the flat All/Active/Errors segment filter with a two-level drill-down. Clicking Active or Errors first filters to that category (as today), then expands inline sub-buttons for individual statuses. Clicking a sub-button narrows to just that status.

## Behavior

### State transitions

| Current state | User action | Next state |
|---|---|---|
| All selected | Click Active | Active expanded, no sub-selection (shows all active) |
| All selected | Click Errors | Errors expanded, no sub-selection (shows all errors) |
| Active expanded (no sub) | Click sub-button (e.g., Syncing) | Active expanded, Syncing selected |
| Active expanded (no sub) | Click Active | Collapse back to All |
| Active expanded + sub | Click different sub | Switch sub-selection |
| Active expanded + sub | Click Active parent | Collapse back to All |
| Active expanded | Click Errors | Switch to Errors expanded |
| Active expanded | Click All | Collapse to All |
| Errors expanded | Same pattern as Active | Same pattern |

### Segment groups

- **All** — no children, terminal button
- **Active** — children: Syncing (DOWNLOADING), Queued (QUEUED), Extracting (EXTRACTING)
- **Errors** — children: Failed (STOPPED), Deleted (DELETED)

### Status-to-label mapping

| ViewFile.Status | Parent segment | Sub-button label |
|---|---|---|
| DOWNLOADING | Active | Syncing |
| QUEUED | Active | Queued |
| EXTRACTING | Active | Extracting |
| STOPPED | Errors | Failed |
| DELETED | Errors | Deleted |

## Visual design

### Default state (All selected)

- Three buttons in a pill group: `All | Active v | Errors v`
- All has active treatment (bg `#222a20`, border `#3e4a38`, shadow)
- Active and Errors show a small down-chevron (10px, 50% opacity, 100% on hover)

### Expanded state (no sub-selection)

- Parent button: full active treatment (border + shadow) with chevron rotated up
- Thin vertical divider (`1px, #3e4a38/60%`) separates parent from children
- Sub-buttons: dimmer text (`#7d8c6d`), slightly smaller padding (`10px` vs `12px`)
- Sub-buttons hover: text `#e0e8d6`, bg `#222a20/40%`

### Expanded state (sub-status selected)

- Parent button: lighter bg (`#222a20/60%`), no border, chevron up in amber (`#c49a4a`)
- Selected sub-button: active treatment (border, shadow) + amber text + amber dot with glow (`box-shadow: 0 0 6px 1px rgba(196, 154, 74, 0.3)`)
- Other sub-buttons: dimmer text as above

### Tokens (from existing SCSS)

| Token | Value |
|---|---|
| Pill background | `#151a14` |
| Active button bg | `#222a20` |
| Border | `#3e4a38` |
| Text primary | `#e0e8d6` |
| Text muted | `#9aaa8a` |
| Sub-button text | `#7d8c6d` |
| Accent | `#c49a4a` |
| Font size | `0.75rem` |
| Font weight | `500` |
| Border radius | `4px` |
| Button padding | `4px 12px` (parent), `4px 10px` (child) |
| Pill padding | `2px` |
| Transition | `0.15s ease` |

## Architecture

### Component changes

Only `TransferTableComponent` changes. No new components needed.

**TypeScript (`transfer-table.component.ts`):**

- Replace `activeSegment: "all" | "active" | "errors"` with a richer state:
  ```
  activeSegment: "all" | "active" | "errors" = "all";
  activeSubStatus: ViewFile.Status | null = null;
  ```
- `onSegmentChange()`: when clicking an already-expanded segment, collapse to All. When clicking a new segment, expand it (clear sub-status).
- New `onSubStatusChange(status: ViewFile.Status)`: sets `activeSubStatus`, updates filter.
- Update the `segmentedFiles$` pipeline: if `activeSubStatus` is set, filter to just that status. Otherwise filter by segment group as today.
- Page resets to 1 on any filter change (already handled).

**Template (`transfer-table.component.html`):**

- Conditional chevron icon (down when collapsed, up when expanded) on Active/Errors buttons
- `@if` block after each expandable button to render divider + sub-buttons when that segment is active
- Sub-buttons get `[class.active]` binding based on `activeSubStatus`

**SCSS (`transfer-table.component.scss`):**

- `.btn-segment--parent-expanded`: lighter bg, no border (when child exists)
- `.btn-segment--parent-active`: full active treatment (when expanded, no child selected)
- `.segment-divider`: thin vertical line
- `.btn-sub`: sub-button styles (smaller padding, dimmer text)
- `.btn-sub.active`: amber text + accent dot + glow
- `.accent-dot`: small circle with glow shadow

### Data flow

```
User clicks segment/sub-button
  -> onSegmentChange() or onSubStatusChange()
  -> updates activeSegment + activeSubStatus
  -> filterState$ emits
  -> segmentedFiles$ recalculates (segment group OR single status)
  -> pagedFiles$ updates
  -> template re-renders
```

No service changes. No new dependencies. The filter logic stays entirely within the component.

## Testing

- Unit tests for the filter logic: each segment group, each sub-status, switching between segments collapses sub-status
- Existing E2E tests unaffected (they don't test filter buttons beyond basic navigation)

## Scope exclusions

- No changes to the search input or pagination
- No changes to `ViewFile.Status` enum or `ViewFileService`
- No mobile-specific sub-button layout (sub-buttons hidden below 768px along with parent segment buttons, as today)
- No animation on expand/collapse (instant show/hide, consistent with existing segment behavior)
