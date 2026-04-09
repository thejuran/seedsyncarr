---
phase: 58
slug: docs-site
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | MkDocs build (--strict mode) |
| **Config file** | `src/python/mkdocs.yml` |
| **Quick run command** | `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-test` |
| **Full suite command** | `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-test` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-test`
- **After every plan wave:** Run `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-test`
- **Before `/gsd-verify-work`:** Full build must be green + site loads at thejuran.github.io/seedsyncarr
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 58-01-01 | 01 | 1 | PRES-04 | — | N/A | smoke | `cd src/python && python3 -m mkdocs build --strict` | ❌ W0 | ⬜ pending |
| 58-01-02 | 01 | 1 | PRES-05 | — | N/A | smoke | `cd src/python && python3 -m mkdocs build --strict` | ❌ W0 | ⬜ pending |
| 58-01-03 | 01 | 1 | PRES-06 | — | N/A | smoke | `cd src/python && python3 -m mkdocs build --strict` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/python/docs/` directory — does not exist; create with all nav pages
- [ ] `src/python/docs/images/` — does not exist; copy favicon and logo assets

*All content pages are created in Wave 1 — build cannot pass until docs/ exists.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Site loads at thejuran.github.io/seedsyncarr | PRES-04 | Requires CI push + GitHub Pages enabled | Push to main, wait for CI, visit URL |
| GitHub Pages branch enabled | PRES-04 | GitHub Settings, not code | Check Settings > Pages > Branch = gh-pages |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
