# Phase 120 — Deferred Items

Out-of-scope discoveries logged during execution. Not fixed in this phase.

## From Plan 05 (live capture)

1. **Webhook handler INFO logs are dropped (pre-existing, not Sonarr-5-caused).**
   `src/python/web/handler/webhook.py` uses `logging.getLogger(__name__)` (`web.handler.webhook`), which is outside
   the app's configured `seedsyncarr` logger, so its INFO lines never reach the app log or stdout. For example, `<source> webhook
   test event received` has 0 occurrences in the sandbox log history even though Test events are answered 200
   `Test OK`. Controller-side webhook lines (`webhook import enqueued`, `Recorded webhook import`) are unaffected.
   Impact: there is no app-log trace of Test events or of other handler-level INFO decisions. Suggested follow-up (Reliability or
   observability backlog): attach handler module loggers to the app logger, e.g. as a child of the context logger,
   with a regression test. Evidence: 120-CAPTURE-NOTES.md, "Observability finding".

## Completion-gate prune logs as "cleared" (found in 120-05 live capture, 2026-10-20)

`CompletionGate._run(prune=True)` drops holds of roots that left the AutoQueue stability sweep (for
example, the remote size changed) through `_clear_hold`, which logs `Completion hold cleared for '<root>'`.
That is the same message as a proof-based release. Observed at 17:01:49 app clock on the sandbox: no queue
or transfer followed, the root was re-held at 17:03:20, and it was released on a completed snapshot at
17:03:21. This is not a safety gap and is version-independent; the message is misleading for operators and
for evidence review. Suggested fix: a distinct message (e.g. `Completion hold dropped for '<root>' (no longer
a queue candidate)`) for the prune path. Out of scope for phase 120.
