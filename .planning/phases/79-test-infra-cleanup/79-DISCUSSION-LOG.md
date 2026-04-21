# Phase 79: Test Infra Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 79-test-infra-cleanup
**Areas discussed:** pytest-cache fix approach, webob/cgi warning fix, CSP listener fixture shape, CSP detection + canary

---

## pytest-cache fix approach

### Q1: How should we silence the 3 pytest-cache write warnings?

| Option | Description | Selected |
|--------|-------------|----------|
| -p no:cacheprovider in Dockerfile CMD | Disable cache plugin entirely at the Docker invocation layer. Matches original todo recommendation. Surgical, localized to test container, local dev unaffected. | ✓ |
| Keep cache_dir in pyproject.toml, debug why it fails | Config is already there but apparently ignored. Investigate pytest 9 + read-only /src mount interaction; fix root cause. | |
| Mount a writable tmpfs for .pytest_cache | Add tmpfs to Docker compose so pytest's default location becomes writable. Keeps pytest cache benefits at the cost of compose complexity. | |

**User's choice:** -p no:cacheprovider in Dockerfile CMD
**Notes:** Matches the original 2026-02-08 todo's recommendation. Chose the surgical fix over root-cause investigation because the pytest-cache provides no real value in an ephemeral test container.

### Q2: Should we also clean up the existing cache_dir config in pyproject.toml?

| Option | Description | Selected |
|--------|-------------|----------|
| Remove the now-dead cache_dir line | With -p no:cacheprovider the plugin never loads; cache_dir has no effect. Remove to avoid future confusion. Single source of truth = Dockerfile CMD. | ✓ |
| Keep cache_dir for local dev | Local dev runs poetry run pytest without Docker and could still benefit from cache. Two configurations to keep consistent. | |

**User's choice:** Remove the now-dead cache_dir line
**Notes:** Dead config is worse than no config — risk of future contributors "fixing" the cache_dir value without realizing the Docker CMD disables the plugin entirely.

---

## webob/cgi warning fix

### Q1: How should we eliminate the webob cgi deprecation warning?

| Option | Description | Selected |
|--------|-------------|----------|
| Upgrade webob | webob pulled by webtest (dev dep). Bump to version that dropped cgi import. Fixes root cause, unblocks Python 3.13, no filter-pattern brittleness. | ✓ |
| Fix filterwarnings so it actually matches | Existing entry doesn't land — import fires before pytest filters install. Switch to PYTHONWARNINGS env or -W flag. | |
| Both: upgrade + keep filterwarnings as belt-and-braces | Upgrade webob AND keep a filterwarnings entry. More defensive; adds config surface. | |

**User's choice:** Upgrade webob
**Notes:** Prefer real fix over suppression. TEST-01 becomes an enabler for future Python 3.13 upgrade work, not just cosmetic stderr cleanup.

### Q2: If no webob version has dropped cgi, what's the fallback?

| Option | Description | Selected |
|--------|-------------|----------|
| Fix filterwarnings via PYTHONWARNINGS env in Dockerfile | Set ENV PYTHONWARNINGS="ignore::DeprecationWarning:webob" so filter applies before cgi import fires. Pragmatic suppression until clean upgrade possible. | ✓ |
| Pin webob via poetry override to a pre-release/fork | Pin to git main if removal exists there. Introduces supply chain risk and a pin to maintain. | |
| Stop here with a documented caveat | Defer the fix; note in REQUIREMENTS.md that TEST-01 webob portion is blocked on upstream. | |

**User's choice:** Fix filterwarnings via PYTHONWARNINGS env in Dockerfile
**Notes:** Rejected supply-chain pin (D-06 in CONTEXT.md). Rejected half-closing the requirement. Fallback is PYTHONWARNINGS at the Dockerfile ENV level, which lands before interpreter startup and catches the import-time warning the pyproject.toml filterwarnings entry misses.

---

## CSP listener fixture shape

### Q1: How should the CSP violation listener attach to specs?

| Option | Description | Selected |
|--------|-------------|----------|
| Custom test.extend() fixture, all specs opt in via import swap | Create fixtures/csp-listener.ts; 6 existing specs swap their top-line import. Zero per-test boilerplate after. Matches modern Playwright idiom. | ✓ |
| Shared helper, call explicitly in beforeEach per spec | Export attachCspListener(page) + assertNoCspViolations(); each spec wires them in beforeEach/afterEach. More explicit, no import swap, but 6 spec files need 4-line additions each. | |
| Global setup in playwright.config.ts | Register listener via use.contextOptions or a global setup file. Auto-applies everywhere with no per-spec change, but per-test boundary is harder. | |

**User's choice:** Custom test.extend() fixture, all specs opt in via import swap
**Notes:** Import swap across 6 files is mechanical and grep-able. Auto-fixture teardown gives clean per-test violation array. Global setup rejected because per-test boundary is load-bearing for clean failure messages.

### Q2: When should the listener fail the spec?

| Option | Description | Selected |
|--------|-------------|----------|
| afterEach assertion | Collect violations in array during test, expect(violations).toEqual([]) in auto-fixture afterEach. Test body stays clean; failure message shows captured violation(s). | ✓ |
| Inline throw the moment a violation fires | Listener throws as soon as violation is seen. Faster failure but harder to debug and can race with page lifecycle. | |
| Both — log during, assert after | console.warn immediately + afterEach fails. Friendlier debugging via CI log, same failure surface. | |

**User's choice:** afterEach assertion
**Notes:** Standard Playwright pattern. Keeps stack traces sane (assertion location, not listener location). Rejected "both" because the extra warn adds noise without catching anything the afterEach wouldn't.

---

## CSP detection + canary

### Q1: Which CSP violation sources should the listener hook?

| Option | Description | Selected |
|--------|-------------|----------|
| Both page.on('console') AND securitypolicyviolation DOM event | Matches success criterion #2 verbatim. Console catches browser's CSP error log line; DOM event catches violations the browser may filter or reshape. Belt-and-braces, redundant but cheap. | ✓ |
| page.on('console') only | Simpler; one listener. Risk: if Chromium changes log format, listener silently misses. | |
| securitypolicyviolation DOM event only | Official DOM API, structured report body. Risk: some violations fire before document's event listener is registered. | |

**User's choice:** Both page.on('console') AND securitypolicyviolation DOM event
**Notes:** Success criterion #2 explicitly names both. Redundancy is cheap; the two surfaces cover complementary timing windows (console catches early-bootstrap; DOM event catches structured reports). Researcher picks exact console text match via real CI image output.

### Q2: What happens to the seeded-violation verification test after the listener is proven working?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as permanent canary/regression guard | Spec stays in suite forever. Catches future regressions where someone disables the listener. Low cost (~20 lines). | ✓ |
| One-shot verify-then-remove | Run once to prove listener works, delete. Suite stays leaner. SC #3 explicitly allows this. Risk: if listener later breaks, nothing catches it. | |
| Keep but skip by default, enable via env flag | test.skip(!process.env.TEST_CSP_CANARY, ...). Runnable manually for debugging, zero cost in normal CI. | |

**User's choice:** Keep as permanent canary/regression guard
**Notes:** The listener is the load-bearing mechanism for "no CSP violations ever ship". Permanent canary is cheap insurance that someone disabling or mis-scoping the fixture gets caught. The canary also validates the CSP header stays restrictive enough to block the seeded injection — two failure modes covered by one test.

### Q3: How should the canary inject its violation without polluting the real app?

| Option | Description | Selected |
|--------|-------------|----------|
| page.addInitScript with an inline <script> via document.write | Inject a script that writes inline <script>alert(1)</script> before navigation. Real CSP blocks it, listener fires. Scoped to canary only — zero app code changes. | ✓ |
| Dedicated backend test route that serves an inline-violating response | Add /test/csp-canary route returning HTML with inline script. Cleaner separation but requires backend plumbing and care to avoid production leak. | |
| Use page.evaluate to attempt eval() or inline onclick | Run eval('1+1') or append element with inline handler. Simpler but tests unsafe-eval / event-handler directives which differ from primary concern (inline <script>). | |

**User's choice:** page.addInitScript with an inline <script> via document.write
**Notes:** Scoped purely to the canary spec — no backend changes, no production CSP surface touched. Tests the primary concern (inline <script> blocked by script-src 'self' with autoCsp hashes). Planner confirms document.write vs appendChild based on which Chromium reliably treats as a CSP violation in the CI image.

---

## Claude's Discretion

- Exact webob target version (researcher confirms cgi-removal release).
- Exact console-text substring used in CSP console filter (researcher captures real Chromium output from CI image).
- Bridge mechanism from DOM event listener back to Node test process (page.exposeFunction vs polling window global).
- document.write vs appendChild(scriptEl) for canary injection.
- Canary spec file name (csp-canary.spec.ts recommended; csp.spec.ts acceptable).
- Whether to add a JSDoc/README at top of csp-listener.ts.

## Deferred Ideas

- Fixing real CSP violations if canary/listener surfaces any (new phase).
- page.on('pageerror') / general JS-error capture in the fixture.
- CSP violation backend reporting (report-uri / report-to).
- Angular unit / Karma / ng-serve E2E / Python backend test CSP coverage.
- arm64 run-tests-python Docker build fix (Phase 80, TECH-01).
- webob git-main pin (rejected; revisit only if cgi removal blocks Python 3.13 work).
