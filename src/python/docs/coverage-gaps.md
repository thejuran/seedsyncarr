# Python Test Coverage Gaps

Documented: 2026-04-25
Phase: 89 (PYARCH-04)

## Purpose

This file lists production modules that have no dedicated test file. Some are partially covered by integration tests that exercise them indirectly. Tracked here so future test coverage work (Phase 94) has a clear starting point.

## Modules Without Dedicated Test Files

| Module | Path | Lines | Purpose | Covered Indirectly? | Phase 94 Req |
|--------|------|-------|---------|---------------------|--------------|
| ActiveScanner | controller/scan/active_scanner.py | 52 | Orchestrates scanner processes, scan scheduling | Partially via test_scanner_process.py | COVER-06 |
| WebAppJob | web/web_app_job.py | 79 | Manages web app lifecycle thread | No | -- |
| WebAppBuilder | web/web_app_builder.py | 62 | Constructs Bottle app with middleware | Partially via integration test_web_app.py | -- |
| scan_fs | scan_fs.py | 40 | Remote filesystem scanning script | No | -- |

## Notes

- Line counts are for the production module only (excluding blank lines and comments would be lower).
- "Covered Indirectly" means another test file exercises this module's code paths without being a dedicated test for it.
- ActiveScanner (COVER-06) and DeleteRemoteProcess (COVER-05) are explicitly tracked for Phase 94.
- WebAppJob and scan_fs remain as future test candidates not yet scheduled.
