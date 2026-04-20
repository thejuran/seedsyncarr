---
phase: 72-restore-dashboard-file-selection-and-action-bar
plan: 03
status: complete
decisions: [D-01, D-03, D-06, D-15]
tasks_completed: 3
files_modified:
  - src/angular/src/app/pages/files/transfer-row.component.ts
  - src/angular/src/app/pages/files/transfer-row.component.html
  - src/angular/src/app/pages/files/transfer-row.component.scss
  - src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts
---

# 72-03 Summary — TransferRow checkbox + selection-signal wiring

## What was built

TransferRowComponent now renders a leading checkbox cell bound to
`FileSelectionService.selectedFiles()` via a `computed()`-backed
`isSelected` signal. Clicking the checkbox stops propagation and emits
`{file, shiftKey}` on `checkboxToggle` for plan 04's range-select contract.
The host `<tr>` picks up `class.row-selected` via `@HostBinding` whenever
the signal reports true, and the host `aria-label` gains a `, selected`
suffix so assistive tech reflects the state.

## Final CSS class names (for plan 04 and plan 05 E2E selectors)

- Row host: `app-transfer-row` (default element) — carries `row-selected` when in selection set
- Leading cell: `td.cell-checkbox`
- Input: `input.ss-checkbox` inside `td.cell-checkbox`
- Selected-row style hook: `:host.row-selected` → amber wash + 3px amber inset left-border

Plan 04's transfer-table header must add a matching `<th class="col-checkbox">`
(or similar) to preserve column alignment. Plan 05's Playwright page object
must target `app-transfer-row td.cell-checkbox input.ss-checkbox` for the
per-row checkbox.

## Selected-row precedence choice

Used **`!important`** on the `background` declaration inside `:host.row-selected`
(and its `&:hover` nested rule) to win over the existing
`:host:nth-child(odd)` zebra-stripe rule. Rule ordering alone was insufficient
because the zebra stripe lives in a sibling `:host` selector with equivalent
specificity; `!important` makes the precedence intent explicit and resilient
to future SCSS reordering. The `box-shadow: inset 3px 0 0 #d4a574;` left-border
does not need `!important` because no existing rule sets `box-shadow` on the
host.

## Palette values ported literally (Variant B, no approximations)

| Where | Value |
|-------|-------|
| `.ss-checkbox` border | `1px solid #2d3a2d` |
| `.ss-checkbox` background | `#1a201a` |
| `.ss-checkbox::before` checkmark clip-path | `polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%)` |
| `.ss-checkbox:checked` fill + border | `#d4a574` |
| `:host.row-selected` background | `rgba(212, 165, 116, 0.04)` |
| `:host.row-selected` left border | `inset 3px 0 0 #d4a574` (D-06 spec — honors 3px over Variant B's `border-l-2` 2px) |
| `:host.row-selected:hover` background | `rgba(212, 165, 116, 0.08)` |

## Spec count delta

- Pre-Task-3: 17 specs
- Post-Task-3: 22 specs (5 new under the `checkbox + selection signal` describe block)
- Result: 22/22 green

## Build / test verification

- `npx tsc --noEmit -p src/tsconfig.app.json` — exits 0
- `npx ng build --configuration=development` — exits 0 (only pre-existing `@import` deprecation warnings from styles.scss)
- `npx ng test --include='**/transfer-row.component.spec.ts' --watch=false --browsers=ChromeHeadless` — 22/22 SUCCESS

## Notes for downstream plans

- Plan 04 will consume `checkboxToggle: EventEmitter<{file, shiftKey}>` on
  each row. The transfer-table is responsible for translating `shiftKey=true`
  into a `selectRange(...)` service call.
- `FileSelectionService` was NOT modified — its signal contract is the
  integration point.
- `click-stop-propagation.directive.ts` was NOT modified — already exists and
  is used as-is via the `appClickStopPropagation` attribute on the new cell.
