# Phase 106: Mock-Fixture Bundle Hygiene - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Move the development-only mock-model fixtures out of the production Angular bundle (DEPS-02). The hardcoded `USE_MOCK_MODEL` class field in `view-file.service.ts:71` becomes a build-time `useMockModel` flag on `environment.ts`/`environment.prod.ts`; `mock-model-files.ts` relocates out of `services/files/` into a dev-only fixtures dir and is swapped for an empty prod stub via Angular `fileReplacements`; the unused `screenshot-model-files.ts` is deleted. After the change the production bundle contains **none** of the mock dataset, while dev-mode mock behavior still works when the env flag is set.

This is the last phase of v1.3.0 slice 3 (Frontend Deps + Dead Code). No tag is cut — the single `v1.3.0` tag is cut only after slice 4. jQuery/css-element-queries removals (Phase 104) and Font Awesome → Phosphor (Phase 105) are complete and out of scope.

</domain>

<decisions>
## Implementation Decisions

### Tree-shake mechanism (load-bearing)
- **D-01:** Two-layer guarantee — the env flag drives runtime behavior **and** a second `fileReplacements` entry physically swaps the fixture module for a tiny prod stub in production builds. Relying on the env-flag dead-code branch alone is rejected: the `import {MOCK_MODEL_FILES}` in `view-file.service.ts` is a static top-level import, and Terser tree-shaking of a `const` holding a large `Immutable.Map` referenced only inside a dead `if(!environment.useMockModel)` else-branch is a heuristic, not a guarantee.
- **D-02:** Add `useMockModel: boolean` to **both** environment files: `true` in `environment.ts` (dev), `false` in `environment.prod.ts` (prod). `view-file.service.ts` imports `environment` and branches on `environment.useMockModel` instead of the hardcoded private `USE_MOCK_MODEL = false` class field (which is removed).
- **D-03:** A prod stub `mock-model-files.prod.ts` exports `MOCK_MODEL_FILES` as an **empty** `Immutable.Map<string, ModelFile>()` (same export name/type/shape so the prod compile is type-clean). `angular.json` production `fileReplacements` gains a second entry swapping the relocated `mock-model-files.ts` → `mock-model-files.prod.ts`. This matches DEPS-02's literal "exclude via `fileReplacements`" wording.

### screenshot-model-files fate
- **D-04:** **Delete** `src/angular/src/app/services/files/screenshot-model-files.ts` (`SCREENSHOT_MODEL_FILES`, ~135 lines) outright. Confirmed **zero importers** across `src/**` (`.ts`/`.html`) — it is dead code. It is NOT relocated; git history preserves it if a future dataset is ever wanted.

### Relocation target
- **D-05:** `mock-model-files.ts` moves to **`src/angular/src/app/tests/fixtures/`** (new dir, per CONCERNS.md). The prod stub `mock-model-files.prod.ts` lives in the same dir. Rationale: fixtures (data) are semantically distinct from the existing `src/app/tests/mocks/` (fake **service** implementations like `mock-view-file.service.ts`); co-locating data with service-doubles was rejected to keep that distinction clean. `view-file.service.ts`'s import path updates to the new location.

### Verification rigor
- **D-06:** Three-part proof:
  1. **Before/after production bundle-size delta** — same rhythm Phases 104/105 used; record prod build stats before and after so the mock dataset is shown to leave the build (bundle must not grow).
  2. **Dev-mode smoke test** — with `environment.ts` `useMockModel: true`, confirm the mock files still render in the file view (the dev toggle continues to work via the new env flag — COMPAT constraint).
  3. **Prod-dist absence grep** — grep the production `dist/` output for a unique mock string (e.g. `A Really Cool Video About Cats`) and assert **zero** hits, directly proving the fixture is physically absent from the prod bundle.
- **D-07:** Karma coverage floors must still hold (statements/branches/functions/lines per the slice floors); CI green on amd64 + arm64. No release/tag/version work in this phase.

### Claude's Discretion
- Exact filename/casing of the prod stub (e.g. `mock-model-files.prod.ts`) and whether the empty-map type annotation is inlined or factored — any type-clean form is fine.
- Whether the dev-mode smoke test is a manual `ng serve` check or a lightweight automated assertion — planner/executor picks the lightest reliable proof, consistent with the sibling phases' D-04-style smoke tests.
- The precise mechanism for capturing bundle stats (build-output table vs `stats.json` vs `source-map-explorer`).
- Commit granularity — a single atomic commit for the relocation+stub+flag is acceptable since DEPS-02 is one requirement (unlike Phase 104's two independent deps); the screenshot-file deletion may be its own commit or folded in.

</decisions>

<specifics>
## Specific Ideas

- The existing `fileReplacements` swap (`environment.ts` → `environment.prod.ts`, already in `angular.json` production config) is the proven pattern to extend — the phase adds a parallel second entry for the fixture module rather than inventing a new mechanism.
- `MOCK_MODEL_FILES` has exactly one consumer: `view-file.service.ts` (import at line 11, used at line 105 inside the mock else-branch). `USE_MOCK_MODEL` appears only at lines 71 and 92 of the same file. The blast radius of the flag change is a single file.
- The "audit usage → confirm unused → relocate/exclude → verify build+bundle+CI" rhythm is the spine of this slice (carried from Phases 104/105).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — DEPS-02 acceptance text (verbatim mechanism: move `USE_MOCK_MODEL` toggle into `environment.ts`, relocate `mock-model-files.ts` + `screenshot-model-files.ts` out of `services/files/`, exclude via `fileReplacements`, dev-mode mock still works, prod bundle contains none of the mock data); Cross-Cutting Constraints (COMPAT no visual/behavioral regression — dev-mode mock toggle MUST keep working; CI green amd64+arm64; Karma floors hold; bundle does not grow; **no tag/version work**).
- `.planning/ROADMAP.md` §"Phase 106: Mock-Fixture Bundle Hygiene" — phase goal one-liner and milestone goal.

### Source of the concern
- `.planning/codebase/CONCERNS.md` §"Tech Debt" — "Mock-model toggle hardcoded in production service" (`view-file.service.ts:71`, fix approach: move toggle to `environment.ts` + `fileReplacements` to drop mock data) and "`USE_MOCK_MODEL` companion files shipped in dist" (`mock-model-files.ts` 192 lines + `screenshot-model-files.ts` 135 lines; fix approach: move to `src/angular/src/app/tests/fixtures/`, import only behind the env-flag check).

### Project constraints
- `.planning/PROJECT.md` Key Decisions — no constraint specific to this phase beyond the standing Angular build conventions; this phase touches only environment config, one service file, and fixture file locations.

No new external specs/ADRs for this phase — requirements are fully captured above and in the decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing `fileReplacements` pattern** (`src/angular/angular.json`, project `seedsyncarr`, `production` config): already swaps `src/environments/environment.ts` → `src/environments/environment.prod.ts`. The phase extends this array with a second entry for the fixture module — no new build mechanism needed.
- **`src/angular/src/environments/environment.ts` + `environment.prod.ts`**: both export `const environment = { production, logger: {...} }`. Add `useMockModel: true` (dev) / `false` (prod) here.
- **`src/angular/src/app/tests/`**: existing test tree with `mocks/` (service doubles) and `unittests/`. New `fixtures/` dir is the relocation home (D-05).

### Established Patterns
- `view-file.service.ts:71` `private readonly USE_MOCK_MODEL = false;` and `:92` `if (!this.USE_MOCK_MODEL) { ...subscribe... } else { this.buildViewFromModelFiles(MOCK_MODEL_FILES); }` — the only flag/branch site. Import at `:11` `import {MOCK_MODEL_FILES} from "./mock-model-files";`.
- Sibling-phase verification rhythm (104 D-02 / 105 D-07): before/after prod bundle-size delta as the evidence the dep/data left the build.

### Integration Points
- **Files changed:** `src/angular/angular.json` (add fixture `fileReplacements` entry), `src/angular/src/environments/environment.ts` + `environment.prod.ts` (add `useMockModel`), `src/angular/src/app/services/files/view-file.service.ts` (drop class field, branch on `environment.useMockModel`, update import path), move `mock-model-files.ts` → `src/angular/src/app/tests/fixtures/mock-model-files.ts`, add `src/angular/src/app/tests/fixtures/mock-model-files.prod.ts` (empty-map stub), delete `src/angular/src/app/services/files/screenshot-model-files.ts`.
- **Verification touches:** Angular production build (`ng build --configuration production`), the prod `dist/` output (absence grep), dev `ng serve` (mock toggle smoke test), Karma suite (floors), Docker/CI Angular path (amd64+arm64).
- **No backend/Python changes.** No user-observable UI/component-API change.

</code_context>

<deferred>
## Deferred Ideas

- **Backend dependency hardening** (paste/bottle server swap, pexpect, patoolib upper-bounds) — REQUIREMENTS Out of Scope; a later milestone, not this frontend slice.
- **INFRA-01 / mp-logger spawn tests** — deferred to slice 4 (backend production change), per STATE.md.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — backend/upstream-blocked; unrelated to frontend fixtures. Not folded.
- `2026-04-24-migrate-config-set-to-post-body` — backend API change (PROJECT.md Out of Scope); separate milestone. Not folded.

</deferred>

---

*Phase: 106-mock-fixture-bundle-hygiene*
*Context gathered: 2026-06-01*
