# Codebase Concerns

**Analysis Date:** 2026-02-03

## Tech Debt

**Deprecated distutils import in config module:**
- Issue: `from distutils.util import strtobool` is used for boolean parsing. The `distutils` module was deprecated in Python 3.10 and removed in Python 3.12.
- Files: `src/python/common/config.py:7`
- Impact: Will fail in Python 3.12+. Current pyproject.toml constrains to `<3.13`, but this creates a hard migration blocker.
- Fix approach: Replace with custom boolean parsing or use a third-party library like `marshmallow` or implement a simple replacement.
  ```python
  # Instead of: bool(strtobool(value))
  # Use: value.lower() in ('true', '1', 'yes', 'on')
  ```

**Large monolithic controller class:**
- Issue: `src/python/controller/controller.py` is 756 lines. While managers have been extracted, the controller still coordinates complex state and interactions.
- Files: `src/python/controller/controller.py`
- Impact: Difficult to test all edge cases, hard to maintain error handling logic consistently.
- Fix approach: Further extract pattern matching/queue processing logic into separate helper classes. Add comprehensive unit tests for command callback patterns.

**Large LFTP job status parser:**
- Issue: `src/python/lftp/job_status_parser.py` is 761 lines with complex regex patterns and state machines for parsing LFTP output.
- Files: `src/python/lftp/job_status_parser.py`
- Impact: Difficult to understand regex patterns, hard to extend with new LFTP output formats. Changes to parsing logic are high-risk.
- Fix approach: Split parser into separate classes per job type (PGET parser, Mirror parser, etc.). Add integration tests that parse real LFTP output.

**Model builder complexity:**
- Issue: `src/python/controller/model_builder.py` is 573 lines building the complete file model from scanner/LFTP data.
- Files: `src/python/controller/model_builder.py`
- Impact: Complex merge logic between remote/local/LFTP state is hard to understand and verify.
- Fix approach: Split into smaller modules (RemoteFileBuilder, LocalFileBuilder, StateReconciler). Add focused unit tests for each reconciliation scenario.

## Known Limitations

**Fixed bounded collections may lose data:**
- Issue: `BoundedOrderedSet` in `src/python/common/bounded_ordered_set.py` has a DEFAULT_MAXLEN of 10,000 items. When this limit is reached, oldest items are silently evicted.
- Files: `src/python/common/bounded_ordered_set.py:35`, `src/python/controller/controller.py` (usage)
- Config: `src/python/common/config.py` has `max_tracked_files` config option (default: 10000)
- Impact: On systems with >10,000 downloaded/extracted files, older files disappear from tracking. Users may not know which files have been silently dropped from the model.
- Current behavior: Evictions are logged, but users could miss the logs or misunderstand the feature.
- Safe modification: Document this limitation prominently. Consider adding a warning in the UI when approaching capacity. Allow users to increase `max_tracked_files` in config.

**No validation of SSH key file permissions:**
- Issue: When `use_ssh_key=true`, the SSH key path is not validated for proper permissions (should be 0600).
- Files: `src/python/controller/file_operation_manager.py:57-59`
- Impact: SSH with incorrect key permissions will fail silently or with unclear error messages.
- Fix approach: Add permission validation when SSH key is configured. Provide clear error message if permissions are wrong.

**Memory monitoring incomplete on non-Unix systems:**
- Issue: `src/python/controller/memory_monitor.py` imports `resource` module which doesn't exist on Windows.
- Files: `src/python/controller/memory_monitor.py:10-15`
- Impact: Memory monitoring silently disabled on Windows (HAS_RESOURCE=False). No way to detect memory leaks on Windows deployments.
- Current behavior: Gracefully handled with fallback, but users won't know monitoring is disabled.
- Fix approach: Add explicit warning log when memory monitoring is unavailable.

## Security Considerations

**Credentials passed to child processes:**
- Risk: Remote passwords are passed to LFTP and SSH processes via command-line arguments or environment variables.
- Files: `src/python/lftp/lftp.py:66`, `src/python/ssh/sshcp.py`, `src/python/controller/file_operation_manager.py:192`
- Current mitigation: LFTP uses `-u user,password` format (standard LFTP practice). SSH operations use pexpect for interactive password entry or SSH key files.
- Recommendations:
  - Verify that `pexpect` doesn't expose passwords in process listing (it shouldn't, but verify)
  - Document that SSH keys are more secure than passwords
  - Consider adding credential masking in logs (ensure passwords never appear)

**No HTTPS by default:**
- Risk: Web UI is served over HTTP without TLS encryption.
- Files: `src/python/web/web_app.py` (Bottle web framework)
- Current mitigation: Security docs recommend using a reverse proxy with authentication if exposing to the internet.
- Recommendations:
  - Document the security considerations more prominently in README
  - Consider adding TLS support with self-signed certificate generation
  - Add warning log if binding to non-localhost addresses

**Configuration file permissions not validated:**
- Risk: Config file contains SSH passwords/keys but no permission validation is performed.
- Files: `src/python/common/config.py`, `src/python/common/persist.py`
- Impact: If config file has world-readable permissions, credentials are exposed.
- Fix approach: Add permission check on startup, warn if config is world-readable.

**No input validation on web API parameters:**
- Risk: File operation endpoints accept file paths without comprehensive validation.
- Files: `src/python/web/handler/controller.py` (bulk command handler)
- Current mitigation: Controller validates file existence before executing operations. LFTP/SSH operations are path-constrained to configured remote/local directories.
- Recommendations:
  - Document the path restrictions clearly
  - Add explicit path traversal prevention tests
  - Validate that requested paths are within allowed directories before reaching LFTP

## Performance Bottlenecks

**O(n log n) sorting on every file update:**
- Problem: ViewFileService sorts entire file list on every update that changes file state.
- Files: `src/angular/src/app/services/files/view-file.service.ts:49-51`
- Cause: Immutable list update requires re-sorting. For 10,000 files with frequent state changes, this becomes expensive.
- Improvement path:
  1. Use insertion sort for small changes (O(n) instead of O(n log n))
  2. Batch updates and sort once
  3. Consider IndexedDB or virtual scrolling for very large file lists

**Model rebuild on every scanner result:**
- Problem: `ModelBuilder` rebuilds the entire model from scratch when scanner results arrive.
- Files: `src/python/controller/controller.py` (model rebuild), `src/python/controller/model_builder.py`
- Cause: Full merge of remote/local/LFTP state on each scanner update cycle.
- Improvement path:
  1. Implement incremental model updates (add/remove specific files)
  2. Batch scanner results and debounce updates
  3. Profile the rebuild time - if <100ms, may not be worth optimizing

**Web API streams without backpressure:**
- Problem: Streaming endpoints (logs, status) use polling without rate limiting or backpressure handling.
- Files: `src/python/web/web_app.py:59-61` (STREAM_POLL_INTERVAL_IN_MS = 100ms)
- Impact: On slow connections, streaming data can accumulate and cause memory pressure.
- Safe modification: Add configurable stream rate limits. Monitor queue depth in memory monitor.

## Fragile Areas

**LFTP job status parsing is tightly coupled to LFTP version:**
- Files: `src/python/lftp/job_status_parser.py`
- Why fragile: Regex patterns assume specific LFTP output format. Minor LFTP version changes can break parsing.
- Safe modification:
  1. Pin LFTP version in Dockerfile/packaging
  2. Add integration tests with multiple LFTP versions
  3. Use regex with more flexibility and fallback patterns
- Test coverage: Job status parser has unit tests but lacks integration tests with actual LFTP output.

**State synchronization between multiple managers:**
- Files: `src/python/controller/controller.py`, `src/python/controller/scan_manager.py`, `src/python/controller/lftp_manager.py`, `src/python/controller/file_operation_manager.py`
- Why fragile: Controllers coordinates three separate process managers. Race conditions possible if state becomes inconsistent.
- Safe modification:
  1. Add invariant checks (e.g., verify file status is consistent across managers)
  2. Add integration tests that trigger concurrent operations
  3. Use event sourcing or event-driven architecture to make state changes explicit
- Test coverage: Managers have unit tests but lack integration tests for concurrent scenarios.

**Angular file list rendering with large datasets:**
- Files: `src/angular/src/app/pages/files/file-list.component.ts` (481 lines)
- Why fragile: Component handles sorting, filtering, selection, pagination, and bulk operations. UI can become unresponsive with 10,000+ files.
- Safe modification:
  1. Implement virtual scrolling (CDK virtual scroll)
  2. Move filtering/sorting to service layer
  3. Debounce user interactions
- Test coverage: Good unit test coverage (761-line spec file) but no performance tests.

**HTTP status code handling inconsistent in web handlers:**
- Files: `src/python/web/handler/controller.py`, `src/python/web/handler/config.py`, `src/python/web/handler/*.py`
- Why fragile: Some endpoints return 400 for validation, others 409 for state conflicts. Inconsistent status codes make client error handling unpredictable.
- Safe modification: Define and document HTTP status code semantics. Add middleware to normalize error responses.
- Test coverage: Web handlers have tests but lack comprehensive error scenario coverage.

## Scaling Limits

**Bounded file tracking (10,000 files default):**
- Current capacity: 10,000 downloaded/extracted files tracked by default
- Limit: When exceeded, oldest files are silently evicted
- Scaling path:
  1. Increase `max_tracked_files` in config
  2. Consider database-backed storage for larger deployments
  3. Implement pagination/archival of old file records

**Scanner process memory usage with large remote directories:**
- Current capacity: Scanner can handle typical 100k+ file remote directories (tested)
- Limit: Very large directories (1M+ files) may consume significant memory
- Scaling path:
  1. Implement incremental scanning (scan subdirectories in batches)
  2. Add memory limits to scanner processes
  3. Implement database-backed file tree for remote filesystem

**Web API endpoint rate limiting:**
- Current capacity: Single-threaded Bottle server with paste multithreading
- Limit: No explicit rate limiting; heavy API usage can starve other requests
- Scaling path:
  1. Add request queuing/rate limiting middleware
  2. Implement API caching for frequently accessed endpoints
  3. Consider async/await architecture for I/O-bound operations

## Dependencies at Risk

**pexpect for LFTP/SSH interaction:**
- Risk: `pexpect` (^4.9.0) is stable but relatively niche. Regex-based terminal interaction is fragile.
- Impact: Updates to pexpect or LFTP output format can break interactive command handling.
- Migration plan: If pexpect becomes unmaintained, consider switching to `paramiko` (pure Python SSH) or `asyncio`-based subprocess management. This would be a major refactoring.

**paste for WSGI multithreading:**
- Risk: `paste` (^3.10.1) is an older WSGI server. Modern alternatives include `gunicorn`, `waitress`, or `uvicorn`.
- Impact: Limited performance and no async support. Single-threaded bottleneck for high-concurrency scenarios.
- Migration plan: Evaluate `waitress` (easier drop-in replacement) or refactor to async with `uvicorn`/`hypercorn`.

**Bottle web framework:**
- Risk: Bottle (^0.13.4) is a micro-framework with limited feature set. Not ideal for growing applications.
- Impact: No built-in request validation, no automatic OpenAPI generation, limited middleware ecosystem.
- Migration plan: For significant scaling, consider FastAPI (async, Pydantic validation) or Flask with extensions. This would require rewriting most web handlers.

**distutils deprecation (high priority):**
- Risk: Python 3.12 removes distutils entirely
- Impact: Code will not run on Python 3.12+
- Migration plan: Implement custom boolean parsing or upgrade to Python 3.11 max until distutils replacement is available (see Tech Debt section)

## Missing Critical Features

**No persistent job queue:**
- Problem: LFTP job queue is in-memory. If application crashes, queued transfers are lost.
- Blocks: Can't guarantee all queued transfers will eventually complete (reliability issue).
- Workaround: User must manually re-queue files. Consider adding config to save job queue to disk.

**No automatic retry for failed transfers:**
- Problem: Failed LFTP transfers don't automatically retry. User must manually restart.
- Blocks: Large-scale, long-running transfers are unreliable.
- Workaround: Manual retry through UI. Consider adding auto-retry config with exponential backoff.

**No bandwidth throttling:**
- Problem: LFTP rate limiting is configured but not adjustable from UI. Requires config file edit.
- Blocks: Can't dynamically adjust transfer speed without stopping service.
- Workaround: Edit config file and restart. Consider adding UI controls for dynamic rate limiting.

**No transfer scheduling:**
- Problem: Transfers start immediately when queued. No ability to schedule transfers for off-peak hours.
- Blocks: Can't optimize network usage for bandwidth-capped connections.
- Workaround: Manual queuing. Consider adding cron-like scheduling to auto-queue patterns.

## Test Coverage Gaps

**LFTP job status parsing edge cases:**
- What's not tested: Malformed LFTP output, timeout messages, connection errors, partial job failures
- Files: `src/python/lftp/job_status_parser.py`, `src/python/tests/unittests/test_lftp/test_lftp.py`
- Risk: Parser may crash or return incorrect status for edge cases that occur in production.
- Priority: **High** - Parser is critical for accurate transfer status reporting.

**Model builder state reconciliation:**
- What's not tested: Concurrent file operations (file deleted while downloading, extract during scan), out-of-order state updates
- Files: `src/python/controller/model_builder.py`, `src/python/tests/unittests/test_controller/test_model_builder.py`
- Risk: Model can become inconsistent if state updates arrive out of order.
- Priority: **High** - State inconsistency can cause silent data loss or incorrect operations.

**Web API error scenarios:**
- What's not tested: Invalid file paths, permission errors, network disconnections during bulk operations
- Files: `src/python/web/handler/controller.py`, `src/python/tests/integration/test_web/` (limited coverage)
- Risk: Error responses may be unclear, making it hard for users to debug issues.
- Priority: **Medium** - Users see errors but may not understand causes.

**Angular file list performance with large datasets:**
- What's not tested: Rendering 10,000+ files, rapid state updates, bulk selection performance
- Files: `src/angular/src/app/pages/files/file-list.component.ts`, `src/angular/src/app/tests/unittests/pages/files/file-list.component.spec.ts`
- Risk: UI becomes unresponsive with large file lists, giving impression of application crash.
- Priority: **Medium** - Affects UX for power users with large file collections.

**SSH key validation:**
- What's not tested: Missing keys, incorrect permissions, key format errors
- Files: `src/python/controller/file_operation_manager.py`, `src/python/ssh/sshcp.py`, `src/python/tests/unittests/test_ssh/`
- Risk: SSH operations fail with unclear error messages.
- Priority: **Medium** - Users need clear guidance on SSH setup.

**Configuration validation:**
- What's not tested: Invalid config values, missing required fields, type mismatches
- Files: `src/python/common/config.py`, `src/python/tests/unittests/test_common/test_config.spec.ts`
- Risk: Invalid configs may be silently accepted or cause cryptic errors at runtime.
- Priority: **Low** - Config is usually set correctly, but validation would catch user errors earlier.

---

*Concerns audit: 2026-02-03*
