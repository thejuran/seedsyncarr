# Phase 112: Defensive Guards & Code Hardening - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

> The user dismissed the gray-area discussion (declined the AskUserQuestion), signalling comfort
> with spec-grounded defaults rather than re-deciding mechanics the Phase 110 FINDINGS artifact
> already constrains tightly — the same posture taken in Phase 110. The decisions below are
> therefore **locked, evidence-grounded defaults** drawn from `110-FINDINGS.md` (HR-02..HR-07),
> the INFRA-01 spawn-fix precedent (Phase 107), `REQUIREMENTS.md` GUARD-01..06, and direct reads
> of the touched source files. The planner/researcher implement to these without re-asking.

<domain>
## Phase Boundary

A **defensive-guards / code-hardening cluster** delivering the six GUARD requirements
(GUARD-01..06) that Phase 110's hostile-reader pass folded into this phase. All six are
**independent small fixes** — no shared architecture, no breaking changes. Each closes a
launch-visible "vibe-coded" tell a skeptical r/selfhosted engineer would flag:

- **GUARD-01** (HR-03): non-loopback-bind-without-`api_token` startup warning — prominence gap.
- **GUARD-02** (HR-03): webhook-without-secret startup warning — warning-**correctness** gap in the
  `empty webhook_secret` + `webhook_require_secret=True` state.
- **GUARD-03** (HR-04): logged delete-path failures — replace `ignore_errors=True` so a failed
  local delete leaves an observable log signal.
- **GUARD-04** (HR-02): the red test — `AppProcess` must create its queue/event from a
  spawn-compatible context so `test_app_process.py::test_process_with_long_running_thread_terminates_properly`
  goes green under `spawn`, with **no test deleted or skipped**.
- **GUARD-05** (HR-07): `.gitignore` the two stray tooling artifacts (`.orchestrator.json`,
  `.playwright-mcp/`).
- **GUARD-06** (HR-06): legacy `~/.seedsync` fallback warning must actually reach the operator
  (it currently fires before the logger is configured).

**Scope discipline:** All six are confirm-and-fix items — the FINDINGS pass already verified each
is real and correctly targeted. Most are *prominence/correctness/observability* gaps on code that
**already exists**, not build-from-scratch features. No new capabilities. No config-set/CFG work
(that is Phase 111, shipped). No presentation/LAUNCH work (Phase 113).

**CI gates that must hold (this is a code phase):** Python `fail_under` ≥ 88; Angular Karma
`check.global` floors stmts/branches/fns/lines 83/68/79/83 (Angular untouched here but stays green);
full suite green on **amd64 + arm64**, under **both `fork` and `spawn`** start methods (GUARD-04).
**No release/tag/version work** — the single `v1.4.0` tag is a milestone-end action on branch
`launch-hardening`, never inside a phase.

</domain>

<decisions>
## Implementation Decisions

### GUARD-04 — AppProcess spawn-context fix (HR-02, the red test; highest-visibility item)
- **D-01:** Mirror the **INFRA-01 precedent** (`common/multiprocessing_logger.py`, Phase 107) as the
  canonical pattern. Create the unpicklable multiprocessing primitives from a **shared `spawn`
  context** rather than the bare top-level `Queue()`/`Event()`: introduce a module/class-level
  `multiprocessing.get_context("spawn")` and build `self.__exception_queue = ctx.Queue()` and
  `self._terminate = ctx.Event()` from it (replacing `app_process.py:47-48` and the top-level
  `from multiprocessing import Process, Queue, Event` import as needed).
- **D-02:** **Decision required by the planner — `AppProcess` differs structurally from MP-logger.**
  `AppProcess` *subclasses* `Process`, so when `.start()` is called the **whole instance is pickled**
  to the spawn child (MP-logger was only an *argument*, so its `__getstate__`/`__setstate__` shim
  sufficed). The planner/researcher must determine, against a live `spawn` repro, whether a
  spawn-context `Queue`/`Event` alone makes the instance picklable, or whether `AppProcess` also
  needs a `__getstate__`/`__setstate__` pair (and/or to construct/own the context such that the
  child can re-acquire it). **Acceptance bar (non-negotiable, from GUARD-04):** the existing
  `test_process_with_long_running_thread_terminates_properly` (`test_app_process.py:175`) passes
  under `spawn` with **nothing deleted or skipped**, and the full suite stays green under `fork`
  too (Linux default). Behavior of `terminate()`/`propagate_exception()` is preserved.
- **D-03:** Do **not** globally `set_start_method("spawn")` — the fix is local to `AppProcess`'s own
  primitives (same blast-radius discipline INFRA-01 used). The default start method per platform is
  unchanged; only `AppProcess`'s queue/event become spawn-safe.

### GUARD-01 / GUARD-02 — Startup-warning prominence + correctness (HR-03)
- **D-04:** **Confirm-the-gap, not build-from-scratch.** Both warnings already exist in
  `seedsyncarr.py::_emit_startup_warnings` (lines 372-397) and are tested
  (`test_seedsyncarr.py:210-228`). Scope is *correcting* and *raising prominence*, not adding a
  feature. The `_emit_startup_warnings` call site (run() line 120, after logger setup) is correct
  and stays — these warnings already reach the configured logger.
- **D-05 (GUARD-02 correctness — the real defect):** Fix the misleading message in the
  `empty webhook_secret` + `webhook_require_secret=True` state. Today the **first** warning
  ("Webhook endpoints will accept requests from any caller", line 375-378) fires *unconditionally*
  whenever `webhook_secret` is empty — but when `webhook_require_secret=True` the handler actually
  **fails closed with 503** (`web/handler/webhook.py:54-60`). **Default fix:** make the
  accept-any-caller warning conditional so it fires **only when the endpoint actually accepts
  unauthenticated callers** — i.e. `not webhook_secret and not webhook_require_secret`. The
  fail-closed state (`not webhook_secret and webhook_require_secret`) emits **only** the accurate
  "rejected with 503" message (lines 379-383). Net: each of the four cells in the HR-03 matrix
  produces exactly one accurate message (or none when authenticated). Planner may instead merge to a
  single state-aware message if cleaner, provided no cell is misleading.
- **D-06 (GUARD-01 prominence):** The `api_token` warning text is already accurate (the app
  hardcodes `0.0.0.0` bind in `web_app_job.py:27`, so "any host on the network can access the API"
  is true). The only gap is **prominence**. Keep it `logging.warning` (consistent with the codebase's
  warning convention and the existing tests) but make it **visually unmissable in the log stream** —
  e.g. a bracketed `SECURITY` prefix / separator line, matching whatever the other startup warnings
  adopt for consistency. **Do not** escalate to raising/exiting or interactive prompts — GUARD-01's
  contract is explicit: *"the default behavior is unchanged, the unsafe posture is no longer silent."*
- **D-07:** Update/extend the existing `test_seedsyncarr.py` warning tests to pin the corrected
  GUARD-02 matrix (assert the accept-any-caller line does **not** fire in the fail-closed state, and
  the 503 line does) — test-first where feasible, reusing the existing warning-test harness.

### GUARD-03 — Logged delete-path failures (HR-04)
- **D-08:** Replace `shutil.rmtree(file_path, ignore_errors=True)` (`delete_process.py:24`) with a
  call that **logs** failures instead of swallowing them, while remaining **best-effort** (a partial
  failure logs and continues — it does not raise out of the one-shot delete process). **Default:**
  pass an error callback (`onexc` on Python ≥ 3.12, falling back to the deprecated-but-present
  `onerror` for the project's 3.11 runtime — planner confirms the runtime Python version and picks
  the supported kwarg) that logs each failed path with context via `self.logger.error(...)` /
  `self.logger.exception(...)`. A simpler `try/except OSError` wrapping `rmtree(path)` (no
  `ignore_errors`) with a single `logger.exception` is an acceptable alternative if per-entry
  granularity is judged unnecessary — the binding requirement (GUARD-03) is only that *a failed
  delete leaves an observable signal in the logs*, not that every entry is itemized.
- **D-09:** **Do not** change the delete *outcome* contract: the local delete remains best-effort and
  non-fatal (matching today's behavior — the sync tool must not crash because one cleanup failed).
  Mirror the existing remote-delete path (`DeleteRemoteProcess.run_once`, lines 46-50), which already
  uses `try/except SshcpError` + `self.logger.exception(...)` — that is the in-repo precedent for the
  log-and-continue shape. Sanitize any interpolated path/filename through the existing
  `sanitize_log_value()` helper (Phase 101, `common/types.py`) if it reaches a log line, consistent
  with the SEC-01 log-injection convention already applied across the controller/delete cluster.
- **D-10:** Add a regression test for the failure path (FINDINGS notes "no test cases for the failure
  path") — e.g. a `rmtree` that raises is observed to produce a log record rather than a silent
  swallow. Keep Python `fail_under` ≥ 88.

### GUARD-06 — Legacy `~/.seedsync` fallback surfacing (HR-06)
- **D-11:** **Root cause is ordering, not a missing warning.** The fallback warning
  (`seedsyncarr.py:268-271`) fires inside `_parse_args` (called at line 40) **before**
  `_create_logger` (line 74) — so it goes to an unconfigured root logger and disappears. **Default
  fix:** keep the *fallback behavior* unchanged (silent auto-fallback to `~/.seedsync` is preserved),
  but make the warning **actually reach the operator** by emitting it through a channel that works
  pre-logger. Preferred: surface the legacy-fallback decision **after** `_create_logger` runs (carry
  a flag/return value out of `_parse_args` and emit via the configured `logger.warning` near the
  other startup warnings), so it lands in the same log stream as GUARD-01/02. A direct
  `print(..., file=sys.stderr)` at the call site is an acceptable fallback if threading the flag
  through is awkward — the binding requirement (GUARD-06) is only that the operator gets a *visible*
  signal.
- **D-12:** Do **not** implement the "gate behind explicit opt-in" alternative GUARD-06 permits — the
  loud-warning path is lower-risk, preserves backward-compatible auto-fallback, and matches the
  posture of GUARD-01/02 (warn, don't change default behavior). Add/extend a test asserting the
  warning is emitted when the fallback triggers.

### GUARD-05 — `.gitignore` tooling artifacts (HR-07) — mechanical, no gray area
- **D-13:** Add `.orchestrator.json` and `.playwright-mcp/` to `.gitignore`, alongside the existing
  `.aidesigner/*`, `.bg-shell/`, `.turingmind/`, `.DS_Store` entries (which already follow this
  pattern). Verify with `git status` that neither artifact appears as untracked afterward. Both are
  currently present untracked in the working tree — confirm neither is already committed (FINDINGS
  confirms both are untracked). Pure repo hygiene; no code, no test impact.

### Ordering / waves (planner guidance, not locked)
- **D-14:** The six items are mutually independent and can be planned as parallel waves. GUARD-04
  (spawn fix) is the highest-value/highest-risk item (it touches a base class every worker process
  subclasses and must hold under both start methods) — sequence it so its full-suite-under-both-start-
  methods verification is not blocked by the cosmetic items. GUARD-05 is trivial and can land first.

### Claude's Discretion
- Exact warning prefix/format chosen for prominence (D-06), provided it is consistent across the
  startup warnings and stays at `logging.warning` level.
- Whether GUARD-03 uses `onexc`/`onerror` callback granularity vs. a single `try/except` wrap (D-08),
  provided a failed delete is observably logged.
- Whether GUARD-06 threads a flag out of `_parse_args` vs. emits to stderr at the call site (D-11),
  provided the operator gets a visible signal.
- Whether GUARD-04 needs `__getstate__`/`__setstate__` in addition to the spawn context (D-02) —
  decided by the planner against a live `spawn` repro, against the green-test acceptance bar.

</decisions>

<specifics>
## Specific Ideas

- The maintainer is sensitive to "vibe-coded" criticism (Phase 110 framing). The single most
  launch-visible item here is **GUARD-04's red test** — a new contributor running `poetry run pytest`
  on macOS hits a `TypeError: cannot pickle '_thread.lock' object` failure immediately. Turning that
  green is the highest-signal outcome of this phase.
- Prefer **in-repo precedent over novelty** for every fix: GUARD-04 mirrors INFRA-01's
  `get_context("spawn")` pattern; GUARD-03 mirrors the existing `DeleteRemoteProcess` try/except +
  `logger.exception` shape; GUARD-01/02 extend the existing tested `_emit_startup_warnings`. This is
  a hardening phase, not a refactor — minimal, surgical, well-tested edits.
- Every fix is "warn / observe, don't change default behavior" — GUARD-01, GUARD-02, GUARD-06 all
  explicitly preserve current runtime behavior and only make an existing posture *visible* or a
  message *accurate*. GUARD-03 preserves best-effort delete. GUARD-04 is behavior-preserving by
  construction (the test pins terminate semantics).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The gating disposition source (read first)
- `.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md` — the
  triaged findings that fold into this phase: **HR-02** (GUARD-04 spawn red test, §HIGH),
  **HR-03** (GUARD-01/02 warning prominence + the correctness matrix, §MEDIUM), **HR-04** (GUARD-03
  delete swallow, §MEDIUM), **HR-06** (GUARD-06 legacy-fallback surfacing, §LOW), **HR-07** (GUARD-05
  gitignore, §LOW). Each carries exact file:line locations and a "why a hostile reader flags this".

### Requirements & scope (the locked acceptance contract)
- `.planning/REQUIREMENTS.md` — GUARD-01 (line 37), GUARD-02 (line 38), GUARD-03 (line 39),
  GUARD-04 (line 40), GUARD-05 (line 41), GUARD-06 (line 42), and the coverage map (lines 92-97).
  Note GUARD-06's explicit "loud warning **OR** opt-in" optionality (we choose loud warning, D-12).
- `.planning/ROADMAP.md` §"Phase 112: Defensive Guards & Code Hardening" — phase goal + GUARD mapping;
  §v1.4.0 CI-gates paragraph (Python ≥88, Angular floors, amd64+arm64, no tag in phase).
- `docs/superpowers/specs/2026-06-02-launch-hardening-design.md` — the approved design spec; the
  GUARD items are §2 (D-table) + §3.1 / §3.2 (the named six fixes) and §5 (Definition of Done).

### The INFRA-01 spawn-fix precedent (the GUARD-04 pattern to mirror)
- `src/python/common/multiprocessing_logger.py` — the Phase 107 fix: `get_context("spawn")` for the
  queue (line 24-25) + `__getstate__`/`__setstate__` (lines 49-80) dropping unpicklable thread state.
  This is the canonical pattern AppProcess's fix mirrors (D-01/D-02).
- `.planning/milestones/v1.3.0-phases/107-mp-logger-spawn-safety/` — Phase 107 CONTEXT/PLAN/SUMMARY
  for the reasoning behind the spawn-context fix and how the spawn-analog tests were structured.

### Touched source (exact locations from FINDINGS)
- `src/python/common/app_process.py` §`__init__` (lines 41-48), §`run`/`terminate`/`propagate_exception`
  — GUARD-04 target; the `Queue()`/`Event()` at lines 47-48 are the bug.
- `src/python/tests/unittests/test_common/test_app_process.py:175` — the red test that must go green.
- `src/python/seedsyncarr.py` §`_emit_startup_warnings` (lines 372-397, GUARD-01/02), §`_parse_args`
  legacy-fallback block (lines 265-272, GUARD-06), and the `__init__`/`run` ordering (lines 40, 74,
  120) that proves the GUARD-06 pre-logger timing bug.
- `src/python/web/handler/webhook.py:54-60` — the fail-closed 503 guard that makes the current
  GUARD-02 first-warning misleading.
- `src/python/controller/delete/delete_process.py:24` (GUARD-03 target) and lines 46-50
  (`DeleteRemoteProcess` log-and-continue precedent).
- `src/python/common/types.py` — `sanitize_log_value()` (Phase 101 SEC-01 helper), if a path/filename
  reaches a GUARD-03 log line.
- `.gitignore` (lines 14, 23-24, 36, 61) — existing artifact-ignore entries GUARD-05 extends.

### Audit baseline (cross-reference, do NOT mutate)
- `.planning/codebase/CONCERNS.md` §Tech Debt / §Security Considerations / §Fragile Areas — the prior
  art for all six items (cross-referenced in FINDINGS Appendix C). Owned by `/gsd:map-codebase`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **INFRA-01 spawn fix (`multiprocessing_logger.py`)** is the direct template for GUARD-04 —
  `get_context("spawn")` + `__getstate__`/`__setstate__`. Phase 107 already proved this pattern works
  on both macOS (`spawn`) and Linux (`fork`).
- **`_emit_startup_warnings` (`seedsyncarr.py:372-397`)** already exists, is called after logger setup
  (run() line 120), and is tested — GUARD-01/02 edit it in place, no new wiring.
- **`DeleteRemoteProcess.run_once` (`delete_process.py:46-50`)** is the in-repo log-and-continue
  precedent (try/except + `logger.exception`) GUARD-03's local-delete fix mirrors.
- **`sanitize_log_value()` (`common/types.py`, Phase 101)** — CR/LF/control-char log-injection
  sanitizer, already applied across the controller/delete cluster; reuse for any GUARD-03 log line.
- **`.gitignore` already ignores `.aidesigner/*`, `.bg-shell/`, `.turingmind/`, `.DS_Store`** — GUARD-05
  follows the identical pattern for `.orchestrator.json` + `.playwright-mcp/`.

### Established Patterns
- **Warn, don't change default behavior:** GUARD-01/02/06 all preserve runtime behavior and only make
  posture visible / messages accurate. This matches the project's opt-in-security stance (auth/webhook
  defaults are intentionally permissive with loud warnings, per CONCERNS.md).
- **Best-effort local cleanup:** the delete process is a one-shot (`AppOneShotProcess`) whose failure
  must not crash the sync tool — GUARD-03 logs but does not raise (D-09).
- **Spawn-safety is local, not global:** INFRA-01 fixed only the one class's primitives, never
  `set_start_method` globally — GUARD-04 follows the same blast-radius discipline (D-03).
- **Test-first, reuse harnesses:** GUARD-02 and GUARD-04 both have existing test files
  (`test_seedsyncarr.py`, `test_app_process.py`) — extend them rather than create new infrastructure.

### Integration Points
- `AppProcess` is the base class for **every** worker process (delete, scan, lftp, etc.) — GUARD-04's
  fix touches all of them transitively, so the full suite under both start methods is the regression net.
- `_emit_startup_warnings` and the legacy-fallback warning both feed the single configured app logger
  (`Constants.SERVICE_NAME`) — GUARD-01/02/06 all land in the same operator-visible log stream.
- No Angular / E2E surface in this phase — it is Python + `.gitignore` only. Angular floors stay green
  by virtue of being untouched.

</code_context>

<deferred>
## Deferred Ideas

- None surfaced beyond the phase's six items — the FINDINGS pass already bounded scope tightly and
  every fold-here finding maps to exactly one GUARD requirement.

### Reviewed Todos (not folded)
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.6, area: security) — **not folded.**
  Already shipped as **Phase 111** (CFG-01..04, complete). The todo belongs to 111, not this phase.
- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.6, area: testing) — **not folded.** This is the
  **DEFER-WEBOB** item, externally blocked on upstream webob 2.0 (PR #466 open) and explicitly parked
  in REQUIREMENTS.md "Future Requirements" and FINDINGS Appendix A. Not actionable in this phase.

</deferred>

---

*Phase: 112-defensive-guards-code-hardening*
*Context gathered: 2026-06-02*
