# Phase 79: Test Infra Cleanup - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Two independent test-infra cleanups ship together so CI output becomes
signal-only:

1. **TEST-01 (Python warnings):** `make run-tests-python` → `pytest` in the
   Docker harness produces zero pytest-cache write warnings and zero
   `webob`/`cgi` deprecation warnings on stderr.
2. **TEST-02 (Playwright CSP listener):** Every spec in the main E2E suite
   fails if a CSP violation fires in the browser, via a shared fixture that
   listens to both `page.on('console')` and the `securitypolicyviolation`
   DOM event and asserts zero violations in `afterEach`.

A permanent canary spec seeds an inline-script violation to prove the listener
fires and to guard against future regressions of the listener itself.

**Out of scope:**
- arm64 Docker build of `run-tests-python` (scheduled Phase 80, TECH-01)
- Bottle / webob major version jump for anything beyond cgi-removal
- CSP header / meta-tag policy changes (backend `web_app.py:152–162` and
  Angular `autoCsp` stay exactly as they are)
- Reducing or reshaping the existing 26 dashboard.page.spec tests from Phase 77
- New Playwright reporters, new CI workflow files, new make targets
- Fixing genuine CSP violations — this phase only detects them; if the canary
  reveals real violations in the existing app, those become a follow-up phase

</domain>

<decisions>
## Implementation Decisions

### TEST-01: pytest-cache warnings

- **D-01:** Suppress the 3 pytest-cache write warnings by adding
  `-p no:cacheprovider` to the Dockerfile CMD:
  `CMD ["pytest", "-v", "-p", "no:cacheprovider"]` in
  `src/docker/test/python/Dockerfile:45`. Surgical, localized to the test
  container, leaves local dev (`poetry run pytest`) untouched.
- **D-02:** Remove the now-dead `cache_dir = "/tmp/.pytest_cache"` line from
  `src/python/pyproject.toml:74`. With `-p no:cacheprovider` the cache plugin
  never loads, so the setting has no effect. Single source of truth =
  Dockerfile CMD.

### TEST-01: webob/cgi deprecation warning

- **D-03:** Primary fix: **upgrade webob** to a version that dropped the
  internal `cgi` import. `webob` is pulled transitively by the `webtest` dev
  dependency (currently pinned to 1.8.9 via poetry.lock). Researcher verifies
  which webob release removed the cgi shim and whether the upgrade is
  poetry-local (`poetry update webob`) or needs a `[tool.poetry.group.dev.dependencies]`
  constraint bump.
- **D-04:** Also remove the stale
  `filterwarnings = ["ignore:'cgi' is deprecated:DeprecationWarning"]` entry
  from `src/python/pyproject.toml` — it apparently doesn't match (warning
  fires at webob-import time, before pytest filters install). Clean up dead
  config once D-03 lands.
- **D-05:** **Fallback** (only if researcher confirms no webob release has
  dropped cgi and a clean upgrade is not available): set
  `ENV PYTHONWARNINGS="ignore::DeprecationWarning:webob"` (or equivalent
  pytest `-W` flag) in `src/docker/test/python/Dockerfile` so the filter
  applies at interpreter start before the cgi import fires. Document the
  fallback in `.planning/PROJECT.md` Key Decisions if taken; track the
  upstream unblock as a new todo.
- **D-06:** No supply-chain pin to a webob fork / pre-release tag — if D-03
  fails and D-05 is taken, we live with suppression until a clean release
  exists.

### TEST-02: Playwright CSP listener fixture

- **D-07:** Create a new custom test fixture at
  `src/e2e/tests/fixtures/csp-listener.ts` using Playwright's `test.extend()`
  pattern: the fixture wraps the `page` fixture, registers both listeners on
  first use, collects violations into a per-test array, and asserts
  `expect(violations).toEqual([])` in an auto-fixture teardown (afterEach).
- **D-08:** Every existing spec file opts in by swapping its top-line import
  from `import { test, expect } from '@playwright/test'` to
  `import { test, expect } from './fixtures/csp-listener'` (or the correct
  relative path). Scope: 6 spec files —
  `about.page.spec.ts`, `app.spec.ts`, `autoqueue.page.spec.ts`,
  `dashboard.page.spec.ts`, `settings-error.spec.ts`, `settings.page.spec.ts`.
  One-line change each.
- **D-09:** Listener hooks **both** sources:
  1. `page.on('console', msg)` — filter for CSP-specific text markers. Match
     candidates: `Refused to` + `Content Security Policy`,
     `because it violates the following Content Security Policy directive`.
     Planner's researcher picks the exact substring(s) that Chromium emits
     in the CI image. Errors from other sources (network, generic JS errors)
     are NOT collected — precision over recall on console noise.
  2. `page.addInitScript` that registers a `document.addEventListener(
     'securitypolicyviolation', e => …)` and relays the structured violation
     report (`blockedURI`, `violatedDirective`, `originalPolicy`) back to
     the test via `page.exposeFunction` (or a similar bridge). Captures
     violations the console log may drop or reshape.
- **D-10:** Failure surface is the `afterEach` assertion — test body stays
  clean, failure message shows the full violation list. No inline throw on
  first violation (harder to debug, races with page lifecycle).

### TEST-02: canary / regression guard

- **D-11:** **Keep a permanent canary spec** as an ongoing regression guard
  for the listener itself. If someone later disables the fixture, mis-scopes
  a filter, or swallows the `expect` error, the canary fails. Cost: ~20–30
  lines of test code in a dedicated spec file or a tagged describe block.
- **D-12:** Canary lives in a new file at
  `src/e2e/tests/csp-canary.spec.ts` (dedicated file — easy to find, easy
  to grep, isolated from real-feature specs). The spec imports the
  CSP-listener `test` fixture, uses `page.addInitScript` to inject an inline
  `<script>` via `document.write` (or `innerHTML` on a created element)
  **before** navigation, navigates to `/`, and asserts that the fixture's
  collected violations array contains **at least one** entry matching the
  seeded violation. This is the inverse assertion of the fixture's normal
  `toEqual([])` — planner implements this via a per-test opt-out of the
  auto-assert (e.g., the fixture exposes a `cspViolations` accessor and an
  `allowViolations()` flag the canary spec sets).
- **D-13:** Canary runs against the **real** backend CSP header + Angular
  autoCsp meta tag (no CSP mocking). This is the load-bearing property —
  if someone weakens CSP, the canary's seeded violation stops being blocked
  and the canary fails in the opposite direction, also surfacing the
  regression.

### Phase packaging

- **D-14:** **Two independent sub-plans**, executable in parallel:
  - **Plan 01 — TEST-01 Python warnings** (Dockerfile + pyproject.toml)
  - **Plan 02 — TEST-02 CSP listener** (new fixture file + 6 spec import
    swaps + canary spec file)
  They share no files and no sequencing. Atomic-revert per plan. Planner
  can schedule them in parallel waves.

### Claude's Discretion

- Exact webob version chosen in D-03 — researcher confirms the cgi-removal
  release (webob 1.8.x vs 2.x) and picks the lowest-churn jump.
- Exact console-text substring(s) used in D-09 filter 1 — researcher
  captures real Chromium output from the CI image and picks the most
  stable marker (likely `"Content Security Policy"` as a substring).
- Exact mechanism for bridging the `securitypolicyviolation` DOM event back
  to the test process in D-09 filter 2 — `page.exposeFunction` callback vs
  polling `window.__cspViolations` set by the init script. Planner picks.
- Whether D-12's canary uses `document.write` or
  `document.body.appendChild(scriptEl)` to inject the inline script —
  whichever Chromium reliably treats as a CSP violation in the CI image.
- File naming for the canary spec (`csp-canary.spec.ts` is recommended but
  `csp.spec.ts` is also acceptable if it reads better).
- Whether to add a tiny JSDoc/README snippet at the top of
  `fixtures/csp-listener.ts` explaining the two-source detection rationale
  (for future maintainers who might be tempted to simplify).

### Folded Todos

- **2026-02-08-clean-up-test-warnings** → TEST-01 (D-01 through D-06).
  Original problem: 4 warnings on every CI Python run (1 webob cgi + 3
  pytest-cache). Solution ported verbatim for pytest-cache
  (`-p no:cacheprovider`); webob solution upgraded from "update webob or
  bottle" to "upgrade webob primary, PYTHONWARNINGS fallback" with an
  explicit fallback plan.
- **2026-02-24-e2e-csp-violation-detection** → TEST-02 (D-07 through D-13).
  Original problem: CSP violations invisible across 4 test layers; the
  `css-element-queries` incident (inline `onload` handlers) proved this.
  Original todo presented two options (global fixture vs dedicated test);
  we chose global fixture (D-07) AND added a dedicated canary spec
  (D-11, D-12) — both options are load-bearing, not alternatives.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement + roadmap context
- `.planning/REQUIREMENTS.md` §TEST-01 — pytest-cache + webob/cgi warnings,
  verification = inspect CI log stderr.
- `.planning/REQUIREMENTS.md` §TEST-02 — shared fixture listens to both
  `page.on('console')` CSP messages and the `securitypolicyviolation` DOM
  event, fails in `afterEach`; seeded-violation verification required.
- `.planning/ROADMAP.md` §"Phase 79: Test Infra Cleanup" — goal, 4 success
  criteria (zero warnings; listener registered; seeded violation fails;
  existing specs stay green). Depends on Phase 77 (CSP listener attaches
  to the main E2E suite which includes the new UAT specs).

### Todos absorbed into this phase
- `.planning/todos/pending/2026-02-08-clean-up-test-warnings.md` — original
  problem statement for TEST-01 (the 4 warnings breakdown).
- `.planning/todos/pending/2026-02-24-e2e-csp-violation-detection.md` —
  original problem statement for TEST-02; includes the `css-element-queries`
  regression that motivated this work.

### TEST-01 surface (Python test harness)
- `src/docker/test/python/Dockerfile` (line 45, `CMD ["pytest", "-v"]`) —
  the line that gains `"-p", "no:cacheprovider"` per D-01. The harness is
  built via `make tests-python` and run via `make run-tests-python` /
  `src/docker/test/python/compose.yml`.
- `src/docker/test/python/compose.yml` — mounts `src/python` as `/src`
  read-only, which is what causes the pytest-cache write warnings in the
  first place. No change to the mount.
- `src/python/pyproject.toml` §`[tool.pytest.ini_options]` (lines 71–78) —
  delete `cache_dir` line (D-02) and the `filterwarnings` entry (D-04)
  after webob upgrade lands.
- `src/python/poetry.lock` — current `webob = 1.8.9`, pulled by `webtest`
  (`[project.optional-dependencies].dev`, line 26). Planner updates via
  `poetry update webob` once D-03's target version is confirmed.
- `Makefile` §`tests-python` (lines 76–89) + §`run-tests-python` (line 91) —
  the build + run flow that produces the stderr this phase polices. No
  change expected.
- `.github/workflows/ci.yml:144` — canonical harness evidence surface per
  the D-20 precedent from Phase 77. Verification of SC #1 ("CI Python
  test stderr contains zero pytest-cache warnings and zero webob/cgi
  deprecation warnings") reads CI log stderr here.

### TEST-02 surface (Playwright E2E)
- `src/e2e/playwright.config.ts` — `workers: 1`, `fullyParallel: false`,
  `timeout: 30000`, `expect.timeout: 10000 (CI)`. No changes per scope.
- `src/e2e/tests/fixtures/` — existing directory, home to `seed-state.ts`
  from Phase 77. New `csp-listener.ts` fixture lands here per D-07.
- `src/e2e/tests/about.page.spec.ts`, `app.spec.ts`, `autoqueue.page.spec.ts`,
  `dashboard.page.spec.ts`, `settings-error.spec.ts`,
  `settings.page.spec.ts` — the 6 specs whose top-line `test, expect`
  import swaps per D-08.
- `src/e2e/package.json` — `@playwright/test ^1.48.0`. No version bump.
- New file: `src/e2e/tests/csp-canary.spec.ts` per D-12.

### CSP policy sources (read-only — do not modify)
- `src/python/web/web_app.py:152–162` — backend `Content-Security-Policy`
  header (default-src 'self'; script-src 'self' 'unsafe-inline'; …).
- `src/angular/angular.json:46` — Angular `autoCsp: true` (hash-based
  inline script/style via `<meta>` tag). Layered with the HTTP header per
  the comment at `web_app.py:145–151`.

### Upstream phase context (tests this phase reads but does not alter)
- `.planning/phases/77-deferred-playwright-e2e-phases-72-73/77-CONTEXT.md`
  — D-09 (all 15 new UAT specs land in `dashboard.page.spec.ts`), D-20
  (CI-as-evidence surface is `ci.yml:144`), D-21 (no Playwright reporter
  or retry tuning). Phase 79's CSP fixture attaches to the suite that
  includes these 15 new specs.

### Project-level rules
- `.planning/PROJECT.md` Key Decisions — "Angular autoCsp for hash-based
  CSP", "Security headers via after_request hook". CSP policy stays exactly
  as-is in Phase 79.
- `/Users/julianamacbook/.claude/projects/-Users-julianamacbook-seedsyncarr/memory/feedback_design_spec_rigor.md`
  — "Port AIDesigner HTML identically." Does not apply to test infra code;
  test-only phase touches zero user-visible UI.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/e2e/tests/fixtures/seed-state.ts`** (from Phase 77) — established
  the `tests/fixtures/` directory convention and a pattern for fixture
  modules exporting typed helpers. `csp-listener.ts` lands alongside it
  using the same structure.
- **pyproject.toml `[tool.pytest.ini_options]`** — existing section with
  `pythonpath`, `timeout`, `cache_dir`, `filterwarnings`. D-02 and D-04
  subtract from it; no new entries.
- **`webtest` dev dependency** — already pulls webob; no new dependency
  added by TEST-01, only a version bump.

### Established Patterns
- **All 6 spec files use `import { test, expect } from '@playwright/test'`**
  — uniform top-line import, making the D-08 swap mechanical across the
  codebase. Grep surface: `grep -l "from '@playwright/test'" src/e2e/tests/*.spec.ts`
  returns exactly those 6 files.
- **Playwright `test.extend()` auto-fixtures** — standard Playwright idiom
  for per-test setup/teardown that runs without explicit `beforeEach` /
  `afterEach` in the consumer spec. `csp-listener.ts` exports a `test`
  that has already composed the fixture.
- **`workers: 1, fullyParallel: false`** from `playwright.config.ts` — each
  spec gets its own `page` and its own violation array. Fixture state is
  per-test; no cross-test leak.
- **Bearer token auth on `/server/*`** — E2E tests navigate to the UI
  which bootstraps the token. CSP fixture does not interact with auth or
  the backend; it only reads browser-emitted events.

### Integration Points
- **Dockerfile CMD ↔ pytest plugin system** — D-01 adds the
  `-p no:cacheprovider` flag at CMD level; this is the single injection
  point. Local dev path (`poetry run pytest`) is unaffected.
- **Fixture ↔ Playwright `page`** — D-07's `test.extend()` overrides the
  `page` fixture to register listeners on first use and tear them down
  after the test. Consumers see a normal `page`; the listener is invisible.
- **Init script ↔ test process** — D-09's DOM-event listener runs in the
  browser context; it must bridge back to the Node test process via
  `page.exposeFunction` or a polling mechanism. This is the primary
  implementation risk; researcher validates.
- **Canary spec ↔ fixture's violation array** — D-12 requires the fixture
  to expose its collected violations as a test-visible accessor and to
  skip the default `toEqual([])` assertion when the canary spec opts out.

### Known Constraints
- **CSP dual-layer** — HTTP header (permissive, `unsafe-inline`) +
  `<meta>` tag (strict, hash-based via autoCsp). Chromium enforces BOTH;
  a violation fires if EITHER policy blocks. Listener captures both
  equally — no need to distinguish.
- **Bearer token meta tag injection** — Angular bootstraps the token via
  a `<meta>` tag. The tag is injected pre-CSP evaluation and does not
  itself violate CSP. Listener does not interact with this.
- **Read-only `/src` mount** is the root cause of pytest-cache warnings
  — mount stays as-is (security property: tests can't mutate source).
- **CSP is currently clean** per ROADMAP SC #4 — enabling the listener
  must not make existing specs fail. If research finds real violations,
  raise before plan execution.

</code_context>

<specifics>
## Specific Ideas

- **"CI test output is signal-only"** is the user-facing phrase. Every
  decision in this phase laddered back to that goal: noise suppression
  (TEST-01) and noise prevention (TEST-02 listener + canary guard).
- **Upgrade > suppress** for the webob fix — D-03 prefers a real upgrade
  so TEST-01 becomes a prerequisite enabler for future Python 3.13 work,
  not just a cosmetic stderr fix.
- **Belt-and-braces on CSP detection** — D-09 runs both console and DOM
  event listeners in parallel, not as alternatives. The cost is trivial;
  the value is that if one surface changes (browser update, Chromium
  suppressing a log line), the other still fires.
- **Canary is inverse-assertion** — D-11/D-12 explicitly noted: the
  canary's seeded violation proves the fixture works AND proves CSP is
  still restrictive enough to block the injection. Two failure modes
  covered by one test.
- **Two plans, no sequencing** — D-14 unblocks parallel execution.
  Planner should not artificially serialize them.

</specifics>

<deferred>
## Deferred Ideas

- **Fixing real CSP violations discovered by the canary or listener** —
  Phase 79 detects; it does not fix. If the CSP clean-bill from ROADMAP
  SC #4 turns out to be wrong once the listener is live, the surfaced
  violations spawn a new phase.
- **page.on('pageerror') or other browser-level error capture** — could
  add general JS-error detection to the fixture later. Out of scope;
  Phase 79 is CSP-specific.
- **CSP violation reporting to a backend endpoint** (production
  observability via `report-uri` / `report-to`) — infrastructure-level
  concern, separate from test-infra. Not in v1.1.1.
- **Angular unit test / Karma CSP coverage** — the todo noted 4 layers
  lack CSP detection. Phase 79 fixes layer 3 (main E2E); layers 1
  (Karma), 2 (ng-serve E2E), 4 (Python backend test) stay open. Revisit
  if those layers start shipping visual/markup that could violate CSP
  (currently they don't).
- **arm64 `run-tests-python` Docker build fix** — scheduled Phase 80
  TECH-01 per roadmap. Not in 79's scope.
- **Supply-chain pin to webob git main** (D-06 rejected) — revisit only
  if a future phase needs cgi-removal and no release has landed.

### Reviewed Todos (not folded)

_None — both absorbed todos were folded into TEST-01/TEST-02 above._

</deferred>

---

*Phase: 79-test-infra-cleanup*
*Context gathered: 2026-04-21*
