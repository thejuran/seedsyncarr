---
phase: 93-ci-docker-hardening
plan: "02"
subsystem: docker-test-security
tags:
  - docker
  - sshd
  - security
  - test-cleanup
  - DOCKSEC-01
  - DOCKSEC-03
  - DOCKSEC-04
  - DOCKSEC-06
dependency_graph:
  requires: []
  provides:
    - hardened-python-test-container
    - key-only-ssh-test-infra
  affects:
    - src/docker/test/python/Dockerfile
    - src/docker/test/python/entrypoint.sh
    - src/python/tests/unittests/test_ssh/test_sshcp.py
    - src/python/tests/integration/test_lftp/test_lftp_protocol.py
    - src/python/tests/integration/test_controller/test_controller.py
tech_stack:
  added: []
  patterns:
    - gosu for signal-correct user switching in Docker entrypoints
    - setcap cap_net_bind_service for non-root port 22 binding
    - sed -i to replace sshd_config lines (not echo >> to avoid conflicting entries)
    - passwd -l to lock user password after useradd+chpasswd
key_files:
  created: []
  modified:
    - src/docker/test/python/Dockerfile
    - src/docker/test/python/entrypoint.sh
    - src/python/tests/unittests/test_ssh/test_sshcp.py
    - src/python/tests/integration/test_lftp/test_lftp_protocol.py
    - src/python/tests/integration/test_controller/test_controller.py
decisions:
  - "Use sed -i to replace PasswordAuthentication (not echo >>) to avoid conflicting entries with pre-existing commented-out lines in sshd_config"
  - "passwd -l seedsyncarrtest placed after useradd (not before) to ensure user exists when locked"
  - "setcap placed as last step touching /usr/sbin/sshd to survive apt-get install of openssh-server"
  - "groupadd testgroup + usermod root into testgroup preserves file group access for tests"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-28"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 93 Plan 02: Python Test Container SSH Hardening Summary

**One-liner:** Hardened python test container with non-root sshdaemon sshd, key-only auth via sed-replaced sshd_config, dedicated testgroup replacing root group, accept-new host key checking, and all password-auth-dependent tests removed from three test files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Harden python Dockerfile and entrypoint | 333f326 | src/docker/test/python/Dockerfile, src/docker/test/python/entrypoint.sh |
| 2 | Remove password-auth tests from test files | 7c97fe0 | test_sshcp.py, test_lftp_protocol.py, test_controller.py |

## What Was Built

### Task 1: Dockerfile and Entrypoint Hardening

**src/docker/test/python/Dockerfile** changes:
- Added `libcap2-bin` and `gosu` to apt-get install line
- Created dedicated `sshdaemon` system user (`useradd -r -s /usr/sbin/nologin -d /nonexistent`) for non-root sshd (DOCKSEC-04)
- Replaced `PasswordAuthentication yes` append with `sed -i` replacement to set `PasswordAuthentication no` (DOCKSEC-03)
- Added `KbdInteractiveAuthentication no` and `UsePAM no` via sed replacement
- Added `passwd -l seedsyncarrtest` to lock password after user creation (DOCKSEC-03)
- Replaced `usermod -a -G root seedsyncarrtest` with `groupadd testgroup` + added both `seedsyncarrtest` and `root` to `testgroup` (DOCKSEC-01)
- Changed `StrictHostKeyChecking no` to `accept-new` using `printf` (DOCKSEC-06)
- Added `setcap cap_net_bind_service=+ep /usr/sbin/sshd` as last step touching sshd binary (DOCKSEC-04)
- Added `chown sshdaemon /var/run/sshd` and `chown sshdaemon:sshdaemon /etc/ssh/ssh_host_*` (DOCKSEC-04)

**src/docker/test/python/entrypoint.sh** changes:
- Changed `sshd -D &` to `gosu sshdaemon /usr/sbin/sshd -D &` (DOCKSEC-04)

### Task 2: Password-Auth Test Removals

**src/python/tests/unittests/test_ssh/test_sshcp.py:**
- Removed `_TEST_PASSWORD = "seedsyncarrpass"` constant
- Removed `("password", _TEST_PASSWORD)` tuple from `_PARAMS` (now keyauth-only)
- Removed `test_copy_error_bad_password` method
- Removed `test_shell_error_bad_password` method
- All 10 parameterized tests now run keyauth variant only

**src/python/tests/integration/test_lftp/test_lftp_protocol.py:**
- Removed `_TEST_PASSWORD = "seedsyncarrpass"` constant
- Removed `self.password = _TEST_PASSWORD` from `setUp`
- Removed `test_password_auth` method (36 lines)
- Removed `test_error_bad_password` method (37 lines)

**src/python/tests/integration/test_controller/test_controller.py:**
- Removed `"remote_password": "seedsyncarrpass"` from setUp config dict
- Removed `test_bad_remote_password_raises_exception` method
- Removed `test_password_auth` method (45 lines)
- `"use_ssh_key": "True"` preserved in setUp config

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed passwd -l ordering: must come after useradd**
- **Found during:** Task 1 review of written Dockerfile
- **Issue:** Initial write placed `passwd -l seedsyncarrtest` (line 34) before `useradd ... seedsyncarrtest` (line 37) — Docker build would fail with "user does not exist"
- **Fix:** Moved `passwd -l seedsyncarrtest` to after the `useradd` + `chpasswd` block, adding it as a separate `RUN` step immediately after user and group setup
- **Files modified:** src/docker/test/python/Dockerfile
- **Commit:** 333f326 (incorporated in same task commit)

## Known Stubs

None — all changes are security hardening and test cleanup. No UI components or data stubs introduced.

## Threat Flags

No new threat surface introduced. All changes reduce the existing attack surface per the threat register (T-93-06 through T-93-10 all mitigated).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/docker/test/python/Dockerfile exists | FOUND |
| src/docker/test/python/entrypoint.sh exists | FOUND |
| src/python/tests/unittests/test_ssh/test_sshcp.py exists | FOUND |
| src/python/tests/integration/test_lftp/test_lftp_protocol.py exists | FOUND |
| src/python/tests/integration/test_controller/test_controller.py exists | FOUND |
| .planning/phases/93-ci-docker-hardening/93-02-SUMMARY.md exists | FOUND |
| Commit 333f326 exists | FOUND |
| Commit 7c97fe0 exists | FOUND |
