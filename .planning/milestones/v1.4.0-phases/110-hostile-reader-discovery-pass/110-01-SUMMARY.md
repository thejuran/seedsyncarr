---
phase: 110-hostile-reader-discovery-pass
plan: 01
subsystem: audit
tags: [security, audit, hostile-reader, findings, dispositions]
dependency_graph:
  requires: []
  provides: [110-FINDINGS.md]
  affects: [Phase 111 fix scope, Phase 112 fix scope, Phase 113 fix scope]
tech_stack:
  added: []
  patterns: [severity-ranked findings artifact, FOLD/PARK dispositions, runtime-image verification]
key_files:
  created:
    - .planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md
  modified: []
decisions:
  - pip 26.0.1 CVEs park: local dev venv only; shipped image uses pip 24.0 (python:3.11-slim); not in CVE range
  - npm CVEs park: devDependencies only (karma, eslint); verified not copied into seedsyncarr_run runtime image
  - GUARD-02 scope widened: warning-correctness gap added alongside prominence gap
  - HR-03 severity MEDIUM not LOW: misleading warning in one config state is a correctness issue, not cosmetic
metrics:
  duration: ~60 minutes
  completed: 2026-06-02
  tasks_completed: 2 of 3 (checkpoint reached at Task 3)
  files_created: 1 (110-FINDINGS.md)
---

# Phase 110 Plan 01: Hostile-Reader Discovery Pass Summary

**One-liner:** Bounded hostile-reader audit produced 9 triaged HR- findings (1 Critical config-set credential-leak, 1 High red test, 5 Medium/Low code gaps) with FOLD/PARK dispositions verified against runtime-image contents; clean Semgrep/ruff/gitleaks result recorded as launch-positive evidence.

## What Was Built

`110-FINDINGS.md` — a 215-line severity-ranked findings artifact answering "what would a skeptical r/selfhosted engineer flag?" Nine launch-visible HR- findings with explicit FOLD -> Phase 111/112/113 or PARK dispositions. These dispositions gate the detailed planning of Phases 111 (config-set migration), 112 (defensive guards), and 113 (presentation/launch).

## Finding Counts by Phase

| Target | Count | Items |
|--------|-------|-------|
| Phase 111 | 1 | HR-01 config-set credential-in-URL (CRITICAL) |
| Phase 112 | 5 | HR-02 red test (HIGH), HR-03 startup warning gap (MEDIUM), HR-04 delete-swallow (MEDIUM), HR-06 seedsync fallback (LOW), HR-07 gitignore (LOW) |
| Phase 113 | 1 | HR-05 LICENSE.txt rename (MEDIUM) |
| PARK | 2 | HR-08 npm CVEs (devDeps), HR-09 pip CVEs (dev venv) |

## Tool Results (Launch-Positive Evidence)

| Tool | Result | Notes |
|------|--------|-------|
| ruff (whole-tree) | 0 findings | Exact CI command `ruff check src/python/` |
| Semgrep (auto-rules) | 0 findings | 320 rules, 92 files |
| gitleaks | 0 leaks | 1,172 commits, 17.24 MB full history |
| pip-audit | 2 CVEs (pip binary) | Local dev venv pip 26.0.1; NOT in shipped image (pip 24.0) |
| npm audit | 4 moderate CVEs | devDeps only (karma→ws, eslint→brace-expansion); NOT in runtime image |
| AppProcess pytest | 1 FAILED | `test_process_with_long_running_thread_terminates_properly` — TypeError: cannot pickle '_thread.lock' object |

## Runtime-Image Verification Summary

**pip CVEs (HR-09 PARK):** Read-only inspection of `seedsyncarr/run/python/devenv:latest` confirms pip 24.0 in the shipped runtime image (`python:3.11-slim` base). The flagged pip 26.0.1 is in the local macOS Poetry virtualenv (Python 3.12). CVE range requires pip >= 26.0, so pip 24.0 is NOT affected. PARK is grounded in evidence, not assumption.

**npm CVEs (HR-08 PARK):** Dockerfile:123 `COPY --from=seedsyncarr_build_angular /build/dist/browser /app/html` — only the compiled SPA static output copies into the runtime image. `node_modules/` and all devDependencies (`karma`, `eslint`, `ws`, `brace-expansion`) are confined to the `seedsyncarr_build_angular_env` build stage. PARK is grounded in Dockerfile evidence.

## Key Decisions Made

1. **GUARD-02 scope widened** — Added warning-correctness dimension to the existing GUARD-02 gap. The matrix shows the `empty`+`require_secret=True` cell fires a first warning saying "accepts any caller" when the handler actually rejects all callers with 503. Phase 112 should fix this, not just improve prominence.

2. **GUARD-01/02 characterized as confirm-the-gap** — Both warnings already exist in `seedsyncarr.py:374-393` with tests. Phase 112 planning should verify the remaining gap (prominence + GUARD-02 correctness) rather than building from scratch.

3. **LICENSE characterized as rename** — `LICENSE.txt` exists with full Apache 2.0 content. The finding is about GitHub detection not recognizing `.txt` suffix, not about missing content.

4. **pip CVEs runtime-verified before parking** — Used `docker run --rm seedsyncarr/run/python/devenv:latest pip --version` (read-only) to confirm pip 24.0 in the shipped image, then parked with evidence citation per plan constraint.

## Deviations from Plan

None. Plan executed exactly as written. The research-predicted tool results matched actual runs. The runtime-image inspection confirmed the pip PARK (as the plan required before parking). No production code or config was modified. Working tree remained clean throughout (only 110-FINDINGS.md added).

## Checkpoint Status

**Task 3 reached.** Awaiting maintainer review of fold/park dispositions at the `checkpoint:human-verify` gate before these are treated as locked fix scope for Phases 111-113. See `110-FINDINGS.md` for the full artifact and the checkpoint message in the executor output for the review instructions.

## Self-Check

- [x] `110-FINDINGS.md` exists at phase directory: FOUND
- [x] Contains `## Summary` rollup
- [x] 9 HR- findings, all dispositioned (SCAN-02 OK: 9 headings, 15 disposition lines)
- [x] All 5 tool result lines present (ruff, semgrep, gitleaks, pip-audit, npm)
- [x] AppProcess red test result cited with exact error string
- [x] Runtime-image evidence cited for pip/npm parks
- [x] Working tree clean: only 110-FINDINGS.md added (no reports/ path)
- [x] Commit d235a42 exists

## Self-Check: PASSED
