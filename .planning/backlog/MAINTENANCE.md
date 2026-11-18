# Routine maintenance — no standalone milestone

Handle only while touching the relevant dependency or test code:

- Remove the webob/cgi warning filter during a suitable dependency upgrade. Verify upstream state then; see ../todos/maintenance/2026-04-21-webob-cgi-upstream-unblock.md.
- Address Bootstrap's internal Sass warnings during its normal upgrade.
- Clean up cosmetic test imports/style opportunistically.
- Replace harmless test sleeps for speed only when convenient. Demonstrated flaky tests remain actionable correctness work.

The dev/test advisory 999.4 was rechecked in Phase 126 and recorded no fix needed (braces@3.0.3). Its original entry and reopening conditions are preserved in [the reconciliation archive](archive/2026-11-18/README.md). Reopen only for new applicable evidence; current remote advisory status was not refreshed on 2026-11-18.
