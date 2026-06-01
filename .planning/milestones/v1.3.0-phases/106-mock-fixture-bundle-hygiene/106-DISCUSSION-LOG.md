# Phase 106: Mock-Fixture Bundle Hygiene - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 106-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-01
**Phase:** 106-mock-fixture-bundle-hygiene
**Mode:** discuss
**Areas discussed:** Tree-shake mechanism, screenshot-model-files fate, Relocation target, Bundle-delta proof

## Area Selection

Presented 4 phase-specific gray areas; user selected **all four** to discuss.

## Tree-shake mechanism

- **Options presented:** (a) Env-flag dead-code branch only — simpler, but static top-level `import {MOCK_MODEL_FILES}` relies on Terser heuristics to drop a large `Immutable.Map`, not guaranteed. (b) Env-flag + a second `fileReplacements` entry swapping the fixture module for an empty prod stub — physically removes the data, verifiable, matches DEPS-02's "exclude via fileReplacements" wording.
- **User selected:** (b) Env-flag + fixture fileReplacements. → D-01, D-02, D-03.

## screenshot-model-files fate

- **Context:** `screenshot-model-files.ts` (`SCREENSHOT_MODEL_FILES`, ~135 lines) confirmed to have zero importers across `src/**`.
- **Options presented:** (a) Delete outright (dead code; git history preserves it). (b) Relocate as a dev fixture for possible future use.
- **User selected:** (a) Delete outright. → D-04.

## Relocation target

- **Context:** existing `src/app/tests/` tree has `mocks/` (service doubles) and `unittests/`.
- **Options presented:** (a) `src/app/tests/fixtures/` (new dir, per CONCERNS.md — fixtures distinct from service mocks). (b) `src/app/tests/mocks/` (co-locate, fewer dirs but conflates data with service doubles).
- **User selected:** (a) `src/app/tests/fixtures/`. → D-05.

## Bundle-delta proof

- **Options presented:** (a) Bundle delta + dev-mode smoke test + prod-dist absence grep (assert a unique mock string has zero hits in prod output). (b) Bundle delta + dev smoke only (skip the dist grep).
- **User selected:** (a) all three checks. → D-06, D-07.

## Deferred Ideas

- Backend dependency hardening — later milestone (REQUIREMENTS Out of Scope).
- INFRA-01 / mp-logger spawn tests — slice 4.

## Claude's Discretion (recorded in CONTEXT)

- Prod stub filename/casing; bundle-stats capture mechanism; manual vs automated dev smoke test; commit granularity (single atomic commit acceptable for the one DEPS-02 requirement).
