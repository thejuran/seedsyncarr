# Phase 99: Low-Priority Python Coverage - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add **one targeted regression test per gap** for the two Low-priority Python coverage gaps from CONCERNS.md — tests that would have caught the documented risk. No full-path coverage sweep (that was Phase 97's medium-tier scope); these are narrow safety nets over already-correct code.

1. **COVLOW-01** — Auto-delete honors a `enabled`/`dry_run` toggle flipped during a *live* `threading.Timer` window. The in-method config re-read at `src/python/controller/controller.py:838-851` must honor the new value: no deletion when disabled, logs-only when dry-run. (`controller.py:823-851`)
2. **COVLOW-02** — `BoundedOrderedSet` eviction ordering after `touch`: a touched item is retained, the oldest non-touched item evicts first. (`src/python/common/bounded_ordered_set.py:91-105`)

Out of scope: Angular work (Phase 100), the CI threshold ratchet (Phase 100 / RATCHET-02), and any non-trivial bug fix surfaced by these tests (→ v1.4.0).
</domain>

<decisions>
## Implementation Decisions

The design spec (`docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` §"Phase 99 — Low-Priority Python Coverage") functions as a locked SPEC for this phase — files, the one-test-per-plan shape, and the two plans (99-01 auto-delete toggle, 99-02 BoundedOrderedSet eviction) are already fixed there. The decisions below resolve the HOW gray areas the spec left open. User delegated all four to Claude's recommendation ("all yo" — same posture as Phase 97's "take your recs for all").

### COVLOW-01 — Timer realism (99-01)
- **D-01:** Drive the gap through a **real `threading.Timer`** via `__schedule_auto_delete`, not a direct `__execute_auto_delete` call. Schedule with a short `delay_seconds` (≈0.05s on the mock context), flip the config toggle *after* scheduling and *before* the Timer fires, then join the pending timer and assert. Rationale: the existing `TestAutoDeleteExecution` tests (`test_execute_dry_run_does_not_delete`, `test_execute_disabled_skips_deletion`, `test_auto_delete.py:101-116`) already flip config and call `__execute_auto_delete` **directly** — re-using that path would NOT close the gap, which is specifically the *schedule → flip → fire* window. The real-Timer path is the only thing that exercises the in-method re-read end-to-end from a scheduled callback.
- **D-01a:** Control flake by **joining the pending timer** (read it from `__pending_auto_deletes` before fire, or poll the dict, then `timer.join(timeout=...)` with a generous timeout like 5s) and asserting via the `delete_local` mock — NOT by `sleep()`-ing a fixed wall-clock interval. A `@pytest.mark.timeout(N)` / unittest-equivalent guard caps the test against a hang. Exact delay value and join mechanism are Claude's discretion within this constraint.

### COVLOW-01 — Both toggles (99-01)
- **D-02:** Cover **both** flips as two distinct tests: (a) `enabled` flipped `True→False` after scheduling → `delete_local.assert_not_called()` (skip path at `controller.py:839-843`); (b) `dry_run` flipped `False→True` after scheduling → `delete_local.assert_not_called()` (logs-only path at `controller.py:846-850`). The spec's "(or dry_run=true)" makes both in-scope, and both share one re-read block so covering both fully exercises it. The log-message assertion (the `"feature was disabled"` / `"DRY-RUN: Would delete"` strings) is optional and at Claude's discretion — the binding assertion is that `delete_local` is not called.

### COVLOW-02 — Eviction shape (99-02)
- **D-03:** Concrete shape: `maxlen=3`, load `['a','b','c']` via `BoundedOrderedSet.from_iterable(...)`, `touch('a')` (moves the oldest to most-recent via `move_to_end`, `bounded_ordered_set.py:104`), then `add('d')` to force exactly one eviction. Assert all three facts: (a) the `add('d')` return value (evicted item) is `'b'` — the oldest *non-touched* item; (b) iteration order / `as_list()` is `['c', 'a', 'd']` — touched `'a'` retained and reordered; (c) `total_evictions == 1`. This proves the touched item survives and the oldest non-touched evicts first — the exact COVLOW-02 statement. Extend `tests/.../test_common/test_bounded_ordered_set.py` (real path: `src/python/tests/unittests/test_common/test_bounded_ordered_set.py`), which has `from_iterable` coverage but no `touch`+eviction-ordering test.

### Trivial-fix posture (carried from Phase 97)
- **D-04:** Carry Phase 97's posture forward verbatim: a clear, small security/correctness fix (≤10 net non-blank/non-comment lines, no public-API change, no observable-behavior change) surfaced by a red test lands **in-scope** as a green commit after its red test; genuinely borderline cases (right at the ~10-line or behavior-change edge) **default to deferring** to v1.4.0 with a one-line STATE.md deferred-items entry referencing the documenting test. Expectation: these are LOW-priority gaps over code that already handles the case correctly (the in-method re-read exists; eviction ordering via `OrderedDict.popitem(last=False)` + `move_to_end` is correct), so **no fix is anticipated** — these are pure regression nets. If a test goes green on the first run, that is the expected outcome, not a sign the test is wrong; the value is the locked-in regression guard.

### Claude's Discretion
- Exact test function/method names, the concrete `delay_seconds` value and timer-join mechanism for 99-01, and the timeout-guard value.
- Whether 99-01 reuses the existing `BaseAutoDeleteTestCase` / `_make_safe_mock_file` helpers (`test_auto_delete.py:10-31, 75-81`) — recommended, to inherit the state/pack-guard-passing mock file and the `setUp` teardown that cancels pending timers (`test_auto_delete.py:26-31`).
- Whether the two 99-01 toggle tests live in the existing `TestAutoDeleteExecution` class or a new `TestAutoDeleteToggleDuringTimer` class — recommend a new class to make the live-Timer distinction explicit.
- Optional log-message assertions for 99-01.
</decisions>

<specifics>
## Specific Ideas

- 99-01 must distinguish itself from the existing direct-call tests. The existing tests prove `__execute_auto_delete` *as a method* honors config; 99-01 proves the *Timer-scheduled callback* re-reads config that changed after `__schedule_auto_delete` ran. The schedule call is the thing under test, not just the execute method.
- `__schedule_auto_delete` (`controller.py:806-821`) reads `delay_seconds` and `__execute_auto_delete` (`controller.py:838-850`) re-reads `enabled`/`dry_run` — the two reads are deliberately split across the timer window, which is exactly what COVLOW-01 pins.
- 99-02: the subtlety is that `touch` calls `OrderedDict.move_to_end` (`bounded_ordered_set.py:104`) and eviction calls `popitem(last=False)` (`bounded_ordered_set.py:85`). Without a test, a future refactor that calls `touch` after `add` (CONCERNS.md risk note) could silently change which item evicts.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (locked requirements)
- `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md` §"Phase 99 — Low-Priority Python Coverage" (plans 99-01, 99-02) plus the global "Tier policy", "Trivial-fix policy", and "Phase shape" sections. MUST read before planning.
- `.planning/REQUIREMENTS.md` — COVLOW-01 / COVLOW-02 acceptance statements (lines 23-24) and traceability table (lines 65-66).
- `.planning/codebase/CONCERNS.md` §"Test Coverage Gaps" → "Auto-delete dry-run vs. enabled toggling under live timer" and "BoundedOrderedSet eviction ordering after touch" (the original 2026-05-26 audit with file:line refs and risk notes).

### Source under test
- `src/python/controller/controller.py` — `__schedule_auto_delete` (806-821) + `__execute_auto_delete` (823-851), specifically the in-method config re-read at 838-851 (COVLOW-01).
- `src/python/common/bounded_ordered_set.py` — `add`/eviction (66-89), `touch` (91-105), `from_iterable` (192) (COVLOW-02).

### Existing test patterns to extend
- `src/python/tests/unittests/test_controller/test_auto_delete.py` — `BaseAutoDeleteTestCase` (10-31), `_make_safe_mock_file` (75-81), `TestAutoDeleteExecution` direct-call tests (72-200). Extend with the live-Timer toggle tests (COVLOW-01).
- `src/python/tests/unittests/test_common/test_bounded_ordered_set.py` — has `from_iterable` + eviction tests but no `touch`+eviction-ordering test. Extend (COVLOW-02).

**Path note:** the design spec writes test paths as `tests/unit/...`; the real repo layout is `src/python/tests/unittests/...`. Use the real paths above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseAutoDeleteTestCase` (`test_auto_delete.py:10-31`) — already wires a controller with auto-delete enabled, `delay_seconds=10`, mock context/webhook/file-op managers, and a `tearDown` that cancels pending timers before stopping patches (critical for the live-Timer test to not leak threads).
- `_make_safe_mock_file` (`test_auto_delete.py:75-81`) — builds a `ModelFile` mock that passes the state + pack guards, so 99-01 can focus purely on the config-toggle assertion.
- `BoundedOrderedSet.from_iterable` (`bounded_ordered_set.py:192`) — already the loading mechanism the spec calls for; existing tests `test_from_iterable` / `test_from_iterable_with_eviction` (`test_bounded_ordered_set.py:207-218`) are the closest analogs to extend.

### Established Patterns
- Private-method access in controller tests uses name-mangled handles: `self.controller._Controller__model.get_file = MagicMock(...)`, `self.controller._Controller__execute_auto_delete(...)`, `_Controller__pending_auto_deletes`, `_Controller__schedule_auto_delete` (`test_auto_delete.py:85-90, 129-138`). 99-01 follows the same convention.
- Config is a mock: flipping `self.mock_context.config.autodelete.enabled = False` mid-test changes what the re-read sees on the next attribute access — no real config reload needed.
- BoundedOrderedSet tests are plain `unittest.TestCase`, no fixtures — 99-02 is a single self-contained method.

### Integration Points
- COVLOW-01 spans `__schedule_auto_delete` (timer arm) → `threading.Timer` → `__execute_auto_delete` (config re-read). The test must arm a real timer and let it fire; asserting on `delete_local`/`delete_remote` mocks is the observable outcome.
- COVLOW-02 is self-contained in `bounded_ordered_set.py` — no external integration.
- Both feed Phase 100's RATCHET-02 only indirectly (they raise the "now" coverage number the ratchet compares against the v1.3.0 baseline).
</code_context>

<deferred>
## Deferred Ideas

- Any bug surfaced by these tests that exceeds the trivial-fix window (>10 net lines, public-API change, or observable-behavior change) → v1.4.0 (Known Bugs + Security), with a one-line STATE.md deferred-items entry referencing the documenting test (per D-04). None anticipated.
- TOCTOU / deeper concurrency hardening of the auto-delete Timer path (e.g. cancelling an in-flight callback) — out of scope; COVLOW-01 only pins the existing in-method re-read, which the code already implements correctly.
- CI threshold ratchet (RATCHET-02) — Phase 100.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock` — matched on generic keywords (test/python) only; blocked on upstream webob 2.0, unrelated to this phase. Same disposition as Phase 97.
- `2026-04-24-migrate-config-set-to-post-body` — matched on generic keywords (config/python/test) only; API contract change for a separate milestone, unrelated. Same disposition as Phase 97.
</deferred>

---

*Phase: 99-low-priority-python-coverage*
*Context gathered: 2026-05-29*
