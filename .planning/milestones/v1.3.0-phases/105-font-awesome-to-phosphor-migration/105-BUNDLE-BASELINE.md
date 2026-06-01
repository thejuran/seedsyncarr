# 105-BUNDLE-BASELINE.md

**D-07 BEFORE record** — Pre-migration production build baseline captured while
`font-awesome ^4.7.0` is still present in `src/angular/package.json` and its CSS
entries are still in `angular.json`. This is the reference for the before/after delta
in plan 105-04 (AFTER record). HEAD at time of capture: `a0bd106`.

---

## BEFORE (pre-migration, font-awesome still present)

`ng build --configuration production` — run from `src/angular/` on 2026-06-01, before
any Font Awesome → Phosphor source edits or dep removal. `font-awesome ^4.7.0` is
present in `package.json` and its stylesheet is loaded in `angular.json`.

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-D4LPEGW2.js      | main          | 574.81 kB |               134.31 kB
styles-KZG6GNQT.css   | styles        | 473.05 kB |                45.47 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.16 MB |               213.00 kB

Application bundle generation complete. [3.535 seconds] - 2026-06-01T13:16:44.052Z
```

Build exit: 0 (green). No errors or warnings.
Node.js v25.9.0 (odd/non-LTS — warning expected, not an error).

---

## Notes

- This build is identical to the Phase 104 AFTER record (same HEAD `a0bd106`, same
  chunk hashes). This is expected: no source changes have been made between the
  Phase 104 AFTER capture and this Phase 105 BEFORE capture. The styles chunk
  (`styles-KZG6GNQT.css`, 473.05 kB) includes Font Awesome's ~37 kB CSS plus the
  Font Awesome font files referenced in that CSS.

- The D-07 AFTER record is appended in plan 105-04 after all `fa-*` usages have
  been migrated, the `font-awesome` dep has been removed from `package.json`, the
  two `font-awesome/css/font-awesome.css` lines have been removed from `angular.json`,
  and `npm install` has regenerated `package-lock.json`.

- Expected delta: the `styles` chunk should shrink by at least the Font Awesome
  CSS (~37 kB uncompressed) once the FA stylesheet is removed from `angular.json`.
  Font files (woff, woff2, ttf, svg, eot) typically add 200–400 kB uncompressed
  but may be in a separate lazy chunk — confirm in the AFTER build output.

- Phase 104 baseline (from 104-BUNDLE-BASELINE.md AFTER record) for cross-check:
  `Initial total 1.16 MB / 213.00 kB estimated transfer`. The Phase 105 AFTER total
  must be ≤ this figure per D-07.

---

*Plan: 105-01 | D-07 artifact (BEFORE half) | Status: BEFORE captured; AFTER pending (plan 105-04)*
