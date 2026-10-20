---
phase: 120-sonarr-5-compatibility
plan: 03
subsystem: testing
tags: [sonarr5, test-connection, webhook, fixtures, hmac]
requires:
  - phase: 120-01
    provides: Sonarr 5 fixture loader (fixtures.py) and placeholder fixtures
provides:
  - SON5-01 CI tests driving ConfigHandler Test Connection with the system_status fixture
  - SON5-03 CI tests driving the webhook route (raw bytes, HMAC) and a real WebhookManager with decoys
affects: [120-06]
tech-stack:
  added: []
  patterns:
    - "Fixture helpers imported via module (`fixtures.tested_version()`) so pytest never collects a `test*`-named helper"
    - "Expected names/versions derived from fixture content, never literals, so live-capture swap needs no test edits"
key-files:
  created:
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_webhook.py
  modified: []
key-decisions:
  - "Sibling-episode decoy computed by bumping the SxxEyy number in the fixture basename (fallback suffix) rather than a literal E01->E02 replace, so it survives the live capture"
metrics:
  duration: ~15min
  completed: 2026-10-20
requirements-completed: [SON5-01, SON5-03]
---

# Phase 120 Plan 03: Sonarr 5 Test Connection and Webhook Tests Summary

Fixture-driven CI tests that run the real Test Connection handler on the Sonarr 5 system/status body and post the raw Sonarr 5 webhook bytes through the Bottle route (with HMAC), plus a real WebhookManager with decoys proving one-file matching.

## What was built

- `test_sonarr5_system_status.py` (5 tests): success with `fixtures.tested_version()` and the exact outbound call shape (URL suffix, X-Api-Key header, timeout 10, no redirects); fixture version matches manifest and matches `5.x.y.z`; docker-network URL resolving to 172.19.0.6 rejected as "private" with `requests.get` never called (documented as the D-02 known limitation deferred to Reliability); CGNAT example 100.64.0.1 passes `_validate_url`; extra status keys present and harmless.
- `test_sonarr5_webhook.py` (8 tests): Test body -> 200 "Test OK", no enqueue; Download body -> 200 "OK", `enqueue_import` called once with the fixture's sourcePath basename and Download provenance; signed raw body accepted; unsigned body 401; signature over re-serialized JSON 401 (byte-for-byte verification); real `WebhookManager.process` with sibling-episode, near-identical other-group, and unrelated decoys returns exactly `[(root, child)]`; same basename under two roots returns `[]`.

## Verification (observed)

- RED observed for both tasks (wrong version prefix: 1 failed / 4 passed; wrong expected basename: 2 failed / 6 passed), then reverted to GREEN.
- `pytest tests/unittests/test_sonarr5 tests/integration/test_web/test_handler/test_webhook.py tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_controller/test_webhook_manager.py -q -rs` -> 154 passed, 1 skipped (Plan 01 placeholder gate, expected).
- `ruff check src/python/` (whole tree) -> All checks passed.
- Acceptance greps: `tested_version()` 4, `5.0.0.2701` 0, `assert_not_called` 1, IP-literal lines 2; webhook file: `post_json` 0, `fixture_bytes(` 5, `Placeholder.Show` 0, `X-Webhook-Signature` 2, `expect_errors=True` 2, `WebhookManager(` 1, `.process(` 2.

## Commits

- 247f61b test(120-03): cover Sonarr 5 Test Connection with the system/status fixture
- 95454fa test(120-03): cover Sonarr 5 webhook bodies through web layer and real manager

## Deviations from Plan

- **[Rule 3 - Blocking] Helper import style.** Plan named `tested_version()` in the behavior/greps, but a bare import would be collected by pytest. Used `from tests.unittests.test_sonarr5 import fixtures` and `fixtures.tested_version()`, which satisfies both the grep and the collection constraint.
- **[Rule 1 - Robustness] CGNAT IP hoisted into `_CGNAT_EXAMPLE_IP`** so the IP-literal grep counts exactly 2 lines as specified.
- Tests are TDD-style but test-only against existing behavior, so each task has a single `test(...)` commit (RED was run and observed, not committed separately).

## Threat Flags

None. No production code changed; the SSRF guard is asserted intact (T-120-09) and only documentation-range IPs appear (T-120-10).

## Self-Check: PASSED
- FOUND: src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py
- FOUND: src/python/tests/unittests/test_sonarr5/test_sonarr5_webhook.py
- FOUND: 247f61b, 95454fa
