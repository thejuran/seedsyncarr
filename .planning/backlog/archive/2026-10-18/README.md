# Archived backlog — 2026-10-18

Owner requested removal of completed and declined work from the active roadmap. This archive preserves the decisions and evidence; it is not a future-work queue.

## Won't do

- 999.1: webhook payload-size completion shortcut; equal sizes do not prove identity or complete contents. Stronger completion evidence and persisted child credit shipped in Phase 119.
- A-01: wholesale pytest-fixture migration.
- A-04: blanket dedicated-test-per-module expansion. Specific demonstrated gaps may still justify targeted tests.
- A-05: refactoring tests away from private attributes; accepted tradeoff.
- Old review-tool-state migration; leave actual tool state untouched.
- Proactive AutoQueue threading redesign while its single-thread contract holds.
- Old missing-summary bookkeeping as a development project.

## Completed

- 999.2 and 999.3: timeout resynchronization and submitted-transfer deletion guard, shipped in Phase 119.
- Test report C-01/C-02/A-02/A-06: corrected thread callback, rate-limit assertion, shared test base, shared encryption config builder; checked during 2026-10-17 triage.

## Historical evidence

- `ROADMAP-before-organization.md`: full previous roadmap and disposition rationale.
- `TEST-HARDENING-REVIEW.md`: April findings plus October dispositions. Remaining old findings are unvalidated historical leads, not automatic future tasks; no blanket test-hardening milestone.

Routine maintenance was not discarded; see ../../MAINTENANCE.md. Existing phase folders and milestone archives remain intact.
