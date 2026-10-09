# Phase 118: Durable State - Research

**Researched:** 2026-10-08
**Domain:** Atomic file replacement in Python (POSIX), plus the 1.7.4 release pipeline (GitHub Actions → GHCR → Synology NAS)
**Confidence:** HIGH (code side), MEDIUM-HIGH (release side; three facts found that contradict planning docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Release flow (REL-01)
- **D-01:** Order is **tag → CI-built image → smoke-test that exact image → deploy the same digest to the NAS**. Code + regression evidence first; then merge to main and push the annotated `v1.7.4` tag; CI builds and pushes `ghcr.io/thejuran/seedsyncarr:1.7.4`; smoke-test that pulled image (startup, transfer status, settings persistence, restart); then deploy the identical digest to the NAS (owner note: "deploy to the NAS the exact image that passed testing (same tag/digest)").
- **D-02:** **One owner approval checkpoint before pushing the tag** (the tag push publishes the release). The plan must include it as a `checkpoint:human-verify`/decision gate — the executor never pushes the tag or deploys unattended.
- **D-03:** NAS deploy pins compose to `:1.7.4` (never `:dev`), via `ssh nas` and the absolute `sudo /usr/local/bin/docker compose ...` path. Flag the wud `watch.digest` side effect. A post-deploy scanner error is accepted as the known warm-up condition **only after** a subsequent successful scan in the log confirms recovery.
- **D-04:** Version bump to `1.7.4` in `package.json` and `src/python/pyproject.toml` (both `version` lines) lands before the tag.

#### Merge to main
- **D-05:** Push local `main` (including the 11 unpushed planning commits 7f7be28..c734c10), then **merge `safety-patch-1.7.4` into `main` preserving history**, and tag from `main`. No squash — evidence files reference per-fix commit SHAs.

#### Rollback runbook
- **D-06:** Write a **full rollback runbook into `release-notes.md` for 1.7.4**: before upgrade, back up the three persist files; to roll back to 1.7.3 — disable auto-delete, stop the service, restore the backups, re-pin `:1.7.3`, keep auto-delete off until imports are reconciled (reason: Phase 116's duplicate-basename skip means 1.7.3 could read a missing import record as "fully imported").
- **D-07:** Release notes also call out the Phase 117 user-visible change: pressing Stop while LFTP status is temporarily unavailable now returns an error (retry once status recovers) instead of a false success. Release notes follow the existing plain-language `release-notes.md` style ("What changed for you" / "Should you update?").

#### Carried forward (locked by spec / prior phases)
- Each targeted regression must be shown to fail against the old behavior before its fix (REL-01 gate 1) — same RED → fix → GREEN evidence format as `117-REL01-EVIDENCE.md`.
- CI gate: full Python suite + `ruff check src/python/` whole-tree + coverage `fail_under` ≥ 88. CI Docker is the full-suite authority; the local host suite hangs in `test_extract_process.py` (use the established deselect/ignore list).
- Known deferred item: backlog 999.2 (LFTP command-stream resync after timeout) stays out of 1.7.4.

### Claude's Discretion
- Temp-file naming/creation mechanism (e.g. `tempfile.mkstemp(dir=...)`), and how each failure point is injected in tests.
- Smoke-test mechanics (docker run against the pulled image with a scratch config dir).
- CHANGELOG.md entry wording.

### Deferred Ideas (OUT OF SCOPE)
- Backlog 999.2 — LFTP command-stream resync after timeout (not in 1.7.4).
- (Spec) path-mapping redesign, persistence migration or format changes, backup systems, load-side recovery changes.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERSIST-01 | Any failure before the atomic replace (serialization, temp creation, write, fsync, replace) leaves the original byte-for-byte intact and removes the temp file | §Pattern 1 (to_file shape), §Pattern 2 (failure injection that is RED on old code for behavioral reasons), Pitfalls 1-5 |
| PERSIST-02 | Successful save → correct content, `0600`; after `os.replace` the new file is committed; directory fsync best-effort, logged not raised | §Pattern 1 (`_fsync_directory` after the commit point), Pitfall 6 (logger must be a child of the `seedsyncarr` logger to reach `/config/log`) |
| REL-01 | Fail-before/pass-after for every 116-118 regression; full suite + whole-tree ruff; smoke test of the built image; `:1.7.4` deployed to NAS with scanner recovery confirmed | §Release Pipeline Facts, §Smoke Test Recipe, §NAS Deploy Recipe, Findings F1-F5 |
</phase_requirements>

## Summary

The code half is small and well-understood. `Persist.to_file` (`src/python/common/persist.py:47-50`) currently does `open(path, "w")` → `write(self.to_str())` → `os.chmod(0o600)`. Because `open("w")` truncates **before** `to_str()` runs, any serialization failure (for example `Config.to_str` raising `ConfigError` when encryption is enabled with no keyfile path, `config.py:496-510`) already leaves an empty file. The fix is the standard POSIX pattern: serialize first → `tempfile.mkstemp(dir=<target dir>)` (atomically created `0600`, `O_EXCL`) → write/flush/`os.fsync` → `os.replace` (atomic on POSIX) → `fsync` the directory fd, best-effort. Callers (`seedsyncarr.py:70, 257-259, 499`) need no change. Re-raise the **original** exception unchanged: `_reencrypt_plaintext_if_needed` catches `(OSError, EncryptionError, ConfigError)`, and wrapping errors in `PersistError` would break that contract.

The release half matters more for planning, because three facts on the ground contradict the planning docs. **(F1)** 1.7.3 was never released: no `v1.7.3` tag, no GitHub release, `CHANGELOG.md` says `## [1.7.3] - Unreleased`, and every version file still says `1.7.2`. 1.7.4 therefore ships the 1.7.3 content too, and "roll back to `:1.7.3`" (D-06) points at an image tag that does not exist. **(F2)** The NAS is not on `:1.7.2`. It runs `ghcr.io/thejuran/seedsyncarr:357`, a CI run-number staging tag built from `main@f8c94e9` (1.7.3 code), with RepoDigest `sha256:87ca6695…4e9f`. That digest is the true pre-upgrade rollback point for the NAS. **(F3)** `scripts/verify-release-metadata.mjs` gates the tag pipeline and checks five version fields, not the three in D-04: `package.json`, `src/angular/package.json`, `src/angular/package-lock.json` (`version` **and** `packages[""].version`), plus a `## [1.7.4]` CHANGELOG heading and a `v{{VERSION}}/CHANGELOG.md` link in `release-notes.md`. The PyPI job stamps `pyproject.toml` from the tag, but D-04's bump of both `pyproject.toml` lines is still right for consistency.

Two more pipeline facts the planner must design around. **(F4)** `publish-docker-image` **rebuilds** the image (`make docker-image-release` → `buildx build --push`, cache-from staging) rather than retagging the e2e-tested staging image. `:1.7.4` and `:latest` are separate builds whose digests can differ. That is exactly why D-01's smoke test of the pulled `:1.7.4` image is the real gate. Record the multi-arch **index** digest of `:1.7.4` and verify that the NAS `RepoDigests` matches it. **(F5)** CI's Python test container runs `pytest -v -p no:cacheprovider` with no `--cov`, so `fail_under = 88` is **not enforced in CI**. Treat coverage as a local check if the gate is kept. CI tests also run as **root**, so permission-based failure injection (read-only dirs) silently does not fail there.

**Primary recommendation:** Implement `to_file` exactly as in Code Example 1 (mkstemp in the realpath'd target dir, `except BaseException` cleanup plus bare `raise`, a separate `_fsync_directory` helper logging through `seedsyncarr.Persist`). Write RED tests whose injected failures are behavioral on the old code. Then run the release as: version/CHANGELOG/release-notes commit → owner checkpoint → push main + tag → wait for publish → smoke-test `:1.7.4` **on the NAS** (amd64, the deploy arch) in a scratch container on port 8801 → deploy the same index digest → confirm a clean remote scan via `/server/status`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Atomic persist write | Python daemon (`common/persist.py`) | Filesystem (btrfs on NAS) | Single write path for all three files; atomicity comes from POSIX `rename(2)` |
| Durability (fsync file + dir) | Python daemon | OS/kernel | Best-effort dir fsync only after the commit point |
| Failure logging | Python daemon logger `seedsyncarr.*` | `/config/log/seedsyncarr.log` | Only loggers under `seedsyncarr` reach the file handler (root has no handlers in MainProcess) |
| Version metadata / changelog | Repo (release commit) | CI `verify-release-metadata` | Tag pipeline fails if the metadata does not match the tag |
| Image build/publish | GitHub Actions `ci.yml` | GHCR | Tag `vX.Y.Z` → e2e (amd64+arm64) → rebuild + push `:X.Y.Z` and `:latest`, GH release, PyPI |
| Smoke test | NAS docker (scratch container) | — | Exercises the amd64 variant actually deployed; local Docker Desktop daemon is not running |
| Deploy + rollback | NAS compose (`/volume1/docker/docker-compose.yml`) | wud (auto-update trigger, live) | Pin `:1.7.4`; wud's dockercompose trigger can rewrite the compose file |

## Standard Stack

No new packages. Python stdlib only.

### Core
| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `tempfile.mkstemp` | stdlib (runtime image Python 3.11; local 3.12.12) | Create the temp file in the target dir, `0600`, `O_EXCL`, no race | "readable and writable only by the creating user ID… no race conditions in the file's creation" [CITED: docs.python.org/3.11/library/tempfile.html#tempfile.mkstemp] |
| `os.replace` | stdlib | Commit point; atomic rename that overwrites on POSIX | Atomic when it succeeds, same-filesystem required [CITED: docs.python.org/3.11/library/os.html#os.replace; exact wording from training, page fetch truncated — ASSUMED wording, behavior is POSIX `rename(2)`] |
| `os.fsync` | stdlib | Flush file data; then flush the directory entry via `os.open(dir, O_RDONLY)` | "first do f.flush(), and then do os.fsync(f.fileno())" [CITED: docs.python.org/3.11/library/os.html#os.fsync]; dir-fd fsync verified working on this macOS host [VERIFIED: local probe] |
| `os.fchmod` | stdlib, Unix | Explicit `0600` on the temp fd (belt and braces with mkstemp's mode) | [CITED: docs.python.org/3.11/library/os.html#os.fchmod] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mkstemp` | `NamedTemporaryFile(delete=False, dir=...)` | Same result, but the wrapper's `delete` semantics and close-on-exit are easy to get wrong; mkstemp is simpler to reason about |
| stdlib | `atomicwrites` (PyPI) | Archived/unmaintained upstream [ASSUMED]; adds a dependency for about 20 lines. Do not add. |

**Installation:** none.

## Package Legitimacy Audit

Not applicable. This phase installs no external packages (stdlib only). `ruff==0.15.22` is already pinned in CI and is not new.

## Architecture Patterns

### Data flow (save path)

```
main loop (every 30s, MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS) / shutdown / startup default-config / re-encrypt
        │
        ▼
Persist.to_file(path)
  1. content = self.to_str()         ── raises → nothing on disk touched → propagate
  2. mkstemp(dir=dirname(realpath(path)), prefix=".<name>.", suffix=".tmp")
  3. fchmod 0600 → write → flush → fsync(file)
  4. os.replace(tmp, target)         ◄── COMMIT POINT
        │ any exception in 2-4 (incl. ServiceExit/KeyboardInterrupt) → unlink tmp (log if unlink fails) → bare raise
        ▼
  5. _fsync_directory(dir)           ── OSError → logger.warning on "seedsyncarr.Persist", NOT raised
        ▼
     return
```

### Pattern 1: Atomic replace with a strict failure contract
**What:** See Code Example 1.
**Key rules:**
- `to_str()` runs before any filesystem call. This alone fixes the serialization-truncation defect.
- Put the temp file in the **same directory** as the target (same filesystem, so `os.replace` is a rename, not `EXDEV`).
- Cleanup catches `BaseException`. `Seedsyncarr.signal` raises `ServiceExit` from the SIGTERM handler in the main thread, and `persist()` runs in the main thread (`seedsyncarr.py:191, 247, 254-259`), so a stop signal can land mid-write. Cleanup then bare `raise`.
- Only the directory fsync is wrapped in a log-and-continue. Everything before `os.replace` raises.

### Pattern 2: Failure injection that is RED on the old code for behavioral reasons
Phase 117's evidence made a point that no RED failure was an ImportError, AttributeError or harness error. Keep that property:

| Failure point | Injection | Old-code RED reason (all `AssertionError`) |
|---|---|---|
| Serialization | `DummyPersist.to_str` raises `ValueError` | Old code truncates first → `b'' != b'ORIGINAL'` |
| Write | Content containing a lone surrogate `"ok \udc80 tail"` → real `UnicodeEncodeError` from the UTF-8 encoder, no mocks | Old code truncates, then the write raises → file is `''` [VERIFIED: local probe on Python 3.12] |
| File fsync | `patch("os.fsync", side_effect=fsync_fail_if_regular_file)` (raise only when `stat.S_ISREG(os.fstat(fd).st_mode)`) | Old code never fsyncs → "OSError not raised" |
| Replace | `patch("os.replace", side_effect=OSError(errno.EACCES, ...))` | Old code never replaces → "OSError not raised" |
| Temp creation (spec lists it in the contract; add as a 5th) | `patch("tempfile.mkstemp", side_effect=OSError(errno.ENOSPC, ...))` | "OSError not raised" |
| Dir fsync after replace | `patch("os.fsync", side_effect=fsync_fail_if_directory)` (real fsync for regular files) + `assertLogs("seedsyncarr.Persist", "WARNING")` | Old code never logs → "no logs of level WARNING or higher triggered" |

Patch targets MUST be the **global** module attributes `"os.fsync"`, `"os.replace"`, `"tempfile.mkstemp"`. Do **not** patch `common.persist.tempfile.mkstemp`: pre-fix `persist.py` does not import `tempfile`, so that target raises `ModuleNotFoundError`/`AttributeError` from `unittest.mock` (a harness error, not a behavioral RED). Do **not** patch `common.persist._fsync_directory` for the same reason (the symbol does not exist on old code). `common.persist.os.replace` happens to resolve on old code (persist.py imports `os`) but is the same object as the global `os.replace`; use the global form everywhere for consistency with 118-01-PLAN.md. Use the `S_ISDIR` side_effect on `os.fsync` to inject the directory-fsync failure. The same global patches work on old and new code because persist.py calls them as module attributes at call time.

Every failure test asserts all three: (a) `assertRaises` with the specific type, (b) original bytes unchanged (read `"rb"`), (c) `sorted(os.listdir(temp_dir)) == ["persist"]` (no temp left). Add a variant with no pre-existing target: after a failure, the directory is empty.

New-contract tests (no pre-fix behavior to fail against; list them separately as in 117): the temp file is created in the target's directory (spy on `mkstemp`'s `dir`), no `.tmp` remains after success, the original exception type is preserved (not wrapped), and an interrupt (`ServiceExit` raised from the write) still cleans up. Preservation tests (pass before and after): the existing `test_to_file_*` and `test_from_file_*` in `test_persist.py`, `test_config.py::test_to_file`, and `test_seedsyncarr.py` re-encrypt tests.

### Anti-Patterns to Avoid
- **Wrapping errors in `PersistError`:** this changes caller contracts (`_reencrypt_plaintext_if_needed` catches `OSError/EncryptionError/ConfigError`; `_load_persist` treats `PersistError` as "corrupt file → back up and reset", which is the load side). Re-raise the original.
- **Temp file in `/tmp` or `gettempdir()`:** that is a different filesystem in Docker (`/config` is a bind mount), so `os.replace` raises `EXDEV`.
- **`with os.fdopen(fd)` without guarding fdopen itself:** if `fdopen` raises, the fd leaks. Close the fd in the except path when no file object owns it yet.
- **Cleanup that masks the original error:** unlink failure must be logged, not raised over the original exception.
- **Permission-based failure injection (`chmod 0500` on the dir):** CI tests run as root (`src/docker/test/python/Dockerfile:49 USER root`), so the injection silently does nothing there. Use mocks or the surrogate trick.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique, race-free temp file | `path + ".tmp"` naming | `tempfile.mkstemp(dir=...)` | Fixed names collide and are not `O_EXCL`; mkstemp gives `0600` and no race |
| Atomic swap | copy-then-truncate, or `os.rename` with a pre-delete | `os.replace` | Single atomic syscall; overwrites on POSIX |
| Smoke harness | A new Python/Node test runner | `docker run` + `curl` against the existing `/server/status`, `/server/config/set`, `/server/config/get` | Endpoints exist; with no `api_token` configured, all `/server/*` are open (`web_app.py:122-127`) |

## Runtime State Inventory

Not a rename phase. One runtime-state item matters for the deploy:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | NAS `/volume1/docker/seedsync/{settings.cfg, controller.persist, autoqueue.persist}` (all `-rw------- jule1651 users`, no ACL `+`); the dir itself is `drwxrwxrwx+` (synoacl, btrfs) | Back up all three before the upgrade (D-06). After deploy, verify they are still `-rw-------`, owned by jule1651, with no `+`, and that no `.*.tmp` remains |
| Live service config | NAS compose pins `seedsyncarr:357` (not `:1.7.2`); label `wud.watch.digest=true`; wud `getwud/wud:8.2.2` has `WUD_TRIGGER_DOCKERCOMPOSE_LOCAL_DRYRUN=false`, compose mounted `rw`, cron `0 */6 * * *`, `WATCHBYDEFAULT=true` | Pin `:1.7.4`; flag that wud can rewrite the compose file; the smoke container needs `--label wud.watch=false` |
| OS-registered state | None — verified by `docker inspect` (compose-managed only) | — |
| Secrets/env vars | None changed | — |
| Build artifacts | None | — |

## Common Pitfalls

### Pitfall 1: Serialize-after-open (the defect itself)
**What goes wrong:** `open("w")` truncates, then `to_str()` raises (`ConfigError` for encryption without a keyfile; `load_or_create_key` I/O errors) and leaves an empty file. On the next start it is treated as corrupt, backed up, and reset.
**How to avoid:** `content = self.to_str()` is the first line.

### Pitfall 2: Cross-filesystem temp file
**What goes wrong:** `EXDEV` on `os.replace`.
**How to avoid:** `dir=os.path.dirname(target)`. Compute from `os.path.realpath(file_path)` so (a) a relative path such as `"settings.cfg"` gives a real dir for `os.open(dir)` (an empty dirname cannot be opened), and (b) a symlinked target keeps today's write-through-the-link behavior instead of replacing the symlink with a regular file. No symlinks exist on the NAS today [VERIFIED: `ls -la`], so (b) is defensive.

### Pitfall 3: Signal mid-write
**What goes wrong:** SIGTERM → `ServiceExit` raised inside `to_file` → with `except Exception` only (if `ServiceExit` is not an `Exception` subclass) or no cleanup, the temp file leaks.
**How to avoid:** `except BaseException:` cleanup + bare `raise`.

### Pitfall 4: Orphan temp files after power loss or `kill -9`
**What goes wrong:** A crash between `mkstemp` and `os.replace` leaves `.settings.cfg.XXXX.tmp`. The original is intact (the contract holds), but the orphan stays.
**How to avoid:** Out of scope (the spec forbids load-side changes). Use a hidden, recognizable prefix/suffix (`.<basename>.<rand>.tmp`) that cannot collide with `__backup_file`'s `<name>.<N>.bak` pattern, and mention manual cleanup in release notes only if the owner wants it.

### Pitfall 5: Old tests that assume in-place writes
**What goes wrong:** Any test that patches `builtins.open` around `to_file`.
**Status:** Checked. No test mocks `to_file` or `open` for persist writes (`grep` across `src/python/tests`). `test_seedsyncarr.py:378,386` and `test_config.py:736` call `to_file` for real; they are preservation tests.

### Pitfall 6: The "logged" dir-fsync warning never reaches the log file
**What goes wrong:** `logging.getLogger(__name__)` → `common.persist` propagates to root. In MainProcess the root logger has **no handlers** (`_create_logger` attaches handlers to `"seedsyncarr"` and `"web_access"` only; `MultiprocessingLogger` configures root only in child processes). The warning goes only to Python's `lastResort` stderr, which lands in `docker logs` but not `/config/log/seedsyncarr.log`.
**How to avoid:** `logging.getLogger(Constants.SERVICE_NAME).getChild("Persist")` → `"seedsyncarr.Persist"`. Tests use `assertLogs("seedsyncarr.Persist", level="WARNING")`. `common/persist.py` may import `.constants` (constants has no intra-package imports, so there is no cycle). Never log file content; the path and errno are fine.

### Pitfall 7: Local ruff is not the CI ruff
**What goes wrong:** Local `ruff 0.15.9` (PATH and poetry) vs CI `ruff==0.15.22`.
**How to avoid:** For the release gate run `uvx ruff@0.15.22 check src/python/` (uvx is at `/opt/homebrew/bin/uvx`) in addition to `poetry run ruff check src/python/`.

### Pitfall 8: Version-file drift fails the tag pipeline
**What goes wrong:** `verify-release-metadata` fails → no image, no release. The tag then needs deleting and re-pushing.
**How to avoid:** Before the checkpoint, run `npm run verify:release-metadata -- 1.7.4` locally (Node available) and `npm run test:release-metadata`. Bump all five fields (F3).

### Pitfall 9: "Same digest" compared at the wrong level
**What goes wrong:** The local/NAS `docker image inspect .Id` is the platform config digest; GHCR's `:1.7.4` is a multi-arch index.
**How to avoid:** Record the index digest via `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.7.4` (or `RepoDigests` after pull). On the NAS, `docker image inspect ghcr.io/thejuran/seedsyncarr:1.7.4 --format '{{json .RepoDigests}}'` must show the same `sha256:` as the smoke-tested pull. Optionally pin compose as `:1.7.4@sha256:<index>` [ASSUMED: compose 2.20.1 accepts tag@digest; it is standard reference syntax].

### Pitfall 10: Scanner warm-up error misread
**How to avoid:** After the deploy, poll `curl -s http://localhost:8800/server/status` on the NAS until `controller.latest_remote_scan_failed == false` **and** `latest_remote_scan_time` is later than the deploy start (or later than any scanner error timestamp in `/volume1/docker/seedsync/log/seedsyncarr.log`). Remember that app-log time = NAS host time + 1h.

## Code Examples

### 1. `Persist.to_file` (recommended shape)
```python
# src/python/common/persist.py  (sketch — planner/executor finalizes)
import logging
import os
import tempfile

from .constants import Constants

_logger = logging.getLogger(Constants.SERVICE_NAME).getChild("Persist")


def _fsync_directory(dir_path: str) -> None:
    fd = os.open(dir_path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Persist(Serializable):
    def to_file(self, file_path: str):
        content = self.to_str()                                   # 1. serialize first
        target = os.path.realpath(file_path)
        dir_path = os.path.dirname(target)
        fd, tmp_path = tempfile.mkstemp(                          # 2. 0600, O_EXCL, same dir
            dir=dir_path, prefix=".{}.".format(os.path.basename(target)), suffix=".tmp")
        try:
            try:
                f = os.fdopen(fd, "w")    # same default encoding as the old open(path, "w")
            except BaseException:
                os.close(fd)
                raise
            with f:
                os.fchmod(f.fileno(), 0o600)
                f.write(content)                                  # 3. write/flush/fsync
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)                          # 4. COMMIT POINT
        except BaseException:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                _logger.warning("Could not remove temp file %s: %s", tmp_path, e)
            raise
        try:                                                      # 5. best effort
            _fsync_directory(dir_path)
        except OSError as e:
            _logger.warning("Directory fsync failed for %s (file committed): %s", dir_path, e)
```
Notes: `os.fdopen(fd, "w")` keeps the old text-mode default encoding. The runtime image sets `LANG=C.UTF-8` (Dockerfile:102), so the on-disk format is unchanged. `from_file` is untouched.

### 2. RED test skeleton (write failure, no mocks)
```python
def test_write_failure_leaves_original_and_no_temp(self):
    path = os.path.join(self.temp_dir, "persist")
    with open(path, "wb") as f:
        f.write(b"ORIGINAL")
    p = DummyPersist(); p.my_content = "ok \udc80 tail"   # lone surrogate → UnicodeEncodeError on write
    with self.assertRaises(UnicodeEncodeError):
        p.to_file(path)
    with open(path, "rb") as f:
        self.assertEqual(b"ORIGINAL", f.read())
    self.assertEqual(["persist"], sorted(os.listdir(self.temp_dir)))
```

### 3. fsync side-effects that discriminate file vs directory
```python
_real_fsync = os.fsync
def _fail_on_regular_file(fd):
    if stat.S_ISREG(os.fstat(fd).st_mode):
        raise OSError(errno.EIO, "injected file fsync failure")
    return _real_fsync(fd)
def _fail_on_directory(fd):
    if stat.S_ISDIR(os.fstat(fd).st_mode):
        raise OSError(errno.EINVAL, "injected dir fsync failure")
    return _real_fsync(fd)
# with patch("os.fsync", side_effect=_fail_on_directory): ...
```
Capture `_real_fsync` at module import, before patching. Patch the global `"os.fsync"` (persist.py does `import os` and calls `os.fsync(...)` as a module attribute, so the global patch is what it resolves). Likewise use `patch("os.replace", ...)` and `patch("tempfile.mkstemp", ...)` — never `common.persist.tempfile.*`, which does not exist pre-fix. That is fine for an isolated unit test.

## Release Pipeline Facts (verified this session)

| # | Fact | Evidence |
|---|------|----------|
| F1 | 1.7.3 never released. CHANGELOG `## [1.7.3] - Unreleased`; tags stop at `v1.7.2`; latest GH release is v1.7.2 (2026-09-06); all version fields `1.7.2`; `origin/main` = `f8c94e9` contains `8142929 fix: stage extraction output atomically… (1.7.3) (#112)` | `git tag`, `gh release list`, file reads [VERIFIED] |
| F2 | NAS runs `ghcr.io/thejuran/seedsyncarr:357` = CI run 357 = push to `main@f8c94e9`; RepoDigest `sha256:87ca66959391846d11fa1d0539601f18faba2294d880934041f8fc040a6d4e9f`; container started 2026-10-05; NAS arch `x86_64` | `ssh nas docker inspect`, `gh run list` [VERIFIED] |
| F3 | Tag pipeline `verify-release-metadata` requires: CHANGELOG `## [1.7.4]` heading; `release-notes.md` contains `v{{VERSION}}/CHANGELOG.md`; `package.json`, `src/angular/package.json`, `src/angular/package-lock.json` `.version` and `.packages[""].version` all = `1.7.4` | `scripts/verify-release-metadata.mjs` [VERIFIED] |
| F4 | On a `v*` tag: unit tests + lint + metadata → build staging → e2e amd64+arm64 → `publish-docker-image` **rebuilds** and pushes `:1.7.4`, then rebuilds and pushes `:latest` → `publish-github-release` (body = `release-notes.md` with `{{VERSION}}` substituted) → `publish-pypi` (stamps pyproject from tag). A push to `main` also publishes `:dev` and a staging `:<run_number>` | `.github/workflows/ci.yml`, `Makefile:52-77` [VERIFIED] |
| F5 | CI Python tests: `pytest -v -p no:cacheprovider`, no `--cov` → `fail_under=88` not enforced by CI; container `USER root` | `src/docker/test/python/Dockerfile:44-60` [VERIFIED] |
| F6 | Branch state: `main` is 11 commits ahead of `origin/main` (planning); `safety-patch-1.7.4` is 79 commits ahead of `main` | `git log` counts [VERIFIED] |

### Implications for the plan
- **CHANGELOG:** Fold or relabel. Recommended: retitle the existing `[1.7.3] - Unreleased` block's content into `## [1.7.4] - <date>` (adding the Phase 116/117/118 entries), with a one-line note that 1.7.3 was never tagged and its fixes ship in 1.7.4. Keeping a dangling "Unreleased 1.7.3" heading below a released 1.7.4 would confuse readers. This is wording and is at Claude's discretion per CONTEXT, but the owner should see it at the checkpoint.
- **release-notes.md:** Covers 1.7.3 content (staged extraction, deferred auto-delete re-arm) plus 1.7.4 (import ambiguity, transfer-state safety + the Stop change, durable state). For public users the "Should you update?" baseline is v1.7.2.
- **Rollback (D-06 correction, needs owner confirmation):** The public runbook should say "roll back to `:1.7.2`" (the last published release; `:1.7.3` does not exist). For the NAS specifically, the exact pre-upgrade image is `:357` @ `sha256:87ca6695…`. The D-06 reasoning (Phase 116's duplicate-basename skip; keep auto-delete off until imports are reconciled) applies equally to either target.
- **Owner checkpoint (D-02)** should present: the final diff summary, the GREEN evidence, the `verify:release-metadata` output, CHANGELOG/release-notes text, the rollback target choice, and the reminder that the tag push also publishes `:latest`, a GitHub Release and **PyPI** (irreversible version number).

## Smoke Test Recipe (D-01; Claude's discretion on mechanics)

Run **on the NAS**. It is the deploy arch (amd64), the pull pre-stages the exact digest, and the local Docker Desktop daemon is not running [VERIFIED]. Port 8801 is free [VERIFIED].

```bash
IMG=ghcr.io/thejuran/seedsyncarr:1.7.4
D=/volume1/docker/seedsync-smoke-1.7.4
ssh nas "sudo /usr/local/bin/docker pull $IMG && sudo /usr/local/bin/docker image inspect $IMG --format '{{json .RepoDigests}}'"
ssh nas "mkdir -p $D && sudo /usr/local/bin/docker run -d --name seedsyncarr-smoke --label wud.watch=false \
  -e PUID=1026 -e PGID=100 -p 8801:8800 -v $D:/config $IMG"
# 1 startup + transfer status: JSON with server/controller keys (server.up may be false: default config is incomplete → controller not started; acceptable for smoke)
ssh nas "curl -fsS -m 5 http://localhost:8801/server/status"
# 2 settings persistence
ssh nas "curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{\"section\":\"sonarr\",\"key\":\"sonarr_url\",\"value\":\"http://smoke-test.invalid:8989\"}' http://localhost:8801/server/config/set"
# wait > 30s (persist interval) OR rely on restart (shutdown path calls persist())
ssh nas "sudo /usr/local/bin/docker restart seedsyncarr-smoke"   # 3 restart → SIGTERM → persist()
ssh nas "grep sonarr_url $D/settings.cfg; ls -la $D; ls -a $D | grep -c '\.tmp$' || true"   # value present, -rw-------, zero .tmp
ssh nas "curl -fsS -m 5 http://localhost:8801/server/config/get | grep -o smoke-test.invalid"  # survives restart
# cleanup
ssh nas "sudo /usr/local/bin/docker rm -f seedsyncarr-smoke && rm -rf $D"
```
Notes: the scratch dir is created by jule1651, and the entrypoint chowns `/config` to PUID:PGID (`entrypoint.sh`). `rm -rf` of files inside may need the same uid, which is fine since PUID=1026=jule1651 [ASSUMED uid mapping; verify with `id` on the NAS]. Never mount production `/volume1/docker/seedsync` or `/downloads` into the smoke container.

## NAS Deploy Recipe (D-03)

```bash
# 0 backup (D-06) — timestamped, cannot collide with <name>.<N>.bak
ssh nas 'cd /volume1/docker/seedsync && TS=$(date +%Y%m%d-%H%M) && for f in settings.cfg controller.persist autoqueue.persist; do cp -p $f $f.pre-1.7.4-$TS; done && ls -la'
# 1 pin compose (currently line 78: image: ghcr.io/thejuran/seedsyncarr:357)
ssh nas "sed -i 's|ghcr.io/thejuran/seedsyncarr:357|ghcr.io/thejuran/seedsyncarr:1.7.4|' /volume1/docker/docker-compose.yml && grep -n 'seedsyncarr:' /volume1/docker/docker-compose.yml"
# 2 deploy
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose pull seedsyncarr && sudo /usr/local/bin/docker compose up -d seedsyncarr'
# 3 verify same digest as smoke, startup, config loading
ssh nas "sudo /usr/local/bin/docker inspect seedsyncarr --format '{{.Config.Image}} {{.Image}} {{.State.Status}}'; sudo /usr/local/bin/docker image inspect ghcr.io/thejuran/seedsyncarr:1.7.4 --format '{{json .RepoDigests}}'"
ssh nas "tail -60 /volume1/docker/seedsync/log/seedsyncarr.log"   # no 'Backing up settings.cfg' (would mean config failed to load)
# 4 scanner recovery gate (repeat until true)
ssh nas "curl -s -m 5 http://localhost:8800/server/status"   # latest_remote_scan_failed=false AND latest_remote_scan_time > deploy time
# 5 persist files after ≥ 30s: still -rw------- jule1651, no '+', no .tmp
ssh nas 'ls -la /volume1/docker/seedsync/'
```
`sed -i` on a file that wud's container also bind-mounts `rw`: sed writes a new inode, and wud's single-file bind mount keeps pointing at the **old** inode, which silently decouples wud from the compose file [ASSUMED: Docker single-file bind-mount semantics]. Prefer an in-place edit that keeps the inode (e.g. `sed ... > tmp && cat tmp > docker-compose.yml`), or flag it. The memory note shows earlier deploys edited this file, so check `ls -i` before and after.

**wud side effect to flag (D-03):** wud's dockercompose trigger is live (`DRYRUN=false`). With `wud.watch.digest=true` on a semver tag, wud tracks digest changes of `:1.7.4` (stable unless re-pushed) and newer semver tags. Whether it treats numeric staging tags such as `:363` as "newer" than `1.7.4` is unverified [ASSUMED risk]. Recommend the owner consider adding `wud.tag.include=^\d+\.\d+\.\d+$` on the seedsyncarr service; this is a product/ops decision, so raise it at the checkpoint rather than doing it unilaterally.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `open(path,"w")` + write + chmod | temp-in-same-dir + fsync + `os.replace` + dir fsync | Crash/error can no longer truncate state; brief world-readable window (between create and chmod) also eliminated |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `os.replace` doc wording (atomic on success, same FS) | Standard Stack | Low — POSIX `rename(2)` semantics are well established |
| A2 | `atomicwrites` is archived/unmaintained | Alternatives | None — not recommended either way |
| A3 | Compose 2.20.1 accepts `image: repo:tag@sha256:…` | Pitfall 9 | Low — optional hardening only |
| A4 | PUID 1026 = jule1651 on NAS | Smoke recipe | Low — cleanup may need sudo-docker `rm` |
| A5 | `sed -i` on the wud-mounted compose file breaks wud's bind mount (inode change) | Deploy recipe | Medium — wud could act on a stale compose copy |
| A6 | wud may treat numeric staging tags as newer than `1.7.4` | Deploy recipe | Medium — the NAS could silently drift off the release tag |
| A7 | Synology ACL inheritance won't add ACL entries to mkstemp-created files (current files show no `+`) | Runtime State | Low — explicit `fchmod 0600` plus the post-deploy `ls -la` check catch it |
| A8 | btrfs fsync latency under heavy download writes is negligible for 3 small files/30s | Pattern 1 | Low — persist runs on the main thread; a stall delays the loop briefly |

## Open Questions (RESOLVED — routed to Plan 118-04 owner checkpoint)

Each item below is presented to the owner as a decision item in the Plan 118-04 Task 1 `checkpoint:decision` packet, with the recommendation shown. None blocks planning or execution of Plans 118-01..03.

1. **Rollback target wording (D-06 says `:1.7.3`, which does not exist).** → checkpoint item **(a)**
   - Known: the last published release is v1.7.2; the NAS runs staging `:357` (1.7.3 code).
   - Recommendation: public runbook → `:1.7.2`; NAS-specific note → `:357@sha256:87ca6695…`. Confirm at the D-02 checkpoint.
2. **CHANGELOG handling of the unreleased `[1.7.3]` block.** → checkpoint item **(b)**. Recommendation: fold it into `[1.7.4]` with a "1.7.3 was not tagged" note. Owner sees it at the checkpoint.
3. **Coverage gate.** → checkpoint item **(c)**. CI does not enforce `fail_under`. Recommendation: run `poetry run pytest --cov` on host part 1 for information only; do not block on a number CI never enforced unless the owner wants it.
4. **wud tag filter.** → checkpoint item **(d)**. Raise at the checkpoint (A6); recommendation is label `wud.tag.include=^\d+\.\d+\.\d+$` on the seedsyncarr service when deploying in 118-05.
5. **Compose-file edit method on the NAS.** → checkpoint item **(e)**. wud bind-mounts the compose file rw; `sed -i` replaces the inode (A5). Recommendation: edit in place preserving the inode and verify `ls -i` before/after.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Poetry venv Python | host tests | ✓ | 3.12.12 (`/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python`) | — |
| ruff (local) | lint gate | ✓ | 0.15.9 (CI pins 0.15.22) | `uvx ruff@0.15.22` |
| Node/npm | `verify:release-metadata` | ✓ (assumed; used by repo scripts) | — | CI job enforces it anyway |
| `gh` CLI | tag/CI/release monitoring | ✓ (authenticated; lacks `read:packages`) | — | Use `docker buildx imagetools inspect` / NAS pull for digests |
| Local Docker daemon | local smoke | ✗ (Docker.app installed, daemon not running) | — | Smoke on NAS (recommended anyway) |
| NAS SSH + sudo docker | smoke + deploy | ✓ | compose 2.20.1 | — |
| curl on NAS | smoke/health | ✓ `/usr/bin/curl` | — | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pytest-timeout 60s per test, `src/python/pyproject.toml:69-72`); tests are `unittest.TestCase` classes |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_common/test_persist.py tests/unittests/test_common/test_config.py tests/unittests/test_seedsyncarr.py -q -p no:cacheprovider` |
| Full suite command | Host part 1: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py`; host part 2: the four files individually under `perl -e 'alarm 60; exec @ARGV'` (baseline 21 failed / 3 errors, must be unchanged); authority: CI `unittests-python` (`make run-tests-python`) |
| Lint | `poetry run ruff check src/python/` **and** `uvx ruff@0.15.22 check src/python/` (whole tree) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERSIST-01 | Serialization failure → original intact, no temp, raises | unit (RED) | `pytest tests/unittests/test_common/test_persist.py -q -k serialization` | ✅ file exists; tests ❌ Wave 0 |
| PERSIST-01 | Write failure (surrogate) → same | unit (RED) | `-k write_failure` | ❌ Wave 0 |
| PERSIST-01 | File fsync failure → same | unit (RED) | `-k file_fsync` | ❌ Wave 0 |
| PERSIST-01 | Replace failure → same | unit (RED) | `-k replace_failure` | ❌ Wave 0 |
| PERSIST-01 | Temp-creation failure → same | unit (RED) | `-k temp_creation` | ❌ Wave 0 |
| PERSIST-01 | Failure with no pre-existing target → dir empty | unit | `-k no_existing_target` | ❌ Wave 0 |
| PERSIST-01 | Interrupt (`ServiceExit`) mid-write cleans up, original intact | unit (new-contract) | `-k interrupt` | ❌ Wave 0 |
| PERSIST-02 | Success → content + `0600` + no `.tmp` | unit (preservation + new) | existing `test_to_file_*` + `-k no_temp_after_success` | partial ✅ |
| PERSIST-02 | Dir fsync failure → committed, logged on `seedsyncarr.Persist`, no raise | unit (RED) | `-k directory_fsync` | ❌ Wave 0 |
| PERSIST-02 | Temp created in target dir | unit (new-contract) | `-k same_directory` | ❌ Wave 0 |
| PERSIST-01/02 | Three real persist types round-trip via new `to_file` | unit (preservation) | ControllerPersist/AutoQueuePersist inherit `to_file` unmodified from `Persist` (no subclass override), so the base-class RED/GREEN tests in `test_persist.py` cover all three file types; `Config.to_file` is additionally exercised end-to-end by `test_config.py::test_to_file` and the `test_seedsyncarr.py` re-encrypt tests | ✅ |
| REL-01 g1 | All 116 (8) + 117 (26) + 118 RED regressions pass on release SHA | regression | one `pytest -v -k "<names>"` over the listed files; evidence → `118-REL01-EVIDENCE.md` | ✅ (116/117 RED already SHA-pinned) |
| REL-01 g2 | Full suite + whole-tree ruff | suite | above; CI green on the merge/tag commit | ✅ |
| REL-01 g3 | Image smoke: startup, status, settings persist, restart | manual-scripted | Smoke Test Recipe | n/a |
| REL-01 g4 | NAS `:1.7.4` same digest, config loads, clean scan after any error | manual-scripted | NAS Deploy Recipe steps 3-5 | n/a |

### Sampling Rate
- **Per task commit:** quick run + `poetry run ruff check src/python/`
- **Per wave merge:** host part 1 + ruff (both versions)
- **Phase gate:** CI green on the tag commit (all jobs, including e2e amd64+arm64 and metadata), smoke recipe passing, NAS gates 3-5

### Wave 0 Gaps
- [ ] RED tests in `src/python/tests/unittests/test_common/test_persist.py` (new class, e.g. `TestPersistAtomicWrite`), committed **before** the fix; RED run recorded against the pre-fix SHA (`git diff --stat <sha> -- src/python/common ':!src/python/tests'` empty) in `118-REL01-EVIDENCE.md`
- No framework install needed

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3/V4 | no | — |
| V5 Input Validation | no (no new input surface) | — |
| V6 Cryptography | indirect | `Config.to_str` encrypts secrets before write; ordering fix ensures a failed encrypt never truncates `settings.cfg` |
| V8 Data Protection | yes | File created `0600` from the start (mkstemp + fchmod), which removes the old create-then-chmod window where `settings.cfg` (possibly with plaintext secrets when encryption is off) was briefly umask-readable |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| Symlink/temp-name race in a shared dir | Tampering | `mkstemp` `O_EXCL` + random name |
| Secret leakage via logs | Info disclosure | Log path + errno only, never `content` |
| Smoke/deploy commands leak credentials | Info disclosure | Never `docker top` the container (lftp args include the seedbox password); don't paste config contents |

## Project Constraints (from CLAUDE.md)

No project `./CLAUDE.md`. Global directives that apply:
- Never log sensitive data (settings content can contain secrets) → log paths/errnos only.
- Resources released on every path → fd/temp cleanup in `finally`/`except BaseException`.
- Don't swallow exceptions silently → dir-fsync and unlink failures are logged.
- NAS docker only via `sudo /usr/local/bin/docker …` / `sudo /usr/local/bin/docker compose …`.
- Owner is product-side: the D-02 checkpoint should frame choices (rollback target, CHANGELOG fold, wud filter) by user impact and risk, not by code.

## Sources

### Primary (HIGH)
- Codebase: `src/python/common/persist.py`, `seedsyncarr.py` (callers, logger setup, signal, backup naming), `common/config.py:496`, `web/web_app.py`, `web/handler/config.py`, `.github/workflows/ci.yml`, `Makefile`, `scripts/verify-release-metadata.mjs`, `src/docker/test/python/Dockerfile`, `src/docker/build/docker-image/{Dockerfile,entrypoint.sh}`
- `.planning/phases/116-import-safety/116-REL01-EVIDENCE.md`, `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md`, `117-VALIDATION.md`
- docs.python.org/3.11/library/tempfile.html#tempfile.mkstemp, docs.python.org/3.11/library/os.html (fsync, fchmod)
- Live NAS inspection (compose, container, image digest, config dir, wud env/logs, `/server/status`), `gh run list`, `gh release list`, `git` refs

### Tertiary (LOW)
- wud tag-comparison behavior for numeric tags; bind-mount inode behavior (A5, A6)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (stdlib, behavior probed locally)
- Architecture/failure contract: HIGH (single write path verified by grep; RED reasons probed)
- Release pipeline: HIGH for facts F1-F6 (verified); MEDIUM for wud interactions

**Research date:** 2026-10-08
**Valid until:** 2026-10-22 (NAS/compose state and open dependabot PRs move quickly; re-check `docker inspect seedsyncarr` and `git log origin/main` at execution start)
