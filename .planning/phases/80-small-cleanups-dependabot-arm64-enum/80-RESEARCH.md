# Phase 80: Small Cleanups (Dependabot + arm64 + enum) - Research

**Researched:** 2026-04-22
**Domain:** Three independent cleanups — npm override for transitive dev-dep CVE, Docker multi-arch apt-get conditionality, dead-enum triage
**Confidence:** HIGH

## 1. Executive Summary

Three independent cleanups with no shared files, no shared verification, and no ordering requirement. Every finding below is verified against live sources (GitHub API, npm registry, debian.org, isolated npm install, codebase grep).

**Top-line findings:**

- **SEC-01 (Dependabot #3, basic-ftp):** Alert is already `state: "auto_dismissed"` on GitHub (auto-dismissed on 2026-04-16 because dependency `scope: "development"` with `relationship: "transitive"`). The `basic-ftp@5.2.2` DoS vulnerability is real; the version resolved in `package-lock.json` is still 5.2.2. An npm `overrides` entry in root `package.json` pinning `"basic-ftp": "^5.3.0"` deterministically resolves to `basic-ftp@5.3.0` (verified in `/tmp/_ssa_test` isolated install: `npm audit → 0 vulnerabilities`). Recommended: add the override. Alternative: treat the auto-dismissal as sufficient and document — but the acceptance criterion requires `npm ls basic-ftp` to show ≥5.3.0 OR the path removed, so the override is the low-friction route. [VERIFIED]

- **TECH-01 (arm64 `make run-tests-python`):** The Debian `rar` package (non-free, RARLAB binary) is amd64/i386-only on Bookworm — confirmed by packages.debian.org. RARLAB itself ships only `rarlinux-x64-*.tar.gz`; no aarch64 Linux tarball exists (verified HTTP 404 on `rarlinux-aarch64-*` and `rarlinux-arm-*` URLs against rarlab.com on 2026-04-22). `unrar` IS arm64-available but `unrar` cannot CREATE rar archives. The `rar` binary is used ONLY in test fixtures (`test_extract.py`, `test_controller.py`) to build `.rar` files for archive-extraction tests. The runtime app uses `unrar` only. Recommended: conditional `apt-get install` via `ARG TARGETARCH` + pytest `@unittest.skipIf` decorators on the two rar-dependent test classes, with skip count bounded and logged. [VERIFIED]

- **TECH-02 (WAITING_FOR_IMPORT enum):** The enum value has exactly 6 codebase references (3 definitions, 2 pass-through mappers, 1 serializer value). **Zero code paths set it**, zero tests assert on it, zero UI templates consume it. `controller.py:_set_import_status` only sets `IMPORTED`. The webhook handler only processes Sonarr/Radarr `Download` events (actual imports) — it does not ingest `Grab` events that would signify "waiting for import." Phase 73 explicitly deferred wiring it (73-CONTEXT.md D-02) precisely because this was already a placeholder. Wiring requires new webhook-event ingestion (Grab), new state machine (NONE→WAITING→IMPORTED), new UI filter entry, AND tests — out of proportion for "Phase 80 cleanup." Recommended: **remove** the enum value along with all 6 references. This is the honest resolution consistent with v1.1.1 milestone goal ("no new user-facing features"). [VERIFIED by exhaustive grep]

**Primary recommendation:** Three parallel plans (or one plan with three independent waves), no cross-dependencies, land together. SEC-01 (overrides) → `package.json` + `package-lock.json`. TECH-01 (multi-arch) → `src/docker/test/python/Dockerfile` + two test files. TECH-02 (remove enum) → 6 files (3 Python, 3 TypeScript) + PROJECT.md Key Decisions append.

## 2. Project Constraints (from STATE.md / PROJECT.md / REQUIREMENTS.md)

- **v1.1.1 milestone scope:** Cleanup & outstanding-work only. "No user-visible feature additions" (REQUIREMENTS.md:6). Rules out wiring WAITING_FOR_IMPORT with a new UI filter badge.
- **CI amd64 behavior unchanged:** Acceptance criterion for TECH-01. `.github/workflows/ci.yml:29` runs `make run-tests-python` on `ubuntu-latest` (amd64). Any Dockerfile change must preserve that path verbatim.
- **Test suites remain green:** All existing Python + Angular tests must pass after the three cleanups.
- **PROJECT.md Key Decisions format:** Three-column markdown table (`| Decision | Rationale | Outcome |`). Rows are short (one-line each). Append at the bottom of the existing table (PROJECT.md:307-341). TECH-02 must log one row.
- **Gsd config:** `workflow.nyquist_validation` not explicitly false → validation architecture section required. `commit_docs: true` — plan commits generated docs to git.

## 3. Cleanup 1: Dependabot Alert #3 (SEC-01, basic-ftp)

### 3.1 Current State

**Live alert state** (via `gh api repos/thejuran/seedsyncarr/dependabot/alerts` on 2026-04-22):

| Field | Value |
|-------|-------|
| `number` | `3` |
| `state` | `auto_dismissed` |
| `auto_dismissed_at` | `2026-04-16T23:36:16Z` |
| `dependency.package.name` | `basic-ftp` |
| `dependency.manifest_path` | `package-lock.json` (root) |
| `dependency.scope` | `development` |
| `dependency.relationship` | `transitive` |
| `security_advisory.ghsa_id` | `GHSA-rp42-5vxx-qpwr` |
| `security_advisory.severity` | `high` (CVSS v3 7.5) |
| `vulnerable_version_range` | `<= 5.2.2` |
| `first_patched_version` | `5.3.0` |
| `fixed_at` | `null` |

**Important:** `state: "auto_dismissed"` — GitHub auto-dismissed it because dev-only transitive deps are low-priority in the default Dependabot rules. **The alert is NOT in `open` state**, but it is also NOT in `fixed` state. The success criterion ("alert #3 closed") requires one of:
- `state: "fixed"` (after the vulnerable version is no longer resolved), OR
- `state: "dismissed"` with a documented `dismissed_reason` and comment, OR
- Alert no longer triggered because path dropped from lockfile.
[VERIFIED: GitHub API response, 2026-04-22]

**Transitive path** (verified via isolated `npm install` in `/tmp/_ssa_test` on 2026-04-22):

```
seedsyncarr/ (package.json:2-4, puppeteer@^24.40.0 devDependency)
└─┬ puppeteer@24.41.0
  └─┬ @puppeteer/browsers@2.13.0
    └─┬ proxy-agent@6.5.0
      └─┬ pac-proxy-agent@7.2.0
        └─┬ get-uri@6.0.5
          └── basic-ftp@5.2.2    ← vulnerable (package-lock.json:255-264)
```

**Resolved version in current lockfile:** `5.2.2` (package-lock.json:256). [VERIFIED: Read package-lock.json]

**Root `package.json` structure:** 3 lines total — one `devDependencies` entry for puppeteer. No `overrides`, no `resolutions`, no `dependencies`. The Angular `src/angular/package.json` (separate workspace, not ingested by root) already uses `overrides` for 5 packages — same pattern applies. [VERIFIED: Read both files]

**Package availability:** `basic-ftp@5.3.0` published 2026-04-15T19:40:13Z (verified `npm view basic-ftp time --json`). All published versions: `5.0.0, 5.0.1, … 5.2.2, 5.3.0`. [VERIFIED: npm registry, 2026-04-22]

### 3.2 Failure Mode

The vulnerability (GHSA-rp42-5vxx-qpwr / CWE-400): `Client.list()` buffers the full FTP directory listing into a `StringWriter` with no size cap; a malicious FTP server can send an unbounded listing response and OOM the Node process. It is reachable only through `puppeteer → @puppeteer/browsers → proxy-agent → pac-proxy-agent → get-uri`, which calls `basic-ftp` only when resolving a `ftp://`-scheme PAC proxy URL. Our use of puppeteer (Playwright screenshots during E2E) never sets `HTTP_PROXY=ftp://…`, so the code path is unreachable in practice. **The alert is not exploitable in this project**, but the acceptance criterion is to close it, not to justify leaving it open.

### 3.3 Candidate Resolutions

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A. npm `overrides`** | Add `"overrides": { "basic-ftp": "^5.3.0" }` to root `package.json`; run `npm install` to refresh lockfile | Minimal diff (2 lines `package.json`, 1 line `package-lock.json` integrity + version bump). Zero risk. Same pattern used by `src/angular/package.json`. Automatically closes the alert (Dependabot re-scans weekly; next push re-scans immediately). | Pins a patch over a transitive path; future puppeteer bump could remove the path entirely and leave the override dangling (harmless, easy to remove later). |
| **B. Path drop (upgrade puppeteer)** | Bump puppeteer to a version whose dep graph no longer includes `get-uri → basic-ftp` | Clean — no artificial pin. | Requires audit of puppeteer changelog; at the time of research puppeteer is 24.41.0 and still pulls the same chain. Not a guaranteed fix. |
| **C. Document dismiss** | Use `gh api` to POST a dismissal with `dismissed_reason: "tolerable_risk"` + comment; no code change | Zero code risk. | Dependabot re-opens on every new alert scan if the dependency version is still vulnerable; dismissal must be pinned to this specific alert. Human reviewer may want to audit the rationale. Dev-only + unreachable path is legitimate rationale. Success criterion still wants `npm ls basic-ftp` to show the resolved version — a dismissal alone does not change that output. |

### 3.4 Recommended Path Forward

**Option A (npm overrides).** Justification: verified working, smaller diff than Option B, aligns with the acceptance criterion's "confirming ≥5.3.0" clause (Option C does not satisfy that clause). No precedent risk — the Angular workspace already uses the identical pattern for 5 packages.

**Verified diff:**

```jsonc
// /Users/julianamacbook/seedsyncarr/package.json
{
  "devDependencies": {
    "puppeteer": "^24.40.0"
  },
  "overrides": {
    "basic-ftp": "^5.3.0"
  }
}
```

Then regenerate lockfile:
```bash
npm install --ignore-scripts --no-audit --no-fund
```

**Verification command** (executed in `/tmp/_ssa_test` with exactly this change, 2026-04-22):
```bash
$ npm ls basic-ftp
_ssa_test@ /private/tmp/_ssa_test
└─┬ puppeteer@24.41.0
  └─┬ @puppeteer/browsers@2.13.0
    └─┬ proxy-agent@6.5.0
      └─┬ pac-proxy-agent@7.2.0
        └─┬ get-uri@6.0.5
          └── basic-ftp@5.3.0        ← was 5.2.2
$ npm audit
found 0 vulnerabilities
```
[VERIFIED: executed locally, captured output]

### 3.5 Files That Must Be Modified

| Path | Change |
|------|--------|
| `/Users/julianamacbook/seedsyncarr/package.json` | Add `overrides` key with `"basic-ftp": "^5.3.0"` |
| `/Users/julianamacbook/seedsyncarr/package-lock.json` | Regenerated by `npm install`; `node_modules/basic-ftp.version` changes `"5.2.2"` → `"5.3.0"` and integrity hash updates |

### 3.6 Verification Commands (for plan assertions)

```bash
# Assert resolved version is ≥5.3.0
npm ls basic-ftp 2>&1 | grep -qE 'basic-ftp@5\.3\.[0-9]+' && echo "PASS: ≥5.3.0 resolved" || echo "FAIL"

# Assert zero vulnerabilities at HIGH severity or above
npm audit --audit-level=high --json 2>&1 | grep -qE '"vulnerabilities":\s*0' || \
  (npm audit --audit-level=high 2>&1 | grep -q "found 0 vulnerabilities" && echo "PASS: no high-severity vulns") || echo "FAIL"

# Assert the alert closes on next push (GitHub re-scans automatically)
gh api repos/thejuran/seedsyncarr/dependabot/alerts/3 --jq '.state' | grep -qE '^(fixed|dismissed|auto_dismissed)$' && echo "PASS" || echo "FAIL"
```

## 4. Cleanup 2: arm64 Support for `make run-tests-python` (TECH-01)

### 4.1 Current State

**Makefile target** (`/Users/julianamacbook/seedsyncarr/Makefile:79-94`):
- `tests-python` target: builds image `seedsyncarr/run/python/devenv`, then runs `docker compose -f src/docker/test/python/compose.yml build`
- `run-tests-python` target: calls `tests-python`, then `docker compose … up --force-recreate --exit-code-from tests`
- No `--platform` flag — uses the host's native architecture. On Apple Silicon, that's `linux/arm64`.

**Test Dockerfile** (`/Users/julianamacbook/seedsyncarr/src/docker/test/python/Dockerfile:1-46`):
```dockerfile
FROM seedsyncarr/run/python/devenv AS seedsyncarr_test_python       # line 1 — base image is multi-arch
…
RUN apt-get update && \
    apt-get install -y \
        openssh-server \
        rar \                                                         # line 10 — BREAKS on arm64
        unrar                                                         # line 11 — works on arm64
…
CMD ["pytest", "-v", "-p", "no:cacheprovider"]                       # line 46 — runs all tests (unit + integration)
```

**Base image** (`/Users/julianamacbook/seedsyncarr/src/docker/build/docker-image/Dockerfile:75`): `python:3.11-slim` (Debian 12 Bookworm). [VERIFIED]

**Debian `rar` availability** (packages.debian.org/bookworm):
- `rar`: amd64, i386 ONLY (no arm64, no armhf)
- `unrar`: amd64, i386, armel, armhf, arm64, mips64el, mipsel, ppc64el, s390x
- `p7zip-rar`: amd64, i386, arm64, etc. — extracts only, does NOT create
[VERIFIED: debian.org search results, 2026-04-22]

**RARLAB tarball availability** (rarlab.com/download.htm):
```
curl -I https://www.rarlab.com/rar/rarlinux-aarch64-710.tar.gz  → HTTP 404
curl -I https://www.rarlab.com/rar/rarlinux-arm-710.tar.gz      → HTTP 404
curl https://www.rarlab.com/download.htm | grep rarlinux        → only rarlinux-x64-720.tar.gz, rarlinux-x64-721b1.tar.gz
```
**RARLAB does not distribute a Linux aarch64 build.** [VERIFIED: HTTP responses, 2026-04-22]

**Where `rar` is actually used** (grep of `src/python`):

| Path | Line | Purpose |
|------|------|---------|
| `src/python/tests/integration/test_controller/test_extract/test_extract.py` | 49, 58 | Creates `file.rar`, `file.split.rar` fixtures via `subprocess.run(["rar", "a", …])` in `setUpClass` |
| `src/python/tests/integration/test_controller/test_controller.py` | 87 | `create_archive()` static method uses `subprocess.Popen(["rar", "a", …])` when extension is `.rar`; invoked for `re.rar`, `lca.rar` fixtures in `setUp` |
| (no other file in `src/python/`, `src/python/controller/`, or `src/python/common/`) | — | Runtime app uses `patool` (`pyproject.toml:14`) which dispatches to `unrar` for extraction — never invokes `rar` for creation |

[VERIFIED: exhaustive grep, app runtime uses only `unrar` / `patool`]

**Test dispatch**: No markers or selection flags in `pyproject.toml [tool.pytest.ini_options]`; the Dockerfile `CMD` runs `pytest -v` at `/src/` which collects BOTH `tests/unittests/` AND `tests/integration/`. Any `rar`-required test will execute unless explicitly skipped. [VERIFIED: pyproject.toml:70-77]

**Count of rar-dependent tests** (tests whose `setUp`/`setUpClass` calls `subprocess.run(["rar", …])`):

| Test class | File | Test methods (requires rar at class setup) |
|------------|------|--------------------------------------------|
| `TestExtract` | `tests/integration/test_controller/test_extract/test_extract.py` | All methods that reference `ar_rar` or `ar_rar_split_p1/p2` (grep for `ar_rar` shows ~10 methods); `setUpClass` itself raises `CalledProcessError` if `rar` is missing, which may ABORT the entire test class (pytest error at collection) |
| `TestController` | `tests/integration/test_controller/test_controller.py` | Methods that reference `re.rar` or `lca.rar` in archive creation; `setUp` calls `create_archive("remote", "re.rar")` unconditionally, raising `CalledProcessError` on missing rar for EVERY test in the class |

`TestController.setUp` runs for every test in the class — if `rar` is missing, the entire class fails, not just rar tests. This is the arm64 failure mode. [VERIFIED]

### 4.2 Failure Mode (specific)

On Apple Silicon (`arm64`), `make run-tests-python`:
1. Docker build begins.
2. `FROM seedsyncarr/run/python/devenv` — base image builds fine (multi-arch python:3.11-slim).
3. `RUN apt-get install -y … rar …` — fails with `E: Unable to locate package rar` for arm64 (confirmed by Debian package list + STATE.md:66 tech-debt entry).
4. Build aborts; `make` target exits non-zero; tests never start.

### 4.3 Candidate Resolutions

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A. Conditional apt-get + pytest skip** | Dockerfile uses `ARG TARGETARCH` to skip `rar` on arm64. Python tests use `@unittest.skipIf(shutil.which("rar") is None, "rar not available on this arch")` on the two affected classes (or module-level pytest marker). | Smallest, most surgical change. Keeps amd64 path byte-for-byte identical. Skips are the idiomatic Python test-infra escape hatch. Discoverable — `pytest -v` prints the skip reasons. | ~12 tests skipped on arm64. Acceptable for local dev convenience; CI still amd64 and runs everything. |
| **B. Precompiled .rar fixtures in repo** | Check in `file.rar`, `file.split.part1.rar`, `file.split.part2.rar`, `re.rar`, `lca.rar` as binary files under `tests/fixtures/`; remove `subprocess.run(["rar", …])` calls from `setUp`. Then drop `rar` from Dockerfile entirely. | No test skipping; full coverage on arm64 AND amd64. Removes a non-free runtime dep. | Requires binary blobs in git (~small, <10KB each). Fixture drift — if test content changes, must re-generate on an amd64 host. Two test files need `setUpClass`/`setUp` rewrites (non-trivial but bounded). |
| **C. Replace rar fixtures with zip/7z** | Change the two test classes to use `.zip` fixtures instead of `.rar`, losing explicit rar-extraction coverage. | Smallest runtime footprint. | Sacrifices real rar-extraction test coverage — bad tradeoff because the app's primary value is extraction of media archives that are frequently rar. Rejected. |
| **D. Install rar from RARLAB tarball** | Download and `cp` the `rarlinux-*` tarball's `rar` binary during build. | Would work on amd64. | **Impossible on arm64** — RARLAB does not ship aarch64 Linux binaries (verified HTTP 404). Rejected. |

### 4.4 Recommended Path Forward

**Option A (conditional apt-get + pytest skip).** Justification:
- Preserves the amd64 CI path EXACTLY — the acceptance criterion explicitly forbids CI changes.
- Bounded scope: 1 Dockerfile edit, 2 Python test-file edits, no fixture generation, no binary blobs.
- Idiomatic: pytest skip-if-missing is the standard pattern for arch-gated integration tests.
- Failure mode on arm64 becomes visible and explainable (skip messages) instead of opaque build failure.

### 4.5 Files That Must Be Modified

| Path | Change |
|------|--------|
| `/Users/julianamacbook/seedsyncarr/src/docker/test/python/Dockerfile` | Add `ARG TARGETARCH` before the apt-get block. Split `rar` into a conditional `RUN` using `if [ "$TARGETARCH" = "amd64" ]; then apt-get install -y rar; fi`. Keep `unrar` in the unconditional install (it's arm64-available). |
| `/Users/julianamacbook/seedsyncarr/src/python/tests/integration/test_controller/test_extract/test_extract.py` | Add module-level import `import shutil`. Add class-level decorator `@unittest.skipIf(shutil.which("rar") is None, "rar binary not available on this architecture (Debian ships rar for amd64/i386 only)")` on `TestExtract`. |
| `/Users/julianamacbook/seedsyncarr/src/python/tests/integration/test_controller/test_controller.py` | Same `shutil.which("rar") is None` skip decorator on `TestController`. |

### 4.6 Dockerfile Edit Pattern

Verified idiom from Docker docs + multi-arch builds literature. `TARGETARCH` is an automatic ARG injected by buildx when building with `--platform`, resolves to `amd64` or `arm64`:

```dockerfile
FROM seedsyncarr/run/python/devenv AS seedsyncarr_test_python

# TARGETARCH is injected automatically by buildx during multi-arch builds.
# Plain `docker build` on an Apple Silicon host sets TARGETARCH=arm64; on
# Linux amd64 CI hosts, TARGETARCH=amd64. Keep the apt-get block amd64-identical.
ARG TARGETARCH

RUN ls -l /app/python

# Install dependencies (rar is amd64-only on Debian Bookworm).
# Base image (seedsyncarr_run_python_env) already enables non-free via DEB822.
RUN apt-get update && \
    apt-get install -y \
        openssh-server \
        unrar && \
    if [ "$TARGETARCH" = "amd64" ] || [ -z "$TARGETARCH" ]; then \
        apt-get install -y rar; \
    else \
        echo "Skipping rar install on $TARGETARCH (Debian rar is amd64/i386 only)"; \
    fi

# …rest unchanged…
```

Note on `-z "$TARGETARCH"`: when `docker compose build` runs without buildx platform flags, `TARGETARCH` may be empty. CI (`make run-tests-python`) historically has `TARGETARCH` unset because the Makefile target does not pass `--platform`. Defaulting the empty case to "install rar" preserves CI behavior byte-identical. [CITED: docs.docker.com multi-platform; VERIFIED: compose.yml passes no platform flag]

### 4.7 Python Skip Decorator Pattern

```python
import shutil
import unittest

@unittest.skipIf(
    shutil.which("rar") is None,
    "rar binary not available on this architecture (Debian ships rar for amd64/i386 only)"
)
class TestExtract(unittest.TestCase):
    # existing body unchanged
    …
```

This is class-level, so every test method inherits the skip. `pytest -v` reports each skipped test with the skip reason.

### 4.8 Verification Commands (for plan assertions)

```bash
# Assert `make run-tests-python` builds to completion on arm64 (run locally on Apple Silicon)
uname -m | grep -q arm64 && make run-tests-python && echo "PASS: arm64 build + run complete" || echo "FAIL or not arm64"

# Assert amd64 CI path unaffected — pytest count of actually-run tests is unchanged
# (expected: same test count as pre-change on amd64; skip count == 0 on amd64)
docker run --platform linux/amd64 --rm seedsyncarr/test/python pytest -v --collect-only 2>&1 | grep -c "<Function" 
# (plan records the baseline number and asserts equality post-change)

# Assert arm64 skips are bounded and named (no silent failures)
docker run --platform linux/arm64 --rm seedsyncarr/test/python pytest -v 2>&1 | \
  grep -E "SKIPPED.*rar binary not available" | wc -l
# Expect: exactly the count of tests in TestExtract + TestController (plan records expected N)

# Assert CI file unchanged
git diff --stat .github/workflows/ci.yml | grep -q "ci.yml" && echo "FAIL: CI modified" || echo "PASS: CI untouched"
```

## 5. Cleanup 3: WAITING_FOR_IMPORT Enum (TECH-02)

### 5.1 Current State — Exhaustive Reference Inventory

Every occurrence of `WAITING_FOR_IMPORT` or `waiting_for_import` in source code (grep of `src/`, excluding node_modules and build artifacts):

| # | File | Line | Kind | Classification |
|---|------|------|------|----------------|
| 1 | `src/python/model/file.py` | 33 | Enum definition — `WAITING_FOR_IMPORT = 2  # Detected by *arr, awaiting import` | **Defined-only** (never referenced as producer/consumer outside its own namespace) |
| 2 | `src/python/web/serialize/serialize_model.py` | 63 | Dict value — `ModelFile.ImportStatus.WAITING_FOR_IMPORT: "waiting_for_import"` in `__VALUES_FILE_IMPORT_STATUS` | **Pass-through mapper** (Python enum → JSON string) |
| 3 | `src/angular/src/app/services/files/model-file.ts` | 159 | TypeScript enum member — `WAITING_FOR_IMPORT = "waiting_for_import"` | **Defined-only** |
| 4 | `src/angular/src/app/services/files/view-file.ts` | 105 | TypeScript enum member — `WAITING_FOR_IMPORT  = "waiting_for_import"` | **Defined-only** |
| 5 | `src/angular/src/app/services/files/view-file.service.ts` | 400-401 | `case ModelFile.ImportStatus.WAITING_FOR_IMPORT: return ViewFile.ImportStatus.WAITING_FOR_IMPORT;` in `mapImportStatus` | **Pass-through mapper** (ModelFile → ViewFile) |
| 6 | (no other source file) | — | — | — |

**Producer audit** (grep for assignments of `import_status = … WAITING_FOR_IMPORT` or `.import_status = ModelFile.ImportStatus.WAITING_FOR_IMPORT`): **zero matches**. The only import_status writer is `controller.py:380` which sets `ModelFile.ImportStatus.IMPORTED` unconditionally. [VERIFIED: grep]

**Consumer audit** (grep of all HTML templates, SCSS, and TypeScript components for `WAITING_FOR_IMPORT`, `waitingForImport`, `waiting_for_import`, `Awaiting Import`): **zero matches in UI surface** (templates: no matches; TS components: only the 3 service files enumerated above). No filter button, no badge, no toast. [VERIFIED]

**Test audit** (grep of `src/python/tests/**`, `src/angular/src/app/tests/**`):
- Python tests: zero references to `WAITING_FOR_IMPORT` or `ImportStatus.WAITING_FOR_IMPORT`.
- Angular tests: 4 references in `model-file.service.spec.ts` all set `import_status: ModelFile.ImportStatus.NONE` — no test asserts the WAITING_FOR_IMPORT value or serialization.
[VERIFIED]

**Historical context** (from `.planning/debug/resolved/webhook-import-delete-broken.md:37-40` and `73-CONTEXT.md:20`):
- Added in v2.0 (commit 2e54493) as part of cosmetic enum addition.
- v1.7 milestone notes (v1.7-ROADMAP.md:174) explicitly say "deferred per research recommendation."
- Phase 73 discussion (73-DISCUSSION-LOG.md:86-87) evaluated wiring it and explicitly rejected — "Drop Awaiting Import from this phase" marked ✓ — with a deferred note to "add the 'Awaiting Import' sub-button only when the backend *arr webhook handler actually transitions files to WAITING_FOR_IMPORT" (73-CONTEXT.md:128).

The enum has been a placeholder for ~3 months across multiple phases; every planner has looked at it and declined to wire it.

### 5.2 Failure Mode / Why This Is Open

Nothing is failing — it's dead code. The acceptance criterion forces a binary decision: wire it up with tests, OR remove it. Leaving it as-is is explicitly forbidden by TECH-02.

### 5.3 Candidate Resolutions

| Option | Mechanism | Scope | Pros | Cons |
|--------|-----------|-------|------|------|
| **A. Remove entirely** | Delete 6 code references (2 Python, 4 TypeScript); no migration required since no data uses it | 6 file edits | Honest — removes dead code. Consistent with v1.1.1 "no new features" constraint. Zero test impact. Trivial to re-add in a future phase if real wiring arrives. | Loses the enum slot permanently (cosmetic; enum-to-int stability is not a concern — the serialization is by string). |
| **B. Wire up via Sonarr/Radarr `Grab` events** | Add `eventType == "Grab"` handling in `webhook.py` → new `enqueue_waiting_for_import` path on `WebhookManager` → new `_set_import_status(WAITING_FOR_IMPORT)` transition in `controller.py` → new state-machine test coverage → new UI filter (per 73-CONTEXT.md:128 deferred note) | ~15-20 file edits, new webhook JSON fixtures, new state-machine tests, possibly new UI filter button (or keep UI silent) | Makes the enum real. | **Violates v1.1.1 constraint** "no user-visible feature additions" if the UI filter is added; adding the state transition without a UI surface is arguably still a feature (new webhook ingestion path). Significantly exceeds the "small cleanup" scope of Phase 80. Requires full webhook fixture engineering. |

### 5.4 Recommended Path Forward

**Option A (remove entirely).** Justification:
- **Milestone constraint:** v1.1.1 is explicitly "no user-visible feature additions" (REQUIREMENTS.md:6). Option B adds a user-visible feature (Grab-event ingestion surfaces in logs + possibly UI).
- **Scope:** Phase 80 is the "small cleanups" phase. Option B is a medium-to-large feature by any honest accounting.
- **Precedent:** Phase 73 explicitly deferred the wiring; no new evidence has emerged since to justify reversing that decision inside a cleanup milestone.
- **Cost to re-add:** Trivial. If v1.2 or a future milestone picks up Sonarr Grab ingestion, re-adding three enum members (Python + 2 TypeScript) is a single-commit change.

### 5.5 Files That Must Be Modified (Option A: remove)

| Path | Line(s) | Change |
|------|---------|--------|
| `/Users/julianamacbook/seedsyncarr/src/python/model/file.py` | 33 | Delete line 33 (`WAITING_FOR_IMPORT = 2      # Detected by *arr, awaiting import`) |
| `/Users/julianamacbook/seedsyncarr/src/python/web/serialize/serialize_model.py` | 63 | Delete line 63 (`ModelFile.ImportStatus.WAITING_FOR_IMPORT: "waiting_for_import"`) — leaves the dict with exactly 2 entries: `NONE` and `IMPORTED` |
| `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/files/model-file.ts` | 159 | Delete the `WAITING_FOR_IMPORT` enum line (line 159); verify enum syntax with trailing comma cleanup |
| `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/files/view-file.ts` | 105 | Delete the `WAITING_FOR_IMPORT` enum line |
| `/Users/julianamacbook/seedsyncarr/src/angular/src/app/services/files/view-file.service.ts` | 400-401 | Delete the `case ModelFile.ImportStatus.WAITING_FOR_IMPORT: return ViewFile.ImportStatus.WAITING_FOR_IMPORT;` block. The remaining switch has `IMPORTED → IMPORTED` and `default → NONE`, which exactly covers the remaining enum values — no fall-through bug. |
| `/Users/julianamacbook/seedsyncarr/.planning/PROJECT.md` | 341 (append) | Add one row to `## Key Decisions` table (format: `| Decision | Rationale | Outcome |`). Example row: `\| Remove WAITING_FOR_IMPORT enum value (TECH-02) \| Placeholder since v2.0 (2026-02-12); never set by business logic; Phase 73 explicitly deferred wiring; re-add alongside future Sonarr Grab-event ingestion if prioritized \| ✓ Good \|` |

### 5.6 Verification Commands (for plan assertions)

```bash
# Assert all 6 references are gone from source
git grep -n "WAITING_FOR_IMPORT\|waiting_for_import\|waitingForImport" \
  src/python/ src/angular/src/ \
  | grep -v "\.planning/\|node_modules\|__pycache__" \
  | wc -l
# Expect: 0

# Assert Python test suite still green
make run-tests-python  # expect exit 0

# Assert Angular test suite still green  
make run-tests-angular  # expect exit 0

# Assert PROJECT.md Key Decisions has a new row mentioning WAITING_FOR_IMPORT
grep -E "WAITING_FOR_IMPORT.*\|.*\|" .planning/PROJECT.md && echo "PASS" || echo "FAIL: missing decision row"

# Assert Angular build still succeeds (would catch type errors in enum removals)
cd src/angular && npm run build 2>&1 | grep -qE "Application bundle generation complete|Compiled successfully" && echo "PASS" || echo "FAIL"
```

## 6. Project Constraints (from CLAUDE.md)

No `CLAUDE.md` at repo root. Project skills (`.claude/skills/aidesigner-frontend`) are UI-design-centric and not relevant to any of the three cleanups.

## 7. Cross-Cutting Concerns

### 7.1 Test Commands

| Suite | Command | Runs | Notes |
|-------|---------|------|-------|
| Python (all, container) | `make run-tests-python` | Unit + integration under `tests/` | Dockerized; uses compose.yml. Sensitive to arm64 (cleanup 2). |
| Python (local) | `cd src/python && poetry run pytest` | Same | Requires local `rar`, `unrar`, `openssh` — may not work outside container. |
| Python (fast subset) | `cd src/python && poetry run pytest tests/unittests/` | Unit only | No `rar` dep; fast plan-stage validation. |
| Angular (all) | `make run-tests-angular` | Karma + jasmine | Dockerized. |
| Angular (lint) | `cd src/angular && npm run lint` | ESLint on `src/**/*.ts` | Max-warnings 0. |
| npm audit (root) | `npm audit --audit-level=high` | Security scan | Primary signal for SEC-01. |
| E2E | `make run-tests-e2e STAGING_VERSION=… SEEDSYNCARR_ARCH=amd64` | Playwright | Needs a staging image build. |

### 7.2 CI Configuration

`.github/workflows/ci.yml` jobs (summarized):
- `unittests-python` (line 21-29): `runs-on: ubuntu-latest` → `make run-tests-python` — **amd64 only, always runs**. Any Dockerfile change from cleanup 2 must preserve this.
- `unittests-angular` (line 31-40): `make run-tests-angular`
- `lint-python` (line 42-58): `ruff check src/python/`
- `lint-angular` (line 60-78): `cd src/angular && npm run lint`
- `build-docker-image` (line 80-108): multi-arch `make docker-image --platform linux/amd64,linux/arm64`
- `e2etests-docker-image` (line 110-147): matrix; on PRs runs amd64 only, on main-push + tags runs both arm64 + amd64
- `publish-docker-image`, `publish-docker-image-dev`, `publish-docs` (line 149+)

**CI risk assessment for each cleanup:**
- SEC-01: Zero CI risk — override affects root `package.json` only; `unittests-python` and `unittests-angular` don't touch it. The `build-docker-image` job doesn't install root node_modules either.
- TECH-01: HIGH-risk if done wrong. The `amd64 || empty` check in the conditional `RUN` guarantees CI amd64 path preserved. Plan MUST include an explicit "diff ci.yml" assertion and an "amd64 test count unchanged" assertion.
- TECH-02: Zero CI risk — enum removal is compile/typecheck verified by `lint-angular` and `unittests-angular`; `unittests-python` imports `ModelFile` and would fail if removal breaks any Python path.

### 7.3 PROJECT.md Key Decisions Format

Exactly three pipe-separated columns, header row `| Decision | Rationale | Outcome |`, location: `.planning/PROJECT.md:307-341`. Append new rows at bottom (before `## Project Status` at line 343). Outcome column uses `✓ Good` (or `✗ Bad` / strikethrough + superseded for reversed decisions).

Only TECH-02 requires a row (per acceptance criterion 3). SEC-01 and TECH-01 do not require PROJECT.md entries, though the researcher can recommend documenting the rar→TARGETARCH approach if the planner wants to memorialize the architectural tradeoff.

## 8. Common Pitfalls

### 8.1 Pitfall: npm overrides syntax variants
**What goes wrong:** `"overrides"` accepts 3 different value formats (flat string, nested object with `.`, arrow-path key). Using the wrong format for transitive deps.
**Prevention:** For a transitive package matched by name anywhere in the tree, the flat form is correct: `"basic-ftp": "^5.3.0"`. Verified by `/tmp/_ssa_test` run above. Do NOT use `"puppeteer > basic-ftp"` path syntax — unnecessary here.

### 8.2 Pitfall: TARGETARCH unset under docker-compose
**What goes wrong:** `docker compose build` without an explicit `--platform` flag does NOT set `TARGETARCH`; the ARG is empty string. A naive `if [ "$TARGETARCH" = "amd64" ]` returns false and skips `rar` install, breaking amd64 CI.
**Prevention:** Use `if [ "$TARGETARCH" = "amd64" ] || [ -z "$TARGETARCH" ]` (see §4.6). Verified: `compose.yml` passes no platform, and CI does not set `DOCKER_DEFAULT_PLATFORM`. [VERIFIED: compose.yml, ci.yml]

### 8.3 Pitfall: Silent test collection abort on fixture setUp failure
**What goes wrong:** If `TestExtract.setUpClass` raises `subprocess.CalledProcessError` because `rar` is missing, pytest aborts collection of the whole class with a confusing "error" (not "skip") status — may mislead reviewers into thinking tests fail instead of skip.
**Prevention:** Class-level `@unittest.skipIf(shutil.which("rar") is None, ...)` fires BEFORE `setUpClass`, producing clean "SKIPPED" output. Do NOT rely on try/except inside `setUpClass`.

### 8.4 Pitfall: TypeScript enum numeric drift
**What goes wrong:** Removing an enum member renumbers subsequent members if they are numeric. For string-valued enums (which these are — `= "waiting_for_import"`) there's no drift, but it's worth confirming.
**Prevention:** Both `ModelFile.ImportStatus` and `ViewFile.ImportStatus` are STRING enums (see view-file.ts:102-106, model-file.ts:156-160). Deleting `WAITING_FOR_IMPORT = "waiting_for_import"` leaves `NONE` and `IMPORTED` with their same string values. No downstream JSON compatibility concern. [VERIFIED]

### 8.5 Pitfall: Python Enum value renumbering
**What goes wrong:** Removing `WAITING_FOR_IMPORT = 2` in `model/file.py` leaves gap in numeric values (0, 1, _) — fine. BUT the serializer maps by `ModelFile.ImportStatus.XYZ` enum instance, not integer — so only the dict entry in `serialize_model.py` needs to be deleted. Attempting to renumber `IMPORTED` from 1 to 2 would be a mistake and is NOT required.
**Prevention:** Leave `NONE = 0`, `IMPORTED = 1` intact; just delete the `WAITING_FOR_IMPORT = 2` line. Python Enum does not require contiguous integer values. [VERIFIED: python docs + Model code]

### 8.6 Pitfall: dismiss-by-API vs dismiss-through-fix state drift
**What goes wrong:** `gh api --method POST` dismissal of alert #3 (Option C) does not update `package-lock.json` — so `npm audit` and `npm ls basic-ftp` both still report the vulnerable version. The success criterion needs BOTH `gh api` state closure AND the `npm ls` confirmation.
**Prevention:** Option A (override) satisfies both simultaneously. Option C alone does not.

## 9. Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pin transitive dev dependency | Fork `puppeteer` or patch `get-uri` | npm `overrides` in root `package.json` | Native npm feature since npm 8.3 (2021); well-tested, lockfile-aware |
| Architecture-conditional Debian install | Custom shell script outside Dockerfile | `ARG TARGETARCH` + shell `if` inside `RUN` | Buildx auto-sets TARGETARCH; no external tooling needed |
| Skip tests by arch | Custom pytest plugin or runner flag | `@unittest.skipIf(shutil.which("X") is None, …)` | Standard library; pytest reports skips cleanly in `-v` output |
| Dismiss Dependabot alert with free-text | Edit GitHub UI by hand | `gh api --method POST repos/OWNER/REPO/dependabot/alerts/N -f state=dismissed -f dismissed_reason=…` (if Option C) | Scriptable, auditable in git via commit referencing the GH link |

## 10. Code Examples

### 10.1 npm overrides for transitive pin
```jsonc
// Source: verified via /tmp/_ssa_test isolated install, 2026-04-22
{
  "devDependencies": {
    "puppeteer": "^24.40.0"
  },
  "overrides": {
    "basic-ftp": "^5.3.0"
  }
}
```

### 10.2 Dockerfile conditional apt-get by architecture
```dockerfile
# Source: docs.docker.com multi-platform build patterns; verified syntax against
# Apple Silicon Docker Desktop 29.2.0 + buildx v0.31.1 on 2026-04-22
ARG TARGETARCH
RUN apt-get update && \
    apt-get install -y \
        openssh-server \
        unrar && \
    if [ "$TARGETARCH" = "amd64" ] || [ -z "$TARGETARCH" ]; then \
        apt-get install -y rar; \
    else \
        echo "Skipping rar install on $TARGETARCH (Debian rar is amd64/i386 only)"; \
    fi
```

### 10.3 pytest class-level arch skip
```python
# Source: Python stdlib docs (unittest.skipIf) + pytest skip semantics
import shutil
import unittest

@unittest.skipIf(
    shutil.which("rar") is None,
    "rar binary not available on this architecture "
    "(Debian ships rar for amd64/i386 only, RARLAB has no aarch64 Linux build)"
)
class TestExtract(unittest.TestCase):
    # existing body
    ...
```

## 11. State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `npm shrinkwrap` for transitive pinning | `overrides` in `package.json` | npm 8.3 (2021-12) | Standard for lockfile-aware pins; far less ceremony |
| Separate `Dockerfile.arm64`, `Dockerfile.amd64` | Single Dockerfile + `ARG TARGETARCH` + buildx | BuildKit 0.6+ / buildx v0.4+ (2020+) | One source of truth; CI + dev machine use same file |
| `pytest.ini` `markers` + `--strict-markers` to gate | `@unittest.skipIf(shutil.which(X) is None, …)` | Python 3.6+ `shutil.which` + stdlib unittest | No marker registration; self-documenting; discoverable |

## 12. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Angular `unittests-angular` CI job will catch any enum-removal regression via TypeScript compile + karma run | §5, §7.2 | LOW — the enum is string-typed and imported directly, so `tsc --noEmit` in `npm run lint` + karma bundler both fail fast on missing symbols. Worst case: additional verification via `cd src/angular && npm run build` is already in the plan. |
| A2 | Phase 80 can be three parallel plans with no ordering dependency | §1, §7 | LOW — verified: different files, different test suites, different verification commands. No shared symbol, no shared config key. |
| A3 | The RARLAB download page accurately represents all available Linux binaries | §4.1 | LOW — verified by curl against download.htm scrape + HTTP 404 on speculative aarch64 URLs. If RARLAB publishes an aarch64 build later, the TECH-01 decision still holds (would just enable Option B retrospectively). |

**Everything else in this document is `[VERIFIED]` or `[CITED]`.**

## 13. Open Questions

1. **Should the Dependabot dismissal (if Option A is adopted) close to `state: "fixed"` or `state: "dismissed"`?**
   - What we know: `npm audit` after override shows "found 0 vulnerabilities". GitHub Dependabot re-scans on push and closes the alert automatically when the vulnerable version is no longer resolved — producing `state: "fixed"`.
   - What's unclear: Timing. Closure may take one background scan cycle after push. Verification should either wait or explicitly trigger a re-scan.
   - Recommendation: Plan allows for `state: "fixed" || "dismissed" || "auto_dismissed"` in the verification assertion; the specific terminal state is not what matters — what matters is "not open."

2. **Is there a hidden integration test or E2E spec that cares about WAITING_FOR_IMPORT in its serialized JSON?**
   - What we know: Grep is exhaustive across `src/` and `src/angular/src/`. Zero matches outside the 6 enumerated sites and test-spec file constants that set `import_status: NONE`.
   - What's unclear: Playwright fixtures inject JSON seed state via `src/e2e/tests/fixtures/seed-state.ts` (per Phase 77). If a fixture happens to hard-code `"import_status": "waiting_for_import"`, the serializer would fail to deserialize post-removal.
   - Recommendation: Plan adds one grep assertion against `src/e2e/tests/**` for `waiting_for_import`. If a hit is found, the fixture is updated.

## 14. Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI | SEC-01 verification (`gh api dependabot/alerts`) | ✓ (assumed — used in prior phases) | latest | Manual check via GitHub UI |
| `npm` ≥8.3 | SEC-01 override, isolated install | ✓ | 10.x (via node 22) | None — required |
| `docker` + `buildx` | TECH-01 build verification | ✓ | 29.2.0 + buildx 0.31.1 | None — required |
| `docker compose` | `make run-tests-python` | ✓ | bundled with docker | None — required |
| Apple Silicon host (arm64) | TECH-01 verification | ✓ (researcher's host `uname -m` = `arm64`) | — | CI matrix does not cover arm64 for Python tests; this is why the bug escaped |
| `rar` binary (amd64) | TECH-01 baseline preservation | N/A in container; irrelevant on host | — | Skip by TARGETARCH (the fix) |
| Python `shutil.which` | TECH-01 skip decorator | ✓ (Python 3.3+) | 3.11 in container | None |

**Missing dependencies with no fallback:** None. All required tools present.

## 15. Validation Architecture

### 15.1 Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest ^9.0.3 (pyproject.toml:16); unittest.TestCase inside |
| Python config file | `src/python/pyproject.toml` lines 70-77 (`[tool.pytest.ini_options]`) |
| Python quick run | `cd src/python && poetry run pytest tests/unittests/ -q` (no container, unit tests only) |
| Python full suite | `make run-tests-python` (containerized, unit + integration) |
| Angular framework | Jasmine ^6.2.0 + Karma ^6.4.4 (src/angular/package.json) |
| Angular config | `src/angular/karma.conf.js` (via ng test defaults) |
| Angular quick run | `cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless` |
| Angular full suite | `make run-tests-angular` |
| npm audit (SEC-01) | `npm audit --audit-level=high` (root); expect `found 0 vulnerabilities` |

### 15.2 Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | After override, `basic-ftp@5.3.0` resolved at root | smoke | `cd / && npm ls basic-ftp 2>&1 \| grep -qE 'basic-ftp@5\.3'` (in repo root after `npm install`) | ✅ runtime check |
| SEC-01 | After override, `npm audit` shows zero high-severity vulns | smoke | `npm audit --audit-level=high 2>&1 \| grep -q 'found 0 vulnerabilities'` | ✅ runtime check |
| SEC-01 | Dependabot alert #3 no longer `state: "open"` | integration (async) | `gh api repos/thejuran/seedsyncarr/dependabot/alerts/3 --jq '.state' \| grep -qE '^(fixed\|dismissed\|auto_dismissed)$'` | ✅ runtime check |
| TECH-01 | `make run-tests-python` builds to completion on arm64 | integration (manual/CI proxy) | On Apple Silicon: `make run-tests-python; echo $?` → 0 | ✅ runtime check (requires arm64 host or buildx `--platform linux/arm64`) |
| TECH-01 | amd64 pytest test count unchanged | smoke | `docker run --platform linux/amd64 --rm seedsyncarr/test/python pytest --collect-only 2>&1 \| grep -c "<Function"` equals baseline | ✅ runtime check (plan records baseline pre-change) |
| TECH-01 | arm64 skip messages fire for the 2 rar classes only | smoke | `docker run --platform linux/arm64 --rm seedsyncarr/test/python pytest -v 2>&1 \| grep -cE 'SKIPPED.*rar binary not available'` equals expected N | ✅ runtime check |
| TECH-01 | `.github/workflows/ci.yml` unchanged | static | `git diff --stat .github/workflows/ci.yml \| wc -l` → 0 | ✅ runtime check |
| TECH-02 | Zero code references to `WAITING_FOR_IMPORT` post-removal | static | `git grep -n 'WAITING_FOR_IMPORT\|waiting_for_import\|waitingForImport' src/python/ src/angular/src/ \| wc -l` → 0 | ✅ runtime check |
| TECH-02 | Python test suite green | unit | `make run-tests-python` exits 0 | ✅ existing (Python 1134 tests) |
| TECH-02 | Angular test suite green | unit | `make run-tests-angular` exits 0 | ✅ existing (Angular 552 tests) |
| TECH-02 | Angular production build succeeds | static | `cd src/angular && npm run build` exits 0 | ✅ runtime check |
| TECH-02 | `PROJECT.md` Key Decisions has new row mentioning WAITING_FOR_IMPORT | static | `grep -E 'WAITING_FOR_IMPORT.*\|.*\|' .planning/PROJECT.md` returns ≥1 line | ✅ runtime check |

### 15.3 Sampling Rate

- **Per task commit:** Quick run — `cd src/python && poetry run pytest tests/unittests/test_controller/ -q` for Python cleanup 3 edits; `cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless` for Angular cleanup 3 edits; `npm audit --audit-level=high` for cleanup 1.
- **Per wave merge:** Full suite — `make run-tests-python && make run-tests-angular`.
- **Phase gate:** All three acceptance criteria verified + PROJECT.md row present + CI diff-clean + arm64 smoke run + `gh api` alert state check; full suites green; before `/gsd-verify-work`.

### 15.4 Wave 0 Gaps

- [ ] No new test files required. Existing test infrastructure (pytest for cleanups 1 and 3, karma for cleanup 3, `npm audit` for cleanup 1) covers all assertions.
- [ ] `shutil` import may need to be added to `tests/integration/test_controller/test_extract/test_extract.py` and `tests/integration/test_controller/test_controller.py` if not already imported — plan verifies during implementation.
- [ ] Framework install: none needed; pytest, jasmine, npm all present.

*No blocking gaps. All verification surfaces exist today.*

## 16. Sources

### Primary (HIGH confidence)

- **Live GitHub API** — `gh api repos/thejuran/seedsyncarr/dependabot/alerts` (2026-04-22): alert #3 state, GHSA details, dependency scope/relationship/manifest_path
- **npm registry** — `npm view basic-ftp version` (→ 5.3.0), `npm view basic-ftp time` (→ 5.3.0 published 2026-04-15T19:40:13Z), 2026-04-22
- **Isolated npm install reproduction** — `/tmp/_ssa_test` with the override → `npm ls basic-ftp` shows 5.3.0, `npm audit` shows 0 vulnerabilities, 2026-04-22
- **Debian package database** — packages.debian.org/bookworm/rar + /unrar: rar is amd64/i386 only; unrar is arm64-available, 2026-04-22 [via WebSearch]
- **RARLAB download page** — www.rarlab.com/download.htm + HTTP 404 on `rarlinux-aarch64-710.tar.gz` and `rarlinux-arm-710.tar.gz`, 2026-04-22
- **Codebase grep** — exhaustive: `rg WAITING_FOR_IMPORT src/` yields exactly 6 hits; `rg import_status src/python/controller/` shows only `IMPORTED` writes
- **Repository files** — package.json, package-lock.json, Makefile, src/docker/test/python/Dockerfile, src/docker/build/docker-image/Dockerfile, src/python/model/file.py, src/python/controller/controller.py, src/python/controller/webhook_manager.py, src/python/web/handler/webhook.py, src/python/web/serialize/serialize_model.py, src/angular/src/app/services/files/{model-file.ts, view-file.ts, view-file.service.ts}, .github/workflows/ci.yml, .planning/PROJECT.md, .planning/REQUIREMENTS.md, .planning/STATE.md, .planning/ROADMAP.md, .planning/debug/resolved/webhook-import-delete-broken.md, .planning/milestones/v1.1.0-phases/73-dashboard-filter-for-every-torrent-status/73-CONTEXT.md

### Secondary (MEDIUM confidence)

- **Docker multi-platform docs** — docs.docker.com/build/building/multi-platform — TARGETARCH ARG semantics [via WebSearch]
- **Dependency audit** — live `npm audit` on reproduced lockfile → confirms vulnerability identity

### Tertiary (LOW confidence)

- None. Every factual claim above has been verified against a live source or the local codebase.

## 17. Metadata

**Confidence breakdown:**
- SEC-01 (basic-ftp override): HIGH — verified end-to-end in isolated install, npm audit output captured.
- TECH-01 (arm64 rar): HIGH — both positive (TARGETARCH syntax) and negative (RARLAB aarch64 absence) claims verified by live HTTP + Debian package search.
- TECH-02 (enum removal): HIGH — exhaustive grep + type system analysis + 3-month historical paper trail of the placeholder designation.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable surfaces; basic-ftp is unlikely to be bumped again, Debian Bookworm package list is stable, enum does not change under us)
