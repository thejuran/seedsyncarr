# Phase 114: Scanner Auto-Recovery - Research

**Researched:** 2026-06-21
**Domain:** Python multiprocessing scanner/controller error-handling resilience (bounded retry + bounded auto-restart) in the SeedSyncarr backend
**Confidence:** HIGH (every recommendation grounded in the actual `src/python/` source and existing test suite read this session)

## Summary

Phase 114 is a tightly-scoped regression fix that wires bounded recovery into infrastructure that already exists in `src/python/`. The 2026-06-19 incident proved the gap: a transient DNS blip resolving `moon.usbx.me` produced a name-resolution `SshcpError`, which `RemoteScanner.scan()` classified `recoverable=False`, `ScannerProcess.run_loop()` re-raised, it propagated up to `seedsyncarr.py run()` where the `AppError` catch (with `args.exit=False`) set `status.server.up=False` and did NOT restart the controller. The scanner stayed dead for ~2 days. [VERIFIED: source read — `sshcp.py:22`, `remote_scanner.py:99-101`, `scanner_process.py:96-98`, `seedsyncarr.py:182-190`]

The fix has two halves on the same error path. **Recovery half (SCAN-01/02):** treat name-resolution failures as transient and add a bounded in-scan retry that retries name-resolution failures ONLY — wrapping BOTH the main scan SSH call AND the install-path SSH operations (md5sum check + copy) so a blip at startup or after an auto-restart (when `__install_done` is false) also recovers. **Safety half (SCAN-03/RECOV-01):** on retry exhaustion, surface exactly as today (`recoverable=False` → byte-for-byte the same `server.up=False` + `error_msg`); and route a permanent-class controller death through the existing `ServiceRestart` path with a consecutive-restart cap and a stayed-up reset, falling through to today's surface after the cap. [VERIFIED: source read; CITED: CONTEXT.md D-01/D-02/D-03]

**Install-path coverage (codex HIGH finding):** `scan()` calls `_install_scanfs()` BEFORE the main scan call whenever `__install_done` is false — which is precisely true at startup and after EVERY auto-restart. `_install_scanfs` converts a name-resolution `SshcpError` to `ScannerError(recoverable=self._is_transient_ssh_error(e))` → `recoverable=False` for a name-resolution string. If the bounded retry were scoped to the main scan call only, a startup/post-restart DNS blip would bypass the retry, kill the controller, AND burn RECOV-01 restart budget — defeating the milestone. The fix therefore applies the SAME bounded, name-resolution-ONLY retry policy to the install-path SSH ops via ONE shared retry helper. Timeout/connection-refused on the install path keep their existing immediate-classification behavior (`recoverable=self._is_transient_ssh_error(e)`, recovered on the next interval), so the existing install md5sum/copy timeout tests and the install/df exact call-count tests stay green unchanged (their errors are not name-resolution, so the retry gate is False and they raise on the first attempt). [VERIFIED: `remote_scanner.py:84-86, 149-187`; the install md5sum/copy timeout + call-count tests]

**Matcher coverage across resolver-string surfaces (codex HIGH finding, this rewrite):** The name-resolution matcher must cover ALL resolver-string surfaces the SSH layer can actually present at the `RemoteScanner` layer — not only the collapsed `Bad hostname:`. There are TWO distinct surfaces, and only one of them collapses:
1. **Collapsed surface:** the two pexpect expect indices that LITERALLY match a resolver string — index 3 (`Could not resolve hostname`) and index 5 (`Name or service not known`) — are caught inside `__run_command` and re-raised as the single string `"Bad hostname: {host}"` (`sshcp.py:97-98, 128-129`). For these two literally-matched indices, the only string seen downstream is `"Bad hostname:"`.
2. **Raw fallthrough surface:** when the ssh/scp child process exits non-zero WITHOUT one of those expect patterns having matched first, the non-zero-exit branch at `sshcp.py:151-155` raises the RAW `sp.before.decode().strip()` string with NO collapse. So a resolver output that arrives on a plain non-zero exit (e.g. `ssh: Could not resolve hostname moon.usbx.me: Temporary failure in name resolution`) reaches `RemoteScanner` as raw text. The existing SSH contract proves these raw surfaces are real and varied: `test_sshcp.py:108-115` (copy) and `:172-178` (shell) accept bad-host errors whose lower-cased text contains `bad hostname`, `could not resolve`, `name or service not known`, or `temporary failure`. If the matcher only knew `Bad hostname:`, those real resolver strings would be non-retryable on BOTH the main scan and the newly-wrapped install md5sum/copy path — a startup or post-restart DNS blip on those platforms/SSH outputs would raise immediately as non-recoverable, kill the controller, and burn the RECOV-01 restart budget despite the shared helper. The matcher therefore covers, at minimum, `Bad hostname:`, `Could not resolve hostname`, `Name or service not known`, and `Temporary failure in name resolution`, matched CASE-INSENSITIVELY (the raw fallthrough casing varies across SSH versions; `test_sshcp.py` itself asserts on `str(...).lower()`), while still excluding timeout/refused/auth/host-key errors. [VERIFIED: `sshcp.py:97-98, 128-129, 151-155`; `test_sshcp.py:108-115, 172-178`]

The single most important architectural insight from reading the code: the existing `__first_run` "retry across scan intervals" mechanism is NOT the bounded retry D-02 asks for. Today, a `Timed out` error after first run sets `recoverable=True`, `run_loop()` swallows it into a failed `ScannerResult`, and the NEXT scan interval (~30s later) retries. That is a 30-second-cadence implicit retry, not a seconds-scale bounded recovery window. D-02 wants a tight in-`scan()` loop (seconds) so a blip recovers within a single scan cycle and never produces a failed result at all. [VERIFIED: `scanner_process.py:95-113`, `remote_scanner.py:104-107`]

**Scoping note (in-scan retry is name-resolution ONLY, on both the scan and install paths):** The bounded in-scan retry covers name-resolution failures ONLY (every resolver-string surface — they fail fast). Transient timeout / connection-refused errors are deliberately NOT retried in-scan on EITHER path: each can block for up to the Sshcp 180s per-command timeout, so retrying them inside a single `scan()` would stack multiple 180s windows and stall the scanner for minutes — violating the existing first-run and install timeout/refused behavior. Those keep their existing immediate-raise (main scan: recoverable per `__first_run`; install: recoverable per `_is_transient_ssh_error`) and recover on the next ~30s scan interval. `_is_transient_ssh_error` therefore stays referenced ONLY inside the immediate-raise recoverability classification (`__to_scanner_error` for the main scan; the existing `_install_scanfs` except for install), never in the in-scan retry gate. [VERIFIED: `sshcp.py` 180s `__TIMEOUT_SECS`; the existing first-run and install timeout/refused tests; aligns with 114-01-PLAN's name-resolution-only invariant]

**Primary recommendation:** Add a bounded retry inside `RemoteScanner` (ONE shared private helper) wrapping the SSH `shell()` scan call AND the install-path md5sum `shell()` + `copy()` calls; reclassify name-resolution failures as transient via a NEW dedicated pattern set + helper (lowest blast radius — do NOT move `"Bad hostname:"` out of `PERMANENT_ERROR_PATTERNS` globally). The new tuple covers ALL resolver-string surfaces (collapsed `Bad hostname:` AND the raw fallthrough `Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`), matched case-insensitively; the in-scan retry gate is `_is_name_resolution_ssh_error` ONLY; on exhaustion the main-scan path raises `ScannerError(REMOTE_SERVER_SCAN, recoverable=False)` and the install path surfaces via its UNCHANGED except as `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)` (unchanged surfaces); add a consecutive-restart counter + stayed-up reset around the `seedsyncarr.py run()` `AppError` catch that raises `ServiceRestart()` until the cap, then falls through to today's `server.up=False` surface. Keep all bounds as hardcoded module/class constants.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSH name-resolution error classification (SCAN-01) | `ssh/sshcp.py` (pattern tuples + new helper) | `controller/scan/remote_scanner.py` (consumes helper) | Classification is already centralized at the SSH layer; reclassification belongs where the patterns live |
| Bounded in-scan retry (SCAN-02, D-02) | `controller/scan/remote_scanner.py` — ONE shared helper wrapping `scan()`'s main SSH call AND `_install_scanfs()`'s md5sum/copy SSH ops | — | D-02 locks the retry "inside the scan attempt"; the install path runs inside the same `scan()` call (before the main SSH call when `__install_done` is false), so the shared helper covers both. This is the one piece of genuinely new code |
| Exhaustion surface (SCAN-03) | `controller/scan/scanner_process.py` `run_loop()` re-raise → `seedsyncarr.py` `AppError` catch | `common/status.py` `ServerStatus.up`/`error_msg` | The surface (`recoverable=False` → propagation → `server.up=False`) already exists; preserve it byte-for-byte on both the scan-exhaustion (`REMOTE_SERVER_SCAN`) and install-exhaustion (`REMOTE_SERVER_INSTALL`) paths |
| Bounded controller auto-restart (RECOV-01, D-03) | `seedsyncarr.py` `run()` `AppError` catch + outer `main()` loop | `common/error.py` `ServiceRestart` | The `ServiceRestart`→`main()`→`continue` machinery already implements full restart; add only the counter/cap/reset |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Retry-then-surface.** Treat all name-resolution failures (`Bad hostname:` / `Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`) as **transient first** and retry with bounded backoff. The bounded retry **is** the test that distinguishes a blip from a real misconfiguration — no up-front heuristic guessing. On exhaustion, surface exactly as today. Satisfies SCAN-01 + SCAN-02 + SCAN-03 together. Consequence if wrong: a real config typo takes N×backoff longer to surface (bounded seconds) — acceptable.
- **D-02 — Bounded retry lives inside the scan attempt** (`remote_scanner.scan()` / `scanner_process.run_loop()`), NOT across scan-interval ticks. One scan cycle = one bounded recovery window (seconds). The install path runs inside `scan()` (when `__install_done` is false), so it is part of "the scan attempt" and shares the same bounded retry. There is NO existing retry/backoff helper in `src/python/` — this is the one new piece of small code. Keep defaults **hardcoded** (UI-configurable counts are Out of Scope). Exact attempt cap + backoff schedule are Claude's discretion, grounded in research.
- **D-03 — Capped consecutive restarts with a stayed-up reset.** On permanent-class controller death, auto-restart via the existing `ServiceRestart` path up to a fixed number of **consecutive** times (e.g. ~3). A run that stays up past a threshold **resets** the consecutive counter. After the cap, fall through to **today's** behavior (`server.up=False` + error surfaced) — no infinite restart loop. Exact cap + reset threshold are Claude's discretion.

### Claude's Discretion

- Exact retry attempt cap, backoff schedule (fixed/exponential, jitter), per-attempt sleep ceiling for D-02.
- Exact consecutive-restart cap and "stayed-up-long-enough" reset threshold for D-03.
- Whether the scan-path retry and the controller-restart bound share a small helper or stay separate (as long as both are bounded and testable). 114-01 factors the scan + install name-resolution retry into ONE shared helper.
- Test approach (existing pytest suite is the regression net throughout).

### Deferred Ideas (OUT OF SCOPE)

- UI-configurable retry counts / backoff — hardcoded defaults only.
- Health/alerting/notification on scanner death — separate concern.
- New scanner/SSH transport — reuse existing infrastructure, no rewrite.
- `webob-cgi-upstream-unblock` todo — upstream-blocked, unrelated.
- Live NAS deploy verification as a gate — QEMU-blocked, deferred.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCAN-01 | A transient name-resolution failure (`Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution` / momentary `Bad hostname`) is classified **recoverable** so the scanner retries. | Add a `NAME_RESOLUTION_ERROR_PATTERNS` tuple (covering the collapsed `Bad hostname:` AND the raw-fallthrough resolver substrings) + a CASE-INSENSITIVE `_is_name_resolution_ssh_error()` helper in `sshcp.py`/`remote_scanner.py`; treat as transient inside the new shared retry helper (used by both the main scan call and the install ops). Lowest-blast-radius approach (Pattern 1 below). |
| SCAN-02 | Recoverable scan failures are retried with **bounded backoff** — capped attempts, never infinite. | New bounded retry (Pattern 2) inside `RemoteScanner`, gating on name-resolution ONLY, shared by the main scan call and the install md5sum/copy ops. Recommended: 3 attempts, exponential backoff 1s→2s→4s with ±20% jitter, ≤4s per-attempt ceiling. Constants on `RemoteScanner`. |
| SCAN-03 | On exhaustion (genuinely wrong host / bad credentials), surface to the user **exactly as today** (`server.up=False` + error message). | On exhaustion the main-scan path raises `ScannerError(REMOTE_SERVER_SCAN, recoverable=False)` and the install path surfaces via its UNCHANGED except as `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)` — identical to today's surfaces, for the collapsed AND raw resolver surfaces; the existing `run_loop()` re-raise → `propagate` chain → `seedsyncarr.py:186-187` path is preserved byte-for-byte (Pattern 3). |
| RECOV-01 | Permanent-class controller death **auto-restarts** via the existing `ServiceRestart` path, itself bounded so an unrecoverable condition is not a restart loop. | Wrap `seedsyncarr.py run()` `AppError` catch with a consecutive-restart counter + stayed-up reset; raise `ServiceRestart()` until cap, then fall through to today's surface (Pattern 4). Recommended cap 3, reset threshold 5 minutes uptime. |

## Standard Stack

No new external packages. This phase uses only the Python standard library already in use and the project's own modules.

### Core (already present — no install)
| Module/Symbol | Location | Purpose | Why Reuse |
|---------|----------|---------|-----------|
| `time.sleep` | stdlib (already imported in `app_process.py`, `seedsyncarr.py`) | Backoff sleeps | Standard; but see Pitfall 1 — must honor terminate Event |
| `random` | stdlib | Backoff jitter | Standard; `random.uniform` for ±jitter |
| `TRANSIENT_ERROR_PATTERNS` / `PERMANENT_ERROR_PATTERNS` | `ssh/sshcp.py:17,22` | SSH error classification | Centralized classification already exists |
| `_is_transient_ssh_error` / `_is_permanent_ssh_error` | `remote_scanner.py:18-28` | Substring matchers | Reuse; add a sibling CASE-INSENSITIVE `_is_name_resolution_ssh_error`. `_is_transient_ssh_error` stays in the immediate-raise recoverability classification (`__to_scanner_error` for the main scan; the existing `_install_scanfs` except for install) ONLY — it is NOT part of the in-scan retry gate (finding 2). |
| `ScannerError(message, recoverable=...)` | `scanner_process.py:13-22` | Recoverable/fatal flag already gates `run_loop()` | Exhaustion just raises `recoverable=False` |
| `ServiceRestart` | `common/error.py:14-18` | Restart signal caught by `main()` | RECOV-01 routes into this existing path |
| `ServerStatus.up` / `error_msg` | `common/status.py:105-112` | The SCAN-03 surface | Preserve; do not replace |

### Supporting (testing — already present)
| Module | Location | Purpose | When to Use |
|--------|----------|---------|-------------|
| `unittest.mock` (`patch`, `MagicMock`, `side_effect`) | stdlib | Mock `Sshcp` at `controller.scan.remote_scanner.Sshcp` | All retry unit tests |
| `pytest-timeout` (`@pytest.mark.timeout`) | dev dep `>=2.3.1` | Bound any test touching real timers/sleeps | Process/timer tests (60s global default) |
| `unittest.mock.patch` on `time.sleep` | stdlib | Make backoff sleeps instant in tests | Retry timing tests — patch `remote_scanner.time.sleep` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `NAME_RESOLUTION_ERROR_PATTERNS` + helper (recommended) | Move `"Bad hostname:"` from `PERMANENT_` to `TRANSIENT_ERROR_PATTERNS` | Global blast radius: `_is_transient_ssh_error` is also used by `_install_scanfs` (`remote_scanner.py:164,186`) and the `__first_run` gate (`:106`). Moving it changes classification everywhere, risking that a genuinely-wrong host never surfaces fatal. REJECTED. |
| New tuple covering ALL resolver-string surfaces (collapsed + raw fallthrough), case-insensitive | A single `("Bad hostname:",)` prefix tuple | REJECTED (codex HIGH, this rewrite) — only the two literally-matched pexpect indices collapse to `Bad hostname:`; the non-zero-exit fallthrough (`sshcp.py:155`) raises the RAW `sp.before`, so raw resolver strings (`Could not resolve hostname`, `Name or service not known`, `Temporary failure in name resolution`) reach `RemoteScanner` un-collapsed. A `Bad hostname:`-only tuple would leave those non-retryable on both paths, so a startup/post-restart DNS blip on those platforms still kills the controller and burns RECOV-01 budget. The existing `test_sshcp.py` contract (:108-115, :172-178) already accepts all of these. |
| New helper + in-loop name-resolution-only handling on BOTH the scan and install paths | Also retry transient (timeout/refused) inside the new helper | REJECTED — transient errors can each block up to the Sshcp 180s per-command timeout; retrying them in-scan stacks multiple 180s windows and stalls the scanner for minutes, and would break the existing first-run AND install timeout/refused tests. Keep them on their existing immediate-raise + next-interval recovery path. |
| ONE shared retry helper wrapping the scan call AND the install md5sum/copy ops | A scan-only retry loop, leaving the install path untouched | REJECTED (codex HIGH) — the install path runs at startup and after every auto-restart (when `__install_done` is false); leaving it untouched means a startup/post-restart DNS blip bypasses the retry, kills the controller, and burns RECOV-01 budget. Sharing one helper gives both paths identical retry/backoff/exhaustion semantics with one implementation. |
| Hardcoded constants on `RemoteScanner` | `Constants` class (`common/constants.py`) | `Constants` holds cross-cutting app constants; scan-retry tuning is scanner-local. Convention favors class-level mangled `__UPPER` constants on `RemoteScanner` (see `Sshcp.__TIMEOUT_SECS`, `AppProcess.__DEFAULT_TERMINATE_TIMEOUT_MS`). Use scanner-local constants; reserve `Constants` for the restart cap if it reads more naturally there. |

**Installation:** None. No `pip install`. No package legitimacy audit required (zero external packages added).

## Package Legitimacy Audit

Not applicable — this phase installs **no external packages**. All code uses the Python standard library and existing project modules. (slopcheck gate skipped: no new dependencies.)

## Architecture Patterns

### System Architecture Diagram

```
                         RemoteScanner.scan()  [SCAN-01/02/03 — recovery happens HERE]
                         ┌───────────────────────────────────────────────────────────┐
 scan interval tick ───► │  if not __install_done:                                    │
 (ScannerProcess         │     _install_scanfs()  ── md5sum shell() + copy() each go   │
  .run_loop)             │       through the SAME shared name-resolution retry helper; │
                         │       a name-resolution blip recovers in the bounded window,│
                         │       exhaustion re-raises SshcpError → the EXISTING        │
                         │       _install_scanfs except → ScannerError(INSTALL,        │
                         │       recoverable=False). Timeout/refused NOT retried.      │
                         │                                                             │
                         │  for attempt in 1..MAX_RETRIES (shared helper):            │
                         │     try: out = ssh.shell(scanfs ...)  ──► success ─────────┼──► (files, total, used)
                         │     except SshcpError as e:                                │        ▲ recovered blip
                         │        if NOT name-resolution: raise __to_scanner_error ───┼──┐     never reaches
                         │            (transient timeout/refused, permanent, and      │  │     propagation
                         │             SystemScannerError all immediate-raise here    │  │
                         │             with the existing __first_run-aware value)      │  │
                         │        if name-resolution (collapsed OR raw):              │  │
                         │            if attempt < MAX:  sleep(backoff w/ jitter); ───┼──┘ (loop)
                         │                                continue                    │  │
                         │            else (exhausted):  raise recoverable=F ─────────┼──┐
                         └───────────────────────────────────────────────────────────┘  │
                                                                                          ▼  SCAN-03 surface
 ScannerProcess.run_loop:  except ScannerError: if not recoverable: raise  ───────────────┐  (unchanged)
 ScanManager.propagate_exceptions ──► Controller.__propagate_exceptions ──► ControllerJob │
 .execute (exc captured in Job.exc_info) ──► ControllerJob.propagate_exception re-raises  │
                                                                                          ▼
 seedsyncarr.py run() main loop:                                                          │
 ┌──────────────────────────────────────────────────────────────────────────────────────┘
 │  try: controller_job.propagate_exception()
 │  except AppError as exc:        [RECOV-01 — restart bound wraps HERE]
 │     if args.exit: raise
 │     else:
 │        if consecutive_restarts < CAP and not args.exit:
 │            consecutive_restarts += 1
 │            raise ServiceRestart()  ──► outer main() catches ──► continue ──► full re-init
 │        else:                                          (rebuilds controller + scanner)
 │            status.server.up = False      ◄── today's surface, after cap exhausted
 │            status.server.error_msg = str(exc)
 │
 │  (stayed-up reset: if a run survives > RESET_THRESHOLD_SECS since last restart,
 │   reset consecutive_restarts = 0 — implemented in the outer main() loop, see Pattern 4)
```

A reader can trace the DNS-blip use case: a blip during the startup install (md5sum/copy) or mid-scan enters at an `ssh` call, the shared helper sleeps and retries (name-resolution only — for ANY resolver-string surface), the host resolves, the install completes / `scan()` returns files — propagation is never reached. A genuinely-wrong host: the helper exhausts → install raises `ScannerError(INSTALL, recoverable=False)` or scan raises `ScannerError(SCAN, recoverable=False)` → propagation → controller dies → first death triggers `ServiceRestart` → re-init scan also exhausts → eventually cap reached → today's `server.up=False` surface. A transient timeout/refused: NOT retried in-scan on either path — immediate-raise with the existing recoverable value, recovers on the next ~30s scan interval.

### Recommended file touch map (no new files for source; one or two new test files)
```
src/python/
├── ssh/sshcp.py                          # ADD NAME_RESOLUTION_ERROR_PATTERNS tuple (collapsed + raw resolver substrings, lower-case)
├── controller/scan/remote_scanner.py     # ADD case-insensitive _is_name_resolution_ssh_error + ONE shared bounded retry helper used by scan()'s main call AND _install_scanfs()'s md5sum/copy ops
├── seedsyncarr.py                        # ADD consecutive-restart counter + reset around AppError catch / main() loop
└── tests/unittests/
    ├── test_ssh/test_sshcp.py                              # extend (or test in remote_scanner)
    ├── test_controller/test_scan/test_remote_scanner.py   # ADD main-scan + install-path retry-recovers / retry-exhausts / bounded / timeout-unchanged tests (collapsed AND raw resolver strings)
    └── test_seedsyncarr.py                                 # ADD restart-cap / stayed-up-reset tests
```

### Pattern 1: Name-resolution reclassification (SCAN-01) — lowest blast radius
**What:** Add a NEW dedicated pattern tuple + helper rather than moving `"Bad hostname:"` between the existing tuples. The tuple covers ALL resolver-string surfaces (collapsed + raw fallthrough); the helper matches case-insensitively.
**When to use:** SCAN-01 classification.
**Why:** `"Bad hostname:"` must STAY in `PERMANENT_ERROR_PATTERNS` so that all other consumers (`_install_scanfs` recoverability at `remote_scanner.py:164,186`, and the `__first_run` strictness gate at `:106`) keep treating it as permanent UNLESS the new shared retry helper has explicitly decided to retry it. The retry helper becomes the single place that knows "name-resolution is retryable up to N times" — for both the scan and install ops.

```python
# ssh/sshcp.py — ADD alongside the existing tuples (sshcp.py:17-22)
# Name-resolution failures: transient at the retry layer (DNS blips), but still
# PERMANENT at the classification layer so they surface fatal once retries exhaust.
# "Bad hostname:" intentionally appears in BOTH PERMANENT_ERROR_PATTERNS and here
# (permanent unless the bounded retry helper chooses to retry it — Phase 114 D-01).
# The raw resolver substrings are ALSO here because the non-zero-exit fallthrough
# (sshcp.py:155) raises the RAW sp.before un-collapsed, so these strings reach the
# RemoteScanner layer verbatim. Entries are lower-case for case-insensitive matching.
NAME_RESOLUTION_ERROR_PATTERNS = (
    "bad hostname:",
    "could not resolve hostname",
    "name or service not known",
    "temporary failure in name resolution",
)
```
```python
# controller/scan/remote_scanner.py — ADD a sibling CASE-INSENSITIVE matcher (remote_scanner.py:18-28)
from ssh import (Sshcp, SshcpError, TRANSIENT_ERROR_PATTERNS,
                 PERMANENT_ERROR_PATTERNS, NAME_RESOLUTION_ERROR_PATTERNS)

@staticmethod
def _is_name_resolution_ssh_error(error: SshcpError) -> bool:
    """Name-resolution failures are retried by the bounded helper (DNS blips) on
    both the scan and install paths, then surface fatal on exhaustion. Covers BOTH
    the collapsed "Bad hostname:" (pexpect indices 3/5) AND the raw fallthrough
    resolver strings (sshcp.py:155 raw sp.before), matched case-insensitively.
    Disjoint from timeout/refused/auth/host-key. See Phase 114 D-01."""
    msg = str(error).lower()
    return any(pattern in msg for pattern in NAME_RESOLUTION_ERROR_PATTERNS)
```
**Note on the actual error strings (CORRECTED — codex HIGH, this rewrite):** There are TWO surfaces and only one collapses. (1) The pexpect expect indices that LITERALLY match — index 3 (`Could not resolve hostname`) and index 5 (`Name or service not known`) — are caught inside `__run_command` and BOTH re-raised as the single message `"Bad hostname: {host}"` (`sshcp.py:97-98, 128-129`). (2) The non-zero-exit fallthrough at `sshcp.py:151-155` raises the RAW `sp.before.decode().strip()` string with NO collapse — so a resolver output arriving on a plain non-zero exit (e.g. `ssh: Could not resolve hostname moon.usbx.me: Temporary failure in name resolution`) reaches the `RemoteScanner` layer verbatim. Therefore the strings seen at the `RemoteScanner` layer for a name-resolution failure are EITHER `"Bad hostname:"` (collapsed) OR a raw resolver string containing `Could not resolve hostname`, `Name or service not known`, or `Temporary failure in name resolution`. Matching the single `"Bad hostname:"` prefix is INSUFFICIENT — the tuple must include the raw substrings, and the matcher must be case-insensitive. The existing SSH contract confirms exactly this accepted set: `test_sshcp.py:108-115` and `:172-178` accept bad-host errors whose lower-cased text contains `bad hostname`, `could not resolve`, `name or service not known`, or `temporary failure`. [VERIFIED: `sshcp.py:97-98, 128-129, 151-155`; `test_sshcp.py:108-115, 172-178`]

**Disjointness check (do NOT broaden over-eagerly):** None of the transient/auth/host-key strings is a substring of any name-resolution pattern, even case-insensitively: `"timed out"`, `"connection refused"`, `"incorrect password"`, and `"remote host key has changed"` do not appear within `"bad hostname:"`, `"could not resolve hostname"`, `"name or service not known"`, or `"temporary failure in name resolution"`. So timeout/refused/auth/host-key keep their existing classification + immediate-raise behavior; the retry gate stays name-resolution-ONLY. The full substring `"temporary failure in name resolution"` (not the bare `"temporary failure"`) is used so the tuple does not over-match an unrelated "temporary failure" from a non-resolver subsystem while still satisfying the `test_sshcp.py` contract (whose accepted `"temporary failure"` substring is contained within it).

### Pattern 2: Bounded retry shared by the scan call and the install ops (SCAN-02, D-02)
**What:** Wrap the SSH scan call in `RemoteScanner.scan()` AND the install-path md5sum `shell()` + `copy()` ops in `_install_scanfs()` with ONE shared bounded retry helper. Retry on `_is_name_resolution_ssh_error` ONLY; never retry transient timeout/refused, `SystemScannerError`, or other permanent errors inside the helper.
**When to use:** Inside `RemoteScanner.scan()`, wrapping the single `self.__ssh.shell(scanfs ...)` call at `remote_scanner.py:88-92`; and inside `_install_scanfs()`, wrapping the md5sum `self.__ssh.shell(...)` at `:155` and the `self.__ssh.copy(...)` at `:180`. The existing `try/except SshcpError` blocks at each site are KEPT — they now receive only a non-name-resolution error (first attempt) or a name-resolution error that exhausted the bound.

```python
# controller/scan/remote_scanner.py — class-level constants (convention: __UPPER mangled)
class RemoteScanner(IScanner):
    __SCAN_MAX_ATTEMPTS = 3          # total attempts incl. the first (bounded — D-02)
    __SCAN_BACKOFF_BASE_SECS = 1.0   # 1s, 2s, 4s exponential
    __SCAN_BACKOFF_CEILING_SECS = 4.0
    __SCAN_BACKOFF_JITTER = 0.2      # ±20%
```
```python
# ONE shared helper. The retry gate is name-resolution ONLY (any resolver surface,
# case-insensitive). On a non-retryable error OR name-resolution exhaustion the helper
# RE-RAISES the original SshcpError so each caller's own except converts it on its own
# path (main scan → __to_scanner_error / REMOTE_SERVER_SCAN; install → REMOTE_SERVER_INSTALL).
# The helper itself NEVER builds a ScannerError, so each path keeps its own localized
# message + recoverable rule, and SCAN-03 stays byte-for-byte on both.
def __ssh_call_with_name_resolution_retry(self, ssh_call, op_label):
    for attempt in range(1, self.__SCAN_MAX_ATTEMPTS + 1):
        try:
            return ssh_call()
        except SshcpError as e:
            self.logger.warning("Caught an SshcpError during %s (attempt %d/%d): %s",
                                op_label, attempt, self.__SCAN_MAX_ATTEMPTS, str(e))
            if not self._is_name_resolution_ssh_error(e):
                raise                       # transient/permanent/SystemScannerError
            if attempt < self.__SCAN_MAX_ATTEMPTS:
                self.__sleep_backoff(attempt)   # honors terminate — see Pitfall 1
                continue
            raise                           # name-resolution exhausted — re-raise
```
```python
# scan() main-call integration (replaces remote_scanner.py:88-111):
try:
    out = self.__ssh_call_with_name_resolution_retry(
        lambda: self.__ssh.shell("{} {}".format(
            shlex.quote(self.__remote_path_to_scan_script),
            shlex.quote(self.__remote_path_to_scan))),
        "main scan")
except SshcpError as e:
    if self._is_name_resolution_ssh_error(e):          # exhausted name-resolution (collapsed OR raw)
        raise ScannerError(
            Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
            recoverable=False)                          # SCAN-03 byte-for-byte
    raise self.__to_scanner_error(e)                   # transient/permanent/system
```
```python
# _install_scanfs() integration — KEEP the existing except blocks; only wrap the SSH ops:
#   md5sum:  out = self.__ssh_call_with_name_resolution_retry(
#                    lambda: self.__ssh.shell("md5sum {} | awk '{{print $1}}' || echo".format(
#                        shlex.quote(self.__remote_path_to_scan_script))), "scanfs install md5sum")
#   copy:    self.__ssh_call_with_name_resolution_retry(
#                    lambda: self.__ssh.copy(local_path=..., remote_path=...), "scanfs install copy")
# Each existing `except SshcpError as e:` still raises
#   ScannerError(REMOTE_SERVER_INSTALL.format(str(e).strip()),
#                recoverable=self._is_transient_ssh_error(e))
# → recoverable=False for any resolver string (none in TRANSIENT_), recoverable=True for "Timed out" (unchanged).
```
The `__to_scanner_error` helper preserves the EXACT existing recoverable rules from `remote_scanner.py:95-111` for the main-scan non-retried (immediate raise) branch — including the `__first_run` interaction AND the transient-on-first-run `recoverable=True` value (see Pitfall 4). The install path keeps its own existing `recoverable=self._is_transient_ssh_error(e)` rule. `_is_transient_ssh_error` lives ONLY inside those two classification sites — never in the `retryable` gate.

**Backoff defaults rationale (grounded in norms):**
- **Attempt cap = 3** (1 initial + 2 retries). [VERIFIED: industry norm — AWS SDKs default to 3 total attempts / `maxAttempts` for standard retry mode; Google Cloud client libraries default to a small number of retries; both cap total attempts in the low single digits]
- **Exponential backoff with full/equal jitter**, base 1s: 1s → 2s → 4s. [VERIFIED: the canonical AWS Architecture Blog "Exponential Backoff And Jitter" recommends exponential backoff WITH jitter over fixed delay to avoid synchronized retry storms; even for a single-client tool jitter is cheap insurance]
- **Per-attempt ceiling ≤ 4s**, so even at max the total added latency for a genuinely-wrong host is ≤ ~3s of sleeps (1s + 2s), well within the 60s pytest-timeout and well under the 30s `interval_ms_remote_scan` so a recovered blip stays inside one scan cycle's "feel." Because only fast-failing name-resolution is retried, the worst-case in-scan latency is just these backoff sleeps — never a stack of 180s SSH timeouts — on both the scan and install ops. [VERIFIED: `seedsyncarr.py:336` `interval_ms_remote_scan = 30000`]
- A DNS blip like the 2026-06-19 incident (host resolved ~2 min later per the debug session) will NOT recover within a 3-attempt/~3s window — and that is correct: it exhausts, surfaces, and RECOV-01's controller auto-restart (with its own re-init scan attempts and longer cadence) becomes the recovery mechanism for multi-minute outages. The two bounds compose: seconds-scale in-scan retry for sub-10s blips, restart-scale recovery for minutes-scale outages. [CITED: debug/resolved/seedbox-files-not-showing.md — "host resolved fine ~2 min later"]

### Pattern 3: Exhaustion surface preservation (SCAN-03)
**What:** On exhaustion, the main-scan path raises `ScannerError(Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()), recoverable=False)` — identical to today's permanent-error raise at `remote_scanner.py:108-111`; the install path re-raises the original `SshcpError` so the UNCHANGED `_install_scanfs` except produces `ScannerError(Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()), recoverable=self._is_transient_ssh_error(e))` (False for every resolver string) — identical to today's install-error raise at `:162-165` / `:184-187`. This holds for the collapsed `Bad hostname:` AND for any raw resolver string.
**Why byte-for-byte:** The downstream chain is unchanged and already correct: `run_loop()` re-raises non-recoverable (`scanner_process.py:96-98`) → `propagate_exception` → `Controller.__propagate_exceptions` (`controller.py:755`) → captured in `Job.exc_info` (`job.py:40-44`) → `ControllerJob.propagate_exception` re-raises → `seedsyncarr.py:183` `AppError` catch → `status.server.up=False` + `error_msg=str(exc)` (`:186-187`). The observable surface (`server.up`, `error_msg`, the localized message format) MUST NOT change on either path so real config errors still stop and prompt. [VERIFIED: full chain read this session]

### Pattern 4: Bounded controller auto-restart (RECOV-01, D-03)
**What:** Add a consecutive-restart counter and a stayed-up reset around the `AppError` catch in `seedsyncarr.py run()` and the outer `main()` loop.
**When to use:** The `except AppError` block at `seedsyncarr.py:184-190` (currently sets `server.up=False`, never restarts) and the `main()` restart loop at `:511-523`.

The cleanest place: the counter and reset threshold live in `main()` (the only code that survives a `ServiceRestart`, since `run()` returns/raises and a fresh `Seedsyncarr()` is constructed each loop). `run()` needs to know "am I allowed to restart?" — pass that in, or track restart bookkeeping in `main()` and have `run()` raise `ServiceRestart()` only when permitted.

Recommended shape (counter + timestamp in `main()`; `run()` decides restart-vs-surface based on a passed-in budget):
```python
# seedsyncarr.py main() — restart bookkeeping survives across ServiceRestart
__RESTART_CAP = 3                     # consecutive auto-restarts before giving up
__RESTART_RESET_SECS = 300           # a run that stays up 5 min resets the counter

def main():
    consecutive_restarts = 0
    last_start = None
    while True:
        try:
            app = Seedsyncarr()
            last_start = datetime.now()
            # tell run() how much restart budget remains
            app.run(restart_budget=(consecutive_restarts < __RESTART_CAP))
        except ServiceExit:
            break
        except ServiceRestart:
            # stayed-up reset: if the prior run survived long enough, reset the count
            if last_start and (datetime.now() - last_start).total_seconds() > __RESTART_RESET_SECS:
                consecutive_restarts = 0
            consecutive_restarts += 1
            Seedsyncarr.logger.info("Restarting (consecutive=%d/%d)...",
                                    consecutive_restarts, __RESTART_CAP)
            continue
        except Exception:
            Seedsyncarr.logger.exception("Caught exception")
            raise
```
```python
# seedsyncarr.py run() — the AppError catch decides restart vs. surface
except AppError as exc:
    if self.context.args.exit:
        raise
    if restart_budget:
        Seedsyncarr.logger.warning("Controller died; auto-restarting via ServiceRestart")
        raise ServiceRestart()          # ← routes into the EXISTING restart machinery
    # Cap exhausted → today's surface, unchanged
    self.context.status.server.up = False
    self.context.status.server.error_msg = str(exc)
    Seedsyncarr.logger.exception("Caught exception (restart budget exhausted)")
```
> **Plan refinement note (114-02-PLAN supersedes the snippet above):** The implemented design evaluates the decision AT FAILURE TIME inside `run()` using the CURRENT run's age (not a `restart_budget` bool precomputed in `main()` before `app.run()`), via a pure `_should_auto_restart(consecutive, cap, current_run_start, reset_secs, now) -> (should_restart, reset_applied)` helper; and `ServiceRestart` carries keyword-only `auto`/`reset` flags so `main()` can NORMALIZE the counter to 1 (a fresh budget) on a reset-at-cap auto restart (finding 2) and so UI restarts never burn the auto budget (finding 1). The snippet above is the conceptual shape; 114-02-PLAN.md is authoritative for the exact wiring.

**Critical correctness notes:**
- The `except Exception` block at `run()` `:199` already re-raises after terminating jobs (`:224`). A `ServiceRestart` raised from inside the `try` will be caught by that outer `except Exception`, the jobs are terminated/joined, persisted, then re-raised — and `main()` catches it. This is exactly how the existing UI-triggered restart at `:194` works, so RECOV-01 reuses a proven path. [VERIFIED: `seedsyncarr.py:193-224, 511-523`]
- **Reset semantics:** D-03 says "a run that stays up past a threshold resets the counter." The reset is computed from the CURRENT run's age at failure time and, on a reset-at-cap restart, normalizes the next counter to 1 (a fresh budget — finding 2). This makes intermittent failures (one death every few hours) recover indefinitely, while a tight restart loop (deaths within 5 min of each restart) hits the cap quickly.
- **Falls through to today's behavior, not a crash:** once the budget is genuinely exhausted, the code path is byte-for-byte the current `:186-188`. No new crash surface. [VERIFIED]
- **Recommended cap 3, reset 300s.** [VERIFIED: small-cap restart norm — systemd's `StartLimitBurst` defaults to 5 starts within `StartLimitIntervalSec=10s`; a cap of 3 with a 5-minute "healthy run" reset is conservative for a self-hosted single-user tool and avoids log churn while giving multi-minute outages several restart-driven retry windows]

### Anti-Patterns to Avoid
- **Moving `"Bad hostname:"` out of `PERMANENT_ERROR_PATTERNS`:** global blast radius — breaks `_install_scanfs` and `__first_run` permanence. Use a dedicated tuple instead.
- **Matching only `"Bad hostname:"` in the name-resolution tuple:** only the two literally-matched pexpect indices collapse to that string; the non-zero-exit fallthrough (`sshcp.py:155`) raises raw resolver text (`Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`). A `Bad hostname:`-only tuple leaves those non-retryable on both paths, so a startup/post-restart DNS blip on those platforms still kills the controller and burns RECOV-01 budget (codex HIGH). Cover all resolver surfaces, case-insensitively.
- **Case-sensitive matching of the raw resolver strings:** the raw fallthrough casing varies across SSH versions (`test_sshcp.py` asserts on `.lower()`). The name-resolution matcher must lower-case the message before comparing.
- **Scoping the bounded retry to the main scan call only, leaving the install path untouched:** the install path runs at startup and after every auto-restart (when `__install_done` is false), so a name-resolution blip there bypasses recovery, kills the controller, and burns RECOV-01 budget (codex HIGH). The shared retry helper MUST also wrap the install md5sum/copy SSH ops.
- **Retrying transient timeout/refused inside the retry helper:** each can block up to the 180s Sshcp per-command timeout, so stacking them inside one `scan()` stalls the scanner for minutes and breaks the existing first-run AND install timeout/refused tests. The in-scan retry gate is name-resolution ONLY; transient keeps its immediate-raise + next-interval recovery.
- **Bare `time.sleep(backoff)` in the retry helper:** blocks shutdown responsiveness; the scanner process can't honor its terminate Event during the sleep. Use the Event-aware wait (Pitfall 1) or a low ceiling with a documented tradeoff.
- **Putting the retry across scan intervals (in `run_loop`) instead of inside `scan()`:** violates D-02 and would mean a blip still produces a failed `ScannerResult` that briefly surfaces. Keep it inside `scan()` (which includes the install path).
- **Infinite restart loop:** RECOV-01 explicitly requires a cap. Never `raise ServiceRestart()` unconditionally.
- **Changing the localized error message or `server.up`/`error_msg` semantics:** breaks SCAN-03's "exactly as today" contract on either the scan-exhaustion or install-exhaustion path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Restart orchestration | A new supervisor thread / process monitor | The existing `ServiceRestart` → `main()` `continue` loop (`seedsyncarr.py:194,511-523`) | Full restart (terminate jobs, join, persist, re-init) is already implemented and battle-tested; RECOV-01 adds only a counter |
| Recoverable/fatal signaling | A new exception type or status field | The existing `ScannerError(recoverable=...)` flag (`scanner_process.py:13-22`) | Already gates `run_loop()` re-raise-vs-continue |
| SSH error classification | New regex parsing of pexpect output | The existing pattern tuples + substring matchers (`sshcp.py`, `remote_scanner.py:18-28`) | Centralized; just add one tuple (covering collapsed + raw resolver surfaces) + one case-insensitive matcher |
| Error surfacing to UI | A new error channel | `status.server.up` / `error_msg` (`common/status.py:105-112`) | The exact SCAN-03 surface; reuse don't replace |
| Two separate retry loops for scan vs install | A scan loop + a copy/install loop | ONE shared `__ssh_call_with_name_resolution_retry(...)` helper wrapping any SSH callable | Identical retry/backoff/exhaustion semantics with a single implementation; both paths stay in lockstep |
| Shutdown-aware sleep | `time.sleep` + signal hacks | `self._terminate.wait(timeout=...)` on the process's existing Event (`app_process.py:48`) | Event.wait returns early when set — see Pitfall 1 |

**Key insight:** Nearly everything Phase 114 needs already exists. The genuinely new code is ~one bounded retry helper in `RemoteScanner` (name-resolution-only, shared by the scan call and the install md5sum/copy ops), one pattern tuple + matcher, and one counter/reset block in `main()`/`run()`. Resist inventing new mechanisms — the CONTEXT and STATE both stress "wire together infrastructure already present."

## Common Pitfalls

### Pitfall 1: `time.sleep` in the scan path blocking shutdown responsiveness
**What goes wrong:** A naive `time.sleep(backoff)` inside the shared retry helper blocks the scanner child process. While sleeping, the process cannot observe its terminate Event, so `ScannerProcess.terminate()` (which sets `_terminate` then waits up to `__DEFAULT_TERMINATE_TIMEOUT_MS = 1000`ms before SIGTERM) will hit the force-terminate timeout on every shutdown during a backoff. [VERIFIED: `app_process.py:96-111` — terminate sets the Event then polls for 1s before `super().terminate()`]
**Why it happens:** The retry helper runs inside `scan()` (including the install path), which is called from `ScannerProcess.run_loop()` in the child process. `time.sleep` is uninterruptible by the Event.
**How to avoid:** The cleanest fix is to make the backoff wait on the process terminate Event so it returns early on shutdown. `RemoteScanner` does NOT currently hold a reference to the process's `_terminate` Event — two options:
- (a) Keep backoff sleeps short (ceiling ≤ ~4s) and accept that worst-case shutdown adds one sleep duration. Simple, but can exceed the 1s terminate poll → force-kill. Acceptable for correctness (force-terminate is safe) but noisy.
- (b) **Recommended:** pass a "should-abort" callable or the terminate Event down into `RemoteScanner` (set in `set_base_logger`/a new setter wired from `ScannerProcess.run_init`), and implement backoff as `if abort_event.wait(timeout=delay): raise ScannerError(..., recoverable=False)` — returns immediately on terminate. This keeps total backoff small AND honors shutdown. Note the spawn caveat: `multiprocessing.Event` is retained across spawn pickling per `AppProcess.__getstate__` (`app_process.py:124-128`), so passing the Event is spawn-safe.
**Warning signs:** Tests that assert `terminate()` returns quickly start timing out; shutdown logs show "Process received terminate flag" delayed; CI `@pytest.mark.timeout` flakes on process tests.
**Planner guidance:** Pick (a) for minimal change if backoff ceiling is kept ≤ ~2s; pick (b) for correctness. Given the locked seconds-scale window, (a) with a low ceiling is defensible and far simpler — but the plan must state the choice explicitly and add a test that `scan()` aborts promptly when the Event is set (option b) OR a comment documenting the accepted force-terminate tradeoff (option a). [114-01-PLAN chose option (a) with a ≤4s ceiling, documented ONCE in the shared helper so it applies to both the scan and install paths.]

### Pitfall 2: Breaking the existing `__first_run` strictness semantics AND retrying the wrong error class
**What goes wrong:** The retry helper and `__first_run` gate interact. Today, before the first successful scan, a non-transient error is fatal (`remote_scanner.py:106-107`) so the user is prompted to fix config; after first success, transient errors are recoverable across intervals. If the new helper retries name-resolution on first run, that is actually DESIRED per D-01 (retry-then-surface applies regardless of first run). But the helper must NOT retry any OTHER error class in-scan — permanent errors (bad password, host-key change) AND transient timeout/refused must keep their existing behavior. Retrying transient timeout/refused in-scan is especially harmful: each can block up to the 180s Sshcp per-command timeout, so stacking them inside one `scan()` stalls the scanner for minutes and breaks the existing first-run AND install timeout/refused tests.
**Why it happens:** Easy to over-generalize the retry condition (e.g. `_is_transient_ssh_error OR _is_name_resolution_ssh_error`), OR to under-cover name-resolution (matching only `Bad hostname:` and missing the raw resolver fallthrough strings).
**How to avoid:** The in-scan retry gate is strictly `self._is_name_resolution_ssh_error(e)` (name-resolution ONLY), and that matcher covers ALL resolver-string surfaces case-insensitively (collapsed + raw fallthrough) while staying disjoint from timeout/refused/auth/host-key. `Timed out`, `Connection refused by server`, `Incorrect password`, and `Remote host key has changed` are NOT in `NAME_RESOLUTION_ERROR_PATTERNS` (and are not substrings of any entry), so they are re-raised by the helper on the first attempt and converted on whichever path raised them — the main scan via `__to_scanner_error(e)` (existing `__first_run`-aware value), the install via the existing `recoverable=self._is_transient_ssh_error(e)`. `_is_transient_ssh_error` is referenced ONLY inside those classification sites, never in the retry gate. Confirm with the existing tests `test_raises_recoverable_error_on_first_run_timeout`, `test_raises_recoverable_error_on_first_run_connection_refused`, `test_recovers_after_first_run_timeout` (asserts exactly 4 SSH calls), `test_raises_nonrecoverable_error_on_wrong_password_after_first_run`, `test_raises_nonrecoverable_error_on_host_key_change_after_first_run`, `test_raises_recoverable_error_on_md5sum_timeout`, and `test_raises_recoverable_error_on_copy_timeout` — they must all still pass UNCHANGED — plus the NEW matcher-excludes-timeout/refused/auth/host-key classification asserts.
**Warning signs:** Those existing first-run/install timeout/refused/password/host-key tests fail; a `test_recovers_after_first_run_timeout` 4-call count changes because a timeout was retried in-scan; or a bad-password scenario takes 3× backoff to surface; OR a raw `Could not resolve hostname` / `Temporary failure in name resolution` blip is NOT retried (matcher too narrow).

### Pitfall 3: `df` capacity is the only SSH op the retry helper must NOT wrap; install md5sum/copy NOW share the retry
**What goes wrong:** `scan()` makes THREE SSH-op kinds today: install (md5sum check `:155` + copy `:180`), the main scan (`:89`), and `df` capacity (`:138`). The shared retry helper must wrap the main scan call AND the two install ops (md5sum + copy) — but NOT `df`. `df` already has a silent-fallback that never raises fatal (`:143-145`), and retrying it adds no value. The existing call-count tests assert exact counts (e.g., `test_calls_correct_ssh_md5sum_command` asserts 3 calls; `test_recovers_after_first_run_timeout` asserts 4; `test_recovers_from_failed_ssh` asserts 6). Those counts are PRESERVED because every one of those tests uses timeout/permanent errors (or success), never name-resolution — so the retry gate is False, the helper re-raises on the first attempt, and the wrapped op is called exactly once per attempt as today. The retry helper changes call counts ONLY in the (new) name-resolution failure path, on either the scan or install op.
**Why it happens:** `scan()` (plus the install it calls) is multiple SSH ops; it is easy to either wrap `df` by accident or to re-run install/df when the OTHER op retries.
**How to avoid:** Wrap exactly three call sites in the shared helper: the main `self.__ssh.shell(scanfs ...)` at `:89-92`, the md5sum `self.__ssh.shell(...)` at `:155`, and the `self.__ssh.copy(...)` at `:180`. Leave `df` (`:138`) untouched. The helper retries ONLY the op it was handed — a main-scan name-resolution retry does NOT re-run md5sum/copy/df, and an install-op retry does NOT re-run the main scan or df. Re-run the existing call-count tests; their timeout/permanent errors keep the gate False so the counts are unchanged.
**Warning signs:** `test_calls_correct_ssh_*`, `test_recovers_*`, `test_recovers_from_failed_ssh` (asserts 6 calls), or the install md5sum/copy tests fail with off-by-N call counts.

### Pitfall 4: Preserving the immediate-raise recoverable value for non-retried errors
**What goes wrong:** When the helper hits a non-retryable error (transient timeout/refused, permanent, or `SystemScannerError`), the caller must raise with the SAME recoverable value the current code computes — which on the main scan depends on `__first_run` and the error class, and on install is `self._is_transient_ssh_error(e)`. If you hardcode `recoverable=False` for all immediate raises, you'd change behavior for the first-run-transient edge (transient after first run is `recoverable=True`) and for install timeouts (recoverable=True).
**How to avoid:** Factor the existing main-scan classification (`remote_scanner.py:95-111`) into a helper `__to_scanner_error(e)` that returns the correctly-flagged `ScannerError`, and call it for the main-scan immediate-raise branch (which now also covers transient timeout/refused, since those are not retried in-scan). Keep the install path's EXISTING except blocks (with `recoverable=self._is_transient_ssh_error(e)`) verbatim — do not refactor them; the shared helper simply re-raises the SshcpError into them. `_is_transient_ssh_error` lives inside `__to_scanner_error` AND the install excepts only. The main-scan exhaustion branch raises `recoverable=False` directly; the install exhaustion surfaces `recoverable=False` via the existing except (False for any resolver string). Keep these raise sites distinct.

### Pitfall 5: ruff whole-tree gate is separate from pytest
**What goes wrong:** A plan that only runs `pytest` passes locally but fails CI's `lint-python` gate, which runs `ruff check src/python/` on the WHOLE tree (default rules, no `[tool.ruff]` config). [VERIFIED: CONVENTIONS.md, TESTING.md, config — CI `lint-python` is a separate job]
**How to avoid:** Every task's verification must run BOTH `pytest` AND `ruff check src/python/` (whole tree). Watch for: unused imports (the new `NAME_RESOLUTION_ERROR_PATTERNS` import), unused locals, f-string vs `%`-logging consistency. Use lazy `%`-style logging in the helper (matches the codebase's logging convention and avoids ruff/perf flags).

### Pitfall 6: spawn vs fork (INFRA-01 history)
**What goes wrong:** macOS dev runs use the `spawn` start method (no explicit `set_start_method` in the codebase — platform default; Docker/Linux = fork). [VERIFIED: no `set_start_method` anywhere in `src/python/`] Under spawn, the scanner process and its scanner object are pickled. `RemoteScanner` is constructed in `ScanManager.__init__` and handed to `ScannerProcess`; if you add a `multiprocessing.Event` reference to `RemoteScanner` (Pitfall 1 option b), it pickles fine (Events are retained), but if you ever add a `threading.Thread` or other non-picklable attribute it would break spawn. The recent v1.4.2 mp-logger spawn-hang fix (commit af7f1e9) is the cautionary precedent.
**How to avoid:** Add only picklable attributes (constants, an Event, a callable referencing module-level functions) to `RemoteScanner`. Do NOT add Thread/Lock objects. If passing the terminate Event, wire it in `ScannerProcess.run_init()` (runs in the child after spawn) rather than relying on `__init__` state, consistent with the `__getstate__` guidance in `app_process.py:144-153`.
**Whether it matters here:** Mostly NO for the scan-retry helper (constants are spawn-safe). 114-01 chose Pitfall-1 option (a), so it adds NO new attribute to `RemoteScanner` and the spawn-pickle surface is unchanged. It would matter only if a future change chooses option (b); the plan should then note the spawn-safe wiring point (`run_init`).

## Code Examples

### Existing test harness — mock Sshcp, drive scan/install outcomes by call count
```python
# Source: src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py:22-26, 631-669
# Pattern: patch Sshcp at the import site; sequence shell() outcomes via a call counter;
# the install copy is driven separately via self.mock_ssh.copy.side_effect.
ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
self.addCleanup(ssh_patcher.stop)
self.mock_ssh = ssh_patcher.start().return_value

def ssh_shell(*args):
    self.ssh_run_command_count += 1
    if self.ssh_run_command_count == 1:      # md5sum install-check (install path)
        raise SshcpError("Bad hostname: somehost")   # install-time name-resolution blip (collapsed surface)
    else:                                    # later attempts succeed
        return json.dumps([]).encode()
self.mock_ssh.shell.side_effect = ssh_shell
```

### Raw-resolver-surface variant — drive the RAW fallthrough string (codex matcher-coverage finding)
```python
# The raw non-zero-exit fallthrough (sshcp.py:155) surfaces resolver text un-collapsed.
# New install/main-scan retry tests must exercise these raw strings, not only "Bad hostname:".
def ssh_shell_raw(*args):
    self.ssh_run_command_count += 1
    if self.ssh_run_command_count == 1:
        raise SshcpError("ssh: Could not resolve hostname moon.usbx.me: Temporary failure in name resolution")
    else:
        return b''   # md5sum mismatch / later attempt succeeds
self.mock_ssh.shell.side_effect = ssh_shell_raw
```

### Existing pattern — assert recoverable flag on the raised ScannerError
```python
# Source: test_remote_scanner.py:361-364
with self.assertRaises(ScannerError) as ctx:
    scanner.scan()
self.assertTrue(ctx.exception.recoverable)   # or assertFalse for exhaustion
```

### Existing pattern — patch time.sleep to make backoff instant
```python
# Recommended for the new retry tests (no existing precedent in this suite, but
# standard unittest.mock usage; patch at the module under test):
with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
    files, _, _ = scanner.scan()          # retries happen with zero real delay
    self.assertEqual(2, mock_sleep.call_count)  # 3 attempts → 2 backoff sleeps
```
Note: `remote_scanner.py` does not currently import `time`; the retry helper will add `import time` (stdlib, top of file per import-order convention). Patch `controller.scan.remote_scanner.time.sleep`.

### Existing pattern — main()/run() restart is exception-driven
```python
# Source: seedsyncarr.py:193-194 (UI restart) and 511-523 (main loop)
# The proven restart path RECOV-01 reuses:
if web_app_builder.server_handler.is_restart_requested():
    raise ServiceRestart()
# ... main():
except ServiceRestart:
    Seedsyncarr.logger.info("Restarting...")
    continue
```

## Runtime State Inventory

> This is a code-path regression fix, not a rename/refactor/migration. No stored data, service config, OS-registered state, secrets, or build artifacts carry any string this phase changes. The phase adds constants and a retry helper; it changes no identifiers, keys, collection names, env var names, or persisted formats.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by reading the change surface (no DB/datastore keys, no persist format change). The phase touches in-memory error classification and control flow only. | None |
| Live service config | None — verified. No external service (n8n, Datadog, Tailscale) configuration is involved; the scanner talks to the seedbox over SSH using existing `settings.cfg` fields, unchanged. | None |
| OS-registered state | None — verified. No Task Scheduler/launchd/systemd unit names change. The Docker container CMD and restart policy are untouched (RECOV-01 restarts in-process via `ServiceRestart`, not via the OS). | None |
| Secrets/env vars | None — verified. No secret key names or env var names referenced or changed. `remote_password`/`use_ssh_key` handling is untouched. | None |
| Build artifacts | None — verified. No package rename, no egg-info, no entry-point change (`seedsyncarr = "seedsyncarr:main"` in `pyproject.toml` unchanged). | None |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-delay retries | Exponential backoff WITH jitter | Long-standing (AWS "Exponential Backoff And Jitter" blog, widely adopted) | Jitter avoids synchronized retry storms; standard even for single-client retries |
| Unbounded retry-on-error | Bounded attempts (low single digits) + surface on exhaustion | Standard across AWS/GCP SDKs (default ~3 total attempts) | Prevents masking real failures; matches D-01/D-02 exactly |

**Deprecated/outdated:** Nothing in this phase relies on deprecated APIs. `pexpect`, stdlib `multiprocessing`, stdlib `logging`, and the project's own modules are all current and in active use.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended retry defaults (3 attempts, 1s→2s→4s exp backoff, ±20% jitter, ≤4s ceiling) | SCAN-02 / Pattern 2 | These are Claude's-discretion tunables grounded in norms; if too tight, a 5-10s blip exhausts and falls to RECOV-01 restart (still recovers, just slower). Low risk — bounded either way. User/planner may prefer different values. |
| A2 | Recommended restart cap 3, stayed-up reset 300s | RECOV-01 / Pattern 4 | Discretionary. Too-low cap surfaces prematurely; too-high churns logs. The reset makes intermittent failures recover indefinitely. Low risk — both fall through to today's safe surface. |
| A3 | Adding a `NAME_RESOLUTION_ERROR_PATTERNS` tuple is lower-blast-radius than moving `"Bad hostname:"` between tuples | Pattern 1 | Verified by tracing all consumers of `_is_transient_ssh_error`/`PERMANENT_ERROR_PATTERNS`; confidence HIGH. Minimal residual risk. |
| A4 | In-scan retry must be name-resolution ONLY (transient timeout/refused NOT retried in-scan) on both the scan and install paths | Summary / Pattern 2 / Pitfall 2 | Verified against the 180s Sshcp per-command timeout and the existing first-run AND install timeout/refused tests. Retrying transient in-scan would stack 180s windows and break those tests. Confidence HIGH — this is the locked invariant in 114-01-PLAN. |
| A5 | Pitfall-1 option (a) (short sleep, accept worst-case force-terminate) is acceptable vs option (b) (Event-aware wait) | Pitfall 1 | Option (a) can trip the 1s terminate poll → SIGTERM on shutdown-during-backoff. Functionally safe (force-terminate works) but noisy. 114-01-PLAN chose (a) with a ≤4s ceiling and a documented comment in the shared helper. Medium-ish operational risk, accepted. |
| A6 | The bounded name-resolution retry must cover the install path (md5sum/copy), not just the main scan call | Summary / Install-path coverage / Pattern 2 / Anti-Patterns | Verified (codex HIGH): `scan()` calls `_install_scanfs()` before the main SSH call when `__install_done` is false — true at startup and after every auto-restart. A scan-only retry would let a startup/post-restart blip kill the controller and burn RECOV-01 budget. Confidence HIGH. |
| A7 | The name-resolution matcher must cover ALL resolver-string surfaces (collapsed `Bad hostname:` AND the raw fallthrough `Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`), case-insensitively | Summary / Matcher coverage / Pattern 1 / Anti-Patterns | Verified (codex HIGH, this rewrite): only the two literally-matched pexpect indices collapse to `Bad hostname:`; the non-zero-exit fallthrough (`sshcp.py:155`) raises the raw `sp.before`. The existing `test_sshcp.py` contract (:108-115, :172-178) accepts all four lower-cased substrings. A `Bad hostname:`-only matcher leaves real resolver strings non-retryable on both paths. Confidence HIGH. |

## Open Questions

1. **Backoff shutdown-responsiveness: option (a) vs (b)?** — RESOLVED in 114-01-PLAN.
   - What we know: The scanner child process can't honor its terminate Event during a bare `time.sleep`. `AppProcess.terminate()` polls 1s before force-kill.
   - Decision: 114-01-PLAN chose option (a) — bare `time.sleep` with a ≤4s ceiling and a documented accepted-tradeoff comment in the ONE shared helper (avoids adding a spawn-pickled attribute to `RemoteScanner`). Because only fast-failing name-resolution is retried, the worst-case backoff stack is small (~3s) on both the scan and install paths.

2. **Where should the restart cap/reset constants live — `main()` module constants or `Constants`?** — RESOLVED in 114-02-PLAN.
   - What we know: `main()` is the only scope that survives `ServiceRestart`. Scanner constants belong on `RemoteScanner`.
   - Decision: Module-level constants in `seedsyncarr.py` next to `main()` (the restart logic is local to that file). `Constants` is used only if a value is referenced from more than one module (none are).

## Environment Availability

> Skipped per gating rule: this phase is code-only changes within `src/python/`. No NEW external tool/service/runtime is introduced. The test suite already runs under the existing Python/pytest/ruff toolchain inside the project's Docker test image (`make run-tests-python`), and the SSH integration tests use the container's bundled sshd. No new dependency to probe.

## Validation Architecture

> Nyquist validation is enabled (`.planning/config.json` has no `workflow.nyquist_validation: false`). Section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.3 with pytest-timeout >= 2.3.1, pytest-cov >= 7.0.0; tests are `unittest.TestCase` classes run by pytest |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (`pythonpath=["."]`, global `timeout=60`, `timeout_func_only=false`, `cache_dir=/tmp/.pytest_cache`) |
| Quick run command | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py tests/unittests/test_seedsyncarr.py -x` (or run inside the Docker test image) |
| Full suite command | `make run-tests-python` (Docker: `pytest -v -p no:cacheprovider` from `/src`) AND `ruff check src/python/` (separate CI gate) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCAN-01 | name-resolution is classified retryable by the new case-insensitive matcher / retried by the shared helper (scan + install) for ALL resolver surfaces (collapsed `Bad hostname:` AND raw `Could not resolve hostname` / `Name or service not known` / `Temporary failure in name resolution`) | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k name_resolution -x` | ❌ Wave 0 (add to existing file) |
| SCAN-02 | Bounded retry recovers on attempt N on the main-scan path; sleep called N-1 times; capped | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k retry_recovers -x` | ❌ Wave 0 |
| SCAN-02 | Bounded retry recovers on the INSTALL path (md5sum/copy) and is capped | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "install_name_resolution_recovers or install_name_resolution_bounded" -x` | ❌ Wave 0 |
| SCAN-02 | Retry is bounded — never more than MAX_ATTEMPTS calls on persistent failure (scan + install) | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "retry_bounded or install_name_resolution_bounded" -x` | ❌ Wave 0 |
| SCAN-02 | Transient timeout/refused is NOT retried in-scan on EITHER path (raises on attempt 1, sleep not called) | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "transient_timeout_not_retried_in_scan or install_timeout_unchanged" -x` | ❌ Wave 0 |
| SCAN-03 | Retry exhaustion raises `ScannerError(recoverable=False)` with the unchanged localized message (scan → REMOTE_SERVER_SCAN; install → REMOTE_SERVER_INSTALL), for collapsed AND raw resolver surfaces | unit | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -k "retry_exhausts or install_name_resolution_bounded" -x` | ❌ Wave 0 |
| SCAN-03 | Existing permanent-error AND first-run/install transient tests (wrong password, host-key change, SystemScannerError, first-run timeout/refused, md5sum/copy timeout, mangled output) still surface their existing recoverable value immediately; new matcher-excludes asserts confirm timeout/refused/auth/host-key are NOT name-resolution | unit (regression) | `pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py -x` | ✅ (must stay green) |
| RECOV-01 | First permanent-class controller death raises `ServiceRestart` (auto-restart) when budget remains | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_within_cap -x` | ❌ Wave 0 |
| RECOV-01 | After the cap, `AppError` falls through to `server.up=False` + `error_msg` (no `ServiceRestart`, no crash) | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_cap_exhausted -x` | ❌ Wave 0 |
| RECOV-01 | A run that stays up past the reset threshold resets the consecutive counter (fresh budget = 1) | unit | `pytest tests/unittests/test_seedsyncarr.py -k restart_reset -x` | ❌ Wave 0 |
| RECOV-01 | `ServiceRestart("restart requested")` preserves its message and defaults auto/reset to False (codex HIGH contract) | unit | `pytest tests/unittests/test_seedsyncarr.py tests/unittests/test_common/test_error.py -k "service_restart_flags or restart_message or message_preserved" -x` | ✅/❌ (test_common exists; seedsyncarr additions Wave 0) |
| (cross-cutting) | Whole-tree lint clean | lint | `ruff check src/python/` | ✅ (separate gate) |

### Sampling Rate
- **Per task commit:** the targeted quick run for the file(s) touched (`pytest <file> -x`) + `ruff check src/python/`.
- **Per wave merge:** `make run-tests-python` (full Python suite) + `ruff check src/python/`.
- **Phase gate:** Full Python suite green AND `ruff check src/python/` clean before `/gsd:verify-work`. No release/tag/version work.

### Wave 0 Gaps
- [ ] `tests/unittests/test_controller/test_scan/test_remote_scanner.py` — extend with retry-recovers / retry-exhausts / retry-bounded / name-resolution-classification / transient-not-retried-in-scan tests for the MAIN-SCAN path AND install-path (`__install_done=false`) name-resolution recover/bounded + install timeout-unchanged tests covering both the md5sum and copy SSH ops (covers SCAN-01/02/03). The classification AND retry tests MUST exercise the RAW resolver strings (`Could not resolve hostname`, `Name or service not known`, `Temporary failure in name resolution`) and a case-insensitive variant, not only `Bad hostname:`. Patch `controller.scan.remote_scanner.time.sleep`. Reuse the existing call-counter `ssh_shell` harness (`:631-669`) for md5sum/main-scan and `self.mock_ssh.copy.side_effect` for copy.
- [ ] `tests/unittests/test_seedsyncarr.py` — add restart-cap / cap-exhausted / stayed-up-reset / fresh-budget tests + ServiceRestart constructor-compatibility tests (covers RECOV-01). The current file tests static methods only; testing `main()`/`run()` restart bookkeeping needs either a refactor of the counter into a testable pure helper (recommended) or patching. **Planner note:** extracting the restart-budget decision into a small static/pure function (e.g. `_should_auto_restart(consecutive, cap, current_run_start, reset_secs, now)`) makes RECOV-01 unit-testable without spinning the full `run()` loop, mirroring how `_emit_startup_warnings`/`_detect_incomplete_config` are tested as static methods.
- [ ] No framework install needed — pytest/ruff/pytest-timeout already present.
- [ ] No new shared fixtures required — existing `tests/helpers` + inline mock-Sshcp harness suffice.

### Spawn-vs-fork test consideration
The new retry-helper unit tests run `scanner.scan()` directly (no process spawn) — start-method-agnostic. 114-01 chose Pitfall-1 option (a), so no Event is added to `RemoteScanner` and no process-level abort-during-backoff test is required. The existing `ScannerProcess` tests (`test_scanner_process.py`) DO spawn and are already `@pytest.mark.timeout(10)`-bounded; if a future change adopts option (b) and adds an Event to `RemoteScanner`, add one process-level test asserting prompt abort during backoff, and ensure any new `RemoteScanner` attribute is picklable (spawn-safe per `app_process.py:__getstate__`).

## Security Domain

> `security_enforcement` not disabled in config → included. This is a resilience/control-flow change with a thin security surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth code changed; SSH credential handling untouched |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (existing) | The scan + install commands already use `shlex.quote` on user-controlled paths (`remote_scanner.py:90-91,138,155` and the copy kwargs); the retry helper must NOT bypass that — it wraps the SAME quoted `shell()`/`copy()` calls via lambdas that close over the existing quoted strings. Do not reconstruct the command inside the helper. |
| V6 Cryptography | no | No crypto changed |
| V7 Error Handling & Logging | yes | Retry logs MUST keep using `sanitize_log_value` for any untrusted value, and must NOT log secrets. The new shared attempt-counter log line should log the error message (already non-secret SSH status, now possibly raw resolver text) and the op_label literal but never the password; sanitize any host/path value. Existing CWE-117 sanitization at `:124-126` stays. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Log injection (CR/LF) via remote-controlled error/path text in the new shared retry log line (now including raw resolver fallthrough text) | Tampering / Repudiation | Use `%`-style lazy logging and `sanitize_log_value` for any path/filename; the SSH error message strings are app-generated (`"Bad hostname: {host}"`, `"Timed out"`) or relayed resolver text — sanitize host/path values if logged. [VERIFIED: `sanitize_log_value` convention, CONVENTIONS.md Logging] |
| Command injection via remote path in the retried scan/install commands | Tampering | Already mitigated by `shlex.quote` (`:90-91,155`) and the `copy(local_path=, remote_path=)` kwargs; the retry helper reuses the same quoted calls via lambdas — must not rebuild them unquoted. Existing regression guard: `test_df_command_quotes_remote_path` (`test_remote_scanner.py:798-825`). |
| Denial of recovery via retry storm against the seedbox / stacked 180s timeouts | Denial of Service | In-scan retry is name-resolution ONLY (fast-failing) on both the scan and install paths, bounded (SCAN-02) + jittered backoff in the ONE shared helper; slow transient timeout/refused are NOT retried in-scan so a single scan() (incl. install) can never stack 180s waits. Bounded restarts (RECOV-01) prevent restart storms. This is the core design. |
| Masking a real config error (security-relevant: stale state) | — | SCAN-03 ensures real permanent errors still surface after bounds on both paths; retry never silently masks. The name-resolution matcher is disjoint from auth/host-key so a wrong password / changed host key is never retried as a "blip." |

## Sources

### Primary (HIGH confidence)
- Source files read this session (authoritative): `src/python/ssh/sshcp.py`, `controller/scan/remote_scanner.py`, `controller/scan/scanner_process.py`, `controller/scan_manager.py`, `controller/controller.py` (process/propagate), `controller/controller_job.py`, `seedsyncarr.py`, `common/error.py`, `common/status.py`, `common/app_process.py`, `common/job.py`, `common/constants.py`, `common/localization.py`, `pyproject.toml`.
- Test suite read this session: `tests/unittests/test_controller/test_scan/test_remote_scanner.py`, `test_scanner_process.py`, `test_controller_job.py`, `tests/unittests/test_ssh/test_sshcp.py`, `tests/unittests/test_seedsyncarr.py`, `tests/unittests/test_common/test_error.py`.
- `.planning/phases/114-scanner-auto-recovery/114-CONTEXT.md` (locked D-01/D-02/D-03, code_context, canonical_refs).
- `.planning/REQUIREMENTS.md` (SCAN-01/02/03, RECOV-01 acceptance + Out of Scope table).
- `.planning/STATE.md` (Phase 114 wiring notes, 2026-06-19 root cause).
- `.planning/debug/resolved/seedbox-files-not-showing.md` (authoritative reproduction with file:line traceback and the "host resolved ~2 min later" DNS-blip confirmation).
- `.planning/codebase/TESTING.md`, `CONVENTIONS.md`, `ARCHITECTURE.md` (pytest/ruff conventions, separate ruff gate, naming).

### Secondary (MEDIUM confidence — backoff/restart norms, verified against widely-cited sources)
- AWS Architecture Blog — "Exponential Backoff And Jitter" (canonical source for backoff-with-jitter recommendation).
- AWS SDK / Google Cloud client-library retry defaults (~3 total attempts, capped) — corroborating the low-single-digit attempt cap.
- systemd `StartLimitBurst`/`StartLimitIntervalSec` defaults (5 starts / 10s) — corroborating a conservative consecutive-restart cap + reset-window pattern.

### Tertiary (LOW confidence)
- None — all recommendations trace to either the read source/tests or widely-established backoff/restart norms.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every reused symbol confirmed by reading the source.
- Architecture / insertion points: HIGH — exact file:line for each integration point read and cross-checked against the debug traceback; install-path coverage (codex HIGH) verified against `scan()` → `_install_scanfs()` ordering; matcher resolver-surface coverage (codex HIGH) verified against `sshcp.py:97-98/128-129` collapse vs `:151-155` raw fallthrough and the `test_sshcp.py` accepted-substring contract.
- Pitfalls: HIGH — each pitfall derived from actual code behavior (terminate poll timing, call-count assertions, `__first_run` gate, 180s timeout, ruff separate gate, spawn `__getstate__`, the collapse-vs-fallthrough distinction).
- Backoff/restart specific values (A1/A2): MEDIUM — sound norms, but explicitly Claude's-discretion tunables flagged in the Assumptions Log for planner/user confirmation.

**Research date:** 2026-06-21
**Valid until:** 2026-07-21 (stable — internal codebase + stdlib; re-verify only if `seedsyncarr.py`/`remote_scanner.py`/`sshcp.py` change before planning)

## RESEARCH COMPLETE
