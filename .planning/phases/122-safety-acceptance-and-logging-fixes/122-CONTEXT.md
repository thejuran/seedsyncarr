# Phase 122: Safety Acceptance and Logging Fixes - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Three deliverables, fixed by ROADMAP.md (requirements SAFE-01, SAFE-02, LOG-01, LOG-02):

1. **LOG-01 / LOG-02 (code):** make web-handler INFO lines reach the app log, and give the completion gate a distinct "dropped" message for hold removals that are not a proof-based release. Each fix has a regression test that fails before and passes after.
2. **SAFE-01 (live acceptance):** on a running build in the NAS sandbox (`seedsyncarr-test`; production untouched), exercise extraction, import and auto-delete and record evidence (log excerpts, timestamps, resulting file state). This completes the extraction/import half of `119-VERIFICATION.md`. The browser half passed 2026-10-18.
3. **SAFE-02 (records):** reconcile `.planning/debug/done-group-no-auto-delete.md` and `.planning/debug/extract-staging-autodel-rearm.md`. Each finding is marked "verified fixed (evidence)" or "remaining operator cleanup". Neither record closes just because its code shipped.

Phase 119 import safeguards (early credit, pending-notice revalidation, arm-on-commit, Waiting holds, one-shot manual release) are **exercised, not rebuilt**.

</domain>

<decisions>
## Implementation Decisions

### Build under test and sequencing
- **D-01:** Order: the LOG-01/LOG-02 fixes land on `main` first (PR merged, CI green). The SAFE-01 acceptance checks then run on the build of that merge commit. The evidence then covers the code 1.8.0 will ship (including Phase 121), and the newly visible log lines become part of it.
- **D-02:** Deploy that build to `seedsyncarr-test` **only**, as the CI-published `:dev` image **pinned by exact digest** (the merge commit's digest; the NAS cannot build images). Owner-approved exception to the "never `:dev`" rule, for the sandbox only. Before changing it, record the sandbox's current image pin (`ghcr.io/thejuran/seedsyncarr:1.7.6` today). Record the deployed digest in the evidence. At phase end, restore the original pin and verify the restore. Production (`seedsyncarr`, 1.7.6) is never touched.
- **D-03:** If any acceptance check fails: record the failure with evidence, diagnose the cause, and bring the owner the proposed fix and its scope **before** changing any code. Do not rebuild Phase 119 safeguards without the owner's go-ahead. SAFE-01 is not marked passed on a partial run.

### Test material (SAFE-01)
- **D-04:** Import and auto-delete are driven by **synthetic material**: fake files in the sandbox's own seedbox folder (`remote_path = ~/v5test`), plus correctly HMAC-signed Sonarr-style `Download` webhooks posted to the sandbox's `/server/webhook/sonarr`, deliberately timed. No tracker grab, and the sandbox Sonarr library is not modified. The real Sonarr-queue completion gate ("Still downloading" hold, then release once Sonarr reports completion) is covered by citing Phase 120's live capture (`120-CAPTURE-NOTES.md`, `120-SON5-EVIDENCE.md`), not re-captured.
- **D-05:** A synthetic root has no Sonarr queue entry, so the gate holds it as "No matching queue entry" (Waiting). The **one-shot manual release** is the intended way to move it forward, which also exercises that safeguard. Use one release per root, and show that the release applies to that transfer only.
- **D-06:** Scenarios to exercise, each with recorded evidence:
  - (a) **Early per-episode credit:** a multi-file root where a child's import webhook arrives while sibling children are still transferring (the Days-of-Hope Case A shape). The child credit is recorded, the root is not committed early, and no auto-delete is armed before commit.
  - (b) **Arm-on-commit:** once the root commits as downloaded with full video coverage, auto-delete arms. After the 300 s delay the local copy is deleted (sandbox has `dry_run = False`).
  - (c) **Pending-notice revalidation / deferral paths:** webhooks for incomplete or not-yet-committed content are not lost, and are re-evaluated rather than dropped.
  - (d) **Restart persistence:** after one child is credited and while its siblings are still pending, restart `seedsyncarr-test` once. Confirm the credit survives the restart and the whole-folder delete still waits for full coverage.
  - (e) **Waiting hold + one-shot manual release** (see D-05).
- **D-07:** **Extraction:** use a **multi-part RAR of roughly 1 GB** (a single dummy `.mkv` inside, split into volumes), matching the Burbs incident shape. The sandbox already has `auto_extract = True` and `use_local_path_as_extract_path = True`. Evidence must show: while extraction runs, the release folder holds only the RAR volumes and the `.seedsyncarr-extracting/<root>/` staging dir grows; the UI/model never lists the staging dir; the full-size file appears in the release folder only at the end. Also exercise the **auto-delete re-arm path**: an import webhook accepted while the root is EXTRACTING produces `Auto-delete deferred for '<root>' (attempt n/24): ... EXTRACTING ...`, followed by `Auto-deleted local file '<root>'` after extraction completes.
- **D-08:** Clean up all synthetic material afterwards: the seedbox `~/v5test` probe files and archive, and the sandbox `/downloads` leftovers. Any temporary sandbox setting changes are restored on every exit path, the Phase 120 teardown discipline.

### Incident record reconciliation (SAFE-02)
- **D-09:** **Read-only production inspection is allowed**: `ls`/`stat`, reading `/volume1/docker/seedsync/log/` and `controller.persist`, and GET-only Sonarr/Radarr API calls. No restarts, deletes, config edits, arr commands or writes of any kind on production. Use it to make the remaining-cleanup list factual, e.g. whether the Days of Hope root or The Burbs 77 GB local copy is still on disk. Note: the app-log clock is the NAS host clock + 1h.
- **D-10:** Each record gets a per-finding table: Done-group Case A and Case B; extract-staging Bug 1, Bug 2, and deep-review items D–G. Each row reads **"verified fixed (evidence)"** with a link or quote to the SAFE-01 evidence or test, or **"remaining operator cleanup"**, or (for D–G) **"deferred"**. Also fill the empty `fix:`/`verification:` fields in `done-group-no-auto-delete.md` with the Phase 119 plans and commits that delivered the fixes.
- **D-11:** Remaining production cleanup is handed to the owner as an **exact checklist**: path, size, what to delete or verify, and how to confirm it's done. **Nothing is performed on production in this phase.** Items stay open until the owner confirms.
- **D-12:** **Close rule:** a record is marked resolved and moved to `.planning/debug/resolved/` only when every finding is "verified fixed (evidence)" **and** the owner has confirmed all operator cleanup. Otherwise it stays in `.planning/debug/` with a status like `fixes_verified_cleanup_pending`. Deferred D–G items do not block closing, but each is carried by name to the ROADMAP backlog.

### Logging fixes (LOG-01 / LOG-02)
- **D-13:** **Logger scope: all four modules** that log through `logging.getLogger(__name__)` outside the app's `seedsyncarr` logger: `src/python/web/handler/webhook.py`, `src/python/web/handler/controller.py`, `src/python/web/handler/config.py`, `src/python/web/rate_limit.py`. Same cause, same fix. Attach them under the app logger (the context logger / `getChild` pattern used elsewhere, e.g. `web_app.py`), following whatever the codebase already does.
- **D-14:** Before merging, review every newly visible line in those modules and confirm none logs secrets, tokens, auth headers or webhook bodies. Includes the `logger.exception` in the Test Connection path in `config.py`, which must not expose credentials.
- **D-15:** Tests: **webhook** gets the required fail-before/pass-after regression (a Test event produces `<source> webhook test event received` at INFO under the app logger). The other three modules each get a lighter check that their lines reach the app logger.
- **D-16:** **"Dropped" covers every hold removal without proof:** (1) the prune path, a root that left the stability sweep / candidate set (this also covers a hold left behind after a one-shot manual release), and (2) the no-arr-enabled path in `CompletionGate._run` (step 2). "Cleared" is used **only** for the proof-based release in `_record` (verdict proven).
- **D-17:** **Exact wording** (all INFO, values through `sanitize_log_value`):
  - Release (unchanged): `Completion hold cleared for '<root>'`
  - Prune: `Completion hold dropped for '<root>' (no longer a queue candidate)`
  - No arr: `Completion hold dropped for '<root>' (no Sonarr/Radarr integration enabled)`
  Keeping "cleared" unchanged keeps existing log searches and Phase 120 evidence scripts valid.
- **D-18:** The LOG-02 regression test covers both paths: the proof-based release logs "cleared" and not "dropped"; the prune path (and the no-arr path) logs "dropped" and not "cleared". It fails against the current single-message `_clear_hold`.

### Claude's Discretion
- How the synthetic webhooks are built and signed (read the HMAC secret from the sandbox config inside a `umask 077` area; never commit or log it), and how fake files are sized and timed so children finish at different times.
- The RAR creation tooling and volume size (on the seedbox, or locally then uploaded), as long as the shape matches D-07.
- Evidence file layout (e.g. `122-SAFE01-EVIDENCE.md`). Use `<nas-tailscale-ip>`-style placeholders for addresses, and keep secrets out of committed files.
- Internal shape of the `_clear_hold` change (a reason parameter vs separate methods), provided D-17 wording and D-18 tests hold.
- Ordering of the live scenarios, and whether some share a single root.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 122: Safety Acceptance and Logging Fixes" — goal and 5 success criteria
- `.planning/REQUIREMENTS.md` — SAFE-01, SAFE-02, LOG-01, LOG-02 wording; Out of Scope (no rebuild of Phase 119 safeguards)

### Phase 119 verification being completed (SAFE-01)
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-VERIFICATION.md` — what was verified in code/unit tests; this phase adds the running-build extraction/import evidence
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-HUMAN-UAT.md` — the 2026-10-18 browser half (probe-file method, Waiting badge, manual-release dialog)
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-CONTEXT.md` — Phase 119 decisions behind early credit, holds, manual release
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md` — prior NAS smoke-test evidence format

### Incident records (SAFE-02)
- `.planning/debug/done-group-no-auto-delete.md` — Case A (dropped pre-commit webhooks) and Case B (truncated import); fix/verification fields empty
- `.planning/debug/extract-staging-autodel-rearm.md` — Bug 1 (extraction staging), Bug 2 (auto-delete re-arm), deferred deep-review items D–G; status awaiting_human_verify; its `next_action` describes the exact NAS checks D-07 performs

### Log findings (LOG-01 / LOG-02)
- `.planning/phases/120-sonarr-5-compatibility/deferred-items.md` — both findings, with suggested fixes
- `.planning/phases/120-sonarr-5-compatibility/120-CAPTURE-NOTES.md` §"Observability finding" and §"Early 'Completion hold cleared' at 17:01:49" — live evidence of both defects
- `.planning/phases/120-sonarr-5-compatibility/120-SON5-EVIDENCE.md` — real Sonarr-queue gate evidence cited by D-04

### Sandbox operation precedent
- `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` and `120-RESEARCH.md` — sandbox teardown/restore discipline, NAS command patterns
- `.planning/codebase/TESTING.md`, `.planning/codebase/CONVENTIONS.md` — test and logging conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `context.logger.getChild(...)`: the app's logger pattern (e.g. `src/python/web/web_app.py:69`). Handler loggers should hang off the same `seedsyncarr` tree.
- `sanitize_log_value` (used throughout `completion_gate.py`): CWE-117 sanitizing for log values.
- `120-webhook_sink.py`, `120-teardown.sh`: prior sandbox tooling to adapt for webhook capture and restore-on-exit.
- Existing tests: `test_auto_delete_rearm.py`, `test_dispatch_staging.py`, and the completion-gate tests are the models for the LOG-02 test and the unit cross-references in evidence.

### Established Patterns
- `CompletionGate._clear_hold(name)` (`src/python/controller/completion_gate.py:427`) is the single logging point, called from the no-arr path (~208), the prune path (~236) and the proof-based release in `_record` (~416).
- `src/python/web/handler/webhook.py:17` / `:142`: `logger = logging.getLogger(__name__)` → `"{} webhook test event received"` is never emitted. Same module-logger pattern in `web/handler/controller.py`, `web/handler/config.py`, `web/rate_limit.py`.
- Webhook endpoints: `/server/webhook/sonarr|radarr`, behind the require-secret guard, rate limit (60/60 s) and HMAC check.
- CI gate: full Python suite plus whole-tree `ruff check src/python/`, as separate gates; regressions run red first.

### Integration Points
- Sandbox: container `seedsyncarr-test` (UI/API on :8801), config `/volume1/docker/v5test/seedsyncarr/settings.cfg`, downloads `/volume1/data/v5test/torrents` → `/downloads`, seedbox remote `~/v5test`, Sonarr → `http://sonarr-v5:8989`, Radarr disabled, AutoDelete enabled (300 s, not dry-run), auto_extract on, in-place extraction.
- Production (read-only for this phase): container `seedsyncarr` 1.7.6, logs `/volume1/docker/seedsync/log/seedsyncarr.log`, persist `/volume1/docker/seedsync/controller.persist`.
- NAS docker must be invoked as `sudo /usr/local/bin/docker ...` (absolute path).

</code_context>

<specifics>
## Specific Ideas

- The extraction evidence should mirror the Burbs incident timeline: archive parts synced → in-place unrar starts → (formerly) the partial mkv visible → now staging only → full-size publish.
- The early-credit scenario should mirror Days of Hope: multiple video children, child webhooks arriving before the root commits.
- Phase 120 found that log messages can mislead evidence review. The SAFE-01 evidence should quote the new `dropped` and `cleared` lines where they occur.

</specifics>

<deferred>
## Deferred Ideas

- Extract-staging deep-review items D–G stay deferred. Carry each by name to the ROADMAP backlog during SAFE-02 reconciliation (D-12).
- A real-grab end-to-end run on the new build was considered and not chosen. Phase 126's REL-06 NAS smoke test (restart, transfer, integration, cleanup on the 1.8.0 digest) covers the release image.
- Not discussed: research-before-questions was enabled in config but skipped for this phase, because the decisions are project-specific verification choices, not ecosystem questions.

</deferred>

---

*Phase: 122-safety-acceptance-and-logging-fixes*
*Context gathered: 2026-10-21*
