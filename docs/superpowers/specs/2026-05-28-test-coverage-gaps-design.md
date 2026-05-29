# Milestone v1.3.0 — Test Coverage Gaps

**Date:** 2026-05-28
**Status:** Design — ready for `/gsd:new-milestone`
**Source of concerns:** `.planning/codebase/CONCERNS.md` (Test Coverage Gaps section, audited 2026-05-26)

---

## Goal

Close the 8 test coverage gaps catalogued in `CONCERNS.md`, tiered by priority. The 4 Medium-priority gaps get full path coverage; the 4 Low-priority gaps get a single targeted regression test that would have caught the documented risk. When a test reveals a trivial bug (< 10 lines, obvious fix, no public API change, no observable behavior change), the bug is fixed in the same plan. Larger findings are deferred to milestone v1.4.0 (Known Bugs + Security). Milestone ends with ratcheted coverage thresholds in CI so the new bar holds.

## Why this milestone, why now

- v1.2.0 (Test & Quality Hardening) shipped 2026-04-28; CONCERNS.md was audited 2026-05-26 against the post-v1.2.0 tree. The 8 gaps remain.
- Coverage is the safety net for the next three milestones planned after this one (v1.4.0 Known Bugs + Security, v1.5.0 Frontend Deps + Dead Code, v1.6.0 Backend Architecture Refactor). Landing the tests first means regressions during those milestones get caught automatically.
- v1.2.0's retro explicitly flagged: "Coverage baselines should be documented in ROADMAP.md at milestone boundaries for historical tracking." This milestone operationalizes that.

## Scope

### In scope

**Medium-priority gaps (full path coverage):**

1. `MultiprocessingLogger` listener-thread shutdown semantics — `src/python/common/multiprocessing_logger.py:67-86`
2. SSRF `_validate_url` IPv6 + reserved-range coverage — `src/python/web/handler/config.py:55-85`
3. LFTP `JobStatusParser` `ValueError` recovery — `src/python/lftp/lftp.py:11-13`, `src/python/lftp/job_status_parser.py:710-727`
4. `confirm-modal.service.ts` `escapeHtml` end-to-end XSS — `src/angular/src/app/services/utils/confirm-modal.service.ts:33-40`

**Low-priority gaps (targeted regression test):**

5. Auto-delete dry-run vs enabled toggling under live Timer — `src/python/controller/controller.py:823-851`
6. `BoundedOrderedSet` eviction ordering after `touch` — `src/python/common/bounded_ordered_set.py:91-105`
7. SSE timeout reconnection race — `src/angular/src/app/services/base/stream-service.registry.ts:111-164`
8. `auth.interceptor.ts` token-missing / rotation path — `src/angular/src/app/services/utils/auth.interceptor.ts:7-17`

**Cross-cutting:**

- Capture coverage baseline before phase 97 starts (`.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`).
- Ratchet `--cov-fail-under` and Karma `coverageReporter.check.global` thresholds at the end of phase 100.
- Record before/after numbers in ROADMAP.md and the v1.3.0 retro entry.

### Out of scope

- The other 8 buckets of CONCERNS.md (tech debt, known bugs, security considerations, performance, fragile areas, scaling, deps, missing features) — those are future milestones in the planned order: v1.4.0 (Known Bugs + Security), v1.5.0 (Frontend Deps + Dead Code), v1.6.0 (Backend Architecture Refactor).
- Per-file coverage floors. Global thresholds only — per-file is too brittle for a homelab-scale project.
- DNS-rebind hardening for `_validate_url`. The existing inline comment marks it out-of-scope; the test documents the limitation but does not fix it.

## Approach

### Tier policy

| Priority | Posture | Test depth |
|---|---|---|
| Medium | Full path coverage | Every documented branch, every realistic input class, end-to-end where the gap concerns an integration |
| Low | Targeted regression | One test that would have caught the specific risk described in CONCERNS.md |

### Trivial-fix policy

When a test reveals a bug:

1. Fix lands in the same plan commit, after the test commit (test commit is red, fix commit is green).
2. Fix is blocked and deferred to v1.4.0 if any of these are true:
   - Fix > 10 lines (counted as net non-blank, non-comment lines added)
   - Fix touches public API (anything not prefixed with `_` in Python, or anything exported from a barrel/index in Angular)
   - Fix changes observable behavior (return types, raised exception types, side effects visible to callers)
3. Deferred items get a one-line entry in `.planning/STATE.md` deferred items table referencing the test that documents the issue.
4. Decision is per-plan; surfaces in plan review.

### Phase shape

By priority tier, then by layer. Continues phase numbering from v1.2.0's last phase (96).

| Phase | Title | Gaps | Layer | Tier | Plans |
|---|---|---|---|---|---|
| 97 | Medium-Priority Python Coverage | MP-logger, SSRF, LFTP parser | Python | Medium | 3 |
| 98 | Medium-Priority Angular Coverage | escapeHtml | Angular | Medium | 1 |
| 99 | Low-Priority Python Coverage | Auto-delete toggle, BoundedOrderedSet | Python | Low | 2 |
| 100 | Low-Priority Angular Coverage + CI Ratchet | SSE timeout, auth interceptor, ratchet | Angular + CI | Low + cross | 3 |

## Phase content

### Phase 97 — Medium-Priority Python Coverage

**Plan 97-01: `MultiprocessingLogger` listener-thread shutdown**

- Files: `src/python/common/multiprocessing_logger.py`, new or extended `tests/unit/test_common/test_multiprocessing_logger.py`
- Cover:
  - Handler raises during `handle(record)` → listener thread sets `__listener_shutdown` and exits
  - `propagate_exception()` re-raises the captured `exc_info`
  - Inner-loop `queue.Empty` does not terminate the listener
  - Clean shutdown via sentinel value
- Trivial-fix window: if the outer `except Exception` silently swallows errors that should propagate to `propagate_exception`, narrow the catch and log before re-raise.
- Test isolation: real `multiprocessing.Queue`, deterministic sentinel, `@pytest.mark.timeout(N)` guard against flake.

**Plan 97-02: SSRF `_validate_url` IPv6 + reserved-range coverage**

- Files: `src/python/web/handler/config.py`, extend `tests/integration/test_web/test_handler/test_config.py`
- Cover: IPv4 private baseline (regression), IPv4 loopback, IPv4 link-local (`169.254/16`), IPv6 link-local (`fe80::/10`), IPv6 loopback (`::1`), IPv6 unique-local (`fc00::/7`), IPv6-mapped IPv4 (`::ffff:10.0.0.1`), unresolved hostnames, valid public host.
- Trivial-fix window: if `ipaddress.ip_address(...).is_private` does not catch the IPv6-mapped form, add an explicit check.
- Test isolation: stub `socket.getaddrinfo`; do not rely on CI runner IPv6 availability.
- DNS-rebind: documented as out-of-scope per existing inline comment; not addressed here.

**Plan 97-03: LFTP `JobStatusParser` `ValueError` recovery**

- Files: `src/python/lftp/lftp.py`, `src/python/lftp/job_status_parser.py`, extend `tests/integration/test_lftp/test_lftp_protocol.py` (or appropriate unit suite)
- Cover:
  - A single malformed `jobs -v` line raises `LftpJobStatusParserError`
  - Controller's consecutive-error counter increments
  - `MAX_CONSECUTIVE_STATUS_ERRORS = 2` triggers documented recovery
  - Counter resets on success
- Trivial-fix window: if the counter does not reset on success, add the reset line.
- Test isolation: use existing `tests/integration/test_lftp/` fixture pattern; verify CI matrix already has real lftp binary.

### Phase 98 — Medium-Priority Angular Coverage

**Plan 98-01: `escapeHtml` end-to-end XSS coverage**

- Files: `src/angular/src/app/services/utils/confirm-modal.service.ts`, new or extended `confirm-modal.service.spec.ts`
- Cover:
  - Every metacharacter from the documented set (`&<>"'`)
  - Attacker payloads injected into `title`, `body`, button labels, button classes
  - Assert resulting `innerHTML` contains no executable markup (no `<script>`, no `on*=`, no `javascript:`)
  - Confirm `escapeHtml` runs in every interpolation path (no bypass call site)
- Trivial-fix window: if backtick, U+2028, U+2029, or null byte create a real risk for any current caller, add them to the escape set.
- Test isolation: standalone-component spec pattern (post-v1.1.2 migration).

### Phase 99 — Low-Priority Python Coverage (targeted regression)

**Plan 99-01: Auto-delete toggle during live Timer**

- Files: `src/python/controller/controller.py`, extend existing auto-delete tests
- One test:
  - Schedule an auto-delete via the Timer
  - Flip `auto_delete.enabled = false` (or `dry_run = true`) before fire
  - Assert the in-method config re-read at `controller.py:838-851` honors the new value: no deletion in disabled case; logs-only in dry-run case

**Plan 99-02: `BoundedOrderedSet` eviction ordering after `touch`**

- Files: `src/python/common/bounded_ordered_set.py`, extend `tests/unit/test_common/test_bounded_ordered_set.py`
- One test:
  - Load N items via `from_iterable`
  - `touch` a middle item
  - Add until eviction triggers
  - Assert eviction order: touched item retained, oldest non-touched evicted first

### Phase 100 — Low-Priority Angular Coverage + CI Ratchet

**Plan 100-01: SSE timeout reconnection race**

- Files: `src/angular/src/app/services/base/stream-service.registry.ts`, extend existing stream-service specs
- One test:
  - `StreamDispatchService` with fakeAsync + tick
  - Simulate heartbeat arriving in the same tick as `checkConnectionTimeout` fires
  - Assert no spurious reconnect, no double subscription

**Plan 100-02: `auth.interceptor.ts` token rotation**

- Files: `src/angular/src/app/services/utils/auth.interceptor.ts`, extend interceptor spec
- One test:
  - Meta tag set, request fires, meta tag changes, `_resetAuthInterceptorCache` called, next request carries new token
  - Documents the implicit page-reload coupling

**Plan 100-03: CI ratchet**

- Python: bump `--cov-fail-under` in pytest config (`pyproject.toml` `[tool.pytest.ini_options]` — verify exact location during planning) to the new line-coverage number from the baseline-vs-now diff
- Angular: bump Karma `coverageReporter.check.global` thresholds (`karma.conf.js`) to the new number
- Both ratchets land in a single commit so a failed CI gate has one obvious revert target
- Record before/after numbers in:
  - `.planning/ROADMAP.md` v1.3.0 milestone summary
  - v1.3.0 retro entry in `.planning/RETROSPECTIVE.md`
- The ratchet only increases; never lower without an explicit decision logged in `.planning/PROJECT.md` Key Decisions table

## Cross-cutting concerns

### Coverage baseline

Before phase 97 starts, capture current numbers as a single commit. Run `pytest --cov` on Python and `ng test --code-coverage` on Angular against `main` HEAD. Record line / branch / function coverage in `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`. The final ratchet in plan 100-03 compares against this anchor, not against whatever number happens to be in CI config at that moment.

### Test isolation patterns

Follow patterns established in v1.2.0:

- Python: pytest + testfixtures (already in deps). No DB mocking; use real `multiprocessing.Queue` with deterministic sentinels for the listener test.
- Angular: standalone-component spec pattern with `provideHttpClient()` (post-v1.1.2 migration).
- SSE timeout (100-01): fakeAsync + tick, not real timers — matches existing stream-service spec patterns.

### CI ratchet mechanics

Single commit at end of phase 100. Ratchet is monotonic (only increases). The first PR opened after the ratchet lands will reveal whether the bar is calibrated correctly — if a legitimate change cannot avoid a < 0.1% drop, document the new floor decision in PROJECT.md Key Decisions.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `MultiprocessingLogger` test flakes on slow CI due to thread scheduling | Medium | Use `join(timeout=…)` with explicit timeouts; `@pytest.mark.timeout(N)`; if flaky, drop to deterministic single-process simulation of the listener loop |
| SSRF IPv6 test depends on real DNS / CI runner blocks IPv6 | Medium | Stub `socket.getaddrinfo`; the test is about validation logic, not DNS |
| Coverage ratchet bites unrelated PRs (legitimate ratchet bite) | Low-Medium | First post-ratchet PR reveals calibration; if a legitimate change drops coverage by more than 0.1% from the new floor, the floor decision is re-opened and logged in PROJECT.md Key Decisions |
| Trivial-fix window expands into milestone v1.4.0 scope | Low | Hard stop on > 10 lines / public API / observable behavior; per-plan code review catches scope creep |
| LFTP parser test requires real lftp binary in CI | Low | Existing `tests/integration/test_lftp/` fixture pattern already runs in CI; verify during plan 97-03 |

## Success criteria

- All 8 gaps from CONCERNS.md (Test Coverage Gaps section) have closing tests committed
- Medium-priority gaps have full-path coverage; Low-priority gaps have at least one targeted regression test
- Any trivial fixes landed are documented in the plan's commit history (test-red commit precedes fix-green commit)
- Larger findings deferred to v1.4.0 are listed in `.planning/STATE.md` deferred items table with a link to the test that documents them
- `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` exists with before numbers
- CI coverage thresholds are ratcheted upward; before/after numbers recorded in ROADMAP.md and RETROSPECTIVE.md
- v1.3.0 retro entry added to RETROSPECTIVE.md following the project's existing retro template

## Future milestones (planned order)

This is milestone 1 of 4 derived from CONCERNS.md. The remaining three are planned in this order:

| # | Milestone | Theme |
|---|---|---|
| v1.3.0 | (this milestone) | Test Coverage Gaps |
| v1.4.0 | Known Bugs + Security | The 4 known bugs + actionable security items (innerHTML→Renderer2, mandatory webhook secret, log-injection audit, plus any deferred trivial-fix findings from v1.3.0) |
| v1.5.0 | Frontend Deps + Dead Code | Drop jQuery 4, FA4, css-element-queries; move mock-model fixtures out of prod bundle |
| v1.6.0 | Backend Architecture Refactor | Extract Controller god-class; refactor Config property machinery; auto-discover secret fields; dedup bulk handler scaffold |

Order reasoning: D (this) → B → A → C from the brainstorm conversation — coverage first (safety net), then deps cleanup (small, contained), then bug fixes (with new coverage in place), then the riskiest refactor last.
