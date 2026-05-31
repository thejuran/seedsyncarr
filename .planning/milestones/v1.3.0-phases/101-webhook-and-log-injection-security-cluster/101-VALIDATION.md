---
phase: 101
slug: webhook-and-log-injection-security-cluster
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 101 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 101-RESEARCH.md §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd src/python && python -m pytest tests/unittests/ tests/integration/test_web/test_handler/test_webhook.py tests/integration/test_web/test_handler/test_config.py -x -q` |
| **Full suite command** | `cd src/python && python -m pytest --cov --cov-report=term-missing -x` |
| **Estimated runtime** | ~quick <30s / full ~minutes (container-inclusive per slice-1 baseline) |

Coverage floor: `fail_under = 88` (must hold or rise).

---

## Sampling Rate

- **After every task commit:** Run the quick command above.
- **After every plan wave:** Run the full suite command.
- **Before `/gsd:verify-work`:** Full suite must be green (amd64 + arm64).
- **Max feedback latency:** ~30 seconds (quick command).

---

## Per-Task Verification Map

| Requirement | Wave | Secure Behavior | Test Type | Automated Command | File Exists |
|-------------|------|-----------------|-----------|-------------------|-------------|
| BUG-02 | 0/1 | Default flag off → no behavior change (existing config loads, no secret → 200 + HMAC skipped) | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py -x` | ✅ existing |
| BUG-02 | 1 | Flag on + no secret → 503 **before body parse** | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py::TestWebhookFailClosed -x` | ❌ W0 |
| BUG-02 | 1 | Flag on + secret set → existing HMAC flow unchanged | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py::TestWebhookFailClosed -x` | ❌ W0 |
| BUG-02 | 1 | Old config file loads without `webhook_require_secret` key → default False | unit | `pytest tests/unittests/test_common/test_config.py -x` | ⚠️ partial — add case |
| SEC-01 | 0/1 | `sanitize_log_value` strips/escapes CR/LF/control chars | unit | `pytest tests/unittests/test_common/test_types.py -x` | ❌ W0 |
| SEC-01 | 2 (Plan 04) | Webhook/command tainted log sites (webhook_manager:37,76 + controller:790,792,760,975,1075) route through helper — site set RE-DERIVED post-adversarial-review, supersedes the original 5-site list; see 101-04-PLAN.md `D-03 re-derived` | unit | `pytest tests/unittests/test_controller/test_webhook_manager.py tests/unittests/test_controller/ -x` | ⚠️ partial |
| SEC-01 | 3 (Plan 05) | Auto-delete-timer + model-layer tainted log sites (controller:229,820,841,848,866,876,897,926,948 + model/model.py:81,97,112) route through helper — controller:229 NO LONGER deferred; lftp/job_status_parser.py:725 + lftp/lftp.py job-name logs remain out of scope this slice (recorded as explicit deferred-item note in 101-05-PLAN.md) | unit | `pytest tests/unittests/test_controller/ tests/unittests/test_model/ -x` | ❌ W3 |
| SEC-03 | 1 | Sonarr webhook returns 429 over 60/60s limit | integration | `pytest tests/integration/test_web/test_handler/test_webhook.py::TestWebhookRateLimit -x` | ❌ W0 |
| SEC-03 | 1 | Radarr and Sonarr rate limits are independent (per-route closures) | unit | `pytest tests/unittests/test_web/test_rate_limit.py::TestRateLimitIndependentClosures` | ✅ existing |
| SEC-02 | 1 | GET returns `""` for `webhook_secret` regardless of value or auth state | integration | `pytest tests/integration/test_web/test_handler/test_config.py::TestConfigHandler -x` | ❌ W0 |
| SEC-02 | 1 | GET returns `""` for `api_token` regardless of auth state | integration | `pytest tests/integration/test_web/test_handler/test_config.py -x` | ⚠️ partial — add case |

*Status legend: ✅ exists · ❌ W0 (create in Wave 0) · ⚠️ partial (extend existing).*

---

## Wave 0 Requirements

- [ ] `tests/unittests/test_common/test_types.py` — unit tests for `sanitize_log_value()`: empty string, plain string unchanged, `\n` escaped, `\r` escaped, `\r\n` both escaped, embedded control chars, combined payload.
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — add `TestWebhookFailClosed`: (1) require_secret=True + no secret → 503 before body parse; (2) require_secret=True + valid secret → passes HMAC; (3) require_secret=False + no secret → 200 (existing behavior preserved).
- [ ] `tests/integration/test_web/test_handler/test_webhook.py` — add `TestWebhookRateLimit`: (1) 60 requests pass; (2) 61st returns 429; (3) Sonarr and Radarr have independent counters.
- [ ] `tests/integration/test_web/test_handler/test_config.py` — add `test_get_secret_fields_always_blank`: set `webhook_secret`/`api_token` non-empty, GET → assert both serialize as `""` on authenticated AND unauthenticated paths.
- [ ] `tests/unittests/test_common/test_config.py` — add cases: from_dict without `webhook_require_secret` → default False; from_dict with `webhook_require_secret: "True"` → True.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Startup warning surfaces require-secret expectation | BUG-02 (D-07) | Log-output assertion on process startup; covered by unit assertion on the warning emitter if extracted, else manual | Start with `webhook_require_secret` semantics and no secret; confirm the extended startup warning fires. Prefer an automated assert on the warning helper. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All requirements have an automated verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick command)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
