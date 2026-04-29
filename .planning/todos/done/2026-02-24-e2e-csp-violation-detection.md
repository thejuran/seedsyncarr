---
created: 2026-02-24T00:00:00Z
title: Add CSP violation detection to e2e tests
area: testing
files:
  - src/e2e/playwright.config.ts
  - src/e2e/tests/
  - src/python/web/web_app.py
---

## Problem

CSP violations in the frontend go undetected by all three test layers:

1. **Angular unit tests** (Karma) — no CSP headers, served by Karma dev server
2. **Angular e2e tests** (Playwright) — no CSP headers, served by `ng serve` at localhost:4200
3. **Main e2e tests** (Playwright) — CSP headers present (served by backend at :8800), but Playwright silently ignores console CSP errors
4. **Python CSP test** (`test_web_app.py`) — only verifies header exists, not frontend compatibility

This allowed `css-element-queries` (ResizeSensor) to ship with inline `onload` handlers that violated `script-src 'self'`, undetected until manual browser testing.

## Solution

Add a Playwright console listener in the main e2e tests that fails on CSP violation messages. Since these tests run against the real Docker container (port 8800) which sets CSP headers, any violation will be caught.

Options:
- **Global fixture**: Add a `page.on('console')` listener in a shared fixture that collects CSP errors and fails the test in `afterEach`
- **Dedicated test**: Add a standalone spec that loads the app and asserts zero CSP violations in the console

The listener should match console messages containing "Content Security Policy" or the `securitypolicyviolation` DOM event.
