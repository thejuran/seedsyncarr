# Phase 70: Drilldown Segment Filters — Research

**Researched:** 2026-04-15
**Domain:** Angular 21 component state management, inline segment filter UI
**Confidence:** HIGH

---

## Summary

Phase 70 replaces the flat three-button segment filter (All / Active / Errors) in `TransferTableComponent` with a two-level drill-down. Clicking Active or Errors expands inline sub-buttons for individual statuses; clicking the same parent again collapses back to All. The design is fully specified — pixel-exact mockup at `/private/tmp/filter-mockup.html` (AIDesigner run `16d38a0c`) and a complete behavior matrix in `docs/superpowers/specs/2026-04-15-drilldown-segment-filters-design.md`.

The implementation touches exactly three files in `src/angular/src/app/pages/files/`:
- `transfer-table.component.ts` — state fields + filtering logic
- `transfer-table.component.html` — conditional sub-button rendering
- `transfer-table.component.scss` — new CSS modifier classes

No new components, services, dependencies, or routes are needed. The existing RxJS `BehaviorSubject`/`combineLatest` pipeline in the component already handles filter reactivity; the change is purely additive state and view logic inside the existing architecture.

**Primary recommendation:** Add `activeSubStatus: ViewFile.Status | null = null` alongside the existing `activeSegment`, update `onSegmentChange()` to toggle-collapse behavior, add `onSubStatusChange()`, widen the `filterState$` BehaviorSubject type to carry the sub-status, and port the three visual states from the mockup into SCSS modifier classes.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-DRILL-01 | Replace flat All/Active/Errors segment filter with two-level drill-down: clicking Active or Errors expands inline sub-buttons for individual statuses (Syncing/Queued/Extracting and Failed/Deleted) | Full design spec + mockup available; component architecture and data model confirmed; implementation path is purely additive within the existing component |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Filter state (activeSegment + activeSubStatus) | Browser / Client | — | Pure UI state in Angular component; no server round-trip |
| Filtering pipeline (segmentedFiles$) | Browser / Client | — | Reactive RxJS pipeline already in TransferTableComponent; sub-status filter is an additional map stage |
| Sub-button rendering | Browser / Client | — | `@if` blocks in Angular template driven by component state |
| Visual styling (pill track, divider, accent dot) | Browser / Client | — | Component-scoped SCSS; all tokens already defined in existing component |

---

## Standard Stack

### Core (already in project — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | 21.2.8 | Component framework, `@if` control flow, async pipe | [VERIFIED: package.json] |
| RxJS | (Angular-bundled) | `BehaviorSubject`, `combineLatest`, `distinctUntilChanged` | [VERIFIED: existing component source] |
| Phosphor Icons | CDN (@phosphor-icons/web) | `ph-bold ph-caret-down` / `ph-caret-up` chevrons | [VERIFIED: src/angular/src/index.html + mockup] |
| Immutable.js | (existing dep) | `ViewFile` record, `.filter()`, `.toList()`, `.size` | [VERIFIED: existing component source] |
| Jasmine + Karma | jasmine-core 6.1, `ng test` | Unit testing | [VERIFIED: package.json, karma.conf.js] |

**Installation:** None — all dependencies are already present.

---

## Architecture Patterns

### System Architecture Diagram

```
User click (segment button / sub-button)
        |
        v
onSegmentChange(seg) or onSubStatusChange(status)
        |
        v
Update component fields:
  activeSegment: "all" | "active" | "errors"
  activeSubStatus: ViewFile.Status | null
        |
        v
filterState$.next({ segment, subStatus, page: 1 })
        |
        v
segmentedFiles$ (combineLatest)
  |-- if subStatus != null  -> filter to single status
  |-- elif segment="active" -> filter DOWNLOADING | QUEUED | EXTRACTING
  |-- elif segment="errors" -> filter STOPPED | DELETED
  |-- else                  -> return all files
        |
        v
pagedFiles$ slices segmentedFiles$ by page
        |
        v
Template re-renders: pill track shows correct visual state
```

### Recommended Project Structure

No structural changes. All edits are in the existing three files:

```
src/angular/src/app/pages/files/
├── transfer-table.component.ts   # state + filter logic changes
├── transfer-table.component.html # drill-down template additions
└── transfer-table.component.scss # new SCSS modifier classes
```

### Pattern 1: Richer filterState$ BehaviorSubject

**What:** Widen the existing `filterState$` type to include `subStatus`.
**When to use:** Whenever sub-status changes should trigger page reset and pipeline re-evaluation in one atomic emission.

```typescript
// Source: existing component pattern, widened
private filterState$ = new BehaviorSubject<{
    segment: "all" | "active" | "errors";
    subStatus: ViewFile.Status | null;
    page: number;
}>({ segment: "all", subStatus: null, page: 1 });
```

The `segmentedFiles$` pipeline then reads `state.subStatus` before falling through to the segment-group logic:

```typescript
map(([files, state]) => {
    if (state.subStatus != null) {
        return files.filter(f => f.status === state.subStatus).toList();
    }
    if (state.segment === "active") {
        return files.filter(f =>
            f.status === ViewFile.Status.DOWNLOADING ||
            f.status === ViewFile.Status.QUEUED ||
            f.status === ViewFile.Status.EXTRACTING
        ).toList();
    }
    if (state.segment === "errors") {
        return files.filter(f =>
            f.status === ViewFile.Status.STOPPED ||
            f.status === ViewFile.Status.DELETED
        ).toList();
    }
    return files;
})
```

Note: `segmentedFiles$` currently uses `distinctUntilChanged()` on only the `segment` field. With `subStatus` added, the distinct guard must cover both fields, or be removed from the inner pipe and placed on the combined observable with a custom comparator. The simplest approach is to remove the inner `distinctUntilChanged()` and rely on the BehaviorSubject emitting only on actual state changes (which `onSegmentChange` and `onSubStatusChange` already ensure).

### Pattern 2: Toggle-collapse onSegmentChange

**What:** Clicking an already-active parent segment collapses back to All (instead of the old no-op).

```typescript
onSegmentChange(segment: "all" | "active" | "errors"): void {
    if (segment !== "all" && this.activeSegment === segment) {
        // Second click on same expandable parent — collapse to All
        this.activeSegment = "all";
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({ segment: "all", subStatus: null, page: 1 });
    } else {
        this.activeSegment = segment;
        this.activeSubStatus = null;
        this.currentPage = 1;
        this.filterState$.next({ segment, subStatus: null, page: 1 });
    }
}
```

### Pattern 3: onSubStatusChange

**What:** New handler for sub-button clicks; switches sub-selection within the currently-expanded parent.

```typescript
onSubStatusChange(status: ViewFile.Status): void {
    this.activeSubStatus = status;
    this.currentPage = 1;
    this.filterState$.next({
        segment: this.activeSegment,
        subStatus: status,
        page: 1
    });
}
```

### Pattern 4: Template — @if drill-down expansion

**What:** Conditionally render divider + sub-buttons after the parent button using Angular 17+ `@if` control flow (already used in this template).

```html
<!-- Active parent button -->
<button type="button" class="btn-segment"
    [class.btn-segment--parent-active]="activeSegment === 'active' && activeSubStatus === null"
    [class.btn-segment--parent-expanded]="activeSegment === 'active' && activeSubStatus !== null"
    (click)="onSegmentChange('active')">
  Active
  <i class="ph-bold"
     [class.ph-caret-down]="activeSegment !== 'active'"
     [class.ph-caret-up]="activeSegment === 'active'"></i>
</button>

@if (activeSegment === 'active') {
  <div class="segment-divider"></div>
  <button type="button" class="btn-sub"
      [class.active]="activeSubStatus === ViewFileStatus.DOWNLOADING"
      (click)="onSubStatusChange(ViewFileStatus.DOWNLOADING)">
    @if (activeSubStatus === ViewFileStatus.DOWNLOADING) {
      <span class="accent-dot"></span>
    }
    Syncing
  </button>
  <button type="button" class="btn-sub"
      [class.active]="activeSubStatus === ViewFileStatus.QUEUED"
      (click)="onSubStatusChange(ViewFileStatus.QUEUED)">
    @if (activeSubStatus === ViewFileStatus.QUEUED) {
      <span class="accent-dot"></span>
    }
    Queued
  </button>
  <button type="button" class="btn-sub"
      [class.active]="activeSubStatus === ViewFileStatus.EXTRACTING"
      (click)="onSubStatusChange(ViewFileStatus.EXTRACTING)">
    @if (activeSubStatus === ViewFileStatus.EXTRACTING) {
      <span class="accent-dot"></span>
    }
    Extracting
  </button>
}
```

To expose `ViewFile.Status` enum values in the template, add a getter or class field:

```typescript
readonly ViewFileStatus = ViewFile.Status;
```

This is the standard Angular pattern for using namespace enums in templates — they cannot be referenced directly without a class-level alias. [ASSUMED — standard Angular pattern, consistent with how the project currently uses ViewFile.Status inside the TS class]

### Pattern 5: SCSS modifier classes

**What:** New classes layered on the existing `.btn-segment` and `.segment-filters` blocks. Do NOT replace the existing `.btn-segment.active` rule — it is still used by the All button.

```scss
// Expanded parent — sub-status IS selected: lighter bg, no border, amber chevron
.btn-segment--parent-expanded {
  background: rgba(34, 42, 32, 0.6);
  border: 1px solid transparent;
  color: #e0e8d6;
}

// Expanded parent — no sub-selection: full active treatment + chevron up
.btn-segment--parent-active {
  background: #222a20;
  border: 1px solid #3e4a38;
  color: #e0e8d6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

// Thin vertical separator between parent and children
.segment-divider {
  width: 1px;
  height: 14px;
  background: rgba(62, 74, 56, 0.6);
  flex-shrink: 0;
}

// Sub-button base
.btn-sub {
  background: transparent;
  border: 1px solid transparent;
  color: #7d8c6d;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  gap: 6px;

  &:hover {
    color: #e0e8d6;
    background: rgba(34, 42, 32, 0.4);
  }

  &.active {
    background: #222a20;
    border: 1px solid #3e4a38;
    color: #c49a4a;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
  }
}

// Amber accent dot with glow (shown only in active sub-button)
.accent-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c49a4a;
  box-shadow: 0 0 6px 1px rgba(196, 154, 74, 0.3);
  flex-shrink: 0;
}
```

### Anti-Patterns to Avoid

- **Removing `.btn-segment.active`:** The All button still uses this class verbatim. Only Active/Errors get the new modifier classes.
- **Touching filterState$ type without updating all consumers:** `pagedFiles$`, `totalPages$`, and `totalCount$` all read from `filterState$`. Adding `subStatus` to the type requires confirming these pipelines still compile — they only use `state.page` and `state.segment`, so they remain compatible once the BehaviorSubject type is widened.
- **Using `*ngIf` instead of `@if`:** The template already uses Angular 17+ control flow syntax (`@if`, `@for`). Keep consistent — use `@if`.
- **Referencing `ViewFile.Status` directly in the template** without a class-level alias — Angular templates cannot access TypeScript namespace members directly.
- **Leaving `pointer-events: none` on parent button when sub-buttons are visible:** The current `.btn-segment.active` rule sets `pointer-events: none`. The new modifier classes must NOT set this, because the parent button must remain clickable for collapse behavior.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chevron icon | Custom SVG or CSS triangle | `ph-bold ph-caret-down` / `ph-caret-up` | Phosphor already loaded via CDN in index.html; used in about-page and settings-page |
| Reactive filter pipeline | Manual subscription + imperative array mutation | Existing `combineLatest` / `BehaviorSubject` pattern | Already handles page reset, pagination, and change detection correctly |
| Animation on expand | CSS transition or Angular Animations | None — spec says instant show/hide | Design spec explicitly excludes animation |

---

## Visual Design Reference

All three pixel-exact states are defined in the mockup at `/private/tmp/filter-mockup.html`.

### State 1: Default (All selected)
- Pill: `bg #151a14`, `padding 2px`, `border 1px solid rgba(62,74,56,0.3)`, `border-radius 6px`, `box-shadow: inset 0 1px 3px rgba(0,0,0,0.4)`
- All button: active treatment (`bg #222a20`, `border #3e4a38`, `color #e0e8d6`, `shadow 0 2px 4px rgba(0,0,0,0.25)`)
- Active / Errors buttons: `color #9aaa8a`, chevron-down at 50% opacity (100% on hover)
- Button height: `28px`; parent padding: `4px 12px`

### State 2: Active expanded + sub-status selected (Syncing shown)
- Active parent: `bg rgba(34,42,32,0.6)`, `border transparent`, chevron-up in amber `#c49a4a`
- Divider: `w 1px h 14px bg rgba(62,74,56,0.6)`
- Syncing (active sub): `bg #222a20 border #3e4a38 color #c49a4a shadow 0 2px 4px rgba(0,0,0,0.25)`, amber dot with glow
- Queued / Extracting (inactive subs): `color #7d8c6d`, hover `color #e0e8d6 bg rgba(34,42,32,0.4)`
- Errors button: unchanged from default (chevron-down, `color #9aaa8a`)

### State 3: Errors expanded, no sub-selection
- All / Active: inactive style (`color #9aaa8a`)
- Errors parent: full active treatment + chevron-up in `#e0e8d6` (NOT amber — no sub selected)
- Divider after Errors parent
- Failed / Deleted: inactive sub-button style (`color #7d8c6d`)

**Key visual difference between State 2 and State 3 parent treatment:**
- State 2 parent (sub selected): `bg rgba(34,42,32,0.6)` + `border transparent` + amber chevron
- State 3 parent (no sub): `bg #222a20` + `border #3e4a38` + white chevron + shadow (same as All active)

This is the most subtle distinction. The SCSS modifier classes encode it:
- `.btn-segment--parent-active` = full active treatment (State 3 parent)
- `.btn-segment--parent-expanded` = lighter treatment (State 2 parent)

---

## Status-to-Label Mapping

[VERIFIED: design spec + view-file.ts enum]

| ViewFile.Status | Enum Value | Sub-button label | Parent segment |
|-----------------|-----------|-----------------|----------------|
| DOWNLOADING | `"downloading"` | Syncing | Active |
| QUEUED | `"queued"` | Queued | Active |
| EXTRACTING | `"extracting"` | Extracting | Active |
| STOPPED | `"stopped"` | Failed | Errors |
| DELETED | `"deleted"` | Deleted | Errors |

---

## Common Pitfalls

### Pitfall 1: filterState$ type mismatch after BehaviorSubject widening

**What goes wrong:** The type of `filterState$` is used in three pipeline subscriptions. If the initial value shape doesn't match the new type, TypeScript will error at the `new BehaviorSubject(...)` call site.
**Why it happens:** The initial value `{segment: "all", page: 1}` must be updated to `{segment: "all", subStatus: null, page: 1}`.
**How to avoid:** Update the BehaviorSubject initial value and the type annotation together.
**Warning signs:** TS2345 type error on the BehaviorSubject constructor.

### Pitfall 2: `pointer-events: none` blocking parent collapse click

**What goes wrong:** The current `.btn-segment.active` rule disables pointer events on the active button. If any code path sets the `active` class on the parent button while it is expanded, the collapse click will be silently swallowed.
**Why it happens:** The `active` class is reused from the All button pattern. The new parent button states use different CSS classes (`.btn-segment--parent-active`, `.btn-segment--parent-expanded`) specifically to avoid this.
**How to avoid:** Never bind `[class.active]="activeSegment === 'active'"` on the Active/Errors parent buttons. Bind the new modifier classes instead.
**Warning signs:** Clicking the expanded Active/Errors parent does nothing — no state change observable in console.

### Pitfall 3: distinctUntilChanged on segment-only drops sub-status changes

**What goes wrong:** The current `segmentedFiles$` pipeline applies `distinctUntilChanged()` to just the `segment` field before combining. Once `subStatus` is part of the state, clicking different sub-buttons while staying on the same segment emits the same `segment` value — so `distinctUntilChanged` suppresses the re-filter.
**Why it happens:** The optimization was written for a world where segment was the only filter dimension.
**How to avoid:** Either remove the `distinctUntilChanged()` from the inner `map(s => s.segment)` pipe, or replace it with a custom comparator that checks both `segment` and `subStatus`. Removing it is simpler — the BehaviorSubject only emits when `onSegmentChange` or `onSubStatusChange` is called, so there is no spurious re-computation risk.
**Warning signs:** Switching from Syncing to Queued shows no change in the table.

### Pitfall 4: ViewFile.Status enum not accessible in template

**What goes wrong:** Template binding `[class.active]="activeSubStatus === ViewFile.Status.DOWNLOADING"` fails at runtime — Angular templates cannot traverse TypeScript namespace paths.
**Why it happens:** `ViewFile.Status` is a namespace enum, not a top-level export accessible to templates.
**How to avoid:** Add `readonly ViewFileStatus = ViewFile.Status;` as a class field and reference `ViewFileStatus.DOWNLOADING` in the template.
**Warning signs:** Angular compile error or `undefined` comparison that always resolves false.

### Pitfall 5: Accent dot visible in non-active sub-buttons

**What goes wrong:** The `.accent-dot` span renders in all sub-buttons instead of only the active one.
**Why it happens:** Placing the dot in SCSS as a pseudo-element on `.btn-sub.active::before` adds it automatically, but if the span is placed unconditionally in the HTML it appears in all.
**How to avoid:** Wrap the `<span class="accent-dot">` in `@if (activeSubStatus === ViewFileStatus.X)`, or use the CSS `::before` pseudo-element approach on `.btn-sub.active` only (no span in HTML). Either is correct — the SCSS pseudo-element approach is simpler.

---

## Code Examples

### Verified token values [VERIFIED: mockup HTML + design spec]

```scss
// Pill container
background: #151a14;
padding: 2px;
border-radius: 6px; // mockup uses rounded-[6px], spec says 4px — mockup wins per project convention
border: 1px solid rgba(62, 74, 56, 0.3);
box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);

// Button height shared across all segments
height: 28px;

// Chevron icon
font-size: 10px;
margin-left: 6px;
```

Note: The design spec states `border-radius: 4px` for buttons but `6px` is shown in the mockup for the pill container. Per project memory ("Port AIDesigner HTML identically, no approximations"), the mockup value (`6px` for pill, `4px` for buttons) is authoritative.

---

## Existing Test Spec Impact

[VERIFIED: transfer-table.component.spec.ts]

The existing spec at `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts`:

- Uses a `TEST_TEMPLATE` override that only has three `.btn-segment` buttons with no sub-buttons
- The test `"should render 3 segment filter buttons"` asserts exactly 3 buttons — this test will need to be updated because the new template has 3 parent buttons + conditional sub-buttons
- Tests for `onSegmentChange()` behavior still pass as-is (the method still accepts "all" / "active" / "errors")
- The `"should set activeSegment when segment button clicked"` test will need updating because clicking active when already active now collapses to "all" (toggle behavior)

New unit tests needed per design spec:
1. Sub-status filter — each of the 5 sub-statuses returns only matching files
2. Switching sub-status within same parent segment
3. Clicking parent when expanded collapses to All + clears subStatus
4. Switching parent segment clears subStatus
5. `"should render 3 segment filter buttons"` — update to cover new template shape

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Jasmine 6.1 + Karma |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && ng test --include="**/transfer-table.component.spec.ts" --watch=false` |
| Full suite command | `cd src/angular && ng test --watch=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-DRILL-01 | Sub-status filter returns only matching status | unit | `ng test --include="**/transfer-table.component.spec.ts" --watch=false` | Yes (needs new cases) |
| UI-DRILL-01 | Toggle-collapse: clicking active parent collapses to All | unit | same | Yes (needs update) |
| UI-DRILL-01 | Switching segment clears subStatus | unit | same | Yes (needs new case) |
| UI-DRILL-01 | Switching sub-status within same parent | unit | same | Yes (needs new case) |

### Wave 0 Gaps

- [ ] Existing test case `"should render 3 segment filter buttons"` — assertion must change (3 parent buttons + conditional subs)
- [ ] Existing test case `"should set activeSegment when segment button clicked"` — toggle-collapse behavior is new
- [ ] New test case: each of 5 sub-statuses filters correctly
- [ ] New test case: switching sub-status within same segment
- [ ] New test case: segment switch clears sub-status
- [ ] `TEST_TEMPLATE` in spec — update to include sub-button structure so template-level tests remain valid

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | Filter state is entirely enum-typed (ViewFile.Status) — no user string input reaches filter logic |
| All others | no | Pure client-side UI state; no network calls, no authentication, no cryptography |

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely client-side code changes with no external service dependencies beyond the existing Angular CLI build toolchain.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a greenfield UI addition, not a rename/refactor/migration phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `readonly ViewFileStatus = ViewFile.Status;` is the standard Angular pattern for exposing namespace enums in templates | Architecture Patterns, Pitfall 4 | Low — if wrong, alternative is to expose individual enum values as properties; no functional impact |
| A2 | Removing `distinctUntilChanged()` from the inner segment pipe will not cause performance issues at typical file list sizes | Common Pitfalls #3 | Low — BehaviorSubject only emits on explicit user interaction; re-filter on 15-page lists is trivial |

---

## Open Questions

1. **Pill container border-radius: 4px (spec) vs 6px (mockup)**
   - What we know: Design spec states `border-radius: 4px`, mockup uses `rounded-[6px]` (Tailwind = 6px). Project memory says "Port AIDesigner HTML identically."
   - What's unclear: Which is authoritative for the pill container (individual buttons are 4px in both).
   - Recommendation: Use 6px for the pill container (`segment-filters`) and 4px for buttons, matching the mockup exactly. The existing `.segment-filters` rule uses `border-radius: 4px` — update it to `6px`.

2. **`pointer-events: none` on `.btn-segment.active`**
   - What we know: The current SCSS has `pointer-events: none` on `.btn-segment.active` — this was fine for the old flat filter where clicking the active button was a no-op.
   - What's unclear: The design implies the parent button remains clickable for collapse. The new modifier classes sidestep this, but the existing `active` class is still applied to the All button.
   - Recommendation: Keep `pointer-events: none` on `.btn-segment.active` (All button behavior unchanged). The Active/Errors parent buttons must never receive the `active` class — only the new modifier classes.

---

## Sources

### Primary (HIGH confidence)
- `/private/tmp/filter-mockup.html` — AIDesigner run 16d38a0c, pixel-exact reference for all three visual states [VERIFIED: read in session]
- `docs/superpowers/specs/2026-04-15-drilldown-segment-filters-design.md` — complete behavior matrix, state transitions, token table, architecture guidance [VERIFIED: read in session]
- `src/angular/src/app/pages/files/transfer-table.component.ts` — current component implementation [VERIFIED: read in session]
- `src/angular/src/app/pages/files/transfer-table.component.html` — current template [VERIFIED: read in session]
- `src/angular/src/app/pages/files/transfer-table.component.scss` — current styles + existing tokens [VERIFIED: read in session]
- `src/angular/src/app/services/files/view-file.ts` — ViewFile.Status enum values [VERIFIED: read in session]
- `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` — existing test cases [VERIFIED: read in session]
- `src/angular/src/index.html` — Phosphor Icons CDN confirmed [VERIFIED: grep in session]

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — project stack confirmed: Angular 21 + Bootstrap 5 + SCSS, no Tailwind [VERIFIED: read in session]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and existing source
- Architecture: HIGH — design spec is complete with exact TypeScript field names and data flow diagram
- Visual tokens: HIGH — verified from both design spec and pixel-exact mockup HTML
- Pitfalls: HIGH — derived from direct inspection of existing component code
- Test coverage gaps: HIGH — spec file read directly

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable Angular 21 component patterns)
