---
phase: 121
slug: credential-forwarding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-21
---

# Phase 121 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma 6.4.4 + Jasmine (Angular unit); Playwright 1.59.1 (E2E) |
| **Config file** | `src/angular/karma.conf.js`, `src/angular/angular.json`; `src/e2e/playwright.config.ts` |
| **Quick run command** | `cd src/angular && npx ng test --browsers ChromeHeadless --watch=false --include='**/auth.interceptor.spec.ts'` |
| **Full suite command** | `cd src/angular && npx ng test --browsers ChromeHeadless --watch=false --code-coverage && npm run lint` |
| **E2E wiring check** | `cd src/e2e && npx tsc --noEmit -p . && npx playwright test --list` |
| **E2E execution** | CI job `e2etests-docker-image` on the PR |
| **Estimated runtime** | ~15 seconds (quick); ~2–3 minutes (full Angular suite) |

---

## Sampling Rate

- **After every task commit:** Run the quick command plus `npm run lint`
- **After every plan wave:** Run the full suite command; for E2E changes also the E2E wiring check
- **Before `/bm:verify-work`:** Full Angular suite green with `check.global` thresholds, lint clean, PR CI E2E job green (including `chromium-token`)
- **Max feedback latency:** 15 seconds (quick command)

---

## Per-Task Verification Map

*Filled in by the planner/executor per task. Requirement → test mapping from RESEARCH.md:*

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| SEC-02 (SC1) | `/server/*` relative and absolute same-origin requests carry Bearer | unit | quick command | ✅ extend `auth.interceptor.spec.ts` | ⬜ pending |
| SEC-02 (SC2) | GitHub URL, other host, protocol-relative, backslash, look-alike, userinfo, non-`/server/`, unparseable → no header | unit | quick command | ✅ extend | ⬜ pending |
| SEC-02 (SC3) | GitHub-URL no-header test fails before fix, passes after | unit (TDD red commit) | quick command; failing output recorded | ✅ extend | ⬜ pending |
| SEC-02 (SC1/SC2, real browser) | Token-configured UI works; `api.github.com` request has no `authorization` | E2E | CI `e2etests-docker-image`; local wiring check | ❌ W0 `src/e2e/tests/auth-token.spec.ts` | ⬜ pending |
| SEC-02 (SC4) | No auth redesign | static | `git diff --stat main -- src/python src/angular/src/app/app.config.ts src/angular/src/app/services/utils/rest.service.ts src/angular/src/app/services/utils/version-check.service.ts` is empty | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/e2e/tests/auth-token.spec.ts` — token-configured E2E (D-12)
- [ ] `src/e2e/playwright.config.ts` — `chromium-token` project with `dependencies: ['chromium']`, and `testIgnore` for the token spec on `chromium`

No framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E token run executes against a real container | SEC-02 | E2E needs a pushed staging image; runs only in PR CI | Confirm the `e2etests-docker-image` job passes, including `[chromium-token]` tests |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
