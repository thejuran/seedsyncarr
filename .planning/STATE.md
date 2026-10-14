---
gsd_state_version: 1.0
milestone: v1.7.5
milestone_name: Safety Release
status: Defining requirements
stopped_at: Phase 119 context gathered
last_updated: "2026-10-14T21:36:37.863Z"
last_activity: 2026-10-14 — Milestone v1.7.5 started
progress:
  total_phases: 22
  completed_phases: 5
  total_plans: 31
  completed_plans: 19
  percent: 23
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** Reliable file sync from seedbox to local with automated media library integration
**Current focus:** Milestone v1.7.5 Safety Release — Phase 119 (sole phase); Reliability follows at Phase 120

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-10-14 — Milestone v1.7.5 started

## Accumulated Context

### Roadmap Evolution

- 2026-10-14: Milestone v1.7.5 Safety Release started (owner decision): 1.7.5 is its own milestone with Phase 119 as sole phase; Reliability becomes the next milestone at Phase 120. Milestone-start phase-dir cleanup skipped by owner (keep 119 and backlog 999.1–999.3; archive completed phases selectively later).
- 2026-10-14: Expanded Phase 119 (owner-approved) with two Done-group incident fixes, each with separate plans and tests: (4) prevent incomplete-file imports — size/mtime are supporting evidence only, reliable arr-queue release identification, absence from queue is not completion, arr unavailable → visible hold/retry never unsafe copy, unverified copy unavailable for import until checks pass; (5) persist per-episode import credit for complete episodes while siblings transfer, whole-folder delete still gated on completion + full video coverage, restart recovery tested, ambiguous-filename protections retained. Diagnosis: `.planning/debug/done-group-no-auto-delete.md`. 999.1 stays separate.
- 2026-10-09: Added Phase 119, Safety Follow-ups and 1.7.5 Release, as the opening phase of the next Reliability milestone. Promotes 999.2 and 999.3 and includes the PyPI packaging repair. Release 1.7.5 before executing later reliability phases; no separate patch milestone. Detailed milestone initialization and plans remain pending.

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**Roadmap shape (v1.7.4): three phases, owner-approved split from the design spec (`docs/superpowers/specs/2026-10-08-safety-patch-design.md`), ordered by risk — deletion safety first.** Numbering continues from v1.4.1's last phase (115). All three are Python-only, behavior-narrowing fixes with no on-disk format change and no UI work. Sequenced 116→117→118 but they touch disjoint code paths; per the spec, Phase 116 may ship alone as 1.7.4 if 117/118 slip, otherwise all three ship as one patch.

- **Phase 116 (Import Safety — IMPORT-01, IMPORT-02):** `Controller.__check_webhook_imports` (`src/python/controller/controller.py`) builds `name_to_root` last-writer-wins. Fix: keep every distinct model path per lowercased basename; exactly one distinct path → today's behavior; two or more → **reject** (no `imported_file_names` entry, no `add_imported_child` record, no badge, no auto-delete timer, one CWE-117-sanitized warning naming the candidate roots). Ambiguity applies across releases and within one release; repeated references to the same path are deduplicated (not ambiguous). Path-mapping redesign is explicitly out of scope — conservative rejection only.
- **Phase 117 (Transfer-State Safety — XFER-01..05):** three fixes on the LFTP status → model → auto-queue path. **B1** `PgetJobParser.parse_header` pops the next line only when it matches `CHUNK_AT`/`CHUNK_AT2`/`CHUNK_GOT`; audit the other next-line-consuming sites (`CHUNK_HEADER`, mirror-empty). **B2** unparseable status → *unavailable* (`None` at the `LftpManager.status()` contract), never `[]`; keep `MAX_CONSECUTIVE_STATUS_ERRORS` counter/escalation exactly as is; verify `ModelPipeline`, `ModelBuilder`, `Controller._update_active_file_tracking`, auto-queue, auto-delete never convert `None` back into empty; genuine empty still clears active state. **B3** remote and local stability measured only on the clock of successful scans; the UI "last scan" field keeps its meaning (a separate successful-scan time is the allowed implementation).
- **Phase 118 (Durable State — PERSIST-01, PERSIST-02, REL-01):** `Persist.to_file` (`src/python/common/persist.py`, sole writer for `settings.cfg`, controller persist, auto-queue persist) truncates in place. Fix contained to that function: serialize first → `0600` temp in the target dir → write/flush/fsync → `os.replace` (**commit point**) → best-effort directory fsync (logged, not raised). Failure contract: any failure before/during the replace leaves the original byte-for-byte intact, removes the temp, raises; after the replace the new file is committed. No migration, no backup system, no load-side change. **REL-01 (release gate) is mapped here** because it is the milestone's final phase: regressions fail-before/pass-after, full suite + ruff, release-image smoke test (startup, transfer status, settings persistence, restart), `:1.7.4` NAS deploy with startup + config loading verified and scanner recovery confirmed by a subsequent successful scan.

**CI gate (every phase):** full Python suite green AND `ruff check src/python/` clean whole-tree — CI runs ruff as a **separate gate from pytest**, so build-verify must run ruff on the whole tree, not just touched files. Python `fail_under` ≥ 88 holds. Each targeted regression must be shown to fail against old behavior before its fix (REL-01 gate 1) — plan tasks should run the new test red first.

**Dependency edges:** 116 → Phase 115 (last GSD phase; `main` currently at release 1.7.3). 117 → 116 and 118 → 117 are sequencing only (disjoint code paths); 118's REL-01 gate requires 116 and 117 complete.

- [Phase 118]: 118-01: RED tests patch only global os.fsync/os.replace/tempfile.mkstemp so pre-fix failures are behavioral AssertionErrors; PERSIST-01/02 stay unchecked until 118-02 lands the fix
- [Phase 118]: Persist.to_file re-raises the original exception unwrapped (never PersistError) so caller handlers and ServiceExit keep working and save failures never trigger the load-side corrupt-file reset
- [Phase 118]: Host coverage 86.36% vs fail_under 88 is informational only (CI runs no --cov); surfaced at 118-04 checkpoint
- [Phase 118]: Owner (2026-10-09): 1.7.4 public release notes are plain English (stop, copy 3 files, upgrade; rollback sets [AutoDelete] enabled = False in restored settings.cfg); loader-based backup check lives only in 118-05
- [Phase 118]: Public rollback target is :1.7.2 (1.7.3 never published); owner confirms at 118-04
- [Phase 118]: 118-04: Owner approved 1.7.4 as drafted; (a)-(e) confirmed (rollback 1.7.2, CHANGELOG fold, coverage informational, wud semver filter in 118-05, inode-preserving compose edit)
- [Phase 118]: 118-04: Tag CI PyPI publish failed (./-prefixed archive paths, nothing uploaded); owner chose ship 1.7.4 via Docker/GitHub only, PyPI fix + Dependabot #93 in 1.7.5; tag not moved
- [Phase 118]: 118-05: owner go-ahead 'deploy keep pin'; NAS on :1.7.4@sha256:682d129d with compose digest pin kept and wud.tag.include semver filter; backup checker runs with --user 1026:100

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
| promoted | 999.2 LFTP command-stream resync after timeout | Phase 119; opening 1.7.5 patch |
| promoted | 999.3 auto-delete timer explicit submitted-unobserved guard | Phase 119; opening 1.7.5 patch |
| debug | extract-staging-autodel-rearm | awaiting_human_verify (fixes applied + self-verified 2026-09-16; acknowledged + deferred at v1.7.4 close) |

> Acknowledged + deferred at v1.7.4 milestone close (2026-10-09): debug session extract-staging-autodel-rearm and todo webob-cgi-upstream-unblock (both pre-existing, outside v1.7.4 scope).
>
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
| v1.7.4 Safety Patch | Phases 116-118 | 2026-10-08 to 2026-10-09 (tagged v1.7.4) |

## Session Continuity

Last session: 2026-10-14T20:14:42.325Z
Stopped at: Phase 119 context gathered
Next action: Discuss and plan Phase 119 (milestone orchestrator), then execute, verify and release 1.7.5.

## Operator Next Steps

- Discuss and plan Phase 119 (requirements XFER-06, DEL-01, IMP-01..03, REL-02, REL-03); verify Sonarr/Radarr queue/API completion semantics during planning.
- Implement, verify and release 1.7.5; then start the Reliability milestone at Phase 120.
