# Phase 105: Font Awesome to Phosphor Migration - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace every remaining `fa-*` (Font Awesome 4.7) icon usage in the Angular app with its `@phosphor-icons/web` equivalent, then remove the `font-awesome` dependency from `src/angular/package.json` and the two `font-awesome/css/font-awesome.css` entries from `angular.json` (dev + prod `styles` arrays). The in-progress FA→Phosphor migration (Phosphor is already wired and used in `about`, `settings`, `transfer-table`) is **completed** here so only one icon library ships. DEPS-01a (jQuery) and DEPS-01c (css-element-queries) shipped in Phase 104; mock-fixture bundle hygiene (DEPS-02) is Phase 106 — both out of scope. This slice cuts **no** git tag.

</domain>

<decisions>
## Implementation Decisions

### Icon mapping fidelity
- **D-01:** Claude produces a **complete fa→ph mapping table for all ~39 distinct `fa-*` classes** in use. The obvious 1:1 mappings (e.g. `fa-bell`→`ph-bell`, `fa-trash`→`ph-trash`, `fa-cloud`→`ph-cloud`, `fa-search`→`ph-magnifying-glass`, `fa-times`→`ph-x`, `fa-eye`/`fa-eye-slash`→`ph-eye`/`ph-eye-slash`, `fa-download`→`ph-download`, `fa-play`/`fa-stop`→`ph-play`/`ph-stop`) are auto-applied. For the **~8 icons with no exact Phosphor twin**, Claude proposes a closest-intent pick with rationale and **pauses for user sign-off on those ambiguous ones only, before any replacement code lands**. Ambiguous set to surface for sign-off (proposed picks are starting points, not locked): `fa-tachometer` (→ph-gauge?), `fa-floppy-o` (→ph-floppy-disk?), `fa-hdd-o` (→ph-hard-drive?), `fa-file-archive-o` (→ph-file-archive / ph-file-zip?), `fa-circle-o-notch` + `fa-spin` (→ph-circle-notch + ph-spin?), `fa-th-large` (→ph-squares-four?), `fa-sliders` (→ph-sliders / ph-sliders-horizontal?), `fa-file-code-o` (→ph-file-code?). Also confirm: `fa-refresh`→`ph-arrows-clockwise`, `fa-cog`→`ph-gear`, `fa-tasks`→`ph-list-checks`, `fa-shield`→`ph-shield`, `fa-ban`→`ph-prohibit`, `fa-clock-o`→`ph-clock`, `fa-folder-open-o`→`ph-folder-open`, `fa-expand`→`ph-arrows-out`.

### Weight / style convention
- **D-02:** Migrated icons default to **regular `ph` weight** — FA4 was effectively a single regular weight, so this is the closest visual match and the least surprising. Where an icon currently carries emphasis via SCSS or context (status indicators, the loading spinner), **preserve that existing intent**, but do **not** introduce new `ph-bold` / `ph-fill` weights the app didn't already have for that icon. The existing deliberate `ph-bold` / `ph-fill` usages in already-migrated templates (about page `ph-fill ph-scales`, settings `ph-bold` headers) are left as-is.

### Test-spec assertions
- **D-03:** The 4 unit specs that reference FA classes are **updated faithfully to the exact Phosphor class the component now renders** — both the `querySelector` presence assertions (`.fa-search`→`.ph-magnifying-glass`, `.stat-icon.fa-cloud`→`.stat-icon.ph-cloud`, etc.) and the inline host-template strings (`'fa fa-bell'`→`'ph ph-bell'`). No loosening to library-agnostic assertions and no new `data-testid` hooks — the specs continue to verify the real rendered icon class. Karma `check.global` floors (stmts/branches/fns/lines 83/68/79/83) must hold or rise.

### Visual verification depth
- **D-04:** Proof that "no icon renders missing or visually degraded" follows the **Phase 104 D-01 rhythm: a dev-server manual smoke test**. After the production build is green, every page/surface that previously rendered an `fa-*` icon is exercised on a dev server and each icon is confirmed to render a visible Phosphor glyph (no blank squares / no missing-glyph console errors). Surfaces to cover: dashboard stats strip, transfer rows, bulk-actions bar, settings page (incl. dynamic `option`/`settings-page` `{{icon}}` binding + conditional toggle states: password eye, copied check, token reveal), logs page (search, autoscroll toggle, clear, export, clock), dashboard log pane (terminal, copy, expand, spinner), notification bell. No Playwright screenshot harness required for this phase.

### Migration surface (locked scope of edits)
- **D-05:** The migration is **not** HTML-only. All of these layers are in scope and must be migrated together so no `fa-*` string remains in production-relevant files:
  1. **`.html` templates** — direct `fa fa-*` and conditional `[class.fa-*]` bindings.
  2. **`options-list.ts`** — icon **data strings** (`icon: "fa-server"`, `"fa-search"`, `"fa-tachometer"`, `"fa-sliders"`, `"fa-list"`, `"fa-trash"`, `"fa-file-archive-o"`).
  3. **Dynamic icon binding** — `option.component.html` (`<i class="fa {{icon}}">`) and `settings-page.component.html` (`<i class="fa {{icon}}">`) render the strings from #2; the binding's static prefix (`fa`) and the data strings must move to Phosphor (`ph` + `ph-*`) consistently, or the rendered class won't form a valid Phosphor icon.
  4. **Conditional class bindings** — `[class.fa-eye]`/`[class.fa-eye-slash]`, `[class.fa-check]`/`[class.fa-copy]`, `[class.fa-check-circle]`/`[class.fa-circle-o]` (settings, logs).
  5. **`.scss` selectors keyed on `.fa-*`** — re-point to the new Phosphor classes: `settings-page.component.scss` (`i.fa` → also `i.ph` already present; `.fa-check` color rules; `i.fa{color:$danger}`), `logs-page.component.scss` (`&--active .fa-check-circle`, `.fa-circle-o`), `dashboard-log-pane.component.scss` (`.fa-terminal`). Leave the existing `i.ph` rules intact and fold the `i.fa`-only rules into them where appropriate.
  6. **Test specs** — per D-03.

### Drop the dependency (the closing act)
- **D-06:** Only **after** all usages are migrated and the build + smoke test are green, remove `font-awesome` from `src/angular/package.json` dependencies, remove the two `node_modules/font-awesome/css/font-awesome.css` lines from `angular.json` (build + test/serve `styles` arrays), and regenerate `package-lock.json` via `npm install` (Phase 104 D-04 pattern). A grep over the built `dist` and over `src/angular/src/` confirms zero remaining `fa-` class strings in production-relevant files and no Font Awesome CSS/font files in the bundle.

### Bundle-size proof
- **D-07:** Capture a **before/after production bundle-size delta** (Phase 104 D-02 pattern) showing the Font Awesome CSS + font files left the bundle and total size is equal-to-or-smaller than the Phase 104 baseline.

### Claude's Discretion
- Exact final Phosphor class for each **non-ambiguous** icon (the obvious 1:1 set in D-01).
- Commit granularity within the phase (e.g. migrate-by-component-cluster vs one large migration commit, with the dep drop as the final atomic commit) — planner's call, but the `font-awesome` drop should be its own clean closing commit per the audit→migrate→drop→verify rhythm.
- The precise mechanism for capturing bundle stats (build-output table vs `stats.json`).
- Whether to also run the full Karma suite during verification in addition to the targeted specs (recommended, since floors must hold).

</decisions>

<specifics>
## Specific Ideas

- The Phosphor convention already established in-repo is `<i class="ph ph-{name}"></i>` for regular, `ph-bold ph-{name}` and `ph-fill ph-{name}` for the heavier weights — follow it exactly (seen in `about-page.component.html`, `settings-page.component.html`, `transfer-table.component.html`).
- Phosphor (`@phosphor-icons/web ^2.1.2`) and its three weight stylesheets (regular/bold/fill) are **already loaded** in `angular.json` — no new dependency or build wiring is needed to *add* Phosphor; this phase only *removes* the Font Awesome half.
- This is the **heaviest item in slice 3** (per Phase 104 CONTEXT) — unlike 104's phantom-dep deletions, it requires real source edits across HTML, TS data, conditional bindings, SCSS, and specs. Expect the bulk of the work to be the careful per-icon mapping + the dynamic-binding/data-string layer, not the dep removal itself.
- `fa-circle` and `fa-circle-o` appear in logs (autoscroll toggle) and as a generic shape; map the filled vs outline distinction deliberately (Phosphor `ph-circle` is outline, `ph-fill ph-circle` is filled) so the toggle's on/off visual difference survives.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — **DEPS-01b** acceptance text ("no longer depends on Font Awesome 4.7; every `fa-*` usage inventoried and replaced with `@phosphor-icons/web` equivalent; FA dep removed; no icon renders missing or visually regressed; only one icon library ships") and Cross-Cutting Constraints (COMPAT no regression, CI green amd64+arm64, Karma floors 83/68/79/83 hold, Python `fail_under` ≥ 88 unchanged, bundle does not grow, **no tag/version work**).
- `.planning/ROADMAP.md` §"Phase 105: Font Awesome to Phosphor Migration" — phase goal and the 5 success criteria (inventory documented → every class replaced → dep removed + clean build → visual smoke test → CI green + bundle ≤ Phase 104 baseline).

### Source of the concern
- `.planning/codebase/CONCERNS.md` §"Dependencies at Risk" → "`font-awesome` 4.7 (legacy)" (lines ~235-239) — FA4 is EOL, duplicate icon libraries shipped, migration plan = inventory `fa-*` and replace with Phosphor then drop the dep.

### Sibling-phase rhythm (decisions to mirror)
- `.planning/milestones/v1.3.0-phases/104-light-dependency-removals/104-CONTEXT.md` — the audit→confirm→drop→verify-build+bundle+CI rhythm; D-01 (build-green + manual smoke test before drop), D-02 (before/after bundle delta), D-04 (regenerate package-lock, note-don't-fix audit deltas). Phase 105 reuses D-01/D-02/D-04 patterns (carried here as D-04/D-07/D-06).

### Project constraints
- `.planning/PROJECT.md` Key Decisions — Bootstrap/icon/theming conventions; this phase touches only the icon library, not Bootstrap or theming.

No new external specs/ADRs for this phase — requirements are fully captured above and in the decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phosphor is already wired and in active use** — `@phosphor-icons/web ^2.1.2` in `src/angular/package.json:24`; `angular.json` lines 39-41 (build) and 108-110 (test/serve) load the regular/bold/fill stylesheets. Reference usages: `about-page.component.html` (`ph ph-info`, `ph ph-github-logo`, `ph ph-book`, `ph ph-bug`, `ph ph-git-commit`, `ph-fill ph-scales`), `settings-page.component.html` (`ph-bold` section headers), `transfer-table.component.html`.
- **Inventory (gathered during discuss, 2026-06-01):** ~85 lines contain `fa-` across `src/angular/src/`; **~39 distinct `fa-*` icon classes** in use. Distinct set: arrow-down, ban, bell, check, check-circle, circle, circle-o, circle-o-notch, clock-o, cloud, cog, copy, database, download, exclamation-circle, exclamation-triangle, expand, eye, eye-slash, file-archive-o, file-code-o, floppy-o, folder-open-o, hdd-o, info-circle, list, play, plus-circle, refresh, search, server, shield, sliders, stop, tachometer, tasks, terminal, th-large, times, trash (+ `fa-spin` animation modifier).

### Established Patterns
- **Five distinct edit layers** (see D-05): direct HTML classes; `options-list.ts` icon data strings; dynamic `<i class="fa {{icon}}">` bindings in `option.component.html` + `settings-page.component.html` (these render the data strings — both the prefix and the strings must migrate together); conditional `[class.fa-*]` toggle bindings; `.scss` selectors keyed on `.fa-*`.
- SCSS already pairs `i.fa, i.ph` in several `settings-page.component.scss` rules — Font Awesome and Phosphor are mid-migration in the same selectors; the migration consolidates onto `i.ph`/`.ph-*`.
- `fa-spin` is used exactly once (`dashboard-log-pane.component.html:18` loading spinner, mirrored in its spec) → Phosphor's `ph-spin` animation class.

### Integration Points
- Files touched (source): `pages/settings/settings-page.component.html` + `.scss`, `pages/settings/option.component.html`, `pages/settings/options-list.ts`, `pages/files/stats-strip.component.html`, `pages/files/transfer-row.component.html`, `pages/files/bulk-actions-bar.component.html`, `pages/files/dashboard-log-pane.component.html` + `.scss`, `pages/files/transfer-table.component.html`, `pages/logs/logs-page.component.html` + `.scss`.
- Files touched (test): `tests/unittests/pages/files/transfer-table.component.spec.ts`, `tests/unittests/pages/files/stats-strip.component.spec.ts`, `tests/unittests/pages/files/dashboard-log-pane.component.spec.ts`, `tests/unittests/pages/main/notification-bell.component.spec.ts`.
- Files touched (config, closing act): `src/angular/package.json` (drop `font-awesome`), `src/angular/angular.json` (remove 2 FA css lines), `src/angular/package-lock.json` (regenerated).
- Verification touches the Angular production build (`ng build --configuration production`), the dev-server smoke test, and the Docker/CI Angular path (must stay green amd64+arm64).

</code_context>

<deferred>
## Deferred Ideas

- **Mock-fixture bundle hygiene (DEPS-02)** — Phase 106. Out of scope here.
- **Backend dependency hardening** (paste/bottle server swap, pexpect, patoolib upper-bounds) — REQUIREMENTS Out of Scope; a later milestone, not this frontend slice.
- **Adding `data-testid`/aria hooks for icons** — considered for test robustness (D-03 option C) but rejected as scope creep beyond an icon-library migration. Revisit if a future phase introduces a general test-hook convention.
- **Playwright screenshot-diff harness for icon regression** — considered for verification (D-04 option B) but deferred; dev-server smoke test matches the sibling-phase rhythm. A reusable visual-regression harness could be its own infra phase.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — backend/upstream-blocked Python item; unrelated to frontend icon migration. Matched only on generic keywords (score 0.6). Not folded.
- `2026-04-24-migrate-config-set-to-post-body` — backend API change (PROJECT.md Out of Scope, separate milestone). Matched only on generic keywords (score 0.6). Not folded.

</deferred>

---

*Phase: 105-font-awesome-to-phosphor-migration*
*Context gathered: 2026-06-01*
