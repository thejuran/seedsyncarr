# Phase 72: Restore dashboard file selection and action bar - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 8 target files (5 modify, 1 adapt, 2 E2E update) + context files
**Analogs found:** 8 / 8 (all have strong, concrete analogs in the same codebase)

## File Classification

| Target File | New/Modified | Role | Data Flow | Closest Analog | Match Quality |
|-------------|--------------|------|-----------|----------------|---------------|
| `src/angular/src/app/pages/files/bulk-actions-bar.component.ts` | Modify (rename optional) | component (action bar) | event-driven | *itself* — adapt in place | exact (self) |
| `src/angular/src/app/pages/files/bulk-actions-bar.component.html` | Modify (rewrite) | component template | request-response | `variant-B-card-internal-bar.html:306-329` | exact (design contract) |
| `src/angular/src/app/pages/files/bulk-actions-bar.component.scss` | Modify (rewrite) | component styles | N/A | `transfer-row.component.scss` (literal-hex SCSS convention) + `variant-B-card-internal-bar.html:306-329` (tokens) | exact (design contract) |
| `src/angular/src/app/pages/files/transfer-row.component.ts` | Modify | row component | signal-driven | `file.component.ts:57-101,184-187` (signal selection + checkbox handler) | exact |
| `src/angular/src/app/pages/files/transfer-row.component.html` | Modify | row template | display | `file.component.html:4-17` (checkbox markup + aria) combined with `variant-B-card-internal-bar.html:184-185,223` (checkbox column cell) | exact |
| `src/angular/src/app/pages/files/transfer-row.component.scss` | Modify | row styles | N/A | `file.component.scss` selected-row patterns + `variant-B-card-internal-bar.html:184,222` (amber-wash + left-border) | exact |
| `src/angular/src/app/pages/files/transfer-table.component.ts` | Modify | container component | request-response | `file-list.component.ts:93-120,171-216,319-376` (selection clearing + Ctrl+A / Esc / shift-click anchor) | exact |
| `src/angular/src/app/pages/files/transfer-table.component.html` | Modify | container template | display | `file-list.component.html:1-48` (bar wiring + header checkbox) | exact |
| `src/e2e/tests/dashboard.page.spec.ts` | Modify (unskip + rewrite) | E2E test | test | Pre-v1.1.0 versions of the 5 tests (git history) + current `dashboard.page.ts:37-51` file shape | role-match |
| `src/e2e/tests/dashboard.page.ts` | Modify (add selectors) | E2E page object | test support | `dashboard.page.ts:37-51` (existing selectors) | exact (self) |

---

## Pattern Assignments

### `bulk-actions-bar.component.ts` (component, event-driven action bar) — ADAPT IN PLACE

**Analog:** Itself — the existing file already contains the eligibility contract the phase must preserve.

**Keep:** `@Input` shape, `ngOnChanges` cache recompute pass, 5 `@Output` emitters, getters, click handlers. Do not alter the signatures or cache strategy. `bulk-actions-bar.component.spec.ts` is the regression anchor (CONTEXT D-14).

**Imports + input/output contract** (lines 1-47, 57, 138-162):
```typescript
import {Component, Input, Output, EventEmitter, ChangeDetectionStrategy, OnChanges, SimpleChanges} from "@angular/core";
import {List} from "immutable";
import {ViewFile} from "../../services/files/view-file";

export interface BulkActionCounts {
    queueable: number;
    stoppable: number;
    extractable: number;
    locallyDeletable: number;
    remotelyDeletable: number;
}

@Component({
    selector: "app-bulk-actions-bar",
    templateUrl: "./bulk-actions-bar.component.html",
    styleUrls: ["./bulk-actions-bar.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
    standalone: true,
})
export class BulkActionsBarComponent implements OnChanges {
    @Input() visibleFiles: List<ViewFile> = List();
    @Input() selectedFiles: Set<string> = new Set();
    @Input() operationInProgress = false;

    @Output() clearSelection = new EventEmitter<void>();
    @Output() queueAction = new EventEmitter<string[]>();
    @Output() stopAction = new EventEmitter<string[]>();
    @Output() extractAction = new EventEmitter<string[]>();
    @Output() deleteLocalAction = new EventEmitter<string[]>();
    @Output() deleteRemoteAction = new EventEmitter<string[]>();
    ...
}
```

**Eligibility cache pattern** (lines 74-132): Do **not** modify. The single-pass `_recomputeCachedValues` on `ngOnChanges` is the M007 performance contract referenced in D-12.

**Getters (`actionCounts`, `queueableFiles`, etc.)** and the five `on*Click()` handlers (lines 230-282) already fan out to the eligible-only subset. Template rewrite uses these same getters — no handler rewrites needed.

**Rename (Claude's discretion, D-13):** `BulkActionsBarComponent` → `TransferActionsBarComponent` allowed; selector change would cascade to `files-page.component.html` and `transfer-table.component.html`. Spec file references `../../pages/files/bulk-actions-bar.component` — update if renaming.

---

### `bulk-actions-bar.component.html` (template, rewrite) — VARIANT B PORT

**Analog:** `.planning/phases/72-restore-dashboard-file-selection-and-action-bar/variant-B-card-internal-bar.html` lines 306-329 (the action bar block itself). Port identically per design-spec rigor memory.

**Bar container** (Variant B, line 306):
```html
<div class="border-t border-brand-amber/30 bg-[#252e23] px-5 py-3 flex justify-between items-center z-10 shadow-[inset_0_1px_0_rgba(212,165,116,0.1)]">
```
Maps to a `.bulk-actions-bar` wrapper in SCSS — keep the `@if (hasSelection)` guard from current line 1.

**Left group — "2 selected" label + Clear link** (Variant B, lines 307-310):
```html
<div class="flex items-center gap-3">
    <span class="text-sm font-medium text-brand-amber">2 selected</span>
    <button class="text-xs text-ui-secondary hover:text-ui-primary underline decoration-moss-border underline-offset-2 transition-colors">Clear</button>
</div>
```
Bind count from `selectedCount`; Clear `(click)="onClearClick()"`. Drop current `{{ selectedCount === 1 ? 'file' : 'files' }}` wording — Variant B text is just "2 selected" (terse).

**Queue button — primary amber** (Variant B, lines 312-314):
```html
<button class="flex items-center gap-1.5 px-3 py-1.5 rounded bg-brand-amber text-moss-base hover:bg-brand-amber/90 font-medium text-xs shadow-sm transition-colors focus:ring-2 focus:ring-brand-amber focus:ring-offset-2 focus:ring-offset-moss-surface">
    <i class="ph-bold ph-play"></i> Queue
</button>
```
Disabled guard: `[disabled]="actionCounts.queueable === 0 || operationInProgress"` from current line 20. **Icon mapping** (per PROJECT.md "map Phosphor → FA4.7"): `ph-play` → `fa fa-play`.

**Stop / Delete Local / Delete Remote — red outline** (Variant B, lines 315-317, 322-324):
```html
<button class="flex items-center gap-1.5 px-3 py-1.5 rounded border border-status-red/40 text-status-red hover:bg-status-red/10 font-medium text-xs transition-colors">
    <i class="ph-bold ph-stop"></i> Stop
</button>
```
Icon maps: `ph-stop` → `fa fa-stop`, `ph-trash` → `fa fa-trash`, `ph-cloud-slash` → `fa fa-cloud` with strikethrough (closest FA4.7).

**Extract (+ disabled-neutral state) + vertical divider** (Variant B, lines 318-321):
```html
<button class="flex items-center gap-1.5 px-3 py-1.5 rounded border border-moss-border text-ui-muted cursor-not-allowed opacity-50 font-medium text-xs bg-moss-terminal/50" disabled>
    <i class="ph-bold ph-archive"></i> Extract
</button>
<div class="w-px h-5 bg-moss-border mx-1"></div>
```
Divider between Extract and Delete Local is a literal 1px × 20px element — not a CSS pseudo. Icon: `ph-archive` → `fa fa-file-archive-o`.

**Current count-in-label pattern** (existing line 22): `Queue ({{ actionCounts.queueable }})`. Variant B omits the count from the button label. Keep or drop per Claude's discretion — Variant B HTML is the literal port target, so **drop** the `({{ count }})` suffix by default.

---

### `bulk-actions-bar.component.scss` (styles, rewrite) — VARIANT B + PROJECT CONVENTION

**SCSS convention analog:** `transfer-row.component.scss:1-22` uses `@use '../../common/common' as *;` header and literal hex values throughout rather than Tailwind tokens — this is the project's "port to SCSS" pattern:
```scss
@use '../../common/common' as *;

:host { display: table-row; transition: background 0.15s ease; }
td { padding: 12px 16px; font-family: 'JetBrains Mono', $font-family-monospace; }
```

**Literal values to port from Variant B (CONTEXT "Palette tokens" + HTML line 306):**
- Background band: `#252e23` (HTML line 306 `bg-[#252e23]`)
- Top divider: `1px solid rgba(212, 165, 116, 0.3)` (HTML `border-t border-brand-amber/30`)
- Inset shadow: `inset 0 1px 0 rgba(212, 165, 116, 0.1)` (HTML `shadow-[inset_0_1px_0_rgba(212,165,116,0.1)]`)
- "selected" label color: `#d4a574` (brand amber)
- Clear link: color `#9ca39a`, hover `#e8ebe6`, `text-decoration: underline`, `text-decoration-color: #2d3a2d`
- Queue fill: `background: #d4a574; color: #1a201a;` + hover `rgba(212, 165, 116, 0.9)`
- Red outline buttons: `border: 1px solid rgba(201, 125, 125, 0.4); color: #c97d7d;` + hover `background: rgba(201, 125, 125, 0.1)`
- Extract disabled neutral: `border: 1px solid #2d3a2d; color: #6b736a; background: rgba(17, 21, 17, 0.5); opacity: 0.5; cursor: not-allowed`
- Vertical divider: `width: 1px; height: 20px; background: #2d3a2d; margin: 0 4px`
- Padding: `12px 20px` (matches Variant B `px-5 py-3` ≈ 20px/12px)
- Button sizing: `padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 500;` (Variant B `px-3 py-1.5 rounded text-xs font-medium`)
- Button gap: `8px` (Variant B `gap-2`)
- Icon-label gap inside button: `6px` (Variant B `gap-1.5`)

**Discard** the existing SCSS entirely (current file uses `var(--app-selection-*)` custom props + Bootstrap semantic `$primary/$secondary/$danger`, which the Variant B port supersedes). Retain only the `@use '../../common/common' as *;` header pattern per the transfer-row convention.

**Media queries:** keep current lines 96-119 shape (stack flex column below `$medium-min-width`, full-width buttons below `$small-max-width`); re-map class names after any SCSS-class rename.

---

### `transfer-row.component.ts` (row component, signal-driven)

**Analog:** `file.component.ts` — same role (single-file row with checkbox + selection signal). The phase brief (CONTEXT line 102) explicitly points to `FileComponent:95-101`.

**Imports pattern** (file.component.ts lines 1-17, especially lines 3-17):
```typescript
import {Component, Input, Output, ChangeDetectionStrategy, EventEmitter, inject, computed, HostBinding} from "@angular/core";
import {ClickStopPropagationDirective} from "../../common/click-stop-propagation.directive";
import {FileSelectionService} from "../../services/files/file-selection.service";
```
Existing transfer-row imports (lines 1-6) stay; add these four.

**Service injection + selection signal** (file.component.ts lines 57-58, 95-101):
```typescript
private selectionService = inject(FileSelectionService);

readonly isSelected = computed(() => {
    const selected = this.selectionService.selectedFiles();
    return this.file?.name != null ? selected.has(this.file.name) : false;
});
```
Copy verbatim into `TransferRowComponent`.

**HostBinding for selected-row class** (file.component.ts lines 104-123 shows the HostBinding pattern; use the same `class.X` binding style for selection):
```typescript
@HostBinding("class.row-selected") get isRowSelected(): boolean { return this.isSelected(); }
```
Note `:host` selector on transfer-row (`transfer-row.component.scss:6` — `display: table-row`) means HostBinding is the correct way to toggle a class on the `<app-transfer-row>` element. File.component uses per-status @HostBindings — follow that convention instead of a single `@HostBinding('class')` to avoid overwriting parent-applied classes (see comment at file.component.ts:104-109).

**Checkbox click handler** (file.component.ts lines 75, 184-187):
```typescript
@Output() checkboxToggle = new EventEmitter<{file: ViewFile, shiftKey: boolean}>();

onCheckboxClick(event: MouseEvent): void {
    event.stopPropagation();
    this.checkboxToggle.emit({file: this.file, shiftKey: event.shiftKey});
}
```
Copy verbatim. The event includes `shiftKey` for range-select (D-03).

**OnPush change detection:** transfer-row.component.ts:15 already uses `ChangeDetectionStrategy.OnPush` — matches M007 requirement (CONTEXT line 104).

**Imports array update:** Add `ClickStopPropagationDirective` to the `@Component.imports` array (already used in file.component.ts:37).

---

### `transfer-row.component.html` (row template) — ADD CHECKBOX CELL

**Analog A — checkbox cell structure** (file.component.html:11-17):
```html
<div class="checkbox" appClickStopPropagation>
    <input type="checkbox"
        [checked]="isSelected()"
        (click)="onCheckboxClick($event)"
        [attr.aria-label]="'Select ' + file.name" />
</div>
```

**Analog B — Variant B `<td>` cell markup** (variant-B-card-internal-bar.html lines 184-185, 223):
```html
<td class="py-3 px-5 text-center"><input type="checkbox" class="ss-checkbox" checked aria-label="Select item"></td>
```
In SCSS form: `<td class="cell-checkbox">` with `text-align: center` and the custom `.ss-checkbox` styling ported.

**Insertion point:** add as the FIRST `<td>` in transfer-row.component.html (before current line 1 `<td class="cell-name">`). Wrap the `<input>` in a container `<div>` or `<span>` carrying `appClickStopPropagation` per the FileComponent pattern — alternatively apply `appClickStopPropagation` directly to the `<td>` since the directive only stops click propagation.

**Final cell template to write:**
```html
<td class="cell-checkbox" appClickStopPropagation>
  <input type="checkbox" class="ss-checkbox"
    [checked]="isSelected()"
    (click)="onCheckboxClick($event)"
    [attr.aria-label]="'Select ' + file.name" />
</td>
```

**ARIA on host** (CONTEXT D-06; file.component.html:8-10 pattern):
```html
role="row"
[attr.aria-label]="file.name + ', ' + (file.status | capitalize) + (isSelected() ? ', selected' : '')"
```
Apply these via `@HostBinding` in the `.ts` since transfer-row's host element already acts as `<tr>`.

---

### `transfer-row.component.scss` (row styles) — SELECTED-ROW TREATMENT

**Analog — custom checkbox style** (variant-B-card-internal-bar.html lines 45-58 inline `<style>`):
```css
.ss-checkbox {
    appearance: none; width: 1rem; height: 1rem;
    border: 1px solid #2d3a2d; border-radius: 0.25rem;
    background-color: #1a201a; display: grid; place-content: center;
    cursor: pointer; transition: all 0.15s ease-in-out;
}
.ss-checkbox::before {
    content: ""; width: 0.65em; height: 0.65em;
    clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%);
    transform: scale(0); transform-origin: bottom left;
    transition: 120ms transform ease-in-out; background-color: #1a201a;
}
.ss-checkbox:checked { background-color: #d4a574; border-color: #d4a574; }
.ss-checkbox:checked::before { transform: scale(1); }
```
Port verbatim into `transfer-row.component.scss` (or a shared location — Claude's discretion).

**Analog — selected-row background + left border** (variant-B-card-internal-bar.html lines 184, 222):
```html
<tr class="hover:bg-moss-base/40 transition-colors bg-brand-amberWash border-l-2 border-l-brand-amber">
```
Maps to:
```scss
:host.row-selected {
    background: rgba(212, 165, 116, 0.04);  // brand-amberWash
    box-shadow: inset 3px 0 0 #d4a574;       // 3px amber left border (D-06)
    // OR: border-left: 3px solid #d4a574 on the first <td>
}
```
Note: `border-left` on `:host` (which renders as `<tr>`) does not render in most browsers' default table styling — use `box-shadow: inset 3px 0 0 #d4a574` OR apply `border-left: 3px solid #d4a574` to the first cell. CONTEXT D-06 specifies "3px amber left-border accent" — either approach satisfies the spec.

**Preserve the existing zebra-stripe rule** (transfer-row.component.scss:14-20):
```scss
&:nth-child(odd) { background: #1a2019; ... }
```
`:host.row-selected` should take precedence — order the selectors so `.row-selected` appears after the zebra stripe rule, or use higher specificity.

**Cell spec for checkbox column** (variant-B-card-internal-bar.html line 174):
```scss
.cell-checkbox {
    padding: 12px 20px;  // matches Variant B py-3 px-5
    text-align: center;
    width: 3rem;         // Variant B w-12
}
```

---

### `transfer-table.component.ts` (container) — WIRE SELECTION CLEARING + SHIFT-CLICK

**Analog:** `file-list.component.ts` — carries the complete selection orchestration pattern the phase reuses (CONTEXT D-15, D-16).

**Selection-clearing hook** — the insertion point. Current transfer-table.component.ts lines 93-98:
```typescript
// Reset page when filter options change
this.viewFileOptionsService.options
    .pipe(takeUntilDestroyed(this.destroyRef))
    .subscribe(() => {
        this.goToPage(1);
    });
```
Add `this.fileSelectionService.clearSelection();` inside this subscribe (CONTEXT D-04, line 99). Same treatment in `onSegmentChange` (lines 117-130) and `onSubStatusChange` (lines 132-150) where page resets to 1. D-04 requires clearing selection on **any** page change, filter change, or segment change.

**Shift-click + anchor tracking pattern** (file-list.component.ts lines 66, 91-100, 346-376):
```typescript
// Track last clicked file name for shift+click range selection
private _lastClickedFileName: string | null = null;
private _currentFiles: List<ViewFile> = List();
...
this.files.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(files => {
    this._currentFiles = files;
});
...
onCheckboxToggle(event: {file: ViewFile, shiftKey: boolean}): void {
    if (event.shiftKey && this._lastClickedFileName !== null) {
        const lastIndex = this._currentFiles.findIndex(f => f.name === this._lastClickedFileName);
        const currentIndex = this._currentFiles.findIndex(f => f.name === event.file.name);
        if (lastIndex !== -1 && currentIndex !== -1) {
            const start = Math.min(lastIndex, currentIndex);
            const end = Math.max(lastIndex, currentIndex);
            const rangeNames: string[] = [];
            for (let i = start; i <= end; i++) {
                const file = this._currentFiles.get(i);
                if (file?.name) { rangeNames.push(file.name); }
            }
            this.fileSelectionService.setSelection(rangeNames);
        } else {
            this.fileSelectionService.toggle(event.file.name!);
            this._lastClickedFileName = event.file.name;
        }
    } else {
        this.fileSelectionService.toggle(event.file.name!);
        this._lastClickedFileName = event.file.name;
    }
}
```
Port verbatim. Note the `_currentFiles` cache must track the **segmented & paged** slice — the shift-click anchor must resolve within whichever list the user is clicking. Options: (a) cache `pagedFiles$` output as `_currentFiles` (D-02 says select-all is page-scoped, so range-select within the page is consistent); (b) cache `segmentedFiles$` for cross-page ranges. Per D-04 (selection clears on page change), option (a) is the safer default.

**Esc-to-clear keyboard handler** (file-list.component.ts lines 171-216 `@HostListener`):
```typescript
@HostListener("document:keydown", ["$event"])
onKeyDown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
        if (!this._isInputElement(event.target)) {
            this.fileSelectionService.clearSelection();
            this._lastClickedFileName = null;
        }
    }
}

private _isInputElement(target: EventTarget | null): boolean {
    if (!target) { return false; }
    const tagName = (target as HTMLElement).tagName?.toLowerCase();
    return tagName === "input" || tagName === "textarea" || tagName === "select";
}
```
Port Esc branch only (D-05: no arrow-keys, no Enter). Ctrl+A path is **not** required by D-05 either.

**Header checkbox state** (file-list.component.ts lines 52, 103-120):
```typescript
public headerCheckboxState$: Observable<"none" | "some" | "all">;
...
this.headerCheckboxState$ = combineLatest([
    this.files,
    this.fileSelectionService.selectedFiles$
]).pipe(
    map(([files, selectedFiles]) => {
        if (files.size === 0 || selectedFiles.size === 0) { return "none"; }
        const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;
        if (visibleSelectedCount === 0) { return "none"; }
        else if (visibleSelectedCount === files.size) { return "all"; }
        else { return "some"; }
    })
);
```
Adapt: replace `this.files` (Observable<List>) with a `pagedFiles$-as-List` stream — D-02 says header is "select all visible on the current page only". Current `pagedFiles$` emits `ViewFile[]` — either `.pipe(map(a => List(a)))` or inline-size-check the array.

**Header checkbox click** (file-list.component.ts lines 319-330):
```typescript
onHeaderCheckboxClick(files: List<ViewFile>): void {
    const selectedFiles = this.fileSelectionService.getSelectedFiles();
    const visibleSelectedCount = files.filter(f => f.name != null && selectedFiles.has(f.name)).size;
    if (visibleSelectedCount === files.size && files.size > 0) {
        this.fileSelectionService.clearSelection();
    } else {
        this.fileSelectionService.selectAllVisible(files.toArray());
    }
}
```
Port verbatim. For Phase 72, `files` here must be the **paged** list (D-02).

**Bulk action dispatchers** (file-list.component.ts lines 386-468) — need to port five handlers. For non-destructive actions (Queue/Stop/Extract), the existing pattern uses `BulkCommandService.executeBulkAction` (lines 480-538); D-16 also says action handlers dispatch via `ViewFileService` "the same ones `FileComponent` used to call" — either approach is valid but the `BulkCommandService` path is what `file-list.component.ts` currently uses for bulk and it already has race-condition locking, notifications, and partial-failure handling. Copy `_executeBulkAction` + `_handleBulkResult` + `_showNotification` verbatim (lines 480-591).

**Bulk delete confirmation** (file-list.component.ts lines 422-468 — demonstrates `ConfirmModalService` bulk pattern; also CONTEXT line 97 references `FileComponent:149-162` for single-file pattern):
```typescript
async onBulkDeleteLocal(fileNames: string[]): Promise<void> {
    const skipCount = this.fileSelectionService.getSelectedFiles().size - fileNames.length;
    const confirmed = await this.confirmModalService.confirm({
        title: Localization.Modal.BULK_DELETE_LOCAL_TITLE,
        body: Localization.Modal.BULK_DELETE_LOCAL_MESSAGE(fileNames.length),
        okBtn: "Delete",
        okBtnClass: "btn btn-outline-danger",
        skipCount: skipCount > 0 ? skipCount : undefined
    });
    if (confirmed) {
        this._executeBulkAction("delete_local", fileNames, {
            successMsg: Localization.Bulk.SUCCESS_DELETED_LOCAL,
            partialMsg: Localization.Bulk.PARTIAL_DELETED_LOCAL
        });
    }
}
```
Single-file fallback pattern (file.component.ts:149-162) if Claude chooses `.then()` style per D-18:
```typescript
showDeleteConfirmation(title: string, message: string, callback: () => void): void {
    this.confirmModal.confirm({
        title: title, body: message,
        okBtn: "Delete", okBtnClass: "btn btn-danger",
        cancelBtn: "Cancel", cancelBtnClass: "btn btn-secondary"
    }).then((confirmed) => { if (confirmed) { callback(); } });
}
```

**Constructor dependency injection** (file-list.component.ts lines 71-79): Add to `TransferTableComponent` constructor:
```typescript
public fileSelectionService: FileSelectionService,
private bulkCommandService: BulkCommandService,
private confirmModalService: ConfirmModalService,
private notificationService: NotificationService,
```

**Localization keys already exist** (verified in `src/angular/src/app/common/localization.ts`):
- `Localization.Modal.BULK_DELETE_LOCAL_TITLE`, `BULK_DELETE_LOCAL_MESSAGE(count)`
- `Localization.Modal.BULK_DELETE_REMOTE_TITLE`, `BULK_DELETE_REMOTE_MESSAGE(count)`
- `Localization.Bulk.SUCCESS_*`, `PARTIAL_*`, `ERROR`, `ERROR_RETRY`
- For D-17 "preview list" — Localization strings currently take a count-only argument. Claude's discretion allows extending them; simplest is to append a preview list to the `body` inline at the call site (truncate > N).

---

### `transfer-table.component.html` (container template) — WIRE BAR + HEADER CHECKBOX

**Analog A — bar wiring** (file-list.component.html lines 1-12):
```html
<app-bulk-actions-bar
    [visibleFiles]="vm.files!"
    [selectedFiles]="vm.selectedFiles ?? emptySet"
    [operationInProgress]="bulkOperationInProgress"
    (clearSelection)="onClearSelection()"
    (queueAction)="onBulkQueue($event)"
    (stopAction)="onBulkStop($event)"
    (extractAction)="onBulkExtract($event)"
    (deleteLocalAction)="onBulkDeleteLocal($event)"
    (deleteRemoteAction)="onBulkDeleteRemote($event)">
</app-bulk-actions-bar>
```
Insertion point (CONTEXT line 109): inside the transfer-card `<div>`, between the table (transfer-table.component.html line 125 `</div>`) and the pagination footer (line 129). The bar's `@if (hasSelection)` internal guard means it only renders when 1+ selected (D-09).

**`[visibleFiles]` binding:** must be `pagedFiles$ | async` converted to `List<ViewFile>` to match the `@Input() visibleFiles: List<ViewFile>` type. Cleanest: add a `pagedFilesList$` derived stream in the `.ts`:
```typescript
this.pagedFilesList$ = this.pagedFiles$.pipe(map(arr => List(arr)));
```

**Analog B — header checkbox `<th>`** (file-list.component.html lines 40-47 + Variant B line 174):
```html
<th class="col-checkbox">
    <input type="checkbox"
        [checked]="(headerCheckboxState$ | async) === 'all'"
        [indeterminate]="(headerCheckboxState$ | async) === 'some'"
        (click)="onHeaderCheckboxClick(vm.paged!)"
        aria-label="Select all visible files" />
</th>
```
Insertion point: as the FIRST `<th>` in the `<thead><tr>` (current transfer-table.component.html lines 104-113), before `<th class="col-name">`. `[indeterminate]` is Angular's standard Boolean property binding on `<input type="checkbox">` — no directive needed.

**Colspan bump** (current line 119): `<td colspan="6" ...>` → `<td colspan="7" ...>` after adding the checkbox column.

**Clear the `@if (hasSelection)` empty-state:** when 0 selected, the bar's internal `@if` hides it — the pagination footer alone shows (D-09). No template change needed beyond the bar's own guard.

---

### E2E tests — `dashboard.page.spec.ts` + `dashboard.page.ts`

**Analog A — current dashboard.page.ts** (lines 37-51) already uses the new-DOM selectors (`.transfer-table tbody app-transfer-row`, `td.cell-name .file-name`, `td.cell-size`). Extend by adding selectors for the new checkbox column and action bar buttons.

**Selector additions to write** (based on DOM decisions above):
- Row checkbox: `app-transfer-row td.cell-checkbox input[type="checkbox"]`
- Header "select all" checkbox: `.transfer-table thead input[type="checkbox"]`
- Action bar container: `app-bulk-actions-bar .bulk-actions-bar` (or new class after rename)
- "N selected" label: `app-bulk-actions-bar .selection-label` (or equivalent after rewrite)
- Clear link: `app-bulk-actions-bar button.clear-btn` (or equivalent)
- Per-button: identify by text content or data-action attribute; Variant B uses plain text, so Playwright `page.getByRole('button', {name: 'Queue'})` inside the bar is the cleanest analog.

**Analog B — spec.ts shape** (lines 37-56): the 5 `.skip()` blocks each have a descriptive `test.skip('should ...')`. For each, unskip and:
1. `test('should show and hide action buttons on select', ...)` — click row checkbox, assert bar visible; click again, assert bar hidden.
2. `test('should show action buttons for most recent file selected', ...)` — select 2+ rows, assert count label updates.
3. `test('should have all the action buttons', ...)` — count 5 `<button>` descendants of the bar (Queue, Stop, Extract, Delete Local, Delete Remote).
4. `test('should have Queue action enabled for Default state', ...)` — select a Default-status row, assert Queue button `[disabled]=false`.
5. `test('should have Stop action disabled for Default state', ...)` — same, assert Stop `[disabled]=true`.

**Page-object method additions (sketch):**
```typescript
async selectFileByName(name: string) {
    const row = this.page.locator('app-transfer-row', { hasText: name });
    await row.locator('input[type="checkbox"]').click();
}
async getActionBar() { return this.page.locator('app-bulk-actions-bar'); }
async getActionButton(name: 'Queue' | 'Stop' | 'Extract' | 'Delete Local' | 'Delete Remote') {
    return this.page.locator('app-bulk-actions-bar').getByRole('button', { name });
}
```

**No new E2E tests beyond the 5 originals** — D-19 explicit.

---

## Shared Patterns

### Authentication / Guard
**Not applicable** — this is a pure Angular front-end phase with no new controllers, routes, or backend endpoints (CONTEXT D-16: reuses existing `ViewFileService` + `BulkCommandService` action APIs).

### OnPush Change Detection
**Source:** `transfer-row.component.ts:15`, `transfer-table.component.ts:20`, `file.component.ts:35`, `file-list.component.ts:33`, `bulk-actions-bar.component.ts:33`.
**Apply to:** All new/modified components.
```typescript
changeDetection: ChangeDetectionStrategy.OnPush,
standalone: true,
```

### Subscription Cleanup
**Source:** `transfer-table.component.ts:41,95,105` + `file-list.component.ts:44,94,124`.
**Apply to:** All new RxJS subscriptions in `TransferTableComponent`.
```typescript
private destroyRef = inject(DestroyRef);
...
observable$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(...);
```
Part of CONTEXT "Established Patterns" line 103.

### Signal-Based Row Selection (M007)
**Source:** `file.component.ts:57-58,95-101` + `file-selection.service.ts:36,139-145` (toggle), 185-196 (setSelection for ranges), 175-179 (clearSelection).
**Apply to:** `TransferRowComponent.isSelected` + `TransferTableComponent.onCheckboxToggle`. No `@Input() bulkSelected` — use `inject(FileSelectionService)` + `computed()` instead (CONTEXT line 102).

### Click Stop-Propagation on Checkbox Cell
**Source:** `click-stop-propagation.directive.ts` (the entire 12-line directive) + `file.component.html:12`.
**Apply to:** `transfer-row.component.html` checkbox `<td>` (prevents the row-level click from firing when the checkbox is toggled).
```typescript
// In directive:
@HostListener("click", ["$event"])
public onClick(event: Event): void { event.stopPropagation(); }
```
Already standalone and importable.

### ConfirmModalService Call Pattern
**Source (single-file `.then` pattern):** `file.component.ts:149-162`.
**Source (bulk `await + skipCount` pattern):** `file-list.component.ts:422-442` (delete-local) and 448-468 (delete-remote).
**Apply to:** `TransferTableComponent.onBulkDeleteLocal` / `onBulkDeleteRemote`.
Per D-18 Claude's discretion: either pattern is acceptable — prefer the `async/await + skipCount` version as it already matches the multi-file case this phase targets.
`ConfirmModalOptions` interface (confirm-modal.service.ts:3-11) supports `skipCount?: number` for the "N files will be skipped (not eligible)" line.

### BulkCommandService `_executeBulkAction` Wrapper
**Source:** `file-list.component.ts:480-538`.
**Apply to:** `TransferTableComponent` bulk handlers for all 5 actions.
Includes: `beginOperation()` lock, `bulkOperationInProgress` flag + `markForCheck()`, response-result unpacking, error-branch with transient-vs-validation distinction, `endOperation()` lock release, `clearSelection()` + `_lastClickedFileName = null` after success.

### Localization Constants
**Source:** `src/angular/src/app/common/localization.ts` lines 22-40+ (already contains all titles and `BULK_*` message factories).
**Apply to:** All modal titles and bulk success/partial notification messages.

### Design-Spec Rigor — Literal Hex Port
**Source:** `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md` + CONTEXT lines 79-83 palette tokens + `transfer-row.component.scss:36-66,91-126` (example of literal hex values in SCSS, no CSS variables, `@use '../../common/common' as *;` header convention).
**Apply to:** `bulk-actions-bar.component.scss` rewrite + `transfer-row.component.scss` additions. Every value from Variant B's Tailwind classes maps to a literal hex value in SCSS per project convention.

### Icon Mapping (Phosphor → Font Awesome 4.7)
**Source:** CONTEXT line 87 — "Variant B uses Phosphor icons in small roles, map to equivalent Font Awesome 4.7 glyphs per memory." Existing FA usage in `transfer-table.component.html:13,33-35,72-75` (`fa fa-search`, `ph-bold ph-caret-down` — note: the project currently mixes `ph-bold` and `fa fa-*`; Claude's discretion which to use).
**Apply to:** All Variant B icons in the action bar template rewrite.
Suggested mappings:
- `ph-play` → `fa fa-play`
- `ph-stop` → `fa fa-stop`
- `ph-archive` → `fa fa-file-archive-o` (FA4.7) or `fa fa-archive`
- `ph-trash` → `fa fa-trash` (or `fa fa-trash-o`)
- `ph-cloud-slash` → `fa fa-cloud` with a CSS strikethrough, or `fa fa-cloud` + an adjacent `fa fa-ban`

---

## No Analog Found

None. Every file to modify has a strong in-codebase analog. The closest-to-risky is the "bulk delete modal preview list" (D-17) since existing `BULK_DELETE_*_MESSAGE` localization takes only a count — but this is an additive template-string change, not a missing-analog problem.

## Metadata

**Analog search scope:**
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/pages/files/` (all components)
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/files/` (selection, view-file)
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/utils/confirm-modal.service.ts`
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/server/bulk-command.service.ts`
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/common/click-stop-propagation.directive.ts`
- `/Users/julianamacbook/seedsyncarr/src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts`
- `/Users/julianamacbook/seedsyncarr/src/e2e/tests/dashboard.page.*`
- `/Users/julianamacbook/seedsyncarr/.planning/phases/72-restore-dashboard-file-selection-and-action-bar/variant-B-card-internal-bar.html`

**Files scanned:** 18 source files, 1 spec file, 2 E2E files, 1 design HTML, 1 localization file.

**Pattern extraction date:** 2026-04-19

