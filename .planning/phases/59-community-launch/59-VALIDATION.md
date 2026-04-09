---
phase: 59
slug: community-launch
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | N/A — content-only phase, no code changes |
| **Config file** | none |
| **Quick run command** | N/A |
| **Full suite command** | N/A |
| **Estimated runtime** | N/A |

---

## Sampling Rate

- **After every task commit:** Manual review of drafted content
- **After every plan wave:** Verify all links resolve, screenshots render
- **Before `/gsd-verify-work`:** All posts drafted, deferrals documented
- **Max feedback latency:** N/A (human review)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 59-01-01 | 01 | 1 | LNCH-01 | — | N/A | manual | Verify post draft exists | N/A | ⬜ pending |
| 59-01-02 | 01 | 1 | LNCH-02 | — | N/A | manual | Verify follow-up drafts exist | N/A | ⬜ pending |
| 59-02-01 | 02 | 2 | LNCH-03 | — | N/A | manual | Verify deferral documented | N/A | ⬜ pending |
| 59-02-02 | 02 | 2 | LNCH-04 | — | N/A | manual | Verify deferral documented | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No code or test framework needed — this phase produces content artifacts only.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| r/selfhosted post follows "I built X" format | LNCH-01 | Content review | Read draft, verify format matches success criteria |
| Follow-up posts are audience-tailored | LNCH-02 | Content review | Read each draft, verify unique framing per audience |
| awesome-selfhosted PR deferred to Aug 2026 | LNCH-03 | Calendar check | Verify calendar reminder exists with correct date |
| Awesomarr PR deferred until 50+ stars | LNCH-04 | Calendar check | Verify calendar reminder exists with correct trigger |
| Docs site links resolve | LNCH-01 | Link check | Open all URLs in drafts, verify 200 status |

---

## Validation Sign-Off

- [ ] All tasks have manual verification steps defined
- [ ] All four LNCH requirements have verification coverage
- [ ] No automated testing needed (content-only phase)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
