---
phase: 122-safety-acceptance-and-logging-fixes
verified: 2026-10-23T22:15:09Z
status: gaps_found
score: 3/5 must-haves verified
has_blocking_gaps: true
overrides_applied: 0
gaps:
  - truth: "No newly visible log line (introduced by attaching web handler loggers to the app logger tree) ever exposes a secret, token or auth header (122-02-PLAN.md D-14 must-have; ROADMAP Phase 122 goal 'log messages stop misleading operators' implies they must not also leak secrets)"
    status: failed
    severity: blocking
    reason: >
      CR-01 (code review, independently reproduced here). ConfigHandler._test_arr_connection's
      bare `except Exception: self.logger.exception(...)` (config.py:195-196) is now attached to
      the app logger tree by LOG-01 (context.logger.getChild("ConfigHandler")), so its traceback
      reaches both the persisted RotatingFileHandler log file and the SSE UI log stream. When
      `requests` raises `InvalidHeader` for an Arr API key containing whitespace or a newline
      (confirmed with a real `requests.get` call: `_validate_header_part` embeds the raw header
      value in the exception message), `logger.exception` logs the full traceback including that
      literal key. Independently reproduced end-to-end through the real `ConfigHandler` method
      and the same plain `logging.Formatter` the app's RotatingFileHandler uses: the key appeared
      verbatim in the formatted record. Neither the RotatingFileHandler formatter nor
      `SerializeLogRecord._redact_sensitive` (web/serialize/serialize_log_record.py) redacts
      `X-Api-Key` values — its four patterns only cover lftp `-u`, `password=`, and SSH
      `user@host` text. This violates the project's absolute rule "never log sensitive data
      (... tokens ..., auth headers)". The existing regression test
      (`test_config_unexpected_error_logged_without_api_key` in
      test_web_app_builder_logging.py) only forces `RuntimeError("boom")`, which never contains
      a key, so it passes without ever exercising the real leak path — confirmed by reading the
      test and the 122-02-SUMMARY.md D-14 review table, which reviewed format-string
      interpolations per call site but did not consider that `logger.exception`'s traceback can
      itself carry a caller-controlled value from a downstream library exception.
    artifacts:
      - path: "src/python/web/handler/config.py"
        issue: "Lines 155-196: _test_arr_connection sends the raw API key via a header with no stripping/character validation before the request, then logs the exception traceback (not just the type) on any unexpected error, now routed to the persisted app log and UI stream"
      - path: "src/python/tests/unittests/test_web/test_web_app_builder_logging.py"
        issue: "test_config_unexpected_error_logged_without_api_key uses RuntimeError('boom') as the injected failure, which can never contain the key, so it gives false confidence against the actual InvalidHeader leak path"
    missing:
      - "Stop logging the exception message/traceback from this boundary (log only type(e).__name__), and/or validate and strip the key's character shape before building the request so InvalidHeader can never be raised from a stored key"
      - "Add a regression test that triggers a real requests.exceptions.InvalidHeader (or an exception whose str() embeds a known key) and asserts the key is absent from both the formatted record and the SSE-serialized record"
      - "Audit other logger.exception sites now reachable under the app logger for outbound Sonarr/Radarr requests (sonarr5/arr_queue clients) for the same pattern"

  - truth: "A kept pending import notice is bounded to the 'transfer ended, awaiting commit' window, not any non-transferring state with a remote copy (122-10-PLAN.md D-06c must-have: 'discarded on expiry, ambiguity, path change, generation change, root removal or a root that has lost its remote copy')"
    status: failed
    severity: blocking
    reason: >
      WR-02 (code review, confirmed by direct code read). controller.py's `post_transfer_pending`
      (~line 806-816) requires only that the (root, matched) key is already in
      `__pending_child_notices` and `root_file.remote_size is not None` — it does not check the
      root's current state or how long ago it left DOWNLOADING/QUEUED. Confirmed by reading
      `_revalidate_pending_notice` (~line 1000-1040): discard triggers are limited to lifecycle
      generation change, an ambiguous match, the resolved path changing, and 6-hour TTL expiry
      (`_PENDING_NOTICE_TTL_SECS = 6 * 3600`); there is no `last_transferring_at` tracking anywhere
      in the file (grepped, none found). So a pending notice now survives — and can be credited —
      for up to 6 hours when the user stops the transfer (root goes DEFAULT with a partial local
      copy) or deletes the local copy while the remote remains (does not bump the lifecycle
      generation), not only in the intended "lftp job ended, local scan lagging" window the
      docstrings (lines 683-685, 786-804) describe. The new tests added by 122-10 only cover the
      DEFAULT-with-scan-lag and remote-loss shapes, not stopped-root or local-deleted-root. The
      current 122-SAFE01-EVIDENCE.md D-06(c) PASS verdict (both the original run and the "Plan 12"
      rerun) exercised only the intended race window and does not exercise this wider gap.
    artifacts:
      - path: "src/python/controller/controller.py"
        issue: "post_transfer_pending (~line 806) has no bound on root state or elapsed time since last-transferring; only remote_size is checked"
    missing:
      - "Track when a root was last seen transferring (e.g. a per-root last_transferring_at set while DOWNLOADING/QUEUED) and only allow post_transfer_pending within a short grace period after that, not the full 6h TTL"
      - "Discard pending notices on delete-local and on user-stop; add regression tests for stopped-root and local-deleted-root shapes"
      - "Per owner decision (2026-10-23): a narrowed fix, plus a D-06(c) sandbox rerun on the new build, before the current PASS verdict can be relied on"

  - truth: "Log wording for the import-credit path names what actually happened (phase goal: log messages stop misleading operators), consistent with the pattern already used for __keep_pending_notice's reason parameter"
    status: failed
    severity: minor
    reason: >
      WR-03 (code review, confirmed by direct code read). `__credit_early_child` (~line 958-977)
      always logs the static string "Credited early import of '{}' in '{}' (root still
      transferring)" regardless of why it was called. Since 122-10, it is also reached via the
      post_transfer_only path, where the root is explicitly NOT transferring — the caller already
      computes a correct, differentiated reason string for the sibling call to
      `__keep_pending_notice` (`reason="transfer finished, awaiting commit" if post_transfer_only
      else "root still transferring"`) but does not pass an equivalent reason into
      `__credit_early_child`. These lines are used directly in NAS log forensics and Phase 120/122
      evidence greps, so the false "(root still transferring)" text is operator-misleading in
      exactly the way this phase's goal targets. In scope per owner decision alongside CR-01/WR-01/WR-02.
    artifacts:
      - path: "src/python/controller/controller.py"
        issue: "__credit_early_child (~line 958) hardcodes '(root still transferring)' with no reason parameter, unlike the parallel __keep_pending_notice which already takes one"
    missing:
      - "Add a reason parameter to __credit_early_child (default 'root still transferring' to keep existing greps matching) and pass reason='transfer finished, awaiting commit' when post_transfer_only"

  - truth: "LOG-01 migrates every in-scope web-handler rate-limit warning to the app logger; no live endpoint still falls back to a detached logger for the exact class of loss LOG-01 was meant to fix"
    status: failed
    severity: minor
    reason: >
      WR-01 (code review, confirmed by direct code read). `StatusHandler.__init__` takes only
      `status` (web_app_builder.py: `StatusHandler(context.status)`), has no `self.logger`, and
      `status.py:16`'s `rate_limit(max_requests=60, window_seconds=60.0)` call omits `logger=`.
      `rate_limit()`'s `logger` parameter defaults to `None` and falls back to
      `globals()["logger"]` (`logging.getLogger("web.rate_limit")`, module-level, detached from
      the `seedsyncarr` app logger tree) — confirmed in rate_limit.py. So `/server/status`'s "Rate
      limit exceeded" warning still does not reach the persisted app log or the UI log stream.
      122-02-PLAN.md explicitly scoped status.py out of D-13 (confirmed by 122-02-SUMMARY.md: "`git
      diff HEAD~1 -- web/handler/status.py` → empty (untouched, as required...)"), so this is not
      a regression against that plan's own declared scope, but the owner's 2026-10-23 decision
      brings it into scope for this phase because any future bare `rate_limit(...)` call silently
      repeats the same detached-logger mistake LOG-01 exists to fix.
    artifacts:
      - path: "src/python/web/handler/status.py"
        issue: "StatusHandler constructed with only status, no context/logger; its rate_limit call has no logger= kwarg"
      - path: "src/python/web/rate_limit.py"
        issue: "logger parameter stays optional with a silent detached-logger fallback, so a future caller can repeat this mistake without any error"
    missing:
      - "Give StatusHandler the context logger and pass logger=self.logger at its rate_limit call site"
      - "Consider making logger a required keyword argument of rate_limit to prevent recurrence (review Info item IN-02 in 122-REVIEW.md as a related cleanup)"
human_verification: []
---

# Phase 122: Safety Acceptance and Logging Fixes Verification Report

**Phase Goal:** The Phase 119 safety behaviors are proven on a running build, the two open incident records say truthfully what is fixed and what is not, and the two log messages found in Phase 120 stop misleading operators
**Verified:** 2026-10-23T22:15:09Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | SAFE-01: extraction, import and auto-delete checks each pass on a running build with recorded evidence | ✗ FAILED (evidence rests on an incomplete fix) | `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` records D-06(a)-(e)/D-07 all PASS on `DEV_PIN sha256:e3941f976b5bf...`, confirmed substantive (not a stub: specific timestamps, log lines, byte sizes, persist-file contents throughout). However, WR-02 and WR-03 (confirmed in code, see Gaps) show the D-06(c) fix underlying that PASS verdict is narrower in scope than it should be and has an inaccurate log line; owner decision (2026-10-23) requires a narrowed fix plus a sandbox rerun before this verdict can be relied on for the shipping build |
| 2 | SAFE-02: both incident records distinguish verified-fixed from remaining operator cleanup; neither closed solely because code shipped | ✓ VERIFIED | `.planning/debug/resolved/done-group-no-auto-delete.md` and `.planning/debug/resolved/extract-staging-autodel-rearm.md` both read directly: per-finding "Reconciliation (Phase 122)" tables with "verified fixed (evidence)" rows linking to 122-SAFE01-EVIDENCE.md sections and commit hashes, deferred items C-G explicitly marked "deferred — carried to ROADMAP.md Backlog" (confirmed present under `## Backlog` in ROADMAP.md with matching item names), owner's verbatim "All confirmed" recorded, both files have `status: resolved` and live in `.planning/debug/resolved/` |
| 3 | LOG-01: a webhook Test event produces a `<source> webhook test event received` INFO line under the app logger, regression test fails-before/passes-after | ✗ FAILED (mechanism works, but the change regressed security and left a gap) | Core mechanism confirmed in code: `webhook.py:140` `self.logger.info("{} webhook test event received"...)` on `self.logger = context.logger.getChild("WebhookHandler")`; targeted test run (262 tests across the 7 phase-touched files) all pass. But CR-01 (confirmed, reproduced independently) shows the same "attach handler loggers to the app logger" change leaks the Arr API key through `ConfigHandler`'s exception path, and WR-01 (confirmed) shows `StatusHandler`'s rate-limit warning was never migrated |
| 4 | LOG-02: completion gate logs "dropped (reason)" for prune/no-arr removals, "cleared" only for proof-based release | ✓ VERIFIED | `completion_gate.py:427-446` `_clear_hold(name, drop_reason=None)`: `drop_reason is None` → `"Completion hold cleared for '%s'"` (proof-based release only, byte-identical to old wording per docstring); else → `"Completion hold dropped for '%s' (%s)"`. Called with `drop_reason=` only from the prune loop (line 236) and the no-arr-enabled loop (line 208); called with no `drop_reason` only from `_record`'s proof-based release (line 416). Root names pass through `sanitize_log_value`. `test_completion_gate.py` tests run and pass |
| 5 | Phase 119 import safeguards (early credit, pending-notice revalidation, arm-on-commit, Waiting holds, one-shot manual release) are exercised, not rebuilt | ✓ VERIFIED | 122-SAFE01-EVIDENCE.md's "Plan 12: D-06 rerun on the fixed build" and "Plan 06" sections show each safeguard exercised live with log-line/persist-file evidence (Waiting hold + one-shot release D-06(e), early credit D-06(a), restart persistence D-06(d)); the Phase 119 code paths themselves (`__credit_early_child`, `__keep_pending_notice`, arm-on-commit loop) are modified only by the in-scope 122-10 D-06(c) gap-closure addition, not rebuilt |

**Score:** 3/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/python/controller/completion_gate.py` | `_clear_hold` cleared/dropped wording split (LOG-02) | ✓ VERIFIED | Exists, substantive, wired into `_run` prune/no-arr loops and `_record`'s proof-based release; tests pass |
| `src/python/web/handler/webhook.py` | WebhookHandler logs under app logger (LOG-01) | ✓ VERIFIED | `context.logger.getChild("WebhookHandler")`; "webhook test event received" INFO line present and tested |
| `src/python/web/handler/config.py` | ConfigHandler logs under app logger (LOG-01) | ⚠️ VERIFIED-WITH-REGRESSION | Logger attachment is wired, but `_test_arr_connection`'s `except Exception: self.logger.exception(...)` now leaks the Arr API key into the persisted log/UI stream on an InvalidHeader (CR-01, confirmed) |
| `src/python/web/handler/status.py` | Rate-limit warning reaches app logger | ✗ NOT WIRED | `StatusHandler` has no logger; `rate_limit()` call at line 16 has no `logger=` kwarg; falls back to the detached module logger (WR-01, confirmed) |
| `src/python/web/rate_limit.py` | `rate_limit(max_requests, window_seconds, logger=None)` | ✓ VERIFIED (exists, substantive) | Confirmed present with the fallback-to-module-logger behavior that produces WR-01 when `logger` is omitted |
| `src/python/controller/controller.py` | D-06(c) post-transfer pending-notice window (122-10 gap closure) | ⚠️ STUB-LIKE GAP | `post_transfer_pending` and `_revalidate_pending_notice` exist and are wired into `__check_webhook_imports`, and work for the intended scan-lag/remote-loss cases (tested), but the retention window is wider than the must-have requires (WR-02, confirmed) |
| `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` | Live sandbox evidence sections for all SAFE-01 scenarios | ✓ VERIFIED | 1267+ lines, section-by-section PASS verdicts with timestamps/log excerpts/persist contents; overall SAFE-01 verdict table present. Evidence is real and substantive; verdict will need a superseding entry once WR-02/WR-03 are fixed and rerun |
| `.planning/debug/resolved/done-group-no-auto-delete.md` | Per-finding reconciliation, Case A/Case B | ✓ VERIFIED | Reconciliation table present with evidence links; `status: resolved` |
| `.planning/debug/resolved/extract-staging-autodel-rearm.md` | Per-finding reconciliation, Bug 1/Bug 2/A/B/H + deferred C-G | ✓ VERIFIED | Reconciliation table present; deferred items C-G explicitly carried to ROADMAP Backlog (confirmed present there by name) |
| `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` | Code review of phase diff | ✓ VERIFIED | `status: issues_found`, CR-01/WR-01/WR-02/WR-03/IN-01/IN-02/IN-03/CV-01 all present; CR-01/WR-01/WR-02/WR-03 independently re-confirmed in this verification |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `WebhookHandler.__init__` | `seedsyncarr` app logger | `context.logger.getChild("WebhookHandler")` | ✓ WIRED | Confirmed; INFO line reaches `assertLogs("seedsyncarr", ...)` in tests |
| `ControllerHandler.__init__` | `seedsyncarr` app logger | `context.logger.getChild("ControllerHandler")` | ✓ WIRED | Confirmed by 122-02-SUMMARY.md grep evidence and test run |
| `ConfigHandler.__init__` | `seedsyncarr` app logger | `context.logger.getChild("ConfigHandler")` | ⚠️ WIRED-BUT-LEAKING | Wiring correct; the same wiring is the mechanism by which CR-01 now surfaces a secret that previously went only to a detached logger |
| `StatusHandler` rate-limit warning | `seedsyncarr` app logger | (expected: `logger=self.logger` at the `rate_limit(...)` call) | ✗ NOT WIRED | No such kwarg exists; confirmed falls back to `logging.getLogger("web.rate_limit")` (WR-01) |
| `CompletionGate._run` prune/no-arr loops | `_clear_hold(name, drop_reason=...)` | keyword argument | ✓ WIRED | Confirmed at lines 208, 236 |
| `CompletionGate._record` proof-based release | `_clear_hold(name)` | call with no `drop_reason` | ✓ WIRED | Confirmed at line 416 |
| `Controller.__check_webhook_imports` | `post_transfer_pending` branch | membership of `__pending_child_notices` + `remote_size is not None` | ⚠️ WIRED-BUT-OVERBROAD | Wired and functional for the intended case, but not bounded to the intended window (WR-02) |
| `post_transfer_only` branch | `__credit_early_child` reason text | (expected: a passed `reason` parameter) | ✗ NOT WIRED | No such parameter exists; the credited log line is a hardcoded string regardless of path (WR-03) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Targeted phase-touched unit tests (LOG-01, LOG-02, D-06c, status quo regressions) | `pytest tests/unittests/test_web/test_web_app_builder_logging.py tests/unittests/test_web/test_rate_limit.py tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_handler/test_controller_handler.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_controller/test_import_credit.py tests/unittests/test_sonarr5/test_sonarr5_system_status.py -q` | `262 passed, 15 subtests passed` | ✓ PASS |
| Whole-tree lint | `ruff check src/python/` (ruff 0.15.22, matching CI pin) | `All checks passed!` | ✓ PASS |
| Full unit suite (run once; baseline comparison) | `pytest tests/unittests -q` | `21 failed, 1787 passed, 3 errors` — all failures in `test_sshcp.py` (missing `testgroup` system group), `test_scanner.py::test_scan_file_with_latin_chars`, `test_scanner_process.py`, `test_extract_process.py` | ✓ PASS (matches orchestrator-reported baseline exactly; none touched by this phase) |
| CR-01 reproduction: does `requests` embed the key in `InvalidHeader`? | `requests.get(url, headers={"X-Api-Key": " SECRETKEY123\n"})` | Raises `InvalidHeader("Invalid leading whitespace, ... header value: ' SECRETKEY123\n'")` | ✓ CONFIRMS LEAK SOURCE |
| CR-01 reproduction: does the leak reach the real `ConfigHandler` + app-logger formatter path? | Direct call to `ConfigHandler._test_arr_connection` with a logger attached the same way `context.logger.getChild("ConfigHandler")` would, formatted with the same plain `Formatter` the RotatingFileHandler uses | Formatted record contains `SECRETKEY123` verbatim | ✓ CONFIRMS CR-01 END-TO-END |
| D-14 test's blind spot: does the existing regression actually exercise a key-bearing exception? | Read `test_config_unexpected_error_logged_without_api_key`: injected failure is `RuntimeError("boom")` | Never contains the key; assertion passes vacuously | ✓ CONFIRMS TEST GAP |
| `_redact_sensitive` coverage for API-key-shaped values | Read `serialize_log_record.py::_redact_sensitive` | Only 4 patterns: lftp `-u`, `password=`, `sftp://user@host`, bare `user@host` — none for `X-Api-Key` | ✓ CONFIRMS NO MITIGATION |
| WR-01: is `StatusHandler` given a logger anywhere? | Read `web_app_builder.py` (`StatusHandler(context.status)`) and `status.py` (`rate_limit(max_requests=60, window_seconds=60.0)`) | No `logger` attribute, no `logger=` kwarg | ✓ CONFIRMS WR-01 |
| WR-02: is there any time/state bound on `post_transfer_pending`? | Read `controller.py` `post_transfer_pending` definition and `grep -n "_PENDING_NOTICE_TTL_SECS\|last_transferring_at"` | Only the 6h TTL; no `last_transferring_at` tracking exists anywhere in the file | ✓ CONFIRMS WR-02 |
| WR-03: does `__credit_early_child`'s log line vary by path? | Read `__credit_early_child` | Hardcoded `"(root still transferring)"` string, no `reason` parameter | ✓ CONFIRMS WR-03 |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` style probes; SAFE-01 acceptance evidence was gathered through manual NAS-sandbox session scripts (`122-teardown.sh`, `122-webhook-post.sh`) documented and read directly in `122-SAFE01-EVIDENCE.md`, not through a repo-committed automated probe this verifier can re-run. Step 7b's unit/lint spot-checks above substitute for an automated probe on the parts of the phase that are code.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| SAFE-01 | 122-04, 05, 06, 07, 08, 10, 11, 12 | Extraction, import and auto-delete checks pass on a running build, with recorded evidence | ✗ BLOCKED | Live evidence in 122-SAFE01-EVIDENCE.md is real and substantive, but rests on a D-06(c) fix with a confirmed scope gap (WR-02) and an inaccurate log line (WR-03); REQUIREMENTS.md/ROADMAP.md mark this `[x] Complete`, which this verification does not confirm until the narrowing fix lands and D-06(c) is rerun per the owner's 2026-10-23 decision |
| SAFE-02 | 122-09 | Both incident records distinguish verified-fixed from remaining operator cleanup | ✓ SATISFIED | Confirmed directly in `.planning/debug/resolved/*.md` — see Observable Truth 2 |
| LOG-01 | 122-02, 04, 11 | Webhook handler INFO messages appear in the app log | ✗ BLOCKED | Core mechanism satisfied, but the same change introduced CR-01 (critical secret leak) and left WR-01 (incomplete coverage); REQUIREMENTS.md marks this `[x] Complete`, which this verification does not confirm |
| LOG-02 | 122-01, 03 | Completion gate logs distinct "dropped" vs "cleared" | ✓ SATISFIED | Confirmed directly in `completion_gate.py` and passing tests — see Observable Truth 4 |

No orphaned requirement IDs: all four phase requirement IDs (SAFE-01, SAFE-02, LOG-01, LOG-02) from `.planning/REQUIREMENTS.md`'s Phase 122 row are claimed by at least one plan's `requirements:` frontmatter, and every plan's `requirements:` entries are one of these four. Cross-referenced against `.planning/REQUIREMENTS.md` lines 17-18 and 37-38.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `src/python/web/handler/config.py` | 195-196 | `except Exception: self.logger.exception(...)` logging a traceback that can carry an upstream library's embedded secret | 🛑 Blocker | CR-01 — confirmed secret leak into persisted log + UI stream |
| `src/python/controller/controller.py` | ~806-816 | Permissive boolean condition (`post_transfer_pending`) with no state/time bound beyond a 6h TTL | 🛑 Blocker | WR-02 — widens an import-safety window beyond its documented and intended scope |
| `src/python/controller/controller.py` | ~958-963 | Hardcoded log string reused across two semantically different call paths | ⚠️ Warning | WR-03 — misleading operator-facing log line on the new path |
| `src/python/web/handler/status.py` / `src/python/web/rate_limit.py` | 16 / 22,29 | Optional parameter with a silent fallback to a detached logger | ⚠️ Warning | WR-01 — incomplete migration, risk of silent recurrence for future callers |

No `TBD`/`FIXME`/`XXX` debt markers found in the phase-touched files (grepped `completion_gate.py`, `controller.py`, `config.py`, `webhook.py`, `status.py`, `rate_limit.py`, `web_app_builder.py`). No placeholder/"coming soon" text found.

### Human Verification Required

None. All four gaps (CR-01, WR-01, WR-02, WR-03) are directly observable and independently confirmed in the codebase (not matters of visual judgment, real-time behavior, or external-service integration), and the owner has already made the relevant product decision (2026-10-23: fix all four in this phase, same PR #134, with a D-06(c) sandbox rerun on the new build). What remains is code-level gap closure, not a human-verification checkpoint.

### Gaps Summary

Phase 122 delivered substantial, well-evidenced work: SAFE-02's incident-record reconciliation is complete and directly verifiable in the resolved debug files, LOG-02's completion-gate wording split is correctly implemented and tested, and the SAFE-01 live sandbox acceptance run (122-SAFE01-EVIDENCE.md) is genuine, substantive evidence — not a documentation-only claim. Phase 119's safeguards were exercised, not rebuilt.

However, the phase's own code review (122-REVIEW.md, 2026-10-23) found a critical security regression and three correctness/completeness gaps, all independently reproduced in this verification:

1. **CR-01 (blocking):** Implementing LOG-01 (attaching previously-detached web handler loggers to the app logger tree) had a side effect the plan did not anticipate: `ConfigHandler`'s existing `logger.exception(...)` call on the Arr-connection-test failure path now writes a full traceback to the persisted app log and the UI log stream. Reproduced here end-to-end: a key containing whitespace/newline causes `requests` to raise `InvalidHeader` with the raw key embedded in its message, and nothing in the logging pipeline (RotatingFileHandler's plain formatter, or `SerializeLogRecord._redact_sensitive`'s narrow lftp/password/ssh patterns) redacts it. This directly violates the project's absolute "never log sensitive data" rule. The regression test that was supposed to guard this (`test_config_unexpected_error_logged_without_api_key`) only injects a `RuntimeError`, so it provides no real protection.

2. **WR-02 (blocking):** The D-06(c) gap-closure fix (122-10), which exists specifically to keep a pending import notice bounded to the window between "transfer ends" and "commits," is implemented more broadly than its own must-haves require: it has no bound on root state or elapsed time beyond the pre-existing 6-hour TTL, so a stopped transfer or a user-deleted local copy can also be covered by the same "keep or credit" logic for up to 6 hours. The 122-SAFE01-EVIDENCE.md D-06(c) PASS verdict (both the original run and the Plan 12 rerun) only exercised the intended scan-lag race, not this wider case.

3. **WR-03 (minor, in scope per owner):** The import-credit log line that is reused on the new post-transfer path still unconditionally claims "(root still transferring)," which is false on that path — a new instance of exactly the kind of misleading operator-facing log message this phase exists to eliminate.

4. **WR-01 (minor, in scope per owner):** `StatusHandler`'s rate-limit warning was never migrated to the app logger (the plan explicitly scoped this out of D-13, but the owner has decided it should be fixed alongside the other three issues in this same phase/PR).

Per the owner's 2026-10-23 decision ("Key leak + log fixes + narrow D-06(c) (Recommended)"), all four items are to be fixed in this same phase and PR #134, with a D-06(c) sandbox rerun on the resulting build before SAFE-01's verdict can be considered final. Until that gap-closure work lands, SAFE-01 and LOG-01 cannot be marked satisfied, even though REQUIREMENTS.md and ROADMAP.md currently show both as `[x] Complete`.

Items explicitly out of scope for this verification (per the orchestrator's instructions): IN-01 (duplicate DEBUG lines), IN-02 (`globals()["logger"]` workaround), IN-03 (redundant `config`/`context` constructor arguments), and CV-01 (import-relativity false positive) — these are informational/convention findings in 122-REVIEW.md that the owner did not select for in-phase fixing; they remain available as optional follow-up cleanup, not phase gaps.

---

_Verified: 2026-10-23T22:15:09Z_
_Verifier: Claude (bm-verifier)_
