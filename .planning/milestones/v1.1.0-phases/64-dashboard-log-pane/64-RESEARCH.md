# Phase 64: Dashboard — Log Pane — Research

**Researched:** 2026-04-14
**Domain:** Angular component, LogService subscription, SCSS styling, Font Awesome icon mapping
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-12 | Compact terminal log pane at bottom of dashboard | LogService provides live stream via ReplaySubject; component subscribes and renders entries in a fixed-height section appended after `<app-transfer-table>` |
| DASH-13 | Log entries use monospace font with timestamp, level badge, and message | LogRecord has `time: Date`, `level: LogRecord.Level`, `message: string`; JetBrains Mono is already loaded in index.html and declared in `$font-family-monospace` |
| DASH-14 | Log levels colored by severity (green INFO, amber WARN, red ERROR) | $semantic-success (#59a362), $primary/#c49a4a (amber), $semantic-error (#c45b5b) are all defined in `_bootstrap-variables.scss` and can be used directly |
</phase_requirements>

---

## Summary

Phase 64 adds a single new Angular standalone component — `DashboardLogPaneComponent` — to the bottom of `FilesPageComponent`. The component subscribes to `LogService.logs` (already provided globally via `StreamServiceRegistry`) and maintains a capped array of the most recent N entries for display.

The data layer requires zero new services or backend changes. `LogService` already emits a `ReplaySubject<LogRecord>` with up to 5000 entries buffered. The component subscribes once on init, appends entries to a local array capped at 50, and uses `ChangeDetectionStrategy.OnPush` with manual `markForCheck()` — exactly the same pattern as existing Phase 63 components.

The visual design is fully defined in the AIDesigner dashboard HTML (lines 520–562). All required color tokens are already in `_bootstrap-variables.scss`. Font Awesome 4.7 is the icon library; the three Phosphor icons in the design spec (`ph-terminal`, `ph-copy`, `ph-arrows-out-simple`) each have a direct FA 4.7 equivalent. No new npm packages, no new global styles, no backend changes needed.

**Primary recommendation:** One standalone component `DashboardLogPaneComponent` with a capped array subscription, Font Awesome icon substitutions, and SCSS variables for all colors — single plan, single wave.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular standalone components | 21 | Component architecture | All Phase 62/63 components use this pattern |
| RxJS | (bundled with Angular) | LogService subscription | `takeUntilDestroyed(destroyRef)` pattern used in TransferTableComponent |
| Font Awesome | 4.7.0 | Icons | Loaded via angular.json assets; all existing dashboard icons use `fa fa-*` |
| Bootstrap 5 SCSS + project tokens | 5.x | Layout and color variables | Entire app uses `@use '../../common/common' as *` |
| JetBrains Mono | (Google Fonts, pre-loaded) | Monospace log text | Already in index.html; `$font-family-monospace` in `_bootstrap-variables.scss` |

### No New Dependencies Needed
All required libraries are already installed. No `npm install` required.

---

## Architecture Patterns

### Recommended Project Structure
New files:
```
src/angular/src/app/pages/files/
├── dashboard-log-pane.component.ts     # New standalone component
├── dashboard-log-pane.component.html   # Log pane template
└── dashboard-log-pane.component.scss   # Component-scoped styles
```

Modified files:
```
src/angular/src/app/pages/files/
├── files-page.component.ts    # Add DashboardLogPaneComponent to imports
└── files-page.component.html  # Add <app-dashboard-log-pane> after <app-transfer-table>
```

### Pattern 1: Capped Array Subscription (do NOT use the logs-page DOM-insertion approach)

The existing `LogsPageComponent` uses `ViewContainerRef.createEmbeddedView()` to imperatively insert DOM nodes — this is necessary for an infinite unbounded log page but is wrong for a compact pane showing the last N entries.

The correct pattern for the dashboard log pane:

```typescript
// Source: [VERIFIED: codebase - transfer-table.component.ts pattern]
import {Component, ChangeDetectionStrategy, ChangeDetectorRef, DestroyRef, inject, OnInit} from "@angular/core";
import {DatePipe, NgClass} from "@angular/common";
import {takeUntilDestroyed} from "@angular/core/rxjs-interop";

import {StreamServiceRegistry} from "../../services/base/stream-service.registry";
import {LogRecord} from "../../services/logs/log-record";

const MAX_PANE_ENTRIES = 50;

@Component({
    selector: "app-dashboard-log-pane",
    templateUrl: "./dashboard-log-pane.component.html",
    styleUrls: ["./dashboard-log-pane.component.scss"],
    standalone: true,
    imports: [DatePipe, NgClass],
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardLogPaneComponent implements OnInit {
    public readonly LogRecord = LogRecord;
    entries: LogRecord[] = [];

    private destroyRef = inject(DestroyRef);

    constructor(
        private streamRegistry: StreamServiceRegistry,
        private cdr: ChangeDetectorRef
    ) {}

    ngOnInit(): void {
        this.streamRegistry.logService.logs
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(record => {
                this.entries.push(record);
                if (this.entries.length > MAX_PANE_ENTRIES) {
                    this.entries.shift();
                }
                this.cdr.markForCheck();
            });
    }
}
```

Key decisions explained:
- `takeUntilDestroyed(this.destroyRef)` — modern Angular 21 pattern (no manual `destroy$` Subject needed); used in TransferTableComponent
- `cdr.markForCheck()` — correct for OnPush when mutating an array
- `entries.shift()` on overflow — keeps the array at MAX_PANE_ENTRIES without slice overhead per push
- `StreamServiceRegistry` injected (not LogService directly) — consistent with how LogsPageComponent accesses it

### Pattern 2: FilesPageComponent Integration

```typescript
// Source: [VERIFIED: codebase - files-page.component.ts]
// Add to imports array:
imports: [StatsStripComponent, TransferTableComponent, DashboardLogPaneComponent]
```

```html
<!-- files-page.component.html — append after transfer table -->
<app-stats-strip></app-stats-strip>
<app-transfer-table></app-transfer-table>
<app-dashboard-log-pane></app-dashboard-log-pane>
```

The `:host` in `files-page.component.scss` already uses `flex-direction: column; gap: 24px` — the new component slots in automatically with correct spacing.

### Pattern 3: Template — Level Badge Logic

```html
<!-- Source: [VERIFIED: codebase - logs-page.component.html LogRecord.Level enum] -->
<!-- Design spec uses [INFO], [WARN], [ERR!] as display strings -->
<!-- LogRecord.Level enum: DEBUG, INFO, WARNING, ERROR, CRITICAL -->

@for (entry of entries; track $index) {
  <div class="log-entry" [class.log-entry--error]="entry.level === LogRecord.Level.ERROR || entry.level === LogRecord.Level.CRITICAL">
    <span class="log-ts">{{ entry.time | date:'HH:mm:ss.SSS' }}</span>
    <span class="log-badge"
          [class.log-badge--info]="entry.level === LogRecord.Level.INFO || entry.level === LogRecord.Level.DEBUG"
          [class.log-badge--warn]="entry.level === LogRecord.Level.WARNING"
          [class.log-badge--error]="entry.level === LogRecord.Level.ERROR || entry.level === LogRecord.Level.CRITICAL">
      {{ levelBadge(entry.level) }}
    </span>
    <span class="log-msg">{{ entry.message }}</span>
  </div>
}
```

Level badge display strings:
| LogRecord.Level | Display Badge | Color class |
|-----------------|---------------|-------------|
| DEBUG | [DEBUG] | --info (green) |
| INFO | [INFO] | --info (green) |
| WARNING | [WARN] | --warn (amber) |
| ERROR | [ERR!] | --error (red) |
| CRITICAL | [CRIT] | --error (red) |

Add a `levelBadge(level: LogRecord.Level): string` method to the component.

### Pattern 4: SCSS Color Mapping

All design tokens are available via `@use '../../common/common' as *`:

| Design spec token | SCSS variable | Hex |
|-------------------|---------------|-----|
| forest-base | $forest-base | #151a14 |
| forest-border | $forest-border | #3e4a38 |
| forest-card | $forest-card | #222a20 |
| forest-row | $forest-row | #1a2019 |
| amber-accent | $primary | #c49a4a |
| ui-primary | $body-color-dark | #e0e8d6 |
| ui-secondary | $secondary | #9aaa8a |
| semantic-success | $semantic-success | #59a362 |
| semantic-error | $semantic-error | #c45b5b |

### Pattern 5: Font Awesome Icon Substitutions

Phosphor icons in the design spec do not exist in the project — only Font Awesome 4.7 is installed. Direct substitutions:

| Design spec (Phosphor) | FA 4.7 substitute | Class |
|------------------------|-------------------|-------|
| `ph ph-terminal` | terminal / code | `fa fa-terminal` |
| `ph ph-copy` | copy | `fa fa-copy` |
| `ph ph-arrows-out-simple` | expand | `fa fa-expand` |
| `ph ph-circle-notch animate-spin` | spinner | `fa fa-circle-o-notch fa-spin` |

[VERIFIED: codebase grep — `fa fa-bell`, `fa fa-check-circle`, `fa fa-search`, etc. confirm FA 4.7 is active across the app]

FA 4.7 includes `fa-terminal`, `fa-copy`, `fa-expand`, and `fa-circle-o-notch` (with Bootstrap's `fa-spin` equivalent).

### Pattern 6: Loading Spinner State

The design shows a spinning `ph-circle-notch` at the bottom when no logs are received yet. Map to `LogService.hasReceivedLogs`:

```html
@if (!streamRegistry.logService.hasReceivedLogs) {
  <div class="log-spinner">
    <i class="fa fa-circle-o-notch fa-spin"></i>
  </div>
}
```

### Anti-Patterns to Avoid

- **Do NOT copy the `ViewContainerRef.createEmbeddedView()` approach from LogsPageComponent.** That pattern is for unbounded page-level rendering where DOM nodes are never removed. The dashboard pane needs a fixed-size window into recent logs — a simple array + ngFor is correct.
- **Do NOT subscribe to `logs` after `ngAfterViewInit`.** Unlike LogsPageComponent (which needs ViewChild elements ready), the pane uses only template bindings — subscribe in `ngOnInit`.
- **Do NOT use `async` pipe on the logs observable.** `LogService.logs` is a hot `ReplaySubject` that replays all buffered entries on subscribe. An `async` pipe in the template would trigger a full replay on every change detection cycle. Subscribe once in the component and accumulate to an array.
- **Do NOT use `ChangeDetectorRef.detectChanges()`.** Use `markForCheck()` with OnPush — detectChanges() is synchronous and can cause extra renders.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log streaming | Custom SSE listener | LogService.logs Observable | Already wired to server SSE, buffered, reconnection-handled |
| Icon rendering | SVG inline or custom CSS shapes | FA 4.7 `fa fa-*` classes | Already loaded globally via angular.json |
| Color tokens | Hardcoded hex values in SCSS | `$forest-base`, `$semantic-success` etc. from `common` | DRY; already verified against design spec |
| Subscription cleanup | Manual Subject + takeUntil | `takeUntilDestroyed(destroyRef)` | Angular 21 standard; no ngOnDestroy boilerplate needed |

---

## Common Pitfalls

### Pitfall 1: ReplaySubject Replay Flood on Init
**What goes wrong:** The first subscriber to `LogService.logs` receives ALL buffered entries (up to 5000) synchronously, causing 5000 `markForCheck()` calls and visible render lag.
**Why it happens:** `ReplaySubject(5000)` replays the full buffer to each new subscriber.
**How to avoid:** Subscribe in `ngOnInit` and render nothing until all replayed entries are processed, or use `Array.from` with `take()` to grab only the last N at subscribe time. The simplest approach: subscribe normally, let the capped array `shift()` discard all but the last 50 — the initial render simply shows the last 50 entries after the replay finishes. Use `requestAnimationFrame` or `ngZone.runOutsideAngular` if needed, but in practice 5000 array operations are sub-millisecond.
**Warning signs:** Dashboard slow to render after navigation; profiler shows many `markForCheck` calls on init.

### Pitfall 2: DatePipe Format for Milliseconds
**What goes wrong:** The design spec shows `14:02:11.450` (HH:mm:ss.SSS). Angular's `DatePipe` with `'HH:mm:ss'` drops the milliseconds.
**Why it happens:** Format string omits `SSS`.
**How to avoid:** Use `entry.time | date:'HH:mm:ss.SSS'` — Angular DatePipe supports milliseconds with `SSS`. [VERIFIED: Angular DatePipe docs format tokens]

### Pitfall 3: files-page `:host` Height
**What goes wrong:** The log pane section has `h-40` (160px) in the design, but the `:host` is `flex-direction: column` with `flex-grow: 1`. If the pane takes `flex-grow`, it expands to fill remaining page height.
**Why it happens:** Not setting an explicit height on the pane section.
**How to avoid:** Set `height: 160px; flex-shrink: 0` on the pane's outer section element in SCSS — matches the design's `h-40` fixed height.

### Pitfall 4: Copy Button with No Clipboard API Guard
**What goes wrong:** `navigator.clipboard.writeText()` throws in non-HTTPS contexts (localhost without HTTPS, older browsers).
**Why it happens:** Clipboard API requires secure context.
**How to avoid:** Wrap in `try/catch` or check `navigator.clipboard` before calling. The copy button is a secondary control — a silent failure is acceptable; add `console.warn` for debug visibility.

### Pitfall 5: WARN vs WARNING Level Mismatch
**What goes wrong:** Displaying `LogRecord.Level.WARNING` as `[WARNING]` instead of `[WARN]` — looks different from design spec badge.
**Why it happens:** The enum value is `WARNING` but design shows the short form `[WARN]`.
**How to avoid:** Use the `levelBadge()` method in the component to map enum values to display strings.

---

## Code Examples

### Timestamp Pipe Format
```html
<!-- Source: [VERIFIED: codebase - logs-page.component.html uses DatePipe] -->
{{ entry.time | date:'HH:mm:ss.SSS' }}
```
Result: `14:02:11.450` — matches design spec exactly.

### Inset Shadow (design spec `shadow-[inset_0_2px_10px_rgba(0,0,0,0.2)]`)
```scss
// Source: [VERIFIED: design.html line 520]
// Translate Tailwind arbitrary value to plain CSS:
box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.2);
```

### FA Spin Animation
```html
<!-- Source: [VERIFIED: codebase - Font Awesome 4.7 includes fa-spin class] -->
<i class="fa fa-circle-o-notch fa-spin"></i>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `ngOnDestroy` + Subject | `takeUntilDestroyed(destroyRef)` | Angular 16+ | No boilerplate OnDestroy needed |
| `ChangeDetectorRef.detectChanges()` | `markForCheck()` with OnPush | Angular best practice | Avoids redundant sync renders |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Copy button copies all visible log entries (not full buffer) to clipboard | Architecture Patterns / Pitfall 4 | UX expectation mismatch — easily adjusted |
| A2 | Expand button navigates to the Logs page (Phase 66 will implement full-page log view) | Phase goal — inferred from design spec "expand" icon | Button may need to do nothing in Phase 64 and be wired in Phase 66 |

---

## Open Questions

1. **Expand button behavior**
   - What we know: Design shows `ph-arrows-out-simple` (expand) button in the log pane header
   - What's unclear: Should clicking it navigate to the Logs page? Show a modal? Do nothing yet?
   - Recommendation: Wire it as a router link to `/logs` in Phase 64 — trivial to implement and useful immediately.

2. **Initial entry count from ReplaySubject**
   - What we know: LogService buffers up to 5000 entries; component caps at 50
   - What's unclear: Should the initial render prefer the 50 MOST RECENT entries from the buffer, or the 50 OLDEST?
   - Recommendation: Most recent 50 — subscribe normally and let `shift()` discard older ones as the replay fills the array past 50. Final result is the last 50 received.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 64 is a pure Angular UI component addition. No external tools, CLIs, or services beyond what the existing Angular build already requires.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine (Angular default) |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `npm run test --watch=false` (inside `src/angular/`) |
| Full suite command | `make run-tests-angular` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-12 | Log pane renders at bottom of dashboard | Manual visual (browser) | — | N/A |
| DASH-13 | Timestamp/badge/message display in monospace | Manual visual (browser) | — | N/A |
| DASH-14 | Level colors correct (green/amber/red) | Manual visual (browser) | — | N/A |

All three requirements are visual/CSS concerns — appropriate validation is browser inspection, not unit tests. No Wave 0 test file gaps.

### Wave 0 Gaps
None — no new test infrastructure needed for this phase.

---

## Security Domain

No security-relevant surface area in this phase. The log pane is a read-only display component that subscribes to an existing in-memory observable. No new API endpoints, no user input, no authentication flows, no cryptography.

---

## Sources

### Primary (HIGH confidence)
- `src/angular/src/app/services/logs/log.service.ts` — LogService API: `logs: Observable<LogRecord>`, `hasReceivedLogs: boolean`
- `src/angular/src/app/services/logs/log-record.ts` — LogRecord model: `time: Date`, `level: LogRecord.Level`, `loggerName: string`, `message: string`
- `src/angular/src/app/pages/logs/logs-page.component.ts` — Reference subscription pattern (ngAfterViewInit, ViewContainerRef)
- `src/angular/src/app/services/base/stream-service.registry.ts` — StreamServiceRegistry provides `logService` accessor
- `src/angular/src/app/common/_bootstrap-variables.scss` — All color tokens verified ($forest-base, $primary, $semantic-success, $semantic-error, etc.)
- `src/angular/src/app/pages/files/files-page.component.{ts,html,scss}` — Integration point: flex-column host, current imports, template insertion point
- `src/angular/src/app/pages/files/transfer-table.component.ts` — `takeUntilDestroyed(destroyRef)` pattern, ChangeDetectionStrategy.OnPush
- `.aidesigner/runs/2026-04-14T03-20-41.../design.html` lines 520–562 — Complete log pane design spec
- `src/angular/angular.json` line 38 — Font Awesome 4.7 loaded via SCSS asset
- `src/angular/src/index.html` line 16 — JetBrains Mono loaded via Google Fonts

### Secondary (MEDIUM confidence)
- Font Awesome 4.7 icon list — `fa-terminal`, `fa-copy`, `fa-expand`, `fa-circle-o-notch` all confirmed in FA 4.7 [ASSUMED: not independently verified against fa-4.7 icon index in this session, but project uses these successfully in existing components]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from existing component files
- Architecture: HIGH — LogService API verified from source; patterns verified from Phase 63 components
- Pitfalls: HIGH — identified from code analysis of actual LogService and Angular change detection behavior
- Icon mapping: MEDIUM — FA 4.7 icon names inferred from pattern; `fa-terminal`, `fa-copy`, `fa-expand` are standard FA 4.7 icons

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable Angular + SCSS domain; icon library locked at 4.7.0)
