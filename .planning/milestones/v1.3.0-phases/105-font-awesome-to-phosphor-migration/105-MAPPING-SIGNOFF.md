# 105-MAPPING-SIGNOFF.md — FA→Phosphor Complete Mapping Table + Ambiguous Sign-Off

**Phase 105: Font Awesome to Phosphor Migration**
**D-01 artifact** — complete fa→ph mapping table for all 39 distinct `fa-*` classes in use.
All `ph-*` class names verified to exist in the installed `@phosphor-icons/web` 2.1.2 regular CSS
(`node_modules/@phosphor-icons/web/src/regular/style.css`).

---

> **CORRECTED NON-INTUITIVE MAPPINGS (read before applying any icon)**
>
> Two mappings are named counter-intuitively and must NOT be applied by the "obvious" name:
>
> 1. **`fa-server` → `ph-computer-tower`** (NOT `ph-server` — `ph-server` does NOT exist in
>    Phosphor 2.1.2; see Pitfall 3 in RESEARCH.md §4)
>    _Source: RESEARCH Migration Surface Map §2a (settings-page.component.html:56 +
>    options-list.ts:19) and RESEARCH Pitfall 3._
>
> 2. **`fa-ban` → `ph-prohibit`** (NOT `ph-ban` — `ph-ban` does NOT exist in Phosphor 2.1.2;
>    see Pitfall 4 in RESEARCH.md §4)
>    _Source: RESEARCH §1a Confident Mappings table, explicit note on `fa-ban` row._

---

## CONFIRMED MAPPINGS (31 confident 1:1 mappings — no sign-off needed)

All sourced from RESEARCH §1a "Confident Mappings" unless otherwise noted.

| FA4 class | Phosphor class | HTML idiom | Weight | Source |
|-----------|----------------|------------|--------|--------|
| `fa-arrow-down` | `ph-arrow-down` | `<i class="ph ph-arrow-down">` | regular | RESEARCH §1a |
| `fa-ban` | `ph-prohibit` | `<i class="ph ph-prohibit">` | regular | RESEARCH §1a (NOTE: `ph-ban` does not exist in v2.1.2) |
| `fa-bell` | `ph-bell` | `<i class="ph ph-bell">` | regular | RESEARCH §1a |
| `fa-check` | `ph-check` | `<i class="ph ph-check">` | regular | RESEARCH §1a |
| `fa-check-circle` | `ph-check-circle` | `<i class="ph ph-check-circle">` | regular | RESEARCH §1a |
| `fa-circle` | `ph-circle` | `<i class="ph ph-circle">` | regular | RESEARCH §1a |
| `fa-circle-o` | `ph-circle` | `<i class="ph ph-circle">` | regular | RESEARCH §1a |
| `fa-clock-o` | `ph-clock` | `<i class="ph ph-clock">` | regular | RESEARCH §1a |
| `fa-cloud` | `ph-cloud` | `<i class="ph ph-cloud">` | regular | RESEARCH §1a |
| `fa-cog` | `ph-gear` | `<i class="ph ph-gear">` | regular | RESEARCH §1a |
| `fa-copy` | `ph-copy` | `<i class="ph ph-copy">` | regular | RESEARCH §1a |
| `fa-database` | `ph-database` | `<i class="ph ph-database">` | regular | RESEARCH §1a |
| `fa-download` | `ph-download` | `<i class="ph ph-download">` | regular | RESEARCH §1a |
| `fa-exclamation-circle` | `ph-warning-circle` | `<i class="ph ph-warning-circle">` | regular | RESEARCH §1a |
| `fa-exclamation-triangle` | `ph-warning` | `<i class="ph ph-warning">` | regular | RESEARCH §1a |
| `fa-expand` | `ph-arrows-out` | `<i class="ph ph-arrows-out">` | regular | RESEARCH §1a |
| `fa-eye` | `ph-eye` | `<i class="ph ph-eye">` | regular | RESEARCH §1a |
| `fa-eye-slash` | `ph-eye-slash` | `<i class="ph ph-eye-slash">` | regular | RESEARCH §1a |
| `fa-folder-open-o` | `ph-folder-open` | `<i class="ph ph-folder-open">` | regular | RESEARCH §1a |
| `fa-info-circle` | `ph-info` | `<i class="ph ph-info">` | regular | RESEARCH §1a |
| `fa-list` | `ph-list` | `<i class="ph ph-list">` | regular | RESEARCH §1a |
| `fa-play` | `ph-play` | `<i class="ph ph-play">` | regular | RESEARCH §1a |
| `fa-plus-circle` | `ph-plus-circle` | `<i class="ph ph-plus-circle">` | regular | RESEARCH §1a |
| `fa-refresh` | `ph-arrows-clockwise` | `<i class="ph ph-arrows-clockwise">` | regular | RESEARCH §1a |
| `fa-search` | `ph-magnifying-glass` | `<i class="ph ph-magnifying-glass">` | regular | RESEARCH §1a |
| `fa-server` | `ph-computer-tower` | `<i class="ph ph-computer-tower">` | regular | RESEARCH Migration Surface Map §2a + Pitfall 3 (NOT §1a — `fa-server` is NOT listed in §1a; `ph-server` does not exist) |
| `fa-shield` | `ph-shield` | `<i class="ph ph-shield">` | regular | RESEARCH §1a |
| `fa-stop` | `ph-stop` | `<i class="ph ph-stop">` | regular | RESEARCH §1a |
| `fa-tasks` | `ph-list-checks` | `<i class="ph ph-list-checks">` | regular | RESEARCH §1a |
| `fa-terminal` | `ph-terminal` | `<i class="ph ph-terminal">` | regular | RESEARCH §1a |
| `fa-times` | `ph-x` | `<i class="ph ph-x">` | regular | RESEARCH §1a |
| `fa-trash` | `ph-trash` | `<i class="ph ph-trash">` | regular | RESEARCH §1a |

**Total confirmed: 32 rows** (31 from §1a + `fa-server` from surface map §2a / Pitfall 3)

---

## AMBIGUOUS — AWAITING SIGN-OFF (8 icons — D-01 gate)

Per D-01 (LOCKED): these 8 icons require explicit user sign-off before any replacement code
lands in plans 105-02 or 105-03. Proposed classes are from RESEARCH §1b / §5.

Each icon has a `DECISION:` line — leave blank until the user signs off. The continuation
agent that executes plans 105-02 and 105-03 reads these DECISION lines as the authoritative
class names to apply.

---

### Q1 — `fa-tachometer`

**Usage:** Settings "LFTP Connection Limits" section header (`settings-page.component.html:141`)
and `options-list.ts:101` (dynamic icon data string).

**Proposed:** `ph-gauge`

**Rationale (RESEARCH §5 Q1):** `ph-gauge` is the standard speedometer/dashboard icon in
Phosphor. `ph-tachometer` does not exist in v2.1.2. Intent is "performance limits / speed
settings" — the gauge/speedometer concept is a direct semantic match.

**Alternate:** None with comparable semantic fit verified in installed package.

**DECISION:** _______________

---

### Q2 — `fa-floppy-o`

**Usage:** Settings "Save Settings" button (`settings-page.component.html:471`).

**Proposed:** `ph-floppy-disk`

**Rationale (RESEARCH §5 Q2):** `ph-floppy-disk` is the save/disk icon in Phosphor.
`ph-floppy-o` does not exist; Phosphor drops the `-o` suffix. Single usage, universally
recognized save icon.

**Alternate:** None.

**DECISION:** _______________

---

### Q3 — `fa-hdd-o`

**Usage:** Settings "Local Directory" option input field icon
(`settings-page.component.html:95` via `[icon]="'fa-hdd-o'"` binding in `option.component.html:13`).

**Proposed:** `ph-hard-drive`

**Rationale (RESEARCH §5 Q3):** `ph-hard-drive` represents local storage/disk. `ph-hdd-o`
does not exist; Phosphor drops the `-o` suffix. The "Local Directory" field context makes
the hard-drive/storage icon semantically correct.

**Alternate:** None with comparable semantic fit.

**DECISION:** _______________

---

### Q4 — `fa-file-archive-o`

**Usage:** Bulk-actions bar "Extract" button (`bulk-actions-bar.component.html:29`),
"Archive Operations" section header, and `options-list.ts:222` (dynamic icon data string).
This single DECISION is applied by BOTH plans 105-02 and 105-03 — they read this same line
so they cannot diverge.

**Proposed:** `ph-file-archive`

**Rationale (RESEARCH §5 Q4):** `ph-file-archive` exists and represents an archive/zip file.
`ph-file-zip` also exists. `ph-file-archive` is the closer semantic match for "Archive
Operations" section header and "Extract" button. Both are valid.

**Alternate:** `ph-file-zip` (equally valid; more literal "zip" concept).

**DECISION:** _______________

---

### Q5 — `fa-circle-o-notch` + `fa-spin`

**Usage:** Dashboard log pane loading spinner (`dashboard-log-pane.component.html:18`):
`<i class="fa fa-circle-o-notch fa-spin"></i>`
Mirrored in `dashboard-log-pane.component.spec.ts` inline template (line 29).

**Proposed icon:** `ph-circle-notch`

**Proposed spin approach:** A new local `@keyframes ph-spin` / `.ph-spin` CSS rule added to
`dashboard-log-pane.component.scss` (scoped). Phosphor 2.1.2 ships NO `ph-spin` animation
class — `fa-spin` was provided entirely by Font Awesome's CSS. Without a replacement rule
the spinner will freeze when FA is removed.

**Proposed CSS addition (RESEARCH §4 / §1d):**
```scss
// Phosphor does not ship a spin animation class; provide one locally.
@keyframes ph-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.ph-spin {
  animation: ph-spin 1s linear infinite;
  display: inline-block;
}
```

**Rationale (RESEARCH §5 Q5):** `ph-circle-notch` exists and is the loading arc icon —
a partial/notched circle identical in intent to FA's `fa-circle-o-notch`. The spin CSS must
be added before FA is removed (plan 105-02) or the spinner freezes.

**This sign-off confirms BOTH:**
1. `ph-circle-notch` as the replacement icon class.
2. Approval to add the local `@keyframes ph-spin` / `.ph-spin` CSS rule to
   `dashboard-log-pane.component.scss`.

**DECISION (icon + spin CSS rule):** _______________

---

### Q6 — `fa-th-large`

**Usage:** Nav bar "dashboard" icon — `app.component.ts` NAV_ICONS map (`app.component.ts:93`,
`dashboard: "fa-th-large"`). Rendered via `<i class="fa" [ngClass]="navIcon(...)">` in
`app.component.html:21`.

**Proposed:** `ph-squares-four`

**Rationale (RESEARCH §5 Q6):** `ph-squares-four` is a 2×2 grid icon — closest to FA's
`fa-th-large` (large-tile grid/dashboard view). `ph-grid-four` and `ph-grid-nine` also
exist; `ph-squares-four` best matches the "large tiles" / dashboard intent.

**Alternates:** `ph-grid-four` (grid of four smaller squares).

**DECISION:** _______________

---

### Q7 — `fa-sliders`

**Usage:** Settings "General Options" section header (`settings-page.component.html:32`)
and `options-list.ts:150` (dynamic icon data string).

**Proposed:** `ph-sliders-horizontal`

**Rationale (RESEARCH §5 Q7):** Both `ph-sliders` and `ph-sliders-horizontal` exist.
FA `fa-sliders` renders vertical sliders. `ph-sliders-horizontal` is more common for
"settings/equalizer" in modern UIs. Recommend horizontal for the equalizer appearance,
but `ph-sliders` (vertical) works equally well.

**Alternate:** `ph-sliders` (vertical variant — equally valid).

**DECISION:** _______________

---

### Q8 — `fa-file-code-o`

**Usage:** Settings "Server Script Path" option input field icon
(`settings-page.component.html:99` via `[icon]="'fa-file-code-o'"` binding).

**Proposed:** `ph-file-code`

**Rationale (RESEARCH §5 Q8):** `ph-file-code` exists. `ph-file-code-o` does not exist;
Phosphor drops the `-o` suffix. Intent is "script file / code file." Single usage.

**Alternate:** None.

**DECISION:** _______________

---

## Summary Table (all 39 classes — for quick reference)

| # | FA4 class | Proposed Phosphor class | Status |
|---|-----------|------------------------|--------|
| 1 | `fa-arrow-down` | `ph-arrow-down` | CONFIRMED |
| 2 | `fa-ban` | `ph-prohibit` | CONFIRMED |
| 3 | `fa-bell` | `ph-bell` | CONFIRMED |
| 4 | `fa-check` | `ph-check` | CONFIRMED |
| 5 | `fa-check-circle` | `ph-check-circle` | CONFIRMED |
| 6 | `fa-circle` | `ph-circle` | CONFIRMED |
| 7 | `fa-circle-o` | `ph-circle` | CONFIRMED |
| 8 | `fa-circle-o-notch` + `fa-spin` | `ph-circle-notch` + `.ph-spin` CSS rule | AWAITING SIGN-OFF (Q5) |
| 9 | `fa-clock-o` | `ph-clock` | CONFIRMED |
| 10 | `fa-cloud` | `ph-cloud` | CONFIRMED |
| 11 | `fa-cog` | `ph-gear` | CONFIRMED |
| 12 | `fa-copy` | `ph-copy` | CONFIRMED |
| 13 | `fa-database` | `ph-database` | CONFIRMED |
| 14 | `fa-download` | `ph-download` | CONFIRMED |
| 15 | `fa-exclamation-circle` | `ph-warning-circle` | CONFIRMED |
| 16 | `fa-exclamation-triangle` | `ph-warning` | CONFIRMED |
| 17 | `fa-expand` | `ph-arrows-out` | CONFIRMED |
| 18 | `fa-eye` | `ph-eye` | CONFIRMED |
| 19 | `fa-eye-slash` | `ph-eye-slash` | CONFIRMED |
| 20 | `fa-file-archive-o` | `ph-file-archive` (proposed) | AWAITING SIGN-OFF (Q4) |
| 21 | `fa-file-code-o` | `ph-file-code` (proposed) | AWAITING SIGN-OFF (Q8) |
| 22 | `fa-floppy-o` | `ph-floppy-disk` (proposed) | AWAITING SIGN-OFF (Q2) |
| 23 | `fa-folder-open-o` | `ph-folder-open` | CONFIRMED |
| 24 | `fa-hdd-o` | `ph-hard-drive` (proposed) | AWAITING SIGN-OFF (Q3) |
| 25 | `fa-info-circle` | `ph-info` | CONFIRMED |
| 26 | `fa-list` | `ph-list` | CONFIRMED |
| 27 | `fa-play` | `ph-play` | CONFIRMED |
| 28 | `fa-plus-circle` | `ph-plus-circle` | CONFIRMED |
| 29 | `fa-refresh` | `ph-arrows-clockwise` | CONFIRMED |
| 30 | `fa-search` | `ph-magnifying-glass` | CONFIRMED |
| 31 | `fa-server` | `ph-computer-tower` | CONFIRMED (see corrected mappings callout above) |
| 32 | `fa-shield` | `ph-shield` | CONFIRMED |
| 33 | `fa-sliders` | `ph-sliders-horizontal` (proposed) | AWAITING SIGN-OFF (Q7) |
| 34 | `fa-stop` | `ph-stop` | CONFIRMED |
| 35 | `fa-tachometer` | `ph-gauge` (proposed) | AWAITING SIGN-OFF (Q1) |
| 36 | `fa-tasks` | `ph-list-checks` | CONFIRMED |
| 37 | `fa-terminal` | `ph-terminal` | CONFIRMED |
| 38 | `fa-th-large` | `ph-squares-four` (proposed) | AWAITING SIGN-OFF (Q6) |
| 39 | `fa-times` | `ph-x` | CONFIRMED |
| 40 | `fa-trash` | `ph-trash` | CONFIRMED |

_Total: 32 confirmed · 8 awaiting sign-off (Q1–Q8)_

---

*Plan: 105-01 | D-01 artifact | Status: awaiting user sign-off on Q1–Q8*
