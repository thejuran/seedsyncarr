---
phase: 93-ci-docker-hardening
plan: "03"
subsystem: docker-e2e
tags: [security, docker, ssh, e2e, hardening]
dependency_graph:
  requires: [93-01]
  provides: [hardened-e2e-remote-container, ephemeral-ssh-key-flow]
  affects: [src/docker/test/e2e/remote/Dockerfile, src/docker/test/e2e/compose.yml, src/docker/test/e2e/configure/setup_seedsyncarr.sh, Makefile]
tech_stack:
  added: []
  patterns: [ephemeral-ed25519-key-pair, non-root-sshd, ssh-build-arg, compose-bind-volume]
key_files:
  created: []
  modified:
    - src/docker/test/e2e/remote/Dockerfile
    - src/docker/test/e2e/compose.yml
    - src/docker/test/e2e/configure/setup_seedsyncarr.sh
    - Makefile
  deleted:
    - src/docker/test/e2e/remote/id_rsa.pub
decisions:
  - Ephemeral ed25519 key generated in Makefile before docker build and passed as --build-arg SSH_PUBKEY to remote Dockerfile
  - PidFile /tmp/sshd.pid added for non-root sshd because /var/run/sshd.pid requires root write access
  - compose.yml bind-mounts /tmp/e2e_test_key read-only into /home/seedsync/.ssh/id_ed25519 (default ED25519 path recognized by SSH/lftp automatically)
  - UsePAM no appended instead of sed-replaced because sshd_config default has no UsePAM line in Ubuntu 22.04
metrics:
  duration: "1 minute"
  completed: "2026-04-28T14:51:10Z"
  tasks_completed: 2
  files_modified: 4
  files_deleted: 1
requirements:
  - DOCKSEC-02
  - DOCKSEC-04
  - DOCKSEC-05
---

# Phase 93 Plan 03: E2E Remote Container SSH Hardening Summary

**One-liner:** Ephemeral ED25519 key-pair via Makefile ssh-keygen + --build-arg, sshd runs as non-root remoteuser on port 1234 with PasswordAuthentication disabled.

## What Was Built

Hardened the E2E remote test Docker container across four coordinated files to eliminate hardcoded SSH credentials and reduce sshd blast radius:

1. **`src/docker/test/e2e/remote/Dockerfile`** — Complete rewrite: removed `remoteuser:remotepass` password, replaced static `ADD id_rsa.pub` with `ARG SSH_PUBKEY` build-arg injection into `authorized_keys`, disabled `PasswordAuthentication` + `KbdInteractiveAuthentication` + `UsePAM`, locked remoteuser password via `passwd -l`, generated sshd host keys and transferred ownership to remoteuser (`chown /etc/ssh/ssh_host_*`), added `PidFile /tmp/sshd.pid` for non-root sshd write access, switched `USER remoteuser` before CMD, added `-e` for sshd stderr logging.

2. **`Makefile`** — Added ephemeral key pair generation (`ssh-keygen -t ed25519 -N "" -f /tmp/e2e_test_key -q 2>/dev/null || true`) before the remote container `docker buildx build` and passed the public key as `--build-arg SSH_PUBKEY="$${E2E_SSH_PUBKEY}"`.

3. **`src/docker/test/e2e/compose.yml`** — Added `volumes` bind-mount to `myapp` service: `/tmp/e2e_test_key` → `/home/seedsync/.ssh/id_ed25519` (read-only); removed `REMOTE_PASSWORD` env var from configure service.

4. **`src/docker/test/e2e/configure/setup_seedsyncarr.sh`** — Replaced `remote_password` curl call with `use_ssh_key/true` to tell the app to use SSH key auth instead of password auth.

5. **`src/docker/test/e2e/remote/id_rsa.pub`** — Deleted (static committed public key no longer needed).

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: Harden E2E remote Dockerfile | `7c4ab43` | src/docker/test/e2e/remote/Dockerfile (rewritten), id_rsa.pub (deleted) |
| Task 2: Wire ephemeral SSH key flow | `747a756` | Makefile, compose.yml, setup_seedsyncarr.sh |

## Security Requirements Satisfied

| Req | Description | How Addressed |
|-----|-------------|---------------|
| DOCKSEC-02 | Disable PasswordAuthentication in remote container | sed replaces PasswordAuthentication+KbdInteractiveAuthentication; echo UsePAM no; passwd -l remoteuser |
| DOCKSEC-04 | Run sshd as non-root in remote container | chown ssh_host_* to remoteuser; PidFile /tmp/sshd.pid; USER remoteuser before CMD |
| DOCKSEC-05 | Ephemeral SSH key pair at build time | Makefile ssh-keygen generates fresh key per build; --build-arg passes pubkey to Dockerfile |

## Threat Model Coverage

All threats T-93-11 through T-93-15 from the plan threat model addressed:
- **T-93-11** (hardcoded "remotepass"): Mitigated — `chpasswd` removed, `PasswordAuthentication no`, `passwd -l`
- **T-93-12** (static id_rsa.pub in git): Mitigated — file deleted, replaced with ephemeral `--build-arg SSH_PUBKEY`
- **T-93-13** (sshd running as root): Mitigated — `USER remoteuser` + host key ownership transfer
- **T-93-14** (ephemeral key at /tmp on CI runner): Accepted — key is per-build, CI runner is ephemeral
- **T-93-15** (ssh-keygen fails silently): Accepted — `|| true` prevents prompt; empty ARG causes test failure caught by E2E

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All plan verification checks passed:
1. `grep -r "remotepass" src/docker/test/e2e/` — no matches
2. `test ! -f src/docker/test/e2e/remote/id_rsa.pub` — file deleted
3. `grep "REMOTE_PASSWORD" src/docker/test/e2e/compose.yml` — no matches
4. `grep "remote_password" src/docker/test/e2e/configure/setup_seedsyncarr.sh` — no matches

Note: `make run-tests-e2e` end-to-end validation requires a live Docker environment and a staged image — this is a CI gate, not a local verification.

## Known Stubs

None.

## Threat Flags

None — all security-relevant surface changes were pre-identified in the plan threat model.

## Self-Check: PASSED

Files exist:
- src/docker/test/e2e/remote/Dockerfile: FOUND
- src/docker/test/e2e/compose.yml: FOUND
- src/docker/test/e2e/configure/setup_seedsyncarr.sh: FOUND
- Makefile: FOUND
- id_rsa.pub deleted: CONFIRMED

Commits exist:
- 7c4ab43: FOUND
- 747a756: FOUND
