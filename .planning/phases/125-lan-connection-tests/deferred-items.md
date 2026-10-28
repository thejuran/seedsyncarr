# Phase 125 — Deferred Items (out of scope)

Logged during 125-01 execution per the executor's scope-boundary rule:
pre-existing failures in files unrelated to this plan's changes
(`src/python/web/handler/config.py`,
`src/python/tests/unittests/test_web/test_handler/test_config_handler.py`,
`src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py`)
are not fixed here.

## Local full-suite run has 26 pre-existing failures, unrelated to LAN-01/LAN-02

`cd src/python && poetry run pytest tests/unittests -p no:cacheprovider -q`
(the 92-second full-suite run beyond the plan's own targeted verify command)
reports 26 failed / 1917 passed / 3 errors on this local macOS poetry
environment (Python 3.12.12). None of the failing files reference
`ConfigHandler` or `_validate_url` (confirmed via grep).

- `tests/unittests/test_ssh/test_sshcp.py` (8 tests): `KeyError:
  getgrnam(): name not found: 'testgroup'` — the test fixture expects a
  `testgroup` Unix group that only exists inside the project's Docker test
  container, not on a bare local macOS poetry venv.
- `tests/unittests/test_common/test_app_process.py` (5 tests) and
  `tests/unittests/test_controller/test_extract/test_extract_process.py`
  (6 tests) and `tests/unittests/test_controller/test_scan/test_scanner_process.py`
  (3 tests + 3 errors): multiprocessing-spawn-context tests that pass in
  isolation (verified `test_init_called_before_loop` individually passes)
  but fail/error under the full-suite run on this local environment —
  consistent with the project's documented local-vs-Docker test
  environment gap (`make run-tests-python` Docker fallback).
- `tests/unittests/test_system/test_scanner.py::test_scan_file_with_latin_chars`
  (1 test): filesystem-encoding-dependent, unrelated to this phase.

The plan's own targeted verify command (`test_config_handler.py` +
`test_web_app_builder_logging.py` + `tests/unittests/test_sonarr5`) and
whole-tree `ruff check src/python/` are both clean. This full-suite note is
recorded for visibility only; no fix applied here (SCOPE BOUNDARY — these
files are untouched by 125-01).
