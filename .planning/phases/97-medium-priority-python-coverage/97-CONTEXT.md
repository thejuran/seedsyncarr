# Phase 97: Medium-Priority Python Coverage - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Capture the pre-phase coverage baseline (RATCHET-01), then add **full path coverage** for three Medium-priority Python test gaps from CONCERNS.md:

1. `MultiprocessingLogger` listener-thread shutdown semantics (COVMED-01) — `src/python/common/multiprocessing_logger.py:67-86`
2. SSRF `_validate_url` IPv6 + reserved-range coverage (COVMED-02) — `src/python/web/handler/config.py:55-85`
3. LFTP `JobStatusParser` `ValueError` recovery (COVMED-03) — `src/python/lftp/lftp.py`, `src/python/lftp/job_status_parser.py`

Full path coverage = every documented branch, every realistic input class, end-to-end where the gap concerns an integration. Trivial bugs (≤10 net non-blank/non-comment lines, no public-API change, no observable-behavior change) are fixed in the same plan after the red test; larger findings defer to v1.4.0. Angular work, the Low-priority gaps, and the CI threshold ratchet are NOT in this phase.
</domain>

<decisions>
## Implementation Decisions

The design spec (`docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md`) functions as a locked SPEC for this phase — files, branches to cover, and test-isolation strategy per plan are already fixed there. The decisions below resolve the HOW gray areas the spec left open. User delegated all four to Claude's recommendation ("take your recs for all").

### SSRF IPv6-mapped-IPv4 fix scope (COVMED-02)
- **D-01:** If the test shows `::ffff:10.0.0.1` (IPv6-mapped private IPv4) is NOT blocked by the current `addr.is_private or is_loopback or is_reserved or is_link_local` check at `config.py:78`, treat adding an explicit unmap-and-recheck as an **in-scope trivial fix** — not a v1.4.0 deferral. It is <10 lines, no public-API change, and the behavior change strengthens an existing security guard (SSRF) rather than altering caller-visible contracts. The spec explicitly anticipates this fix.
- **D-02:** Implementation shape for the fix (if needed): detect `addr.ipv4_mapped` (or equivalent) and re-run the private/reserved/loopback/link-local checks against the unmapped IPv4 before returning valid. Keep it minimal; do NOT add DNS-rebind handling (out of scope per existing inline comment at `config.py:59-62`).

### LFTP test layer (COVMED-03)
- **D-03:** Cover `JobStatusParser` `ValueError` recovery as an **integration test** using the existing `tests/integration/test_lftp/test_lftp_protocol.py` fixture pattern (real lftp binary already in CI matrix), NOT a mocked unit test. The recovery behavior spans parser → controller consecutive-error counter, which the integration harness already exercises end-to-end.
- **D-04:** Cover all four documented points: malformed `jobs -v` line raises `LftpJobStatusParserError`; controller consecutive-error counter increments; `MAX_CONSECUTIVE_STATUS_ERRORS = 2` triggers the documented recovery; counter resets on a subsequent success.

### Trivial-fix default posture
- **D-05:** At the borderline (a candidate fix sitting right at the ~10-line or behavior-change edge), **default to deferring** to v1.4.0 with a one-line STATE.md deferred-items entry referencing the documenting test. v1.3.0's purpose is the additive coverage safety net; routing ambiguous bugs to v1.4.0 (Known Bugs + Security) keeps this milestone low-regression. Clear, small fixes (e.g., the SSRF unmap in D-01, or a missing counter-reset line) stay in-scope — the deferral default applies only to genuinely borderline cases.

### Baseline capture mechanics (RATCHET-01)
- **D-06:** Capture the baseline by running the existing `make` coverage targets (Python `--cov` run + Angular Karma) against `main` HEAD, recording the raw totals verbatim into `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`. Commit this file BEFORE any new test lands in phase 97. Record both Python (line) and Angular (statements/branches/functions/lines) numbers so the Phase 100 ratchet has a complete "before" reference.

### Claude's Discretion
- Exact test function names, fixture wiring, and `@pytest.mark.timeout(N)` values (spec mandates a timeout guard on the MP-logger test against flake).
- Whether the MP-logger test uses a real `multiprocessing.Queue` with a deterministic sentinel (spec's stated isolation approach) vs an equivalent deterministic harness — default to the spec's approach.
- The exact `socket.getaddrinfo` stubbing mechanism for the SSRF test (spec mandates stubbing so CI IPv6 availability is irrelevant).
</decisions>

<specifics>
## Specific Ideas

- MP-logger branches to cover (from spec + code at `multiprocessing_logger.py:67-86`): handler raises during `handle(record)` → outer `except Exception` sets `__listener_exc_info`, sets `__listener_shutdown`, breaks; `propagate_exception()` re-raises the captured `exc_info` and clears it; inner-loop `queue.Empty` breaks the inner loop only (does NOT terminate the listener); clean shutdown via `stop()` setting the event.
- Spec trivial-fix window for MP-logger: if the outer `except Exception` silently swallows errors that should propagate, narrow the catch / ensure `propagate_exception` surfaces them (apply D-05 posture if borderline).
- SSRF cases to cover (from spec): IPv4 private (regression baseline), IPv4 loopback, IPv4 link-local `169.254/16`, IPv6 link-local `fe80::/10`, IPv6 loopback `::1`, IPv6 unique-local `fc00::/7`, IPv6-mapped IPv4 `::ffff:10.0.0.1`, unresolved hostname (`gaierror` → "Cannot resolve hostname"), valid public host.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (locked requirements)
- `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` — Full v1.3.0 design. **Phase 97 content is in the "Phase 97 — Medium-Priority Python Coverage" section** (plans 97-01/02/03), plus the global "Tier policy", "Trivial-fix policy", and "Phase shape" sections. MUST read before planning.
- `.planning/REQUIREMENTS.md` — COVMED-01/02/03 and RATCHET-01 acceptance statements; traceability.
- `.planning/codebase/CONCERNS.md` §"Test Coverage Gaps" — original audit (2026-05-26) that catalogued these gaps with file:line refs.

### Source under test
- `src/python/common/multiprocessing_logger.py` — `__listener` loop, `propagate_exception`, `stop` (COVMED-01).
- `src/python/web/handler/config.py` §`_validate_url` (lines 55-85) — SSRF guard (COVMED-02).
- `src/python/lftp/lftp.py`, `src/python/lftp/job_status_parser.py` — parser + `LftpJobStatusParserError`, and the controller consecutive-error counter (`MAX_CONSECUTIVE_STATUS_ERRORS`) (COVMED-03).

### Existing test patterns to extend
- `tests/integration/test_lftp/test_lftp_protocol.py` — integration fixture pattern for COVMED-03 (D-03).
- `tests/integration/test_web/test_handler/test_config.py` — extend for COVMED-02.
- `tests/unit/test_common/test_multiprocessing_logger.py` (new or extended) — COVMED-01.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/integration/test_lftp/` fixtures — real lftp binary harness, already CI-gated on amd64+arm64.
- `tests/integration/test_web/test_handler/test_config.py` — existing handler-test scaffolding (bottle request mocking, `_validate_url` is a `@staticmethod` so it's directly callable).
- pytest-cov already wired with `--cov-fail-under` (current bar from v1.1.2 baseline: Python 85.05%).

### Established Patterns
- `_validate_url` is a pure `@staticmethod` (`config.py:55`) → unit-testable in isolation by stubbing `socket.getaddrinfo`; no bottle stack needed for the SSRF cases.
- MP-logger uses `threading.Event` for shutdown and stashes `sys.exc_info()` for cross-thread propagation — tests must drive a real listener thread and join via `stop()`.
- Trivial-fix policy from prior milestones: security-strengthening fixes on existing guards have precedent for in-scope inclusion (e.g., v3.1 SSRF/shell-escape work).

### Integration Points
- COVMED-03 recovery spans `job_status_parser` (raises) → `lftp.py` → controller error counter; the integration test asserts the counter behavior, not just the parser exception.
- RATCHET-01 baseline file feeds the Phase 100 ratchet (RATCHET-02) — the "before" column of ROADMAP's Coverage Ratchet table.
</code_context>

<deferred>
## Deferred Ideas

- Any bug surfaced by these tests that exceeds the trivial-fix window (>10 lines, public-API change, or observable-behavior change) → v1.4.0 (Known Bugs + Security), with a one-line STATE.md deferred-items entry referencing the documenting test (per D-05).
- DNS-rebind (TOCTOU) hardening for `_validate_url` — explicitly out of scope per the existing inline comment; the SSRF test documents the limitation but does not fix it.
- Per-file coverage floors — out of scope milestone-wide (global thresholds only).

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — blocked on upstream webob 2.0; unrelated to this phase.
- `2026-04-24-migrate-config-set-to-post-body` — API contract change, separate milestone; unrelated to this phase.
</deferred>

---

*Phase: 97-medium-priority-python-coverage*
*Context gathered: 2026-05-28*
