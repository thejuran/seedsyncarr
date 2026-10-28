---
phase: 126
slug: release-1-8-0
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-10-28
---

# Phase 126 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Release-operations phase: most verification is CI and scripted live checks, not new unit tests. Source: 126-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python), Karma + Jasmine (Angular), Playwright (e2e), `node --test` (release metadata) |
| **Config file** | `src/python/pyproject.toml`, `src/angular/karma.conf.js`, `src/e2e/playwright.config.ts`, `scripts/verify-release-metadata.test.mjs` |
| **Quick run command** | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` (host exclusions: test_sshcp.py, test_scanner_process.py, test_scanner.py, test_extract_process.py) + `ruff check src/python/` |
| **Full suite command** | PR CI on the release branch (Dockerized unittests-python, unittests-angular, e2e, Docker build, CodeQL, packaging) |
| **Estimated runtime** | quick ~120 s; PR CI ~20–30 min |

---

## Sampling Rate

- **After every dependency-bump sub-task:** the touched ecosystem's targeted suite (Python quick run, or `make run-tests-angular` + `npm run lint`), so a failure maps to one bump (D-02)
- **After every plan wave:** release-branch push → full PR CI
- **Before `/bm:verify-work`:** PR CI fully green, `node scripts/verify-release-metadata.mjs 1.8.0` green, 0 open Dependabot alerts
- **Max feedback latency:** 120 s locally; CI as the wave gate

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| REL-05 | All open Dependabot PRs rolled in, 0 open alerts, 999.4 outcome recorded | scripted | `gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'` → `0`; `cd src/angular && npm audit --audit-level=low` | ✅ | ⬜ pending |
| REL-05 | Bumps break nothing | existing suites | Python quick run + whole-tree ruff + `make run-tests-angular` + `npm run lint` | ✅ | ⬜ pending |
| REL-05/06 | Version metadata consistent at 1.8.0 | existing script | `node scripts/verify-release-metadata.mjs 1.8.0` | ✅ | ⬜ pending |
| REL-06 | Release commit passes full CI | CI | `gh pr checks <release PR>` all green | ✅ | ⬜ pending |
| REL-06 | Tag publishes GHCR / GitHub release / PyPI | CI + scripted | `gh run view <tag run>`; `gh release view v1.8.0`; clean-venv `pip install seedsyncarr==1.8.0` | ✅ | ⬜ pending |
| REL-06 | Sandbox smoke on exact digest (incl. D-12a spot checks) | scripted live | 126 smoke sequence + `126-teardown.sh` (extends 125-teardown.sh with Radarr URL restore) | ❌ W-exec (created during execution) | ⬜ pending |
| REL-06 | Prod deploy by digest, successful scan, wud restored | scripted live + owner | 119.1-REL04 deploy recipe at 1.8.0 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. `126-teardown.sh` is an evidence/ops script created during execution, not test infrastructure.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-tag approval (notes, dependency list, CI) | REL-05/06 (D-13) | Owner decision; tag push is irreversible | Present checkpoint; record verbatim reply |
| Pre-prod approval with smoke results | REL-06 (D-13) | Owner decision | Present checkpoint; record verbatim reply |
| Post-deploy confirmation | REL-06 (D-17) | Owner sign-off | Record verbatim confirmation after successful scan + arr check |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
