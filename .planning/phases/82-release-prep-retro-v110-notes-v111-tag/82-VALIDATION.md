---
phase: 82
slug: release-prep-retro-v110-notes-v111-tag
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 82 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + jest 29.x (existing) |
| **Config file** | `src/python/pyproject.toml` / `src/angular/jest.config.ts` |
| **Quick run command** | `make test-python && cd src/angular && npx jest --bail` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test-python && cd src/angular && npx jest --bail`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 82-01-01 | 01 | 1 | DOCS-01 | — | N/A | file-check | `test -f CHANGELOG.md && grep "## \[1.1.0\]" CHANGELOG.md` | ✅ | ⬜ pending |
| 82-01-02 | 01 | 1 | DOCS-01 | — | N/A | cli-check | `gh release view v1.1.0 --json tagName` | ✅ | ⬜ pending |
| 82-02-01 | 02 | 1 | DOCS-01 | — | N/A | file-check | `grep "## \[1.1.1\]" CHANGELOG.md` | ✅ | ⬜ pending |
| 82-03-01 | 03 | 2 | DOCS-01 | — | N/A | file-check | `grep '"version": "1.1.1"' src/angular/package.json` | ✅ | ⬜ pending |
| 82-03-02 | 03 | 2 | DOCS-01 | — | N/A | file-check | `grep 'version = "1.1.1"' src/python/pyproject.toml` | ✅ | ⬜ pending |
| 82-04-01 | 04 | 3 | DOCS-01 | — | N/A | ci-check | `test -f .github/workflows/ci.yml && grep "deb" .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 82-05-01 | 05 | 3 | DOCS-01 | — | N/A | cli-check | `git tag -l v1.1.1` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no new test framework or stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker image publishes on tag push | DOCS-01 | Requires actual tag push to GitHub triggering CI | Push v1.1.1 tag, verify Docker Hub image appears |
| Deb package attached to GitHub Release | DOCS-01 | Requires CI run completion | After tag push, verify `gh release view v1.1.1 --json assets` lists .deb |
| GitHub Release body matches CHANGELOG | DOCS-01 | Content comparison | Compare `gh release view v1.1.1 --json body` against CHANGELOG.md v1.1.1 section |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
