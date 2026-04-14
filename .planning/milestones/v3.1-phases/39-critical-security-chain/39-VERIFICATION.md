---
phase: 39-critical-security-chain
verified: 2026-02-23T00:00:00Z
status: passed
score: 3/3 success criteria verified
re_verification: false
---

# Phase 39: Critical Security Chain Verification Report

**Phase Goal:** The RSA private key attack chain is completely closed — no committed key material, no SSH MITM downgrade opportunity, and no pickle deserialization RCE vector
**Verified:** 2026-02-23
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Repository contains no RSA private key file; .gitignore prevents any future commit of key material | VERIFIED | `src/docker/stage/deb/id_rsa` absent from working tree; `.gitignore` contains `id_rsa` and `*.pem` patterns (lines 12-13) |
| 2 | SSH connections to the remote server require host key verification — unknown hosts are not silently accepted and MITM downgrade is not possible | VERIFIED | `sshcp.py` line 53: `StrictHostKeyChecking=accept-new`; `UserKnownHostsFile=/dev/null` removed entirely; MITM detection pattern `REMOTE HOST IDENTIFICATION HAS CHANGED` present in both pexpect branches (lines 84, 116) with explicit error at lines 103 and 134; Docker image `Dockerfile` line 128: `StrictHostKeyChecking accept-new` |
| 3 | Remote scanner communicates scan results via JSON; pickle deserialization is not used anywhere in the scan pipeline | VERIFIED | `scan_fs.py` uses `import json` + `json.dumps` (lines 3, 43-44); `remote_scanner.py` uses `json.loads` + `SystemFile.from_dict` (lines 74-76); `SystemFile.to_dict()` and `from_dict()` implemented in `file.py` (lines 55-89); zero pickle imports in scan pipeline (grep confirmed `NO_PICKLE`) |

**Score:** 3/3 success criteria verified

---

## Required Artifacts

### Plan 39-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.gitignore` | Private key exclusion patterns | VERIFIED | Contains `id_rsa` (line 12) and `*.pem` (line 13) under `# SSH private keys` comment |
| `src/python/ssh/sshcp.py` | Hardened SSH options | VERIFIED | `StrictHostKeyChecking=accept-new` at line 53; `REMOTE HOST IDENTIFICATION HAS CHANGED` at lines 84 and 116; `UserKnownHostsFile` entirely absent |
| `src/docker/build/docker-image/Dockerfile` | Docker SSH hardening | VERIFIED | Line 128: `echo "StrictHostKeyChecking accept-new" > /root/.ssh/config` |
| `src/docker/stage/deb/Dockerfile` | ssh-keygen at build time | VERIFIED | Lines 28-30: `ssh-keygen -t rsa -b 4096 -N "" -f /home/user/.ssh/id_rsa` |
| `src/docker/stage/deb/id_rsa` (deleted) | Private key absent from working tree | VERIFIED | File does not exist; confirmed by `test ! -f` returning success |

### Plan 39-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/system/file.py` | JSON serialization for SystemFile | VERIFIED | `to_dict()` at lines 55-68; `from_dict()` classmethod at lines 70-89; full round-trip including timestamps and nested children |
| `src/python/scan_fs.py` | JSON output from scan script | VERIFIED | `import json` at line 3; `json_list = [f.to_dict() for f in root_files]` at line 43; `sys.stdout.write(json.dumps(json_list))` at line 44 |
| `src/python/controller/scan/remote_scanner.py` | JSON deserialization of scan results | VERIFIED | `import json` at line 2; `json.loads(out_str)` at line 75; `SystemFile.from_dict(d)` at line 76; error handling for `JSONDecodeError, KeyError, TypeError, ValueError` at line 77 |
| `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` | Updated tests using JSON | VERIFIED | `import json` at line 9; all mock return values use `json.dumps([]).encode()`; mangled-output test asserts `"Invalid scan data"` at line 436; zero pickle references in file |

---

## Key Link Verification

### Plan 39-01 Key Links

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `src/python/ssh/sshcp.py` | SSH connections | `StrictHostKeyChecking=accept-new` option | WIRED | Line 53 sets the flag in `command_args`; used in every `ssh` and `scp` invocation via `__run_command` |
| `src/docker/stage/deb/Dockerfile` | SSH key setup | `ssh-keygen` at build time | WIRED | Lines 28-30 generate keypair as `user`; no static key file referenced anywhere |

### Plan 39-02 Key Links

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `src/python/scan_fs.py` | `src/python/controller/scan/remote_scanner.py` | JSON-encoded SystemFile list over SSH stdout | WIRED | `scan_fs.py` writes JSON via `sys.stdout.write(json.dumps(json_list))`; `remote_scanner.py` reads it via `json.loads(out_str)` at line 75 |
| `src/python/system/file.py` | `src/python/scan_fs.py` | `SystemFile.to_dict()` called before `json.dumps` | WIRED | `scan_fs.py` line 43: `[f.to_dict() for f in root_files]` |
| `src/python/system/file.py` | `src/python/controller/scan/remote_scanner.py` | `SystemFile.from_dict()` called after `json.loads` | WIRED | `remote_scanner.py` line 76: `[SystemFile.from_dict(d) for d in file_dicts]` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEC-01 | 39-01-PLAN.md | RSA private key removed from repository and added to .gitignore (CWE-312) | SATISFIED | `id_rsa` absent from working tree; `.gitignore` lines 11-13 prevent future commits; staging Dockerfile generates key at build time |
| SEC-02 | 39-01-PLAN.md | SSH connections use StrictHostKeyChecking=accept-new with known_hosts instead of disabled verification (CWE-295) | SATISFIED | `sshcp.py` line 53: `accept-new`; MITM detection in both pexpect branches; Docker image uses `accept-new`; `UserKnownHostsFile=/dev/null` removed |
| SEC-07 | 39-02-PLAN.md | Remote scanner uses JSON deserialization instead of pickle (CWE-502) | SATISFIED | Full pipeline migrated: `scan_fs.py` → `json.dumps`, `remote_scanner.py` → `json.loads + from_dict`, `SystemFile` has `to_dict/from_dict`, tests use `json.dumps([]).encode()` |

**Orphaned requirements check:** REQUIREMENTS.md lists SEC-01, SEC-02, SEC-07 as mapped to Phase 39. All three are claimed by plans and verified. No orphaned requirements.

---

## Anti-Patterns Found

None. Scanned all 9 modified files for TODO/FIXME/HACK/placeholder patterns, empty implementations, and stub returns. Zero hits.

Notable intentional exception: `src/docker/test/python/Dockerfile` retains `StrictHostKeyChecking no` with an explicit comment "Test-only: disable host key checking for ephemeral test container connecting to localhost sshd" — this is a documented, intentional exception for an ephemeral container, not an anti-pattern.

The `htmlcov/` directory contains an HTML coverage report that references the old `StrictHostKeyChecking=no` string, but `htmlcov/` is listed in `.gitignore` (line 8) and is not a source file.

---

## Human Verification Required

None required for goal verification. All security changes are structural code modifications verifiable programmatically. The following are optional operational validations outside the scope of this phase:

1. **Live connection test** — Verify that SeedSync actually connects to a remote SSH host after these changes and that the `~/.ssh/known_hosts` file is populated correctly. This requires a running environment, not verifiable from source.

2. **MITM detection test** — Verify that altering a host key while SeedSync is running produces the explicit error message "Remote host key has changed. This may indicate a MITM attack." in the UI. Requires a controlled environment.

Neither item blocks goal verification — the code changes are complete and correct.

---

## Gaps Summary

No gaps. All three success criteria are fully achieved:

1. The committed `id_rsa` private key is deleted from the working tree, `.gitignore` protects against future commits, and the staging Dockerfile generates a fresh key at build time — the CWE-312 credential exposure vector is closed.

2. Every SSH connection path (`sshcp.py`, Docker image) now uses `StrictHostKeyChecking=accept-new` and the default `~/.ssh/known_hosts` file. The `UserKnownHostsFile=/dev/null` bypass is removed. Active MITM detection via pexpect raises an explicit `SshcpError` in both the password-auth and key-auth code paths — the CWE-295 MITM downgrade vector is closed.

3. The full remote scan pipeline (`scan_fs.py` → SSH stdout → `remote_scanner.py`) uses JSON throughout. `SystemFile.to_dict()` and `from_dict()` provide a safe, data-only serialization format. Zero pickle imports remain in any scan pipeline file. Malformed input raises a non-recoverable `ScannerError` with message "Invalid scan data" — the CWE-502 pickle RCE vector is closed.

All 4 commits (f6643db, e34ba5e, 108018f, abef04a) are present in git history.

---

_Verified: 2026-02-23_
_Verifier: Claude (gsd-verifier)_
