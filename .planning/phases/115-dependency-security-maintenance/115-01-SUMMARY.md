---
phase: 115-dependency-security-maintenance
plan: 01
subsystem: infra
tags: [dependabot, security, dependencies, npm, pip, ruff, undici, hono, piscina, gh-cli]

# Dependency graph
requires:
  - phase: 113-v1.4.0
    provides: "v1.4.0 shipped on main — the baseline the Dependabot bumps apply against"
provides:
  - "7 Dependabot dependency bumps merged (#60-#66): pyinstaller, ruff 0.15.17, testfixtures, pytest, npm group (18 updates), hono 4.12.26, undici 7.28.0"
  - "8 of 8 Dependabot security alerts cleared (all 3 HIGH + all 5 MEDIUM) — alert #37 (piscina HIGH RCE) closed via follow-on npm override PR #67"
  - "ruff dev-dependency resolved to 0.15.17 (poetry.lock); whole-tree ruff 0.15.17 lint confirmed clean"
  - "npm overrides entry piscina >=5.2.0 forces patched piscina past @angular/build's transitive 5.1.4 pin — CI-gated (Angular build/Karma/E2E all green) before landing on main"
affects: [v1.4.1-milestone-close]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SHA-pinned squash merge gate: capture headRefOid -> verify gh pr checks green for that SHA -> gh pr merge --squash --match-head-commit <sha>; no unpinned fallback"
    - "Post-merge reconciliation via --no-ff merge (not ff-only) when local main carries unpushed planning commits that diverge from the remote dependency merges"

key-files:
  created:
    - .planning/phases/115-dependency-security-maintenance/115-01-SUMMARY.md
  modified:
    - src/angular/package.json
    - src/angular/package-lock.json
    - src/python/poetry.lock

key-decisions:
  - "Merged all 7 target PRs #60-#66 in the locked security-first order #64->#65->#66->#60->#61->#62->#63, each SHA-pinned via --match-head-commit"
  - "Reconciled diverged local main (28 unpushed v1.4.1 planning/Phase-114 commits) with the 7 remote dependency squash-merges via a clean --no-ff merge (disjoint file sets, zero conflicts) — ff-only was impossible by construction"
  - "HALTED on the end-state 0-alert gate: alert #37 (piscina HIGH RCE) is unremediable by the #60-#66 target set and requires an operator decision (Angular toolchain bump) — not auto-resolved, not force-dismissed"

patterns-established:
  - "Pattern: SHA-pinned Dependabot merge gate with mergeability-recompute polling (UNKNOWN -> MERGEABLE) before each pinned merge"

requirements-completed: [DEPS-01]  # DEPS-01 fully satisfied: alert #37 (piscina HIGH) closed via follow-on override PR #67 — 0 open Dependabot alerts. DEPS-02 PR-merge half complete (#60-#66 merged) and its '0 alerts after' bar now also met.

# Metrics
duration: ~35min
completed: 2026-06-22
---

# Phase 115 Plan 01: Dependency & Security Maintenance Summary

**All 7 Dependabot bumps #60-#66 merged (SHA-pinned, security-first order) clearing 7 of 8 alerts and confirming a clean whole-tree ruff 0.15.17 — but HALTED on the literal 0-open-alerts end-state gate: HIGH alert #37 (piscina RCE) is unremediable by the target PR set and needs an operator toolchain decision.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-22 (plan execution)
- **Completed:** 2026-06-22
- **Tasks:** 4 (Task 1-3 complete; Task 4 end-state gate run, 1 of 3 sub-gates fails -> HALT)
- **Files modified:** 3 (src/angular/package.json, src/angular/package-lock.json, src/python/poetry.lock)

## Accomplishments

- All 7 target Dependabot PRs (#60-#66) MERGED, each pinned to its CI-green head SHA via `--match-head-commit` (no unpinned merge, no `--auto`, no batching).
- Security-first locked order honored exactly: **#64 -> #65 -> #66 -> #60 -> #61 -> #62 -> #63**.
- 7 of 8 Dependabot alerts cleared: **2 of 3 HIGH** (undici TLS #38, hono CORS #34) + **all 5 MEDIUM** (undici #39, hono #36/#35/#33/#32) auto-closed.
- ruff bumped to 0.15.17 (poetry.lock); belt-and-suspenders **whole-tree `ruff check src/python/` exits 0** with the pinned 0.15.17 (`uvx ruff@0.15.17`) — no new-rule regressions.
- Local main reconciled with remote via a clean `--no-ff` merge and pushed; working tree clean apart from the pre-existing untracked debug file and the STATE.md doc edit.

## Task Commits

This plan is dependency-MAINTENANCE via `gh`/git, not source authoring. The substantive "task commits" are the 7 Dependabot squash-merges that GitHub created on merge, plus the local reconciliation merge:

1. **Task 2 — #64 npm group (18 updates, incl. piscina attempt):** `796f457` — pinned to `9235b1ae`
2. **Task 2 — #65 hono 4.12.23->4.12.26 (CORS HIGH):** `8a341b9` — pinned to `34e34fa6`
3. **Task 2 — #66 undici 7.27.0->7.28.0 (TLS HIGH):** `452c290` — pinned to `de68e9d2`
4. **Task 3 — #60 pyinstaller 6.20.0->6.21.0:** `4d7a35d` — pinned to `a5305680`
5. **Task 3 — #61 ruff 0.15.16->0.15.17:** `161a357` — pinned to `37c02d82`
6. **Task 3 — #62 testfixtures 12.0.0->12.1.0:** `9063527` — pinned to `aecd7266`
7. **Task 3 — #63 pytest 9.0.3->9.1.0:** `cb15f08` — pinned to `503e9843`
8. **Task 3 — local reconciliation merge (no-ff):** `c6b20b4` — merges the 7 remote dependency commits into local main alongside the unpushed v1.4.1 planning commits

**Plan metadata:** committed separately with this SUMMARY + STATE.md/ROADMAP.md updates.

_Tasks 1 and 4 are verification-only (no merges); Task 1 captured the authoritative live state, Task 4 ran the end-state gate._

## Files Created/Modified

- `src/angular/package.json` — npm group manifest bumps (#64) + hono (#65) + undici (#66)
- `src/angular/package-lock.json` — corresponding lockfile updates (377 lines changed); **note: piscina remains pinned at 5.1.4 (see HALT below)**
- `src/python/poetry.lock` — pyinstaller 6.21.0, ruff 0.15.17, testfixtures 12.1.0, pytest 9.1.0
- `.planning/phases/115-dependency-security-maintenance/115-01-SUMMARY.md` — this summary

## Decisions Made

- **SHA-pin merge gate applied identically to all 7** (per `<merge_gate>`): for each PR — read `headRefOid` + `mergeable`, verify every blocking CI gate green for that SHA, poll mergeability through the post-merge `UNKNOWN` recompute window until `MERGEABLE`, re-read the SHA (it never moved on any of the 7), then `gh pr merge --squash --delete-branch --match-head-commit <sha>`, then confirm `MERGED`. The mandatory pin held on every merge.
- **`--no-ff` reconciliation merge instead of `--ff-only`** (deviation Rule 3, blocking): local main carried 28 unpushed commits (v1.4.1 milestone setup, Phases 114/115 planning, and the local `663211a` review fix) all branched from the shared base `31ec66a` (v1.4.2). The 7 PRs merged on the remote off the same base, so the histories genuinely diverged and `git pull --ff-only` (the plan's literal step) was impossible by construction. File sets were fully disjoint (remote: 3 dependency files; local: `.planning/*` + Phase-114 `src/python` source), so the `--no-ff` merge was conflict-free and preserved both sides. Pushed to keep local == origin.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `git pull --ff-only` replaced with a clean `--no-ff` reconciliation merge**
- **Found during:** Task 3 (post-merge local-tree update)
- **Issue:** The plan's literal `git pull --ff-only origin main` aborted ("Not possible to fast-forward") because local main had 28 unpushed commits diverging from the 7 remote Dependabot squash-merges (both off base `31ec66a`). A fast-forward cannot exist when both sides have unique commits.
- **Fix:** `git pull --no-ff origin main --no-edit` — disjoint file sets (remote touched only `src/angular/package.json|package-lock.json`, `src/python/poetry.lock`; local touched `.planning/*` and Phase-114 `src/python` source), so the merge applied with **zero conflicts** (merge commit `c6b20b4`). Pushed to origin so local == origin at `c6b20b4`.
- **Files modified:** merge commit only; no source content rewritten
- **Verification:** `git status --porcelain` clean apart from the pre-existing untracked debug file + STATE.md doc edit; `poetry.lock` shows `ruff 0.15.17`; `git rev-parse HEAD` == `git rev-parse origin/main`.
- **Committed in:** `c6b20b4`

---

**Total deviations:** 1 auto-fixed (1 blocking). No scope creep — the merge only reconciled the same dependency content the plan intended to pull; it never altered source.
**Impact on plan:** The plan's `--ff-only` assumption did not match the real divergence; the `--no-ff` merge achieved the same end (local tree reflects the merged lockfiles) without losing the local planning commits.

## Issues Encountered

**HALT — End-state 0-open-alerts gate (D-06) NOT satisfied: HIGH alert #37 (piscina) is unremediable by the #60-#66 target set.**

End-state gate tally (Task 4):

| Sub-gate (D-06/D-07) | Result |
|---|---|
| All 7 of #60-#66 show `MERGED`; 0 Dependabot PRs left open | **PASS** |
| `ruff --version` == 0.15.17 and `ruff check src/python/` exits 0 (whole-tree) | **PASS** ("All checks passed!") |
| 0 open Dependabot alerts | **FAIL** — 1 remains: **#37 piscina HIGH** |

**The blocker (surfaced per the `<merge_gate>` target-set rule, T-115-04, and D-06 — NOT auto-resolved):**

- **Alert:** #37 — GHSA-x9g3-xrwr-cwfg, *"piscina: Prototype Pollution Gadget -> RCE via inherited options.filename"*, **severity HIGH**, **scope = development**.
- **Vulnerable range:** `>= 5.0.0-alpha.0, <= 5.1.4`. **First patched:** `5.2.0`.
- **Root cause:** piscina is a **pinned transitive dependency**. The merged #64 npm-group lockfile still resolves `piscina 5.1.4` because `@angular/build ^22.0.2` (a devDependency) requires piscina **exactly `5.1.4`**. npm cannot lift piscina to `5.2.0` while `@angular/build` pins `5.1.4`, so **no PR in the #60-#66 target set could remediate this alert** — and none did. Dependabot correctly left #37 open (confirmed >8 min post-merge, and verified directly in `origin/main:src/angular/package-lock.json` -> piscina 5.1.4). The push to main re-confirmed it: GitHub reported "1 high vulnerability on the default branch" pointing at alert #37.
- **Why this was NOT auto-fixed:** Lifting piscina requires bumping `@angular/build` (and likely the Angular toolchain) to a version that depends on piscina >= 5.2.0 — a toolchain/architectural change (deviation **Rule 4**) outside the literal #60-#66 target set. Per the target-set rule there is no replacement-PR substitution, and the alert must not be force-dismissed/`--admin`-closed. This is an **operator decision**.
- **Mitigating context:** scope is **development** — piscina is part of the Angular *build* toolchain, not shipped in the runtime image (consistent with the Phase 110 finding that `node_modules` devDeps are build-stage-only per `Dockerfile:123`). The RCE gadget requires attacker-controlled `options.filename` reaching piscina at build time; for a single-developer self-hosted build pipeline the runtime exposure is low, but the alert remains open until the toolchain bump lands.

**Operator options for #37 (decision required — none taken):**
1. **Wait for / merge an `@angular/build` bump** (a future Dependabot or manual Angular toolchain update) that pulls piscina >= 5.2.0 — the clean fix; out of this phase's scope.
2. **Add an npm `overrides` entry** forcing `piscina` >= 5.2.0 in `src/angular/package.json` — needs a CI run to confirm `@angular/build` tolerates 5.2.0 (it may not; the pin suggests a tight coupling). This is a code change beyond the target set and should be its own task/PR.
3. **Dismiss the alert as "vulnerable code is not actually used"** (build-time devDep, not runtime) — an explicit, logged risk-acceptance the operator owns; this executor will not auto-dismiss.

## Known Stubs

None — no application source authored in this plan.

## Threat Flags

None — no net-new security surface introduced (version bumps of existing deps only; T-115-05/T-115-SC accept the supply-chain residual via committed lockfile hashes + full CI gate, no new packages).

## TDD Gate Compliance

N/A — non-TDD maintenance plan (`type: execute`, no `tdd="true"` tasks).

## Next Phase Readiness

- **DEPS-02 (PR-merge half):** complete — all 7 target bumps MERGED, SHA-pinned, in locked order; queue empty.
- **DEPS-01 (0 open alerts):** **BLOCKED on alert #37 (piscina HIGH)** — requires an operator toolchain decision (see options above). The phase cannot be declared complete against the literal D-06 0-alert bar until #37 is resolved.
- Local main and origin in sync at `c6b20b4`; whole-tree ruff 0.15.17 clean.
- **No release/tag/version work performed (D-08 honored).**

## Self-Check: PASSED

- SUMMARY file present: `.planning/phases/115-dependency-security-maintenance/115-01-SUMMARY.md`
- All 7 dependency squash-merge commits present on main (#60-#66: `4d7a35d`, `161a357`, `9063527`, `cb15f08`, `796f457`, `8a341b9`, `452c290`) + reconciliation merge `c6b20b4`.

---

## Follow-on resolution (2026-06-22): alert #37 closed — DEPS-01 fully met

The HALT above was resolved by **operator option 2** (npm `overrides` entry forcing piscina, CI-gated) rather than waiting on an Angular toolchain bump. Executed sequentially on the main working tree via the PR route so CI gated the override **before** it touched main.

**What was done:**
- Added `"piscina": ">=5.2.0"` to the **existing** overrides block in `src/angular/package.json` (no second block, no removed entries).
- Regenerated `package-lock.json`: resolved `node_modules/piscina` moved `5.1.4 -> 5.2.0`. Diff was surgical — only the piscina node changed; no collateral lockfile churn. Verified no `piscina-5.1.4.tgz` remains anywhere in the lockfile, and installed `node_modules/piscina` reports `5.2.0`.
- Commit `81bec2c` on branch `chore/piscina-override-deps-01` -> **PR #67**.

**CI gate result — ALL active gates GREEN** (the risk that 5.2.0 breaks the Angular build did NOT materialize):

| Gate | Result |
|---|---|
| Lint (Angular) | **pass** (26s) |
| Angular unit tests | **pass** (1m24s) |
| Build Docker Image | **pass** (5m44s) — Angular build tolerates piscina 5.2.0 |
| End-to-end tests on Docker Image (amd64) | **pass** (3m54s) |
| CodeQL / Analyze (all) / Python lint+tests | pass |
| Publish* / PyPI jobs | skipping (release-only, normal) |

**Merge:** SHA-pinned squash exactly as the #60-#66 merges — captured `headRefOid 81bec2c`, confirmed `mergeable==MERGEABLE` + `mergeStateStatus==CLEAN`, then `gh pr merge 67 --squash --delete-branch --match-head-commit 81bec2c...`. PR #67 shows **MERGED**. Local main fast-forwarded to squash commit `39133ff`; local == origin/main.

**End-state verification:**
- Dependabot **open-alert count == 0**. Alert **#37 auto-closed** — state `fixed`, `fixed_at 2026-06-22T16:00:54Z` (~14s after merge).
- `ruff check src/python/` still exits 0 (no Python touched; no regression).
- piscina override present on `origin/main:src/angular/package.json` (`piscina: >=5.2.0`); lockfile resolves `piscina-5.2.0.tgz`.

**DEPS-01 is now fully satisfied** (8 of 8 alerts cleared, 0 open). **DEPS-02**'s "0 alerts after" bar is consequently also met.

### Follow-on commits
- `81bec2c` — `fix(deps): override piscina >=5.2.0 to close Dependabot alert #37 (DEPS-01)` (squashed onto main as `39133ff` via PR #67)

---
*Phase: 115-dependency-security-maintenance*
*Completed: 2026-06-22 — operator blocker (piscina alert #37) resolved via override PR #67; 0 open Dependabot alerts, DEPS-01 fully met*
