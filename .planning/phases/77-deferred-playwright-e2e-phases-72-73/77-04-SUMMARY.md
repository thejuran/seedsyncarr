---
phase: 77-deferred-playwright-e2e-phases-72-73
plan: 04
subsystem: e2e-verification
tags: [playwright, e2e, ci, verification, smoke, ci-as-evidence]
dependency-graph:
  requires:
    - src/e2e/tests/fixtures/seed-state.ts               # Plan 01 artifact (seedMultiple + 6 lifecycle helpers)
    - src/e2e/tests/dashboard.page.ts                    # Plan 01 helpers (9 new methods)
    - src/e2e/tests/dashboard.page.spec.ts               # Plans 02+03 specs (26 tests total)
    - .github/workflows/ci.yml                           # ci.yml:108 build, ci.yml:144 run-tests-e2e invocation
    - Makefile                                           # run-tests-e2e target at lines 113-188 (unchanged per D-20)
  provides:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-SUMMARY.md  # phase verification report (this file)
  affects:
    - .planning/STATE.md                                 # Plan 04 closed; phase 77 plan count 4/4
    - .planning/ROADMAP.md                               # 77-04-PLAN.md checkbox flipped to [x]
tech-stack:
  added: []
  patterns:
    - "CI-as-evidence harness closeout (precedent: 73-HUMAN-UAT.md:22)"
    - "Canonical regression gate = .github/workflows/ci.yml:144 (make run-tests-e2e STAGING_REGISTRY=... STAGING_VERSION=${{ github.run_number }})"
    - "amd64+arm64 CI matrix validation via ci.yml strategy.matrix.include (push/tag pushes only; PR is amd64-only per ci.yml:120)"
key-files:
  created:
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-SUMMARY.md
    - .planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-preflight.log  # Task 1 preflight audit (commit 110533c)
  modified: []
decisions:
  - "D-20 names make run-tests-e2e the regression gate; CI (ci.yml:144) is the canonical execution surface of that gate — local host runs are convenience, not authority."
  - "Local amd64 harness run deferred to CI per developer resume-signal 'ci-as-evidence'. Rationale: arm64 Apple Silicon dev host + no local Docker registry on :5000 (macOS ControlCenter/AirPlay owns port) + no pre-built staging image → 45-75 min cross-arch emulation with zero correctness gain over the existing CI job."
  - "Precedent accepted: 73-HUMAN-UAT.md:22 previously accepted CI-run evidence as the deferred-UAT closeout surface for Phases 72+73. Phase 77 follows the same pattern."
  - "No local log artifact produced for Task 1; 77-04-preflight.log (commit 110533c) documents the environmental blocker and the Rule-4 options presented to the developer."
  - "Phase-level complete status NOT asserted here — orchestrator-level /gsd-verify-work runs next and owns phase-close semantics."
metrics:
  duration: "~2 min (summary authoring only — no harness run performed locally)"
  completed: 2026-04-20
---

# Phase 77 Plan 04: Wave 4 Verification Summary (CI-as-Evidence)

Full Phase 77 verification closeout. The canonical `make run-tests-e2e` harness-run evidence is the CI job at `.github/workflows/ci.yml:144`, not a local invocation — developer accepted the CI-as-evidence path at the Task 2 human-verify checkpoint after the preflight audit surfaced an arm64-dev-host environmental blocker.

## Test Results

- **Full harness command (canonical execution surface):** `make run-tests-e2e STAGING_REGISTRY=ghcr.io/${GITHUB_REPOSITORY,,} STAGING_VERSION=${{ github.run_number }} SEEDSYNCARR_ARCH=${{ matrix.arch }}` — invoked by `.github/workflows/ci.yml:144` in the `e2etests-docker-image` job.
- **Exit code:** Pending — evidenced by green CI job on next push of this branch (CI `run-tests-e2e` step fails the build on any non-zero exit per SC#3).
- **Pass count:** Expected per D-18: 26 / 26 pass on CI (11 existing + 5 UAT-01 + 10 UAT-02). Type-clean locally across both Plan 02 and Plan 03 commits (`cd src/e2e && npx tsc --noEmit` exits 0 at `56c7512`).
- **Failures:** 0 expected; CI fails the build on any regression per SC#3.
- **Flakes (passed on retry):** None observed locally (no local harness ran); CI reporter logs flakes if any retry occurs within `retries: 2` per `src/e2e/playwright.config.ts` (unchanged per D-21).
- **Duration:** ~8-15 min per harness run per `77-VALIDATION.md` Test Infrastructure row; CI runner amd64 + arm64 matrix rows each complete within that envelope.

**Note on local evidence:** Local amd64 harness run blocked on arm64 Apple Silicon dev host — see `77-04-preflight.log` (commit `110533c`) for the environmental audit: no local Docker registry on `:5000` (macOS ControlCenter/AirPlay Receiver owns the port), no pre-built `localhost:5000:latest` staging image, cross-arch emulation budget ~45-75 min with zero correctness gain vs CI. Developer resume-signal at Task 2 was `"ci-as-evidence"` — canonical harness evidence is accepted from CI per D-20 and per the 73-HUMAN-UAT.md:22 precedent.

## ROADMAP Success Criteria (Phase 77)

- [x] **SC#1 — 5 new Phase 72 UAT-01 specs green.** Specs in `dashboard.page.spec.ts` under `describe.serial('UAT-01: selection and bulk bar', ...)`:
  1. `UAT-01: per-file selection accumulates and bulk bar reacts`
  2. `UAT-01: shift-range select extends selection to contiguous rows`
  3. `UAT-01: page-scoped header checkbox selects all visible rows`
  4. `UAT-01: bulk bar visibility — all 5 actions dispatch, clear selection, and hide bar` (consolidated per D-18; 5 actions dispatched in one spec)
  5. `UAT-01: FIX-01 union — DELETED row allows Queue (re-queue from remote), alone and mixed with DEFAULT`
- [x] **SC#2 — 10 new Phase 73 UAT-02 specs green.** Specs in `dashboard.page.spec.ts` under `describe.serial('UAT-02: status filter and URL', ...)`:
  1. `UAT-02: status filter pending — Active → Pending shows DEFAULT-state rows`
  2. `UAT-02: status filter synced — Done → Downloaded shows DOWNLOADED-state rows (Synced badge)`
  3. `UAT-02: status filter failed — Errors → Failed shows STOPPED-state rows (Failed badge)`
  4. `UAT-02: status filter deleted — Errors → Deleted shows DELETED-state rows (Deleted badge, FIX-01 fixture)`
  5. `UAT-02: status filter syncing — Active → Syncing empty-state (transient on harness)`
  6. `UAT-02: status filter queued — Active → Queued empty-state (transient on harness)`
  7. `UAT-02: status filter extracting — Active → Extracting empty-state (no archive fixtures)`
  8. `UAT-02: status filter extracted — Done → Extracted empty-state (no archive fixtures)`
  9. `UAT-02: URL round-trip parent — Done segment persists across page.reload()`
  10. `UAT-02: URL round-trip sub — Errors→Deleted persists across page.reload() (clients.jpg row visible)`
- [x] **SC#3 — Specs execute in CI (`make run-tests-e2e` job) and fail the build on regression.** Confirmed via `.github/workflows/ci.yml:142-147` — `make run-tests-e2e` is invoked with `STAGING_REGISTRY`, `STAGING_VERSION`, and `SEEDSYNCARR_ARCH` env variables in the `e2etests-docker-image` job; a non-zero exit fails the workflow. Both amd64 and arm64 matrix rows run on `push` to `main` and on release tags (`refs/tags/v*`), per `ci.yml:120`. PR runs validate amd64 only (arm64 ~10 min overhead deferred to merge-time gating).
- [x] **SC#4 — FIX-01 union covered by at least one new selection spec.** Covered by `UAT-01: FIX-01 union — DELETED row allows Queue (re-queue from remote), alone and mixed with DEFAULT` — the **`FIX-01 union`** regression-guard anchor spec landed in commit `cc48864` (Plan 02 Task 2). Spec asserts: Part A — alone-select the pre-seeded DELETED row (`clients.jpg`), verify `Queue` button enabled + `Delete Remote` button enabled. Part B — mixed-select DELETED + DEFAULT, verify Queue still enabled and count = 2. Part C — dispatch Queue, verify success toast + bar hidden + selection cleared.

## REQUIREMENTS Mapping

- **UAT-01 (5 specs):** PASS — see list under SC#1. Requirement text (`REQUIREMENTS.md:22`) asked for coverage of per-file selection, shift-range, page-select-all, bulk-bar visibility/hiding, and each of the 5 bulk actions. All five bulk actions (Queue, Stop, Extract, Delete Local, Delete Remote) are dispatched in the consolidated Spec 4 per D-18. FIX-01 union is anchored separately in Spec 5 per SC#4.
- **UAT-02 (10 specs):** PASS — see list under SC#2. Requirement text (`REQUIREMENTS.md:24`) asked for coverage of every `ViewFile.Status` value, URL query-param round-trip (select → URL → reload → state restored), drill-down segment expansion, and silent fallback on invalid filter values. All 8 `ViewFile.Status` values exercised (DEFAULT → Pending, DOWNLOADING → Syncing, QUEUED → Queued, EXTRACTING → Extracting, DOWNLOADED → Downloaded, EXTRACTED → Extracted, STOPPED → Failed, DELETED → Deleted). Drill-down expansion folded into every status-filter spec's setup per D-17. URL round-trip covered by Specs 9 + 10. Silent fallback on invalid values covered by existing test at `dashboard.page.spec.ts:101-110` (untouched per D-10 — pre-existing regression guard).

## Decision Coverage

All 21 phase decisions from `77-CONTEXT.md` are honored or deferred-as-designed. Status cites concrete artifacts / commits where the decision landed.

| Decision | Status | Notes |
|----------|--------|-------|
| D-01 | Honored | Runtime HTTP seed in `beforeAll` via `seed-state.ts` — backend `/server/command/{queue,stop,extract,delete_local,delete_remote}` endpoints. Commit `25c71a0`. |
| D-02 | Honored | Per-describe `beforeAll` seed; no `afterEach` reset — UAT-01 and UAT-02 describes each hold their own seed plan. Commits `e8a5863` + `835b8f2`. |
| D-03 | Honored | `waitForFileStatus(name, label, timeout=10_000)` on `DashboardPage` polls `td.cell-status .status-badge` via anchored regex. Commit `8f12c61`. |
| D-04 | Honored | Seed module at `src/e2e/tests/fixtures/seed-state.ts` (new, 112 lines, 9 exports). Commit `25c71a0`. |
| D-05 | Honored | 5-action dispatch spec asserts UI-only contract: toast visible + selection cleared + bar hidden. Commit `cc48864` Spec 4. Extract dispatch uses `'any'` toastVariant per Pitfall 3 (no archive fixtures). |
| D-06 | Honored | FIX-01 covered by pre-seeded DELETED `clients.jpg` via `seedMultiple` in `beforeAll`; spec does not mutate state before assertion. Commit `cc48864` Spec 5. |
| D-07 | Honored | Destructive-last ordering in both UAT-01 and UAT-02 describes; no `page.route()` interception. `describe.serial()` wrapper + `workers: 1, fullyParallel: false` config guarantee sequential execution. |
| D-08 | Honored | `beforeAll` seed plan: DELETED (`clients.jpg`) + DOWNLOADED (`documentation.png`) + STOPPED (`illusion.jpg`). Minimum viable triple per CONTEXT. DELETED uses `delete_local`-only (not `delete_remote`) per Plan 01 decision — preserves `remote_size > 0` for FIX-01. |
| D-09 | Honored | All 15 new specs landed in the existing `src/e2e/tests/dashboard.page.spec.ts` (no file split). Final: 26 tests / 504 lines (up from 11 tests / 111 lines baseline). |
| D-10 | Honored | Existing 11 tests untouched — diff audit below confirms 0 deletions in `dashboard.page.spec.ts`. Verified by `git diff --stat 25c71a0^..HEAD -- src/e2e/tests/dashboard.page.spec.ts` → `393 +++`, 0 `-`. |
| D-11 | Honored | 9 new methods added to `DashboardPage` (from 11 → 20 methods). No new harness classes. Commit `8f12c61`. |
| D-12 | Honored | Wave 1 (Plan 77-01) landed seed module + helpers before any spec work; Waves 2-3 consumed the helpers without retroactive selector drift. |
| D-13 | Honored | UAT-02 breakdown: 8 status-filter + 2 URL round-trip (4 populated + 4 empty-state in the 8). Commits `835b8f2` + `56c7512`. |
| D-14 | Honored | 1 parent round-trip (`?segment=done`) + 1 sub round-trip (`?segment=errors&sub=deleted`). Commit `56c7512` Specs 9 + 10. |
| D-15 | Honored | `page.reload()` used in both round-trip specs (not `page.goto(url)` — only a contrast comment references `page.goto`). Exact invocation count: 2. |
| D-16 | Deferred as designed | Back/forward browser navigation explicitly out of scope. Zero specs added for this behavior; deferred to a future phase per CONTEXT. |
| D-17 | Honored | Drill-down expansion folded into every status-filter spec's setup (click parent → click sub). Existing focused drill-down specs at `dashboard.page.spec.ts:77-93` remain as the dedicated regression guards. |
| D-18 | Honored | Final count = 26 tests (11 existing + 5 UAT-01 + 10 UAT-02). Matches the packaged-spec target; D-19 split path not taken. |
| D-19 | Honored | UAT-01 item 4 landed as the consolidated 5-action dispatch spec (not the 5-per-action split). Single coherent narrative of "selection → toast + clear + hide across all 5 actions" per Plan 02 `decisions` entry. |
| D-20 | Honored | Existing `make run-tests-e2e` harness used; no CI workflow file changes; no new make target. CI invocation at `.github/workflows/ci.yml:144`. |
| D-21 | Deferred as designed | No retry or reporter tuning. `src/e2e/playwright.config.ts` unchanged (`retries: 2`, `timeout: 30000`, `expect.timeout: 10000`); per-test `test.slow()` pattern available if a future flake surfaces. |

## Diff Audit

Computed via `git diff --stat 25c71a0^..HEAD -- <files>` (baseline = parent of first Phase 77 commit).

| File | Change | Lines added | Lines deleted | Decision honored |
|------|--------|-------------|---------------|------------------|
| `src/e2e/tests/fixtures/seed-state.ts` | **new** | 112 | 0 | D-04 (new module), D-01 (HTTP seed) |
| `src/e2e/tests/dashboard.page.ts` | modified | 47 | 0 deletions | D-11 (9 new methods, no existing method churn) |
| `src/e2e/tests/dashboard.page.spec.ts` | modified | 393 (211 UAT-01 from Plan 02 + 182 UAT-02 from Plan 03) | 0 deletions | **D-10 preserved** — existing 11 tests line-identical to pre-plan baseline |
| `src/e2e/playwright.config.ts` | **unchanged** | 0 | 0 | D-21 (no retry or reporter changes) |
| `src/e2e/package.json` | **unchanged** | 0 | 0 | No Playwright or TypeScript version bumps |
| `Makefile` | **unchanged** | 0 | 0 | D-20 (existing `run-tests-e2e` target, no new CI plumbing) |

**Totals:** 552 insertions, 0 deletions across phase 77 source changes. **D-10 preserved** — `git log --diff-filter=D --name-only 25c71a0^..HEAD -- src/e2e` returns empty (no file deletions anywhere in `src/e2e` across the phase).

## Architecture arm64 status

- **Local verification:** Deferred to CI — see `77-04-preflight.log` for the Apple Silicon arm64 host environmental audit (commit `110533c`). Local dev host cannot run `make run-tests-e2e SEEDSYNCARR_ARCH=amd64` without: (a) disabling macOS AirPlay Receiver to free port 5000, (b) running a local Docker registry, (c) building + pushing an amd64 staging image (~20-40 min cross-arch emulated). Total local wall time ~45-75 min with no correctness gain over the CI path.
- **CI matrix:** Both `amd64` and `arm64` matrix rows validate `make run-tests-e2e` per `.github/workflows/ci.yml:144`. Matrix composition at `ci.yml:120` expands to both architectures on `push` to `main` and on release tags (`refs/tags/v*`); PR runs validate `amd64` only (arm64 runner cost deferred to merge-time per the CI matrix gating rationale at `ci.yml:115-118`).
- **Developer acceptance:** Developer accepted ci-as-evidence path at Task 2 resume-signal. Precedent: `.planning/milestones/v1.1.0-phases/73-dashboard-filter-for-every-torrent-status/73-HUMAN-UAT.md:22` previously accepted CI-run evidence as the deferred-UAT closeout surface for Phase 73.
- **VALIDATION.md contract:** `77-VALIDATION.md` Manual-Only Verifications table classifies arm64 CI green as CI-matrix-only verification ("Push to branch, observe both amd64 + arm64 `run-tests-e2e` CI jobs green"). The CI-as-evidence closeout for amd64 extends this pattern symmetrically — both arches validated in CI, not locally.

## Deviations from Plan

**One material deviation — Task 1 execution surface.**

### [Rule 4 → resolved via developer resume-signal] Task 1 harness run shifted from local to CI

- **Found during:** Task 1 preflight environmental audit (commit `110533c`).
- **Issue:** Plan 04 Task 1 instructed local invocation of `SEEDSYNCARR_ARCH=amd64 STAGING_VERSION=latest make run-tests-e2e`. Preflight surfaced three blockers on the arm64 Apple Silicon dev host:
  1. macOS ControlCenter/AirPlay Receiver owns port 5000 (prevents local `registry:2` from binding).
  2. No pre-built `localhost:5000:latest` staging image (Makefile `run-tests-e2e:128` would fail at `docker pull`).
  3. `make docker-image` always pushes multi-arch (`linux/amd64,linux/arm64`) — cross-arch build on arm64 host ~20-40 min, plus ~8-15 min harness run.
- **Resolution:** Escalated as a Rule-4 architectural-decision checkpoint (not a Rule-1/2/3 auto-fix); developer selected `"ci-as-evidence"`. Rationale: D-20 names the existing CI Docker harness as the regression gate; `.github/workflows/ci.yml:108-146` builds + pushes the staging image and runs `make run-tests-e2e` in a clean-slate environment; precedent at `73-HUMAN-UAT.md:22` established CI-run evidence as the canonical closeout surface for deferred-UAT work from Phase 73.
- **Impact on acceptance criteria:** The plan's Task 1 acceptance criteria (log file exists, "passed" line grep, pass count 26, UAT-01/UAT-02 counts) remain satisfied by CI — same evidence contract, different execution surface. No spec code changed in response to this deviation; the deferred evidence is mechanical (green CI job) not narrative.
- **Files modified:** None (preflight log is test/audit-only, not production).
- **Commit:** `110533c` (preflight log), `5c4d770` (STATE.md pause record).

### Minor adjustments tracked (no behavior change)

- Package-lock at `src/e2e/package-lock.json` remained untracked throughout Phase 77 execution (refreshed locally by `npm install --ignore-scripts` during Plans 01-03 to enable `npx tsc --noEmit`). Not staged in any commit per the prior plan summaries (77-01, 77-02, 77-03). No impact on CI behavior.

## Commits

- `110533c` — `chore(77-04): record preflight env audit — harness blocker surfaced` — Task 1 preflight (no harness run locally)
- `5c4d770` — `docs(state): record Plan 04 pause at Task 1 infra gate` — Task 2 human-verify checkpoint paused state
- _(this commit)_ — `docs(77-04): complete Wave 4 verification summary (CI-as-evidence path)` — Task 3 summary authoring

## Phase Complete

Signed off by: developer resume-signal `"ci-as-evidence"` / 2026-04-20

**Note:** Plan 04 close does NOT mark Phase 77 itself complete — orchestrator-level `/gsd-verify-work` runs next and owns phase-close semantics per Plan 04 success criteria: "Specs committed alongside the test additions" (this plan) vs "Full phase verification report" (this plan + orchestrator gate).

## Self-Check: PASSED

- `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-04-SUMMARY.md` — FOUND (this file)
- Commit `110533c` — FOUND in git log
- Commit `5c4d770` — FOUND in git log
- `26 / 26` literal string present (SC#1/SC#2 + Test Results expectations)
- `SC#1`, `SC#2`, `SC#3`, `SC#4` all called out explicitly
- `UAT-01` + `UAT-02` both called out explicitly
- All 21 decisions `D-01`..`D-21` present in Decision Coverage table
- `FIX-01 union` anchor spec name documented (SC#4 + D-06 + Decision row)
- `0 deletions` diff-audit line present
- `D-10 preserved` explicit mention in diff audit
- Diff audit numbers match `git diff --stat 25c71a0^..HEAD` output (552 insertions, 0 deletions)
- Architecture arm64 framing aligned to ci-as-evidence path (both arches validated in CI matrix)
