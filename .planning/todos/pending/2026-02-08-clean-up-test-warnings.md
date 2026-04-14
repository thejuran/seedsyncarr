---
created: 2026-02-08T20:00:00Z
title: Clean up CI test runner warnings
area: testing
files:
  - src/docker/test-python/Dockerfile
  - src/python/pyproject.toml
---

## Problem

The Python test suite produces 4 warnings on every CI run:

1. **webob `cgi` deprecation** (1 warning): `webob` imports the deprecated `cgi` module which is removed in Python 3.13. Currently on 3.11 so not broken, but will block future Python upgrades.

2. **pytest cache warnings** (3 warnings): The Docker test container mounts `/src` as read-only, so pytest cannot write `.pytest_cache`. These are harmless but add noise to the CI output.

## Solution

1. **pytest cache**: Add `-p no:cacheprovider` to pytest invocation in the Docker test config to suppress cache warnings.

2. **webob/cgi**: Update `webob` (or its consumer `bottle`) to a version that no longer imports the deprecated `cgi` module. This should be done before any Python 3.13 upgrade.
