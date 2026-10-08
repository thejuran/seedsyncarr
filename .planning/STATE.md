---
gsd_state_version: 1.0
milestone: v1.7.4
milestone_name: Safety Patch
status: executing
stopped_at: Phase 116 context gathered
last_updated: "2026-10-08T22:53:25.693Z"
last_activity: 2026-10-08 -- Phase 116 execution started
progress:
  total_phases: 19
  completed_phases: 2
  total_plans: 6
  completed_plans: 4
  percent: 11
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-08)

**Core value:** Reliable file sync from seedbox to local with automated media library integration
**Current focus:** Phase 116 — Import Safety

## Current Position

Phase: 116 (Import Safety) — EXECUTING
Plan: 1 of 3
Status: Executing Phase 116
Last activity: 2026-10-08 -- Phase 116 execution started

Progress: [░░░░░░░░░░] 0% (0/3 phases)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**Roadmap shape (v1.7.4): three phases, owner-approved split from the design spec (`docs/superpowers/specs/2026-10-08-safety-patch-design.md`), ordered by risk — deletion safety first.** Numbering continues from v1.4.1's last phase (115). All three are Python-only, behavior-narrowing fixes with no on-disk format change and no UI work. Sequenced 116→117→118 but they touch disjoint code paths; per the spec, Phase 116 may ship alone as 1.7.4 if 117/118 slip, otherwise all three ship as one patch.

- **Phase 116 (Import Safety — IMPORT-01, IMPORT-02):** `Controller.__check_webhook_imports` (`src/python/controller/controller.py`) builds `name_to_root` last-writer-wins. Fix: keep every distinct model path per lowercased basename; exactly one distinct path → today's behavior; two or more → **reject** (no `imported_file_names` entry, no `add_imported_child` record, no badge, no auto-delete timer, one CWE-117-sanitized warning naming the candidate roots). Ambiguity applies across releases and within one release; repeated references to the same path are deduplicated (not ambiguous). Path-mapping redesign is explicitly out of scope — conservative rejection only.
- **Phase 117 (Transfer-State Safety — XFER-01..05):** three fixes on the LFTP status → model → auto-queue path. **B1** `PgetJobParser.parse_header` pops the next line only when it matches `CHUNK_AT`/`CHUNK_AT2`/`CHUNK_GOT`; audit the other next-line-consuming sites (`CHUNK_HEADER`, mirror-empty). **B2** unparseable status → *unavailable* (`None` at the `LftpManager.status()` contract), never `[]`; keep `MAX_CONSECUTIVE_STATUS_ERRORS` counter/escalation exactly as is; verify `ModelPipeline`, `ModelBuilder`, `Controller._update_active_file_tracking`, auto-queue, auto-delete never convert `None` back into empty; genuine empty still clears active state. **B3** remote and local stability measured only on the clock of successful scans; the UI "last scan" field keeps its meaning (a separate successful-scan time is the allowed implementation).
- **Phase 118 (Durable State — PERSIST-01, PERSIST-02, REL-01):** `Persist.to_file` (`src/python/common/persist.py`, sole writer for `settings.cfg`, controller persist, auto-queue persist) truncates in place. Fix contained to that function: serialize first → `0600` temp in the target dir → write/flush/fsync → `os.replace` (**commit point**) → best-effort directory fsync (logged, not raised). Failure contract: any failure before/during the replace leaves the original byte-for-byte intact, removes the temp, raises; after the replace the new file is committed. No migration, no backup system, no load-side change. **REL-01 (release gate) is mapped here** because it is the milestone's final phase: regressions fail-before/pass-after, full suite + ruff, release-image smoke test (startup, transfer status, settings persistence, restart), `:1.7.4` NAS deploy with startup + config loading verified and scanner recovery confirmed by a subsequent successful scan.

**CI gate (every phase):** full Python suite green AND `ruff check src/python/` clean whole-tree — CI runs ruff as a **separate gate from pytest**, so build-verify must run ruff on the whole tree, not just touched files. Python `fail_under` ≥ 88 holds. Each targeted regression must be shown to fail against old behavior before its fix (REL-01 gate 1) — plan tasks should run the new test red first.

**Dependency edges:** 116 → Phase 115 (last GSD phase; `main` currently at release 1.7.3). 117 → 116 and 118 → 117 are sequencing only (disjoint code paths); 118's REL-01 gate requires 116 and 117 complete.

### Phase 110 Decisions (2026-06-02)

- **GUARD-02 warning-correctness gap confirmed:** `empty webhook_secret + require_secret=True` fires first startup warning saying "accept any caller" while the handler actually returns 503 (fail-closed). Phase 112 fixed warning text accuracy (v1.4.0).
- **pip CVEs PARK grounded in image inspection:** Shipped runtime image uses `pip 24.0` (`python:3.11-slim` base), NOT the flagged `pip 26.0.1` (local dev venv). CVE range is `>= 26.0.x < 26.1` — pip 24.0 is NOT affected. PARK is evidence-based.
- **npm CVEs PARK grounded in Dockerfile evidence:** `Dockerfile:123` copies only `/build/dist/browser` into runtime. `node_modules/` devDeps (`karma`, `eslint`, `ws`, `brace-expansion`) are build-stage-only. PARK is evidence-based.

### Pending Todos

None.

### Blockers/Concerns

- None at roadmap creation. Watch-out for Phase 118's deploy gate: NAS local-build is blocked by the QEMU limitation (deploy-environment, not a code defect) — deploy the CI-published multi-arch `:1.7.4` tag, never a local build and never `:dev`.

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
| backlog | 999.1 webhook import evidence (payload size == remote size) | v2 requirement IMPORT-F1; defense in depth, not in v1.7.4 scope |

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
| v1.4.1 Scanner Auto-Recovery | Phases 114-115 | 2026-06-19 to 2026-06-22 (tagged v1.5.0) |

## Session Continuity

Last session: 2026-10-08T22:18:12.726Z
Stopped at: Phase 116 context gathered
Next action: Plan Phase 116 (Import Safety) — `/bm:plan-phase 116`

## Operator Next Steps

- `/bm:plan-phase 116` — Import Safety (IMPORT-01, IMPORT-02); design spec Phase A is the planning source
