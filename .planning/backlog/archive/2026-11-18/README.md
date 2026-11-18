# Roadmap reconciliation — 2026-11-18

Original backlog entries below are preserved, not new work.

- **999.4 closed at release:** [Phase 126 verification](../../../phases/126-release-1-8-0/126-VERIFICATION.md) records braces@3.0.3 and no fix needed. Reopen only for a newly applicable advisory or affected dependency change; current remote advisory state was not checked.
- **Symlink publication fix already delivered:** current `src/python/controller/extract/dispatch.py` strips symlinks before moving staged output. `src/python/tests/unittests/test_controller/test_extract/test_dispatch_staging.py::test_symlinks_in_extracted_output_are_dropped_before_publish` covers top-level, nested and dangling links. The review inspected source/tests; it did not rerun that test. Reopen for a reproduced bypass or changed extraction behavior.

## Original entries

### 999.4: Recheck the braces/karma dev-test advisory

**Scope:** Bounded maintenance side task, separate from milestone scope. recheck the recorded braces/karma dev-test advisory and related deferred PRs (#128/#125/#117), including current affected versions and runtime/build exposure. Apply the smallest supported fix if still relevant, with the affected build/test checks. Records classify it as dev/test-only; current advisory status has not been refreshed. This is not a separate milestone or a general test-runner rewrite. It is rechecked within REL-05 (Phase 126) as part of the pre-tag Dependabot review; that recheck records the outcome, and the item is rolled into 1.8.0 only if the fix is cheap or current evidence establishes material exposure.


### Deferred: Extract-staging symlink hardening

Refuse symlink entries at publish time in `ExtractDispatch.__publish_staged_output` (skip with a WARNING), closing a pre-existing exposure where patool could write a symlink straight into the release folder. Security HIGH, CWE-59. Source: `.planning/debug/extract-staging-autodel-rearm.md` item C.

