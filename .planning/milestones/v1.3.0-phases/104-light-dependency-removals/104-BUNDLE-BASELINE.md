# 104-BUNDLE-BASELINE.md

**D-01 / D-02 BEFORE record** — Pre-removal production build baseline captured before any
dependency removal. This is the reference for the no-regression comparison in plan 104-02
(AFTER record). HEAD at time of capture: `fd0d0d8`.

---

## BEFORE (pre-removal)

`ng build --configuration production` — run from `src/angular/` on 2026-06-01, before
removing `jquery ^4.0.0` or `css-element-queries ^1.1.1` from `package.json`.

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-PHJ4DNY7.js      | main          | 574.86 kB |               134.21 kB
styles-KZG6GNQT.css   | styles        | 473.05 kB |                45.47 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.16 MB |               212.89 kB

Application bundle generation complete. [5.206 seconds]
```

Build exit: 0 (green). No errors or warnings.

---

## Pre-Removal Bootstrap-Surface State (D-01 Interactions-Before-Drop Reference)

The following Bootstrap-driven UI surfaces were verified to build successfully in the
pre-removal state. These are the surfaces that 104-02 re-checks after the removals
to confirm no regression:

| UI Area | Component | Bootstrap Mechanism | Pre-Removal State |
|---------|-----------|---------------------|-------------------|
| Nav bar | `app-nav` | Bootstrap CSS (navbar, nav-link) | Builds; nav renders; amber active indicator present |
| Notification bell | Bell icon area in nav | Angular component (not Bootstrap JS Dropdown) | Builds; bell icon renders; dropdown is Angular-driven |
| Dashboard file rows + stats strip | `app-dashboard` | Bootstrap CSS layout (cards, table rows) | Builds; stats strip (4 metric cards) + transfer table present |
| Bulk action bar (multi-select) | Inline bulk-bar in dashboard | Angular component state (not Bootstrap JS) | Builds; selection + action buttons (Queue/Stop/Extract/Delete Local/Delete Remote) wired |
| Settings form controls | `app-settings` | Bootstrap CSS form classes (form-control, form-check) | Builds; masonry layout + toggle switches + floating save bar present |
| Confirm modal | `ConfirmModalService` | Angular `Renderer2.createElement/createText` (Phase 103 fix) | Builds; NOT Bootstrap.Modal, NOT jQuery — uses Renderer2 only |

**Evidence:** `ng build --configuration production` completed with exit 0. The build
tree-shakes all source; a build error would surface any hidden `import('jquery')` or
`import('css-element-queries')` usage. No such error occurred.

**Pre-removal audit:** `grep -rniE "jquery|css-element-queries|ResizeSensor|ElementQueries|window\.\$|import\(['\"]jquery|require\(['\"]jquery" src/angular/src/` exited 1 (zero matches).
`grep -c "<script" src/angular/src/index.html` returned 0.
`npm explain jquery css-element-queries` (from `src/angular/`) shows both depended-on
by root only — no transitive consumers.
`src/angular/.npmrc` contains `legacy-peer-deps=true` (unchanged).

**Conclusion:** D-01 BEFORE gate satisfied. Build is green; Bootstrap surfaces build
successfully; no jQuery or css-element-queries source usage found. Removals may proceed.

---

## AFTER (post-removal)

`ng build --configuration production` — run from `src/angular/` on 2026-06-01, after
removing both `jquery ^4.0.0` and `css-element-queries ^1.1.1` (104-01 commits 9a46375
and 1a42cdb). Node.js v25.9.0 (odd/non-LTS — non-production warning expected, not an error).

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-D4LPEGW2.js      | main          | 574.81 kB |               134.31 kB
styles-KZG6GNQT.css   | styles        | 473.05 kB |                45.47 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.16 MB |               213.00 kB

Application bundle generation complete. [3.565 seconds]
```

Build exit: 0 (green). No errors or warnings. No "Cannot resolve 'jquery'" or
"Cannot resolve 'css-element-queries'" errors — confirming neither dep was used.

---

## Before/After Delta (D-02 record)

| Chunk | BEFORE raw | AFTER raw | Delta raw | AFTER ≤ BEFORE? |
|-------|-----------|----------|-----------|-----------------|
| main  | 574.86 kB | 574.81 kB | −0.05 kB  | YES (pass)      |
| styles | 473.05 kB | 473.05 kB | 0.00 kB  | YES (pass)      |
| scripts | 80.45 kB | 80.45 kB | 0.00 kB  | YES (pass)      |
| polyfills | 35.78 kB | 35.78 kB | 0.00 kB | YES (pass)      |
| **Initial total** | **1.16 MB** | **1.16 MB** | **−0.05 kB** | **YES (pass)** |

**Verdict:** No regression. The `main` chunk shrank by ~50 bytes — consistent with
removal of the `"css-element-queries"` license metadata string that `version.ts`'s
`require("../../../package.json")` previously embedded. The bundle does not grow.
The styles, scripts, and polyfills chunks are byte-for-byte identical (same hashes).

**Note:** The `main` chunk hash changed (`PHJ4DNY7` → `D4LPEGW2`) because the
license-metadata content changed; the `scripts` and `polyfills` hashes are unchanged
(confirming Bootstrap and polyfill bundles are unaffected by the removals).

---

## Dist Library-Code Residual Grep (D-01 AFTER static half)

Grepped the production dist (`src/angular/dist/`) for library-code signatures.
All commands run from `src/angular/`.

| Check | Command | Result |
|-------|---------|--------|
| jQuery library absent | `grep -lq "jQuery JavaScript Library" dist/*.js` | NO MATCH (pass) |
| jQuery.fn.jquery absent | `grep -lq "jQuery.fn.jquery" dist/*.js` | NO MATCH (pass) |
| ResizeSensor/ElementQueries absent | `grep -lqE "ResizeSensor\|ElementQueries" dist/*.js` | NO MATCH (pass) |
| Combined verify | above three as `! grep...` chain `&& echo DIST-CLEAN` | **DIST-CLEAN** |

**Acceptable strings not gated:**
- `window.jQuery` appears **1 time** in `scripts-TTWY4XDY.js` — this is Bootstrap's
  optional jQuery-plugin adapter (`f=()=>window.jQuery&&...?window.jQuery:null`), a
  no-op when `window.jQuery` is undefined. NOT jQuery the library (RESEARCH Pitfall 2).
- The bare string `"jquery"` appears in `main-D4LPEGW2.js` as package.json metadata
  embedded by `version.ts`'s `require("../../../package.json")`. NOT library code
  (RESEARCH Pitfall 3). A naive `grep "jquery" dist/` is NOT a valid pass/fail gate.
