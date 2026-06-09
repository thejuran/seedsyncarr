# Codebase Concerns

**Analysis Date:** 2026-06-09

This audit follows the v1.4.0 launch-hardening milestone (completed 2026-06-03) and the 2026-06-08 production incident (`/downloads` write-permission failure on the NAS deployment). The v1.4.0 milestone resolved most previously folded findings: `/server/config/set` is now POST-only with a JSON body (`src/python/web/handler/config.py:25-26`), local delete failures are logged instead of swallowed (`src/python/controller/delete/delete_process.py:24-30`), `AppProcess` is spawn-picklable via `__getstate__`/`__setstate__` (`src/python/common/app_process.py:124-150`), startup security warnings are state-accurate (`src/python/seedsyncarr.py:375-400`), the legacy-fallback warning is deferred until the logger exists (`src/python/seedsyncarr.py:268-277`), and `.gitignore` covers tooling artifacts. A PUID/PGID-honoring entrypoint now ships (`src/docker/build/docker-image/entrypoint.sh`). The codebase remains clean — zero TODO/FIXME markers in production source, ruff/Semgrep/gitleaks all green per the Phase 110 hostile-reader pass. Remaining concerns are deferred robustness items, deployment fragilities exposed by the June 8 incident, and latent edge-cases.

## Tech Debt

**Deferred shutdown sequencing in main loop (DEFER-SHUTDOWN):**
- Issue: Shutdown relies on a fixed `time.sleep(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` to let child jobs finish setup before termination. The in-code note says "There might be a better way to ensure that job setup has completed, but this will do for now."
- Files: `src/python/seedsyncarr.py:199-211`
- Impact: Shutdown immediately after start can kill child processes mid-setup, leaving lingering threads. Low frequency in practice. Formally deferred at v1.4.0 close (tracked as DEFER-SHUTDOWN in `.planning/milestones/v1.4.0-REQUIREMENTS.md`).
- Fix approach: Replace the sleep with a per-job "setup complete" `threading.Event` that `terminate()` waits on with a bounded timeout.

**Legacy config-directory fallback still active:**
- Issue: Startup falls back to `~/.seedsync` (pre-fork SeedSync directory) when the configured `--config_dir` is absent. The warning is now reliably surfaced post-logger-creation (`legacy_fallback_warning` return value), but the fallback mechanism itself remains.
- Files: `src/python/seedsyncarr.py:268-277`
- Impact: A typo'd or unmounted config volume loads a stale legacy config instead of failing loudly. The migration aid has outlived its purpose for fresh installs.
- Fix approach: Gate behind an explicit opt-in flag and plan removal in a future major version.

**`AutoQueue` documents a single-thread assumption inline:**
- Issue: `AutoQueue` is documented as needing no synchronization "for now" because it runs only in the Controller thread.
- Files: `src/python/controller/auto_queue.py` (class docstring and inline note near line 154)
- Impact: Latent coupling — any future change that calls `AutoQueue` from another thread (e.g., a webhook fast-path) silently introduces a race. Not a current defect.
- Fix approach: Assert calling-thread identity in debug builds, or promote the invariant to a hard documented contract.

**`PYTHONWARNINGS` cgi filter pending upstream webob release (DEFER-WEBOB):**
- Issue: `src/docker/test/python/Dockerfile` carries `ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"` solely to suppress webob 1.8.x's stdlib `cgi` import warning. Blocked on upstream webob 2.0 (Pylons/webob PR #466).
- Files: `src/docker/test/python/Dockerfile`, `src/python/poetry.lock`, tracked in `.planning/todos/pending/2026-04-21-webob-cgi-upstream-unblock.md`
- Impact: Cosmetic; masks one warning class in the test image. Removal steps are documented in the todo.
- Fix approach: When webob ships without the `cgi` import — bump webob, regenerate lock, delete the ENV line, re-run `make run-tests-python`.

**Test-suite hardening backlog (DEFER-TESTHARDEN):**
- Issue: A deep review of the Python test suite (`.planning/backlog/TEST-HARDENING-REVIEW.md`, 2026-04-24) catalogs ~20 findings: two false-coverage tests (thread target invoked instead of passed at `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py:182`; assertion-less test at `tests/unittests/test_controller/test_lftp_manager.py:83-98`), temp files with plaintext test credentials left in `/tmp`, unused conftest fixtures duplicated by hand in 3+ files, ~4.5s of wall-clock sleeps per run, and 100+ name-mangled private-attribute accesses coupling tests to `Controller` internals.
- Files: `src/python/tests/` (see backlog doc for line-level detail)
- Impact: Inflated coverage confidence on two paths; minor CI hygiene/speed issues. No production risk.
- Fix approach: The backlog doc includes a 5-wave milestone structure; Waves 1-2 (false coverage + temp-file hygiene) are the high-value, low-risk slice.

## Known Bugs

No active functional bugs in production code paths. Historical fixes (BUG-01 confirm-modal XSS, BUG-02 `webhook_require_secret`, BUG-03 auto-delete shutdown race, WR-02 imported-children TOCTOU) are documented inline with regression tests. Items below are latent edge-cases.

**`StreamQueue.put` drop-oldest is not atomic under concurrent producers (DEFER-STREAMQUEUE):**
- Symptoms: With multiple producer threads hitting a full queue, the get-then-put "make room" sequence can interleave so the retry `put(block=False)` still raises `Full` and the event is silently dropped (counted, but lost).
- Files: `src/python/web/utils.py:33-63`
- Trigger: Sustained overflow (slow/disconnected SSE client) with >1 producer feeding the same `StreamQueue` concurrently.
- Workaround: Drops are bounded, counted, and logged every 100 (`__dropped_count`); queue capped at 1000 events, so memory is safe. Wrapping the get+put pair in a `Lock` makes it strictly atomic. Formally deferred at v1.4.0 close.

**Controller wedges under sustained local-write failure (observed 2026-06-08):**
- Symptoms: When LFTP cannot write the local destination for hours (June 8: `/downloads` turned read-only inside the container), the long-running controller wedged — queue commands returned 504 timeouts, scan activity stopped, and only a container restart recovered it.
- Files: `src/python/controller/controller.py`, `src/python/web/handler/controller.py:101-102` (504 path), `src/python/web/handler/controller.py:366-375` (bulk timeout path)
- Trigger: Persistent `mirror: Access failed` on every queue attempt over an extended period.
- Workaround: Restart the container. No self-recovery or watchdog exists for this failure mode. Documented in `.planning/debug/active-files-not-downloading.md` (resolved at the deployment layer; the wedge behavior itself was not root-caused).

## Security Considerations

**Auth and Host validation are opt-in (backward-compatible defaults):**
- Risk: With `api_token` empty, ALL `/server/*` endpoints are unauthenticated, and Host-header validation only runs when `allowed_hostname` is set. The app always binds `0.0.0.0`.
- Files: `src/python/web/web_app.py:97-126` (Host + token gates), `src/python/web/web_app_job.py:27` (bind address)
- Current mitigation: Token comparison uses `hmac.compare_digest`; api-token meta tag is HTML-escaped; CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` always set. Since v1.4.0, prominent `[SECURITY]` startup warnings fire for the no-token and bound-to-0.0.0.0 states (`src/python/seedsyncarr.py:388-400`).
- Recommendations: Defaults are documented; keep README/SECURITY.md guidance in sync with `_emit_startup_warnings` behavior.

**Webhook HMAC verification is skipped when no secret is set:**
- Risk: With `webhook_secret` empty and `webhook_require_secret` off (default), `/server/webhook/{sonarr,radarr}` accepts unauthenticated POSTs.
- Files: `src/python/web/handler/webhook.py:83-86` (skip path), `src/python/web/handler/webhook.py:43-62` (fail-closed 503 guard)
- Current mitigation: Small blast radius — enqueued titles only act on names already present in the scanned model (unknown title = no-op); 1 MB body cap; 60/60s rate limit per route; `webhook_require_secret=True` fails closed with 503 before reading the body; HMAC uses `hmac.compare_digest`. Startup warnings are state-accurate per the GUARD-02 matrix fix.
- Recommendations: Continue recommending `webhook_require_secret=True` in docs for any non-localnet exposure.

**Remote command execution surface (lftp / ssh / scp):**
- Risk: The app spawns `lftp`, `ssh`, `scp` and runs remote `rm -rf`, `df`, `md5sum`, and the scan script — all with user-influenced paths/filenames.
- Files: `src/python/lftp/lftp.py:315-342` (queue command), `src/python/ssh/sshcp.py:159-208` (shell/copy), `src/python/controller/scan/remote_scanner.py:89-91,138,155`, `src/python/controller/delete/delete_process.py:52-57` (remote `rm -rf`)
- Current mitigation: Handled carefully — `pexpect.spawn(argv)` (no `shell=True`); remote-shell args `shlex.quote`-escaped; `lftp.queue` rejects `\n`/`\r`/`\x00`; SSH uses `StrictHostKeyChecking=accept-new` with changed-key (MITM) detection; delete filenames originate from the filesystem scan, not raw HTTP input. Semgrep auto-rules report zero findings.
- Recommendations: Preserve the invariant that any NEW shell-bound path passes through `shlex.quote` and resolves through the model — never directly from webhook/HTTP input. This is the single most important convention in the codebase.

**Secret-at-rest encryption has a documented keyfile-loss / false-positive path:**
- Risk: `is_ciphertext()` is a best-effort discriminator (a plaintext starting with `gAAAAA` + ≥100 base64 chars is a false positive); a missing keyfile alongside ciphertext values produces decrypt errors at startup.
- Files: `src/python/common/encryption.py:96-121` (discriminator), `src/python/common/config.py:449-469` (keyfile-missing guard, `_decrypt_errors`)
- Current mitigation: Keyfile created atomically at `0600` via `O_EXCL` and re-tightened each load; decrypt failures collected and surfaced as startup warnings rather than crashing.
- Recommendations: None urgent — fails safe and warns. Operator note: losing the keyfile means re-entering stored secrets.

## Performance Bottlenecks

**Single-threaded model lock serializes the controller hot path:**
- Problem: All model reads/writes funnel through `__model_lock`. Subprocess-spawning operations (`delete_local`/`delete_remote`) deliberately run OUTSIDE the lock.
- Files: `src/python/controller/controller.py` (lock at ~line 101; lock-release-before-subprocess discipline in the delete paths)
- Cause: Holding the lock across a blocking subprocess would stall all scan/model updates. Correct today, but a structural constraint: every future long-running operation MUST release the lock first.
- Improvement path: None needed now; flag for any future feature touching `__model_lock`.

**Controller runs a ~1/sec process cycle while downloads are active:**
- Problem: `interval_ms_downloading_scan = 1000` drives a per-second scan/diff cycle whenever transfers are in flight; in-flight files emit `file_updated` events each cycle.
- Files: `src/python/controller/controller.py`, `src/python/controller/auto_queue.py:189-199` (cycle log, now debug-level to avoid INFO spam), `src/python/seedsyncarr.py:336-338` (interval defaults)
- Cause: Poll-based progress tracking. The June 8 debug session flagged the steady idle-adjacent cycling as an efficiency item worth a look (log spam half already fixed).
- Improvement path: Acceptable for current scale; if CPU becomes a concern, lengthen the downloading-scan interval adaptively when no sizes change.

**SSE stream is a busy-poll loop:**
- Problem: `__web_stream` polls all handlers every 10 ms (data available) or 100 ms (idle) per connection, plus a 15 s heartbeat.
- Files: `src/python/web/web_app.py:248-298`
- Cause: Pull-based handler model rather than condition-variable wakeups.
- Improvement path: Fine for a handful of browser clients; switch to event-driven wakeups if client count grows.

**Remote scan re-verifies the scan script each cycle:**
- Problem: `RemoteScanner` compares a local md5sum against a remote `md5sum` over SSH to decide whether to re-upload `scan_fs`, paying an extra SSH round-trip per cycle.
- Files: `src/python/controller/scan/remote_scanner.py:138-185`
- Cause: Correctness-over-speed.
- Improvement path: Cache "remote script verified this session" to skip the round-trip after first successful install per connection.

## Fragile Areas

**Deployment permissions: Synology ACLs can silently revoke `/downloads` write access:**
- Files: `src/docker/build/docker-image/entrypoint.sh` (PUID/PGID remap + non-recursive chown of `/config` and `/downloads`), `.planning/debug/active-files-not-downloading.md` (incident record)
- Why fragile: On 2026-06-08 the NAS share `/volume1/data/torrents` presented as `dr-xr-xr-x root:root` inside the container despite Docker reporting the mount RW and host POSIX bits being world-writable — Synology ACLs override POSIX bits. Result: every LFTP queue failed (`mirror: Access failed`), nothing downloaded, and the controller eventually wedged. Cause of the ACL flip was never established (suspected DSM reindex/backup service), so recurrence is possible. The chown in the entrypoint succeeded during the incident but did NOT restore write — a `chmod` was also required.
- Safe modification: The entrypoint chown is deliberately non-recursive (set `ENTRYPOINT_CHOWN_RECURSIVE=true` for a one-time deep fix) and tolerant of read-only bind mounts inside SSH home — preserve both behaviors when editing.
- Test coverage: None possible in CI (host-ACL dependent). See Missing Critical Features for the startup write-probe gap.

**`lftp` interaction via pexpect pattern-matching:**
- Files: `src/python/lftp/lftp.py` (hardcoded error-string list ~lines 155-160), `src/python/lftp/job_status_parser.py` (752 lines), `src/python/ssh/sshcp.py:77-118` (prompt/error strings)
- Why fragile: Behavior depends on regex/`expect` matching of lftp/ssh human-readable output (`'password: '`, `'No route to host'`, etc.). An lftp/openssh version that changes wording silently breaks status parsing or error detection.
- Safe modification: Treat the error-string lists and status parser as a versioned contract; run the Dockerized integration tests (`src/python/tests/integration/test_lftp/`) on any base-image lftp/openssh bump.
- Test coverage: Strong — `test_job_status_parser.py` (~1539 lines) plus protocol integration tests, but the integration tier requires a live lftp+sftp service (Docker) and does not run in plain unit mode.

**Auto-delete Timer-thread orchestration:**
- Files: `src/python/controller/controller.py` (schedule + execute, ~lines 573-717), `src/python/controller/auto_delete_manager.py`
- Why fragile: Correctness depends on documented lock ordering (`__model_lock` THEN `__auto_delete_lock`; `exit()` takes only `__auto_delete_lock`) and a `__shutdown_event` checked under lock to defeat the BUG-03 shutdown race and WR-02 TOCTOU. Daemon Timer threads fire after a delay. Reordering the locks or moving the shutdown check reintroduces a deadlock or delete-after-shutdown bug.
- Safe modification: Preserve the lock-ordering comments verbatim; never acquire `__model_lock` while holding `__auto_delete_lock`.
- Test coverage: `test_auto_delete.py` (~935 lines) covers the guards.

**Filesystem delete operations:**
- Files: `src/python/controller/delete/delete_process.py:15-30` (local `os.remove`/`shutil.rmtree` with logged `OSError`), `:52-57` (remote `rm -rf` via `shlex.quote`)
- Why fragile: Permanently destroys user data. Safety rests on `file_name` originating from the model (validated against the scan) plus `os.path.join` + `shlex.quote`. The former `ignore_errors=True` swallow was replaced in v1.4.0 with `logger.exception` on failure.
- Safe modification: Never wire a raw HTTP/webhook string into these constructors; always resolve through the model first (as `controller.py` does).
- Test coverage: Controller delete tests cover the happy path; the local-rmtree failure branch is logged but lightly asserted.

## Scaling Limits

**In-memory model and bounded collections:**
- Current capacity: Downloaded/extracted name-sets use `BoundedOrderedSet` (eviction-based); SSE queues capped at 1000 events; `MemoryMonitor` logs structure sizes and growth trends every 5 minutes.
- Files: `src/python/common/bounded_ordered_set.py`, `src/python/web/utils.py`, `src/python/controller/memory_monitor.py`
- Limit: The live model itself is unbounded — one entry per remote/local file. Very large remote trees (hundreds of thousands of entries) grow RSS linearly and increase per-cycle diff cost (amplified by the 1 s downloading-scan cadence).
- Scaling path: Monitor `model_files` via `MemoryMonitor.detect_growth_trend`; paginate or prune the model representation if it becomes a problem.

## Dependencies at Risk

**Native/CLI dependencies coupled to the runtime image:**
- Risk: Requires `/usr/bin/lftp` (hardcoded path in `src/python/lftp/lftp.py:62`), `ssh`/`scp` binaries, and `patool` extraction backends in the container — environment dependencies, not pinned Python packages.
- Impact: An image rebuild changing lftp/openssh versions can break output parsing (see Fragile Areas); the hardcoded path breaks if lftp moves.
- Migration plan: Pin base-image lftp/openssh versions; add a startup existence check for `lftp`.

**Python and Angular major-version posture:**
- Risk: Python constrained to `>=3.11,<3.13` (`src/python/pyproject.toml:10`); Angular on v22 (`@angular/core ^22.0.0`, `src/angular/package.json:19`) with TypeScript `~6.0.3` — current as of 2026-06-04 (all Dependabot PRs cleared, 0 open security alerts), but both move fast.
- Impact: `cryptography>=44,<47` is sensibly bounded; Angular majors require periodic migration effort (the v21→v22 bump needed strict-template TS fixes).
- Migration plan: Routine — track Angular LTS cadence; widen the Python ceiling once 3.13 is validated against the lftp/pexpect stack.

## Missing Critical Features

**No startup/runtime writability probe for `local_path`:**
- Problem: The application never verifies that `local_path` (`/downloads` in the container) is writable. When it is not (June 8 incident), the failure surfaces only as opaque LFTP `mirror: Access failed` errors, 504 queue timeouts, and ultimately a wedged controller — with no log line naming the actual cause. No `os.access`/write-probe exists anywhere in `src/python/`.
- Blocks: Fast diagnosis of the most likely real-world deployment failure (bind-mount permission mismatch on NAS hosts). A startup probe (`touch`/unlink in `local_path`) plus a periodic re-check with a clear `[DEPLOYMENT]` error would have turned a multi-hour debug session into a one-line log read.

**NAS deploy build environment blocked (known, deferred):**
- Problem: Local NAS image builds are blocked by a QEMU/cross-build issue. CI multi-arch builds (amd64 + arm64) succeed on GitHub runners.
- Files (working CI for contrast): `.github/workflows/ci.yml` (`build-docker-image`, multi-arch E2E matrix, `publish-docker-image`)
- Blocks: Maintainer's local image production only; does NOT block CI publish. Environment limitation, not a code defect (tracked Out of Scope in v1.4.0 REQUIREMENTS).

## Test Coverage Gaps

**Coverage gate is solid but not 100%:**
- What's tested: `fail_under = 88` enforced (`src/python/pyproject.toml:88`); 77 Python test files, 40 Angular spec files, 16 E2E spec/page files. Hardened areas (encryption, webhook HMAC, confirm-modal XSS, auto-delete races, job-status parsing) have dedicated large suites.
- Risk: The ~12% uncovered slice is mostly defensive/error branches (rmtree failure arm, log-and-reraise `except Exception` arms, platform fallbacks).
- Priority: Low.

**Integration tests require external services and don't run in unit mode:**
- What's not tested in unit runs: Real lftp/sftp protocol behavior. `src/python/tests/integration/test_lftp/` and `tests/integration/test_controller/test_controller.py` (~2400 lines) need a live SFTP/lftp service (Docker).
- Risk: A parsing change that passes unit tests (captured fixtures) could break against a new lftp version; only the Dockerized integration/E2E job catches it.
- Priority: Medium — ensure the integration job runs on any lftp/openssh base-image bump.

**Controller wedge / sustained-write-failure path untested:**
- What's not tested: Behavior when every LFTP queue attempt fails for an extended period (the June 8 wedge). No test simulates persistent local-write failure or asserts the controller stays responsive.
- Files: `src/python/controller/controller.py`, `src/python/web/handler/controller.py`
- Risk: Recurrence of the wedge would again require a manual restart with no alerting.
- Priority: Medium — pair with the writability-probe feature above.

**Known false-coverage tests (from test-hardening backlog):**
- What's not tested despite appearing covered: Extract-completion concurrency (`tests/unittests/test_controller/test_extract/test_extract_process.py:182` — thread target invoked, not passed) and rate-limit-skip behavior (`tests/unittests/test_controller/test_lftp_manager.py:83-98` — body is `pass`).
- Risk: Coverage metrics overstate confidence on these two paths.
- Priority: High within the test-hardening backlog (Wave 1, mechanical fixes).

---

*Concerns audit: 2026-06-09*

