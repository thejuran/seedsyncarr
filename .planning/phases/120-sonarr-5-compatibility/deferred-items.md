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
