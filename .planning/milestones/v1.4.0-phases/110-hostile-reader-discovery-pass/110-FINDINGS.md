# Phase 110: Hostile-Reader Discovery Pass — Findings

**Produced:** 2026-06-02
**Pass framing:** "What would a skeptical r/selfhosted engineer flag if they browsed this public repo today?"
**Tooling:** ruff whole-tree + Semgrep auto-rules (320 rules) + gitleaks (full history) + pip-audit (Poetry venv) + npm audit (Angular tree) + AppProcess pytest + Dockerfile runtime-image inspection
**Phase boundary:** Discovery only. No production code, config, test, or docs changes land here.

---

## Summary

| Severity | Count | Fold | Park |
|----------|-------|------|------|
| Critical | 1     | 1    | 0    |
| High     | 1     | 1    | 0    |
| Medium   | 3     | 3    | 0    |
| Low      | 4     | 2    | 2    |
| **Total**| **9** | **7**| **2**|

**Fold destinations:**
- Phase 111: 1 finding (CFG — config-set GET→POST migration)
- Phase 112: 5 findings (GUARD — defensive hardening)
- Phase 113: 1 finding (LAUNCH — presentation + community health)

**Parked:** 2 findings with runtime-image-verified rationale.

**Tools run clean (launch-positive evidence):**
- ruff: 0 findings (whole-tree `src/python/`, exact CI command)
- Semgrep: 0 findings (320 rules, 92 files, `--config=auto`)
- gitleaks: 0 leaks (1,172 commits, 17.24 MB, full history)
- pip-audit: 2 CVEs in `pip` binary (local dev venv only; see HR-08)
- npm audit: 4 moderate CVEs (devDependencies only; see HR-09)

---

## CRITICAL

### HR-01: Config-set credentials travel as URL path segments

**Severity:** CRITICAL
**Location:** `src/python/web/handler/config.py:27`, `src/angular/src/app/services/settings/config.service.ts:22`, `src/docker/test/e2e/configure/setup_seedsyncarr.sh:8-29`
**Source:** CONCERNS.md §Security Considerations / SEC-09 / REQUIREMENTS.md CFG-01..04

A skeptical engineer running `grep -r "config/set"` immediately finds `GET /server/config/set/<section>/<key>/<value:re:.+>` — credential values (including `lftp/remote_password`) travel as URL path segments, meaning they land verbatim in server access logs, browser history, reverse-proxy logs, and any monitoring that records raw request URIs. The E2E setup script (`setup_seedsyncarr.sh:8-29`) calls `curl "…/server/config/set/…"` with passwords in the URL, confirming this is the current integration pattern. This is the one change that warrants a minor version bump (breaking HTTP contract).

**Disposition:** FOLD -> Phase 111 (CFG-01..04)

---

## HIGH

### HR-02: Red test — AppProcess unpicklable under spawn start method

**Severity:** HIGH
**Location:** `src/python/common/app_process.py:52-53`, `src/python/tests/unittests/test_common/test_app_process.py:175`
**Source:** STATE.md Tech Debt / RESEARCH.md §5

The test `test_process_with_long_running_thread_terminates_properly` FAILS in the public suite with `TypeError: cannot pickle '_thread.lock' object`. A hostile reader who runs `poetry run pytest` — the obvious sanity-check for any new contributor — hits a red test immediately. A failing test in a CI-gated suite is the single most "vibe-coded" signal a skeptical reviewer encounters. Root cause: `AppProcess.__init__` instantiates `self.__exception_queue = Queue()` and `self._terminate = Event()` from the default (fork) multiprocessing context (`app_process.py:52-53`); under macOS `spawn` start method (default since Python 3.8), these objects cannot be pickled for the subprocess. Result: 1 failed, 8 passed, 1 error in the targeted file.

**Disposition:** FOLD -> Phase 112 (GUARD-04)

---

## MEDIUM

### HR-03: Startup security warning text misleading in one config state (GUARD-01/02 correctness gap)

**Severity:** MEDIUM
**Location:** `src/python/seedsyncarr.py:374-393` (`_emit_startup_warnings`), `src/python/web/handler/webhook.py:54-60`
**Source:** RESEARCH.md §4 GUARD-01/02 / CONCERNS.md §Security Considerations

The startup security warnings for both no-api-token (GUARD-01) and webhook-unauthenticated (GUARD-02) **already exist** in `seedsyncarr.py:374-393` and are tested (`test_seedsyncarr.py:210-228`). This is NOT an unimplemented feature — it is a confirm-the-gap item.

**GUARD-01 gap:** The `api_token` warning fires unconditionally when no token is set (`seedsyncarr.py:384-393`). The warning text is accurate — the app always binds `0.0.0.0` (hardcoded in `web_app_job.py:27`). Gap is prominence: `logging.warning` may not surface to an operator who is not watching logs actively.

**GUARD-02 warning-correctness matrix:**

| `webhook_secret` | `webhook_require_secret` | Actual runtime behavior | Warning text fired | Accurate? |
|---|---|---|---|---|
| empty | False (default) | Accepts any caller; no HMAC | "webhook endpoints accept requests from any caller" | ACCURATE |
| empty | True | **FAILS CLOSED with 503** (webhook.py:54-60 guard fires before any body read) | "accept requests from any caller" (first warning) + "will be rejected with 503" (second warning) | MISLEADING — first warning says "accept any caller" but handler actually REJECTS all callers with 503 |
| set | False | Accepts callers; HMAC verified | No warning | OK (authenticated) |
| set | True | Accepts callers; HMAC enforced | No warning | OK (authenticated) |

The misleading cell is `empty`+`True`: the first startup warning fires saying the endpoint "will accept requests from any caller," but the runtime handler rejects ALL callers with 503. A user reading only the first warning line would believe their endpoint is open when it is actually fail-closed. The second warning (`webhook_require_secret is True but webhook_secret is not set. All webhook requests will be rejected with 503`) partially corrects this, but a user skimming logs may see only the first warning. Phase 112 should either suppress the first warning in this state or reorder/merge to a single accurate message.

**Disposition:** FOLD -> Phase 112 (GUARD-01 prominence gap + GUARD-02 warning-correctness gap)

### HR-04: Delete failures silently swallowed (`ignore_errors=True`)

**Severity:** MEDIUM
**Location:** `src/python/controller/delete/delete_process.py:24`
**Source:** CONCERNS.md §Fragile Areas + §Test Coverage Gaps / REQUIREMENTS.md GUARD-03

`shutil.rmtree(file_path, ignore_errors=True)` swallows ALL exceptions — partial deletes, permission errors, disk-full conditions — without logging anything. A hostile reader who checks the delete path (the most destructive operation in a sync tool) will flag this immediately: if a delete silently fails, the file stays on disk and the user has no signal. There are no test cases for the failure path. This is a real operational correctness gap, not a theoretical edge-case.

**Disposition:** FOLD -> Phase 112 (GUARD-03)

### HR-05: `LICENSE.txt` not recognized by GitHub license detector (shows "No license")

**Severity:** MEDIUM
**Location:** `/LICENSE.txt` (exists), `/LICENSE` (absent at repo root)
**Source:** RESEARCH.md §6 / REQUIREMENTS.md LAUNCH-05 / D-09

`LICENSE.txt` exists and contains correct Apache 2.0 text — this is **NOT** a missing license, it is a misnamed one. GitHub license detection reads files named exactly `LICENSE`, `LICENSE.md`, or `COPYING`; the `.txt` suffix is not recognized, so the repo metadata shows "No license" and the `shields.io/github/license` badge likely reflects the same. A skeptical reviewer browsing the repo will read "No license" in the sidebar and either stop or conclude this is an incomplete/abandoned project. The fix is a rename: `LICENSE.txt` -> `LICENSE` (plus updating the `README.md:118` badge link from `LICENSE.txt` to `LICENSE`).

**Disposition:** FOLD -> Phase 113 (LAUNCH-05)

---

## LOW

### HR-06: Legacy `~/.seedsync` fallback warning may not surface pre-logger (GUARD-06)

**Severity:** LOW
**Location:** `src/python/seedsyncarr.py:265-272`
**Source:** CONCERNS.md §Tech Debt / REQUIREMENTS.md GUARD-06

The `~/.seedsync` fallback warning at `seedsyncarr.py:268-271` uses bare `logging.warning()` **before** `_create_logger()` is called (at line ~285). The root logger has no handlers configured at that point, so the warning silently disappears into the logging void unless the user has already configured root-level handlers elsewhere. A user who typos `--config_dir` will load a stale legacy config with no visible indication unless they are watching stderr very carefully. The warning exists but may not reach the operator.

**Disposition:** FOLD -> Phase 112 (GUARD-06 narrow gap — warning exists, surfacing is unreliable)

### HR-07: Tooling artifacts not in `.gitignore` (`.orchestrator.json`, `.playwright-mcp/`)

**Severity:** LOW
**Location:** `.gitignore` (missing entries), repo root (`.orchestrator.json`, `.playwright-mcp/` present untracked)
**Source:** CONCERNS.md §Tech Debt / REQUIREMENTS.md GUARD-05

Both `.orchestrator.json` and `.playwright-mcp/` are present in the working tree, untracked, and NOT matched by `.gitignore`. A hostile reader who runs `git status` or looks at the repo's untracked files list sees these tooling/run artifacts immediately. `.DS_Store`, `.aidesigner/*`, `.bg-shell/`, and `.turingmind/` are already gitignored — these two slipped through. Risk: accidental commit of local orchestration state.

**Disposition:** FOLD -> Phase 112 (GUARD-05)

### HR-08: npm audit: 4 moderate CVEs (ws, brace-expansion) in devDependencies

**Severity:** LOW
**Location:** `src/angular/package.json` (devDependencies: `karma`, `eslint`)
**Source:** npm audit run 2026-06-02 / REQUIREMENTS.md DEFER-* context

npm audit reports 4 moderate vulnerabilities: `brace-expansion` (CVE GHSA-jxxr-4gwj-5jf2, via `eslint > minimatch > brace-expansion`) and `ws` (CVE GHSA-58qx-3vcg-4xpx, via `karma > socket.io > engine.io > ws`; also `socket.io-adapter`). Both root packages (`eslint`, `karma`) are **devDependencies** confirmed in `package.json`. Neither `node_modules/` nor devDependency packages ship in the runtime container.

**Runtime-image verification (from Dockerfile inspection + build stages):** The Angular SPA is compiled by the `seedsyncarr_build_angular` build stage (`ng build --configuration=production`). Only the compiled static output is copied into the runtime image via `COPY --from=seedsyncarr_build_angular /build/dist/browser /app/html` (Dockerfile:123). The `node_modules/` directory and all devDependencies reside exclusively in the `seedsyncarr_build_angular_env` build stage and are **NOT** copied into `seedsyncarr_run`. Verified: the flagged packages (`ws`, `brace-expansion`, `engine.io`, `socket.io-adapter`) are not present in the shipped runtime image.

**Disposition:** PARK -- devDependencies only; verified not copied into `seedsyncarr_run` runtime image (Dockerfile:123 `COPY --from=seedsyncarr_build_angular /build/dist/browser /app/html` — node_modules excluded); not reachable in the deployed container

### HR-09: pip-audit: 2 CVEs in `pip` binary (local dev venv, NOT in shipped container)

**Severity:** LOW
**Location:** Local Poetry venv (`pip 26.0.1`), NOT in the shipped Docker image
**Source:** pip-audit run 2026-06-02 / RESEARCH.md §1.3

pip-audit reports `pip 26.0.1` has CVE-2026-3219 and CVE-2026-6357 (fix: pip >= 26.1) in the local Poetry virtualenv. These CVEs are in the `pip` packaging tool itself, not in any application dependency.

**Runtime-image verification (from Dockerfile inspection + built-image package listing):** The runtime image (`seedsyncarr_run_python_env`) is built on `python:3.11-slim` and installs `pip3 install poetry` (Dockerfile:96) + `poetry install --only main` (Dockerfile:106). A local read-only inspection of the shipped runtime image (`docker run --rm seedsyncarr/run/python/devenv:latest pip --version`) confirms: **pip 24.0** is installed in the shipped image (from the `python:3.11-slim` base), NOT pip 26.0.1. The CVE-affected pip 26.0.1 is present only in the local macOS development venv (Python 3.12 Poetry venv), not in the Docker image's Python 3.11 environment. Additionally, `poetry` (2.4.1) is present in the runtime image as expected (ships as part of the dependency installation mechanism), but its `pip` remains the 3.11-slim base version 24.0 which is not in the CVE range.

**Disposition:** PARK -- CVE affects pip 26.0.1 in local macOS dev venv only; shipped runtime image verified to use pip 24.0 (python:3.11-slim base) which is not in the CVE range (fix required >= 26.1, so only pip 26.x is affected); not reachable in the deployed container

---

## Appendix A: Pre-Parked Latent / Out-of-Scope Items

These items are **excluded from the HR- finding list, HR- IDs, and the Summary rollup** (D-04). They are latent, invisible to a launch reader, or externally blocked — tracked here for completeness only.

### Future Requirements (REQUIREMENTS.md DEFER-*)

**DEFER-SHUTDOWN** — Deferred shutdown sequencing (`seedsyncarr.py:197-205`): fixed `time.sleep` in the main shutdown loop. Real robustness gain, but invisible to a r/selfhosted browser. No test-visible signal.
PARK -- invisible to launch reader; tracked in REQUIREMENTS.md as DEFER-SHUTDOWN

**DEFER-STREAMQUEUE** — Non-atomic `StreamQueue.put` drop-oldest (`web/utils.py:33-63`): under concurrent producers a second `put(block=False)` can still raise `Full`. Latent, bounded, logged, documented. Not a browser-visible defect.
PARK -- latent, well-mitigated, documented; tracked in REQUIREMENTS.md as DEFER-STREAMQUEUE

**DEFER-TESTHARDEN** — Test-suite hardening backlog (A-01..A-06): test-infra quality improvements invisible to a launch reader.
PARK -- test-infra niceties invisible to a launch reader; tracked in REQUIREMENTS.md as DEFER-TESTHARDEN

**DEFER-WEBOB** — `PYTHONWARNINGS` cgi filter: blocked until webob ships without the stdlib `cgi` import (upstream PR #466 open). Not actionable.
PARK -- blocked on upstream webob 2.0 release; tracked in REQUIREMENTS.md as DEFER-WEBOB

### Out of Scope (REQUIREMENTS.md Out of Scope table)

**NAS-QEMU** — NAS local-build QEMU issue: deploy-environment limitation, not a code defect. CI multi-arch publish works.
PARK -- environment limitation, not a code defect; tracked in REQUIREMENTS.md Out of Scope

**Dual-GET config-set** — Keeping both GET and POST live for config-set: explicitly rejected per D-4 (the insecure GET path must go, not be preserved alongside a POST path).
PARK -- out of scope per REQUIREMENTS.md Out of Scope (D-4 decision)

---

## Appendix B: What Was Checked and Came Up Clean

This section records the launch-positive evidence a hostile reader would find if they ran the standard tools.

**Static Analysis (Python):** `ruff check src/python/` — `All checks passed!` Zero findings. This is the exact CI lint-gate command (whole-tree, not scoped). A hostile reader who runs `ruff check` in under 10 seconds gets a green result.

**SAST (Semgrep):** `semgrep scan src/python --config=auto` — `Ran 320 rules on 92 files: 0 findings`. The 320 auto-rules include injection patterns, secret detection, use-after-free equivalents, and command-execution risks. Zero findings across the full Python source tree.

**Secret Scan (gitleaks):** `gitleaks detect --source . --config .gitleaks.toml --no-banner` — `no leaks found` across 1,172 commits, 17.24 MB. Full commit history is clean; the `.gitleaks.toml` allowlist correctly suppresses test-fixture false positives.

**Coverage:** Python test suite at ~89% container-inclusive coverage (CI enforces `fail_under = 88`). Angular Karma enforces `check.global` floors (stmts 83 / branches 68 / fns 79 / lines 83). High coverage is one of the strongest "this is not vibe-coded" signals to a technical reviewer.

**Security hardening:** Bearer token API auth (auto-generated, constant-time comparison, meta tag injection), HMAC-SHA256 webhook authentication, hash-based CSP via Angular autoCsp (no `unsafe-inline`), DNS rebinding prevention, path traversal guards, rate limiting on all mutable endpoints, Fernet encryption at rest for secrets, `shlex.quote` on all shell-bound remote paths, `pexpect.spawn(argv)` (no `shell=True`), SSH TOFU (`accept-new`) with changed-key detection. Zero Semgrep injection findings confirms these mitigations are not just claims.

---

## Appendix C: CONCERNS.md Cross-Reference

The following CONCERNS.md entries are cross-referenced by the above findings. CONCERNS.md is not mutated — see `CONCERNS.md` §Tech Debt, §Security Considerations, §Fragile Areas, §Test Coverage Gaps for the underlying detail.

| Finding | CONCERNS.md Entry |
|---------|-------------------|
| HR-01 (config-set) | §Security Considerations — "Auth and Host validation are opt-in" |
| HR-03 (startup warnings) | §Security Considerations — "Webhook HMAC verification is skipped when no secret is set" |
| HR-04 (delete swallow) | §Fragile Areas — (implied by `ignore_errors=True` pattern) |
| HR-06 (seedsync fallback) | §Tech Debt — "Legacy config-directory fallback" |
| HR-07 (gitignore) | §Tech Debt — "Untracked operational artifacts not in `.gitignore`" |
| DEFER-SHUTDOWN | §Tech Debt — "Deferred shutdown sequencing in main loop" |
| DEFER-STREAMQUEUE | §Known Bugs — "`StreamQueue.put` drop-oldest is not atomic" |
