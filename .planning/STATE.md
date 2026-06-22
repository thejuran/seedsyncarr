---
gsd_state_version: 1.0
milestone: v1.4.1
milestone_name: Scanner Auto-Recovery
status: Awaiting next milestone
stopped_at: "Completed 115-01 + follow-on piscina override PR #67 — alert #37 closed, 0 open Dependabot alerts, DEPS-01 fully met"
last_updated: "2026-06-22T16:22:40.555Z"
last_activity: 2026-06-22 — Milestone v1.4.1 completed and archived
progress:
  total_phases: 15
  completed_phases: 2
  total_plans: 3
  completed_plans: 3
  percent: 13
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-21)

**Core value:** Reliable file sync from seedbox to local with automated media library integration
**Current focus:** Phase 115 — dependency-security-maintenance

## Current Position

Phase: Milestone v1.4.1 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-06-22 — Milestone v1.4.1 completed and archived

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Roadmap shape (v1.4.1): **two phases**. Phase 114 (Scanner Auto-Recovery), derived from the 4 scanner/controller requirements (SCAN-01, SCAN-02, SCAN-03, RECOV-01) — one coherent change to the same controller/scanner error-handling path (transient-error reclassification + bounded retry + surface-on-exhaustion + controller auto-restart); over-decomposition explicitly avoided, a tightly-scoped regression fix. Phase 115 (Dependency & Security Maintenance), derived from DEPS-01/DEPS-02 — a disjoint dependency/security-maintenance track (clear the 8 open Dependabot security alerts + merge the 7 open Dependabot PRs, each gated on CI green). The two are separate phases because their verification differs: a code-path regression fix (114) vs. CI-green-per-merge mechanical dependency maintenance with 0 open alerts after (115). **Current position is unchanged — Phase 114 is still the next phase to plan;** Phase 115 was appended after 114, not inserted before it.

- **Phase 114 (Scanner Auto-Recovery — SCAN-01/02/03, RECOV-01)** wires together infrastructure that **already exists** in `src/python/` — no new mechanisms:
  - `sshcp.py` — `PERMANENT_ERROR_PATTERNS`, `TRANSIENT_ERROR_PATTERNS`, `_is_transient_ssh_error`
  - `remote_scanner.py` — `scan()` recoverable classification, `_is_permanent_ssh_error`, `first_run` strictness
  - `scanner_process.py` — `ScannerError` recoverable flag
  - `scan_manager.py` — `propagate_exceptions` / `_check_process_health` / `ScannerProcessDiedError`
  - `seedsyncarr.py` `run()` `AppError` catch (~lines 182-190), gated on `args.exit`
  - `common/error.py` — `ServiceRestart` (~lines 14-18)
- **SCAN-01** (reclassify transient name-resolution failures: `Could not resolve hostname` / `Name or service not known` / momentary `Bad hostname` → recoverable so the scan retries instead of dying) and **SCAN-02** (bounded backoff — capped attempts, never infinite) are the recovery half.
- **SCAN-03** (retries exhausted → surface to the user exactly as today: controller reports failure / `server.up=False` with the error message) is the safety half — the retry path must never silently mask a real permanent config error.
- **RECOV-01** (permanent-class controller death → auto-restart via the existing `ServiceRestart` path instead of staying down; recovery itself bounded so an unrecoverable condition doesn't become a restart loop) is the controller-level safety net.

- **Phase 115 (Dependency & Security Maintenance — DEPS-01, DEPS-02)** is the dependency/security-maintenance track, disjoint from Phase 114's code path (manifests/lockfiles vs. `src/python/`):
  - **DEPS-01** — clear all **8** open Dependabot security alerts: 3 HIGH (`hono` CORS-credentials reflection → 4.12.25, `piscina` prototype-pollution→RCE → 5.2.0, `undici` TLS-cert-validation bypass → 7.28.0) + 5 MEDIUM (4× `hono`, 1× `undici` cross-user info disclosure). All are remediated by the open PRs.
  - **DEPS-02** — merge all **7** open Dependabot PRs, each gated on CI green: #60 pyinstaller, #61 ruff, #62 testfixtures, #63 pytest (Python dev-deps); #64 npm_and_yarn group (18 updates, incl. `piscina`); #65 hono; #66 undici (JS). Decision (2026-06-21): merge **all 7** for a full cleanup.
  - Watch-outs: #64 (18-update npm group) must not regress the Angular build or Karma/Playwright gates; #61 bumps `ruff` itself and CI runs `ruff check src/python/` as a **separate gate from pytest**, so verify ruff whole-tree with the new version. No release/tag/version work in-phase.

**Root cause (incident 2026-06-19, debug session `seedbox-files-not-showing`; prior variant `hold-the-dream-not-syncing`):** A transient DNS failure resolving `moon.usbx.me` raised `SshcpError('Bad hostname')`, classified as permanent/non-recoverable; it propagated to `seedsyncarr.py run()` (caught as `AppError` with `args.exit=False`), marking the controller down **without** restarting it. The web server stayed up so the UI looked fine, but the file list was frozen ~2 days until a manual container restart.

**CI gate:** Python full suite green AND `ruff check src/python/` clean. CI runs `ruff check src/python/` as a **separate gate from pytest** — build-verify must run ruff whole-tree (not just the touched files), not only the test suite. No release/tag/version work happens inside the phase.

**Dependency edges:** Phase 114 depends on Phase 113 (v1.4.0 shipped on `main`). No intra-milestone edges (single phase).

- [Phase ?]: Phase 115: merged all 7 Dependabot PRs #60-#66 SHA-pinned via --match-head-commit in locked order #64->#65->#66->#60->#61->#62->#63; cleared 7 of 8 alerts (2/3 HIGH + all 5 MEDIUM); whole-tree ruff 0.15.17 clean. Follow-on: piscina HIGH #37 (transitive pin via @angular/build) closed via npm override `piscina >=5.2.0` in PR #67 — CI-gated (Angular build/Karma/E2E all green), SHA-pin-merged to main (39133ff), alert #37 auto-closed. **8 of 8 alerts cleared, 0 open; DEPS-01 fully met.**

### Phase 110 Decisions (2026-06-02)

- **GUARD-02 warning-correctness gap confirmed:** `empty webhook_secret + require_secret=True` fires first startup warning saying "accept any caller" while the handler actually returns 503 (fail-closed). Phase 112 fixed warning text accuracy (v1.4.0).
- **pip CVEs PARK grounded in image inspection:** Shipped runtime image uses `pip 24.0` (`python:3.11-slim` base), NOT the flagged `pip 26.0.1` (local dev venv). CVE range is `>= 26.0.x < 26.1` — pip 24.0 is NOT affected. PARK is evidence-based.
- **npm CVEs PARK grounded in Dockerfile evidence:** `Dockerfile:123` copies only `/build/dist/browser` into runtime. `node_modules/` devDeps (`karma`, `eslint`, `ws`, `brace-expansion`) are build-stage-only. PARK is evidence-based.

### Pending Todos

None.

### Blockers/Concerns

- None. (RESOLVED 2026-06-22) Dependabot alert #37 (piscina HIGH RCE, GHSA-x9g3-xrwr-cwfg) is CLOSED: npm override `piscina >=5.2.0` added to `src/angular/package.json` lifted the transitively-pinned 5.1.4 to patched 5.2.0; PR #67 CI-gated (Angular build/Karma/E2E all green — the @angular/build pin tolerated 5.2.0), SHA-pin-merged to main (39133ff). Alert #37 auto-closed (state `fixed`); 0 open Dependabot alerts.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260528-khw | triage and merge dependabot PRs, resolve open security alert | 2026-05-28 | 22616f9 | [260528-khw-triage-and-merge-dependabot-prs-resolve-](./quick/260528-khw-triage-and-merge-dependabot-prs-resolve-/) |
| 260604-g9c | Handle open Dependabot PRs and alerts: merge webob+ruff (security alert resolved); Angular v22 PR #50 istanbul fix pushed (TS migration completed in 260604-gmy) | 2026-06-04 | 957a896 | [260604-g9c-handle-open-dependabot-prs-and-alerts-me](./quick/260604-g9c-handle-open-dependabot-prs-and-alerts-me/) |
| 260604-gmy | Fix Angular v22 strict-template TS errors (TS2532/TS2339/TS2345/TS2322) and merge Dependabot PR #50 — all Dependabot PRs now cleared, 0 open alerts | 2026-06-04 | ac087a5 | [260604-gmy-fix-angular-v22-typescript-template-type](./quick/260604-gmy-fix-angular-v22-typescript-template-type/) |

## Deferred Items

| Category | Item | Status |
|----------|------|--------|
| todo | webob-cgi-upstream-unblock | testing (upstream — blocked on webob 2.0; DEFER-WEBOB) |
| todo | shutdown-readiness-event | robustness (DEFER-SHUTDOWN — invisible to launch reader; deferred v1.4.0) |
| todo | streamqueue-atomic-drop-oldest | robustness (DEFER-STREAMQUEUE — latent, well-mitigated; deferred v1.4.0) |
| todo | test-hardening-backlog A-01..A-06 | test-infra (DEFER-TESTHARDEN — deferred v1.4.0) |
| quick_task | 260528-khw-triage-and-merge-dependabot-prs | housekeeping (prior session, SUMMARY missing; acknowledged + deferred at v1.4.0 close) |

> Acknowledged + deferred at v1.4.0 milestone close (2026-06-03): webob-cgi-upstream-unblock (still blocked on upstream webob 2.0) and the 260528-khw dependabot quick-task (prior-session housekeeping).

## Tech Debt

- Bootstrap 5.3 still uses @import internally (blocked until Bootstrap 6)

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
| v1.4.0 Launch-Hardening for Public Release | Phases 110-113 | 2026-06-02 to 2026-06-03 (v1.4.0 tag cut) |

## Session Continuity

Last session: 2026-06-22T16:01:00.000Z
Stopped at: Completed 115-01 + follow-on piscina override PR #67 — alert #37 closed, 0 open Dependabot alerts, DEPS-01 fully met
Next action: Phase 115 is complete (DEPS-01 + DEPS-02 met, 0 open alerts). Run the Phase 115 verifier when ready, then proceed toward the v1.4.1 milestone close.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
