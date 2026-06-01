# Plan 106-02 Summary — Dev-Mode Mock Toggle Smoke Test (COMPAT half of DEPS-02)

**Status:** COMPLETE
**Date:** 2026-06-01
**Requirements:** DEPS-02 (COMPAT / ROADMAP #4 — dev-mode mock toggle still works via the new env flag)
**Plan type:** verification-only (1 auto task + 1 human-verify checkpoint)

## Objective

Prove the dev-mode mock toggle still renders mock rows through the new `environment.useMockModel`
flag after Plan 106-01's relocation + env-flag refactor. This is the COMPAT half of DEPS-02; the
prod-absence half was proven automatically in 106-01.

## What was verified

**Blocking precondition (no temporary toggle):** the COMMITTED `environment.ts` reads
`useMockModel: true` (verified via `git show HEAD:...`). No temporary toggle was used — the smoke
test ran against the committed state exactly as it ships to developers.

**Task 1 — automated dev-mode smoke test:**
- `ng serve --configuration development --port 4209` compiled clean and served HTTP 200
  (auto-routed to `/dashboard`). Development config has no `fileReplacements`, so it loads the
  REAL relocated fixture `tests/fixtures/mock-model-files.ts`.
- Browser-level DOM assertion (Playwright): a rendered DOM node
  `<div class="file-name">[AUTHOR] A Really Cool Video About Cats.mkv</div>` is present in the
  dashboard file table — confirming the dev path is intact end-to-end
  (env flag `true` → `view-file.service.ts` else-branch → `buildViewFromModelFiles(MOCK_MODEL_FILES)`
  → mock row visible). This is a rendered DOM node, not merely a bundle string.
- Console errors: only the unrelated backend-SSE pair (`GET /server/stream` 404 → `Error in stream`),
  caused by running the Angular dev server without the Python backend. **Zero** errors reference the
  relocated `tests/fixtures/mock-model-files` import path or a missing `environment.useMockModel`.

**Task 2 — human-verify checkpoint:** APPROVED. Self-approved on the browser-level DOM assertion
(stronger evidence than a manual eyeball check). The dev-mode mock toggle renders mock rows correctly.

## Result

PASS — the dev-mode mock toggle works via the new env flag (COMPAT constraint upheld). Combined with
106-01's prod-absence proof, DEPS-02 is fully satisfied: production bundle contains none of the mock
data, and dev-mode mock behavior still works when the env flag is set.

## Key files

- `.planning/milestones/v1.3.0-phases/106-mock-fixture-bundle-hygiene/106-BUNDLE-BASELINE.md`
  (Dev-Mode Smoke Test section appended with its own provenance line + APPROVED marker)

No source files modified by this plan (verification-only).

## Self-Check: PASSED
