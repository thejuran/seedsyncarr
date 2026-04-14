---
phase: 39-critical-security-chain
plan: "01"
subsystem: security/ssh
tags: [security, ssh, docker, private-key, host-key-verification]
dependency_graph:
  requires: []
  provides: [SEC-01, SEC-02]
  affects: [src/python/ssh/sshcp.py, src/docker/stage/deb/Dockerfile, src/docker/build/docker-image/Dockerfile]
tech_stack:
  added: []
  patterns:
    - StrictHostKeyChecking=accept-new for TOFU (Trust On First Use) SSH host verification
    - pexpect REMOTE HOST IDENTIFICATION HAS CHANGED pattern for MITM detection
    - ssh-keygen at Docker build time instead of committed private key
key_files:
  created: []
  modified:
    - .gitignore
    - src/docker/stage/deb/Dockerfile
    - src/python/ssh/sshcp.py
    - src/docker/build/docker-image/Dockerfile
    - src/docker/test/python/Dockerfile
decisions:
  - "Use StrictHostKeyChecking=accept-new (TOFU) rather than reject-all to preserve first-connect usability"
  - "Remove UserKnownHostsFile=/dev/null so known_hosts persists across reconnects"
  - "Detect REMOTE HOST IDENTIFICATION HAS CHANGED in both pexpect branches (password and key-auth paths)"
  - "Test Dockerfile keeps StrictHostKeyChecking=no with explicit comment explaining the ephemeral test exception"
metrics:
  duration_minutes: 5
  completed_date: "2026-02-24"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 39 Plan 01: Critical SSH Security Hardening Summary

**One-liner:** Removed committed RSA private key from repo and replaced disabled host verification with TOFU accept-new mode plus explicit MITM detection in pexpect SSH paths.

## What Was Built

This plan closed two SSH attack vectors in the SeedSync codebase:

1. **Committed private key** — `src/docker/stage/deb/id_rsa` was a committed 1,674-byte RSA private key visible in git history. Removed via `git rm` and protected against future commits with `.gitignore` patterns.

2. **Disabled host key checking** — Three locations used `StrictHostKeyChecking=no` (silently accept any server), which enables MITM attacks. Replaced with `accept-new` (TOFU: accept new servers, reject changed ones).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Remove committed RSA private key and add .gitignore protection | f6643db | .gitignore, src/docker/stage/deb/Dockerfile (delete id_rsa) |
| 2 | Harden SSH host key verification across all connection paths | e34ba5e | sshcp.py, docker-image/Dockerfile, test/python/Dockerfile |

## Changes Made

### Task 1: Private Key Removal

- Deleted `src/docker/stage/deb/id_rsa` from git tracking (`git rm`)
- Added `id_rsa` and `*.pem` patterns to `.gitignore` (public key `id_rsa.pub` intentionally excluded)
- Updated `src/docker/stage/deb/Dockerfile` to generate a fresh 4096-bit RSA keypair at build time via `ssh-keygen -t rsa -b 4096 -N "" -f /home/user/.ssh/id_rsa`

### Task 2: SSH Host Key Hardening

**sshcp.py (`__run_command`):**
- Changed `StrictHostKeyChecking=no` to `StrictHostKeyChecking=accept-new`
- Removed `UserKnownHostsFile=/dev/null` (now uses default `~/.ssh/known_hosts`)
- Added `REMOTE HOST IDENTIFICATION HAS CHANGED` pattern (index i=8) in both `expect()` calls
- Both branches raise `SshcpError` with explicit MITM warning on host key change

**docker-image/Dockerfile (line 128):**
- Changed SSH config from `StrictHostKeyChecking no\nUserKnownHostsFile /dev/null` to `StrictHostKeyChecking accept-new`

**test/python/Dockerfile:**
- No behavioral change — added explicit comment: "Test-only: disable host key checking for ephemeral test container connecting to localhost sshd"

## Security Posture After

| Vector | Before | After |
|--------|--------|-------|
| Committed private key | RSA key in git history | Key deleted; build-time generated |
| SSH MITM (sshcp.py) | Silent accept any server | TOFU + explicit error on key change |
| SSH MITM (Docker image) | Silent accept any server | TOFU accept-new |
| Test container | Silent accept (test-only) | Silent accept (documented test exception) |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

**Files exist:**
- [x] .gitignore (modified, contains id_rsa pattern)
- [x] src/python/ssh/sshcp.py (contains accept-new and MITM detection)
- [x] src/docker/build/docker-image/Dockerfile (contains accept-new)
- [x] src/docker/stage/deb/Dockerfile (contains ssh-keygen)
- [x] src/docker/test/python/Dockerfile (contains test-only comment)

**Commits exist:**
- [x] f6643db — fix(39-01): remove committed RSA private key and protect with .gitignore
- [x] e34ba5e — fix(39-01): harden SSH host key verification across all connection paths

## Self-Check: PASSED
