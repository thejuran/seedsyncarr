# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1.2 — Test Suite Audit

**Shipped:** 2026-04-24
**Phases:** 4 | **Plans:** 6

### What Was Built
- Independent staleness audit of all three test layers (72 Python files, 40 Angular specs, 7 E2E specs)
- Zero stale tests found across all layers -- prior milestones' rebrand and redesign had already cleaned them
- HttpClientTestingModule migrated to provideHttpClient() in 6 Angular spec files
- E2E harness autoqueue config fixed, coverage baselines documented
- Full CI green: 1262 Python, 599 Angular, 37 E2E on amd64+arm64

### What Worked
- Layer-by-layer sequencing (Python -> Angular -> E2E -> Validation) gave clear coverage impact visibility before moving on
- Research phase per layer surfaced the audit methodology before planning, preventing wasted effort
- The "zero stale" finding validated that the v1.0.0 rebrand and v1.1.0 redesign milestones were thorough with test cleanup
- Code review (Phase 86) caught missing `set -euo pipefail` and `curl --fail` in the E2E harness script

### What Was Inefficient
- The milestone was scoped for removal work but found nothing to remove -- the audit confirmed health rather than performing cleanup
- Phase 86 missing VERIFICATION.md created a tech debt item that could have been avoided with a verify step
- REQUIREMENTS.md E2E checkboxes went stale despite the work being done -- traceability updates should happen at plan completion, not milestone close

### Patterns Established
- Coverage baselines should be documented in ROADMAP.md at milestone boundaries for historical tracking
- E2E harness configuration (setup_seedsyncarr.sh) needs `set -euo pipefail` and `curl -Sf` as standard practice

### Key Lessons
1. An audit milestone that confirms "everything is clean" is still valuable -- it provides documented confidence and coverage baselines
2. HttpClientTestingModule migration was a worthwhile opportunistic cleanup found during audit, even though it wasn't in the original scope
3. arm64 Unicode sort order variance (glibc locale differences) is a platform concern to monitor, not a test bug

---

## Milestone: v1.2.0 — Test & Quality Hardening

**Shipped:** 2026-04-28
**Phases:** 10 | **Plans:** 23

### What Was Built
- Fixed 19 Python test defects (2 critical false-coverage, 8 warning, 9 medium) across 4 phases
- Fixed 7 Angular test issues (subscription leaks, fakeAsync, double-cast, optional chaining)
- Fixed 9 E2E test + 5 infrastructure issues (Playwright APIs, CSP enforcement, arm64 locale, Docker health)
- Hardened CI (least-privilege permissions, SHA-pinned actions, release dependency chain, Docker build cache)
- Hardened Docker test containers (SSH key-only auth, non-root sshd, ephemeral keys, no hardcoded passwords)
- Filled 6 test coverage gaps (SSE streaming, Logs E2E, Settings E2E, webhook integration, DeleteRemoteProcess, ActiveScanner)
- Added rate limiting to all mutable HTTP endpoints via reusable sliding-window decorator
- Tightened Semgrep rules, eliminating 628 false positives

### What Worked
- The v1.1.2 audit milestone identified exactly the right findings — this milestone executed cleanly against those findings with no scope surprises
- Three-layer parallelism (Python / Angular / E2E+CI independently) allowed efficient phase sequencing
- WSGI iterator harness pattern (Phase 94) unblocked SSE streaming tests that had been skipped since the test suite was written
- TDD approach for rate limiter (Phase 96) — failing tests first, then implementation — caught edge cases early
- Code review after each phase caught real issues (mock time in flaky test, dead mock setup, unsafe afterEach)

### What Was Inefficient
- REQUIREMENTS.md checkbox drift — 12 checkboxes stayed unchecked despite the work being done; had to bulk-update at milestone close
- Summary file one-liner extraction failed for many phases — inconsistent frontmatter format caused garbled MILESTONES.md entry (had to rewrite manually)
- Verification files marked `human_needed` for runtime checks (Docker, Karma) that can't be automated — these accumulate as false-positive gaps in the audit
- The milestone audit was run mid-milestone (at Phase 92) and found 28 gaps — all of which were simply not-yet-executed phases, not real gaps

### Patterns Established
- Closure-based sliding-window rate limiter as the standard pattern for HTTP endpoint protection
- WSGI iterator harness (`wsgi_stream.py`) as the pattern for testing Bottle streaming responses without HTTP
- `helpers.py` module for shared test utilities (replacing conftest fixture scope issues)
- Ephemeral SSH key generation at Docker build time as the standard for test container auth

### Key Lessons
1. Quality-only milestones (no new features) ship faster than mixed milestones — 5 days for 68 items across 10 phases
2. Verification `human_needed` status should not block milestone close — if CI passes, the runtime checks are implicitly satisfied
3. REQUIREMENTS.md checkboxes should be updated at plan completion, not milestone close — prevents the stale-checkbox cleanup step
4. The v1.1.2 audit → v1.2.0 fix pipeline worked well as a two-milestone pattern: audit identifies, hardening fixes

---

## Milestone: v1.3.0 — Test Coverage Gaps

**Shipped:** 2026-05-29
**Phases:** 4 (97-100) | **Plans:** 10

### What Was Built
- Captured coverage baseline at milestone start: Python 85.19% host/provisional, Angular Stmts 83.34% / Branches 69.01% / Functions 79.73% / Lines 84.21% (v1.3.0-COVERAGE-BASELINE.md)
- Full-path Python coverage for 3 medium-priority gaps: MultiprocessingLogger shutdown (4 branches), SSRF IPv4/IPv6 reserved-range validation, LFTP JobStatusParser consecutive-error recovery
- Full end-to-end Angular coverage for confirm-modal `escapeHtml` (XSS path, including DOM injection probe)
- Targeted regression tests for 2 low-priority Python gaps: auto-delete dry-run/enabled toggle under live Timer, BoundedOrderedSet eviction-after-touch (COVLOW-01/02 closed by Phase 99 adversarial review)
- Targeted regression tests for 2 low-priority Angular gaps: SSE timeout reconnection race (heartbeat-saves vs no-heartbeat contrast, fakeAsync), auth.interceptor token-rotation via `_resetAuthInterceptorCache` seam (COVLOW-03/04)
- CI coverage ratchet: Angular Karma `check.global` gate (first-ever thresholds) + `--code-coverage` Dockerfile flag; Python `fail_under` raised 84 → 88
- **Coverage before (container-inclusive re-measure):** Python 89.27% / Angular Stmts 84.14% / Branches 69.46% / Functions 80.49% / Lines 84.99%
- **Floors set:** Python 88 (floor(89.27)−1, strictly > 84); Angular 83/68/79/83 (floor(measured)−1, first Karma thresholds)

### What Worked
- Wave sequencing (medium-priority first, low-priority second, ratchet last) gave accurate "after" numbers — the ratchet measured post-all-tests, not mid-milestone
- Container-inclusive Python re-measure (real-lftp suite inside Docker) revealed 89.27% vs provisional 85.19% — the honest "after" was significantly higher
- The `--code-coverage` + `check.global` dual-patch approach (both in one commit) correctly enforces that the gate is non-silent: text-summary output in CI logs proves coverage was collected, not just config-evaluated
- The COVERAGE_FILE=/tmp/.coverage env override was a clean solution for the read-only /src mount constraint
- Adversarial deep-review (Phase 99 close) caught COVLOW-01/02 regression test gaps before plan execution

### What Was Inefficient
- The container-inclusive Python re-measure command needs the `-e COVERAGE_FILE=/tmp/.coverage` redirect documented prominently — it's non-obvious and would silently fail without it (read-only mount)
- The Angular Dockerfile CMD had no `--code-coverage` since initial setup — a Karma `check.global` block would have been a permanent silent no-op without this plan's dual-patch
- No way to run Angular coverage locally (no `ng` in PATH on macOS) — all Angular measurement paths go through Docker, which adds ~5 minutes per iteration

### Patterns Established
- Container-inclusive Python coverage measurement (COVERAGE_FILE=/tmp/.coverage redirect + `docker compose run --rm -e ...`) as the authoritative ratchet source
- Dual-patch rule: `check.global` block + `--code-coverage` Dockerfile flag must land in the same commit (otherwise gate is a silent no-op)
- Monotonic ratchet: `fail_under = floor(container-inclusive measured) − 1`, computed floor strictly > prior floor; Angular = floor(measured) − 1 per metric, all > prior threshold (or > 0 for first-ever thresholds)
- `COVERAGE_FILE=/tmp/.coverage` env override required whenever running pytest-cov inside containers with read-only source mounts

### Key Lessons
1. The provisional host-only Python coverage (85.19%) understates the real number by ~4pp — the container-inclusive run (real-lftp suite included) reached 89.27%; always use container-inclusive for threshold-setting
2. A `check.global` block in `karma.conf.js` is completely inert without `--code-coverage` in the Dockerfile CMD — coverage instrumentation never runs, the block is never evaluated; both files must be patched together
3. Coverage ratchets should be set at `floor(measured) − 1` (not `floor(measured)`) to avoid immediate failures from measurement noise while still raising the bar from the prior floor
4. Wave dependencies matter for ratchet accuracy: measure AFTER all test additions land, not before or during

---

## Milestone: v1.7.4 — Safety Patch

**Shipped:** 2026-10-09
**Phases:** 3 (116-118) | **Plans:** 16

### What Was Built
- 116 Import Safety: ambiguous webhook import matches (a basename resolving to 2+ distinct model paths) rejected with no credit/badge/auto-delete; delete-time duplicate-basename guard as defense in depth.
- 117 Transfer-State Safety: LFTP parser peek-before-pop; status unavailable = `None` end to end; submitted-but-unobserved transfers protected (incl. 409 on manual extract/delete); success-only stability clocks.
- 118 Durable State: atomic `Persist.to_file`; 1.7.4 release gate run and the image deployed to the NAS by digest.

### What Worked
- Design spec → 3 risk-ordered phases with disjoint code paths; deletion safety landed first so it could ship alone if needed.
- RED-first regressions (fail-before/pass-after, 42 named tests) made the release gate mechanical and auditable.
- Digest-pinned smoke test with a real SSH→LFTP transfer before the production deploy; clean 79 s cutover.
- Phase verifiers re-ran evidence independently (incl. reproducing RED in a disposable worktree) instead of trusting SUMMARY narratives.

### What Was Inefficient
- Phase 117 grew to 8 plans: codex adversarial passes expanded XFER-02 scope (submitted-unobserved protection, same-cycle command guard, Stop reconcile) mid-phase.
- Phase 118's plan went through 4 rewrites; the owner waiver of the final codex re-review was never written down.
- PyPI publish broke at tag time (`./`-prefixed wheel paths) — packaging was never exercised before the tag.
- REQUIREMENTS.md / VALIDATION.md bookkeeping lagged behind completion again (117 unchecked, 118 VALIDATION left draft).

### Patterns Established
- "Unavailable" vs "empty" as distinct states for any external status source.
- Atomic same-directory temp + `os.replace` for every persisted file; relies on `/config` being a directory mount.
- Milestone audit integration check catches cross-phase seams the per-phase verifiers can't (116 auto-delete × 117 submitted-unobserved → backlog 999.3).

### Key Lessons
- When a safety fix adds a guard on one destructive path (manual delete), check every other destructive path (timer auto-delete) for the same guard in the same phase.
- Dry-run the PyPI build/upload (or `twine check`) before tagging a release.
- Record owner waivers in the phase CONTEXT/DISCUSSION log at the moment they're given.

### Cost Observations
- Model mix: Opus-driven orchestration, Sonnet subagents for planning/verification/integration check, codex for adversarial plan review.
- Sessions: multiple over 2 days (2026-10-08 → 2026-10-09).
- Notable: per-phase deep reviews all came back with 0 findings; the gates that caught real issues were codex adversarial (scope) and the milestone integration check (cross-phase seam).

### Orchestrator Gates (retro, 2026-10-09)
- Pauses: 14 owner pauses across 3 phases (3 auto-followed risk-tier prompts excluded; the DISCUSS card's pause is counted on both risk-tier and requirement-manifest).
- K0→K1 tokens (`docs/bench/meas02-after-0.11.0.md`, the latest bench; no 0.11.1 bench exists, and 45 of 52 v1.7.4 records ran on 0.11.1): output_tokens median 2752 (before 2331, +421), requests 5 (before 4), elapsed 25.7 s (before 22.8 s), read_scripts 0.
- Security-scan row 6: both phase-118 blocking findings (braces GHSA-vfj7, source-map-js GHSA-68fv; dev-only Angular test/build tooling, owner accepted risk) adjudicated real by owner → blocking FP rate 0.0% (0/2).

```
== QUALITY BESIDE SAVINGS (MEAS-02; tokens come from docs/bench/, not the gate log) ==
  note: the DISCUSS card's pause is recorded on both risk-tier and requirement-manifest (counted twice)
  _unscoped: phases=0 escaped=0/0 phases with a postmortem pauses=0 (auto-followed excluded=0) session_model=claude-opus-5-5[1m]:1 plugin_version=0.11.0:1
  v1.7.0: phases=0 escaped=0/0 phases with a postmortem pauses=n/a (auto-followed excluded=0) session_model=not recorded plugin_version=not recorded unattributed postmortems=2
  v1.7.4: phases=3 escaped=0/3 phases with a postmortem pauses=14 (auto-followed excluded=3) session_model=claude-opus-5-5[1m]:52 plugin_version=0.11.0:7,0.11.1:45
    116: escaped=0 catches=adversarial:1/1,build-verify:0/1,deep-review:0/1,preflight:0/1,security-scan:0/1 pauses=4 session_model=claude-opus-5-5[1m]:14 plugin_version=0.11.0:7,0.11.1:7
    117: escaped=0 catches=adversarial:4/4,build-verify:0/1,deep-review:0/1,preflight:0/1,security-scan:0/1 pauses=3 session_model=claude-opus-5-5[1m]:17 plugin_version=0.11.1:17
    118: escaped=0 catches=adversarial:4/4,build-verify:0/1,deep-review:0/1,preflight:0/1,security-scan:1/1 pauses=5 session_model=claude-opus-5-5[1m]:18 plugin_version=0.11.1:18
```

## Milestone: v1.7.5 — Safety Release

**Shipped:** 2026-10-15 (tags `v1.7.5`, `v1.7.6`; `1.7.6` deployed)
**Phases:** 2 (119, 119.1 inserted) | **Plans:** 18

### What Was Built
- 119 Safety Follow-ups: LFTP sentinel resync after a timeout (XFER-06); auto-delete timer defers on submitted-unobserved transfers using a shared root reservation (DEL-01); incomplete-import prevention: forced temp files, arr-queue completion gate, visible "Waiting" holds, one-shot confirmed manual release (IMP-01/02); persisted per-episode import credit (IMP-03); PyPI packaging repaired with a member-path CI check (REL-02); 1.7.5 published (REL-03).
- 119.1 Startup log secrets fix: no `settings.cfg` dump at startup; debug dump redacts every `secret_fields()` option; unreadable config is fatal and value-free; `%` round-trips (SEC-01). 1.7.6 released and deployed to NAS production by digest (REL-03 NAS portion, REL-04).

### What Worked
- The 1.7.5 smoke test found a pre-existing (since v1.0.0) secrets-in-startup-log leak before production. Holding the deploy and inserting 119.1 kept leaked credentials out of the production log.
- Count-only secret checks (field names and counts, never values), with a 1.7.5 positive control, proved the fix without the evidence itself leaking secrets.
- Incident-driven scope (Obsession, Days of Hope) with replay RED tests made the import fixes concrete and testable.
- The milestone integration check confirmed the frontend and backend hold-reason codes match exactly, a classic drift point.

### What Was Inefficient
- Phase 119 grew to 12 plans after the owner added two incident fixes mid-milestone. The 119-11 deploy plan was superseded.
- The UI pieces (Waiting badge, release confirm box) never got a browser check: no e2e seed creates a held file, and production had none at walkthrough time.
- SUMMARY `requirements_completed` frontmatter was mostly empty, and the GSD `milestone.complete` stats and accomplishments pulled from earlier milestones and had to be corrected by hand.

### Patterns Established
- "Hold, never release" when external completion evidence is unavailable; elapsed time never grants completion.
- Smoke-test the exact release digest on a NAS scratch setup before production, including a no-secrets log check.
- Secret-bearing evidence is count-only, and walkthrough artifacts that capture secrets get deleted.

### Key Lessons
- Any user-visible state the backend can produce (held, waiting) needs an e2e seed, or its UI never gets a visual check.
- Audit startup scripts for config dumps when adding new secret config fields; the leak was 1.x-old and only surfaced on a fresh smoke.
- Keep SUMMARY frontmatter `requirements_completed` filled so the audit's three-source cross-reference works without manual reconciliation.

### Cost Observations
- Model mix: Opus-driven orchestration; Sonnet subagents for planning, verification and the integration check; codex for adversarial plan review.
- Sessions: multiple over 2 days (2026-10-14 → 2026-10-15).
- Notable: the per-phase deep review of 119.1 returned 0 findings. The real catches were the release smoke (secrets leak) and the owner hold.

## Milestone: v1.7.7 — Sonarr 5 Compatibility

**Closed:** 2026-10-20 (verified; no release needed; no tag)
**Phases:** 1 (120) | **Plans:** 6

### What Was Built
- Live sandbox proof that 1.7.6 works with Sonarr 5.0.0.2701: Test Connection (SON5-01), queue-based completion hold and release for one tracked download (SON5-02), Test and Download webhooks (SON5-03).
- Sanitized live Sonarr 5 fixtures with a manifest (version, scenario, capture time), a hygiene test that rejects keys, hostnames and personal paths, and CI tests that run them through the real handlers, client and gate (SON5-04).
- Sanitizer, disposable webhook sink and an idempotent teardown script for sandbox captures. Tests only; no production code changed.

### What Worked
- Placeholder fixtures plus CI tests first (Waves 1–2), live capture second, swap last: the CI wiring was proven before the NAS run, and the swap was a one-commit change guarded by a "source must be live" check.
- Classifying failures before acting: the container-name Test Connection refusal was recognized as the existing private-address guard (Reliability item 5), not a Sonarr 5 regression, so no needless release.
- Sandbox-only scope kept production untouched, even with the seedbox refusing SSH mid-capture.

### What Was Inefficient
- The live capture (120-05) needed 8 deviations: Sonarr 5 masks the download-client password, the seedbox finishes downloads in seconds (needed a temporary speed cap), a ~10-minute seedbox SSH outage, and a trap that kept running after a signal.
- Planning assumed a natural "still downloading" window; real seedbox speed made it disappear.

### Patterns Established
- Conditional-release milestones: close as "verified; no release needed" without a version tag, because a `vX.Y.Z` tag triggers the release pipeline.
- Compatibility claims are scoped to the exact upstream build captured; a later build needs its own capture.
- Fixture manifests record source, version, scenario and capture time, and a hygiene test enforces sanitization in CI.

### Key Lessons
- To capture an "incomplete" state from a fast seedbox, plan a per-torrent speed cap up front.
- Signal traps in capture scripts must exit explicitly (`trap 'exit 130' INT TERM HUP` plus an EXIT trap for teardown).
- Live runs surface observability gaps (handler logger not attached; "cleared" wording on a prune) worth logging even when out of scope.

### Cost Observations
- Model mix: Opus orchestration and execution; planning, checking and verification subagents.
- Sessions: 1 day (2026-10-20).
- Notable: GSD `milestone.complete` again recorded 0 tasks and no accomplishments; MILESTONES.md entry corrected by hand.

## Milestone: v1.8.0 — Reliability

**Shipped:** 2026-10-28 (tag `v1.8.0`; GHCR/GitHub/PyPI; NAS production by digest)
**Phases:** 6 (121–126) | **Plans:** 52

### What Was Built
- The app token is sent only to SeedSyncarr's own API, so the GitHub update check no longer receives it (SEC-02).
- The Phase 119 import and auto-delete safeguards were proven live on the sandbox, both incident records were closed, and two misleading log messages were fixed (SAFE-01/02, LOG-01/02).
- A partial startup or a failing cleanup no longer leaves components running, and restart-time false errors are gone (LIFE-01/02).
- After a stream overflow, a slow browser tab recovers with one snapshot and bounded buffering (STRM-01/02).
- Test Connection works for LAN and Docker addresses while staying closed to metadata and ambiguous URLs (LAN-01/02).
- 1.8.0 was released with every Dependabot fix, smoke-tested by digest and deployed to production (REL-05/06).

### What Worked
- Live sandbox checks found real defects that unit tests missed: the dropped late webhook notice (122-05) and the scanner-death race (123-06, 3 of 5 restarts). Both were fixed in-phase with the owner's decision, not deferred.
- Reproducing before fixing (Phase 124) gave the fix a concrete, measurable target.
- One PR per phase, with the PR CI staging image used as the sandbox pin by digest. Production stayed byte-identical through every sandbox session.
- Code review after verification caught a real pre-existing bypass (125 CR-01) before release.

### What Was Inefficient
- Phases 122 and 123 each needed two gap-closure rounds (17 plans each against 3–6 originally planned), mostly because live timing on the NAS differed from what the unit tests assumed.
- Review findings committed after the owner's sign-off left VERIFICATION.md files at `gaps_found`, which the close audit flagged again even though the items were already parked.
- `milestone.complete` again produced an unusable MILESTONES.md entry (52 raw plan one-liners, phase count 7). It had to be rewritten by hand.

### Patterns Established
- Bounded, clock-based grace windows (monotonic, 10 s) instead of "one more cycle" for shutdown races.
- Live restart harnesses record every cycle's outcome (PASS/FAIL/INCOMPLETE), with a process sampler that proves reaping instead of inferring it from quiet logs.
- URL guards validate the exact string the HTTP stack will connect to.
- Before a version bump, review Dependabot and roll the fixes in, with a follow-up PR for alerts that appear after merge and before the tag.

### Key Lessons
- Shutdown and signal timing must be checked on the real container. Unit tests got the grace window wrong once already.
- When review findings land after verification, re-run or annotate verification at the same time so later audits don't flag them again.
- Budget for a gap-closure round on any phase that ends in a live sandbox check.

### Cost Observations
- Model mix: Opus orchestration and execution; balanced-profile planning, checking and verification subagents.
- Sessions: 8 days (2026-10-21 → 2026-10-28), 309 commits.
- Notable: the two live-check phases (122, 123) accounted for 34 of the 52 plans.

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.8.0 | 6 | 52 | Live sandbox acceptance with in-phase gap rounds; digest-pinned PR staging images; full Dependabot roll-in |
| v1.7.7 | 1 | 6 | Compatibility check on a sandbox; live fixtures in CI; closed with no release |
| v1.7.5 | 2 | 18 | Incident-driven safety release; deploy held on smoke finding, inserted 119.1 for a secrets fix |
| v1.7.4 | 3 | 16 | Safety patch from a design spec; RED-first release gate; digest-pinned NAS deploy |
| v1.2.0 | 10 | 23 | Quality-only hardening; audit→fix pipeline; 5-day execution |
| v1.1.2 | 4 | 6 | Audit-only milestone; research-first per layer |
| v1.1.1 | 8 | 26 | Cleanup sweep; deferred E2E + UAT from v1.1.0 |
| v1.1.0 | 12 | 30 | Full UI redesign with AIDesigner artifacts |

### Cumulative Quality

| Milestone | Python Tests | Angular Tests | E2E Specs | Python Coverage |
|-----------|-------------|---------------|-----------|-----------------|
| v1.8.0 | 1,945 (host run at release) | 657 | 45+ | fail_under 88 (CI) |
| v1.7.5 | 1,895 (CI dockerized) | 643 | 45+ | fail_under 88 (CI) |
| v1.7.4 | 1,481 host part-1 (+ container-only suites) | — | 45+ | fail_under 88 (CI); host 86.36% informational |
| v1.3.0 | 1,278 | 614 | 45+ | 89.27% container-inclusive (fail_under 88) |
| v1.2.0 | 1,200+ | 599 | 45+ | 84% (fail_under enforced) |
| v1.1.2 | 1,262 | 599 | 37 | 85.05% |
| v1.1.1 | 1,262 | 599 | 37 | 85.05% |
| v1.1.0 | 1,134 | 552 | 22 | 84% |

### Top Lessons (Verified Across Milestones)

1. Test cleanup happens naturally during feature work — dedicated audit milestones confirm rather than fix
2. E2E harness configuration is a recurring source of subtle CI failures (autoqueue, arm64 rar, CSP)
3. Quality-only milestones execute faster than mixed milestones — clear scope, no feature drift
4. REQUIREMENTS.md checkboxes should be updated at plan completion, not deferred to milestone close (repeated in v1.7.4)
5. A guard added to one destructive path must be checked on every destructive path (v1.7.4 → backlog 999.3)
6. Live checks on the real container find timing and race defects that unit tests miss; plan a gap round for them (v1.7.7, v1.8.0)
