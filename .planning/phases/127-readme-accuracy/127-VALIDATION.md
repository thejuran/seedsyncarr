---
phase: 127
slug: readme-accuracy
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-11-18
---

# Phase 127 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None for prose. Mechanical python3/grep/awk/git checks (see 127-RESEARCH.md "Validation Architecture"). Existing CI (pytest, `ruff check src/python/`, Angular, e2e) unaffected |
| **Config file** | none |
| **Quick run command** | `python3 .planning/phases/127-readme-accuracy/127-check.py all` (replaces the verification block in 127-RESEARCH.md; covers the widened D-08: SECURITY.md lines 40 and 43) |
| **Full suite command** | quick block + `ruff check src/python/` (expect clean, unchanged) |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick block
- **After every plan wave:** Run the full command
- **Before `/bm:verify-work`:** Full command green and the D-04 claims read-through complete
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 127-01-T1 | 01 | 1 | DOC-01, DOC-04 | T-127-02 | Guides linked; Quick Start states port exposure and that `api_token` does not protect the UI | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py structure` | yes | ⬜ pending |
| 127-01-T2 | 01 | 1 | DOC-02, DOC-03 | T-127-01, T-127-03, T-127-04 | Defaults and cleanup conditions stated as the code behaves; no webhook-secret recommendation | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py claims` | yes | ⬜ pending |
| 127-01-T3 | 01 | 1 | DOC-02, DOC-03 (D-08) | T-127-03, T-127-06 | SECURITY.md changed on lines 40 and 43 only; scope limited to README.md and SECURITY.md | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py all && ruff check src/python/` | yes | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No remaining unconditional claims in README | DOC-03 / D-04 | Judgment of prose | Read the full README against the claims table in 127-RESEARCH.md; confirm each is qualified or removed |
| Webhook-security wording does not recommend a secret / require-secret for Sonarr/Radarr | DOC-02/03, revised D-03 | Prose meaning | Read README Security + How It Works and SECURITY.md line ~43 bullet |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
