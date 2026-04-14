# Phase 38: Terminal Polish & Traceability — Research

**Researched:** 2026-02-17
**Domain:** Angular SCSS / CSS custom properties / gap closure
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAV-03 | User sees app version at bottom of sidebar | CSS variable typo causes version text to render in wrong color (#e6edf3 white) instead of muted gray (#8b949e); fixing `var(--app-text-muted)` → `var(--app-muted-text)` in `sidebar.component.scss` line 76 completes the cosmetic requirement |
</phase_requirements>

## Summary

Phase 38 is a precision gap-closure phase with exactly one code change: fix a CSS custom property name typo in `sidebar.component.scss`. The v3.0 milestone audit (conducted 2026-02-17) identified that line 76 uses `var(--app-text-muted)` but the property is defined in `styles.scss` as `--app-muted-text`. This causes the sidebar version text to inherit the body text color (`#e6edf3`, effectively white) instead of rendering in the intended muted gray (`#8b949e`).

The requirement NAV-03 ("User sees app version at bottom of sidebar") is functionally satisfied — the version text is visible, appears at the correct location, and expands/collapses correctly with the sidebar hover behavior. The typo only affects color fidelity: it renders bright white instead of muted gray. The traceability entries in REQUIREMENTS.md were already updated during audit gap closure (the audit noted `[ ]` checkboxes but they have since been updated to `[x]`).

Phase 38 delivers a single 1-line CSS fix with zero risk of regression. No new libraries, no architecture changes, no tests to update.

**Primary recommendation:** Change `color: var(--app-text-muted)` to `color: var(--app-muted-text)` on line 76 of `sidebar.component.scss`. Verify visually (sidebar version text should appear in muted gray, not bright white). Update REQUIREMENTS.md traceability note to reflect Phase 38 completion.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | 19.x | Component-scoped SCSS via ViewEncapsulation | Already in use; no additions needed |
| SCSS | (Angular bundled) | CSS custom property references | Already in use; this is a property-name fix |

**Installation:** No new packages. This phase requires no `npm install`.

## Architecture Patterns

### CSS Custom Property Naming Convention in This Project

The project defines all app-specific CSS custom properties in `styles.scss` inside `:root`. The naming convention is `--app-<adjective>-<noun>` (e.g., `--app-muted-text`, `--app-selection-bg`, `--app-logo-color`).

**Known properties defined in `styles.scss` `:root` block:**
```scss
// Text
--app-logo-color: #3fb950;
--app-muted-text: #8b949e;      // ← correct name — adjective-noun order
--app-separator-color: #484f58;
```

Three SCSS files consume `--app-muted-text` correctly:
- `option.component.scss`: `color: var(--app-muted-text);`
- `about-page.component.scss`: `color: var(--app-muted-text);`
- `sidebar.component.scss` line 76: `color: var(--app-text-muted);` ← TYPO (noun-adjective reversed)

### Angular ViewEncapsulation Context

The sidebar component uses Angular's default `ViewEncapsulation.Emulated`. CSS custom properties defined in `:root` (global `styles.scss`) are accessible from within component-scoped SCSS — CSS variables are not scoped by ViewEncapsulation because they cascade through the DOM. The typo fix requires no encapsulation workaround; it is a simple string substitution.

### Recommended Pattern: Verify Undefined CSS Variables

When a CSS variable reference cannot be resolved by the browser, the property uses its inherited value or initial value. `color` inherits, so `var(--app-text-muted)` (undefined) causes `color` to inherit from the `body` rule, which is `#e6edf3` (Bootstrap 5 dark mode body color). This is exactly the symptom documented in the audit.

```scss
// sidebar.component.scss — BEFORE (line 76)
.sidebar-version {
    padding: 8px 12px;
    font-family: var(--bs-font-monospace);
    font-size: 0.75rem;
    color: var(--app-text-muted);    // ← undefined property, inherits body color
    border-top: 1px solid var(--bs-border-color);
}

// sidebar.component.scss — AFTER (line 76)
.sidebar-version {
    padding: 8px 12px;
    font-family: var(--bs-font-monospace);
    font-size: 0.75rem;
    color: var(--app-muted-text);    // ← correct: resolves to #8b949e
    border-top: 1px solid var(--bs-border-color);
}
```

### Anti-Patterns to Avoid

- **Inventing the correct variable name without verifying**: Always confirm against `styles.scss` `:root` definitions. The correct name is `--app-muted-text` (verified in `styles.scss` line 108).
- **Searching for `--app-text-muted` elsewhere**: Only `sidebar.component.scss` uses the wrong name. No other file uses this typo. The fix is localized to a single line.
- **Adding a new CSS variable as an alias**: Do not add `--app-text-muted` to `styles.scss` as an alias. Fix the typo at the call site; aliases create confusion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color verification | Custom test | Visual inspection in browser | Single-pixel color; `ng serve` is sufficient |
| Variable existence check | Lint rule | Direct grep of styles.scss | Only 3 consumers; trivial to cross-check |

**Key insight:** This phase is 1 line of CSS. Any tooling overhead would exceed the work itself.

## Common Pitfalls

### Pitfall 1: Fixing the Wrong File
**What goes wrong:** Editing `styles.scss` to add `--app-text-muted` as a new variable instead of fixing the typo in `sidebar.component.scss`.
**Why it happens:** Both approaches "make it work" but the correct approach fixes the call site.
**How to avoid:** Change the CSS variable reference in `sidebar.component.scss` line 76. Do not touch `styles.scss`.
**Warning signs:** If you find yourself editing `styles.scss`, stop and re-read this document.

### Pitfall 2: Editing the Wrong Line
**What goes wrong:** Changing the `color` property inside `.button.selected` or `.sidebar-icon` instead of `.sidebar-version`.
**Why it happens:** `.sidebar-version` is near the bottom of the `#sidebar` block.
**How to avoid:** The target rule is `.sidebar-version` at line 72-78 of `sidebar.component.scss`. Line 76 specifically is the `color` declaration.
**Warning signs:** `filter: invert(1)` or `font-weight` on the same edited line indicates the wrong block.

### Pitfall 3: Expecting Test Failures
**What goes wrong:** Running `ng test` and expecting a CSS test to catch the typo.
**Why it happens:** Angular unit tests (Karma/Jasmine) do not test computed CSS color values.
**How to avoid:** Visual verification in browser is the appropriate check. CSS variable resolution requires a rendering engine.
**Warning signs:** There are no unit tests for this CSS property; their absence is expected.

## Code Examples

Verified patterns from direct codebase inspection:

### Correct Usage (from other consumers)
```scss
// Source: src/angular/src/app/pages/settings/option.component.scss
color: var(--app-muted-text);

// Source: src/angular/src/app/pages/about/about-page.component.scss
color: var(--app-muted-text);
```

### Variable Definition (authoritative)
```scss
// Source: src/angular/src/styles.scss line 108
:root {
  // Text
  --app-logo-color: #3fb950;
  --app-muted-text: #8b949e;       // ← #8b949e = muted gray
  --app-separator-color: #484f58;
}
```

### The Fix
```scss
// Source: src/angular/src/app/pages/main/sidebar.component.scss line 76
// BEFORE:
color: var(--app-text-muted);    // undefined — inherits #e6edf3 (white)

// AFTER:
color: var(--app-muted-text);    // resolves to #8b949e (muted gray)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `[ ]` checkboxes in REQUIREMENTS.md | `[x]` checkboxes (updated post-audit) | 2026-02-17 | Traceability already closed; no REQUIREMENTS.md changes needed |
| NAV-03 partially satisfied (wrong color) | NAV-03 fully satisfied (correct color) | Phase 38 closes this | Cosmetic fix only |

**Already done (no Phase 38 action needed):**
- REQUIREMENTS.md checkboxes updated to `[x]` for all 21 requirements
- REQUIREMENTS.md traceability table maps NAV-03 to "Phase 34, 38"
- Coverage summary reflects "1 with cosmetic fix pending in Phase 38"

## Open Questions

1. **Does REQUIREMENTS.md need any changes at all?**
   - What we know: All checkboxes are `[x]`. The traceability table references Phase 38. The coverage note says "pending in Phase 38".
   - What's unclear: Should the coverage note be updated from "pending" to "complete" after Phase 38 runs?
   - Recommendation: Yes — update the REQUIREMENTS.md coverage note on line 95 from "1 with cosmetic fix pending in Phase 38" to reflect completion. This is a documentation cleanup, not a re-opened gap.

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `src/angular/src/app/pages/main/sidebar.component.scss` — typo confirmed at line 76
- Direct file inspection: `src/angular/src/styles.scss` line 108 — canonical variable name `--app-muted-text` confirmed
- Direct file inspection: `src/angular/src/app/pages/settings/option.component.scss` — correct usage verified
- Direct file inspection: `src/angular/src/app/pages/about/about-page.component.scss` — correct usage verified
- Direct file inspection: `.planning/v3.0-MILESTONE-AUDIT.md` — audit finding documented with file/line specificity
- Direct file inspection: `.planning/REQUIREMENTS.md` — current checkbox and traceability state confirmed

### Secondary (MEDIUM confidence)
- Angular ViewEncapsulation documentation (training knowledge, confirmed by Phase 34 prior work): CSS custom properties defined in `:root` are accessible from component-scoped SCSS because they cascade through the DOM.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, existing Angular/SCSS setup
- Architecture: HIGH — single-line fix, file and line number precisely identified in audit
- Pitfalls: HIGH — directly observed from audit findings and file inspection

**Research date:** 2026-02-17
**Valid until:** Stable indefinitely (this is a fix to existing code, not a moving target)
