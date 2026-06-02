---
gsd_state_version: 1.0
milestone: v1.4.0
milestone_name: Launch-Hardening for Public Release
status: executing
stopped_at: Phase 112 context gathered
last_updated: "2026-06-02T22:40:33.430Z"
last_activity: 2026-06-02 -- Phase 112 execution started
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-02)

**Core value:** Reliable file sync from seedbox to local with automated media library integration
**Current focus:** Phase 112 — defensive-guards-code-hardening

## Current Position

Phase: 112 (defensive-guards-code-hardening) — EXECUTING
Plan: 1 of 3
Status: Executing Phase 112
Last activity: 2026-06-02 -- Phase 112 execution started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Roadmap shape (v1.4.0): 4 phases derived from the 18 v1.4.0 requirements (SCAN-01/02, CFG-01..04, GUARD-01..06, LAUNCH-01..06). Two largely-disjoint tracks (code + presentation) plus one cross-cutting change.

- **Phase 110 (Hostile-Reader Discovery Pass — SCAN-01/02)** runs first and **gates the fix scope**. It produces a triaged, severity-ranked findings artifact; each finding marked fold-into-fix-phase (with target) or parked (with rationale). Has a findings checkpoint (autonomous:false appropriate); no production code lands here. Folded-in findings inform Phases 111-112 before they are planned in detail.
- **Phase 111 (Config-Set Endpoint Migration — CFG-01..04)** is the one breaking HTTP-contract change: `/server/config/set` GET→POST hard cutover (JSON body), legacy GET path fully removed. Spans backend (`web/handler/config.py`), Angular (`services/settings/config.service.ts`), and E2E (`src/e2e/tests/settings.page.ts`, `src/docker/test/e2e/configure/setup_seedsyncarr.sh`). On-disk config format is unchanged (CFG-04). Isolated so it can be walked through carefully.
- **Phase 112 (Defensive Guards & Code Hardening — GUARD-01..06)** clusters the independent small fixes: non-loopback-without-token + webhook-without-secret startup warnings, logged delete-path failures (replace `ignore_errors=True`), `.gitignore` for run artifacts, legacy `~/.seedsync` fallback warning, and the AppProcess spawn-context fix. GUARD-04 has a concrete bar: `test_app_process.py::test_process_with_long_running_thread_terminates_properly` must go green with no test deleted/skipped, by creating AppProcess's `Queue()`/`Event()` from a spawn-compatible context (same fix pattern as the shipped INFRA-01 MP-logger fix). Independent of Phase 111.
- **Phase 113 (Presentation & Launch Readiness — LAUNCH-01..06)** is the presentation track, sequenced last (independent of code phases; reflects the hardened code from 111-112 so README/SECURITY.md claims are accurate). Cynical-reader teardown + codex pass → README / SECURITY.md / community-health / release-notes. LAUNCH-03 screenshots are captured at the milestone-end walkthrough against the NAS-deployed branch build, NOT during phase execution. Repo-metadata application (part of LAUNCH-06) + the actual git push/publish are manual maintainer actions outside phase execution.

**Dependency edges:** 110 → 111, 110 → 112 (both fix phases gated on findings dispositions; 111 and 112 are mutually independent), 112 → 113 (presentation sequenced last).

**CI gates every code phase (110-112) must hold:** Python `fail_under` ≥ 88; Angular Karma `check.global` floors stmts/branches/fns/lines 83/68/79/83; full suite green on amd64 + arm64. No release/tag/version work inside any phase.

**Branch-isolated workflow:** branch `launch-hardening`; NAS walkthrough on the branch; merge + single `v1.4.0` tag only after CI green + maintainer sign-off — a milestone-end orchestrator/maintainer action, NOT a roadmap phase.

### Phase 110 Decisions (2026-06-02)

- **GUARD-02 warning-correctness gap confirmed:** `empty webhook_secret + require_secret=True` fires first startup warning saying "accept any caller" while the handler actually returns 503 (fail-closed). Phase 112 must fix warning text accuracy, not just prominence.
- **pip CVEs PARK grounded in image inspection:** Shipped runtime image uses `pip 24.0` (`python:3.11-slim` base), NOT the flagged `pip 26.0.1` (local dev venv). CVE range is `>= 26.0.x < 26.1` — pip 24.0 is NOT affected. PARK is evidence-based.
- **npm CVEs PARK grounded in Dockerfile evidence:** `Dockerfile:123` copies only `/build/dist/browser` into runtime. `node_modules/` devDeps (`karma`, `eslint`, `ws`, `brace-expansion`) are build-stage-only. PARK is evidence-based.
- **GUARD-01/02 characterized as confirm-the-gap:** Both warnings already exist in `seedsyncarr.py:374-393` with tests. Phase 112 gap is prominence + GUARD-02 correctness, not build-from-scratch.

### Pending Todos

None. GUARD-04 (AppProcess spawn fix) is now in scope (Phase 112) — clears the Tech Debt item below.

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260528-khw | triage and merge dependabot PRs, resolve open security alert | 2026-05-28 | 22616f9 | [260528-khw-triage-and-merge-dependabot-prs-resolve-](./quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/) |

## Deferred Items

| Category | Item | Status |
|----------|------|--------|
| todo | webob-cgi-upstream-unblock | testing (upstream — blocked on webob 2.0; DEFER-WEBOB) |
| todo | shutdown-readiness-event | robustness (DEFER-SHUTDOWN — invisible to launch reader; deferred v1.4.0) |
| todo | streamqueue-atomic-drop-oldest | robustness (DEFER-STREAMQUEUE — latent, well-mitigated; deferred v1.4.0) |
| todo | test-hardening-backlog A-01..A-06 | test-infra (DEFER-TESTHARDEN — invisible to launch reader; deferred v1.4.0) |

> Note: `migrate-config-set-to-post-body` (previously deferred) is now IN SCOPE as Phase 111 (CFG-01..04). Removed from deferred list.

## Tech Debt

- Bootstrap 5.3 still uses @import internally (blocked until Bootstrap 6)
- ~~`AppProcess` spawn-unpicklable~~ — now IN SCOPE as GUARD-04 (Phase 112). `AppProcess.__init__` creates `self.__exception_queue = Queue()` + `self._terminate = Event()` from the default (fork) context; under `spawn`, `AppProcess.start()` pickles the instance and raises `TypeError: cannot pickle '_thread.lock' object`. Fix = migrate those two fields to a spawn-compatible context (same pattern as the shipped INFRA-01 MP-logger fix). Pre-existing failing test: `test_app_process.py::test_process_with_long_running_thread_terminates_properly`. See `.planning/milestones/v1.3.0-phases/107-mp-logger-spawn-safety/deferred-items.md`.

## Milestones Shipped

| Milestone | Phases/Slices | Date |
|-----------|---------------|------|
| v1.0-v1.6 | Phases 1-21 | 2026-02-03 to 2026-02-10 |
| v1.7-v2.0.1 | Phases 22-32 | 2026-02-10 to 2026-02-14 |
| v3.0-v3.2 | Phases 33-51 | 2026-02-17 to 2026-03-22 |
| M001-M010 | 29 slices | 2026-03-21 to 2026-03-28 |
| v4.0.3 | Phase 52 | 2026-04-08 |
| v1.0.0 Rebrand | Phases 53-61 | 2026-04-08 to 2026-04-13 |
| v1.1.0 UI Redesign | Phases 62-74 (71 dropped) | 2026-04-13 to 2026-04-19 |
| v1.1.1 Post-Redesign Cleanup | Phases 75-82 | 2026-04-19 to 2026-04-23 |
| v1.1.2 Test Suite Audit | Phases 83-86 | 2026-04-24 |
| v1.2.0 Test & Quality Hardening | Phases 87-96 | 2026-04-24 to 2026-04-28 |
| v1.3.0 Slice 1 (Test Coverage Gaps) | Phases 97-100 | 2026-05-28 to 2026-05-31 |
| v1.3.0 Slice 2 (Known Bugs + Security) | Phases 101-103 | 2026-05-31 to 2026-06-01 |
| v1.3.0 Slice 3 (Frontend Deps + Dead Code) | Phases 104-106 | 2026-06-01 |
| v1.3.0 Slice 4 (Backend Arch Refactor + Test Infra) | Phases 107-109 | 2026-06-01 to 2026-06-02 (v1.3.0 tag cut) |

## Session Continuity

Last session: 2026-06-02T22:02:42.523Z
Stopped at: Phase 112 context gathered
Next action: Plan Phase 110 (Hostile-Reader Discovery Pass) with `/gsd:plan-phase 110` (or discuss first with `/gsd:discuss-phase 110`)

## Operator Next Steps

- Cut branch `launch-hardening` from `main` (v1.3.0) before starting Phase 110 code work.
- Plan and execute Phase 110 (SCAN) first — its findings dispositions gate the detailed planning of Phases 111-112.
- Run phases one-at-a-time per the orchestrator run cadence; stop between for review.
