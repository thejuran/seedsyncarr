---
phase: 97-medium-priority-python-coverage
plan: 03
subsystem: web-config-ssrf
tags: [coverage, ssrf, security, python, ipv6, testing]
requires:
  - "97-01 (coverage baseline anchor — RATCHET-01)"
provides:
  - "TestValidateUrl: full-path unit coverage for ConfigHandler._validate_url (COVMED-02)"
affects:
  - "Phase 100 ratchet (these tests raise covered branches in web/handler/config.py)"
tech-stack:
  added: []
  patterns:
    - "Pure @staticmethod tested directly (ConfigHandler._validate_url), no bottle stack / no real DNS"
    - "socket.getaddrinfo stubbed via @patch('web.handler.config.socket') with mock_socket.gaierror = socket.gaierror reassignment"
    - "IP under test injected at addr_info[4][0]; multi-address result proves the all-results loop"
key-files:
  created: []
  modified:
    - "src/python/tests/unittests/test_web/test_handler/test_config_handler.py (added TestValidateUrl, 15 cases)"
decisions:
  - "D-01/D-02 unmap-and-recheck fix UNNECESSARY: Python 3.12 ipaddress natively flags ::ffff:10.0.0.1/::ffff:127.0.0.1/::ffff:169.254.0.1 as private/loopback/link-local, and ::ffff:8.8.8.8 returns None — verified RED-first; config.py left unchanged"
  - "A blanket IPv4-mapped block would have been a regression (it would wrongly reject ::ffff:8.8.8.8); the no-op decision is the secure outcome"
  - "DNS-rebind / TOCTOU left out of scope per the documented limitation at config.py:59-62 (T-97-03-02 accepted)"
metrics:
  duration: ~10m
  completed: 2026-05-28
requirements: [COVMED-02]
---

# Phase 97 Plan 03: SSRF _validate_url IPv6/Reserved-Range Coverage Summary

Added a dedicated `TestValidateUrl` class (15 cases) exercising every documented input
class of the SSRF guard `ConfigHandler._validate_url`
(`src/python/web/handler/config.py:55-85`) by calling the `@staticmethod` directly with
`socket.getaddrinfo` stubbed — IPv4 private/loopback/link-local, IPv6
link-local/loopback/unique-local, IPv6-mapped IPv4 (private/loopback/link-local blocked,
**public `::ffff:8.8.8.8` allowed**), a multi-address result where any addr is private,
unresolved-hostname `gaierror`, a valid public host, and the scheme / no-hostname early
returns. All 15 cases ran **GREEN against the unmodified `config.py`**, so the pre-approved
D-01/D-02 unmap-and-recheck fix was **NOT applied** — Python 3.12's native `ipaddress`
checks already block mapped-private/loopback/link-local while allowing mapped-public, and a
blanket mapped-block would have regressed `::ffff:8.8.8.8`. COVMED-02 closed.

## What Was Built

- **`TestValidateUrl`** (appended to `test_config_handler.py`) — 15 unit tests calling
  `ConfigHandler._validate_url(...)` directly (it is a pure staticmethod, no handler
  instance / no bottle stack), with `web.handler.config.socket` patched per-test:
  - **IPv4 reserved (blocked):** `test_rejects_ipv4_private` (10.0.0.1),
    `test_rejects_ipv4_loopback` (127.0.0.1), `test_rejects_ipv4_link_local` (169.254.0.1).
  - **IPv6 reserved (blocked):** `test_rejects_ipv6_link_local` (fe80::1),
    `test_rejects_ipv6_loopback` (::1), `test_rejects_ipv6_unique_local` (fc00::1).
  - **IPv6-mapped IPv4 (blocked):** `test_rejects_ipv6_mapped_private_ipv4`
    (::ffff:10.0.0.1), `test_rejects_ipv6_mapped_loopback_ipv4` (::ffff:127.0.0.1),
    `test_rejects_ipv6_mapped_link_local_ipv4` (::ffff:169.254.0.1).
  - **IPv6-mapped PUBLIC (allowed → None):** `test_ACCEPTS_ipv6_mapped_PUBLIC_ipv4`
    (::ffff:8.8.8.8) — the load-bearing case proving unmap-AND-recheck, not blanket-block.
  - **Multi-address loop:** `test_rejects_multi_address_when_any_private`
    (`[(8.8.8.8),(10.0.0.1)]` → private/reserved) — proves the loop inspects ALL results.
  - **Resolution / control flow:** `test_unresolved_hostname` (gaierror → "Cannot resolve
    hostname"), `test_accepts_public_ip` (8.8.8.8 → None), `test_rejects_ftp_scheme`
    (no socket call → "Only http and https URLs are allowed"), `test_rejects_no_hostname`
    (`http:///path` → "Invalid URL: no hostname").

Every resolving test sets `mock_socket.getaddrinfo.return_value` (IP at index `[4][0]`)
and re-assigns `mock_socket.gaierror = socket.gaierror` so the real `except socket.gaierror`
clause keeps catching. The two early-return tests do NOT patch socket and assert the exact
return strings. Tests are CI-IPv6-independent (`getaddrinfo` is stubbed; the IP strings are
parsed by `ipaddress` directly, never resolved).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Add TestValidateUrl covering all SSRF input classes (RED-first) | `fbecf34` | `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` |
| 2 | Apply IPv6-mapped unmap fix ONLY-IF-RED; else confirm green and record D-01 no-op | (no commit — outcome 1: all green, `config.py` unchanged) | none |

## RED-First Result (D-01 / D-02 decision)

Outcome **(1): all 15 cases GREEN against the current, unmodified `config.py`.**

```
tests/unittests/test_web/test_handler/test_config_handler.py::TestValidateUrl
............... [100%]  15 passed
```

Python 3.12's `ipaddress` natively flags the IPv6-mapped reserved cases without any explicit
unmap:
- `ipaddress.ip_address("::ffff:10.0.0.1").is_private` → True (blocked),
- `ipaddress.ip_address("::ffff:127.0.0.1").is_loopback` → True (blocked),
- `ipaddress.ip_address("::ffff:169.254.0.1").is_link_local` → True (blocked),
- `ipaddress.ip_address("::ffff:8.8.8.8")` trips none of the four checks → `_validate_url`
  returns None (**allowed**, as required).

Therefore the pre-approved D-01/D-02 `addr.ipv4_mapped` unmap-and-recheck was **NOT applied**.
The current guard (`config.py:78`: `addr.is_private or addr.is_loopback or addr.is_reserved
or addr.is_link_local`) already satisfies the must-haves. Applying a blanket IPv4-mapped block
would have been a **regression** — it would wrongly reject `::ffff:8.8.8.8`. No DNS-rebind
handling was added (out of scope, T-97-03-02 accepted). No STATE.md deferred entry is needed
(no out-of-window finding; D-05 not triggered).

## Verification

- `cd src/python && poetry run pytest tests/unittests/test_web/test_handler/test_config_handler.py -q`
  → **48 passed** (33 pre-existing + 15 new), no regression. Run inside the worktree
  (`.claude/worktrees/agent-aa7976c489d514c1d/src/python`), not the main repo, so the
  freshly-added tests are exercised.
- `::ffff:8.8.8.8 → None` (mapped-public allowed) and the multi-address
  `[(public),(private)] → private/reserved` cases both pass — unmap-and-recheck behavior and
  the all-results loop are proven.
- `config.py` diff is empty (`git diff` shows only the test file changed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verify command path corrected to the worktree**
- **Found during:** Task 1
- **Issue:** The plan's `<verify>` command targets
  `/Users/julianamacbook/seedsyncarr/src/python` (the MAIN repo). Running there reported
  "not found: ...::TestValidateUrl" because the new test exists only in the worktree
  checkout — the main repo would have run stale code and produced a false RED.
- **Fix:** Ran pytest from the worktree path
  (`/Users/julianamacbook/seedsyncarr/.claude/worktrees/agent-aa7976c489d514c1d/src/python`)
  so the just-written test was actually exercised. No source change.
- **Files modified:** None.
- **Commit:** n/a

**2. [Rule 3 - Blocking] Poetry created a fresh worktree venv (locked deps only)**
- **Found during:** Task 1
- **Issue:** The worktree had no associated virtualenv, so the first `poetry run pytest`
  created `seedsyncarr-...-py3.12` and installed lockfile-pinned deps.
- **Fix:** Allowed — this is provisioning of already-committed, `poetry.lock`-pinned
  dependencies (explicitly permitted by the plan's notes), NOT a `poetry add` of a new/
  unverified package, so the Rule-3 slopsquat exclusion does not apply.
- **Files modified:** None tracked (venv is outside the repo).
- **Commit:** n/a

### Other Notes

- A pre-existing `PytestConfigWarning: Unknown config option: timeout / timeout_func_only`
  warning surfaces in the fresh worktree venv because `pytest-timeout` is not installed there.
  This is out of scope for this plan (the `TestValidateUrl` tests do not use timeouts) and was
  not "fixed" — logged here as an observation, not a deviation. The global `pyproject.toml`
  `timeout = 60` setting is unchanged.
- Per the objective, **STATE.md and ROADMAP.md were NOT modified** by this executor.

## Authentication Gates

None.

## Known Stubs

None. The tests stub `socket.getaddrinfo` (the mandated SSRF test pattern), but there are no
production-code stubs/placeholders — `config.py` was not modified, and `_validate_url` is the
real, complete guard under test.

## Threat Flags

None. No new network endpoints, auth paths, file-access patterns, or schema changes were
introduced. The plan's threat register (T-97-03-01 mitigate, T-97-03-02 / T-97-03-SC accept)
is fully addressed: T-97-03-01's SSRF mitigation is now covered by `TestValidateUrl`
(private/reserved IPv4+IPv6, mapped-private/loopback/link-local rejected, mapped-PUBLIC
allowed, multi-address-any-private rejected); T-97-03-02 (DNS-rebind/TOCTOU) remains
documented out-of-scope; T-97-03-SC (no new pip installs) holds — only stdlib `socket`/
`ipaddress` and existing test deps are used.

## Notes for Orchestrator

- COVMED-02 is fully covered; mark complete in REQUIREMENTS.md.
- No `config.py` source change was needed (D-01 recorded as a no-op). The branch-coverage
  gain in `web/handler/config.py:72-85` comes purely from the new tests exercising the loop,
  the four-check guard across IPv4/IPv6/mapped inputs, the gaierror catch, and the two early
  returns.

## Self-Check: PASSED

- Test class exists: FOUND `TestValidateUrl` in
  `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`
- Task 1 commit exists: FOUND `fbecf34`
- Task 1 verify gate: PASSED (15 passed, RED-first → all green against unmodified config.py)
- Task 2 verify gate (full file, no regression): PASSED (48 passed)
- config.py unchanged (outcome 1): CONFIRMED (no source edit; D-01 fix recorded unnecessary)
