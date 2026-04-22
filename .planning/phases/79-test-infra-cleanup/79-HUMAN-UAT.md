---
status: partial
phase: 79-test-infra-cleanup
source: [79-VERIFICATION.md]
started: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Test

[awaiting CI run on post-merge commit]

## Tests

### 1. SC #1a + #1b — zero pytest-cache and zero cgi DeprecationWarning lines in `make run-tests-python` stderr
expected: Both grep counts return 0 after `make tests-python && make run-tests-python` completes on CI amd64
why_human: Cannot run locally due to documented arm64 base-image apt-get failure (openssh-server/rar/unrar). Requires CI amd64 run post-merge. Static code evidence (Dockerfile CMD + PYTHONWARNINGS) is verified; only the runtime outcome is deferred.
result: [pending]

### 2. SC #1c — CI log at `.github/workflows/ci.yml:144` confirms zero matching stderr lines
expected: First post-merge CI run shows no lines matching `pytest-cache|could not create cache` or `cgi.*deprecated`
why_human: CI log lives in GitHub Actions UI. Not accessible programmatically from local environment.
result: [pending]

### 3. SC #3a/#3b/#4 — `make run-tests-e2e` full-suite run, all 7 suites green (canary passes, no existing specs fail)
expected: Exit 0, 7 suites green including `csp-canary.spec.ts`; canary `poll >= 1` and `sawScriptSrc === true` assertions both fire
why_human: Requires pre-staged Docker image from registry + STAGING_VERSION/SEEDSYNCARR_ARCH env vars + full Docker Compose stack. Not runnable from local environment without live infra. Deferred to CI run per 79-02-SUMMARY.md documented exemption.
result: [pending]

### 4. Task 79-02-01 manual headed CSP pre-flight — zero existing CSP violations before fixture landed
expected: Chromium DevTools console shows zero occurrences of `"violates the following Content Security Policy directive"` across the 6 spec nav paths
why_human: Requires headed Playwright run + human DevTools console inspection. Deferred to CI self-validation — canary passing in CI simultaneously validates A1 (current CSP is clean) per RESEARCH §9 R-2.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
