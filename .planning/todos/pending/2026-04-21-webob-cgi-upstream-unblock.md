---
created: 2026-04-21T21:40:00Z
title: Remove PYTHONWARNINGS cgi filter once webob drops stdlib cgi import
area: testing
files:
  - src/docker/test/python/Dockerfile
  - src/python/poetry.lock
upstream: https://github.com/Pylons/webob/pull/466
triggers_on: webob release without stdlib cgi import
---

## Problem

`src/docker/test/python/Dockerfile` carries an `ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"` line purely to suppress the stdlib `cgi` DeprecationWarning triggered by webob 1.8.9's `from cgi import parse_header` in `src/webob/compat.py`. As of 2026-04-21, webob 1.8.9 is the latest release on PyPI and PR #466 (cgi-removal for webob 2.0) is unmerged. Python pin is `>=3.11,<3.13` so `legacy-cgi` conditional dependency (3.13+ only) does not activate.

When webob ships a release without the stdlib `cgi` import:

1. Bump `webob` in `src/python/pyproject.toml`, regenerate `poetry.lock`.
2. Remove the `ENV PYTHONWARNINGS` line from `src/docker/test/python/Dockerfile`.
3. Re-run `make run-tests-python` and confirm stderr stays clean.

## Related

- Phase 79 Plan 01 installed the filter as the D-05 fallback (D-03 upgrade path unavailable). See `.planning/phases/79-test-infra-cleanup/79-01-SUMMARY.md` and `79-RESEARCH.md` §2.
- This todo supersedes the webob/cgi half of the original `2026-02-08-clean-up-test-warnings.md`.
