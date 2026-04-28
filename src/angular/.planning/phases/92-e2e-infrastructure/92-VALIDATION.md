---
phase: 92
slug: e2e-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 92 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (E2E) + shell scripts (infrastructure) |
| **Config file** | `src/e2e/playwright.config.ts` |
| **Quick run command** | `make run-tests-e2e` |
| **Full suite command** | `make run-tests-e2e` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-e2e`
- **After every plan wave:** Run `make run-tests-e2e`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 92-01-01 | 01 | 1 | E2EINFRA-01 | — | N/A | integration | `grep -n 'SERVER_UP=""' src/docker/test/e2e/run_tests.sh` | ✅ | ⬜ pending |
| 92-01-02 | 01 | 1 | E2EINFRA-02 | — | N/A | integration | `grep -n 'service_healthy' src/docker/test/e2e/compose.yml` | ✅ | ⬜ pending |
| 92-01-03 | 01 | 1 | E2EINFRA-03 | — | N/A | verify-only | `grep -n 'wait.*down\|poll.*up' src/docker/test/e2e/configure/setup_seedsyncarr.sh` | ✅ | ⬜ pending |
| 92-01-04 | 01 | 1 | E2EINFRA-04 | — | N/A | integration | `grep -n 'except.*JSONDecodeError' src/docker/test/e2e/configure/parse_status.py` | ✅ | ⬜ pending |
| 92-01-05 | 01 | 1 | E2EINFRA-05 | — | N/A | e2e | `make run-tests-e2e` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| arm64 reliability | E2EINFRA-05 | Platform-specific, requires arm64 hardware | Run `make run-tests-e2e` on arm64 Docker host, verify no timing failures |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
