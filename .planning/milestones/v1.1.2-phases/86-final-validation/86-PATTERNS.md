# Phase 86: Final Validation - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 2 (1 source file modified + 1 planning doc modified)
**Analogs found:** 2 / 2

---

## File Classification

Phase 86 is a pure validation and documentation phase. Two files are modified:

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/docker/test/e2e/configure/setup_seedsyncarr.sh` | config (harness setup) | request-response (curl config calls) | Itself — extend the existing curl block | exact (self-extension) |
| `.planning/ROADMAP.md` | documentation | batch (milestone notes) | `.planning/phases/85-e2e-test-audit/85-01-SUMMARY.md` + prior milestone sections in ROADMAP.md | role-match |

---

## Pattern Assignments

### `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (config, harness setup, request-response)

**Analog:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (self — extend existing curl block)

**Current file — full content** (lines 1-20):
```bash
#!/bin/bash
# Force rebuild: 2026-01-21-v2
./wait-for-it.sh myapp:8800 -t 60 -- echo "Seedsync app is up (before configuring)"
curl -sS "http://myapp:8800/server/config/set/general/debug/true"; echo
curl -sS "http://myapp:8800/server/config/set/general/verbose/true"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/local_path/%252Fdownloads"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/remote_address/remote"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/remote_username/remoteuser"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/remote_password/remotepass"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/remote_port/1234"; echo
curl -sS "http://myapp:8800/server/config/set/lftp/remote_path/%252Fhome%252Fremoteuser%252Ffiles"; echo
curl -sS "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo

curl -sS -X POST "http://myapp:8800/server/command/restart"; echo

./wait-for-it.sh myapp:8800 -t 60 -- echo "Seedsync app is up (after configuring)"

echo
echo "Done configuring SeedSyncarr app"
```

**Core pattern:** Each configuration value is set via a `curl -sS` GET to
`/server/config/set/<section>/<key>/<value>` followed by `; echo` to flush
the output. All config calls come before the restart call.

**The fix to apply** (insert at line 13, immediately after `patterns_only` line, before the blank line):
```bash
curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo
```

**Resulting corrected config block** (lines 12-14 after edit):
```bash
curl -sS "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo
curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo

curl -sS -X POST "http://myapp:8800/server/command/restart"; echo
```

**Why this is needed:** `autoqueueEnabled` is initialized to `null` in the Python config
(`Config.AutoQueue.__init__` uses `Checkers.null`). The Angular component
`settings-page.component.ts` reads it and uses it in an `@if (autoqueueEnabled && patternsOnly)`
guard at settings-page.component.html line 206. Without `enabled=true`, the `.pattern-section`
block is hidden and `autoqueue.page.ts navigateTo()` times out waiting for `.pattern-section`
with `state: 'visible'`.

**Validation command after edit:**
```bash
grep "autoqueue" src/docker/test/e2e/configure/setup_seedsyncarr.sh
# Expected output — both lines present:
# curl -sS "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo
# curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo
```

---

### `.planning/ROADMAP.md` (documentation, milestone notes, batch)

**Analog:** The existing v1.1.1 milestone section in `.planning/ROADMAP.md` lines 258-265 and the
Phase 83-85 phase detail sections (lines 269-306).

**Current milestone entry** (lines 258-265):
```markdown
### v1.1.2 Test Suite Audit (Phases 83-86) - IN PROGRESS

**Milestone Goal:** Identify and remove stale, redundant, or dead-path tests inherited from the
original SeedSync repo — lean the test suite to only test current behavior.

- [x] **Phase 83: Python Test Audit** - Identify and remove stale Python backend tests (completed 2026-04-24)
- [x] **Phase 84: Angular Test Audit** - Identify and remove stale Angular unit tests (completed 2026-04-24)
- [x] **Phase 85: E2E Test Audit** - Identify and remove redundant Playwright specs (completed 2026-04-24)
- [ ] **Phase 86: Final Validation** - Full CI green and coverage baseline documented
```

**Pattern for milestone completion — line 32 and line 258 must be updated:**

Line 32 (milestones list at top of file):
```markdown
# Before:
- v1.1.2 Test Suite Audit - Phases 83-86 (in progress)

# After:
- v1.1.2 Test Suite Audit - Phases 83-86 (shipped YYYY-MM-DD)
```

Line 258 (milestone section header):
```markdown
# Before:
### v1.1.2 Test Suite Audit (Phases 83-86) - IN PROGRESS

# After:
### v1.1.2 Test Suite Audit (Phases 83-86) - SHIPPED YYYY-MM-DD
```

Line 265 (Phase 86 checkbox):
```markdown
# Before:
- [ ] **Phase 86: Final Validation** - Full CI green and coverage baseline documented

# After:
- [x] **Phase 86: Final Validation** - Full CI green and coverage baseline documented (completed YYYY-MM-DD)
```

**Coverage Baseline subsection to add** (after the Phase 86 checkbox in the milestone block,
following the D-03 mandate for milestone notes with no standalone file):
```markdown
**Coverage Baseline (Python):**
| Metric | Before Audit (Phase 83) | After Audit (Phase 86) |
|--------|------------------------|------------------------|
| Total coverage | 85.05% | XX.XX% |
| fail_under threshold | 84% | 84% |
| Safety margin | 1.05pp | X.XXpp |

**Coverage Baseline (Angular) — Phase 84:**
| Metric | Value |
|--------|-------|
| Statements | 83.34% (1682/2018) |
| Branches | 69.01% (461/668) |
| Functions | 79.73% (421/528) |
| Lines | 84.21% (1622/1926) |

**Known Caveats:**
- 2 arm64 E2E specs fail due to pre-existing locale-dependent Unicode sort order (glibc amd64 vs arm64
  difference). Not introduced by the audit. Tracked for future resolution (see D-07/D-08).
```

**Progress table row to update** (lines 351-354):
```markdown
# Before:
| 86. Final Validation | v1.1.2 | 0/TBD | Not started | - |

# After:
| 86. Final Validation | v1.1.2 | 1/1 | Complete    | YYYY-MM-DD |
```

**Phase 86 detail section to update** (lines 308-319):
```markdown
### Phase 86: Final Validation
**Goal**: All three test layers are green end-to-end in CI and the post-audit coverage baseline is recorded
**Depends on**: Phase 85
**Requirements**: VAL-01, VAL-02
...
**Plans:** 1/1 plans complete
Plans:
- [x] 86-01-PLAN.md — Push documentation commit, confirm CI green, record coverage baseline
```

**Prior milestone completion pattern for reference** (v1.1.1, lines near 250-256 — use as formatting guide):
The pattern is: header changes from `- IN PROGRESS` to `- SHIPPED YYYY-MM-DD`, the top-level
milestone list line changes from `(in progress)` to `(shipped YYYY-MM-DD)`, and the phase
checkboxes use `[x]` with a `(completed YYYY-MM-DD)` suffix.

---

## Shared Patterns

### curl Config Call Pattern
**Source:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh` lines 4-12
**Apply to:** The `autoqueue/enabled/true` addition in this same file
```bash
curl -sS "http://myapp:8800/server/config/set/<section>/<key>/<value>"; echo
```
Convention: always `curl -sS`, always `; echo` suffix, always use URL-encoded values where needed.
All config sets come before the restart `curl -X POST`.

### ROADMAP.md Milestone Completion Pattern
**Source:** `.planning/ROADMAP.md` lines 3-32 (milestones list) and prior shipped milestone sections
**Apply to:** The v1.1.2 milestone section on completion
- Top-level milestones list: `(in progress)` → `(shipped YYYY-MM-DD)`
- Milestone section header: `- IN PROGRESS` → `- SHIPPED YYYY-MM-DD`
- Phase checkbox: `- [ ]` → `- [x]` with `(completed YYYY-MM-DD)` suffix
- Progress table: `Not started | -` → `Complete | YYYY-MM-DD`

### Two-Wave Commit Strategy
**Source:** D-02 decision + RESEARCH.md "Recommended Commit Structure"
**Apply to:** All plan commit tasks in this phase

Wave 1 — push to trigger CI arm64 (arm64 only runs on main push, not PRs):
```
commit: docs/config: fix autoqueue harness + Phase 86 planning artifacts
files: setup_seedsyncarr.sh, 86-01-PLAN.md, 86-PATTERNS.md, [RESEARCH already committed]
```

Wave 2 — update ROADMAP.md with actual CI coverage number:
```
commit: docs(86): complete v1.1.2 milestone — CI green, coverage baseline recorded
files: ROADMAP.md, 86-01-SUMMARY.md, 86-VERIFICATION.md
```

---

## No Analog Found

None — both files have clear analogs (self-extension for setup_seedsyncarr.sh; prior milestone
entries for ROADMAP.md). No new file types are introduced in this phase.

---

## Key Findings for Planner

| Finding | Implication for Plan |
|---------|---------------------|
| `autoqueue/enabled/true` missing from setup_seedsyncarr.sh | Task 1 of Plan 01 must add this curl line BEFORE the first CI push; without it, autoqueue.page.spec.ts will time out on `.pattern-section` visibility |
| arm64 E2E only triggers on push to main (not PRs) | Plan must push directly to main (not a PR) for VAL-01 to be satisfied; D-01 mandates this |
| "After" Python coverage number is only available from CI logs | Plan must explicitly instruct executor to read the `unittests-python` job log after CI completes; it cannot be pre-computed |
| 2 arm64 sort failures are pre-existing (Phase 85 UAT documented) | VAL-01 satisfied with caveat per D-07; if arm64 shows exactly 2 failures in `dashboard.page.spec.ts`, document and proceed; if more than 2, investigate before closing |
| ROADMAP.md needs two distinct updates | Wave 1: add coverage placeholder; Wave 2: fill in actual "after" number once CI logs are read |
| D-08 requires a todo item for the arm64 sort issue | Plan must create a tracked todo item for the locale-dependent Unicode sort failures |

---

## Metadata

**Analog search scope:** `src/docker/test/e2e/configure/`, `.planning/`
**Files scanned:** 8 (setup_seedsyncarr.sh, ROADMAP.md, 85-01-PLAN.md, 85-01-SUMMARY.md, 85-PATTERNS.md, 83-01-SUMMARY.md, 85-VERIFICATION.md, 86-CONTEXT.md + 86-RESEARCH.md)
**Pattern extraction date:** 2026-04-24
