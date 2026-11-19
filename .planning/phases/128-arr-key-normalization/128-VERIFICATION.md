---
phase: 128-arr-key-normalization
verified: 2026-11-19T11:33:31Z
status: human_needed
score: 15/16 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
human_verification:
  - test: "Push the branch (or open the phase PR) and read the Linux CI result for the Python job: full pytest, whole-tree `ruff check src/python/`, and the coverage gate (`fail_under = 88`)."
    expected: "All three pass on Linux CI, with total coverage at or above 88%."
    why_human: "The coverage gate cannot be reproduced on this Mac. The CI-only modules (extract, scan, lftp, sshcp) cannot run here, so the local total is 86.47% against 86.39% at the phase base. The branch has no upstream and no PR yet, so there is no CI run to read."
---

# Phase 128: Arr Key Normalization Verification Report

**Phase Goal:** A Sonarr/Radarr API key behaves the same whether it is being saved, tested, or used for a live queue check, regardless of incidental whitespace
**Verified:** 2026-11-19T11:33:31Z
**Status:** human_needed
**Re-verification:** No (initial verification)

## Goal Achievement

The goal is met in the code. One item is open and it is not about the arr code: the 88% coverage gate has to be confirmed by Linux CI, and the branch has not been pushed yet.

Evidence below comes from reading the code at HEAD (`31d013e0`), running the phase tests, and running a verifier-written probe that was not part of the phase. The SUMMARY files were not used as evidence.

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | **Roadmap SC1.** Save, Test Connection and queue checks use one normalization rule; a padded key is saved normalized, using Test Connection's rule | VERIFIED | `common/arr_api_key.py` holds the only definition. `web/handler/config.py` calls `normalize_arr_api_key` + `is_valid_arr_api_key` in both `__handle_set_config` and `_test_arr_connection`; `controller/arr_queue.py` calls them in `enabled_targets` and `start_fetch`. Verifier probe: saving `" \t<key>\r\n "` through `POST /server/config/set` stored the bare key for both Sonarr and Radarr, and Test Connection and the queue client then both sent that exact key as `X-Api-Key`. |
| 2 | **Roadmap SC2.** A previously saved padded key works for queue checks without resaving; regression fails before the fix and passes after | VERIFIED | Verifier probe: a padded key written straight into the live config (not through Save) was sent trimmed by the queue client. Fail-before reproduced independently: with the pre-phase `arr_queue.py` and `config.py` (commit `2f2b1576`) in a scratch copy, `test_padded_in_memory_key_is_sent_normalized` and both live-config parity tests fail; they pass at HEAD. |
| 3 | **Roadmap SC3.** An empty or invalid key in queue checks produces no unsafe import or deletion decision, and no key value appears in logs | VERIFIED | `start_fetch` returns `None` before any thread or request. `completion_gate.py` line 220 (`if fid is None`) records a failure, so the item is held as `<code>_unavailable`. `completion_gate.py` is unchanged in the phase diff. Verifier probe: for `""`, `None`, whitespace-only, inner space, non-ASCII, NUL and a number, no request was made and no thread was created, and no captured log line at any level contained the key. `TestBadKeyFailsSafe` (5 tests) passes. |
| 4 | Shared rule lives in `common/arr_api_key.py`, is importable from the `common` barrel, and is the single definition in the tree | VERIFIED | Barrel import works. `grep -rl API_KEY_CHARS` over non-test Python lists only `common/arr_api_key.py` and `common/__init__.py`. `_API_KEY_CHARS` count in `web/handler/config.py` is 0. |
| 5 | `normalize_arr_api_key` / `is_valid_arr_api_key` semantics; rule table pinned and exported as `RULE_CASES` | VERIFIED | Code read: non-str gives `""` / `False` without raising. `test_arr_api_key.py` passes; the parity test imports `RULE_CASES` from it. |
| 6 | D-03: a key still invalid after trimming is refused with 400 "`<Svc>` API key contains invalid characters"; stored key unchanged; value not echoed | VERIFIED | Handler code plus verifier probe (inner space, line break, non-ASCII): 400 each time, stored key still `goodKEY1`, submitted value absent from the response. |
| 7 | D-04: a whitespace-only key is refused with 400 "Invalid request body"; stored key unchanged | VERIFIED | Handler code plus verifier probe (`"   "`, `"\n"`). |
| 8 | Test Connection uses the shared rule; both error strings unchanged; no private regex left | VERIFIED | The phase diff of `_test_arr_connection` changes only the two rule lines; "API key is required" and "API key contains invalid characters" are untouched. Existing Test Connection tests pass. |
| 9 | D-07: every `Config.secret_fields()` property confirms as "`<section>.<key>` updated" and never echoes the value, on success or refusal; non-secret properties keep "set to `<value>`" | VERIFIED | Handler code: `is_secret` branch returns "updated"; a refused secret returns "Invalid value for ..." and logs only the exception type. `secret_fields()` returns webhook_secret, api_token, remote_password and both arr keys. Verifier probe: the value was absent from responses and from all log lines for those properties. `grep -c 'set to {}'` is 1 (non-secret branch only). |
| 10 | A padded key and its trimmed form give the same `ArrTarget.identity` (no spurious gate reset) | VERIFIED | The key is trimmed in `enabled_targets` before the target is built, so the identity token is computed on the trimmed key. `test_padded_key_and_trimmed_key_share_identity` passes at HEAD and fails against the pre-phase code. |
| 11 | D-06: on a missing or invalid key `start_fetch` returns `None`, starts no worker, makes no request; gate holds as unavailable | VERIFIED | See truth 3. |
| 12 | D-06: skip logs "`<Label>` queue check skipped: API key is missing or invalid" at WARNING once per key value per arr, DEBUG for repeats, WARNING again after the key changes or a valid key is seen | VERIFIED | `__key_skip_warned` keyed by arr code, compared by opaque key token, cleared when a valid key is seen. Four warn-once tests pass at HEAD and fail against the pre-phase code. |
| 13 | Changing a working key to a missing or invalid one discards evidence fetched with the old key | VERIFIED | Key change alters `ArrTarget.identity`, which triggers `_reset_integration_state` in the gate. `test_bad_key_after_valid_key_discards_cached_evidence` passes. |
| 14 | String-input parity: for every non-empty string row of the rule table, Save, Test Connection and the queue check give the same accept/reject verdict | VERIFIED | `test_arr_key_parity.py` runs the table over one real Config through all three paths and passes. All three paths apply the same two functions to the same value (code read). |
| 15 | Non-string input is handled by each path's own guard (as amended by review WR-01: Save refuses non-text values) | VERIFIED (amended) | The plan text said Save turns a number into text (`12345` saved as `"12345"`). Review WR-01 replaced that: Save now answers 400 "Invalid request body" for any non-text value and keeps the stored key (commits `ebb52e1f`, `31d013e0`). Verifier probe: `True`, `False`, `0`, `12345`, `[]`, `{}`, `["a"]`, `1.5` were all refused and the stored key was unchanged. This is stricter and safer than the plan and brings Save in line with the queue client, which already treats a non-text key as missing. Tests were updated to match (`test_set_arr_key_non_string_value_is_refused`, parity boundary case). See note below. |
| 16 | Phase gate on the combined branch: full pytest green, whole-tree ruff clean, coverage at or above 88 | UNCERTAIN (`unverifiable_runtime`) | Ruff whole-tree: clean (run by verifier). Phase and neighbouring test modules: 753 passed, 216 subtests (run by verifier). Phase files measured at 100% (`common/arr_api_key.py`), 98% (`controller/arr_queue.py`), 97% (`web/handler/config.py`); the uncovered lines are not lines this phase added. The total-coverage gate cannot be reproduced on macOS and there is no CI run to read: the branch has no upstream and no PR. |

**Score:** 15/16 truths verified

**Note on truth 15.** No formal override is recorded for the superseded "12345 is stringified" clause, and none was invented here. The deviation tightens behaviour, was made in response to a code-review warning, and has no effect on the settings page (the Angular client always sends text). If the owner wants the deviation on record, add this to the frontmatter:

```yaml
overrides:
  - must_have: "Save turns a number into text (12345 is saved as '12345')"
    reason: "Superseded by review WR-01: Save refuses non-text Sonarr/Radarr key values with 400 and keeps the stored key"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
```

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/python/common/arr_api_key.py` | `ARR_API_KEY_CHARS`, `normalize_arr_api_key`, `is_valid_arr_api_key` | VERIFIED | 24 lines, real logic, used by both production call sites |
| `src/python/common/__init__.py` | Barrel re-export | VERIFIED | Line 2 re-exports all three names |
| `src/python/web/handler/config.py` | Save trim/refuse, secret-free responses, Test Connection on shared rule | VERIFIED | `_ARR_KEY_PROPS` present; wired in `__handle_set_config` and `_test_arr_connection` |
| `src/python/controller/arr_queue.py` | Normalize on read, validate-and-skip with warn-once | VERIFIED | Wired in `enabled_targets` and `start_fetch`; `Controller` builds the client from the same `context.config` the web handler writes to |
| `tests/unittests/test_common/test_arr_api_key.py` | Rule table and `RULE_CASES` | VERIFIED | Passes; imported by the parity test |
| `tests/unittests/test_web/test_handler/test_config_handler.py` | Save and secret-response unit tests | VERIFIED | Passes; includes the WR-01 refusal test |
| `tests/integration/test_web/test_handler/test_config.py` | Real-Config ARR-01 and D-07 tests | VERIFIED | Passes; fails against pre-phase code |
| `tests/unittests/test_controller/test_arr_queue.py` | ARR-02 regression, identity, ARR-03 skip tests | VERIFIED | 9 phase tests enumerated and passing |
| `tests/unittests/test_controller/test_completion_gate.py` | Gate fail-safe with the real client | VERIFIED | `TestBadKeyFailsSafe`, 5 tests passing |
| `tests/integration/test_web/test_handler/test_arr_key_parity.py` | Cross-path parity over a real Config | VERIFIED | Passes; 3 of its tests fail against pre-phase code |
| `128-VALIDATION.md` | Filled verification map and sign-off | VERIFIED | `nyquist_compliant: true`; records the local coverage shortfall honestly |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `common/__init__.py` | `common/arr_api_key.py` | re-export line | WIRED | Import from barrel succeeds |
| `config.py` `__handle_set_config` | shared rule | `normalize_arr_api_key(value)` for `_ARR_KEY_PROPS` pairs | WIRED | The call now takes `value` (after the `isinstance(value, str)` guard) instead of `value_str`; same effect for text input |
| `config.py` `__handle_set_config` | `Config.secret_fields()` | membership test | WIRED | Decides "updated" versus "set to" |
| `config.py` `_test_arr_connection` | `is_valid_arr_api_key` | replaces private regex | WIRED | |
| `arr_queue.py` `enabled_targets` | `normalize_arr_api_key` | wraps both config reads | WIRED | Lines 174, 178 |
| `arr_queue.py` `start_fetch` | `is_valid_arr_api_key` | after URL check, before in-flight check | WIRED | |
| `start_fetch` returning `None` | `completion_gate._record_failure` | existing `if fid is None` branch | WIRED | Gate file unchanged |
| Web handler and queue client | one Config object | `context.config` | WIRED | `web_app_builder.py:33` and `controller.py:210` both use the same context, so a saved key is the key the queue check reads |

### Data-Flow Trace (Level 4)

Not applicable: no artifact in this phase renders dynamic data. The equivalent check (saved value reaches the outbound `X-Api-Key` header on both paths) is covered by truth 1.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Padded key saved trimmed; all three paths send the same key (Sonarr and Radarr) | Verifier probe `test_save_trims_and_three_paths_agree` | passed | PASS |
| Padded key in live config works for queue check without resaving | Verifier probe `test_live_padded_key_without_resave` | passed | PASS |
| Bad saves (whitespace-only, invalid characters, 8 non-text values) refused; stored key kept; value not echoed | Verifier probe `test_bad_saves_keep_stored_key` | passed | PASS |
| Queue check skips on 7 kinds of bad key: no request, no thread, no key in logs | Verifier probe `test_queue_skips_on_bad_key_no_request_no_leak` | passed | PASS |
| Secret saves never echo the value in response or logs | Verifier probe `test_secret_saves_never_echo` | passed | PASS |
| Regression fails before the fix | Phase tests against a scratch copy with pre-phase `arr_queue.py` and `config.py` | 18 failed, 3 passed | PASS (fails before, as required) |
| Phase and neighbouring test modules | `poetry run pytest` on test_common/test_arr_api_key, test_controller/test_arr_queue, test_completion_gate, test_web (unit and integration), test_sonarr5, test_seedsyncarr | 753 passed, 216 subtests | PASS |

The full workspace suite was not re-run by the verifier because of the known macOS limits (extract tests hang; scan, lftp, sshcp and one scanner test fail for environment reasons). 128-VALIDATION.md records the last local full run as 1952 passed, 62 skipped, 12 failed, all 12 in those CI-only modules.

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| 01: rule tests | `pytest tests/unittests/test_common/test_arr_api_key.py` | passed (in the 753 run) | PASS |
| 01: barrel import | `python -c "from common import ARR_API_KEY_CHARS, normalize_arr_api_key, is_valid_arr_api_key"` | exit 0 | PASS |
| 02: no private regex | `grep -c '_API_KEY_CHARS' src/python/web/handler/config.py` | 0 | PASS |
| 02: one "set to" branch | `grep -c 'set to {}' src/python/web/handler/config.py` | 1 | PASS |
| 03: gate untouched | `git diff --stat 2f2b1576..HEAD -- src/python/controller/completion_gate.py` | empty | PASS |
| 04: single definition | `grep -rl 'API_KEY_CHARS' src/python --include='*.py' \| grep -v '/tests/'` | exactly the two expected files | PASS |
| 04: parity module | `pytest tests/integration/test_web/test_handler/test_arr_key_parity.py` | passed (in the 753 run) | PASS |
| All plans: ruff | `ruff check src/python/` | All checks passed | PASS |
| 04: full pytest and coverage at or above 88 | `poetry run pytest --cov -q` | not reproducible on macOS; no CI run yet | SKIP (routed to human verification) |

No `scripts/*/tests/probe-*.sh` files are declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| ARR-01 | 128-01, 128-02, 128-04 | A key entered with leading/trailing whitespace is saved normalized, using Test Connection's rule | SATISFIED | Truths 1, 6, 7, 8 |
| ARR-02 | 128-01, 128-03, 128-04 | A previously saved padded key works for queue requests without resaving; one consistent rule on all three paths | SATISFIED | Truths 1, 2, 10, 14 |
| ARR-03 | 128-03, 128-04 | An empty or invalid key fails safely in queue checks; no key value in logs | SATISFIED | Truths 3, 11, 12, 13 |

All three IDs mapped to Phase 128 in REQUIREMENTS.md are claimed by at least one plan. No orphaned requirements. The boxes are still unticked in REQUIREMENTS.md by design (the orchestrator ticks them after verification); that is not counted as a gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | - | No TBD, FIXME, XXX, TODO, HACK or placeholder markers in any of the 10 files changed by the phase | - | - |

Informational, from the code review, not blocking:

- **Settings page shows the padded value until reload (review SA-01).** After a save, the Angular client keeps what the user typed in its local copy, while the server stores the trimmed key. Display only: Test Connection and the queue check both use the server's trimmed copy. UI changes are out of scope for this phase. Needs an owner ruling: accept, or schedule a follow-up.
- **Only `enabled_targets` trims the key (review IN-01).** `start_fetch` validates but does not trim. `enabled_targets` is the only production place that builds a target, so there is no live effect; a future second caller passing a raw padded key would be skipped (fail-safe) rather than trimmed.
- **Refused secrets give a generic message (review IN-02).** A refused `lftp.remote_password` now says "Invalid value for lftp.remote_password" rather than "is empty". Acceptable under D-07.
- **Typo in REQUIREMENTS.md line 24:** "padded key is works for queue requests".

### Human Verification Required

### 1. Linux CI gate for the phase branch

**Test:** Push `gsd/phase-128-arr-key-normalization` (or open the phase PR) and read the Python CI job result: full pytest, whole-tree `ruff check src/python/`, and the coverage gate.
**Expected:** All pass, with total coverage at or above 88%.
**Why human:** The CI-only modules cannot run on this Mac, so the local total is 86.47% (86.39% at the phase base). The branch has no upstream and no PR, so no CI result exists yet. Nothing found in this verification suggests the gate will fail: the phase's own files are at 97 to 100% and the phase raised the local total slightly.

### Gaps Summary

No gaps in the phase goal. Every roadmap success criterion and all three requirements are met in the code, confirmed by reading the code, by the phase tests, by a verifier-written probe against the real config, handler and queue client, and by reproducing the regression failing against the pre-phase code.

One must-have is unresolved for a reason outside the arr code: the coverage part of the phase gate needs a Linux CI run, which does not exist yet because the branch is unpushed.

The live padded-key queue check on a release image is Phase 130's smoke test and is not part of this phase.

---

_Verified: 2026-11-19T11:33:31Z_
_Verifier: Claude (bm-verifier)_
