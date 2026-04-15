---
status: partial
phase: 70-drilldown-segment-filters
source: [70-VERIFICATION.md]
started: 2026-04-15T20:55:00Z
updated: 2026-04-15T20:55:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Drill-down visual layout (Active)
expected: Clicking Active shows Syncing/Queued/Extracting sub-buttons inline within the pill container, with a divider separator
result: [pending]

### 2. Drill-down visual layout (Errors)
expected: Clicking Errors shows Failed/Deleted sub-buttons inline within the pill container, with a divider separator
result: [pending]

### 3. Amber accent dot with glow
expected: Selected sub-button shows a 6px amber (#c49a4a) dot with subtle glow (box-shadow)
result: [pending]

### 4. Toggle-collapse interaction
expected: Second click on expanded parent collapses back to All; clicking a different parent switches and clears sub-status
result: [pending]

### 5. Chevron rotation
expected: Chevron icon rotates from caret-down to caret-up when parent segment is expanded
result: [pending]

### 6. Pixel-exact mockup match
expected: All 3 visual states (default, expanded+sub-selected, expanded+no-sub) match /private/tmp/filter-mockup.html
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
