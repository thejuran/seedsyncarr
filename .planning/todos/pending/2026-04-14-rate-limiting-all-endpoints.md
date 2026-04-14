---
created: 2026-04-14T00:00:00Z
title: Add rate limiting to all HTTP endpoints
area: security
files:
  - src/python/web/web_app.py
  - src/python/web/handler/config.py
  - src/python/web/handler/status.py
  - src/python/web/handler/server.py
---

## Problem

Only the bulk command endpoint (`/server/command/bulk`) has rate limiting (10 req/60s sliding window). All other endpoints — config get/set, status, test-connection — have no rate limiting. Behind auth this is low-risk, but defense-in-depth says we should limit abuse potential, especially on test-connection endpoints which make outbound HTTP calls.

## Solution

Add a reusable rate-limiting decorator (similar to the existing sliding-window implementation in `controller.py:239-251`) and apply it to:

- `/server/config/set` — prevent rapid config overwrites
- `/server/config/test/*` — prevent abuse as a port scanner (even with SSRF validation)
- `/server/status` — prevent polling abuse

Keep the limits generous (e.g. 30 req/60s) since legitimate use is low-frequency.
