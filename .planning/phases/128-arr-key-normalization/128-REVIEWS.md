---
phase: 128
reviewers: [codex]
reviewed_at: 2026-11-18
plans_reviewed: [128-01-PLAN.md, 128-02-PLAN.md, 128-03-PLAN.md, 128-04-PLAN.md]
cycle: 3
---

# Cross-AI Plan Review — Phase 128

Run in parallel with bm-plan-checker per CLAUDE.local.md (`codex exec --skip-git-repo-check --sandbox read-only -`, codex-cli 0.153.4).

## Codex Review

## Summary

The plans are well grounded in the repository and should achieve ARR-01 through ARR-03. The shared helper, normalization at the save/read boundaries, and unchanged completion gate are appropriate. Dependency ordering is sound, and plans 02 and 03 have disjoint file ownership. Before execution, clarify plan 03’s variable ordering and correct plan 04’s parity claims and validation commands. No fundamental architectural or security blocker was found. This was a read-only review; tests were not run.

## Plan 128-01 — Shared rule

**Strengths**

- Small, dependency-free helper with explicit normalization and validation contracts.
- Covers Unicode whitespace, embedded controls, empty values, and character-range boundaries.
- Avoids config PROP changes that could reject existing configurations at startup.

**Concerns**

- **LOW:** The plan claims the rule “exists once” at completion, but explicitly leaves the original regex until plan 02. That invariant only holds after wave 2.
- **LOW:** Copying the existing comment perpetuates an inaccurate claim that printable ASCII without spaces is the only header content `requests` accepts. This is the application’s chosen policy, not the complete HTTP-library acceptance rule.
- **LOW:** Exact row counts, import counts, and regex-text assertions constrain implementation more than behavior requires.

**Suggestions**

- Make the single-definition invariant a phase-level check.
- Describe the regex as the shared application policy.
- Prefer behavioral assertions over source-layout checks where possible.

**Risk assessment: LOW.** The implementation is straightforward and isolated.

## Plan 128-02 — Save and Test Connection


- Preserves validation order and existing 404 behavior.
- Refuses invalid keys before mutation and tests preservation of stored values.
- Uses `Config.secret_fields()` rather than a duplicated secret list.
- Fixed secret-error responses provide stronger protection than relying on current checker messages.
- Correctly accounts for API-token changes affecting subsequent integration requests.


- **MEDIUM:** The new `ConfigError` warning path lacks an explicit log-leak assertion. The planned exception-message probe checks the response, while plan 04’s log test exercises Arr validation refusals that return before this exception branch.
- **LOW:** “All paths agree” needs qualification for non-string inputs: Save deliberately stringifies `12345`, while the shared normalizer rejects non-strings. Test Connection also retains its existing `.strip()` guard.


- Extend `test_set_secret_config_error_does_not_echo_value` to inspect formatted logger calls and verify the probe and exception message are absent.
- Document parity as applying to string key values, with separate tests for boundary-specific input coercion.

**Risk assessment: LOW.** The production change is narrow; the main gap is verification of the newly introduced logging branch.

## Plan 128-03 — Queue normalization and safe skip


- The in-memory regression correctly bypasses configparser and should fail before the fix.
- Normalizing before identity generation avoids unnecessary gate resets.
- Validation occurs before worker creation.
- Repository inspection confirms that `start_fetch() → None → _record_failure()` supports the proposed unavailable/hold behavior.
- Warning suppression uses existing tokens without logging credentials.


- **MEDIUM:** Task 2 inserts validation before `code = target.code`, then instructs the valid branch to call `pop(code, None)` “before continuing.” Following that ordering literally would reference `code` before assignment and break valid requests.
- **MEDIUM:** `threading.active_count()` is a process-wide, timing-sensitive assertion. It neither reliably proves no worker was started nor excludes unrelated thread activity.
- **LOW:** Fresh-client gate tests do not directly cover changing a previously successful integration to an invalid key while cached evidence or a request exists.


- Specify `self.__key_skip_warned.pop(target.code, None)`, or assign `code` before the new block.
- Patch the queue module’s thread constructor in skip tests and assert it was not called.
- Add one valid-to-invalid transition test proving cached or late evidence cannot authorize completion after the key changes.

**Risk assessment: MEDIUM.** The design is safe, but the variable-order instruction needs correction and concurrency assertions should be deterministic.

## Plan 128-04 — Parity and phase gate


- Exercises the normal settings-save flow using a real `Config`.
- Separately covers legacy padded values placed directly in live config.
- Requires actual coverage evidence and explicitly forbids declaring an unavailable gate passed.
- Includes formatted-log capture and response checks.


- **MEDIUM:** The must-have claiming identical verdicts for *every* rule-table row contradicts the task’s exclusions. Numeric input intentionally differs across boundaries, and Save is not tested for the `None` and empty-string rows.
- **MEDIUM:** The current validation map’s “one rule across three paths” command runs only the helper unit tests, not the new parity module. Several other command cells contain `same` or descriptive prose, despite Task 2 requiring each cell to be executable.
- **LOW:** Valid Test Connection cases are specified mainly through header inspection or absence of a key-validation error. A malformed mock or downstream failure could satisfy those weaker assertions.
- **LOW:** Repeated full-suite runs in the action and verification blocks add execution cost without necessarily adding evidence.


- State the string-input parity contract precisely; explicitly test Save’s empty/null rejection and numeric coercion separately.
- Update the validation map to invoke `test_arr_key_parity.py` and replace all shorthand cells with executable commands.
- Require `success: true` for valid Test Connection cases and successful queue outcomes, alongside normalized-header assertions.
- Reuse recorded gate results unless files change afterward.

**Risk assessment: MEDIUM.** The intended coverage is strong, but the validation contract currently overstates what its commands prove.

## Overall risk assessment

**MEDIUM, primarily execution and verification risk.** The referenced production paths, helper signatures, test harnesses, secret metadata, and coverage floor match the repository. The scope remains appropriate, and expected runtime overhead is negligible. Correct the plan 03 ordering ambiguity and plan 04 validation map before execution; the remaining suggestions strengthen evidence without requiring architectural changes.

## Consensus Summary (cycle 1)

Single external reviewer. HIGH: none. MEDIUM concerns fed into the revision loop:

1. 128-03 Task 2: warn-once reset references `code` before assignment; use `target.code` or assign first.
2. 128-03: `threading.active_count()` assertion is nondeterministic; patch the module's thread constructor and assert not called.
3. 128-02: new ConfigError warning path for secrets lacks a log-leak assertion.
4. 128-04: "identical verdicts for every rule-table row" overstates parity (non-string / None / "" rows differ by boundary); state the string-input contract precisely.
5. 128-04: validation map "one rule across three paths" points only at helper tests; cells with `same`/prose must become executable commands including `test_arr_key_parity.py`.

---

## Codex Review — Cycle 2 (after revision 61494c3a)

## 1. Summary

The revised plans address all five MEDIUM concerns from cycle 1 and should achieve ARR-01 through ARR-03 and D-07. Normalization occurs at the appropriate boundaries, secret refusals use fixed messages, and the existing completion gate supports safe holds without production changes.

One new MEDIUM test-fixture issue remains. No HIGH concerns or architectural blockers found. This was a read-only review; tests were not run.

## 2. Status of previous concerns

| Previous concern | Status | Assessment |
|---|---|---|
| 01: Single-definition invariant claimed too early | **Not resolved fully** | Frontmatter correctly defers it, but Task 2’s `<done>` still says the rule “exists once” before plan 02 removes the original. |
| 01: Inaccurate comment about headers accepted by `requests` | **Resolved** | Replacement describes the application’s chosen policy. |
| 01: Overly restrictive row/import/source-layout assertions | **Not resolved — LOW** | Exact counts and regex-source assertions remain. They constrain implementation unnecessarily but do not block correctness. |
| 02: Secret `ConfigError` warning lacks leak assertions | **Resolved** | Explicit formatted-message and argument checks cover values, exception text, exception objects, and `exc_info`. |
| 02: Non-string parity needs qualification | **Resolved** | Numeric coercion and null/empty handling are explicitly separated from string parity. |
| 03: `code` referenced before assignment | **Resolved** | New instructions consistently use `target.code`. |
| 03: Process-wide thread counting is nondeterministic | **Resolved** | Skip tests patch the thread constructor and use fresh clients. |
| 03: Missing valid-to-invalid transition coverage | **Resolved** | Added transition test checks cached snapshot removal and unavailable hold. |
| 04: Every-row parity claim contradicts exclusions | **Resolved** | Contract now covers the 15 non-empty-string rows, with separate boundary tests. |
| 04: Validation map omits parity and contains non-executable cells | **Resolved** | Commands explicitly include the parity module; zero-test selections fail validation. |
| 04: Valid outcomes asserted too weakly | **Resolved** | Positive Test Connection success and successful queue records are required. |
| 04: Repeated full-suite runs | **Not resolved fully — LOW** | Task action says to reuse one coverage run, but `<verify>` executes it again; validation sampling also mandates full-suite runs after waves. |

## 3. New concerns

**MEDIUM — Plan 03’s Radarr bad-key fixture lacks a valid URL.**

`TestBadKeyFailsSafe` setup specifies only the Sonarr URL. Its Radarr test then enables Radarr, sets its key to `None`, and disables Sonarr without assigning `radarr_url`.

With the specified `MagicMock` config, the unset URL remains a mock. The existing [`start_fetch()`](/Users/julianamacbook/seedsyncarr/src/python/controller/arr_queue.py:178) parses the URL before validating the key. Consequently, the test can fail during URL parsing instead of exercising the missing-key skip. Giving it an empty URL would also exercise the wrong branch.

Set `cfg.radarr.radarr_url = "http://radarr.internal.example:7878"` in setup or that test.

## 4. Suggestions

- Fix the Radarr fixture before execution.
- Change plan 01’s completion wording to “shared module is available; caller migration follows in wave 2.”
- Explicitly allow recorded coverage/lint results to satisfy verification when the tested code has not changed.
- Optionally strengthen the transition test with a previously authorizing snapshot or an outstanding request. The current empty-queue test proves snapshot invalidation, but starts from evidence that already holds completion.

## 5. Risk assessment

**LOW overall; MEDIUM localized test-execution risk until the Radarr fixture is corrected.**

The production design is sound. Repository inspection confirms configuration identity changes clear gate evidence, and a refused fetch becomes an unavailable hold. Remaining issues concern test setup and execution instructions rather than unsafe completion decisions.

## Consensus Summary (cycle 2)

HIGH: none. MEDIUM: 1 — 128-03 TestBadKeyFailsSafe Radarr test lacks a valid radarr_url (MagicMock URL would fail parsing before the key check). LOW: 128-01 Task 2 <done> still says rule 'exists once' in wave 1; 128-04 verify reruns coverage; optional stronger transition test.

---

## Codex Review — Cycle 3 (after revision 150d24c6)

## 1. Summary

The cycle-2 **MEDIUM Radarr fixture issue is resolved**. The diff introduces **no new HIGH, MEDIUM, or LOW findings**.

The premature single-definition claim and duplicate phase-gate verification are corrected. Some previously noted LOW concerns remain nonblocking. This was a read-only review against the supplied plans and relevant repository files; tests were not run.

## 2. Status of cycle-2 concerns

| Concern | Status | Assessment |
|---|---|---|
| **MEDIUM:** Radarr fixture lacks a valid URL | **Resolved** | Setup now supplies a real HTTP URL. The test also requires the key-specific warning and excludes the URL-scheme warning, proving it exercises the intended branch. |
| **LOW:** Plan 01 claims a single definition too early | **Resolved** | Task 2 now explicitly defers caller migration and removal of the old constant to plan 02, with the invariant checked in plan 04. |
| **LOW:** Repeated full-suite runs | **Resolved for task verification; partially outstanding overall** | The explicit reuse rule removes the action/verification duplicate when Python files are unchanged. `128-VALIDATION.md` still requires full-suite runs after every wave; that broader sampling cost remains. |
| **LOW:** Restrictive source-layout assertions | **Retained, nonblocking** | The new assignment instructions make the existing AST check predictable, but preserve rather than remove its implementation constraints. |
| Optional stronger transition test | **Unchanged, nonblocking** | The empty-queue transition proves cached snapshot invalidation. Previously authorizing evidence or an outstanding request would provide stronger coverage, but was an optional suggestion. |

## 3. New Concerns

**None identified in the diff.**

The corrected Test Connection routes match repository registration. The pending-row pattern excludes the status legend, and the separate Approval check covers the remaining pending marker. The gate-result reuse instructions require recorded evidence and unchanged Python files.

## 4. Risk Assessment

**LOW.** The localized fixture blocker is fixed, and the revisions add no apparent correctness or security regression. The plans are ready for execution; remaining concerns concern test-maintenance flexibility and verification cost.

## Consensus Summary (cycle 3)

HIGH: none. MEDIUM: none. Cycle-2 MEDIUM (Radarr fixture URL) resolved. Remaining LOWs nonblocking (AST source-layout constraint, per-wave full-suite sampling cost, optional stronger transition test). Risk LOW; plans ready for execution.
