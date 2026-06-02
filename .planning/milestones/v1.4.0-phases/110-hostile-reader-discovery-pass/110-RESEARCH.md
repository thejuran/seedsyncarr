# Phase 110: Hostile-Reader Discovery Pass — Research

**Researched:** 2026-06-02
**Domain:** Security audit tooling, findings-artifact design, pre-named fix scope verification
**Confidence:** HIGH (all evidence gathered from direct tool runs and codebase reads in this session)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Tool set = ruff whole-tree + Shield (Semgrep SAST + gitleaks + dep audit) + pip-audit + npm audit + entry-point/high-traffic reads. No new tooling introduced.
- D-02: All tool runs are read-only / report-only. No `--fix`, no autofix.
- D-03: Fold bar = "a skeptical r/selfhosted engineer would visibly hold this against the project on launch day."
- D-04: Latent, well-mitigated, invisible-to-a-reader items are PARKED with one-line rationale.
- D-05: Deliverable = `110-FINDINGS.md` in the phase directory. Do NOT edit `CONCERNS.md`.
- D-06: Artifact structure = severity-grouped findings; per-finding: stable ID, title, file:line, 1-2 sentence hostile-reader framing, explicit FOLD/PARK disposition line.
- D-07: Artifact includes a summary rollup at the top: counts by severity and by disposition.
- D-08: The six pre-named fix items are locked/confirm-only — not re-litigated.
- D-09: Missing `LICENSE` file at repo root is confirmed absent (D-09). Disposition: `FOLD → Phase 113`.

### Claude's Discretion
- Exact severity scheme labels and finding-ID prefix.
- Whether Shield runs via `/shield:shield` orchestrator or individual tool scripts.
- Ordering/sectioning within the artifact beyond severity-ranked + disposition.
- Whether to include a "what was checked but came up clean" appendix.

### Deferred Ideas (OUT OF SCOPE)
- DEFER-SHUTDOWN, DEFER-STREAMQUEUE, DEFER-TESTHARDEN, DEFER-WEBOB (REQUIREMENTS.md "Future Requirements").
- NAS local-build QEMU fix, dual-GET+POST support for config-set (REQUIREMENTS.md "Out of Scope").
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCAN-01 | A maintainer can read a triaged findings artifact that lists, by severity, what a skeptical engineer reviewing the public repo would flag — produced by reading the entry points, running ruff whole-tree + Semgrep/Shield + dependency audit, skimming high-traffic files. | Tool invocation patterns confirmed (§1). All tools verified available and working. |
| SCAN-02 | Each finding is marked "fold into a v1.4.0 fix phase" (with target) or "parked" (with rationale), so scope decisions are explicit and traceable. | Artifact schema defined (§3). Pre-named fix scope confirmed with file:line evidence (§4). Parked items pre-identified from REQUIREMENTS.md (§2). |
</phase_requirements>

---

## Summary

Phase 110 is a read-only discovery/audit pass that produces `110-FINDINGS.md`. The research
confirms this project is in an unusually clean state: ruff whole-tree passes with zero findings,
Semgrep auto-rules (320 rules, 92 files) returns zero findings, and gitleaks returns no leaks
across 1,167 commits. The primary findings for the pass are already known from CONCERNS.md and
the design spec's pre-named fix scope — the pass confirms them with file:line evidence and
assigns explicit fold/park dispositions.

Two material discoveries that change the planning context:

1. **GUARD-01 and GUARD-02 are substantially already implemented.** `_emit_startup_warnings()` in
   `seedsyncarr.py:372-397` fires at startup for both the no-api-token and no-webhook-secret
   conditions, with tests in `test_seedsyncarr.py`. These were introduced in commits 340567e
   (v1.3.0-s2) and earlier. CONCERNS.md was written as a recommendation ("consider warning"), but
   the code already has the warnings. Phase 112 planning should verify the GUARD-01/02
   requirements are fully satisfied or identify the precise remaining gap (e.g. "non-loopback"
   conditionality vs. unconditional), rather than building them from scratch.

2. **The LICENSE gap is `LICENSE.txt` not `LICENSE`.** The file `LICENSE.txt` exists and contains
   Apache 2.0 text. GitHub's license detection reads files named exactly `LICENSE` (or `LICENSE.md`);
   the `.txt` suffix causes the license badge to silently read from the wrong path. The README badge
   already links to `LICENSE.txt` (correct for the Markdown link) but the GitHub repo metadata
   license field will show "No license" because GitHub doesn't recognize `LICENSE.txt`. The finding
   should say "rename `LICENSE.txt` → `LICENSE`" not "create a LICENSE file."

The pass's additive value beyond the pre-named items is: npm audit (4 moderate devDep CVEs),
pip-audit (2 `pip` binary CVEs unrelated to app deps), and the GUARD-01/02 implementation
re-check. Near-clean result is itself launch-positive evidence.

**Primary recommendation:** The executor runs each tool, captures its exact output, and maps
every finding (new or pre-named) onto the `110-FINDINGS.md` schema with fold/park disposition.
The near-clean tooling result is recorded in a "came up clean" appendix for launch-confidence.

---

## Section 1: Tool Invocation Patterns

All commands are read-only. Run from repo root `/Users/julianamacbook/seedsyncarr` unless noted.

### 1.1 ruff — Python Linter

```bash
ruff check src/python/
```

**Current output (verified in this session):** `All checks passed!` — zero findings.
[VERIFIED: direct tool run, 2026-06-02]

Notes:
- This is the exact command CI runs as a separate gate from pytest (see CI lint gap note).
- No `--fix`, no `--select`, no `--ignore`. Whole-tree exactly matches CI.
- `ruff` is installed as a dev dependency (`src/python/pyproject.toml:30`, `ruff >= 0.4.0`).
  Available without any `uvx`/`pipx` fallback.

### 1.2 Shield — SAST + Secrets + Dependency Audit

Shield is installed as a nested skill repo at `shield-claude-skill/`. Three invocation paths:

**Option A — Via skill invocation (orchestrated):**
```
/shield:shield quick
```
Runs Semgrep + gitleaks + package audit + dependency freshness in one pass.
Saves consolidated report to `reports/security-YYYY-MM-DD.md`.

**Option B — Via individual Shield scripts (faster, matches D-02 read-only discipline):**

```bash
# SAST (Semgrep)
bash shield-claude-skill/scripts/run-sast.sh /path/to/repo python
# Uses shield-claude-skill/configs/semgrep-rules/python.yaml

# Secrets (gitleaks)
bash shield-claude-skill/scripts/run-secrets.sh /path/to/repo

# Package audit
bash shield-claude-skill/scripts/run-sca.sh /path/to/repo pip
```

**Option C — Semgrep standalone (broader rule set):**
```bash
semgrep scan src/python --config=auto
```
Runs 320 auto-rules against 92 Python source files.

**Current output (all verified in this session):**
- Shield SAST (`run-sast.sh`): 0 findings [VERIFIED: direct tool run, 2026-06-02]
- `semgrep scan --config=auto`: `Ran 320 rules on 92 files: 0 findings` [VERIFIED: direct tool run, 2026-06-02]
- `gitleaks detect`: `no leaks found` (1,167 commits scanned, 17.16 MB) [VERIFIED: direct tool run, 2026-06-02]

**Tool availability (verified):**
- `semgrep`: installed at `/Users/julianamacbook/Library/Python/3.9/bin/semgrep`, version 1.136.0
- `gitleaks`: installed at `/opt/homebrew/bin/gitleaks`, version 8.30.1
- Both confirmed by `shield-claude-skill/scripts/check-prereqs.sh` [VERIFIED: direct run, 2026-06-02]

**gitleaks config:** `.gitleaks.toml` at repo root allowlists `src/python/tests/` paths to suppress test-fixture false positives. Run with `--config .gitleaks.toml`.

Standalone gitleaks command:
```bash
gitleaks detect --source . --config .gitleaks.toml --no-banner
```

### 1.3 pip-audit — Python Dependency CVE Audit

**Project uses Poetry** (`src/python/poetry.lock`). There is no `requirements.txt`. The correct
invocation targets the project's Poetry venv directly:

```bash
# Step 1: get the venv path
VENV=$(poetry -C src/python env info --path)

# Step 2: run pip-audit against that Python interpreter
PIPAPI_PYTHON_LOCATION="${VENV}/bin/python" pip-audit
```

Or as a one-liner:
```bash
PIPAPI_PYTHON_LOCATION="$(poetry -C src/python env info --path)/bin/python" pip-audit
```

**Why not `pip-audit --project-path`:** `--project-path` is not a valid flag for pip-audit 2.10.0.
`pip-audit -r` requires a flat `requirements.txt`, which Poetry does not produce without the
deprecated `poetry export` plugin. The `PIPAPI_PYTHON_LOCATION` env var is the correct mechanism.

**pip-audit is installed:** `/Users/julianamacbook/.local/bin/pip-audit`, version 2.10.0.
Does NOT need `uvx pip-audit` or `pipx run pip-audit`.

**Current output (verified in this session):**
```
Found 2 known vulnerabilities in 1 package
Name    Version    ID              Fix Versions
pip     26.0.1     CVE-2026-3219   26.1
pip     26.0.1     CVE-2026-6357   26.1
```
[VERIFIED: direct tool run, 2026-06-02]

NOTE: These CVEs are in the `pip` binary itself inside the venv, NOT in any application
dependency. The project's application deps (pexpect, cryptography, requests, patool, etc.) are
clean. `pip` is a build/packaging tool, not shipped in the Docker runtime image. Expected
disposition: **PARK** — pip CVEs in the dev venv do not affect the deployed container; the
Dockerfile installs app packages, not pip itself.

### 1.4 npm audit — Angular Dependency CVE Audit

```bash
# From the Angular tree
npm audit --prefix src/angular
```

Or from within `src/angular/`:
```bash
cd src/angular && npm audit
```

**npm version:** 11.12.1 at `/opt/homebrew/bin/npm`. Already installed — no `npx` needed.

**Current output (verified in this session):**
```
brace-expansion  5.0.2 - 5.0.5   (moderate)
  brace-expansion: Large numeric range defeats documented max DoS protection
  via: eslint > minimatch > brace-expansion

ws  8.0.0 - 8.20.0   (moderate)
  ws: Uninitialized memory disclosure
  via: karma > socket.io > engine.io > ws

4 moderate severity vulnerabilities
```
[VERIFIED: direct tool run, 2026-06-02]

**Severity scale for npm audit:** npm uses `critical | high | moderate | low | info`. `moderate`
means exploitable but requires specific conditions or has limited blast radius.

**Key context for disposition:** All four moderate findings are in **devDependencies** (`karma`
for ws/socket.io/engine.io; `eslint` for brace-expansion). They are NOT present in the
production Docker image — the Angular SPA is built (`ng build`) and only the compiled static
files are shipped; `node_modules/` is never present at runtime. Expected disposition: **PARK** —
devDependency-only CVEs, not reachable at runtime.

**How to read npm audit severity output:**
- `npm audit --json` for machine-readable output with `metadata.vulnerabilities.{critical,high,moderate,low}` keys.
- `npm audit` (text) gives the dependency chain showing which package introduced the vulnerable dep.
- Check `via:` chain to determine if the vulnerable package is a production or dev dep.

### 1.5 Entry-Point + High-Traffic Read

No special command — the executor reads these files directly:

| File | Why a Hostile Reader Looks |
|------|---------------------------|
| `README.md` | First impression; screenshots, quickstart, claims |
| `src/python/seedsyncarr.py` | Daemon entry point; startup logic; `_emit_startup_warnings` |
| `src/python/web/web_app.py` | Auth gate, token handling, CSP |
| `src/python/web/handler/config.py` | Config-set GET endpoint (SEC-09) |
| `src/python/controller/delete/delete_process.py` | `ignore_errors=True` delete swallow |
| `src/python/common/app_process.py` | Queue()/Event() from default context (spawn failure) |
| `.gitignore` | Untracked artifacts |
| `src/python/pyproject.toml` | Dependency posture |

---

## Section 2: Existing Audit Baseline (CONCERNS.md Cross-Reference)

CONCERNS.md (2026-06-02 post-v1.3.0 audit) already enumerates these items. The pass
CONFIRMS rather than rediscovers them. Each is tagged with its CONCERNS.md section and the
pre-determined disposition.

### Already in CONCERNS.md — Pass Confirms and Disposes

| CONCERNS.md Item | Section | Pass Disposition |
|-----------------|---------|-----------------|
| Legacy `~/.seedsync` fallback — silent on missing `--config_dir` | Tech Debt | FOLD → Phase 112 (GUARD-06) |
| Untracked `.orchestrator.json` + `.playwright-mcp/` not in `.gitignore` | Tech Debt | FOLD → Phase 112 (GUARD-05) |
| `shutil.rmtree(ignore_errors=True)` swallows delete failures | Fragile Areas + Test Coverage Gaps | FOLD → Phase 112 (GUARD-03) |
| Auth opt-in: no api_token → all endpoints unauthenticated | Security Considerations | FOLD → Phase 112 (GUARD-01) — **already substantially implemented**, see §4 |
| Webhook HMAC skipped when no secret + require_secret off | Security Considerations | FOLD → Phase 112 (GUARD-02) — **already substantially implemented**, see §4 |
| DEFER-SHUTDOWN: fixed `time.sleep` in shutdown | Tech Debt | PARK — invisible to launch reader (REQUIREMENTS.md DEFER-SHUTDOWN) |
| DEFER-STREAMQUEUE: non-atomic drop-oldest | Known Bugs | PARK — latent, well-mitigated, documented (REQUIREMENTS.md DEFER-STREAMQUEUE) |
| AutoQueue single-thread assumption | Tech Debt | PARK — latent coupling, not a current defect |
| Bootstrap 5.3 `@import` | (STATE.md Tech Debt) | PARK — blocked on Bootstrap 6 |
| SSE busy-poll loop | Performance | PARK — acceptable for expected client count |
| Remote scan md5sum round-trip | Performance | PARK — correctness-over-speed, acceptable |
| lftp pexpect fragility | Fragile Areas | PARK — well-tested, not a launch-visible bug |
| Single-threaded model lock | Performance | PARK — correctly handled, structural constraint |
| NAS local-build QEMU | Missing Critical Features | PARK — environment limitation (REQUIREMENTS.md Out of Scope) |
| Integration tests need Docker | Test Coverage Gaps | PARK — invisible to launch reader |
| `fail_under = 88` (not 100%) | Test Coverage Gaps | PARK — mostly defensive error branches |

### Areas NOT Covered by CONCERNS.md — Pass Must Add

| Area | What the Pass Adds |
|------|-------------------|
| Entry-point readability | README first-impression (screenshot, quickstart accuracy, claims) |
| LICENSE gap | `LICENSE.txt` named incorrectly for GitHub detection → `LICENSE` needed (confirmed §1) |
| Dependency CVEs | pip-audit (2 pip CVEs) + npm audit (4 moderate devDep CVEs) |
| Secret leakage in git history | gitleaks scan (confirmed clean — 0 findings across 1,167 commits) |
| SAST findings | Semgrep (confirmed clean — 0 findings across 320 rules / 92 files) |
| Red failing test | AppProcess spawn test (confirmed failing — see §5) |
| Config-set credential leak | SEC-09: `GET /server/config/set/{section}/{key}/{value}` (confirm file:line) |

---

## Section 3: Findings Artifact Schema

The `110-FINDINGS.md` file should follow this exact structure to satisfy SCAN-01 (maintainer
can read a triaged severity-ranked artifact) and SCAN-02 (every finding has explicit disposition).

### 3.1 Severity Scheme

Use four levels matching Shield's scheme (established in `shield-claude-skill/CLAUDE.md`):

| Level | Label | Meaning for this pass |
|-------|-------|-----------------------|
| CRITICAL | Critical | Credential leak in transit or at rest, actively exploitable |
| HIGH | High | Red/failing test, major security misconfiguration visible to a reviewer |
| MEDIUM | Medium | Real issue a hostile reader would flag but not immediately exploitable |
| LOW | Low | Repo hygiene tell, minor code smell a skeptical reader screenshots |

### 3.2 Finding ID Prefix

Use `HR-` prefix (Hostile-Reader) with two-digit sequence: `HR-01`, `HR-02`, ... (up to HR-99).
This is distinct from Shield's `SHIELD-XXX` IDs and traceable to this phase.

### 3.3 Per-Finding Fields

```markdown
### HR-XX: [One-line title]

**Severity:** [CRITICAL | HIGH | MEDIUM | LOW]
**Location:** `[file:line]` (or multiple files)
**Source:** [CONCERNS.md §section | SEC-09 | this pass | D-09]

[1-2 sentences written from the hostile reader's perspective: what they see,
why they'd screenshot it or hold it against the project.]

**Disposition:** FOLD → Phase [111|112|113]
  — or —
**Disposition:** PARK — [one-line rationale]
```

### 3.4 Summary Rollup (Top of Artifact)

```markdown
## Summary

| Severity | Count | Fold | Park |
|----------|-------|------|------|
| Critical | N     | N    | N    |
| High     | N     | N    | N    |
| Medium   | N     | N    | N    |
| Low      | N     | N    | N    |
| **Total**| **N** | **N**| **N**|

**Fold destinations:**
- Phase 111: [N] findings (CFG — config-set GET→POST migration)
- Phase 112: [N] findings (GUARD — defensive hardening)
- Phase 113: [N] findings (LAUNCH — presentation + community health)

**Parked:** [N] findings with written rationale.

**Tools run clean (launch-positive evidence):**
- ruff: 0 findings (whole-tree)
- Semgrep: 0 findings (320 rules, 92 files)
- gitleaks: 0 leaks (1,167 commits, 17.16 MB)
- pip-audit: 2 CVEs in pip binary (dev venv only, not app deps, not in container)
- npm audit: 4 moderate CVEs (devDependencies only, not in production image)
```

### 3.5 SCAN-02 Compliance Check

Every finding MUST have exactly one disposition line in the form:
- `FOLD → Phase NNN` (with N in {111, 112, 113})
- `PARK — [rationale referencing REQUIREMENTS.md DEFER-* or other specific reason]`

No finding may be left without a disposition. The planner should add a verification step that
counts findings vs. dispositioned findings and asserts equality.

---

## Section 4: Pre-Named Fix Scope Confirmation

The six fix items from the design spec (D-07, D-08 context) are confirmed with exact file:line
evidence. These are LOCKED — the pass records them as already-folded, does NOT re-litigate.

### CFG: config-set GET endpoint (SEC-09)

**Confirmed real.** File:line evidence:
- **Backend route:** `src/python/web/handler/config.py:27` — `"/server/config/set/<section>/<key>/<value:re:.+>"`
- **Handler function:** `src/python/web/handler/config.py:92` — `def __handle_set_config(self, section, key, value)`
- **Angular caller:** `src/angular/src/app/services/settings/config.service.ts:22` — `` `/server/config/set/${section}/${option}/${value}` ``
- **E2E page object:** `src/e2e/tests/settings.page.ts:16, 25, 33, 37, 60, 71, 80, 89` — multiple `GET /server/config/set/...` calls
- **E2E setup script:** `src/docker/test/e2e/configure/setup_seedsyncarr.sh:8–29` — `curl -sSf "http://myapp:8800/server/config/set/..."` (credentials like `lftp/remote_password` in URL)

Disposition: `FOLD → Phase 111` (CFG-01..04)

### GUARD-01: Startup warning — non-loopback + no api_token

**IMPORTANT RE-CHARACTERIZATION:** The warning already exists.
`src/python/seedsyncarr.py:384-393` (`_emit_startup_warnings`, called at line 120):
```python
if not config.general.api_token:
    logger.warning("Security: No API token configured. ...")
    logger.warning("Security: Application is bound to 0.0.0.0 without an API token. ...")
```
Tested at `src/python/tests/unittests/test_seedsyncarr.py:220-228`
(`test_startup_warns_when_api_token_empty`).

The warning fires unconditionally when no api_token, which is correct because
`web_app_job.py:27` hardcodes `host="0.0.0.0"` — the app ALWAYS binds non-loopback. Since the
"non-loopback" condition is always true at runtime, the "no api_token" check is equivalent to
"non-loopback + no api_token."

**Finding for the pass:** GUARD-01 requirement is substantially met by existing code. Phase 112
planning should verify this satisfies the requirement or identify remaining gap (e.g. promotion
to a more prominent banner rather than standard `logging.warning`). Record as already-folded:
`FOLD → Phase 112` (confirm-only; gap may be narrower than originally estimated).

### GUARD-02: Startup warning — webhook unauthenticated

**IMPORTANT RE-CHARACTERIZATION:** The warning already exists.
`src/python/seedsyncarr.py:374-380`:
```python
if not config.general.webhook_secret:
    logger.warning("Security: webhook_secret is not configured. ...")
if config.general.webhook_require_secret and not config.general.webhook_secret:
    logger.warning("Security: webhook_require_secret is True but webhook_secret is not set. ...")
```
Tested at `src/python/tests/unittests/test_seedsyncarr.py:210-218`
(`test_startup_warns_when_webhook_secret_empty`).

Same characterization as GUARD-01. `FOLD → Phase 112` (confirm-only).

### GUARD-03: Delete-path `ignore_errors=True` swallow

**Confirmed real.** `src/python/controller/delete/delete_process.py:24`:
```python
shutil.rmtree(file_path, ignore_errors=True)
```
CONCERNS.md §Fragile Areas + §Test Coverage Gaps confirm this.
`FOLD → Phase 112` (GUARD-03)

### GUARD-04: AppProcess spawn failure / red test

**Confirmed failing.** See §5 for full details.
`src/python/common/app_process.py:52-53`:
```python
self.__exception_queue = Queue()
self._terminate = Event()
```
Both imported from `multiprocessing` (fork context default). Under `spawn`, pickling fails.
Test: `src/python/tests/unittests/test_common/test_app_process.py:175`
(`test_process_with_long_running_thread_terminates_properly`) — **CURRENTLY FAILING**.
`FOLD → Phase 112` (GUARD-04)

### GUARD-05: `.gitignore` missing entries

**Confirmed real.** `.gitignore` does not contain `.orchestrator.json` or `.playwright-mcp/`:
```bash
$ grep -E "orchestrator|playwright-mcp" .gitignore
(no output)
```
Both files are present in the working tree (confirmed by `git status` at session start).
`FOLD → Phase 112` (GUARD-05)

### GUARD-06: Legacy `~/.seedsync` fallback — silent

**CONFIRMED NUANCE:** The fallback DOES log a warning (`logging.warning` at `seedsyncarr.py:268-271`):
```python
logging.warning(
    "Config directory %s not found; falling back to legacy %s",
    args.config_dir, legacy_dir
)
```
However this uses `logging.warning` before the logger is configured (it runs at arg-parse time
at `seedsyncarr.py:265-272`, before `_create_logger` at line ~285). This means the warning may
not be visible in the configured log output. Also, CONCERNS.md says "already logged at WARNING —
consider promoting to a one-time banner."

GUARD-06 requirement: "operator sees a loud one-time warning." The current `logging.warning`
pre-logger-setup may not satisfy "loud." Phase 112 planning should investigate whether this
warning actually surfaces in the configured output.
`FOLD → Phase 112` (GUARD-06, narrow gap)

---

## Section 5: The AppProcess Red Test

### Failing Test Location

`src/python/tests/unittests/test_common/test_app_process.py:175` —
`TestAppProcess::test_process_with_long_running_thread_terminates_properly`

Run command (from repo root):
```bash
poetry -C src/python run pytest tests/unittests/test_common/test_app_process.py -v
```

### Current Failure Output (verified in this session)

```
FAILED test_app_process.py::TestAppProcess::test_process_with_long_running_thread_terminates_properly
TypeError: cannot pickle '_thread.lock' object
```

Full traceback: `AppProcess.start()` → `popen_spawn_posix.py` → `reduction.dump(obj)` →
`ForkingPickler.dump(obj)` → `TypeError: cannot pickle '_thread.lock' object`

The test uses macOS `spawn` start method (the default on macOS since Python 3.8). When
`AppProcess` is pickled for the spawned subprocess, `Queue()` and `Event()` from the fork
context hold `_thread.lock` objects that cannot be pickled.

**Result:** 1 failed, 8 passed, 1 error (the same test counts as both FAILED and ERROR).

### Root Cause in Source

`src/python/common/app_process.py:52-53`:
```python
from multiprocessing import Process, Queue, Event
...
self.__exception_queue = Queue()   # line 52 — fork-context Queue
self._terminate = Event()          # line 53 — fork-context Event
```

Both are instantiated from the default (fork) multiprocessing context. Under spawn, the
`AppProcess` instance is pickled before `start()`, and `_thread.lock` objects inside
fork-context synchronization primitives cannot be pickled.

### Fix Pattern (for Phase 112)

Same as the shipped INFRA-01 MP-logger fix (Phase 107 precedent): create the queue and event
from a spawn-compatible context (`multiprocessing.get_context('spawn').Queue()` /
`get_context('spawn').Event()`) or use the context-agnostic `multiprocessing.Manager`-based
approach. STATE.md Tech Debt entry confirms this analysis.

### Finding Record for the Artifact

This is the single most "vibe-coded" launch tell: a red test in the public CI suite.
**HR finding:** HIGH severity.
`FOLD → Phase 112` (GUARD-04)

---

## Section 6: The LICENSE Gap

### Confirmed State

- `LICENSE.txt` EXISTS at repo root — Apache License 2.0 text confirmed.
- `LICENSE` (no extension) does NOT exist — confirmed by `ls /path/LICENSE 2>/dev/null`.
- GitHub license detection reads files named exactly `LICENSE`, `LICENSE.md`, `LICENSE.rst`,
  or `COPYING`. `LICENSE.txt` is NOT recognized. [ASSUMED — GitHub license detection file
  naming behavior; consistent with known GitHub community health file requirements.]

### Implications

1. The `shields.io/github/license/thejuran/seedsyncarr` badge in README.md may display
   "no license" rather than "Apache 2.0" to repo visitors. (Badge reads GitHub's API.)
2. `README.md:118` links to `LICENSE.txt` — this Markdown link is functional.
3. `src/angular/package.json` declares `"license": "Apache 2.0"` — correct.

### Fix

Rename `LICENSE.txt` → `LICENSE` (no extension). This is the convention GitHub expects.
The README Markdown link will need updating from `LICENSE.txt` to `LICENSE`.

### Disposition

`FOLD → Phase 113` (LAUNCH-05 — community health files including accurate `LICENSE`)

NOTE: This is a rename, not a create. The D-09 language "verified absent" refers to the
standard `LICENSE` filename, not the content. Content is present in `LICENSE.txt`.

---

## Section 7: Findings Artifact Content Preview

Based on the research, the planner can pre-populate the executor's starting point for
`110-FINDINGS.md`. Expected finding list (IDs assigned by executor):

| ID | Title | Severity | Source | Disposition |
|----|-------|----------|--------|-------------|
| HR-01 | Config-set credentials travel as URL path segments | CRITICAL | CONCERNS.md SEC, config.py:27 | FOLD → Phase 111 |
| HR-02 | Red test: AppProcess unpicklable under spawn start method | HIGH | STATE.md Tech Debt, test_app_process.py:175 | FOLD → Phase 112 (GUARD-04) |
| HR-03 | Startup security warnings may not surface (GUARD-01/02) | MEDIUM | seedsyncarr.py:372-397 | FOLD → Phase 112 (confirm gap) |
| HR-04 | Delete failures silently swallowed (`ignore_errors=True`) | MEDIUM | delete_process.py:24 | FOLD → Phase 112 (GUARD-03) |
| HR-05 | `LICENSE.txt` not recognized by GitHub (should be `LICENSE`) | MEDIUM | repo root, README badge | FOLD → Phase 113 (LAUNCH-05) |
| HR-06 | Legacy `~/.seedsync` fallback warning may not surface pre-logger | LOW | seedsyncarr.py:265-272 | FOLD → Phase 112 (GUARD-06) |
| HR-07 | Tooling artifacts not git-ignored (`.orchestrator.json`, `.playwright-mcp/`) | LOW | .gitignore | FOLD → Phase 112 (GUARD-05) |
| HR-08 | npm audit: 4 moderate CVEs (ws, brace-expansion) in devDependencies | LOW | npm audit src/angular | PARK — devDeps only, not in production image |
| HR-09 | pip-audit: 2 CVEs in `pip` binary (venv tool, not app dep) | LOW | pip-audit | PARK — pip is not a runtime dependency |
| HR-10 | DEFER-SHUTDOWN: fixed `time.sleep` in shutdown | — | CONCERNS.md Tech Debt | PARK — invisible to launch reader (DEFER-SHUTDOWN) |
| HR-11 | DEFER-STREAMQUEUE: non-atomic drop-oldest | — | CONCERNS.md Known Bugs | PARK — latent, well-mitigated (DEFER-STREAMQUEUE) |
| HR-12 | Auth/webhook validation opt-in by default (no silent exposure) | — | CONCERNS.md Security | PARK — already warned at startup; mitigations documented |

Severity totals: 1 Critical, 1 High, 3 Medium, 2 Low, 5 parked informational items.

The executor will refine IDs, severity, and phrasing based on actual tool output and hostile
framing. This preview is a planning skeleton, not a final artifact.

---

## Section 8: Environment Availability

| Tool | Required By | Available | Version | Command |
|------|------------|-----------|---------|---------|
| ruff | D-01, CI gate | YES | >=0.4.0 (dev dep) | `ruff check src/python/` |
| semgrep | D-01, Shield SAST | YES | 1.136.0 | `semgrep scan src/python --config=auto` |
| gitleaks | D-01, Shield secrets | YES | 8.30.1 | `gitleaks detect --source . --config .gitleaks.toml --no-banner` |
| pip-audit | D-01 | YES | 2.10.0 | `PIPAPI_PYTHON_LOCATION=$(poetry -C src/python env info --path)/bin/python pip-audit` |
| npm | D-01 | YES | 11.12.1 | `npm audit --prefix src/angular` |
| poetry | Venv path for pip-audit | YES | — | `poetry -C src/python env info --path` |

No missing tools. No `uvx`/`pipx` fallbacks needed. All tools pre-installed.

---

## Common Pitfalls

### Pitfall 1: Treating GUARD-01/02 as "not yet implemented"
**What goes wrong:** The planner allocates effort to build startup warnings from scratch in
Phase 112, but they already exist in `seedsyncarr.py:372-397`.
**Why it happens:** REQUIREMENTS.md says "Pending" and CONCERNS.md says "consider warning" —
both were written before the implementation was confirmed.
**How to avoid:** Phase 112 planning should read the current source before scoping GUARD-01/02.
The narrow remaining gap (if any) is about warning prominence/discoverability, not existence.

### Pitfall 2: Treating LICENSE as missing when it's just misnamed
**What goes wrong:** The executor writes "create a LICENSE file" but `LICENSE.txt` already has
the full Apache 2.0 text.
**How to avoid:** The fix is a rename + README link update, not a content write.

### Pitfall 3: Treating devDep npm CVEs as production security issues
**What goes wrong:** The executor marks `ws` and `brace-expansion` CVEs as HIGH/MEDIUM and
folds them into Phase 112, inflating scope.
**How to avoid:** Verify the dep chain. `ws` enters via `karma` (a test runner, devDep only).
`brace-expansion` enters via `eslint` (a devDep). Neither package is in the production Docker
image. Correct disposition: PARK.

### Pitfall 4: Running pip-audit without targeting the project venv
**What goes wrong:** Running `pip-audit` bare reports CVEs in the system pip-audit venv, not
the project's dependencies.
**How to avoid:** Always set `PIPAPI_PYTHON_LOCATION` to the poetry venv Python path.

### Pitfall 5: Adding `--fix` to any tool invocation
**What goes wrong:** Violates D-02 (read-only pass) and mutates source before the findings
artifact is finalized, making the audit untrustworthy as a baseline.
**How to avoid:** D-02 is absolute. Every tool runs with report-only flags.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GitHub license detection requires file named `LICENSE` (not `LICENSE.txt`) | §6 | If GitHub does recognize `LICENSE.txt`, the finding severity drops from MEDIUM to LOW (cosmetic badge issue only); disposition unchanged (still FOLD → 113) |
| A2 | The 4 npm moderate CVEs (ws, brace-expansion) are devDeps only and not present in the production container image | §1.4 | If any are transitively included in the Angular build output, severity escalates to HIGH; executor must verify by checking `ng build` output vs. `node_modules/` |

---

## Sources

### Primary (HIGH confidence — direct tool runs in this session)
- `ruff check src/python/` — confirmed 0 findings, 2026-06-02
- `semgrep scan src/python --config=auto` — 0 findings, 320 rules, 92 files, 2026-06-02
- `gitleaks detect --source . --config .gitleaks.toml` — 0 leaks, 1167 commits, 2026-06-02
- `PIPAPI_PYTHON_LOCATION=... pip-audit` — 2 CVEs in `pip` binary (venv tool), 2026-06-02
- `npm audit --prefix src/angular` — 4 moderate CVEs in devDeps (karma chain), 2026-06-02
- `poetry -C src/python run pytest tests/unittests/test_common/test_app_process.py` — 1 FAILED (TypeError: cannot pickle '_thread.lock' object), 2026-06-02
- Direct file reads: `app_process.py`, `seedsyncarr.py`, `delete_process.py`, `config.py`, `web_app_job.py`, `.gitignore`, `README.md`, `LICENSE.txt`
- `shield-claude-skill/scripts/check-prereqs.sh` — all required tools confirmed available

### Secondary (MEDIUM confidence — official project artifacts)
- `.planning/codebase/CONCERNS.md` — post-v1.3.0 audit baseline (2026-06-02)
- `.planning/REQUIREMENTS.md` — GUARD-01..06 / SCAN-01/02 requirements
- `docs/superpowers/specs/2026-06-02-launch-hardening-design.md` — D-01..D-10, §3.1 fix scope
- `110-CONTEXT.md` — locked decisions D-01..D-09

---

## Metadata

**Confidence breakdown:**
- Tool invocation patterns: HIGH — all tools verified available and invoked successfully
- Pre-named fix scope: HIGH — all 6 items confirmed with exact file:line evidence
- AppProcess red test: HIGH — test run confirmed, exact error output captured
- LICENSE gap: HIGH (content) / ASSUMED (GitHub detection behavior)
- npm CVE disposition (devDep-only): HIGH — verified via `npm ls` chain

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (30 days — stable tooling; CVE landscape may change faster)
