# Phase 118: Durable State - Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 10 (2 code, 6 release metadata, 2 evidence docs)
**Analogs found:** 9 / 10 (the NAS smoke/deploy evidence has no prior in-repo analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/common/persist.py` (modify `to_file`, add `_fsync_directory`, module logger) | utility (persistence base class) | file-I/O | itself (lines 1-59) + `src/python/controller/extract/dispatch.py:303-345` (atomic `os.replace`/`os.rename`, never-mask-original warning) | exact (same file) + role-match |
| `src/python/tests/unittests/test_common/test_persist.py` (add RED class, e.g. `TestPersistAtomicWrite`) | test | file-I/O | itself (lines 1-99: `DummyPersist`, temp-dir fixture) + `tests/unittests/test_controller/test_extract/test_dispatch_staging.py:373-383` (os-call patch with real fallback) + `tests/unittests/test_lftp/test_lftp_status_contract.py:247` (`assertLogs`) | exact |
| `.planning/phases/118-durable-state/118-REL01-EVIDENCE.md` (create) | evidence doc | batch (test run record) | `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md` (281 lines) and `116-REL01-EVIDENCE.md` (83 lines) | exact |
| `package.json` | config (version) | transform | release commit `4f3a092` (v1.7.2) | exact |
| `src/angular/package.json` | config (version) | transform | `4f3a092` | exact |
| `src/angular/package-lock.json` (two fields) | config (version) | transform | `4f3a092` | exact |
| `src/python/pyproject.toml` (two `version` lines, 7 and 43) | config (version) | transform | `4f3a092` | exact |
| `CHANGELOG.md` | docs | n/a | `CHANGELOG.md:7-67` (`[1.7.3] - Unreleased`) and `:9-44` of the 1.7.2 block | exact |
| `release-notes.md` (rewrite for 1.7.4 + rollback runbook) | docs | n/a | current `release-notes.md` (v1.7.2) + `git show ff1ecce:release-notes.md` (v1.7.0, multi-bullet) | role-match (no prior rollback runbook) |
| Release/smoke/NAS-deploy evidence (section of `118-REL01-EVIDENCE.md` or a separate `118-RELEASE-EVIDENCE.md`) | evidence doc | request-response (ssh/curl) | none in repo; use RESEARCH §Smoke Test Recipe / §NAS Deploy Recipe, formatted like 117 evidence | no analog |

## Pattern Assignments

### `src/python/common/persist.py` (utility, file-I/O)

**Analog:** itself. Current imports and the method being replaced:

Imports (lines 1-6):
```python
import os
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from .error import AppError
from .localization import Localization
```
Package-relative imports (`from .x import`) are the local style in `common/`. Add `import logging`, `import tempfile`, and `from .constants import Constants` in the same block style. `common/constants.py:5` defines `SERVICE_NAME = "seedsyncarr"`; constants has no intra-package imports, so there is no cycle.

Current write path (lines 47-50), which is the defect:
```python
    def to_file(self, file_path: str):
        with open(file_path, "w") as f:
            f.write(self.to_str())
        os.chmod(file_path, 0o600)  # restrict to owner read/write only
```
`from_file` (lines 39-45) stays byte-for-byte unchanged (load side is out of scope).

**Replacement shape:** RESEARCH.md Code Example 1 (lines 213-263). Keep: `content = self.to_str()` first; `os.path.realpath`; `tempfile.mkstemp(dir=..., prefix=".<basename>.", suffix=".tmp")`; guard `os.fdopen` and close the fd if it raises; `fchmod 0o600` / write / flush / `os.fsync`; `os.replace` as the commit point; `except BaseException:` unlink + log unlink failure + bare `raise`; `_fsync_directory` after the commit wrapped in `except OSError` → warning.

**Logger pattern.** No module in `common/` uses a module-level logger yet. The closest established pattern is the child-of-service-logger idiom:
- `src/python/common/multiprocessing_logger.py:23`: `self.logger = base_logger.getChild("MPLogger")`
- `src/python/common/context.py:50`: `child_context.logger = self.logger.getChild(context_name)`
- `src/python/seedsyncarr.py:308-309`: `_create_logger(name, ...)` → `logging.getLogger(name)`; handlers are attached to `"seedsyncarr"` only.

Apply as `_logger = logging.getLogger(Constants.SERVICE_NAME).getChild("Persist")` → `"seedsyncarr.Persist"` (RESEARCH Pitfall 6). Do not use `logging.getLogger(__name__)`: its output never reaches `/config/log/seedsyncarr.log`.

**Never-mask-the-original-error pattern.** Analog: `src/python/controller/extract/dispatch.py:330-345`:
```python
    def __warn_unpublished_output(self, archive_path: str, staging_dir_path: str, out_dir_path: str):
        """
        A move into out_dir_path failed partway. Log what is still in the
        staging dir -- it never reached the release folder and will be
        discarded by __remove_task_staging. Never raises: this runs inside an
        OSError handler and must not mask the original failure.
        """
        if not os.path.isdir(staging_dir_path):
            return
        try:
            file_count, entries = ExtractDispatch.__list_staged_output(staging_dir_path)
        except OSError:
            self.logger.exception("Failed to list staging dir {}".format(staging_dir_path))
            return
```
Apply to the temp-unlink cleanup: an unlink `OSError` is logged (path and errno only, never `content`), then the original exception is re-raised with bare `raise`.

**Atomic rename precedent.** `dispatch.py:326-328` uses `os.replace(src, dst)` / `os.rename(src, dst)` on one filesystem (the 1.7.3 staged-extraction fix). It is the same "stage beside the target, rename into place" approach. Its docstring at `dispatch.py:62` and `:256` explains the same-filesystem requirement, so mirror that wording in the `to_file` docstring.

**Error contract (do not wrap).** Callers that must keep working unchanged:
- `seedsyncarr.py:498-501`:
```python
            try:
                config.to_file(config_path)
            except (OSError, EncryptionError, ConfigError) as exc:
                logger.warning("Encryption: failed to write re-encrypted config: %s", exc)
```
- `seedsyncarr.py:254-259` `persist()` (main thread; `ServiceExit` from `signal()` can land mid-write; `ServiceExit` subclasses `AppError(Exception)` per `common/error.py:1-12`, but `except BaseException` also covers `KeyboardInterrupt`).
- `seedsyncarr.py:70` (default-config creation).
Re-raise the original type. Never convert it to `PersistError`, because `_load_persist` (`seedsyncarr.py:520-560`) treats `PersistError` as "corrupt → `__backup_file` → reset".

**Temp-name non-collision.** `seedsyncarr.py:566-579` `__backup_file` uses `<name>.<N>.bak` in the same dir. The `.<name>.<rand>.tmp` prefix/suffix cannot collide with it.

---

### `src/python/tests/unittests/test_common/test_persist.py` (test, file-I/O)

**Analog:** itself. Reuse the existing imports, `DummyPersist`, and fixture. Add a new `TestPersistAtomicWrite(unittest.TestCase)` class; do not edit the existing `TestPersist` tests (they are the PERSIST-02 preservation tests).

Imports (lines 1-6), to extend with `errno`, `stat`, and `from unittest.mock import patch`:
```python
import unittest
import tempfile
import shutil
import os

from common import overrides, Persist, AppError, Localization
```
Add `ServiceExit` to the `from common import ...` line for the interrupt test (it is exported in `common/__init__.py`).

`DummyPersist` (lines 9-22): `to_str` returns `self.my_content`. For the serialization-failure test, subclass it with a `to_str` that raises `ValueError`. The lone-surrogate content `"ok \udc80 tail"` triggers a real `UnicodeEncodeError` on write.

Fixture (lines 25-34):
```python
class TestPersist(unittest.TestCase):
    @overrides(unittest.TestCase)
    def setUp(self):
        # Create a temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="test_persist")

    @overrides(unittest.TestCase)
    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.temp_dir)
```

Existing success-path assertion style (lines 70-76), which the new `no_temp_after_success` test should follow:
```python
    def test_to_file_sets_0600_permissions(self):
        file_path = os.path.join(self.temp_dir, "persist_perms")
        persist = DummyPersist()
        persist.my_content = "sensitive content"
        persist.to_file(file_path)
        mode = os.stat(file_path).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 permissions, got {oct(mode)}")
```

**OS-call patch with a real fallback.** Analog: `tests/unittests/test_controller/test_extract/test_dispatch_staging.py:373-383`:
```python
        real_rename = os.rename
        moved = []

        def _rename(src, dst):
            if moved:
                raise OSError("simulated rename failure")
            real_rename(src, dst)
            moved.append(os.path.basename(dst))
        rename_patcher = patch("controller.extract.dispatch.os.rename", side_effect=_rename)
        self.addCleanup(rename_patcher.stop)
        rename_patcher.start()
```
Apply for the file-vs-directory `os.fsync` discriminators (RESEARCH Code Example 3): capture `_real_fsync = os.fsync` at module import, then patch the **global** `"os.fsync"` with an `S_ISREG` or `S_ISDIR` side effect. Use the global `patch("os.replace", ...)` and `patch("tempfile.mkstemp", ...)` targets for the replace and temp-creation failures (the dispatch analog above patches a module-qualified path, but that does not transfer here). Never patch `common.persist.tempfile.mkstemp`: pre-fix `persist.py` does not import `tempfile`, so that target is a `ModuleNotFoundError`/`AttributeError` harness error, not a behavioral RED. Never patch `common.persist._fsync_directory` for the same reason. The global attributes are what `persist.py` resolves at call time on both pre- and post-fix code; 118-01-PLAN.md mandates this and gates it with `grep -n 'patch("common.persist'` returning nothing.

**Log assertion.** Analog: `tests/unittests/test_lftp/test_lftp_status_contract.py:247-252`:
```python
        with self.assertLogs("Lftp", level="WARNING") as cm:
            self.assertIsNone(lftp.status())
        for line in cm.output:
            self.assertNotIn("secret-path", line)
```
Apply as `with self.assertLogs("seedsyncarr.Persist", level="WARNING") as cm:` for the dir-fsync test. Also assert the written content does not appear in `cm.output` (the CWE-117 / no-secret-in-log idiom from the same test).

**Module docstring.** `test_lftp_status_contract.py:1-17` opens with a docstring that states the contract being pinned. Copy that convention for the new class or section: original intact, no temp left, original exception type raised, dir-fsync logged and not raised.

**Per-failure assertion triple** (RESEARCH Pattern 2): `assertRaises(<specific type>)`; `open(path, "rb").read() == b"ORIGINAL"`; `sorted(os.listdir(self.temp_dir)) == ["persist"]`. Plus a no-pre-existing-target variant that asserts `os.listdir(self.temp_dir) == []`.

**RED commit discipline** (from `117-01-SUMMARY.md:38, 103-104, 122`): per-task `test(118-01)` commits contain test files only, with no production change, so the pre-fix SHA is provable with `git diff --stat`.

---

### `.planning/phases/118-durable-state/118-REL01-EVIDENCE.md` (evidence doc, batch)

**Analog:** `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md`. Copy its section skeleton exactly:

1. Title and pre-fix SHA proof (lines 1-10):
```
# Phase 117 REL-01 gate-1 evidence (fail-before / pass-after)

RED run executed against pre-fix code at `05f03ae` (...). The production tree at that SHA is byte-identical to `7da18e0`:

$ git diff --stat 7da18e0 05f03ae -- src/python/lftp src/python/common src/python/controller ':!src/python/tests'
(empty)
```
For 118 the pathspec is `src/python/common ':!src/python/tests'`.
2. `## RED (pre-fix) — Plan 118-01`: the **Command** block (lines 14-29) with `-q -p no:cacheprovider -rf --tb=line --junitxml=<scratchpad>/118-red.xml`; a worktree note that it ran under the main checkout's Poetry interpreter (lines 31-32: `/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python -m pytest`); verbatim `FAILED ... - <first line of junit failure message>` list (lines 34-63); a **Failure types** paragraph stating that none is ImportError, AttributeError or TypeError (line 67); **Summary line**; whole-tree **Ruff** line; **Preservation tests passing on pre-fix code** bullets (lines 73-84); and a `| # | Failing test | Requirement | Decision |` table (lines 86-113).
3. `### New-contract tests (added with the fixes; not regressions)` table (lines 117-131).
4. `## GREEN (post-fix)`: post-fix SHA, **Fix commits** table (lines 141-148), the `git diff --stat` file list (line 150), **Targeted regressions** `-v -k` output (lines 152-189), phase quick run with a **Delta vs RED** arithmetic paragraph (lines 191-205), new-contract names, preservation re-run.
5. `### Full host suite`, two parts (lines 251-263): part 1 with the four `--ignore`s, then part 2 per-file under `perl -e 'alarm 60; exec @ARGV'`. Baseline **21 failed / 3 errors** must be unchanged, plus a ruff line.

**REL-01 combined-regression addition (new for 118):** one `-v -k` run on the release SHA covering 116's 8 RED names (`116-REL01-EVIDENCE.md:22-29`), 117's 26 (`117-REL01-EVIDENCE.md:37-62`) and 118's new RED names. The shorter 116 format (`116-REL01-EVIDENCE.md:1-40`: command, FAILED list, summary, ruff, preservation names) is acceptable for the 118 RED section, since there are only about 6 tests.

---

### Version-bump sites (config, transform)

**Analog:** release commit `4f3a092` ("chore(release): v1.7.2 ..."). It touched exactly 6 files: `CHANGELOG.md`, `package.json`, `release-notes.md`, `src/angular/package-lock.json`, `src/angular/package.json`, `src/python/pyproject.toml`. Current values are all `1.7.2`:

| File | Line(s) | Current |
|------|---------|---------|
| `package.json` | 2 | `"version": "1.7.2",` |
| `src/angular/package.json` | 3 | `"version": "1.7.2",` |
| `src/angular/package-lock.json` | 3 and 9 (`packages[""].version`) | `"version": "1.7.2",` (leave line 60 `2.3.0` alone; it is a dependency) |
| `src/python/pyproject.toml` | 7 (`[project]`) and 43 (`[tool.poetry]`) | `version = "1.7.2"` |

Commit message pattern (from `4f3a092`):
```
chore(release): v1.7.4 — <one-line theme>

<short paragraph>

Bump version to 1.7.4 across package.json, angular package/lock, and
pyproject.toml; add CHANGELOG [1.7.4] and rewrite release-notes.md.
Release-metadata verifier passes for 1.7.4.
```
**Gate:** `scripts/verify-release-metadata.mjs:25-28` needs a heading matching `^##\s+\[?1.7.4\]?(?:\s+-\s+.+)?\s*$`. Lines 94-103 need `v{{VERSION}}/CHANGELOG.md` in `release-notes.md`. Lines 106+ check the package versions. Run `npm run verify:release-metadata -- 1.7.4` and `npm run test:release-metadata` (`package.json:4-5`) before the D-02 checkpoint.

### `CHANGELOG.md` (docs)

**Analog:** `CHANGELOG.md:7-67` (the `[1.7.3] - Unreleased` block) and the `[1.7.2] - 2026-09-05` block. Structure: `## [X.Y.Z] - YYYY-MM-DD`; an incident/context paragraph hard-wrapped at about 76 columns; `### Fixed` bullets ("Fixed <user-visible defect>. <mechanism>."); optional `### Added`; `### Internal` (constants and test modules by name). Per RESEARCH F1, fold the existing 1.7.3 content into `## [1.7.4] - <date>` with a one-line "1.7.3 was never tagged; its fixes ship here" note. Add Fixed entries for Phase 116 (import ambiguity), Phase 117 (transfer-state safety, plus the Stop behavior change) and Phase 118 (atomic persist writes).

### `release-notes.md` (docs)

**Analog:** current `release-notes.md` (15 lines, v1.7.2) and `git show ff1ecce:release-notes.md` (v1.7.0; the better template for a multi-fix release). Structure:
```
<one-paragraph plain-language summary, no version heading>

Existing config and persist files load unchanged; ...

### What changed for you

- **<Bold user-facing outcome>** — <one or two plain sentences>.

### Should you update?

<Yes/when, baseline version>.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
```
The final `{{VERSION}}` line is required by the metadata gate. There is **no prior rollback-runbook section** (`git log -S 'oll back'` finds nothing). Add a new `### Before you upgrade / If you need to roll back` section in the same plain-language bullet style, with the D-06 steps. The rollback target is `:1.7.2` publicly, because `:1.7.3` does not exist (RESEARCH F1 / Open Question 1; confirm at the checkpoint). D-07's Stop change goes in as a "What changed for you" bullet.

---

## Shared Patterns

### Logging (no secrets, path and errno only)
**Source:** `src/python/tests/unittests/test_lftp/test_lftp_status_contract.py:244-252` (CWE-117 assertion) and `dispatch.py:313-315` (`self.logger.warning("Replacing existing '{}' ...".format(dst))`)
**Apply to:** `persist.py` warnings and their tests. Log the path and the exception. Never log `content` (settings.cfg may hold plaintext secrets when encryption is off).

### RED → fix → GREEN evidence
**Source:** `117-REL01-EVIDENCE.md` (whole file), `116-REL01-EVIDENCE.md:1-40`
**Apply to:** Plan 118-01 (RED tests + RED evidence), the fix plan, and the GREEN/REL-01 plan. Every RED failure must be `AssertionError` or "<Exc> not raised", never AttributeError or ImportError.

### Lint gate
**Source:** evidence files' ruff lines; CI pins `ruff==0.15.22`
**Apply to:** every code plan. `poetry run ruff check src/python/` plus `uvx ruff@0.15.22 check src/python/` (whole tree).

### NAS commands
**Source:** global CLAUDE.md NAS section and RESEARCH recipes
**Apply to:** smoke and deploy tasks. Always use `ssh nas '... sudo /usr/local/bin/docker compose ...'`; never bare `sudo docker`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Smoke-test + NAS-deploy evidence (image index digest, RepoDigests match, `/server/status` scanner-recovery proof, persist-file `ls -la`) | evidence doc | request-response | No prior phase recorded deploy evidence in `.planning/` (grep for `RepoDigests` / `compose pull` finds only 118-RESEARCH). Use RESEARCH §Smoke Test Recipe (lines 312-334) and §NAS Deploy Recipe (lines 336-355) as the command source, and the 117 evidence style (command block → verbatim output → one-line verdict) for formatting. |
| Rollback runbook section in `release-notes.md` | docs | n/a | No prior release notes contain a rollback runbook; reuse only the plain-language bullet style. |

## Conventions

`gsd-tools verify conventions --derive --scope src/python`:

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| file-name casing | none (other 45 / snake 39 / camel 29) | 40% | 0.986 | contested hotspot |
| identifier casing | none (camel 425 / Pascal 279) | 55% | 0.605 | contested hotspot |
| export style | cjs | 100% | 0 | named contract (JS-oriented detector; not meaningful for Python) |
| import style | n/a | n/a | n/a | insufficient data |
| py-wildcard-import | explicit | 100% | 0 | named contract |
| py-import-relativity | none (relative 48 / absolute 26) | 65% | 0.935 | contested hotspot |

**Contested hotspots (author's choice):** match the directory's local style. In `common/`, production modules use package-relative imports (`from .error import AppError`), while tests use absolute imports from the package root (`from common import ...`). The casing axes are skewed by the JS-oriented detector; Python code here uses snake_case functions and files and PascalCase classes. The prototype intentional split is the CJS<->SDK dual resolver (`bin/lib/**` CJS vs `sdk/src/**` ESM): each half is internally consistent per directory and contested only repo-wide. Apply the same rule here.

## Metadata

**Analog search scope:** `src/python/common`, `src/python/controller/extract`, `src/python/seedsyncarr.py`, `src/python/tests/unittests/{test_common,test_lftp,test_controller/test_extract}`, `.planning/phases/{116,117}*`, `scripts/verify-release-metadata.mjs`, release commits `4f3a092`/`ff1ecce`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-08
