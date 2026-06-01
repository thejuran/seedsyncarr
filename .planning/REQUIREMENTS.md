# Requirements: SeedSyncarr — v1.3.0 Slice 3 of 4: Frontend Deps + Dead Code

**Defined:** 2026-05-31
**Core Value:** Reliable file sync from seedbox to local with automated media library integration.
**Milestone:** v1.3.0 — Slice 3 of 4: Frontend Deps + Dead Code (GSD internal label `v1.3.0-s3`; one user-facing `v1.3.0` tag cut after slice 4)
**Source:** `.planning/codebase/CONCERNS.md` — "Dependencies at Risk" (jQuery 4, Font Awesome 4.7, css-element-queries) + "Tech Debt" (mock-model toggle / fixtures in prod bundle); carried as v2 requirements (DEPS-01, DEPS-02) in the slice-2 REQUIREMENTS.md.

> **Release note:** This milestone cuts **no** git tag. The entire 4-slice v1.3.0 program ships under a single combined `v1.3.0` tag, cut only after the final program slice (slice 4) completes.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Frontend Dependencies

- [ ] **DEPS-01a**: The Angular app no longer depends on **jQuery 4**. The dep is removed from `src/angular/package.json` after confirming no source usage (CONCERNS.md notes only Bootstrap referenced it, and Bootstrap 5.3 does not require jQuery); the `_bootstrap-overrides.scss` and `@popperjs/core` paths are audited to confirm removal is safe. The app builds, all Bootstrap-driven interactions (dropdowns, modals, collapses) still work, and the bundle no longer ships jQuery.
- [ ] **DEPS-01b**: The Angular app no longer depends on **Font Awesome 4.7** (EOL). Every remaining `fa-*` icon class usage in templates is inventoried and replaced with its `@phosphor-icons/web` equivalent (the in-progress migration is completed), then the `font-awesome` dep is removed from `src/angular/package.json`. No icon renders missing or visually regressed; only one icon library ships.
- [ ] **DEPS-01c**: The Angular app no longer depends on **css-element-queries** (unmaintained since 2019). Any usage is replaced with the native `ResizeObserver` API; if no usage exists, the dep is removed outright. Element-resize-driven behavior (if any) is unchanged across supported browsers.

### Dead Code / Bundle Hygiene

- [ ] **DEPS-02**: The development-only mock-model fixtures no longer ship in the production bundle. The `USE_MOCK_MODEL` toggle moves from a hardcoded class field in `view-file.service.ts` to a build-time flag in `src/angular/src/environments/environment.ts`, and `mock-model-files.ts` + `screenshot-model-files.ts` are relocated out of `services/files/` and excluded from production output via Angular `fileReplacements` so the mock dataset is tree-shaken from the prod build. Dev-mode mock behavior still works when the env flag is set; production bundle contains none of the mock data.

## Cross-Cutting Constraints

These apply to **every** phase in this slice; each phase's success criteria must hold them:

- **COMPAT — no visual or behavioral regression.** No `fa-*` icon may be dropped without a verified Phosphor replacement rendered in its place; no Bootstrap interaction may break when jQuery is removed; the dev-mode mock toggle must continue to work via the new env flag. No change to any user-observable UI behavior or component API.
- **CI green** on amd64 + arm64 (Angular unit + E2E; Python unaffected but must stay green).
- **No coverage regression** — slice-1 ratchet floors hold or rise: Karma global stmts/branches/fns/lines 83/68/79/83; Python `fail_under` 88 (untouched this slice).
- **Bundle does not grow** — each dependency removal should reduce (never increase) production bundle size; the mock-fixture removal must measurably drop mock data from the prod build.
- **No release/tag/version-bump work** in any phase (single `v1.3.0` tag cut only after slice 4).

## v2 Requirements (deferred to the final program slice — v1.3.0 slice 4)

### Backend Architecture Refactor (slice 4)

- **ARCH-01**: Extract the `Controller` god-class (`controller.py`, ~1115 lines) into cohesive collaborators.
- **ARCH-02**: Refactor `Config` property machinery; auto-discover secret fields (push `secret=True` into the `PROP` declaration so encrypt/decrypt loops discover secrets dynamically).
- **ARCH-03**: Dedup the per-action bulk handler scaffold (`_dispatch_command(...)` helper shared by the five `__handle_action_*` methods and the bulk loop).

### Test Infra (rolled forward — slice 4)

- **INFRA-01**: The three `MultiprocessingLogger` analog tests pass on both `fork` and `spawn` start methods. Requires creating the MP-logger queue from a shared `spawn` context — a **production-module change** to `multiprocessing_logger.py`. Deferred to slice 4 where a backend production change to that module is in thematic scope. (Originally deferred out of slice-2 Phase 102 on 2026-05-31; see slice-2 REQUIREMENTS.md INFRA-01 in git history for the full repro/diagnosis.)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing `paste` / `bottle` Python HTTP server | Backend dependency risk noted in CONCERNS.md, but a server swap is a large behavior-test-heavy effort outside a frontend-deps slice; revisit in a future milestone. |
| Replacing `pexpect`-driven LFTP/SSH | No Python SFTP library matches lftp's parallel-mirror feature set; treated as an external runtime requirement, documented not removed. |
| Pinning `patoolib` / upper-bound hygiene on Python deps | Backend dep hardening, not frontend dead-code; can fold into slice 4 or a later dependency-maintenance pass. |
| jQuery **upgrade** (vs. removal) | Goal is removal; if an audit unexpectedly finds a hard jQuery usage, that becomes a scoped finding — not a version bump. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPS-01a | TBD | Pending |
| DEPS-01b | TBD | Pending |
| DEPS-01c | TBD | Pending |
| DEPS-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 4 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 4 ⚠️ (resolved at roadmap creation)

---
*Requirements defined: 2026-05-31*
*Last updated: 2026-05-31 after defining v1.3.0 slice 3 requirements*
