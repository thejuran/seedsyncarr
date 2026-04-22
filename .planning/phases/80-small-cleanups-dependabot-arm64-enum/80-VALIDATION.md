---
phase: 80
slug: small-cleanups-dependabot-arm64-enum
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-22
---

# Phase 80 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from `80-RESEARCH.md` §15.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Python)** | pytest ^9.0.3 (`src/python/pyproject.toml:16`), unittest.TestCase inside |
| **Framework (Angular)** | Jasmine ^6.2.0 + Karma ^6.4.4 (`src/angular/package.json`) |
| **Config file (Python)** | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`, lines 70–77) |
| **Config file (Angular)** | `src/angular/karma.conf.js` (via `ng test`) |
| **Quick run (Python)** | `cd src/python && poetry run pytest tests/unittests/ -q` |
| **Quick run (Angular)** | `cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless` |
| **Full suite (Python)** | `make run-tests-python` (containerized, unit + integration) |
| **Full suite (Angular)** | `make run-tests-angular` |
| **Security audit (SEC-01)** | `npm audit --audit-level=high` (repo root) |
| **Estimated runtime** | Python quick ~30s · Angular quick ~40s · Python full ~3–5 min · Angular full ~1 min |

---

## Sampling Rate

- **After every task commit:**
  - SEC-01 tasks: `npm audit --audit-level=high`
  - TECH-01 Dockerfile edits: `docker build --platform linux/arm64 -f src/docker/test/python/Dockerfile src/python` (smoke)
  - TECH-02 enum-removal tasks: `cd src/python && poetry run pytest tests/unittests/test_controller/ -q` · `cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless` (scoped)
- **After every plan wave:** `make run-tests-python && make run-tests-angular`
- **Before `/gsd-verify-work`:** Full Python + Angular suites green; `npm audit` clean; arm64 build smoke passes; `git diff .github/workflows/ci.yml` empty.
- **Max feedback latency:** ~60s (quick runs).

---

## Per-Task Verification Map

Canonical verification contract. Each REQ-ID has ≥1 automated assertion with an exact command. Status updated during execution.

| REQ | Behavior | Test Type | Automated Command | Source |
|-----|----------|-----------|-------------------|--------|
| SEC-01 | `basic-ftp@≥5.3.0` resolved at repo root after `npm install` | smoke | `npm ls basic-ftp 2>&1 \| grep -qE 'basic-ftp@5\.3'` | RESEARCH §15.2 |
| SEC-01 | `npm audit` shows 0 high-sev vulns | smoke | `npm audit --audit-level=high 2>&1 \| grep -q 'found 0 vulnerabilities'` | RESEARCH §15.2 |
| SEC-01 | Dependabot alert #3 closed (not `open`) | integration | `gh api repos/thejuran/seedsyncarr/dependabot/alerts/3 --jq '.state' \| grep -qE '^(fixed\|dismissed\|auto_dismissed)$'` | RESEARCH §15.2 |
| SEC-01 | Root `package.json` declares a top-level `overrides` block | static | `grep -E '"overrides"' package.json \| wc -l` → `≥1` | Plan 01 Task 1 (structural) |
| SEC-01 | `basic-ftp` pinned to `^5.3.0` in `overrides` | static | `grep -E '"basic-ftp": "\^5\.3\.0"' package.json \| wc -l` → `1` | Plan 01 Task 1 (structural) |
| SEC-01 | Edit scope bounded to `package.json` + `package-lock.json` | static | `git diff --stat package.json package-lock.json \| grep -cE '^ (package\.json\|package-lock\.json)'` → `2` | Plan 01 Task 1 (structural) |
| SEC-01 | Lockfile regen is confined to `basic-ftp` subgraph (no unrelated transitive bumps) | static | JSON-snapshot diff: `diff /tmp/before.json /tmp/after.json \| grep -E '"(resolved\|version)":' \| grep -v basic-ftp \| wc -l` → `0` (threat T-80-01 mitigation; snapshot files captured via `npm ls --all --json` before + after `npm install`) | Plan 01 Task 1 (confinement) |
| TECH-01 | `make run-tests-python` runs to completion on arm64 | integration | On Apple Silicon host: `make run-tests-python; echo $?` → `0` | RESEARCH §15.2 |
| TECH-01 | amd64 pytest collection count unchanged vs. pre-change baseline | smoke | `docker run --platform linux/amd64 --rm seedsyncarr/test/python pytest --collect-only 2>&1 \| grep -c '<Function'` equals baseline captured before edits | RESEARCH §15.2 |
| TECH-01 | arm64 skip messages fire only for the two rar-dependent classes | smoke | `docker run --platform linux/arm64 --rm seedsyncarr/test/python pytest -v 2>&1 \| grep -cE 'SKIPPED.*rar binary not available'` equals the documented expected count | RESEARCH §15.2 |
| TECH-01 | `.github/workflows/ci.yml` byte-identical | static | `git diff --stat .github/workflows/ci.yml \| wc -l` → `0` | RESEARCH §15.2 |
| TECH-02 | Zero residual references to the enum symbol | static | `git grep -n 'WAITING_FOR_IMPORT\|waiting_for_import\|waitingForImport' src/python/ src/angular/src/ \| wc -l` → `0` | RESEARCH §15.2 |
| TECH-02 | Python test suite green post-removal | unit+integration | `make run-tests-python` exits `0` | RESEARCH §15.2 |
| TECH-02 | Angular test suite green post-removal | unit | `make run-tests-angular` exits `0` | RESEARCH §15.2 |
| TECH-02 | Angular production build succeeds | static | `cd src/angular && npm run build` exits `0` | RESEARCH §15.2 |
| TECH-02 | `PROJECT.md` Key Decisions records the resolution | static | `grep -E 'WAITING_FOR_IMPORT' .planning/PROJECT.md` returns ≥1 line | RESEARCH §15.2 |

*Status column populated by execute-phase at run time: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No new test files required — existing infrastructure covers all phase requirements.

- [x] pytest present (`src/python/pyproject.toml`)
- [x] karma/jasmine present (`src/angular/package.json`)
- [x] `npm audit` available at repo root
- [ ] During TECH-01 plan: if `shutil` is not already imported in `tests/integration/test_controller/test_extract/test_extract.py` or `tests/integration/test_controller/test_controller.py`, add the import alongside the `@unittest.skipIf` decorator (not a Wave 0 pre-step — part of the edit itself)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| arm64 full-suite run | TECH-01 | Requires an Apple Silicon host; CI matrix does not cover `linux/arm64` for Python | On arm64 host: `make run-tests-python`; expect exit `0`. Record host `uname -m` and the final `pytest` summary line in the phase UAT/verification report. |
| Dependabot terminal state visibility | SEC-01 | GitHub scan cycle may take minutes to hours after push — rescan is async | After push: `gh api repos/thejuran/seedsyncarr/dependabot/alerts/3 --jq '.state'`; accept any non-`open` terminal state (`fixed`, `dismissed`, `auto_dismissed`). |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (none required)
- [ ] No watch-mode flags (all commands use `--watch=false` or `-q`)
- [ ] Feedback latency < 60s for quick runs
- [ ] `nyquist_compliant: true` set in frontmatter after sign-off during execution

**Approval:** pending
