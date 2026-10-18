# Routine maintenance — no standalone milestone

Handle only while touching the relevant dependency or test code:

- Remove the webob/cgi warning filter during a suitable dependency upgrade. Verify upstream state then; see ../todos/maintenance/2026-04-21-webob-cgi-upstream-unblock.md.
- Address Bootstrap's internal Sass warnings during its normal upgrade.
- Clean up cosmetic test imports/style opportunistically.
- Replace harmless test sleeps for speed only when convenient. Demonstrated flaky tests remain actionable correctness work.

The dev/test dependency advisory 999.4 is an explicit bounded side task in ROADMAP.md: recheck current status/exposure and apply the smallest supported fix if relevant. It is not automatically a Reliability completion gate; material exposure may justify reprioritization.
