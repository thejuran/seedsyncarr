# Phase 104: Light Dependency Removals — Research

**Researched:** 2026-06-01
**Domain:** Angular npm dependency removal, bundle verification, Bootstrap 5 jQuery independence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (removal verification rigor):** "Unused" is proven by both static grep evidence AND a clean production build (`ng build --configuration production`) plus a manual smoke-test of Bootstrap dropdowns, modals, and collapses before either dep is dropped. Static evidence alone is not sufficient.
- **D-02 (bundle-size proof):** The phase captures a before/after production bundle-size delta as evidence the deps actually left the build. Record `ng build --configuration production` output stats before and after — bundle must shrink (or at worst not grow).
- **D-03 (commit granularity):** Two atomic commits, one per requirement — DEPS-01a (jQuery) first (or second), then DEPS-01c (css-element-queries). Not a single combined commit.
- **D-04 (lockfile + audit):** `package-lock.json` is regenerated in the same change (via `npm install` after editing `package.json`). Any `npm audit` delta from the removal is noted but scope is NOT expanded to fix unrelated advisories.

### Claude's Discretion

- Ordering of the two atomic commits (jQuery first or css-element-queries first).
- The precise mechanism for capturing bundle stats (build-output table vs `stats.json` vs `source-map-explorer`).
- Whether to run the existing Karma suite as part of verification in addition to the production build.

### Deferred Ideas (OUT OF SCOPE)

- Font Awesome 4.7 → Phosphor (DEPS-01b) — Phase 105.
- Mock-fixture bundle hygiene (DEPS-02) — Phase 106.
- Backend dependency hardening (paste, bottle, pexpect, patoolib) — later milestone.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPS-01a | Remove jQuery 4 from `src/angular/package.json` after confirming no source usage; Bootstrap-driven interactions still work; bundle no longer ships jQuery. | Verified zero usage in source; Bootstrap 5 does not require jQuery; esbuild tree-shaking prevents phantom deps from entering the bundle. |
| DEPS-01c | Remove css-element-queries from `src/angular/package.json` after confirming no source usage (or replace with ResizeObserver); element-resize behavior unchanged. | Verified zero usage in source; no replacement needed (nothing to replace). |
</phase_requirements>

---

## Summary

Phase 104 removes two phantom npm dependencies — `jquery ^4.0.0` and `css-element-queries ^1.1.1` — from `src/angular/package.json`. Both are confirmed dead weight: a fresh live audit of `src/angular/src/` finds zero imports, zero dynamic uses, and zero references in SCSS or HTML templates for either library. Neither appears in the `angular.json` `scripts` or `styles` arrays, and neither is a transitive dependency of any retained package.

Bootstrap 5.3 uses only `@popperjs/core` for JS-driven behavior (tooltips/positioning); its optional `window.jQuery` detection in `bootstrap.bundle.min.js` is a graceful no-op when jQuery is absent — not a hard dependency. The current production dist already ships without jQuery code (confirmed by searching for jQuery's distinctive factory string in the dist files). The single `"css-element-queries"` string that appears in the current `main-YFVXCCK6.js` is package.json metadata embedded by Angular's license extractor — not library code. After removal from `package.json`, that metadata reference will also disappear.

The removal rhythm is: (1) record pre-removal bundle sizes from `ng build --configuration production` output, (2) delete the dep from `package.json`, (3) run `npm install` to regenerate `package-lock.json`, (4) run production build and confirm bundle shrinks, (5) grep `dist/` for residual library code, (6) smoke-test Bootstrap CSS interactions in the dev server. No source edits are expected; the risk of a hidden usage is extremely low and well-understood (see Pitfall 1 below).

**Primary recommendation:** Delete both entries from `src/angular/package.json`, run `npm install`, run `ng build --configuration production`, compare bundle sizes to pre-removal baseline, and confirm zero residual library strings in dist. Two atomic commits (D-03). No source changes unless the build surfaces a hidden usage.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dependency declaration | Frontend build (package.json) | — | npm manifest governs what is installed and available for bundling |
| Bundle composition | Frontend build (esbuild via @angular/build:application) | — | esbuild tree-shakes unused modules; phantom deps don't enter the bundle |
| Bootstrap JS interactions (dropdowns, modals) | Browser (bootstrap.bundle.min.js via scripts array) | — | Bootstrap 5 plugins operate on data-bs-* attributes without jQuery |
| Karma test coverage floors | CI / test runner | — | karma.conf.js enforces stmts/branches/fns/lines 83/68/79/83 |
| Lockfile regeneration | Frontend build (npm install) | CI Docker | package-lock.json v3 is regenerated by npm install after package.json edit |

---

## Standard Stack

This phase makes no new installations. For completeness, the retained Angular build stack that the verification pipeline exercises:

### Core (retained — do not change)
| Library | Version in package.json | Purpose | Notes |
|---------|------------------------|---------|-------|
| `bootstrap` | `^5.3.3` | CSS + optional JS plugins | jQuery-free since Bootstrap 4; v5.3 confirmed |
| `@popperjs/core` | `^2.11.8` | Positioning engine for Bootstrap tooltips | Stays; not jQuery |
| `@angular/build` | `^21.2.12` | esbuild-based builder (`@angular/build:application`) | Produces `ng build` output table |
| `@angular/cli` | `^21.2.12` | `ng` CLI | Used in Docker build + local |

### Packages being removed
| Library | Version | Registry | Disposition |
|---------|---------|----------|-------------|
| `jquery` | `^4.0.0` (locked at `4.0.0`) | npm | REMOVE (phantom dep, no source usage) |
| `css-element-queries` | `^1.1.1` (locked at `1.2.3`) | npm | REMOVE (phantom dep, no source usage) |

**Removal command (for each dep — run `npm install` after each edit, or after both edits for combined lockfile regeneration):**
```bash
cd src/angular
# Edit package.json to remove the dep (manual edit or npm uninstall)
npm uninstall jquery          # removes from package.json + regenerates lockfile
npm uninstall css-element-queries  # same
```

Alternatively, edit `package.json` manually and run `npm install` once — either approach regenerates `package-lock.json` correctly. The Docker build uses `npm install --include=dev --legacy-peer-deps`; the `--legacy-peer-deps` flag is pre-existing (required for unrelated peer dep conflicts in the Angular 21 tree, not related to these removals) and must be preserved in the Dockerfile.

---

## Package Legitimacy Audit

> This phase **removes** packages — no new external packages are installed. The legitimacy audit is N/A for removals. Packages are listed only for completeness.

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| `jquery` | npm | ~15 yrs (v4.0.0 released 2024) | N/A — removing | REMOVE |
| `css-element-queries` | npm | ~8 yrs (last release 2019 per CONCERNS.md) | N/A — removing | REMOVE |

**Packages removed due to slopcheck [SLOP] verdict:** none — removals are not slopcheck candidates.

---

## Phantom-Dependency Audit — Live Verification Results

The following confirms both deps are true phantoms (zero usage) as of 2026-06-01:

### jQuery (`jquery ^4.0.0`)

**Grep command and results:**
```bash
# Production source (*.ts, *.html, *.scss)
grep -rn "jquery\|jQuery" src/angular/src/ --include="*.ts" --include="*.html" --include="*.scss"
# Result: 0 matches
```

**False-positive pattern to distinguish:** `$(` appearing in `.ts` files is RxJS observable naming (`stats$`, `toasts$`, `selectedCount$`) — these are `$`-suffixed Observable names, not jQuery selectors. The grep above confirms zero `jquery`/`jQuery` string matches; none of the `$(` patterns are jQuery calls. [VERIFIED: live grep 2026-06-01]

**index.html:** Only `<link>` tags for favicons — no `<script src="jquery">`. [VERIFIED: live file read]

**angular.json scripts array:** Contains only `"node_modules/bootstrap/dist/js/bootstrap.bundle.min.js"`. jQuery is absent. [VERIFIED: live read]

**package-lock.json dependents:** `jquery` is depended-on only by `""` (the root package) — no transitive consumers. [VERIFIED: live parse]

**Current dist:** `"jQuery JavaScript Library"` factory string is absent from `dist/main-YFVXCCK6.js` and `dist/scripts-TTWY4XDY.js`. The only jQuery-related text in the dist is `window.jQuery` appearing twice in `scripts-TTWY4XDY.js` (the Bootstrap bundle's optional jQuery detection — a conditional no-op when `window.jQuery` is undefined). [VERIFIED: live grep]

**Bootstrap 5 jQuery relationship:** `bootstrap.bundle.min.js` contains `f=()=>window.jQuery&&!document.body.hasAttribute("data-bs-no-jquery")?window.jQuery:null` — Bootstrap's jQuery plugin wrapper activates ONLY when `window.jQuery` is already defined. It is never loaded in this app. Bootstrap 5 operates entirely without jQuery. [VERIFIED: live source read]

**Conclusion:** DEPS-01a is a clean deletion. No source edits needed.

---

### css-element-queries (`css-element-queries ^1.1.1`, installed at `1.2.3`)

**Grep command and results:**
```bash
grep -rn "css-element-queries\|ResizeSensor\|ElementQueries" src/angular/src/
# Result: 0 matches (exit code 1 — no matches)
```

**Also checked:** spec files, SCSS imports, `angular.json` styles array — zero references. [VERIFIED: live grep 2026-06-01]

**package-lock.json dependents:** Depended-on only by `""` (root) — no transitive consumers. [VERIFIED: live parse]

**Current dist:** The one occurrence of `"css-element-queries"` in `dist/main-YFVXCCK6.js` is the package.json metadata embedded by Angular's license extractor (a JSON blob listing all dependencies). It is NOT library code: `ResizeSensor` and `ElementQueries` strings return 0 matches from the dist. [VERIFIED: live grep]

**Conclusion:** DEPS-01c is a clean deletion. No ResizeObserver replacement is needed (nothing to replace). No source edits needed.

---

## Architecture Patterns

### System Architecture Diagram

```
package.json                   angular.json                    dist/
(dep declaration)              (build config)                  (output)
     |                              |                              |
     v                              v                              v
npm install              @angular/build:application          main-[hash].js
  |                      (esbuild, AOT, tree-shaking)        scripts-[hash].js  <- bootstrap.bundle.min.js only
  v                              |                            styles-[hash].css
node_modules/                   |                            polyfills-[hash].js
  jquery/           -----> NOT IMPORTED -----> NOT IN BUNDLE
  css-element-queries/ -> NOT IMPORTED -----> NOT IN BUNDLE
  bootstrap/        -----> scripts array -----> scripts-[hash].js (jQuery-optional, no-op)
  @popperjs/core    -----> via bootstrap -----> embedded in bootstrap.bundle
```

**Key insight:** esbuild in `@angular/build:application` tree-shakes unused imports. Because no `.ts` file imports `jquery` or `css-element-queries`, they never enter the bundle even while they're in `node_modules`. This is why the current dist already has no jQuery code despite the package being installed. Removing them from `package.json` makes the phantom nature explicit and shrinks `node_modules` and `package-lock.json`.

### Recommended Execution Structure

```
Wave 1 (per D-03: two atomic commits):
  Commit 1 — DEPS-01a: remove jquery from package.json + npm install → lockfile regenerated
  Commit 2 — DEPS-01c: remove css-element-queries from package.json + npm install → lockfile regenerated

Verification (after both removals):
  - ng build --configuration production → compare output table to baseline
  - grep dist/ for residual strings
  - ng serve → smoke-test Bootstrap CSS interactions
  - ng test --browsers ChromeHeadless → Karma floors hold
```

### Anti-Patterns to Avoid

- **Grepping `dist/` for `"jquery"` as a pass/fail test:** The string appears in Bootstrap's bundle (the optional `window.jQuery` detection). A better signal is the absence of `"jQuery JavaScript Library"` (the jQuery factory header) and the absence of `"ResizeSensor"` or `"ElementQueries"`.
- **Treating the `"css-element-queries"` reference in `main.js` as a real dependency:** It is package.json metadata embedded by the license extractor. After removal from `package.json`, this string will no longer appear.
- **Assuming `--legacy-peer-deps` was only needed for jquery/css-element-queries:** The Docker build uses this flag for pre-existing Angular 21 peer dep conflicts. It must be preserved as-is.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bundle size tracking | Custom webpack plugin, stats.json parser | `ng build --configuration production` output table printed to stdout | Angular 21 esbuild builder prints "Initial Chunk Files" table with raw and estimated transfer sizes — that table IS the before/after record |
| Checking for residual dep code | Decompiling minified JS | `grep -l "jQuery JavaScript Library"` and `grep -l "ResizeSensor"` in `dist/` | jQuery has a distinctive factory header; css-element-queries exports ResizeSensor — these strings are reliable presence indicators |
| Lockfile management | Manual lockfile editing | `npm install` (or `npm uninstall <pkg>`) | npm automatically regenerates package-lock.json v3 after any package.json change |

**Key insight:** This is a deletion phase. The planner should not introduce tooling (source-map-explorer, webpack-bundle-analyzer) for a one-time size check — the built-in build output table is sufficient evidence.

---

## Bundle/Build Verification Approach

### Before/After Record

The `ng build --configuration production` output table is the cheapest reliable delta record. It looks like:

```
Initial Chunk Files              | Names    | Raw Size  | Estimated Transfer Size
main-YFVXCCK6.js                 | main     | 573.84 kB |               165.00 kB
scripts-TTWY4XDY.js              | scripts  |  80.45 kB |                26.00 kB
polyfills-B7LGQ2G6.js            | polyfills |  35.78 kB |                11.00 kB
...
```

**Procedure:**
1. Before any edit: run `ng build --configuration production` and record the output table (copy to a `BEFORE.txt` or include in commit message).
2. After both removals: run again and compare. Sizes should be equal (jquery/css-element-queries were never in the bundle) or marginally smaller (license metadata removal).

**Note:** Because neither dep was bundled, the size delta will be zero or very small. The point of D-02 is to prove no regression, not a large savings. The removal of license metadata from `main.js` may produce a tiny shrinkage.

### Residual String Verification

```bash
# After build, confirm no jQuery library code:
grep -l "jQuery JavaScript Library" dist/*.js
# Expected: no matches

# Confirm no ResizeSensor/ElementQueries code:
grep -l "ResizeSensor\|ElementQueries" dist/*.js
# Expected: no matches (0 matches is passing)

# The `window.jQuery` in scripts-[hash].js from Bootstrap is acceptable — it's not jQuery the library.
```

### No stats.json Available

The `@angular/build:application` esbuild builder does not produce a `stats.json` by default (that was `@angular-devkit/build-angular:browser`'s feature). Do not attempt `ng build --stats-json` — it will error. The stdout output table is the correct approach. [VERIFIED: checked angular.json builder type and options]

---

## npm/Lockfile Mechanics

**What `npm install` does after editing `package.json`:** [ASSUMED — standard npm v11 behavior]

1. Reads the updated `package.json`.
2. Computes the required tree. Since jquery and css-element-queries have no dependents, their removal simply removes them from the lockfile.
3. Writes a new `package-lock.json` v3 (confirmed lockfileVersion: 3 in the repo).
4. Runs `npm prune` semantics — deletes `node_modules/jquery` and `node_modules/css-element-queries`.

**`--legacy-peer-deps` requirement:** The Docker build runs `npm install --include=dev --legacy-peer-deps`. This flag is for pre-existing peer dep conflicts in the Angular 21 ecosystem (unrelated to jQuery/css-element-queries). The flag must remain in the Dockerfile; the removals do not affect or resolve this.

**npm audit after removal:** Current audit shows 4 moderate vulns: `brace-expansion`, `engine.io`, `socket.io-adapter`, `ws`. None are attributable to `jquery` or `css-element-queries`. After removal, the audit count should remain 4 (or decrease, not increase). Per D-04: note the delta, do not pursue unrelated advisories. [VERIFIED: live npm audit run]

**Peer dep warnings:** Neither `jquery@4.0.0` nor `css-element-queries@1.2.3` declare `peerDependencies`. No remaining package in `package.json` lists either as a `peerDependency`. No removal-attributable peer dep warnings are expected. [VERIFIED: live npm view + lockfile analysis]

---

## Bootstrap-5-Without-jQuery Smoke Test

Bootstrap 5 dropped its jQuery dependency in v5.0 (released 2021). The app's Bootstrap interactions work via:

- **CSS classes only** for dropdowns, modals, collapses — inspecting all Angular templates finds zero `data-bs-toggle` or `data-bs-target` attributes; the app does not use Bootstrap's JS plugin API (`new bootstrap.Modal()`, etc.). [VERIFIED: live grep]
- **`bootstrap.bundle.min.js` via `scripts` array** — this bundles Popper + Bootstrap JS. The `window.jQuery` check in this bundle is entirely optional: `f=()=>window.jQuery&&...?window.jQuery:null` returns `null` and Bootstrap continues to function. [VERIFIED: live source read]
- **Confirm modal (`ConfirmModalService`)** — was reworked in Phase 103 (BUG-01) to use `Renderer2.createElement/createText` — not Bootstrap's `Modal` class and not jQuery. [VERIFIED: live source read]

**Smoke-test surface (what to exercise after removal):**

| UI Area | What to Verify | Bootstrap Component |
|---------|---------------|---------------------|
| Nav bar | Navigation renders, links work | Bootstrap CSS (nav, navbar) |
| Notification bell | Bell icon dropdown opens/closes | Custom Angular component (not Bootstrap JS Dropdown) |
| Dashboard | File rows render; stats strip shows | Bootstrap CSS layout |
| Bulk action bar | Multi-select, action buttons | Angular component state |
| Settings page | Form controls, inputs render | Bootstrap CSS form classes |
| Confirm modal | Delete/stop/queue confirmations | Angular Renderer2 (Phase 103 fix) |

**Browser console:** After removing jQuery, `window.jQuery` will be `undefined`. Bootstrap's bundle will function exactly as before — no console errors expected.

**How to detect a hidden usage:** If jQuery IS somehow wired in (not found by grep), the symptom would be a build error ("Cannot resolve 'jquery'") if it's a static import, or a runtime `TypeError: $ is not a function` in the browser console. Neither is expected based on the audit, but this is the fallback signal to watch for.

---

## Common Pitfalls

### Pitfall 1: `$(` in TypeScript Mistaken for jQuery
**What goes wrong:** A grep for `\$` or `\$\(` in `.ts` files returns many hits (RxJS stream names: `stats$`, `toasts$`, `selectedCount$`, `hasSelection$`, `files$`).
**Why it happens:** RxJS convention names Observables with a `$` suffix.
**How to avoid:** Grep for `"jquery"`, `"jQuery"`, or `import.*jquery` — not for `$(` or `\$`. The live audit confirms zero jQuery-keyword matches. [VERIFIED]
**Warning signs:** A grep returning zero matches for `jquery` (case-insensitive) is the correct clean signal.

### Pitfall 2: Confusing Bootstrap's `window.jQuery` Check with a jQuery Dependency
**What goes wrong:** Seeing `window.jQuery` in the `scripts-[hash].js` dist file and concluding jQuery is required.
**Why it happens:** Bootstrap 5 ships an optional jQuery plugin adapter that activates ONLY if `window.jQuery` is already defined. It is not a hard dependency.
**How to avoid:** Look for `"jQuery JavaScript Library"` (jQuery's own factory header) — absence means jQuery the library is not bundled. The `window.jQuery` check is Bootstrap's code, not jQuery's code.
**Warning signs:** If Bootstrap's optional detection fires incorrectly, it would be a console warning, not a hard failure.

### Pitfall 3: Treating the License-Metadata `"css-element-queries"` String as Code
**What goes wrong:** Grepping `dist/main.js` for `"css-element-queries"` returns 1 match and concludes the library is still in the bundle after removal.
**Why it happens:** Angular's `extractLicenses: true` (production config) embeds a JSON blob of package.json dependency names for license attribution. This is metadata, not code.
**How to avoid:** The specific string to watch for the library is `"ResizeSensor"` or `"ElementQueries"` (the library's own exports). After removal from `package.json`, the metadata reference will also disappear from the blob. [VERIFIED: confirmed the one occurrence is metadata]
**Warning signs:** Zero `ResizeSensor` matches = library not in bundle (correct signal).

### Pitfall 4: Forgetting `--legacy-peer-deps` in Docker After Removing a Dep
**What goes wrong:** Removing jquery/css-element-queries and then also removing `--legacy-peer-deps` from the Dockerfile, which breaks the Angular 21 install.
**Why it happens:** The flag was added for pre-existing Angular 21 peer dep conflicts, which still exist after these removals.
**How to avoid:** Do not touch the Dockerfile's `--legacy-peer-deps` flag. This phase changes only `package.json` + `package-lock.json`.

### Pitfall 5: Hidden Dynamic Import or `require()` String-Based Usage
**What goes wrong:** A dynamic `import('jquery')` or `require('jquery')` that a static grep misses.
**Why it happens:** Dynamic imports use string literals that grep would catch, but `require(variable)` would not. However, this pattern does not exist in the Angular 21/TypeScript codebase (TypeScript strict mode + Angular's ES module system don't support CommonJS `require`).
**How to avoid:** The `ng build --configuration production` build step is the definitive catch-all — esbuild resolves all static and dynamic imports and would report a missing module error if any reference to `jquery` or `css-element-queries` existed. A clean build is the proof. [ASSUMED — esbuild behavior for missing modules]
**Contingency:** If the build reports `Cannot resolve 'jquery'` or similar, that is the "hidden usage found" signal. Per REQUIREMENTS.md: this becomes a scoped finding, NOT a version bump.

---

## Runtime State Inventory

This is a package.json + lockfile change — not a rename/refactor. No runtime state uses the string "jquery" or "css-element-queries" as a key, collection name, or identifier:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — these are browser-side npm packages; no DB keys | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | `node_modules/jquery/` and `node_modules/css-element-queries/` in the Angular build Docker layer (cached) | Docker cache is invalidated by the `package*.json` COPY step in the Dockerfile; next Docker build automatically re-runs `npm install` without these packages |

**Docker cache note:** The Dockerfile's `seedsyncarr_build_angular_env` stage copies `package*.json` and runs `npm install`. Because `package.json` changes, Docker will invalidate the cache for that layer on next build — no manual cache bust needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + npm | `npm install`, `ng build` | ✓ (macOS dev) | npm 11.12.1 | — |
| `@angular/cli` (in node_modules) | `ng build`, `ng test` | ✓ | 21.2.x (in node_modules) | Use `node node_modules/@angular/cli/bin/ng.js` |
| Chrome/Chromium | Karma unit tests | ✓ (macOS, Docker CI) | via Docker on CI | Docker provides ChromeHeadless |
| Docker + Buildx | CI amd64+arm64 build | ✓ (CI); QEMU blocked for NAS | — | Local runs use local arch only; CI covers both |

**Note on local vs CI testing:** The Karma test run is done via Docker in CI (see `src/docker/test/angular/Dockerfile`). Local dev can run `ng test --browsers ChromeHeadless --watch=false --code-coverage` directly if Chrome is installed. Both paths use the same `karma.conf.js` with the same coverage floors.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma 6.4.4 + Jasmine 6.2.0 |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && ng test --browsers ChromeHeadless --watch=false` |
| Full suite command | `cd src/angular && ng test --browsers ChromeHeadless --watch=false --code-coverage` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| DEPS-01a | No jQuery import/usage in Angular source | Audit (grep) | `grep -r "jquery" src/angular/src/` → 0 matches | Not a unit test — a build-time verification |
| DEPS-01a | Production build succeeds without jQuery | Build | `cd src/angular && ng build --configuration production` | Build failure = hidden usage found |
| DEPS-01a | Bundle contains no jQuery code | Dist grep | `grep "jQuery JavaScript Library" dist/*.js` → 0 matches | Checks jQuery's factory header |
| DEPS-01a | Bootstrap interactions work | Manual smoke | `ng serve` → verify nav, dropdown, confirm modal | No automated test for Bootstrap CSS |
| DEPS-01c | No css-element-queries import/usage | Audit (grep) | `grep -r "ResizeSensor\|ElementQueries" src/angular/src/` → 0 matches | Build-time verification |
| DEPS-01c | Production build succeeds | Build | `cd src/angular && ng build --configuration production` | Combined with DEPS-01a |
| DEPS-01c | Bundle contains no ResizeSensor code | Dist grep | `grep "ResizeSensor\|ElementQueries" dist/*.js` → 0 matches | Library's own exports |
| CROSS | Karma floors hold (83/68/79/83) | unit | `ng test --browsers ChromeHeadless --watch=false --code-coverage` | No new unit tests needed (no source changes) |
| CROSS | CI green amd64+arm64 | CI | GitHub Actions `unittests-angular` job | E2E also stays green |

### Sampling Rate
- **Per commit:** `cd src/angular && ng build --configuration production` (confirms no broken imports)
- **Per wave merge:** `cd src/angular && ng test --browsers ChromeHeadless --watch=false --code-coverage` (confirms Karma floors hold)
- **Phase gate:** Full Karma suite green + production build green + dist grep clean before verify-work

### Wave 0 Gaps
None — no new test files needed. This phase makes no source changes that would require new unit tests. Existing test infrastructure covers all verification requirements.

---

## Security Domain

> `security_enforcement` not explicitly set in `.planning/config.json` — treat as enabled. Evaluated and found N/A for this removal phase.

### Applicable ASVS Categories

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V2 Authentication | No | Package removal does not touch auth |
| V3 Session Management | No | Package removal does not touch sessions |
| V4 Access Control | No | No access control changes |
| V5 Input Validation | No | No input handling changes |
| V6 Cryptography | No | No cryptography changes |

**Security benefit of removal:** Removing jQuery 4 eliminates a dependency that could in future receive security advisories (jQuery has historically been a source of XSS and prototype pollution CVEs). Proactive removal is the right call. css-element-queries (unmaintained since 2019) eliminates an unmaintained package from the dependency surface. No ASVS controls are impacted by these removals.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `npm install` after editing `package.json` correctly removes `node_modules/jquery` and `node_modules/css-element-queries` and regenerates `package-lock.json` with no surprises | npm/Lockfile Mechanics | Extremely low — standard npm v11 behavior; worst case: run `npm ci` instead |
| A2 | esbuild (via `@angular/build:application`) would report a "Cannot resolve" error if any dynamic import of `jquery` existed | Common Pitfalls — Pitfall 5 | Low — esbuild resolves all static imports; truly dynamic string-variable requires would be visible as a runtime error, not a silent bundle inclusion |
| A3 | The `--legacy-peer-deps` flag in Docker is not related to jquery or css-element-queries | npm/Lockfile Mechanics | Low — confirmed by examining what packages are in the tree; the flag existed before these deps were ever added |

**Verified claims:** All other claims in this research were confirmed via live grep, file read, or live npm view in this session.

---

## Open Questions

1. **Can the planner run `ng build --configuration production` locally for the pre-removal baseline?**
   - What we know: The build runs in Docker for CI; local build requires `node_modules` to be installed.
   - What's unclear: Whether the executor will use the local dev environment or Docker for the baseline capture.
   - Recommendation: Either works. The simplest approach is `cd src/angular && ng build --configuration production` locally (uses the current `node_modules`). Capture the output table line by line. The existing dist at `src/angular/dist/` already serves as an informal baseline (sizes: main=573.84 kB, scripts=80.45 kB, polyfills=35.78 kB).

2. **Will the tiny css-element-queries package.json metadata removal produce a measurable size delta?**
   - What we know: The one occurrence of `"css-element-queries"` is ~25 chars of license metadata. The bundle is 573 kB.
   - What's unclear: Whether minification makes this unobservable.
   - Recommendation: The delta may be zero bytes at gzip level. That is acceptable — D-02 says "shrinks or at worst not grows," and removing a phantom dep while the bundle stays equal is still a pass.

---

## Sources

### Primary (HIGH confidence — live verification in this session)
- Live grep of `src/angular/src/` — zero jQuery, css-element-queries, ResizeSensor, ElementQueries references
- `src/angular/angular.json` — live read; scripts array confirmed (bootstrap.bundle.min.js only)
- `src/angular/package.json` — live read; both deps confirmed in `dependencies`
- `src/angular/package-lock.json` — live parse; both deps depended-on by root only
- `src/angular/dist/` — live grep; jQuery factory string absent; ResizeSensor absent; one metadata reference to css-element-queries confirmed as license extractor output
- `src/angular/node_modules/bootstrap/dist/js/bootstrap.bundle.min.js` — live read; `window.jQuery` confirmed as optional detection only
- `src/angular/karma.conf.js` — live read; floors confirmed at stmts/branches/fns/lines 83/68/79/83
- `src/docker/build/docker-image/Dockerfile` — live read; `--legacy-peer-deps` and Angular build steps confirmed
- npm audit output — live run; zero advisories for jquery or css-element-queries; 4 pre-existing moderate vulns unrelated to these deps

### Secondary (MEDIUM confidence — official project docs)
- `.planning/codebase/CONCERNS.md` §"Dependencies at Risk" — source of concern documentation (jQuery, css-element-queries)
- `.planning/milestones/v1.3.0-phases/104-light-dependency-removals/104-CONTEXT.md` — all locked decisions (D-01 through D-04)
- `.planning/REQUIREMENTS.md` — DEPS-01a, DEPS-01c acceptance criteria; Cross-Cutting Constraints

---

## Metadata

**Confidence breakdown:**
- Phantom-dependency audit: HIGH — live grep, zero matches, confirmed in multiple file types
- Bootstrap 5 jQuery independence: HIGH — confirmed from Bootstrap source and Angular app architecture
- Bundle verification approach: HIGH — confirmed builder type (@angular/build:application esbuild), no stats.json, output table is the correct mechanism
- npm lockfile mechanics: MEDIUM (A1 tagged ASSUMED) — standard npm behavior; confirmed lockfileVersion: 3
- CI/Docker path: HIGH — Dockerfile and compose confirmed live

**Research date:** 2026-06-01
**Valid until:** 2026-07-01 (stable Angular build ecosystem; only changes if Angular 21 builder API changes)
