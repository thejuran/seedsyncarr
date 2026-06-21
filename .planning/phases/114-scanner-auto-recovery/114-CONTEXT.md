# Phase 114: Scanner Auto-Recovery - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The seedbox scanner survives transient DNS/network blips and recovers from controller death on its own, instead of silently freezing the file list for days until a manual container restart. Three cohesive behaviors on the same controller/scanner error-handling path:

1. **SCAN-01** — reclassify transient name-resolution failures (`Could not resolve hostname` / `Name or service not known` / a momentary `Bad hostname`) as recoverable so the scanner retries instead of dying.
2. **SCAN-02** — bounded backoff: a capped number of retry attempts, never an infinite loop.
3. **SCAN-03** — when retries are exhausted (genuinely wrong / persistently-unresolvable hostname, bad credentials), surface the failure to the user **exactly as today** (`server.up=False` + error message) so real config errors still stop and prompt — the retry path must never silently mask a permanent config error.
4. **RECOV-01** — a permanent-class controller death auto-restarts via the existing `ServiceRestart` path instead of staying down forever, itself bounded so an unrecoverable condition doesn't become a restart loop.

This **wires together infrastructure already present in `src/python/`** — no new transport, no new mechanisms invented. The scanner/SSH rewrite, UI-configurable retry counts, external alerting on scanner death, and live-NAS deploy gating are all explicitly out of scope (see REQUIREMENTS.md Out of Scope).
</domain>

<decisions>
## Implementation Decisions

### Transient vs. config-error disambiguation (SCAN-01, SCAN-03)
- **D-01:** **Retry-then-surface.** Treat all name-resolution failures (`Bad hostname:` / `Could not resolve hostname` / `Name or service not known`) as **transient first** and retry with bounded backoff. The bounded retry loop **is** the test that distinguishes a blip from a real misconfiguration — there is no up-front heuristic guessing whether the hostname is "really" wrong. A DNS blip recovers within the retry window (the 2026-06-19 incident: host resolved fine ~2 min later); a genuinely wrong hostname costs a few bounded retries and then stops, surfacing exactly as today. This single decision satisfies SCAN-01 (retry instead of die), SCAN-02 (bounded), and SCAN-03 (exhaustion surfaces unchanged) together.
  - **Consequence if wrong:** a real config typo takes N×backoff longer to surface than today (seconds, bounded) — an acceptable cost for never freezing on a blip.

### Where the bounded retry lives (SCAN-02)
- **D-02:** **Inside the scan attempt.** Wrap the SSH scan in a bounded retry loop within the scan path (`remote_scanner.scan()` / `scanner_process.run_loop()`), not across scan-interval ticks. On a transient/name-resolution failure: sleep with backoff, retry up to N times, then raise non-recoverable on exhaustion. One scan cycle = one bounded recovery window (seconds, not minutes). Recovery is tight to where the failure happens and is straightforward to unit-test in isolation.
  - **Note for planner:** there is **no existing retry/backoff helper** in `src/python/` — "retry" today is only the implicit scan-interval timer. This loop is the one piece of genuinely new (small) code; keep defaults hardcoded (REQUIREMENTS.md Out of Scope forbids UI-configurable counts). Choose sensible bounded defaults (attempt cap + backoff schedule) — exact values are Claude's discretion, grounded in research.

### Controller auto-restart bound (RECOV-01)
- **D-03:** **Capped consecutive restarts with a stayed-up reset.** On a permanent-class controller death, auto-restart via the existing `ServiceRestart` path up to a fixed number of **consecutive** times (e.g. ~3). A run that stays up past a threshold **resets** the consecutive-restart counter, so intermittent failures recover indefinitely over time. After the cap is hit, fall through to **today's** behavior (`server.up=False` + error surfaced) — no infinite restart loop on a genuinely unrecoverable condition.
  - **Consequence if wrong:** too low a cap surfaces a recoverable condition prematurely; too high churns logs. Counter + reset-threshold are the tunable knobs (hardcoded defaults; exact values Claude's discretion).

### Claude's Discretion
- Exact retry attempt cap, backoff schedule (fixed/exponential, jitter), and the per-attempt sleep ceiling for D-02 — pick sensible bounded defaults; research backoff norms for short-lived SSH/DNS retries.
- Exact consecutive-restart cap and the "stayed-up-long-enough" reset threshold for D-03.
- Whether the scan-path retry and the controller-restart bound share a small helper or stay separate — implementation detail, as long as both are bounded and testable.
- Test approach (the existing pytest suite is the regression net throughout).

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` (matched score 0.6, area: testing) — **not folded.** It's a webob/stdlib-`cgi` `PYTHONWARNINGS` cleanup blocked on upstream webob 2.0; unrelated to scanner/controller recovery and already tracked as a deferred/upstream-blocked item in STATE.md. Out of this phase's scope.
</decisions>

<specifics>
## Specific Ideas

- The 2026-06-19 incident is the canonical reproduction: at 02:44:51, a transient DNS failure resolving `moon.usbx.me` raised `SshcpError('Bad hostname: moon.usbx.me')`, classified permanent → `ScannerError(recoverable=False)` → propagated through `scanner_process.py` → `scan_manager.propagate_exceptions()` → `controller.__propagate_exceptions()` → `controller_job.execute()` → caught in `seedsyncarr.py run()` as `AppError` (with `args.exit=False`) → `status.server.up=False`, controller dead, web server alive, list frozen ~2 days until manual container restart. The fix must turn that exact trace into: retry the blip → recover; or, on a real permanent death, auto-restart via `ServiceRestart` → recover; only surface after bounds are exhausted.
- SCAN-03 anchor: "surface exactly as today" means the **same** observable outcome that exists now (`server.up=False` + `error_msg`) — do not invent a new error surface; the existing one is correct, it just must only fire after the retry/restart bounds are exhausted.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & milestone intent
- `.planning/REQUIREMENTS.md` — SCAN-01/02/03 + RECOV-01 acceptance criteria, and the Out of Scope table (no transport rewrite, no UI-configurable retries, no alerting, no NAS deploy gate).
- `.planning/ROADMAP.md` §"Phase 114: Scanner Auto-Recovery" + the v1.4.1 milestone block — phase goal and CI-gate note (Python suite green **AND** `ruff check src/python/` whole-tree clean; ruff is a **separate** CI gate from pytest).
- `.planning/STATE.md` §Decisions — the detailed Phase 114 wiring notes (which existing symbols to reuse) and the 2026-06-19 root-cause summary.

### Root-cause evidence
- `.planning/debug/resolved/seedbox-files-not-showing.md` — full resolved debug session: exact error, full propagation traceback with file:line, DNS-blip confirmation, and the eliminated alternatives. The authoritative reproduction.

### Existing infrastructure to wire (no rewrites — see code_context for file:line)
- `src/python/sshcp.py` — `TRANSIENT_ERROR_PATTERNS`, `PERMANENT_ERROR_PATTERNS`, `_is_transient_ssh_error` / `_is_permanent_ssh_error`; pexpect blocks that raise `SshcpError`.
- `src/python/remote_scanner.py` — `scan()` classification (~line 88-111), `__first_run` strictness gate.
- `src/python/scanner_process.py` — `ScannerError(recoverable=...)` (lines 13-22), `run_loop()` re-raise (lines 85-98).
- `src/python/scan_manager.py` — `propagate_exceptions` / `_check_process_health` / `ScannerProcessDiedError` (lines 146-200).
- `src/python/controller/controller.py` — `__propagate_exceptions()` (~line 750-757).
- `src/python/controller/controller_job.py` — `execute()` (~line 23-25).
- `src/python/seedsyncarr.py` — `run()` `AppError` catch (lines 183-190), `ServiceRestart` raise (~line 194), outer `main()` restart loop (~lines 511-523).
- `src/python/common/error.py` — `AppError` / `ServiceExit` / `ServiceRestart` hierarchy (lines 1-18).
- `src/python/common/status.py` — `ServerStatus.up` / `error_msg` (lines 105-112) — the SCAN-03 surface.

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`, `CONVENTIONS.md`, `TESTING.md` — backend structure, conventions, and the pytest/ruff regression-net conventions to follow.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Error classification is already centralized:** `sshcp.py` pattern tuples + `remote_scanner._is_transient_ssh_error` / `_is_permanent_ssh_error` substring matchers. SCAN-01 is a reclassification at this layer (move/treat name-resolution patterns as transient), not new detection.
- **The `recoverable` flag already exists** on `ScannerError` (`scanner_process.py:13-22`) and already gates re-raise-vs-continue in `run_loop()`. SCAN-02's exhaustion just raises `recoverable=False` after the bounded loop.
- **`ServiceRestart` + the outer `main()` loop already implement full restart** (`seedsyncarr.py:194` raise, `~511-523` catch → `continue`). RECOV-01 routes permanent-class controller death into this *existing* path, adding only the consecutive-restart bound/counter.
- **`status.server.up=False` + `error_msg`** (`common/status.py:105-112`, set at `seedsyncarr.py:186`) is the exact SCAN-03 surface to preserve — reuse, don't replace.

### Established Patterns
- Worker processes propagate exceptions via an exception queue (`app_process.py propagate_exception()`); the controller drains them in `__propagate_exceptions()`. The retry must sit **below** this propagation (inside the scan) so a recovered blip never reaches propagation at all (D-02).
- `__first_run` strictness gate exists in `remote_scanner.py` — D-01 deliberately does NOT lean on it for name-resolution failures (retry-then-surface applies regardless of first run), but the planner should confirm the interaction so first-run behavior for *other* permanent errors (bad password, host-key change) stays unchanged.

### Integration Points
- Scan retry loop: `remote_scanner.scan()` / `scanner_process.run_loop()` (D-02).
- Controller restart bound: the `AppError`-catch / `ServiceRestart` region of `seedsyncarr.py run()` + outer `main()` loop (D-03).
- Regression surface: `status.server.up` / `error_msg` must remain byte-for-byte the same observable outcome on exhaustion (SCAN-03).
</code_context>

<deferred>
## Deferred Ideas

- UI-configurable retry counts / backoff — explicitly Out of Scope (REQUIREMENTS.md); hardcoded defaults only.
- Health/alerting/notification on scanner death — separate concern, Out of Scope.
- New scanner/SSH transport — Out of Scope; reuse existing infrastructure.
- `webob-cgi-upstream-unblock` todo — upstream-blocked, unrelated to this phase (see Reviewed Todos above).

</deferred>

---

*Phase: 114-scanner-auto-recovery*
*Context gathered: 2026-06-21*
