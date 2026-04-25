---
created: 2026-04-24T00:00:00Z
title: Migrate /server/config/set from GET-path to POST-body
area: security
files:
  - src/python/web/handler/config.py
  - src/angular/src/app/services/settings/config.service.ts
  - src/e2e/tests/settings.page.ts
  - src/docker/test/e2e/configure/setup_seedsyncarr.sh
---

## Problem

`/server/config/set/{section}/{key}/{value}` passes credential values as URL path segments. This means sensitive values (passwords, API keys) appear in:
- Server access logs
- Browser history (if accessed via browser)
- Reverse proxy logs

The E2E setup script (`setup_seedsyncarr.sh`) uses this pattern to configure `remote_password`, making the test credential visible in container logs.

## Solution

Migrate the config set endpoint from GET with path parameters to POST with request body:

1. Backend: Change `/server/config/set` to accept POST with JSON body `{ "section": "...", "key": "...", "value": "..." }`
2. Frontend: Update `ConfigService` to use POST
3. E2E: Update `setup_seedsyncarr.sh` and page objects to use `--data-urlencode` / POST
4. Backward compat: Consider supporting both GET (deprecated) and POST for one release cycle

## Context

Surfaced as SEC-09 in 999.7 Docker Test Security deep review (score 75). Deferred from v1.2.0 because it's a backend API contract change, not a test hardening item. Also related to E2E-06 in 999.3 (HTTP GET for state-mutating operations).
