# Phase 104: Light Dependency Removals - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove two phantom Angular dependencies from `src/angular/package.json` — **jQuery 4** (DEPS-01a) and **css-element-queries** (DEPS-01c) — and verify the production build, bundle, and Bootstrap-driven interactions are unaffected. Both deps are confirmed to have **zero source usage** (see Existing Code Insights). Font Awesome → Phosphor (DEPS-01b) is Phase 105; mock-fixture bundle hygiene (DEPS-02) is Phase 106 — both out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Removal verification rigor
- **D-01:** "Unused" is proven by **both** the static grep evidence already gathered **and** a clean production build (`ng build --configuration production`) **plus** a manual smoke-test of the only jQuery-adjacent surface — Bootstrap dropdowns, modals, and collapses — before either dep is dropped. Static evidence alone is not sufficient to land the removal; the build must be green and the Bootstrap interactions verified working.

### Bundle-size proof
- **D-02:** The phase captures a **before/after production bundle-size delta** as evidence the deps actually left the build, satisfying the REQUIREMENTS "bundle does not grow" constraint. Record bundle stats (e.g. `ng build --configuration production` output / `stats.json`) before and after the removals so the change is measurable and the bundle is shown to shrink (or at worst not grow).

### Commit granularity
- **D-03:** The two removals land as **two atomic commits**, one per requirement — DEPS-01a (jQuery) and DEPS-01c (css-element-queries) — for clean traceability, even though they are independent phantom deps. Not a single combined commit.

### package-lock + audit handling
- **D-04:** `package-lock.json` is **regenerated** in the same change (via `npm install` after editing `package.json`) so the lockfile reflects the dropped deps. Any `npm audit` delta from the removal is **noted** but scope is NOT expanded to fixing unrelated advisories — this phase removes two deps, it does not take on a security-advisory remediation pass.

### Claude's Discretion
- Exact ordering of the two atomic commits (jQuery first or css-element-queries first) — either order is fine; they are independent.
- The precise mechanism for capturing bundle stats (build-output table vs `stats.json` vs `source-map-explorer`) — planner/executor picks the lightest reliable proof.
- Whether to run the existing Karma suite as part of verification in addition to the production build (recommended, since the floors must hold, but the smoke-test of Bootstrap interactions is the load-bearing check for jQuery).

</decisions>

<specifics>
## Specific Ideas

- jQuery 4 and css-element-queries are **phantom dependencies** — declared in `package.json` but referenced nowhere in source, not wired into the `angular.json` build `scripts` array, and (per `package-lock.json`) depended-on-by `(root)` only with no transitive consumers. The expected outcome is two clean deletions, not a refactor.
- The "audit usage → confirm unused → drop dep → verify build+bundle+CI" rhythm is the spine of this phase. If the build or Bootstrap smoke-test surfaces an *implicit* jQuery dependency that scouting missed, that becomes a scoped finding (REQUIREMENTS notes a jQuery hard-usage discovery is a finding, NOT a version bump).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — DEPS-01a (jQuery removal) and DEPS-01c (css-element-queries removal) acceptance text; Cross-Cutting Constraints (COMPAT no regression, CI green amd64+arm64, Karma floors 83/68/79/83 hold, bundle does not grow, **no tag/version work**).
- `.planning/ROADMAP.md` §"Phase 104: Light Dependency Removals" — phase goal and 5 success criteria.

### Source of the concern
- `.planning/codebase/CONCERNS.md` §"Dependencies at Risk" — jQuery 4.x ("no usages found; only Bootstrap consumed it"; BS5 doesn't require jQuery; audit `_bootstrap-overrides.scss` + `@popperjs/core`) and css-element-queries ("unmaintained; superseded by ResizeObserver; search for usages and replace, or drop if unused").

### Project constraints
- `.planning/PROJECT.md` Key Decisions — "Keep @import for Bootstrap SCSS" / "Bootstrap 5.3 data-bs-theme for dark mode" (Bootstrap stays as-is; this phase does not touch Bootstrap itself, only confirms jQuery isn't needed by it).

No new external specs/ADRs for this phase — requirements are fully captured above and in the decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Scouting evidence (gathered during discuss, 2026-05-31) is the load-bearing input:
  - **jQuery:** zero hits across `src/**` (`.ts`/`.html`/`.scss`/`.json`); `src/index.html` has no `<script>` tags (favicon links only); `src/main.ts` + `src/polyfills.ts` import neither jQuery nor css-element-queries; `package-lock.json` shows jquery depended-on-by `(root)` only. The `$(` matches in `.ts` are RxJS observable naming (`stats$`, `toasts$`), not jQuery.
  - **css-element-queries:** zero hits anywhere (no `ResizeSensor`, no `ElementQueries`, no import).

### Established Patterns
- `src/angular/angular.json` build config: the `scripts` array loads **only** `node_modules/bootstrap/dist/js/bootstrap.bundle.min.js` (bundles Popper, requires no jQuery in Bootstrap 5). The `styles` array loads `font-awesome/css/font-awesome.css` + three `@phosphor-icons/web` styles (relevant to Phase 105, not 104). jQuery is NOT in the `scripts` array — confirming it isn't even loaded at runtime.
- `@popperjs/core ^2.11.8` is a direct dependency — Bootstrap 5's positioning engine, fully jQuery-independent. It stays.
- Bootstrap interactions in the app (dropdowns, modals, collapses) are driven by `bootstrap.bundle.min.js`, which is the surface to smoke-test after jQuery removal.

### Integration Points
- Only file changed for the removals: `src/angular/package.json` (drop `jquery` and `css-element-queries` from `dependencies`) + regenerated `src/angular/package-lock.json`.
- Verification touches the Angular production build (`ng build --configuration production`) and the Docker/CI Angular path (must stay green on amd64+arm64). No `.ts`/`.html`/`.scss` source edits are expected unless the build surfaces a hidden usage.

</code_context>

<deferred>
## Deferred Ideas

- **Font Awesome 4.7 → Phosphor (DEPS-01b)** — Phase 105. The heaviest dep item (template `fa-*` inventory + per-icon replacement); explicitly out of scope here.
- **Mock-fixture bundle hygiene (DEPS-02)** — Phase 106.
- **Backend dependency hardening** (paste/bottle server swap, pexpect, patoolib upper-bounds) — REQUIREMENTS Out of Scope; a later milestone, not this frontend slice.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — backend/upstream-blocked; not related to frontend deps. Not folded.
- `2026-04-24-migrate-config-set-to-post-body` — backend API change (PROJECT.md Out of Scope); separate milestone. Not folded.

</deferred>

---

*Phase: 104-light-dependency-removals*
*Context gathered: 2026-05-31*
