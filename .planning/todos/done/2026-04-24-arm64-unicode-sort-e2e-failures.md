---
created: 2026-04-24T23:00:00.000Z
title: Fix arm64 Unicode sort order failures in E2E dashboard specs
area: testing
files:
  - src/e2e/tests/dashboard.page.spec.ts
---

## Problem

Two Playwright E2E specs in `dashboard.page.spec.ts` fail on arm64 (ubuntu-24.04-arm) due to locale-dependent Unicode sort order differences between amd64 and arm64 glibc implementations.

The sort order of torrent names containing Unicode characters differs between:
- amd64 (`ubuntu-latest`): passes — sort matches expected order
- arm64 (`ubuntu-24.04-arm`): fails — glibc sorts Unicode code points differently

## Context

- Documented in Phase 85 E2E audit (85-HUMAN-UAT.md): "33 passed, 2 pre-existing arm64 sort failures"
- Pre-existing — NOT introduced by the v1.1.2 test suite audit
- Per D-06/D-07: these failures are accepted as pre-existing and locale-dependent
- VAL-01 (CI green) is satisfied with a caveat documenting these 2 failures

## Possible Approaches

1. Normalize sort comparison in the spec to be locale-independent
2. Use `toSorted()` with explicit `localeCompare` in the test assertion
3. Skip the sort-order assertion on arm64 using a platform detection helper
4. Accept as known limitation and mark specs with `test.fixme()` on arm64
