---
phase: 100
slug: low-priority-angular-coverage-ci-ratchet
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 100 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `100-RESEARCH.md` §"Validation Architecture" and the three planned plans (100-01 SSE race, 100-02 auth rotation, 100-03 CI ratchet).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Angular)** | Jasmine + Karma (Angular CLI managed, Angular `^21.x`) |
| **Framework (Python)** | pytest + pytest-cov |
| **Config file (Angular)** | `src/angular/karma.conf.js` (NET-NEW `coverageReporter.check.global` added by 100-03) |
| **Config file (Python)** | `src/python/pyproject.toml` (`[tool.coverage.report] fail_under`, line 88) |
| **Quick run command (Angular spec subset)** | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=src/app/tests/unittests/services/base/stream-service.registry.spec.ts` (100-01) / `--include=.../services/utils/auth.interceptor.spec.ts` (100-02) |
| **Full suite (Angular)** | `make run-tests-angular` |
| **Coverage gate (Angular, after 100-03 patches Dockerfile + karma.conf.js)** | `make run-tests-angular` (now with `--code-coverage` → `check.global` enforced) |
| **Coverage gate (Python)** | Authoritative ratchet source = CONTAINER-INCLUSIVE: `make tests-python && docker compose -f src/docker/test/python/compose.yml run --rm -e COVERAGE_FILE=/tmp/.coverage tests pytest --cov --cov-report=term-missing -p no:cacheprovider` (real-lftp suite INCLUDED; `-e COVERAGE_FILE=/tmp/.coverage` redirects the data file off the read-only `/src` mount; enforces `fail_under`). Host `make coverage-python` is a PROVISIONAL cross-check only (excludes the real-lftp suite), NOT the ratchet source. |
| **Lint command** | `cd src/angular && npx eslint "<spec path>" --max-warnings 0` |
| **Estimated runtime** | ~5–10s per Angular spec (headless); full Angular suite + Python coverage within standard CI budget |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the spec being edited (~5–10s) + lint.
- **After every plan wave:** `make run-tests-angular` (100-01/100-02); plus `make coverage-python` once 100-03 lands.
- **Before `/gsd:verify-work`:** Full Angular suite + Python coverage both green, with the ratcheted thresholds in place (100-03).
- **Max feedback latency:** ~10 seconds (single-spec quick run); full suite within CI budget.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 100-01-* | 01 | 1 | COVLOW-03 | — | Heartbeat firing in the same fakeAsync frame as `checkConnectionTimeout` re-arms `_lastEventTime` (line 130 re-read) → `EventSourceFactory.createEventSource` call count stays 1 (no spurious reconnect), no `notifyDisconnected` on the contested tick (no double subscription). Test must re-arm the interval via `startTimeoutChecker()` (outer `beforeEach` discards it). | unit (fakeAsync) | quick run (stream-service spec) | ✅ (extend existing spec) | ⬜ pending |
| 100-01-* (contrast) | 01 | 1 | COVLOW-03 | — | Positive control: no heartbeat → `tick` past `CONNECTION_TIMEOUT_MS` → `checkConnectionTimeout` fires → `reconnectDueToTimeout` → after `STREAM_RETRY_INTERVAL_MS`, `createEventSource` called a 2nd time. Proves the guard, not mere inertia. | unit (fakeAsync) | quick run (stream-service spec) | ✅ (extend existing spec) | ⬜ pending |
| 100-02-* | 02 | 1 | COVLOW-04 | — | Token rotation: `setupWithMeta("v1")` → request carries `Bearer v1`; mutate meta to `"v2"` → `_resetAuthInterceptorCache()` → next request carries `Bearer v2`. Mirror of the existing cache (negative) test. Code comment names the real page-reload coupling (user reload/navigation re-instantiates the module — NOT version-check.service, which does not reload). | unit | quick run (auth interceptor spec) | ✅ (extend existing spec) | ⬜ pending |
| 100-03-* | 03 | 2 | RATCHET-02 | — | Re-measure post-99 coverage; ADD `coverageReporter.check.global` to karma.conf.js AND `--code-coverage` to `src/docker/test/angular/Dockerfile` CMD (gate is a silent no-op without both); bump `[tool.coverage.report] fail_under` (84 → new floor); set each threshold at floor(measured) − ~0.5–1% margin; one commit; before/after in ROADMAP + RETROSPECTIVE; floor decision in PROJECT.md. | CI gate | `make run-tests-angular` + `make coverage-python` | ❌ W0 (karma.conf.js check.global + Dockerfile `--code-coverage` are net-new) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*No `<threat_model>` threats: this phase adds regression tests over already-correct code and ratchets CI thresholds. No production behavior change, no new attack surface (D-09 trivial-fix posture — no fix anticipated).*

---

## Wave 0 Requirements

- [ ] `src/angular/karma.conf.js` — ADD `coverageReporter.check.global` (statements/branches/functions/lines) + an `lcovonly`/`text-summary` reporter so the check runs headlessly (RATCHET-02). Net-new; no coverage check exists today.
- [ ] `src/docker/test/angular/Dockerfile` — ADD `--code-coverage` to the `ng test` CMD. Without it, the `check.global` block is never evaluated — a silent no-op (RESEARCH finding #2). Both files patched in the SAME commit as the threshold bump.
- [ ] Re-measure Python + Angular coverage against current HEAD (after 100-01/100-02 land) using the SAME exclusions as the v1.3.0 baseline anchor — required as Plan 100-03's FIRST task, before writing threshold values.

*The existing spec files `stream-service.registry.spec.ts` and `auth.interceptor.spec.ts` already exist and are extended in place — no new spec files. Karma + Jasmine + ChromeHeadlessCI and pytest + pytest-cov are already installed and CI-gated.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* The SSE race and auth rotation are fully observable via fakeAsync/`HttpTestingController` assertions; the ratchet is observable via a CI run failing below threshold. Success criterion #4 ("CI green on ratcheted thresholds across amd64+arm64") is verified by the CI pipeline itself — no manual visual inspection.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (100-01/100-02 automated; 100-03 has Wave 0 config patches + automated CI gate)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (karma.conf.js check.global + Dockerfile `--code-coverage` + re-measurement)
- [ ] No watch-mode flags (`--watch=false` / `ChromeHeadlessCI`)
- [ ] Feedback latency < 10s (single-spec quick run)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
