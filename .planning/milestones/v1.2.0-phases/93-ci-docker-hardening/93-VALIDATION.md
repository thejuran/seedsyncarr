---
phase: 93
slug: ci-docker-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 93 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) + GitHub Actions workflow validation |
| **Config file** | `src/python/tests/conftest.py` |
| **Quick run command** | `make test-python` |
| **Full suite command** | `make test-python && make e2e-test` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test-python`
- **After every plan wave:** Run `make test-python && make e2e-test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 93-01-01 | 01 | 1 | CISEC-01 | — | Workflow-level permissions set to `contents: read` | config | `grep 'contents: read' .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 93-01-02 | 01 | 1 | CISEC-02 | — | All actions pinned to SHA with version comment | config | `grep -E '@[a-f0-9]{40} #' .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 93-01-03 | 01 | 1 | CISEC-03 | — | publish-docker-image in needs chain of publish-github-release | config | `grep -A5 'publish-github-release' .github/workflows/ci.yml \| grep publish-docker-image` | ✅ | ⬜ pending |
| 93-01-04 | 01 | 1 | CISEC-04 | — | Per-job write permissions only where needed | config | `grep -c 'permissions:' .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 93-02-01 | 02 | 2 | DOCKSEC-01 | — | SSH key-only auth in Python test container | integration | `make test-python` | ✅ | ⬜ pending |
| 93-02-02 | 02 | 2 | DOCKSEC-02 | — | SSH key-only auth in E2E remote container | e2e | `make e2e-test` | ✅ | ⬜ pending |
| 93-02-03 | 02 | 2 | DOCKSEC-03 | — | PasswordAuthentication no in sshd_config | config | `grep 'PasswordAuthentication no' src/docker/test/python/Dockerfile` | ✅ | ⬜ pending |
| 93-02-04 | 02 | 2 | DOCKSEC-04 | — | No hardcoded passwords in Dockerfiles | config | `grep -r 'remotepass\|testpass' src/docker/test/` | ✅ | ⬜ pending |
| 93-02-05 | 02 | 2 | DOCKSEC-05 | — | Ephemeral SSH key pairs at build time | integration | `make test-python` | ✅ | ⬜ pending |
| 93-02-06 | 02 | 2 | DOCKSEC-06 | — | sshd runs as non-root | config | `grep -E 'USER|gosu' src/docker/test/python/Dockerfile` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Actions permissions actually enforced | CISEC-01, CISEC-04 | Requires actual CI run on GitHub | Push branch, verify CI workflow runs successfully with restricted permissions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
