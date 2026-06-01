---
phase: 106-mock-fixture-bundle-hygiene
status: passed
verified: 2026-06-01
requirements: [DEPS-02]
method: goal-backward (live codebase on main + recorded proof artifact)
---

# Phase 106 Verification — Mock-Fixture Bundle Hygiene (DEPS-02)

**Verdict: PASSED** — the codebase genuinely delivers the phase goal, verified against live source on `main`, not merely task completion.

## Phase Goal (ROADMAP §106)

Move `USE_MOCK_MODEL` toggle into `environment.ts`, relocate mock files out of `services/files/`, exclude via `fileReplacements`; production bundle contains none of the mock data; dev-mode mock behavior still works (DEPS-02).

## Goal-Backward Evidence (verified on live `main` source)

| Decision | Claim | Live verification | Result |
|----------|-------|-------------------|--------|
| D-02 | env flag in both env files | `environment.ts: useMockModel: true`; `environment.prod.ts: useMockModel: false` | ✓ |
| D-02 | service branches on flag, no class field | `view-file.service.ts:92 if (!environment.useMockModel)`; `USE_MOCK_MODEL` class field absent | ✓ |
| D-05 | fixture relocated; service import updated | `view-file.service.ts:12 import from "../../tests/fixtures/mock-model-files"`; old `services/files/mock-model-files.ts` gone; `tests/fixtures/mock-model-files.ts` present | ✓ |
| D-03 | empty prod stub | `tests/fixtures/mock-model-files.prod.ts` exports `MOCK_MODEL_FILES = Immutable.Map<string, ModelFile>()` (empty) | ✓ |
| D-04 | dead screenshot file deleted | `services/files/screenshot-model-files.ts` does not exist | ✓ |
| D-01/D-03 | second fileReplacements (prod only) | `angular.json` production: 2 entries (env swap + fixture→prod-stub); development: 0; test target swaps only environment (real fixture retained in test) | ✓ |
| D-06.1 | true before/after bundle delta | `106-BUNDLE-BASELINE.md` records BEFORE (commit `00a77a4`, 207.70 kB) → AFTER (commit `7aa11d0`, 207.23 kB), main −4.87 kB raw | ✓ |
| D-06.3 | dist filename-literal absence (HARD) | `MOCK-ABSENT-FROM-PROD-DIST`; independent re-grep of live `dist/` for `A Really Cool Video About Cats` → zero hits; symbol also tree-shaken | ✓ |
| D-06.2 | dev-mode smoke test | `ng serve` dev → browser-DOM node `<div class="file-name">[AUTHOR] A Really Cool Video About Cats.mkv</div>` rendered; checkpoint APPROVED | ✓ |
| D-07 | Karma floors hold, no tag | 611/611 pass, floors 84/69/80/85 ≥ 83/68/79/83; no `v1.3.0` tag exists (cut only after slice 4) | ✓ |

## Cross-Cutting Constraints (REQUIREMENTS)

- **COMPAT — no visual/behavioral regression:** dev-mode mock toggle still works via the env flag (D-06.2, browser-verified); production behavior unchanged (env flag is a build-time-constant `false` in prod, identical to the prior hardcoded `false`). ✓
- **Bundle does not grow:** AFTER (207.23 kB) ≤ BEFORE (207.70 kB) — it shrank. ✓
- **CI green / Karma floors:** 611/611, all four floors held. ✓
- **No release/tag/version work:** confirmed — no tag cut. ✓

## Must-Haves (goal-backward)

1. Production bundle contains none of the mock dataset → **MET** (dist filename-literal grep zero hits + symbol tree-shaken).
2. Dev-mode mock behavior still works when the env flag is set → **MET** (rendered DOM node under `ng serve`).

## Conclusion

DEPS-02 is fully and genuinely satisfied. Both plans (106-01 mechanism + 106-02 COMPAT smoke) complete with SUMMARY.md. Phase 106 goal achieved.

**Status: passed**
