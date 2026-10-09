# Phase 117 Deferred Items

## Found during 117-08 (out of scope)

- `tests/unittests/test_controller/test_scan/test_scanner_process.py` (3 tests: failed + errored at teardown) and
  `tests/unittests/test_controller/test_extract/test_extract_process.py::TestExtractProcess::test_calls_start_dispatch`
  fail on local macOS runs with `_pickle.PicklingError: Can't pickle <class 'unittest.mock.MagicMock'>` or a 2s
  timeout. macOS multiprocessing uses the `spawn` start method, which pickles the mock-patched process object;
  Linux CI uses `fork`. These are unrelated to the 117-08 files (lftp_manager, model_builder, model_pipeline,
  command_processor) and are not in the phase quick-run set. Not fixed.
