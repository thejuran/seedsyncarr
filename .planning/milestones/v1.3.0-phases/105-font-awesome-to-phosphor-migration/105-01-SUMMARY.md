---
phase: 105-font-awesome-to-phosphor-migration
plan: "01"
subsystem: frontend-icons
tags: [icons, font-awesome, phosphor, mapping, bundle-baseline, sign-off]
dependency_graph:
  requires: [DEPS-01b]
  provides: [D-01-mapping-complete, D-07-before-baseline]
  affects:
    - .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-MAPPING-SIGNOFF.md
    - .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-BUNDLE-BASELINE.md
tech_stack:
  added: []
  patterns: [icon-mapping-audit, bundle-baseline-capture, user-sign-off-gate]
key_files:
  created:
    - .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-MAPPING-SIGNOFF.md
    - .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-BUNDLE-BASELINE.md
  modified: []
decisions:
  - D-01 mapping gate satisfied: complete 39-class fa->ph mapping table documented before any code change; user signed off all 8 ambiguous icons on 2026-06-01
  - Q4 substitution: fa-file-archive-o -> ph-file-zip (user selected option B; plans 105-02 and 105-03 must both use ph-file-zip, NOT ph-file-archive)
  - Q5 spin CSS approved: .ph-spin @keyframes rule approved for addition to dashboard-log-pane.component.scss in plan 105-02
  - D-07 BEFORE baseline captured: styles chunk 473.05 kB / initial total 1.16 MB (font-awesome still present, HEAD a0bd106)
  - Two corrected non-intuitive mappings documented: fa-server->ph-computer-tower (NOT ph-server; Pitfall 3), fa-ban->ph-prohibit (NOT ph-ban; §1a)
metrics:
  duration: "~20 minutes (Task 1 production build + sign-off checkpoint)"
  completed_date: "2026-06-01"
  tasks_completed: 2
  files_modified: 0
  files_created: 2
---

# Phase 105 Plan 01: FA->Phosphor Mapping Table + Bundle Baseline Summary

**One-liner:** Documented the complete 39-class Font Awesome to Phosphor mapping table (32 confirmed + 8 user-signed-off ambiguous decisions, including Q4 substituted to ph-file-zip) and captured the D-07 BEFORE bundle baseline (styles 473.05 kB, total 1.16 MB) while font-awesome ^4.7.0 is still present.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Author 39-class fa->ph mapping table + capture BEFORE bundle baseline | 4715585 | 105-MAPPING-SIGNOFF.md (created), 105-BUNDLE-BASELINE.md (created) |
| 2 | User sign-off on 8 ambiguous icon mappings (D-01 LOCKED gate) | [this commit] | 105-MAPPING-SIGNOFF.md (DECISION lines filled) |

---

## Outcome

D-01 success criterion #1 satisfied: the complete fa->ph mapping table for all 39 distinct `fa-*` classes is documented before any code change lands.

**Confirmed mappings (32 total):**

31 confident 1:1 mappings sourced from RESEARCH §1a (fa-arrow-down, fa-ban->ph-prohibit, fa-bell, fa-check, fa-check-circle, fa-circle, fa-circle-o, fa-clock-o, fa-cloud, fa-cog->ph-gear, fa-copy, fa-database, fa-download, fa-exclamation-circle->ph-warning-circle, fa-exclamation-triangle->ph-warning, fa-expand->ph-arrows-out, fa-eye, fa-eye-slash, fa-folder-open-o->ph-folder-open, fa-info-circle->ph-info, fa-list, fa-play, fa-plus-circle, fa-refresh->ph-arrows-clockwise, fa-search->ph-magnifying-glass, fa-shield, fa-stop, fa-tasks->ph-list-checks, fa-terminal, fa-times->ph-x, fa-trash).

1 corrected mapping from RESEARCH Migration Surface Map §2a + Pitfall 3: fa-server->ph-computer-tower (NOT ph-server — ph-server does not exist in Phosphor 2.1.2).

**Two corrected non-intuitive mappings (prominently documented):**
1. `fa-server` -> `ph-computer-tower` — source: surface map §2a / Pitfall 3 (NOT §1a, which does not list fa-server; ph-server does not exist in v2.1.2)
2. `fa-ban` -> `ph-prohibit` — source: §1a confident table note (ph-ban does not exist in v2.1.2)

**Ambiguous mappings (8 total — all signed off 2026-06-01):**

| Q | FA class | Final Phosphor class | Decision |
|---|----------|---------------------|----------|
| Q1 | fa-tachometer | ph-gauge | CONFIRMED (accepted as proposed) |
| Q2 | fa-floppy-o | ph-floppy-disk | CONFIRMED (accepted as proposed) |
| Q3 | fa-hdd-o | ph-hard-drive | CONFIRMED (accepted as proposed) |
| Q4 | fa-file-archive-o | **ph-file-zip** | USER SUBSTITUTED option B — NOT ph-file-archive |
| Q5 | fa-circle-o-notch + fa-spin | ph-circle-notch + .ph-spin CSS rule | CONFIRMED (icon + local spin CSS approved) |
| Q6 | fa-th-large | ph-squares-four | CONFIRMED (accepted as proposed) |
| Q7 | fa-sliders | ph-sliders-horizontal | CONFIRMED (accepted as proposed) |
| Q8 | fa-file-code-o | ph-file-code | CONFIRMED (accepted as proposed) |

**Q4 critical note:** The authoritative class for `fa-file-archive-o` is `ph-file-zip`. Plans 105-02 and 105-03 read from the same DECISION line in 105-MAPPING-SIGNOFF.md and MUST both use `ph-file-zip`. Using `ph-file-archive` in either plan is a deviation.

**Q5 critical note:** The `.ph-spin` CSS rule (`@keyframes ph-spin` + `.ph-spin` scoped to `dashboard-log-pane.component.scss`) is approved for addition in plan 105-02. Phosphor 2.1.2 ships no spin animation class — without this addition the spinner will freeze when FA is removed.

---

## D-07 BEFORE Bundle Baseline

`ng build --configuration production` run from `src/angular/` on 2026-06-01 while `font-awesome ^4.7.0` is still present. HEAD at time of capture: `a0bd106`.

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-D4LPEGW2.js      | main          | 574.81 kB |               134.31 kB
styles-KZG6GNQT.css   | styles        | 473.05 kB |                45.47 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.16 MB |               213.00 kB
```

Build exit: 0 (green). The `styles` chunk (473.05 kB) includes Font Awesome's ~37 kB CSS plus font files. The D-07 AFTER record is appended in plan 105-04 — expected delta is at minimum ~37 kB reduction in the styles chunk once FA CSS is removed from `angular.json`.

---

## Deviations from Plan

None — plan executed exactly as written. Task 1 automated; Task 2 was the D-01 LOCKED checkpoint, which the user resolved with all 8 decisions (Q4 was a user substitution from the proposed pick, not a deviation from the plan — the plan explicitly offered ph-file-zip as an alternate).

---

## No Source Code Edited

No `.html`, `.ts`, or `.scss` files were modified in this plan. 105-01 is documentation + baseline only. Source `fa-*` icons are untouched.

---

## Known Stubs

None.

---

## Threat Flags

None. Per the T-105-01 and T-105-SC threat register entries: this plan produces documentation and runs a read-only `ng build`. No new network endpoints, auth paths, file access patterns, or schema changes were introduced.

---

## Self-Check: PASSED
