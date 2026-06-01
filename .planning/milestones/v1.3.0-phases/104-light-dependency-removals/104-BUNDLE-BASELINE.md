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
