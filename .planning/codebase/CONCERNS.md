# Codebase Concerns

**Analysis Date:** 2026-06-02

This audit follows the v1.3.0 release (Backend Architecture Refactor + Test Infra). The codebase is unusually clean and security-hardened for its size: almost no `TODO`/`FIXME`/`HACK` markers survive, all `except Exception` blocks are deliberate log-and-reraise or queue-and-reraise patterns, secrets are Fernet-encrypted at rest, all shell-bound paths are `shlex.quote`-escaped, and the web layer ships Bearer-token auth, HMAC webhook verification, CSP/security headers, rate limiting, and constant-time comparisons. The concerns below are therefore mostly residual edge-cases, operational/deployment gaps, and a handful of latent fragilities rather than active defects.

## Tech Debt

**Deferred shutdown sequencing in main loop:**
- Issue: The main loop relies on a fixed `time.sleep(MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)` to let child jobs finish setup before termination, rather than a deterministic readiness signal. The in-code note states "There might be a better way to ensure that job setup has completed, but this will do for now".
- Files: `src/python/seedsyncarr.py:197-205` (shutdown sleep), `src/python/seedsyncarr.py:200-203` (the note)
- Impact: On fast shutdown (or shutdown immediately after start), child processes/threads may be killed mid-setup, leaving lingering threads. Low frequency in practice (requires shutdown within the setup window).
- Fix approach: Replace the sleep with an explicit "setup complete" `threading.Event` per job that `terminate()` waits on (bounded by a timeout).

**Legacy config-directory fallback:**
- Issue: Startup silently falls back to `~/.seedsync` (the pre-fork SeedSync directory) when the configured `--config_dir` is absent.
- Files: `src/python/seedsyncarr.py:266-272`
- Impact: A typo'd or unmounted config volume can cause the app to load a stale legacy config instead of failing loudly, producing confusing "why is my config wrong" behavior. The fallback is a one-time migration aid that has outlived its purpose for fresh installs.
- Fix approach: Gate the fallback behind an explicit opt-in flag or emit a prominent startup warning (already logged at WARNING — consider promoting to a one-time banner) and plan removal in a future major version.

**`AutoQueue` documents a single-thread assumption inline:**
- Issue: `AutoQueue` is documented as needing no synchronization "for now" because it runs in the Controller thread.
- Files: `src/python/controller/auto_queue.py:154` (and the class docstring)
- Impact: The "for now" caveat is a latent coupling: any future change that calls `AutoQueue` from another thread (e.g., a webhook fast-path) would silently introduce a race. Not a current defect.
- Fix approach: Either assert the calling thread identity in debug builds, or document the invariant as a hard contract rather than a temporary state.

**Untracked operational artifacts not in `.gitignore`:**
- Issue: `.orchestrator.json` and `.playwright-mcp/` are present in the working tree, untracked, and NOT matched by `.gitignore` (`git check-ignore` returns non-zero for both).
- Files: `/.orchestrator.json`, `/.playwright-mcp/`, `/.gitignore`
- Impact: Risk of accidentally committing tooling/run artifacts. `.DS_Store`, `.aidesigner/*`, `.bg-shell/`, and `.turingmind/` are already ignored; these two slipped through.
- Fix approach: Add `.orchestrator.json` and `.playwright-mcp/` to `.gitignore`.

## Known Bugs

No active functional bugs were identified in the production code paths during this audit. Historical bug fixes (BUG-01 confirm-modal XSS, BUG-02 webhook_require_secret, BUG-03 auto-delete shutdown race, WR-02 imported-children TOCTOU) are documented inline and have regression tests. The items below are latent edge-cases, not confirmed bugs.

**`StreamQueue.put` drop-oldest is not atomic under concurrent producers:**
- Symptoms: Under multiple simultaneous producer threads hitting a full queue, the get-then-put "make room" sequence can interleave such that the second `put(block=False)` still raises `Full`, and the event is silently dropped (counted, but lost).
- Files: `src/python/web/utils.py:33-63`
- Trigger: Sustained overflow (slow/disconnected SSE client) with >1 producer thread feeding the same `StreamQueue` subclass concurrently.
- Workaround: Drops are bounded, counted, and logged every 100 (`__dropped_count`), and the queue is capped at `DEFAULT_QUEUE_MAXSIZE = 1000`, so memory is safe — the only consequence is occasional extra event loss beyond the intended single drop. Wrapping the get+put pair in a `Lock` would make it strictly atomic.

## Security Considerations

**Auth and Host validation are opt-in (backward-compatible defaults):**
- Risk: When `api_token` is empty, ALL `/server/*` endpoints are unauthenticated (`bottle.request.auth_valid = True`), and Host-header validation only runs when `allowed_hostname` is configured. A default deployment exposed beyond localhost has no API auth and no DNS-rebinding protection.
- Files: `src/python/web/web_app.py:97-126` (Host + token gates), `src/python/web/web_app.py:122-126` (empty-token allow-all)
- Current mitigation: Token comparison uses `hmac.compare_digest` (constant-time); the api-token meta tag is HTML-escaped (`src/python/web/web_app.py:222`); CSP, `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff` are always set; SSE and `/server/status` are intentionally auth-exempt with documented rationale.
- Recommendations: Document prominently that `api_token` + `allowed_hostname` SHOULD be set for any non-localhost exposure; consider warning at startup when the server binds to a non-loopback interface with no token configured.

**Webhook HMAC verification is skipped when no secret is set:**
- Risk: With `webhook_secret` empty and `webhook_require_secret` off (the default), `/server/webhook/{sonarr,radarr}` accepts unauthenticated POSTs. An attacker who can reach the endpoint can enqueue arbitrary import titles.
- Files: `src/python/web/handler/webhook.py:83-86` (skip path), `src/python/web/handler/webhook.py:43-62` (fail-closed guard)
- Current mitigation: Blast radius is small — enqueued titles are matched case-insensitively against the EXISTING model (`webhook_manager.process` only acts on names already in the scan), so an unknown title is a no-op. Payload is capped at 1 MB (`_WEBHOOK_MAX_BODY_BYTES`), rate-limited to 60/60s per route, and `webhook_require_secret=True` makes the endpoint fail-closed (503) when no secret is set. HMAC uses `hmac.compare_digest`.
- Recommendations: Recommend enabling `webhook_require_secret` in docs; the no-op-on-unknown-title behavior already prevents path traversal or arbitrary deletion via this vector.

**Remote command execution surface (lftp / ssh / scp):**
- Risk: The app spawns `lftp`, `ssh`, `scp`, and runs remote `rm -rf`, `df`, `md5sum`, and the scan script on the remote host. All take user-influenced paths/filenames.
- Files: `src/python/lftp/lftp.py:315-342` (queue command), `src/python/ssh/sshcp.py:159-208` (shell/copy), `src/python/controller/scan/remote_scanner.py:89-91,138,155` (remote shell), `src/python/controller/delete/delete_process.py:44-47` (remote `rm -rf`)
- Current mitigation: This is handled carefully. `pexpect.spawn(argv)` is used (no `shell=True`, no string interpolation into a local shell); remote-shell arguments are `shlex.quote`-escaped before being sent to the remote shell; `lftp.queue` rejects `\n`/`\r`/`\x00` and escapes quotes; `Sshcp` uses `StrictHostKeyChecking=accept-new` and explicitly detects/raises on changed host keys (MITM). Filenames reaching delete originate from the filesystem scan, not raw user input.
- Recommendations: Maintain the invariant that any NEW shell-bound path passes through `shlex.quote` and originates from the model, not directly from webhook/HTTP input. This is the single most important convention to preserve in future phases.

**Secret-at-rest encryption has a documented false-positive / keyfile-loss path:**
- Risk: `is_ciphertext()` is a best-effort discriminator; a user-chosen plaintext beginning with `gAAAAA` and ≥100 valid base64 chars is a false positive, and a missing keyfile alongside ciphertext values produces decrypt errors at startup.
- Files: `src/python/common/encryption.py:96-121` (discriminator), `src/python/common/config.py:449-469` (keyfile-missing guard, `_decrypt_errors`)
- Current mitigation: Keyfile is created atomically at `0600` via `O_EXCL` and re-tightened on every load; decrypt failures are collected into `_decrypt_errors` and surfaced as startup warnings rather than crashing; PyCA exceptions never escape the module boundary.
- Recommendations: None urgent — the design already fails safe and warns. Note for operators: losing the keyfile means stored secrets must be re-entered.

## Performance Bottlenecks

**Single-threaded model lock serializes the controller hot path:**
- Problem: All model reads/writes funnel through `__model_lock`. Subprocess-spawning operations (`delete_local`/`delete_remote`) are deliberately run OUTSIDE the lock to avoid starving model updates.
- Files: `src/python/controller/controller.py:101` (lock), `src/python/controller/controller.py:610-716` (lock-release-before-subprocess discipline), `src/python/controller/command_processor.py`
- Cause: Holding the lock across a blocking subprocess would stall all scan/model updates. This is correctly handled today, but it is a structural constraint: every future long-running operation MUST release the lock first.
- Improvement path: None needed now; the constraint is documented in code. Flag for any future feature that touches `__model_lock`.

**SSE stream is a busy-poll loop:**
- Problem: `__web_stream` polls all handlers every 10 ms (data available) or 100 ms (idle) and sends a 15 s heartbeat, per connection.
- Files: `src/python/web/web_app.py:248-298`
- Cause: Pull-based handler model rather than condition-variable wakeups.
- Improvement path: Acceptable for the expected small number of concurrent browser clients. If client count grows, switch to event-driven wakeups (queue `Condition`) to cut idle CPU.

**Remote scan re-installs/re-hashes the scan script each cycle:**
- Problem: `RemoteScanner` computes a local md5sum and compares against a remote `md5sum` over SSH to decide whether to re-upload `scan_fs`.
- Files: `src/python/controller/scan/remote_scanner.py:138-185`
- Cause: Correctness-over-speed: ensures the remote script matches the bundled one. Each remote scan cycle pays an extra SSH round-trip for `df` and (when checking) `md5sum`.
- Improvement path: Cache the "remote script verified this session" state to skip the md5sum round-trip after the first successful install per connection.

## Fragile Areas

**`lftp` interaction via pexpect pattern-matching:**
- Files: `src/python/lftp/lftp.py`, `src/python/lftp/job_status_parser.py` (752 lines), `src/python/ssh/sshcp.py`
- Why fragile: Behavior depends on matching lftp/ssh human-readable output via regex and `expect` patterns (`__expect_pattern`, `__detect_errors_from_output`, the hardcoded error-string list, and SSH prompt strings like `'password: '`, `'No route to host'`). An lftp/openssh version that changes wording or prompt format can silently break status parsing or error detection.
- Safe modification: Treat the error-string lists (`lftp.py:155-160`, `sshcp.py:77-118`) and the status parser as a versioned contract; add an integration test against the target lftp/ssh versions when bumping the base image.
- Test coverage: Well covered — `test_job_status_parser.py` (1539 lines), `test_job_status_parser_components.py` (516 lines), plus integration tests in `src/python/tests/integration/test_lftp/`. The integration tests require a real lftp+sftp service (run via Docker), so they do not run in plain unit-test mode.

**Auto-delete Timer-thread orchestration:**
- Files: `src/python/controller/controller.py:573-717` (schedule + execute), `src/python/controller/auto_delete_manager.py`
- Why fragile: Correctness depends on a carefully documented lock ordering (`__model_lock` THEN `__auto_delete_lock`; `exit()` takes only `__auto_delete_lock`) and a `__shutdown_event` checked under lock to defeat a shutdown race (BUG-03) and a webhook TOCTOU (WR-02). Timers are daemon threads fired after a delay. The reasoning is correct but dense; an edit that reorders the locks or moves the shutdown check would reintroduce a deadlock or a delete-after-shutdown bug.
- Safe modification: Preserve the lock-ordering comments verbatim when touching this code; never acquire `__model_lock` inside code already holding `__auto_delete_lock`.
- Test coverage: `test_auto_delete.py` (935 lines) covers the guards; keep the BFS pack-guard and coverage-guard tests green.

**Filesystem delete operations:**
- Files: `src/python/controller/delete/delete_process.py:15-24` (local `os.remove`/`shutil.rmtree`), `:42-47` (remote `rm -rf`)
- Why fragile: These permanently destroy user data. Local delete uses `shutil.rmtree(..., ignore_errors=True)`, which swallows partial-failure errors silently. Safety today rests entirely on `file_name` originating from the model (validated against the scan) and on `os.path.join` + `shlex.quote`.
- Safe modification: Never wire a raw HTTP/webhook string into these constructors; always resolve through the model first (as the controller does at `controller.py:732`, `controller.py:652`). Consider replacing `ignore_errors=True` with explicit error handling so a failed local delete is logged rather than silently passed.
- Test coverage: Covered by controller delete tests; the `ignore_errors=True` swallow path is not asserted.

## Scaling Limits

**In-memory model and bounded collections:**
- Current capacity: Downloaded/extracted file tracking uses `BoundedOrderedSet` (eviction-based) and SSE queues are capped at 1000 events. `MemoryMonitor` logs structure sizes and eviction counts every 5 minutes.
- Files: `src/python/common/bounded_ordered_set.py`, `src/python/web/utils.py:8`, `src/python/controller/memory_monitor.py`
- Limit: The live model itself is unbounded in memory (one entry per remote/local file). Very large remote trees (hundreds of thousands of entries) would grow RSS linearly and increase per-cycle model-diff cost.
- Scaling path: The eviction bounds and monitor are already in place for the persisted name-sets; if the live model becomes a problem, paginate or prune the model representation. Monitor `model_files` growth trend via `MemoryMonitor.detect_growth_trend`.

## Dependencies at Risk

**Native/CLI dependencies coupled to the runtime image:**
- Risk: The app requires `/usr/bin/lftp` (hardcoded path in `lftp.py:62`), `ssh`/`scp` binaries, and `patool` extraction backends present in the container. These are environment dependencies, not pinned Python packages.
- Impact: An image rebuild that changes the lftp/openssh version can break output parsing (see Fragile Areas). The hardcoded `/usr/bin/lftp` path breaks if lftp moves.
- Migration plan: Pin the base-image lftp/openssh versions; add a startup check that `lftp` exists at the expected path.

**Python and Angular major-version posture:**
- Risk: Python is constrained to `>=3.11,<3.13`; Angular is on v21 (`@angular/core ^21.2.14`) with TypeScript `~6.0.3`. These are current but move fast.
- Files: `src/python/pyproject.toml:10` (Python range), `src/angular/package.json:19,57`
- Impact: Dependency ceilings (`cryptography>=44,<47`) are sensibly bounded; the Angular major will require periodic migration effort.
- Migration plan: Routine — track Angular LTS cadence; widen the Python upper bound once 3.13 is validated against the lftp/pexpect stack.

## Missing Critical Features

**NAS deploy build environment blocked (known, deferred):**
- Problem: The local NAS deployment build is blocked by a QEMU/cross-build issue. CI multi-arch builds (amd64 + arm64) succeed because GitHub-hosted runners provide working QEMU + buildx and a native arm64 runner (`ubuntu-24.04-arm`), but the maintainer's local NAS build path cannot produce the deploy image.
- Files (CI that DOES work, for contrast): `.github/workflows/ci.yml:113-150` (`build-docker-image` with `setup-qemu-action`), `.github/workflows/ci.yml:152-199` (multi-arch E2E matrix), `.github/workflows/ci.yml:224-275` (`publish-docker-image` multi-arch)
- Blocks: Local/NAS image production for the maintainer's own deployment; does NOT block CI publish to GHCR or PyPI.
- Note: This is a deployment-environment limitation, not a code defect. The published images are produced by CI; the gap is reproducing that build locally on the NAS under QEMU.

## Test Coverage Gaps

**Coverage gate is solid but not 100%:**
- What's tested: `fail_under = 88` is enforced (`src/python/pyproject.toml:88`). 77 Python test files, 40 Angular spec files, 9 E2E specs. The hardened areas (encryption, webhook HMAC, confirm-modal XSS, auto-delete races, job-status parsing) all have dedicated, large test suites.
- Risk: The ~12% uncovered slice likely includes defensive/error branches (the `ignore_errors=True` delete path, some `except Exception` log-and-reraise arms, Windows-only `chmod` fallbacks).
- Priority: Low — the uncovered code is mostly defensive.

**Integration tests require external services and don't run in unit mode:**
- What's not tested in CI unit runs: Real lftp/sftp protocol behavior. `src/python/tests/integration/test_lftp/` and `test_controller/test_controller.py` (2373 lines) need a live SFTP/lftp service (Docker) and only run in the E2E/integration job.
- Files: `src/python/tests/integration/test_lftp/test_lftp.py`, `test_lftp_protocol.py`, `src/python/tests/integration/test_controller/test_controller.py`
- Risk: A change to lftp output parsing that passes unit tests (which use captured fixtures) could still break against a new lftp version; only the Dockerized integration/E2E job catches this.
- Priority: Medium — ensure the integration job runs on any lftp/openssh base-image bump.

**Silent-failure delete path not asserted:**
- What's not tested: That a failed local `shutil.rmtree` (currently `ignore_errors=True`) is detected or logged.
- Files: `src/python/controller/delete/delete_process.py:24`
- Risk: A delete that partially fails leaves orphaned files with no signal to the user or logs.
- Priority: Low/Medium — pair with the "replace `ignore_errors=True`" fix in Fragile Areas.

---

*Concerns audit: 2026-06-02*
