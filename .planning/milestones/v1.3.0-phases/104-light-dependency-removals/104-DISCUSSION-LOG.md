# Phase 104: Light Dependency Removals - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 104-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-31
**Phase:** 104-light-dependency-removals
**Mode:** discuss (standard)
**Areas analyzed:** Removal verification rigor, Bundle-size proof, Commit granularity, package-lock + audit handling

## Codebase Scouting (pre-discussion)

Performed before presenting gray areas, since the phase hinges on whether the two deps are actually used:

| Dep | Source usage | index.html | main.ts/polyfills | package-lock | Verdict |
|-----|--------------|-----------|-------------------|--------------|---------|
| jquery ^4.0.0 | 0 hits (ts/html/scss/json) | no script tags | not imported | depended-on-by `(root)` only | phantom — clean removal |
| css-element-queries ^1.1.1 | 0 hits (no ResizeSensor/ElementQueries) | n/a | not imported | root only | phantom — clean removal |

`angular.json` `scripts` array loads only `bootstrap.bundle.min.js` (bundles Popper; no jQuery). `@popperjs/core` is a direct, jQuery-independent dep. The `$(` hits in `.ts` are RxJS observable naming (`stats$`, `toasts$`), not jQuery.

## Gray Areas Presented

The user was offered four implementation decisions (multiSelect) and answered: **"use your recommendations for all."** All four locked to the recommended default.

### Removal verification rigor
- **Options:** (a) static grep evidence is enough; (b) also require clean prod build + Bootstrap dropdown/modal/collapse smoke-test before dropping.
- **Decision:** (b) — build + Bootstrap smoke-test (recommended default).

### Bundle-size proof
- **Options:** capture before/after prod bundle-size delta, or not.
- **Decision:** yes — record before/after bundle stats (recommended default).

### Commit granularity
- **Options:** one combined commit, or two atomic commits (one per requirement).
- **Decision:** two atomic commits, DEPS-01a + DEPS-01c (recommended default).

### package-lock + audit handling
- **Options:** regenerate lock + note audit delta (no scope expansion), or package.json+lock only.
- **Decision:** regenerate lock, note npm audit delta, do NOT expand scope to unrelated advisories (recommended default).

## Corrections Made

No corrections — user accepted all recommended defaults in a single response.

## Deferred Ideas

- Font Awesome 4.7 → Phosphor (DEPS-01b) → Phase 105
- Mock-fixture bundle hygiene (DEPS-02) → Phase 106
- Backend dep hardening (paste/bottle, pexpect, patoolib) → later milestone (REQUIREMENTS Out of Scope)

## Reviewed Todos (not folded)

- `webob-cgi-upstream-unblock` — backend/upstream-blocked, unrelated to frontend deps.
- `migrate-config-set-to-post-body` — backend API change, separate milestone (PROJECT.md Out of Scope).
