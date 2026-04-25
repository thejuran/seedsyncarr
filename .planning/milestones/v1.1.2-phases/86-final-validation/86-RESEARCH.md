# Phase 86: Final Validation - Research

**Researched:** 2026-04-24
**Domain:** CI validation, coverage documentation, GitHub Actions pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Verify CI green by pushing to GitHub and confirming the real GitHub Actions pipeline passes. No local pre-check required. The authoritative proof for VAL-01 is the CI run itself.
- **D-02:** The push can be a documentation-only commit (coverage notes in ROADMAP.md) or the phase's own planning artifacts — no source code changes are expected.
- **D-03:** Document Python coverage before/after in the v1.1.2 milestone section of ROADMAP.md when the milestone is completed. No standalone coverage report file.
- **D-04:** Include Angular coverage baselines (from Phase 84: 83.34%/69.01%/79.73%/84.21%) alongside Python (85.05%) for completeness in the milestone notes.
- **D-05:** Python coverage must not drop below 84% (`fail_under` in pyproject.toml). Phase 83 recorded 85.05% — the "after" number comes from the CI run in this phase.
- **D-06:** The 2 pre-existing arm64 Unicode sort failures in E2E (documented in Phase 85) are NOT regressions from the test audit. They are deferred to a future phase/todo.
- **D-07:** VAL-01 is satisfied with a caveat documenting these 2 failures as pre-existing and locale-dependent (arm64 glibc sort order differs from amd64). The audit did not introduce them.
- **D-08:** Create a todo for the arm64 sort issue so it's tracked for future resolution.

### Claude's Discretion

No specific requirements — open to standard approaches.

### Deferred Ideas (OUT OF SCOPE)

- **Arm64 Unicode sort failures** — 2 E2E specs fail on arm64 due to locale-dependent Unicode sort order (glibc differences between amd64 and arm64). Pre-existing, not introduced by the audit. Track as a todo for future resolution.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAL-01 | Full CI green after all removals (Python + Angular + E2E + lint) | CI pipeline structure documented; arm64 caveat protocol documented; push trigger mechanism confirmed |
| VAL-02 | Python coverage % documented before and after (must not drop below 84%) | Before = 85.05% (Phase 83); after = CI run result; fail_under = 84 enforced in pyproject.toml; ROADMAP.md is the documentation target |
</phase_requirements>

---

## Summary

Phase 86 is a pure validation and documentation phase — no source code changes are expected. The three prior audit phases (83: Python, 84: Angular, 85: E2E) all completed with zero test removals, leaving the test suite structurally identical to the pre-audit state. The CI pipeline has never been broken by the audit; this phase exists to produce the authoritative proof-of-green CI run and record the coverage baseline in the milestone notes.

The primary execution path is straightforward: push a documentation commit (ROADMAP.md milestone notes + this phase's planning artifacts), wait for the GitHub Actions pipeline to complete green on main, and record the resulting Python coverage percentage alongside the pre-audit baseline. The push to `main` triggers both the amd64 and arm64 E2E jobs (arm64 only runs on main push, not PRs), which makes it the correct trigger for full VAL-01 verification.

The one technical complexity is the autoqueue E2E concern inherited from Phase 85 (Pitfall 1): `setup_seedsyncarr.sh` sets `autoqueue/patterns_only/true` but does NOT set `autoqueue/enabled/true`. This means the `autoqueueEnabled` value will be `null` (falsy) in the Angular component, causing the `.pattern-section` block to be hidden and `btn-pattern-add` to be disabled. If the three `autoqueue.page.spec.ts` tests that call `addPattern()` fail at CI runtime, the fix is a one-line addition to `setup_seedsyncarr.sh` — this is a harness configuration bug, not a test staleness issue, and it is explicitly within Phase 86 scope per the Phase 85 VERIFICATION.md deferred item.

**Primary recommendation:** Push a documentation commit with ROADMAP.md milestone notes, confirm CI green on main (both amd64 + arm64 E2E), then record the "after" Python coverage from the CI run logs.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CI pipeline trigger | GitHub Actions (external) | Git push (local) | Push to main triggers the full pipeline including arm64 E2E |
| Python test execution + coverage | CI runner (Docker) | Local make target | `make run-tests-python` runs inside Docker; coverage computed by pytest-cov |
| Angular test execution | CI runner (Docker) | Local make target | `make run-tests-angular` runs inside ChromeHeadlessCI Docker |
| E2E test execution | CI runner (Docker + GHCR image) | No local path | Requires pre-built staging image + Docker compose stack; no local-only path |
| Coverage documentation | Planning docs (ROADMAP.md) | — | D-03 mandates milestone section, no standalone file |
| Arm64 E2E | GitHub-hosted arm64 runner | — | `ubuntu-24.04-arm` runner, only triggered on main push or version tags |

---

## Standard Stack

### Core (what CI uses)
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest + pytest-cov | 9.0.3 / 7.0.0 | Python test runner + coverage | `fail_under = 84` enforced in pyproject.toml |
| Karma + Jasmine | Angular 21 runner | Angular unit tests | ChromeHeadlessCI, 599 tests |
| Playwright (E2E) | via Docker | E2E browser tests | 37 specs, 7 files |
| ruff | latest (CI: `pip install ruff`) | Python lint | `ruff check src/python/` |
| ESLint | via npm | Angular lint | `cd src/angular && npm run lint` |
| Docker Buildx + QEMU | v3 | Multi-arch image build | amd64 + arm64 |
| GitHub Actions | N/A | CI orchestration | `.github/workflows/ci.yml` |

### CI Job Dependency Chain
```
unittests-python ──┐
unittests-angular ─┤
lint-python ───────┼──► build-docker-image ──► e2etests-docker-image (amd64 + arm64)
lint-angular ──────┘                                │
                                                    ├──► publish-docker-image-dev  (main only)
                                                    ├──► publish-docs               (main only)
                                                    └──► (publish jobs on tags only)
```

**Key trigger rules:**
- PRs: amd64 E2E only
- Push to `main`: both amd64 AND arm64 E2E
- Release tags: both amd64 + arm64, then publish jobs

This means a push to `main` is required for VAL-01 to be satisfied — a PR would not run arm64.

---

## Architecture Patterns

### System Architecture Diagram

```
[git push to main]
        │
        ▼
[GitHub Actions: ci.yml]
        │
        ├─► unittests-python ──► Docker: pytest --cov ──► coverage %
        │        (fail_under=84 enforced)
        │
        ├─► unittests-angular ──► Docker: ng test ChromeHeadlessCI ──► 599 pass/fail
        │
        ├─► lint-python ──► ruff check src/python/
        │
        ├─► lint-angular ──► npm run lint
        │
        └─► [all 4 pass] ──► build-docker-image (multi-arch amd64+arm64, push to GHCR)
                                      │
                                      ▼
                        e2etests-docker-image (matrix)
                          ├─► amd64 (ubuntu-latest)
                          │     └─► make run-tests-e2e SEEDSYNCARR_ARCH=amd64
                          │           └─► 37 Playwright specs
                          └─► arm64 (ubuntu-24.04-arm)
                                └─► make run-tests-e2e SEEDSYNCARR_ARCH=arm64
                                      └─► 35 pass, 2 pre-existing sort failures (caveat)
```

### Documentation Target: ROADMAP.md Milestone Section

The v1.1.2 milestone section in `ROADMAP.md` (currently inline, not in a `<details>` block) is where coverage numbers go per D-03. The planner should add a `**Coverage Baseline**` subsection to the Phase 86 entry after CI passes.

### Recommended Commit Structure

Since D-02 specifies the push can be documentation-only:

1. **Wave 1 commit:** Add ROADMAP.md placeholder/notes entry for v1.1.2 milestone completion + this phase's planning artifacts (RESEARCH.md, PLAN.md). Push to main.
2. **CI runs:** Wait for all CI jobs green. Extract Python coverage % from `unittests-python` job logs.
3. **Wave 2 commit:** Update ROADMAP.md with the actual "after" coverage number and milestone completion date.

This requires two pushes to main, which is fine — the second push confirms CI is still green after the documentation update.

**Alternative:** Write a placeholder "TBD" in Wave 1, then update in Wave 2 once CI results are known. The verifier step confirms the final number is present and CI is green.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage enforcement | Custom threshold check | `fail_under = 84` in pyproject.toml | Already configured; pytest-cov enforces with exit code 2 if not met |
| CI green verification | Script polling GitHub API | Push to main, check Actions UI | D-01 mandates the CI run itself is the proof; no scripted verification needed |
| Coverage number extraction | Custom parser | Read it from CI logs manually | One number, once — not worth automation |
| Arm64 sort fix (if needed) | Architecture-specific sort workaround | `autoqueue/enabled/true` in setup_seedsyncarr.sh | The Pitfall 1 fix is a 1-line curl addition |

**Key insight:** This phase is pure orchestration + documentation. The heavy lifting is done by CI. The planner should not add code complexity.

---

## Common Pitfalls

### Pitfall 1: autoqueue.page.spec.ts May Fail at CI Runtime
**What goes wrong:** The three `autoqueue.page.spec.ts` tests that call `addPattern()` rely on `.pattern-section` being visible and `.btn-pattern-add` being clickable. Because `setup_seedsyncarr.sh` does not set `autoqueue/enabled/true`, `autoqueueEnabled` is `null` (falsy) in the Angular component. The `@if (autoqueueEnabled && patternsOnly)` guard hides the entire pattern section, and `navigateTo()` waits for `.pattern-section` with `state: 'visible'` — this will time out.
**Why it happens:** `setup_seedsyncarr.sh` only sets `patterns_only=true`, not `enabled=true`. Phase 83 did not touch the harness. Phase 84 did not touch it. Phase 85 documented it as pre-existing. Phase 86 inherits it.
**How to avoid:** Add `curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo` to `setup_seedsyncarr.sh` before the restart command, as the first task in the plan — before pushing to CI. Then confirm all 3 autoqueue tests pass.
**Warning signs:** CI E2E job shows `TimeoutError: locator('.pattern-section') waiting for visible` in `autoqueue.page.spec.ts`.
**Scope confirmation:** Phase 85 VERIFICATION.md explicitly notes: "If these tests time out, the fix is a harness configuration bug in Phase 86 (add `curl .../autoqueue/enabled/true` to setup_seedsyncarr.sh), not a Phase 85 staleness issue."

### Pitfall 2: arm64 E2E Does Not Run on PRs
**What goes wrong:** If the phase uses a PR-based workflow, the arm64 E2E job is skipped (matrix condition: only runs on `push` to `main` or version tags). VAL-01 requires arm64 to pass.
**Why it happens:** The CI matrix uses a conditional expression to select runners based on event type and ref.
**How to avoid:** Push directly to main (D-01). Do not use a PR for the authoritative CI run.
**Warning signs:** CI run shows only one `e2etests-docker-image` job (amd64 only) instead of two.

### Pitfall 3: Python Coverage Number Not Captured from CI
**What goes wrong:** The "after" coverage number is left undocumented, or the wrong run's number is used.
**Why it happens:** The CI `unittests-python` job logs contain the coverage output but it scrolls away or is missed.
**How to avoid:** After CI completes green, open the `unittests-python` job log and find the `Total coverage: XX.XX%` line from pytest-cov output. This is the VAL-02 "after" number. Document it alongside the Phase 83 "before" baseline of 85.05%.
**Warning signs:** ROADMAP.md says "TBD" after the phase is marked complete.

### Pitfall 4: arm64 Sort Failures Treated as CI Blockers
**What goes wrong:** The 2 pre-existing arm64 Unicode sort failures cause the arm64 E2E job to fail, blocking the push-to-GHCR `:dev` publish step and appearing to block VAL-01.
**Why it happens:** The arm64 E2E matrix uses `fail-fast: false`, so the amd64 job can succeed even if arm64 fails. But VAL-01 wording says "CI pipeline completes green across all jobs."
**How to avoid:** Per D-07, VAL-01 is satisfied with a caveat. The 2 sort failures are pre-existing and locale-dependent. Document them explicitly in the milestone notes as pre-existing, then mark VAL-01 as satisfied with caveat. Create the D-08 todo item.
**Warning signs:** Treating the arm64 failures as blocking without checking if they match the pre-existing sort failures documented in Phase 85 UAT.

---

## Code Examples

### Fix for Pitfall 1: setup_seedsyncarr.sh Addition

```bash
# Source: src/docker/test/e2e/configure/setup_seedsyncarr.sh (current state)
# Current line 12:
curl -sS "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo

# Add immediately after:
curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo
```

The full corrected block (lines 12-13, before restart):
```bash
curl -sS "http://myapp:8800/server/config/set/autoqueue/patterns_only/true"; echo
curl -sS "http://myapp:8800/server/config/set/autoqueue/enabled/true"; echo

curl -sS -X POST "http://myapp:8800/server/command/restart"; echo
```

[VERIFIED: read src/docker/test/e2e/configure/setup_seedsyncarr.sh — line 12 confirmed, no enabled=true line present]

### ROADMAP.md Milestone Notes Pattern

```markdown
### v1.1.2 Test Suite Audit (Phases 83-86) — SHIPPED YYYY-MM-DD

**Coverage Baseline (Python):**
| Metric | Before Audit (Phase 83) | After Audit (Phase 86) |
|--------|------------------------|------------------------|
| Total coverage | 85.05% | XX.XX% |
| fail_under threshold | 84% | 84% |
| Safety margin | 1.05pp | X.XXpp |

**Coverage Baseline (Angular) — Phase 84:**
| Metric | Value |
|--------|-------|
| Statements | 83.34% (1682/2018) |
| Branches | 69.01% (461/668) |
| Functions | 79.73% (421/528) |
| Lines | 84.21% (1622/1926) |

**Known Caveats:**
- 2 arm64 E2E specs fail due to pre-existing locale-dependent Unicode sort order (glibc amd64 vs arm64 difference). Not introduced by the audit. Tracked for future resolution.
```

[VERIFIED: confirmed against D-03, D-04, D-07 decisions in CONTEXT.md]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HttpClientTestingModule | provideHttpClient() + provideHttpClientTesting() | Angular 21 (Phase 84) | Migration done; no CI noise |
| N/A | fail_under = 84 in pyproject.toml | Phase 15 (v1.5) | Enforced every CI run |

**No deprecated approaches in use** for this phase — the stack is clean post-Phase 84 migration.

---

## Runtime State Inventory

Phase 86 is not a rename/refactor phase. This section is not applicable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| GitHub Actions | VAL-01 CI run | ✓ | Managed service | None — CI is the authoritative check |
| Docker (local) | Not required | N/A | N/A | — |
| `make` targets | Local verification (optional) | ✓ | macOS built-in | N/A |
| GitHub CLI (`gh`) | Monitoring CI run status | ✓ | Assumed via shell env | Open GitHub Actions UI directly |

**Missing dependencies with no fallback:** None — D-01 mandates push to GitHub as the verification method; no local toolchain dependency is required for the phase to succeed.

**Note:** Local Python test runs fail on macOS for SSH/LFTP/multiprocessing tests (environment-dependent failures documented in Phase 83). This does not affect CI — Docker containers provide the correct Linux environment.

---

## Validation Architecture

### Test Framework (inherited from prior phases)

| Property | Value |
|----------|-------|
| Python framework | pytest 9.0.3 + pytest-cov 7.0.0 |
| Python config | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Python quick run | `cd src/python && poetry run pytest tests/ --cov -q --tb=short` |
| Python full suite | `make run-tests-python` (Docker) |
| Angular framework | Karma + Jasmine, ChromeHeadlessCI |
| Angular config | `src/angular/karma.conf.js` |
| Angular full suite | `make run-tests-angular` (Docker) |
| E2E framework | Playwright |
| E2E full suite | `make run-tests-e2e STAGING_REGISTRY=... STAGING_VERSION=... SEEDSYNCARR_ARCH=amd64|arm64` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| VAL-01 | Full CI pipeline passes all jobs | Integration (CI) | Push to main → GitHub Actions | Arm64 E2E has 2 known sort failures (pre-existing caveat) |
| VAL-02 | Python coverage documented before+after, ≥ 84% | Documentation + CI enforcement | `fail_under = 84` enforced by pytest-cov exit code | "After" number read from CI logs |

### Sampling Rate

- **Per task commit:** Push to main, check CI run
- **Per wave merge:** Not applicable (single-wave phase)
- **Phase gate:** CI green (with arm64 caveat documented) before `/gsd-verify-work`

### Wave 0 Gaps

None — no new test files needed. This phase verifies existing infrastructure.

---

## Security Domain

This phase makes no changes to security-relevant code. The only modifications are to:
1. `src/docker/test/e2e/configure/setup_seedsyncarr.sh` (harness configuration, not production)
2. `ROADMAP.md` (documentation)

No ASVS categories apply to documentation-only and test-harness-configuration changes.

---

## Open Questions

1. **Will autoqueue.page.spec.ts pass at CI runtime without the fix?**
   - What we know: `setup_seedsyncarr.sh` does not set `autoqueue/enabled/true`; `autoqueueEnabled` will be null; `navigateTo()` waits for `.pattern-section` to be visible; the `@if` guard hides the section when `autoqueueEnabled` is falsy.
   - What's unclear: Whether any CI run since the autoqueue pattern UI was added has ever exercised these 3 tests successfully — the Phase 85 VERIFICATION.md notes it as a "pre-existing harness configuration concern" but does not have a recorded CI failure either.
   - Recommendation: Proactively add the `autoqueue/enabled/true` line to `setup_seedsyncarr.sh` as Wave 1 Task 1, before pushing to CI. This avoids a wasted CI run.

2. **Will the arm64 E2E job fail on exactly 2 tests (sort failures) or more?**
   - What we know: Phase 85 UAT documented "33 passed, 2 pre-existing arm64 sort failures." The 2 failures are in `dashboard.page.spec.ts` (Unicode sort order for torrent names).
   - What's unclear: Whether the autoqueue fix (if needed) affects arm64 vs amd64 differently.
   - Recommendation: If arm64 shows more than 2 failures, investigate before closing the phase. If exactly 2, document as pre-existing per D-07.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python coverage will remain above 84% in CI (no drift since Phase 83) | Standard Stack | Low risk — no test or production code changed since 85.05% was recorded |
| A2 | The arm64 sort failures are exactly in `dashboard.page.spec.ts` (sort-order assertions on torrent names) | Common Pitfalls | Low risk — documented in Phase 85 UAT "33 passed, 2 pre-existing arm64 sort failures" |
| A3 | GitHub Actions arm64 runner (`ubuntu-24.04-arm`) is available and not deprecated | Environment Availability | Low risk — used successfully in Phase 85 UAT |

---

## Sources

### Primary (HIGH confidence)
- `.github/workflows/ci.yml` — Read directly; CI job structure, matrix conditions, runner specs verified
- `src/python/pyproject.toml` — Read directly; `fail_under = 84`, pytest config, coverage config verified
- `Makefile` — Read directly; `run-tests-python`, `run-tests-angular`, `run-tests-e2e` targets verified
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — Read directly; `autoqueue/enabled/true` absence confirmed
- `.planning/phases/83-python-test-audit/83-01-SUMMARY.md` — Read directly; 85.05% coverage baseline confirmed
- `.planning/phases/84-angular-test-audit/84-02-SUMMARY.md` — Read directly; 83.34%/69.01%/79.73%/84.21% Angular baselines confirmed
- `.planning/phases/85-e2e-test-audit/85-01-SUMMARY.md` — Read directly; 37 specs, 7 files, autoqueue Pitfall 1 documented
- `.planning/phases/85-e2e-test-audit/85-VERIFICATION.md` — Read directly; arm64 sort failures, autoqueue deferral to Phase 86
- `src/e2e/tests/autoqueue.page.ts` — Read directly; `navigateTo()` waits for `.pattern-section`, `addPattern()` clicks `.btn-pattern-add`
- `src/e2e/tests/autoqueue.page.spec.ts` — Read directly; 3 tests confirmed in `test.describe` block

### Secondary (MEDIUM confidence)
- Phase 85 UAT result "33 passed, 2 pre-existing arm64 sort failures" — from 85-HUMAN-UAT.md (referenced in STATE.md commit log; not directly read but cited in VERIFICATION.md)

---

## Metadata

**Confidence breakdown:**
- CI pipeline structure: HIGH — read ci.yml directly
- Coverage thresholds: HIGH — read pyproject.toml directly, `fail_under = 84` confirmed
- autoqueue Pitfall 1: HIGH — read setup_seedsyncarr.sh, autoqueue.page.ts, autoqueue.page.spec.ts directly; absence of `enabled=true` confirmed
- Prior phase baselines: HIGH — read all three SUMMARY files directly
- Arm64 sort failures: MEDIUM — cited from Phase 85 UAT, not directly verified in this session

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable CI infrastructure; valid until ci.yml or pytest config changes)
