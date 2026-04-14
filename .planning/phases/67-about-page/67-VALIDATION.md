---
phase: 67
slug: about-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 67 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x / Angular test (karma) |
| **Config file** | `pytest.ini` / `karma.conf.js` |
| **Quick run command** | `cd frontend && npx ng test --watch=false --browsers=ChromeHeadless` |
| **Full suite command** | `cd frontend && npx ng test --watch=false --browsers=ChromeHeadless && cd .. && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx ng test --watch=false --browsers=ChromeHeadless`
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 67-01-01 | 01 | 1 | ABUT-01 | — | N/A | visual | Manual snapshot | — | ⬜ pending |
| 67-01-02 | 01 | 1 | ABUT-02 | — | N/A | visual | Manual snapshot | — | ⬜ pending |
| 67-01-03 | 01 | 1 | ABUT-03 | — | N/A | visual | Manual snapshot | — | ⬜ pending |
| 67-01-04 | 01 | 1 | ABUT-04 | — | N/A | visual | Manual snapshot | — | ⬜ pending |
| 67-02-01 | 02 | 2 | ABUT-01 | — | N/A | unit | `npx ng test --watch=false --browsers=ChromeHeadless` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Identity card layout matches mockup | ABUT-01 | Visual fidelity check | Verify app icon, title, version, tagline, build info render in centered card |
| System info table rows | ABUT-02 | Visual layout | Verify key-value rows for Python, Angular, OS, uptime, PID, config path |
| Link cards hover transition | ABUT-03 | CSS interaction | Hover each card, verify amber color transition |
| License badge and copyright footer | ABUT-04 | Visual check | Verify badge and copyright text at bottom |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
