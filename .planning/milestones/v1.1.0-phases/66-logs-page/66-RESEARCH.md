# Phase 66: Logs Page - Research

**Researched:** 2026-04-14
**Domain:** Angular 21 terminal-style log viewer, client-side filtering, array accumulation, SCSS custom properties
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Pixel-exact match to the AIDesigner mockup. Dark terminal background (`#0a0d09` / `seed-term`), monospace font, full-viewport height. Terminal area is a flex-1 container with `overflow-y: auto` and custom scrollbar styling.

**D-02:** Sequential line numbers in a fixed-width gutter column (left-aligned, muted `textsec/30` color, `border-r border-seed-border/30`). Numbers reset when logs are cleared. Each row is a flex container: `[line-num | timestamp | level-badge | message]`.

**D-03:** ERROR rows get red tinted background (`bg-error/10`) with top/bottom border (`border-y border-seed-error/20`). ERROR level badge is filled pill (`bg-seed-error text-white px-1.5 py-0.5 rounded text-[10px] font-bold`). Error message text is `#ff8e8e`.

**D-04:** WARN rows get warning-tinted background on hover (`hover:bg-seed-warning/10`). WARN text and timestamp tinted warning color.

**D-05:** DEBUG entries use dimmed text (`textsec/50` for level, `textsec/70` for message). INFO entries use green-bold level badge (`text-seed-success font-bold`) and standard text color for message.

**D-06:** Timestamps displayed in `HH:MM:SS.mmm` format in amber/70 color. Row hover effect: `hover:bg-seed-row/80`.

**D-07:** Bottom gradient fade on the terminal viewport (`h-8 bg-gradient-to-t from-seed-term to-transparent pointer-events-none`).

**D-08:** Sticky card-styled toolbar above the terminal viewport: `bg-seed-card border border-seed-border rounded-md p-2.5` with `flex-wrap items-center justify-between`. Contains level filter (left) and action buttons (right).

**D-09:** Segmented button group for level filtering: ALL / INFO / WARN / ERROR / DEBUG. Container: `bg-seed-base rounded-md p-1 border border-seed-border`. Active button: `bg-seed-amber text-seed-base shadow`. Inactive buttons use level-specific text colors.

**D-10:** Level mapping: ALL = show all. INFO = `LogRecord.Level.INFO` only. WARN = `LogRecord.Level.WARNING` only. ERROR = `LogRecord.Level.ERROR + LogRecord.Level.CRITICAL`. DEBUG = `LogRecord.Level.DEBUG` only.

**D-11:** Regex search field with FA 4.7 `fa-search` icon (left). Placeholder: "Grep logs (regex supported)...". Focus state: `border-seed-amber ring-1 ring-seed-amber`. Width ~320px. Real-time filtering (~200ms debounce).

**D-12:** Auto-scroll toggle: FA 4.7 `fa-check-circle` (green) + "Auto-scroll" when ON; `fa-circle-o` dimmed when OFF. Default ON. Manual scroll up disables it. New log while OFF does not scroll.

**D-13:** Clear button: `fa-trash` + "Clear". Export button: `fa-download` + "Export .log". Vertical divider separates auto-scroll from clear/export.

**D-14:** Fixed footer: `bg-seed-base border-t border-seed-border px-6 py-2` flex justify-between. Text: `text-xs text-seed-textsec`.

**D-15:** Left footer: green pulsing dot + "Connected to active seedbox daemon". Disconnected: red dot (no pulse) + "Disconnected — waiting for connection". Source: `ConnectedService.connected` Observable.

**D-16:** Right footer: log count ("N logs indexed") + `fa-clock-o` icon + "LAST UPDATED: HH:MM:SS AM/PM" uppercase tracking. Count updates in real time.

**D-17:** No ping display — outside scope.

**D-18:** Switch from ViewContainerRef template insertion to array-based accumulation (`scan` pattern from DashboardLogPaneComponent). 5000-record cap from LogService.

**D-19:** Level filter and regex search are client-side array filters. No debounce on level buttons; ~200ms debounce on search input.

**D-20:** Clear button clears component display array and resets line counter. LogService ReplaySubject buffer is NOT flushed. Cleared state persists within the component.

**D-21:** Export produces a plain text `.log` file download. Format: `YYYY/MM/DD HH:MM:SS - LEVEL - loggerName - message`. Exports currently visible (filtered) entries only. Uses Blob + URL.createObjectURL + anchor download link pattern.

### Claude's Discretion
- Exact responsive breakpoint behavior for toolbar wrapping on mobile
- Custom scrollbar CSS specifics (webkit-scrollbar styling from mockup as reference)
- Debounce timing on regex search input
- Whether to use Angular's `trackBy` or other optimization for the log list rendering
- Transition animations on filter/clear state changes
- Keyboard shortcuts for toolbar actions (if any)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOGS-01 | Log level filter as segmented button group (ALL/INFO/WARN/ERROR/DEBUG) | D-09, D-10 — client-side filter against `allLogs` array; active state toggle with amber bg |
| LOGS-02 | Search field with regex support for filtering log entries | D-11, D-19 — `Subject<string>` + `debounceTime(200)` + `new RegExp(query)` filter; display regex error state |
| LOGS-03 | Auto-scroll toggle, clear, and export .log action buttons | D-12, D-13, D-20, D-21 — scroll detection via ElementRef + ViewChild; Blob export |
| LOGS-04 | Status bar footer showing connection status, log count, last updated | D-14, D-15, D-16 — `ConnectedService.connected`, `allLogs.length`, `Date` formatted as HH:MM:SS AM/PM |

</phase_requirements>

---

## Summary

Phase 66 is a complete rewrite of `LogsPageComponent` — replacing the old ViewContainerRef/template-insertion pattern with a fully redesigned terminal-style log viewer. The design target is the AIDesigner mockup at `.aidesigner/runs/2026-04-14T03-35-39-500Z-seedsyncarr-logs-page-triggarr-style/design.html`.

The three-part architecture (toolbar, terminal viewport, status bar footer) maps cleanly to the existing component file set. The data layer is already production-ready: `LogService` provides a hot `ReplaySubject(5000)` observable and `ConnectedService` provides `connected: Observable<boolean>`. The reference implementation pattern (`DashboardLogPaneComponent`) shows the exact `scan` + `debounceTime` accumulation pattern to reuse.

The primary technical challenges are: (1) translating Tailwind alpha/opacity shorthands from the mockup into Bootstrap 5 + SCSS equivalents using CSS custom properties and `rgba()`; (2) implementing the auto-scroll toggle with correct manual-scroll detection; (3) safely constructing `RegExp` objects from user input without crashing on invalid patterns.

**Primary recommendation:** Complete rewrite of all three files (`logs-page.component.ts`, `.html`, `.scss`). Wire `LogService.logs` through `scan` into `allLogs[]`, derive `filteredLogs[]` as a computed getter. The status bar uses `ConnectedService` and a `Date` timer. Export uses the Blob/anchor pattern already proven in the codebase.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | 21 | Component framework | Project standard — standalone components, OnPush, DestroyRef |
| RxJS | (project version) | Reactive data streams | `scan`, `debounceTime`, `Subject` — all used in existing code |
| Bootstrap 5 | (project version) | Base layout utilities | Project standard — flex, border, padding utilities |
| Font Awesome 4.7 | CDN | Icons (`fa-search`, `fa-check-circle`, `fa-circle-o`, `fa-trash`, `fa-download`, `fa-clock-o`) | Project constraint — Phase 65 CONTEXT confirmed FA 4.7 only |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Angular `FormsModule` | — | `[(ngModel)]` on search input | Only if two-way binding chosen over Subject approach |
| Immutable.js `LogRecord` | — | Immutable log record type | Already in use — no change needed |

### No Additions Needed
This phase requires zero new npm packages. All required libraries are already installed and in use.

---

## Architecture Patterns

### Component Structure (after rewrite)

```
LogsPageComponent
  ├── allLogs: LogRecord[]            — accumulated buffer (max 5000)
  ├── filteredLogs: LogRecord[]       — computed: allLogs filtered by level + search
  ├── lineNumbers: Map<LogRecord,number>  — reset on clear
  ├── activeLevel: LevelFilter        — 'ALL'|'INFO'|'WARN'|'ERROR'|'DEBUG'
  ├── searchQuery: string             — bound to input
  ├── searchQuery$: Subject<string>   — debounced source for filtering
  ├── autoScroll: boolean             — default true
  ├── isConnected: boolean            — from ConnectedService
  ├── logCount: number                — allLogs.length
  ├── lastUpdated: Date | null        — timestamp of last received log
  └── @ViewChild('terminalViewport')  — for scroll management
```

### Pattern 1: Array Accumulation via `scan`
**What:** Subscribe to `LogService.logs`, accumulate into component array.
**When to use:** All real-time log display (replaces ViewContainerRef pattern).

```typescript
// Source: DashboardLogPaneComponent (verified in codebase)
this.logService.logs
    .pipe(
        takeUntilDestroyed(this.destroyRef),
        scan((acc: LogRecord[], record) => {
            const next = [...acc, record];
            return next.length > MAX_LOG_ENTRIES ? next.slice(-MAX_LOG_ENTRIES) : next;
        }, []),
        debounceTime(0)  // batch rapid emissions in one tick
    )
    .subscribe(entries => {
        this.allLogs = entries;
        this.lastUpdated = new Date();
        this.cdr.markForCheck();
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    });
```

### Pattern 2: Client-Side Filter as Computed Getter
**What:** `filteredLogs` is a getter that applies `activeLevel` and `searchQuery` to `allLogs`.
**Why getter:** Always in sync — no separate subscription needed; OnPush re-checks when `markForCheck()` called.

```typescript
// [VERIFIED: codebase pattern] — safe regex construction
get filteredLogs(): LogRecord[] {
    let result = this.allLogs;

    if (this.activeLevel !== 'ALL') {
        const levels = this.levelFilter(this.activeLevel);
        result = result.filter(r => levels.includes(r.level));
    }

    if (this.searchQuery.trim()) {
        try {
            const rx = new RegExp(this.searchQuery, 'i');
            result = result.filter(r => rx.test(r.message) || rx.test(r.loggerName));
        } catch {
            // invalid regex — show all (or optionally show error state)
        }
    }

    return result;
}
```

### Pattern 3: Auto-Scroll Toggle with Manual Scroll Detection
**What:** Detect when user scrolls up manually in the terminal viewport element; disable auto-scroll.
**Critical detail:** Scroll detection must be on the terminal viewport `div`, NOT on `window` (the terminal is a flex-1 container with `overflow-y: auto`, scroll happens inside the div).

```typescript
// [VERIFIED: codebase scroll pattern reference — logs-page.component.ts existing code]
@HostListener('scroll', ['$event.target'])
onTerminalScroll(target: HTMLElement): void {
    const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 10;
    if (!isAtBottom && this.autoScroll) {
        this.autoScroll = false;
        this.cdr.markForCheck();
    }
}

scrollToBottom(): void {
    if (this.terminalViewport?.nativeElement) {
        const el = this.terminalViewport.nativeElement;
        el.scrollTop = el.scrollHeight;
    }
}
```

**Implementation note:** The HostListener needs to be placed on the component host — or use `(scroll)` event binding on the terminal viewport element in the template. Using `(scroll)` on the div is simpler and avoids window event binding issues.

### Pattern 4: Debounced Search Input
**What:** Subject-based debounce for regex search.

```typescript
// [VERIFIED: option.component.ts uses same pattern with debounceTime]
private searchQuery$ = new Subject<string>();

ngOnInit() {
    this.searchQuery$
        .pipe(
            takeUntilDestroyed(this.destroyRef),
            debounceTime(200),
            distinctUntilChanged()
        )
        .subscribe(q => {
            this.searchQuery = q;
            this.cdr.markForCheck();
        });
}

onSearchInput(value: string): void {
    this.searchQuery$.next(value);
}
```

### Pattern 5: Export as .log File
**What:** Blob + URL.createObjectURL + anchor click pattern.
**When:** User clicks "Export .log" button.

```typescript
// [VERIFIED: standard browser API, same pattern as copyLogs in DashboardLogPaneComponent adapted for file]
exportLogs(): void {
    const lines = this.filteredLogs.map(e => {
        const d = e.time;
        const date = `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')}`;
        const time = `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
        return `${date} ${time} - ${e.level} - ${e.loggerName} - ${e.message}`;
    }).join('\n');

    const blob = new Blob([lines], {type: 'text/plain'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seedsyncarr-logs-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.log`;
    a.click();
    URL.revokeObjectURL(url);
}
```

### Pattern 6: Level-Specific Row CSS Classes (SCSS translation from mockup)
**What:** Row appearance driven by `[ngClass]` bindings; SCSS variables for level colors.

```scss
// SCSS equivalent of Tailwind alpha classes from mockup
// Source: _bootstrap-variables.scss verified color values

.log-row {
    display: flex;
    font-family: var(--bs-font-monospace);
    font-size: 13px;
    line-height: 1.6;
    letter-spacing: -0.01em;

    &:hover {
        background-color: rgba(26, 32, 25, 0.8);  // seed-row/80
    }

    &--error {
        background-color: rgba(196, 91, 91, 0.1);  // seed-error/10
        border-top: 1px solid rgba(196, 91, 91, 0.2);
        border-bottom: 1px solid rgba(196, 91, 91, 0.2);
        margin: 2px 0;

        &:hover {
            background-color: rgba(196, 91, 91, 0.15);
        }
    }

    &--warn:hover {
        background-color: rgba(209, 140, 52, 0.1);  // seed-warning/10
    }
}

.log-gutter {
    width: 3rem;
    text-align: right;
    padding-right: 0.75rem;
    color: rgba(154, 170, 138, 0.3);  // textsec/30
    border-right: 1px solid rgba(62, 74, 56, 0.3);  // seed-border/30
    user-select: none;
    flex-shrink: 0;
}

.log-ts {
    padding: 0 1rem;
    color: rgba(196, 154, 74, 0.7);  // seed-amber/70
    white-space: nowrap;
}

.log-level {
    width: 4rem;
    flex-shrink: 0;

    &--info  { color: #59a362; font-weight: 700; }
    &--warn  { color: #d18c34; font-weight: 700; }
    &--debug { color: rgba(154, 170, 138, 0.5); }
    &--error-badge {
        background: #c45b5b;
        color: #fff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
}
```

### Anti-Patterns to Avoid

- **Keeping ViewContainerRef insertion:** Old pattern causes scroll management complexity and doesn't support client-side filtering. The `scan` array pattern is required.
- **Window-level scroll listener:** The terminal is a scrollable div, not the window. Binding to `window:scroll` (as the old component does) will not detect in-viewport scroll events.
- **Constructing `RegExp` without try/catch:** Invalid user regex input will throw. Always wrap in try/catch and gracefully degrade.
- **Flushing LogService ReplaySubject on clear:** D-20 explicitly forbids this. Clear only resets the component's `allLogs` array, not the service buffer.
- **Using Phosphor icons:** Phase constraint — FA 4.7 only. The mockup uses Phosphor; translation to FA 4.7 is mandatory per D-11, D-12, D-13.
- **Importing Google Fonts in SCSS:** Fonts are already loaded globally. The mockup links JetBrains Mono and Inter — project already configures these in `_bootstrap-variables.scss`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log accumulation with cap | Custom event queue | `scan` operator from RxJS | Already in DashboardLogPaneComponent; handles replay subject correctly |
| Regex search | Manual string matching | Native `RegExp` constructor | Handles all regex features; just wrap in try/catch |
| Timestamp formatting | Custom date formatter | `DatePipe` or manual `Date` methods | `DatePipe` in template for display timestamps; manual formatting for export format |
| File download | Custom file writer | `Blob` + `URL.createObjectURL` + anchor | Standard browser API, zero dependencies |
| Connection status | Custom ping mechanism | `ConnectedService.connected` Observable | Already wired from SSE stream, accurate and reactive |
| Subscription cleanup | Manual `destroy$` Subject | `takeUntilDestroyed(this.destroyRef)` | Modern Angular 21 pattern used in DashboardLogPaneComponent |

---

## CSS Custom Properties: What Exists vs. What Needs Adding

### Already in `styles.scss` `:root`
| Variable | Value |
|----------|-------|
| `--app-header-bg` | `#222a20` |
| `--app-muted-text` | `#9aaa8a` |
| `--app-selection-bg` | `rgba(196, 154, 74, 0.25)` |
| `--app-selection-border` | `#c49a4a` |

### Already in `_bootstrap-variables.scss` (SCSS vars)
| Variable | Value |
|----------|-------|
| `$forest-base` | `#151a14` |
| `$forest-card` | `#222a20` |
| `$forest-row` | `#1a2019` |
| `$forest-border` | `#3e4a38` |
| `$forest-muted` | `#2c3629` |
| `$primary` (amber) | `#c49a4a` |
| `$success` | `#59a362` |
| `$warning` | `#d18c34` |
| `$danger` (error) | `#c45b5b` |

### Needs Adding: `seed-term` terminal background
The `#0a0d09` terminal background color is NOT present in any existing SCSS file. [VERIFIED: grep of `styles.scss` and `_bootstrap-variables.scss` found no match for `#0a0d09` or `seed-term`.]

**Action required in Wave 1:** Add to `styles.scss` `:root` block:
```scss
--app-term-bg: #0a0d09;  // Deep terminal background for logs page
```

Or alternatively, define in the component SCSS:
```scss
$term-bg: #0a0d09;  // Used only by logs page
```

---

## Common Pitfalls

### Pitfall 1: Scroll detection on wrong element
**What goes wrong:** Developer binds `@HostListener('window:scroll')` (copied from old component), which never fires for in-container scroll.
**Why it happens:** Old component used window-level scrolling; new design has terminal in a constrained `overflow-y: auto` flex container.
**How to avoid:** Add `(scroll)="onTerminalScroll($event)"` directly to the terminal viewport `div` in the template. Check `scrollTop + clientHeight >= scrollHeight - threshold` on the target element.
**Warning signs:** Auto-scroll toggle never activates/deactivates when user scrolls manually.

### Pitfall 2: Line counter out of sync with filtered display
**What goes wrong:** Line numbers shown on screen don't match the position in `allLogs` — numbers are per-`filteredLogs` index, not per-`allLogs` position.
**Why it happens:** Template iterates over `filteredLogs`; `$index` gives filtered position, not original position.
**How to avoid:** Line numbers should be the position in `filteredLogs` (1-based `$index + 1`), not in `allLogs`. Per D-02, line numbers reset when logs are cleared — this means they count visible filtered rows, not original buffer positions. Simplest: use `$index + 1` in the template.

### Pitfall 3: Invalid regex crashes the filter
**What goes wrong:** User types `(` or `[^` in the search field, `new RegExp(query)` throws `SyntaxError`, Angular error boundary catches it but filter stops working.
**How to avoid:** Wrap `RegExp` construction in try/catch. On invalid regex: either show empty results or show all results with a visible "invalid regex" indicator.

### Pitfall 4: Auto-scroll re-enables itself on filter change
**What goes wrong:** Filtering changes `filteredLogs`, template re-renders, new content is shorter or longer, scroll position changes, and auto-scroll logic incorrectly triggers.
**How to avoid:** Auto-scroll re-enable only happens on new log arrival (new entry added to `allLogs`). Filter/clear operations should not re-enable auto-scroll.

### Pitfall 5: Export downloads all logs instead of filtered
**What goes wrong:** Export iterates `allLogs` instead of `filteredLogs`.
**Why it happens:** Developer uses whichever array is easier to reach.
**How to avoid:** Per D-21, export must use `filteredLogs` — the currently visible set.

### Pitfall 6: `seed-term` color missing at runtime
**What goes wrong:** Terminal background renders as transparent or falls back to body background because `--app-term-bg` is not declared.
**How to avoid:** Wave 0 task must add the CSS custom property before any other work references it.

---

## Icon Mapping: Mockup Phosphor → FA 4.7

| Mockup (Phosphor) | Project (FA 4.7) | Usage |
|-------------------|------------------|-------|
| `ph-magnifying-glass` | `fa-search` | Search field icon |
| `ph-fill ph-check-circle` | `fa-check-circle` | Auto-scroll ON state |
| `ph ph-check-circle` | `fa-circle-o` | Auto-scroll OFF state |
| `ph-trash` | `fa-trash` | Clear button |
| `ph-download-simple` | `fa-download` | Export button |
| `ph-clock` | `fa-clock-o` | Status bar last-updated |

[VERIFIED: FA 4.7 class names confirmed from existing codebase usage — `fa-check-circle`, `fa-circle-o`, `fa-trash`, `fa-download`, `fa-clock-o` all used in project files.]

---

## Validation Architecture

**Test framework:** Karma + Jasmine (confirmed: `karma.conf.js` present, `ng test` script)
**Config file:** `/Users/julianamacbook/seedsyncarr/src/angular/karma.conf.js`
**Quick run:** `cd src/angular && ng test --include='**/logs*' --watch=false`
**Full suite:** `cd src/angular && ng test --watch=false`

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOGS-01 | Level filter buttons update visible entries | unit | `ng test --include='**/logs-page*' --watch=false` | ❌ Wave 0 |
| LOGS-02 | Regex search filters entries in real time | unit | `ng test --include='**/logs-page*' --watch=false` | ❌ Wave 0 |
| LOGS-03 | Auto-scroll, clear, export buttons function | unit | `ng test --include='**/logs-page*' --watch=false` | ❌ Wave 0 |
| LOGS-04 | Status bar shows connection, count, timestamp | unit | `ng test --include='**/logs-page*' --watch=false` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Visual inspection in browser (karma tests for DOM-heavy UI components take time to set up)
- **Per wave merge:** `cd src/angular && ng test --watch=false`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/angular/src/app/tests/unittests/pages/logs/logs-page.component.spec.ts` — covers LOGS-01 through LOGS-04

*(Existing test infrastructure: `dashboard-log-pane.component.spec.ts` provides the spec pattern to follow — inline template approach, `MockLogService` with Subject, `fakeAsync`/`tick` for debounce.)*

---

## Environment Availability

Step 2.6: SKIPPED — phase is a frontend-only component rewrite with no new external services, CLI tools, or databases. All dependencies (Angular CLI, Karma, LogService, ConnectedService) are already present and confirmed by existing codebase.

---

## Runtime State Inventory

Step 2.5: NOT APPLICABLE — this is a greenfield UI rewrite, not a rename/refactor/migration phase. No stored data, service configs, OS registrations, secrets, or build artifacts embed any identifier that this phase renames or moves.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `#0a0d09` is not yet defined as a CSS custom property in any project file | CSS Custom Properties section | If it already exists under a different name, the Wave 0 task to add it would create a duplicate — low risk, easily resolved |
| A2 | FA 4.7 `fa-check-circle` renders as a filled circle (matching `ph-fill ph-check-circle`) | Icon Mapping | If FA 4.7 `fa-check-circle` renders as outline, the ON/OFF visual distinction relies on color only — acceptable fallback |
| A3 | `(scroll)` event on the terminal `div` element fires correctly with `overflow-y: auto` in Angular 21 | Auto-scroll pattern | Standard browser behavior — extremely high confidence this works |

---

## Open Questions

1. **TrackBy function for log list**
   - What we know: `@for ... track $index` is the default; Angular 21 requires a track expression
   - What's unclear: Whether `track $index` vs `track entry.time.getTime()` is better for performance at 5000 entries
   - Recommendation: Use `track $index` — since `filteredLogs` is recomputed on each filter/arrival, item identity shifts anyway. This is in Claude's discretion.

2. **WARN row line number color**
   - What we know: Mockup shows `text-seed-warning/50` for WARN row gutter number
   - What's unclear: D-02 says gutter is always `textsec/30` — WARN rows appear to override this in the mockup
   - Recommendation: Follow mockup pixel-exact spec (D-01 is the governing decision) — WARN gutter uses `rgba(209, 140, 52, 0.5)` per mockup line 76.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: codebase]` — `src/angular/src/app/pages/files/dashboard-log-pane.component.ts` — scan/accumulation pattern, `takeUntilDestroyed`, `debounceTime`, `levelBadge()`, `copyLogs()` Blob pattern
- `[VERIFIED: codebase]` — `src/angular/src/app/services/logs/log.service.ts` — `ReplaySubject(5000)`, hot observable, `hasReceivedLogs`
- `[VERIFIED: codebase]` — `src/angular/src/app/services/logs/log-record.ts` — Level enum values (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `[VERIFIED: codebase]` — `src/angular/src/app/services/utils/connected.service.ts` — `connected: Observable<boolean>` from `BehaviorSubject`
- `[VERIFIED: codebase]` — `src/angular/src/app/common/_bootstrap-variables.scss` — all forest palette SCSS variables and their hex values
- `[VERIFIED: codebase]` — `src/angular/src/styles.scss` — `:root` CSS custom properties, global scrollbar styling, `app-logs-page` display flex rule
- `[VERIFIED: codebase]` — `src/angular/src/app/pages/settings/option.component.ts` — `debounceTime` + `Subject` pattern for input debounce
- `[VERIFIED: codebase]` — `.aidesigner/runs/2026-04-14T03-35-39-500Z-seedsyncarr-logs-page-triggarr-style/design.html` — pixel-exact visual spec read in full

### Secondary (MEDIUM confidence)
- `[ASSUMED]` — FA 4.7 icon name mapping for `fa-check-circle`, `fa-circle-o`, `fa-trash`, `fa-download`, `fa-clock-o` — confirmed by existing codebase grep but full FA 4.7 icon catalog not exhaustively checked

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already present and verified in codebase
- Architecture: HIGH — reference implementation (`DashboardLogPaneComponent`) verified in full; patterns are direct adaptations
- Pitfalls: HIGH — derived from direct code inspection of old component and reference implementation
- CSS mapping: HIGH — all color hex values verified from SCSS variables files; only `seed-term` (#0a0d09) is new

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable Angular + Bootstrap stack)
