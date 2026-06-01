---
phase: 105
phase_slug: font-awesome-to-phosphor-migration
date: 2026-06-01
nyquist_validation: enabled
source: 105-RESEARCH.md §"Validation Architecture"
---

# Phase 105: Font Awesome → Phosphor Migration — Validation Strategy

> Nyquist validation strategy. Derived from `105-RESEARCH.md` §"Validation Architecture".
> Requirement: **DEPS-01b**.

## Test Framework

| Property | Value |
|----------|-------|
| Framework | Karma + Jasmine (existing) |
| Config file | `src/angular/karma.conf.js` |
| Run command | `cd src/angular && npx karma start --single-run` |
| Coverage floors (must hold or rise) | Karma `check.global` — stmts/branches/fns/lines **83 / 68 / 79 / 83** |
| Python floor (unaffected, must stay green) | `fail_under` ≥ 88 |

## Phase Requirements → Test Map

| Req ID | Behavior to validate | Test type | Automated command | Spec / surface |
|--------|----------------------|-----------|-------------------|----------------|
| DEPS-01b | Rendered DOM uses Phosphor classes, not `fa-*` | unit | `npx karma start --single-run` | stats-strip.spec, dashboard-log-pane.spec, transfer-table.spec, notification-bell.spec |
| DEPS-01b | Icon selectors in specs match new Phosphor classes | unit | `npx karma start --single-run` | all 4 spec files (faithful update per CONTEXT D-03) |
| DEPS-01b | No regression in existing component logic | unit | `npx karma start --single-run` | full suite (all 611 tests pass) |
| DEPS-01b | Loading spinner still animates (FA `fa-spin` gone) | unit + smoke | karma + dev-server | dashboard-log-pane (`@keyframes ph-spin` + `.ph-spin` rule added per RESEARCH finding) |
| DEPS-01b | Every former `fa-*` location renders a visible Phosphor glyph | smoke (manual) | dev-server inspection (CONTEXT D-04) | dashboard stats strip, transfer rows, bulk-actions bar, settings (incl. dynamic `{{icon}}` + toggle states), logs, dashboard log pane, notification bell |
| DEPS-01b | FA absent from production bundle | grep | `ng build --configuration production` then `grep -rn "font-awesome\|fa-" dist/` (production-relevant files) | dist output |
| DEPS-01b | Bundle ≤ Phase 104 baseline | build-stats delta | `ng build --configuration production` before/after (CONTEXT D-07) | build output / stats |

## Wave 0 Gaps

None — the existing Karma/Jasmine infrastructure and the 4 spec files cover all phase requirements. The specs are **updated, not created**. The only net-new test-relevant artifact is the `ph-spin` keyframes/CSS rule (compensating for FA's removed `fa-spin`), validated by the spinner smoke check.

## Notes

- The visual "no icon missing / no layout shift" criterion (success criterion #4) is validated by the **manual dev-server smoke test** (CONTEXT D-04), not an automated assertion — consistent with the Phase 104 D-01 rhythm.
- Residual-FA detection is a hard grep gate over `dist/` and `src/angular/src/` (production-relevant files) — zero `fa-` class strings and no font-awesome CSS/font files permitted post-migration.
