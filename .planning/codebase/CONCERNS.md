# Codebase Concerns

**Analysis Date:** 2026-05-26

## Tech Debt

**Mock-model toggle hardcoded in production service:**
- Issue: `USE_MOCK_MODEL` private boolean lives as a class field in production code rather than as a build-time environment flag.
- Files: `src/angular/src/app/services/files/view-file.service.ts:71`, `src/angular/src/app/services/files/mock-model-files.ts`
- Impact: Toggling requires a code edit and rebuild. The mock dataset (`screenshot-model-files.ts`, `mock-model-files.ts`) is bundled into production output instead of being tree-shaken via environment branching.
- Fix approach: Move the toggle into `src/angular/src/environments/environment.ts` and import the flag from there. Use `fileReplacements` so production builds drop the mock data entirely.

**Mutable model state pattern leaks through controller:**
- Issue: `Controller` calls protected methods `_unfreeze()`, `_set_parent()`, `_replace_children()` on `ModelFile` (which is otherwise frozen/immutable). The "controller owns the freeze lifecycle" comment acknowledges this is intentional protected-API access.
- Files: `src/python/controller/controller.py:355-381`, `src/python/model/file.py:74-78`
- Impact: The freeze contract is fragile. A future contributor mutating a ModelFile outside the controller will silently break thread-safety assumptions documented in `model/file.py:17`.
- Fix approach: Replace the freeze/unfreeze pattern with a builder/factory (`ModelFile.with_import_status(status)` returns a new frozen copy). Eliminates protected-access calls and makes immutability a true invariant.

**`InnerConfig` global property metadata map:**
- Issue: `InnerConfig.__prop_addon_map` is a class-level `OrderedDict` shared across all config subclasses (General, Lftp, Controller, etc.). The TODO-style comment in code asks "Is there a way for each concrete class to do this separately?"
- Files: `src/python/common/config.py:137-145`
- Impact: Property ordering across sections relies on import order and class definition order. Test isolation is impossible without monkeypatching the class attribute.
- Fix approach: Move metadata into a per-class `__init_subclass__` hook, or convert to a class-level dict keyed by `(cls, name)`.

**Per-action HTTP handlers duplicate the same scaffold:**
- Issue: `__handle_action_queue`, `__handle_action_stop`, `__handle_action_extract`, `__handle_action_delete_local`, `__handle_action_delete_remote` all repeat the same 15-line pattern (unquote → guard → callback → wait → response).
- Files: `src/python/web/handler/controller.py:76-181`
- Impact: Bug fixes (e.g., timeout adjustments) must be applied in five places. Drift risk is real — only the path-guarded actions call `_check_path_safe`.
- Fix approach: Extract a `_dispatch_command(action, file_name, success_msg, *, guard=False)` helper. The bulk path (`_process_bulk_commands`) already uses a single loop and can share it.

**Duplicate-by-five secret-field walk in `Config`:**
- Issue: Encrypt and decrypt loops both iterate `_SECRET_FIELD_PATHS` (5 hardcoded tuples) and embed the same `is_ciphertext`/`encrypt_field`/`decrypt_field` choreography.
- Files: `src/python/common/config.py:19-25`, `src/python/common/config.py:420-498`
- Impact: Adding a new secret field requires touching the tuple AND verifying both `from_str` and `to_str` branches handle it. Easy to miss.
- Fix approach: Push field metadata into the `PROP` declaration (e.g. `PROP("api_token", ..., secret=True)`) so the encrypt/decrypt loops discover secrets dynamically.

**Backward-compatibility branches in `Config.from_dict`:**
- Issue: Eight separate `if "<section>" not in config_dict:` blocks fall back to defaults for older config files (Sonarr, Radarr, AutoDelete, Encryption, webhook_secret, api_token, allowed_hostname, rate_limit).
- Files: `src/python/common/config.py:515-569`
- Impact: Each new feature compounds the entrance code. Reading the function requires holding the deprecation timeline in mind.
- Fix approach: Introduce a `Config.MIGRATIONS = [(version, migrate_fn), ...]` list applied in order. Drop migrations older than N releases as a documented breaking change.

**`USE_MOCK_MODEL` companion files shipped in dist:**
- Issue: `mock-model-files.ts` (192 lines) and `screenshot-model-files.ts` (135 lines) are committed in `services/files/` despite being development-only fixtures.
- Files: `src/angular/src/app/services/files/mock-model-files.ts`, `src/angular/src/app/services/files/screenshot-model-files.ts`
- Impact: Production bundles include unused mock data. Source tree mixes test fixtures with production services.
- Fix approach: Move to `src/angular/src/app/tests/fixtures/` and import only behind the environment-flag check.

## Known Bugs

**`asyncio` `wait()` swallows premature `Empty` in `MultiprocessingLogger`:**
- Symptoms: A `queue.Empty` raised from the inner `get(block=False)` ends the inner-loop but does not end the listener-thread iteration; the `except Exception` outer handler captures *any* downstream exception (including programming errors) and shuts down listener silently.
- Files: `src/python/common/multiprocessing_logger.py:71-83`
- Trigger: Any unexpected exception inside `self.logger.getChild(record.name).handle(record)` (e.g., a logging filter raising) terminates the entire MP-logger pipeline; child-process logs stop appearing in the main log.
- Workaround: Restart the service. The exception is captured in `self.__listener_exc_info` and surfaces on `propagate_exception()`.

**`set_property` swallows non-string values that are not properly typed:**
- Issue: `InnerConfig.set_property` only runs the converter when `type(value) is str`. If a caller passes a non-string value of a wrong type (e.g. an `int` to a `bool` property), the value bypasses conversion and only hits the checker.
- Files: `src/python/common/config.py:208-218`
- Trigger: Programmatic config mutation via `inner_config.set_property("debug", 1)` — sets `debug=1` rather than `debug=True`.
- Workaround: Always pass strings or pre-converted native values from callers.

**ServiceExit-loop relies on broad `except Exception`:**
- Symptoms: In `Seedsyncarr.run()`, an unexpected exception in the main loop is logged as "Exiting Seedsyncarr" before threads are torn down, regardless of the actual failure mode. The bare `except Exception:` block at line 198 catches both `ServiceExit`/`ServiceRestart` (subclasses of `BaseException` derivatives) and unexpected errors with identical handling.
- Files: `src/python/seedsyncarr.py:167-223`
- Trigger: Any unhandled exception that reaches the main thread.
- Workaround: None — relies on the outer `main()` while-loop to re-raise and exit. Recovery semantics depend on `--exit` arg.

**Bulk command timeouts can leave commands queued in controller:**
- Issue: When `_process_bulk_commands` times out a per-file wait, the callback is reported as failed to the HTTP client, but the underlying `Controller.Command` is still in the controller's command queue. If the controller eventually processes it, the callback's `on_success`/`on_failure` will fire on a no-longer-referenced object (no-op), but the action (queue/extract/delete) executes anyway.
- Files: `src/python/web/handler/controller.py:400-415`
- Trigger: Bulk action against many files when controller is busy; per-file timeout fires for some files while controller is still draining the batch.
- Workaround: None visible. The action may execute server-side after the client has been told it failed.

## Security Considerations

**`innerHTML` used to build confirmation modal:**
- Risk: Direct `innerHTML` assignment is an XSS sink. Although every interpolated value is run through `ConfirmModalService.escapeHtml`, this depends on every caller never passing through code paths that bypass the escape.
- Files: `src/angular/src/app/services/utils/confirm-modal.service.ts:100-116`
- Current mitigation: A static `escapeHtml` helper escapes `&<>"'` for each of `title`, `body`, button labels and classes before substitution.
- Recommendations: Replace `innerHTML` with `Renderer2.createElement` + `createText` calls for content nodes. Or render the modal as an actual Angular component (the project already has standalone components) and let Angular's sanitizer/binding handle escaping.

**API token shipped in HTML response body:**
- Risk: `WebApp.__index` injects `<meta name="api-token" content="...">` into the SPA shell. Any XSS or local file disclosure exposes the token; the token grants full `/server/*` access.
- Files: `src/python/web/web_app.py:219-235`, `src/angular/src/app/services/utils/auth.interceptor.ts:10-17`
- Current mitigation: CSP, `X-Frame-Options: DENY`, HTML escape via `html.escape(api_token, quote=True)`, and `/server/*` Bearer enforcement. Token value is also visible to anyone with browser DevTools access.
- Recommendations: Document that the homelab/single-user threat model is acceptable. For a future hardened mode, move auth to short-lived session cookies issued by a login endpoint and drop the meta-tag approach.

**SSRF DNS-rebind known limitation:**
- Risk: `ConfigHandler._validate_url` resolves the hostname at validation time then trusts `requests.get` to resolve again at request time. A DNS rebinding attack can pass validation and still hit a private IP.
- Files: `src/python/web/handler/config.py:55-85`
- Current mitigation: Inline docstring acknowledges this limitation; rate-limited to 5 requests/minute on test-connection endpoints (`config.py:31-37`).
- Recommendations: Accepted risk per code comment ("out of scope for a homelab tool"). For hardening, swap `requests` for a socket-level intercepted HTTP client that validates the resolved IP at connect time (e.g. ssrfpy).

**Trust of `requests.json` parsing in webhook path:**
- Risk: `body = request.json` (via Bottle) reads up to 1 MB (`_WEBHOOK_MAX_BODY_BYTES = 1_048_576`) and parses JSON before HMAC verification when no secret is configured.
- Files: `src/python/web/handler/webhook.py:90-103`
- Current mitigation: Body-size cap before reading; HMAC verification when `webhook_secret` is configured (`webhook.py:43-77`).
- Recommendations: The startup warning (`seedsyncarr.py:372-378`) already warns about the empty-secret case. Consider making `webhook_secret` mandatory when `sonarr.enabled` or `radarr.enabled` is True.

**File-rename / log injection partially mitigated:**
- Risk: Webhook-supplied file names flow into log lines and SSE events.
- Files: `src/python/controller/webhook_manager.py:35-38`, `src/python/controller/webhook_manager.py:73-91`
- Current mitigation: Newline characters are replaced with `\n`/`\r` literals before logging (CWE-117 mitigation explicitly called out in code comments).
- Recommendations: Audit every other log site that interpolates webhook/user-supplied names — the controller and lftp_manager also log filenames without going through `safe_file_name`.

**Plain HTTP between Angular and Bottle:**
- Risk: `MyWSGIRefServer` binds to `0.0.0.0` with no TLS support. The api-token meta tag is then served in cleartext.
- Files: `src/python/web/web_app_job.py:25-45`
- Current mitigation: None at the application layer. Users are expected to terminate TLS at a reverse proxy (nginx) or restrict access to LAN.
- Recommendations: Document the expectation in `SECURITY.md`. Optional: detect `X-Forwarded-Proto: https` and emit a startup banner when the proxy chain looks correct.

**Bottle attribute-bypass via `object.__setattr__`:**
- Risk: `WebApp.__init__` and `WebApp.stop` use `object.__setattr__(self, '_stop_flag', ...)` to bypass Bottle's `__setattr__` (which treats unknown attribute writes as plugin-conflict errors).
- Files: `src/python/web/web_app.py:75-78`, `src/python/web/web_app.py:206-207`
- Current mitigation: Comment explains why. Behavior is correct but couples the app to internal Bottle dispatch logic.
- Recommendations: Migrate to a composition pattern (`self._app = bottle.Bottle()`) so app state can be tracked without bypassing the framework, or wait for Bottle to expose a public extension hook.

## Performance Bottlenecks

**`ViewFileService.buildViewFromModelFiles` is O(2N) per tick:**
- Problem: The diff loop walks both `_prevModelFiles.keySeq()` and `modelFiles.keySeq()` on every update from the SSE stream. The `setComparator` path re-sorts the full list and rebuilds the indices map.
- Files: `src/angular/src/app/services/files/view-file.service.ts:114-192`, `src/angular/src/app/services/files/view-file.service.ts:278-295`
- Cause: Acknowledged in code comments ("This is a roughly O(2N) operation on every update, so won't scale well, But should be fine for small models").
- Improvement path: Subscribe to incremental model events rather than rebuilding from the full map; piggyback on the existing `EVENT_ADDED`/`EVENT_UPDATED`/`EVENT_REMOVED` SSE channel that `ModelFileService` already exposes.

**LFTP status parsing rebuilds large regex set per parse:**
- Problem: `LftpJobStatusParser.parse` calls a chain of compiled-but-still-greedy regex matches across the entire `jobs -v` output every poll cycle. Some patterns contain nested `?P<>` alternation and run on tens to hundreds of lines.
- Files: `src/python/lftp/job_status_parser.py:13-149`, `src/python/lftp/job_status_parser.py:710-748`
- Cause: LFTP output format constraints — patterns must remain permissive for SFTP variants.
- Improvement path: Profile under a busy queue with multiple parallel jobs. If hot, switch from regex to a line-prefix dispatch table (pget/mirror/queue/chunk) before regex matching.

**`Model.get_file_names` + `get_file` loop builds new list every API call:**
- Problem: `_get_model_files` iterates `get_file_names()` and calls `get_file()` for each, returning a new list — happens on every `/server/command/*` request (under the model lock) and once per SSE handler setup.
- Files: `src/python/controller/controller.py:310-317`
- Cause: Defensive against external callers; the comment notes "Files are frozen (immutable) after being added to the model, so we can safely return direct references without deep copying."
- Improvement path: Cache the list inside the model and invalidate on add/remove/update. The lock window for command processing is already a known contention point.

**`Job` thread polls at 500ms regardless of activity:**
- Problem: Every `Job` (controller + webapp) sleeps `_DEFAULT_SLEEP_INTERVAL_IN_SECS = 0.5` between executes. The controller's `process()` runs even when nothing changed.
- Files: `src/python/common/job.py:13-47`
- Cause: Simple polling model.
- Improvement path: Switch to a condition variable signaled by command queue inserts and SSE events. The 500ms latency floor on commands is unnecessary.

**`StreamQueue` drops oldest events under load:**
- Problem: `StreamQueue.put` drops events when `maxsize` (default 1000) is reached. The dropped count is logged at every 100th drop only.
- Files: `src/python/web/utils.py:33-63`
- Cause: Memory-safety tradeoff for SSE clients that disconnect without unsubscribing.
- Improvement path: Already monitored via `MemoryMonitor` (`controller.py:151-187`). For high-frequency model updates (large directories), consider coalescing consecutive `UPDATED` events for the same file before queueing.

## Fragile Areas

**`Config` property machinery (lambdas + class-level state):**
- Files: `src/python/common/config.py:118-218`
- Why fragile: Properties are built with `lambda` closures referencing the parent class via `__prop_addon_map`. Adding a new property requires repeating the pattern correctly in three places (class-level `PROP` declaration, `__init__` initializer to `None`, and entry in `_SECRET_FIELD_PATHS` if secret).
- Safe modification: Always follow the existing 3-step pattern. Run `tests/integration/test_web/test_handler/test_config.py` and the encryption round-trip suite.
- Test coverage: Good for happy paths; thin for "what happens if you set the property twice during from_dict" type edge cases.

**`Controller` god-class (1115 lines):**
- Files: `src/python/controller/controller.py`
- Why fragile: Owns command queue, model, all scanners (via ScanManager), LFTP manager, file operation manager, webhook manager, memory monitor, and auto-delete timers. Thread safety relies on careful comments around `__model_lock`, `__auto_delete_lock`, and which methods release the lock before subprocess dispatch.
- Safe modification: Read the multiline docstrings above each method (e.g. `controller.py:823-833` documents why `delete_local` runs outside the lock). Never extend the lock to cover subprocess spawns.
- Test coverage: Heavy integration coverage in `tests/integration/test_web/`. Unit coverage for auto-delete edge cases is in `test_seedsyncarr.py`.

**LFTP `pexpect.spawn` and prompt regex:**
- Files: `src/python/lftp/lftp.py:38-100`
- Why fragile: The prompt-match regex `lftp {user}@{host}:.*>` depends on lftp's prompt output format; any lftp version that changes prompt formatting silently breaks job control. `__timeout = 180` for command responses, but `pexpect.expect` blocks the whole controller indirectly.
- Safe modification: Run `tests/integration/test_lftp/` against a real lftp binary before changing any pexpect interaction. Never change `_SET_COMMAND_AT_EXIT = "cmd:at-exit"` value — it prevents zombie processes.
- Test coverage: `tests/integration/test_lftp/test_lftp.py` and `test_lftp_protocol.py` exercise the protocol against a real lftp.

**`SshCp` brittle expect-list:**
- Files: `src/python/ssh/sshcp.py:74-130`
- Why fragile: 9 expect-string alternatives mapped to numeric indices. SSH client message text varies by OpenSSH version; the parser is best-effort.
- Safe modification: Add new error strings to the end of the expect list and assign new indices in the `if i in {...}` branches. Don't reorder existing entries.
- Test coverage: Limited — most tests mock `Sshcp` rather than exercising the expect loop.

**Auto-delete BFS + coverage check sequence:**
- Files: `src/python/controller/controller.py:823-975`
- Why fragile: A 150-line method with multiple early-return paths under three different locks (`__auto_delete_lock`, `__model_lock`) and an in-band BFS bounded by `_AUTO_DELETE_BFS_NODE_LIMIT = 10_000`. WR-02 comment block (`controller.py:960-970`) documents a TOCTOU mitigation that depends on dispatch happening BEFORE `imported_children.pop` releases.
- Safe modification: Preserve the relative order of `pop` and `delete_local` dispatch. The lock-held window must include the coverage check.
- Test coverage: Phase 75 (GH #19) tests cover D-01 through D-16 decision points.

**`MyWSGIHandler` chunk-encoding override:**
- Files: `src/python/web/web_app_job.py:47-54`
- Why fragile: Subclasses `paste.httpserver.WSGIHandler` to coerce `str` chunks to `bytes`. The comment says "fix a bug in Paste http server" but doesn't link to the bug. If Paste fixes the upstream issue, this override could subtly change behavior.
- Safe modification: Keep the override until Paste is replaced.
- Test coverage: SSE integration tests in `tests/integration/test_web/test_handler/test_stream_*.py` exercise the chunked encoding path.

**Bulk action queueing + waiting model:**
- Files: `src/python/web/handler/controller.py:317-448`
- Why fragile: Per-file timeout (`_BULK_TIMEOUT_PER_FILE = 5.0`) and aggregate cap (`_BULK_MAX_TIMEOUT = 300.0`) are tuned empirically. Cancellation isn't supported — once queued, a command will execute even after the HTTP client gives up.
- Safe modification: If timeouts are raised, ensure rate-limit window (`max_requests=10, window_seconds=60.0` at `controller.py:73`) still keeps total in-flight commands bounded.
- Test coverage: `tests/integration/test_web/test_handler/test_controller.py` covers bulk action paths.

## Scaling Limits

**Tracked-files cap of 10,000:**
- Current capacity: `DEFAULT_MAX_TRACKED_FILES = 10000` for each of downloaded/extracted/stopped/imported sets.
- Limit: At cap, oldest entries are LRU-evicted. A library with >10k completed downloads will lose the earliest "do not re-queue" signal first.
- Files: `src/python/controller/controller_persist.py:25`, `src/python/common/bounded_ordered_set.py:32`
- Scaling path: Configurable via `Controller.max_tracked_files` setting. Increasing it linearly increases memory (~200 bytes/entry × N) and persist-file write cost (full rewrite on each persist cycle).

**Bulk request file cap of 1000:**
- Current capacity: `_MAX_BULK_FILES = 1000` for `/server/command/bulk`.
- Limit: Hard 400 response above 1000. Sonarr/Radarr cannot bulk-trigger more than 1000 episode imports in one webhook batch (though webhooks are per-import in practice).
- Files: `src/python/web/handler/controller.py:207`
- Scaling path: Raise the cap and adjust `_BULK_TIMEOUT_PER_FILE`. Memory is bounded since responses are streamed in single response.

**Auto-delete BFS at 10,000 nodes:**
- Current capacity: `_AUTO_DELETE_BFS_NODE_LIMIT = 10_000` per pack-guard traversal.
- Limit: A pack-root with >10k descendants is skipped on every Timer fire with a warning. The user has no way to bypass.
- Files: `src/python/controller/controller.py:45`
- Scaling path: Raise the cap if real-world packs exceed it. Consider switching to iterative traversal with yield-points so a single pack doesn't monopolize the controller thread.

**`StreamQueue` dropping at 1000 events:**
- Current capacity: `DEFAULT_QUEUE_MAXSIZE = 1000` per stream subscriber.
- Limit: Slow SSE clients (laggy reverse proxies, browser tabs in background) drop oldest events first. Drops are logged every 100th.
- Files: `src/python/web/utils.py:8`
- Scaling path: Increase cap or add backpressure (close the stream on too many drops).

**Per-root child cap of 500:**
- Current capacity: `DEFAULT_MAX_CHILDREN_PER_ROOT = 500` for `imported_children` tracking.
- Limit: A pack with >500 imported children loses oldest child tracking; auto-delete coverage check may pass falsely after eviction.
- Files: `src/python/controller/controller_persist.py:31`
- Scaling path: Configurable raise. Multi-season anime packs are the realistic concern.

## Dependencies at Risk

**jQuery 4.x in Angular app:**
- Risk: jQuery 4.0 is a major version recently released; ecosystem compat (e.g. Bootstrap 5 plugins) targets jQuery 3.x. Listed as direct dep but no usages found in source — only Bootstrap consumes it.
- Files: `src/angular/package.json:31`
- Impact: Bundle size penalty + version-mismatch fragility against Bootstrap 5.3 plugins.
- Migration plan: Bootstrap 5 no longer requires jQuery. Audit `_bootstrap-overrides.scss` and the `@popperjs/core` dep to confirm jQuery can be dropped entirely.

**`font-awesome` 4.7 (legacy):**
- Risk: Font Awesome 4.x is end-of-life (FA5 was released in 2018). Project also depends on `@phosphor-icons/web` 2.x, indicating an in-progress migration.
- Files: `src/angular/package.json:29`, `src/angular/package.json:24`
- Impact: Duplicate icon libraries shipped; FA4 receives no fixes.
- Migration plan: Inventory remaining `fa-*` class usages in HTML templates and replace with Phosphor equivalents, then drop the FA4 dep.

**`css-element-queries` (unmaintained):**
- Risk: `css-element-queries` had its last release in 2019. Now superseded by `ResizeObserver` (cross-browser available since 2020).
- Files: `src/angular/package.json:28`
- Impact: Carries polyfills/legacy code; small bundle penalty.
- Migration plan: Search for usages and replace with native `ResizeObserver`. If unused, drop the dep.

**`paste` HTTP server (low-activity upstream):**
- Risk: `paste` (used via `paste.httpserver`) has very low release cadence and was originally an early-2000s WSGI server. SSE-friendly but lacks HTTP/2 and modern TLS.
- Files: `src/python/web/web_app_job.py:6-7`, `src/python/pyproject.toml:13`
- Impact: Couples the project to a server that may not be maintained long-term. `MyWSGIHandler` already monkey-patches a bug fix.
- Migration plan: Evaluate `waitress` or `gunicorn` with SSE support. Behavior-test the streaming path heavily.

**`bottle` 0.13.x:**
- Risk: Bottle is a tiny single-file framework with infrequent releases. Project pins `>=0.13.4` and uses internal hook semantics (`hook('before_request')`, `hook('after_request')`) that may shift across major versions.
- Files: `src/python/pyproject.toml:12`, `src/python/web/web_app.py:83-164`
- Impact: Upgrade risk for security patches.
- Migration plan: Pin upper bound. Evaluate `flask` or `starlette` for a future rewrite if bottle stalls.

**`pexpect`-driven LFTP and SSH:**
- Risk: Whole product depends on pexpect's prompt-driven interaction with binaries that are not API-stable (lftp prompt format, OpenSSH message strings).
- Files: `src/python/lftp/lftp.py`, `src/python/ssh/sshcp.py`
- Impact: Distro-version-specific failures.
- Migration plan: No good Python SFTP library matches lftp's feature set (mirror with parallel jobs, queue-parallel). Continue treating lftp as an external runtime requirement; document version range in `SECURITY.md`/`README.md`.

**`patoolib` for archive extraction:**
- Risk: Pins `>=4.0.3`; v4 was a major rewrite. Catches `patoolib.util.PatoolError` broadly.
- Files: `src/python/controller/extract/extract.py`, `src/pyinstaller_hooks/hook-patoolib.py`
- Impact: A future patool API change in `get_archive_format` return shape would break `is_archive`. Already requires a PyInstaller hook for packaging.
- Migration plan: Pin upper bound (`<5`). Audit test coverage of `extract.py`.

## Missing Critical Features

**No structured cancellation for queued bulk commands:**
- Problem: Once a `Controller.Command` is enqueued, there is no way to cancel it. Even when the HTTP handler times out (`_BULK_TIMEOUT_PER_FILE = 5.0`), the underlying action will still run when the controller drains.
- Blocks: Reliable rate-limited bulk operations against many files. Race recovery on controller restart.

**No TLS termination guidance baked into the product:**
- Problem: Project ships with `0.0.0.0` bind and api-token in HTML body. No documented deployment story for HTTPS.
- Blocks: Safe internet exposure. Users must DIY a reverse proxy.

**No persistent settings audit log:**
- Problem: Settings can be changed via `/server/config/set/...` with rate-limit `60 req/min` but no audit trail of who/when/what.
- Blocks: Forensics if credentials are leaked. Tracking back when an SSRF-friendly Sonarr URL was set.

**No graceful handling of clock skew in Fernet keys:**
- Problem: Fernet tokens embed a 64-bit timestamp. Code accepts any timestamp; no max-age check on stored secrets. Not strictly a bug but worth noting for credential rotation.
- Blocks: Forward secrecy on rotated keys.

## Test Coverage Gaps

**`confirm-modal.service.ts` XSS escape logic:**
- What's not tested: The `escapeHtml` static helper has no dedicated tests; every modal call passes through it but no test verifies an attacker-controlled string is escaped end-to-end.
- Files: `src/angular/src/app/services/utils/confirm-modal.service.ts:33-40`
- Risk: A regression that bypasses the helper would silently re-introduce an XSS sink against bulk action confirmations.
- Priority: Medium — the surface is small (only callers within the codebase) but the helper IS the only thing standing between user input and `innerHTML`.

**`MultiprocessingLogger` listener-thread shutdown semantics:**
- What's not tested: The `except Exception` branch (`multiprocessing_logger.py:78`) sets `__listener_shutdown` on any error and stops the listener silently. No test simulates a logger handler raising.
- Files: `src/python/common/multiprocessing_logger.py:67-86`
- Risk: A bug in a downstream log handler (e.g. file-rotate failure) could silently stop all child-process logs.
- Priority: Medium.

**`auth.interceptor.ts` token-missing path:**
- What's not tested: The interceptor reads the meta tag once and caches. There's a reset helper `_resetAuthInterceptorCache` (`auth.interceptor.ts:39`) but production code has no path to re-read the token if the server rotates it.
- Files: `src/angular/src/app/services/utils/auth.interceptor.ts:7-17`
- Risk: After token rotation (settings change), the SPA continues to send the old Bearer until reload.
- Priority: Low — token rotation triggers a page reload via `version-check.service.ts` in practice, but the coupling is implicit.

**SSE timeout reconnection paths:**
- What's not tested fully: `StreamDispatchService.reconnectDueToTimeout` and `checkConnectionTimeout` rely on `setInterval` + `Date.now()` deltas; race conditions between heartbeat arrival and timeout fire are subtle.
- Files: `src/angular/src/app/services/base/stream-service.registry.ts:111-164`
- Risk: SSE-related flake on slow CI.
- Priority: Low — exercised by e2e tests under `src/e2e/tests/`.

**SSRF private-IP validation:**
- What's not tested: `_validate_url` rejects private addresses but the unit tests don't exercise IPv6 link-local (`fe80::/10`) or rare reserved ranges.
- Files: `src/python/web/handler/config.py:55-85`
- Risk: A docstring-acknowledged DNS-rebind bypass plus an under-tested IPv6 path could let a crafted Sonarr URL leak credentials.
- Priority: Medium.

**`Lftp` parser ValueError recovery:**
- What's not tested: `LftpJobStatusParser.parse` raises `LftpJobStatusParserError` on internal `ValueError`. The controller catches it via `LftpJobStatusParserError` in its general error queue, but recovery from repeated parser failures (`MAX_CONSECUTIVE_STATUS_ERRORS = 2` in `lftp.py:12`) isn't covered by integration tests.
- Files: `src/python/lftp/lftp.py:11-13`, `src/python/lftp/job_status_parser.py:710-727`
- Risk: A new lftp output format quirk could cause the controller to hard-fail.
- Priority: Medium.

**Auto-delete dry-run vs. enabled toggling under live timer:**
- What's not tested: The Timer fires `__execute_auto_delete` after `delay_seconds`. If the user disables auto-delete or toggles dry-run between scheduling and firing, the code re-reads config (`controller.py:838-851`). A test where the toggle flips during the Timer window is not visible in the unit suite.
- Files: `src/python/controller/controller.py:823-851`
- Risk: User cancels auto-delete after scheduling but a Timer that already started its callback executes anyway.
- Priority: Low — the in-method config re-read handles this; just lacks explicit test coverage.

**`BoundedOrderedSet` eviction ordering after `touch`:**
- What's not tested: `touch()` moves an item to the end (most recent). If many items are touched after a `from_iterable` load, eviction order can diverge from insertion order in subtle ways.
- Files: `src/python/common/bounded_ordered_set.py:91-105`
- Risk: Tracked-files lists may evict items unexpectedly if a future refactor calls `touch` after `add`.
- Priority: Low.

---

*Concerns audit: 2026-05-26*
