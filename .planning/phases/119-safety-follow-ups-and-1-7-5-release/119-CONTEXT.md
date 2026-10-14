# Phase 119: Safety Follow-ups and 1.7.5 Release - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Sole phase of milestone v1.7.5 Safety Release. Delivers requirements XFER-06, DEL-01, IMP-01, IMP-02, IMP-03, REL-02, REL-03 (see `.planning/REQUIREMENTS.md`):

- LFTP command-boundary resync after a timed-out status command (999.2).
- Explicit submitted-but-unobserved guard in the auto-delete timer (999.3).
- PyPI packaging repair (Dependabot #93 only as relevant).
- Incomplete-import prevention — Obsession incident (IMP-01 + IMP-02, one plan, own regression tests).
- Early per-episode import credit — Days of Hope incident (IMP-03, separate plan, own regression tests).
- 1.7.5 release through Docker/GitHub/PyPI with NAS verification of the tested image.

Fixed by ROADMAP.md; discussion clarified HOW, not WHETHER.

</domain>

<decisions>
## Implementation Decisions

### Root cause framing (from diagnosis, confirmed in discussion)
- **D-01:** The Obsession defect is a *transfer started before the seedbox download finished*. The NAS already runs with `use_temp_file = True`; lftp copied what existed on the seedbox, completed its pget against the short remote file, and renamed the temp file to the final name. The fix must gate the transfer (start and/or release-to-final-path) on proven seedbox completion — not only re-check before marking local completion.
- **D-02:** Temp-file transfer (write under a non-importable name, rename only after completion is verified) becomes mandatory for automatic transfers regardless of the `use_temp_file` setting, so an interrupted, retried, crashed or restart-recovered copy is never at an importable path (IMP-01). Planner decides whether the setting is removed, ignored, or forced, and how the rename is deferred until verification passes.

### Completion evidence (IMP-02)
- **D-03:** Sonarr/Radarr download-queue state is the primary completion evidence. Size and mtime stability are supporting evidence only and can never establish completion on their own.
- **D-04:** Each of these keeps completion unproven and the item held: Sonarr/Radarr API unavailable or erroring; ambiguous queue match (more than one candidate release); no queue entry found; queue entry still downloading/queued/paused. Elapsed time never grants completion.
- **D-05:** A successful API response alone is insufficient — planning must pin down the specific queue fields and matching rules that prove download completion. Planning MUST verify the actual Sonarr v3/v4 and Radarr v3 queue/API semantics needed to identify a release and establish completion (fields, status values, download-client completion signal, how the seedbox path/title maps to the queue entry, behaviour after import when the entry leaves the queue). The incident diagnosis establishes the problem, not the solution details.
- **D-06:** The arr URLs and API keys already exist in config (`Config.Sonarr` / `Config.Radarr`, currently used only by the web test-connection handler) and are configured on the NAS. No new user setup step; API keys stay secrets (never logged).

### Items Sonarr/Radarr can't vouch for
- **D-07:** Items whose completion can't be established (including items with no queue entry — absence does not prove an item is unrelated to Sonarr/Radarr) are held, never auto-transferred. No exemption for "non-arr" items.
- **D-08:** Manual release override: the user can deliberately release a held item. The existing Queue action must NOT silently bypass safety — releasing a held/unverified item requires an explicit confirmation: "Completion could not be verified. Transfer and release this item anyway?" The approval applies only to that one transfer attempt (not persisted for future attempts/re-queues).
- **D-09:** Manual release is a recorded, explicit exception to IMP-01/IMP-02 and a small, owner-approved exception to the phase's "no UI features" boundary. Normal automatic transfers keep the strict checks. The override bypasses source-completion verification only: the local copy must still finish transferring (temp-file + verified local completion) before it becomes importable.

### Hold visibility
- **D-10:** A held item shows as waiting in the existing file list, using existing status display, with its reason available there: "Sonarr unavailable" / "Radarr unavailable", "Ambiguous match", "Still downloading" and "No matching queue entry" (required). No new screen, no bell notification this milestone.
- **D-11:** Log on hold start, reason change, and hold clear — not on every retry. When verification succeeds the hold clears automatically and the transfer proceeds.

### Retry behaviour
- **D-12:** Retry indefinitely; never release because a timeout expired. Resume automatically when Sonarr/Radarr returns.
- **D-13:** Capped retry backoff, and queue checks shared across waiting items (one queue fetch per arr per check cycle, not one API request per file per scan), so an outage doesn't hammer the APIs.

### Early per-episode credit (IMP-03)
- **D-14:** Credit and persist an import notice only for a uniquely identified, fully transferred episode while siblings still transfer; credit survives restart. Credit alone never authorizes whole-folder deletion — deletion requires both a complete folder transfer and import coverage of every required video. Existing ambiguous-filename rejection (Phase 116, IMPORT-01/02) stays in force.

### Carried-forward requirements (no new decisions needed)
- **D-15:** XFER-06, DEL-01, REL-02, REL-03 as written in REQUIREMENTS.md / ROADMAP.md success criteria. REL-03 smoke checks: startup, real transfer, import visibility and webhook handling, automatic cleanup, settings persistence, restart; successful scan after any startup scanner error (other startup errors need their own resolution).

### Claude's Discretion
- Exact gating point(s) in the pipeline (auto-queue acceptance vs. lftp completion/rename vs. both), data structures for hold state, backoff constants, queue-match algorithm (subject to D-04/D-05), persistence format for per-episode credit, PyPI packaging fix approach, LFTP resync mechanism.

</decisions>

<specifics>
## Specific Ideas

- Confirmation text for manual release (verbatim): "Completion could not be verified. Transfer and release this item anyway?"
- Hold reasons as user-facing labels: "Sonarr unavailable", "Radarr unavailable", "Ambiguous match", "Still downloading".
- Incident evidence to turn into regressions: Obsession — remote 55,477,377,022 B, Radarr imported 54,676,946,944 B, re-queue at 20:47:48 then import at 20:48:32; Days of Hope — three Sonarr notices rejected "no transfer evidence" ~1 min before the root committed, then 24 partial-import deferrals and give-up.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/REQUIREMENTS.md` — XFER-06, DEL-01, IMP-01..03, REL-02, REL-03 (locked wording)
- `.planning/ROADMAP.md` §"Phase 119" — scope items 1–5, success criteria 1–7, scope boundary

### Incident diagnosis
- `.planning/debug/done-group-no-auto-delete.md` — production evidence and root causes for Obsession (IMP-01/02) and Days of Hope (IMP-03), recommended fix direction
- `.planning/debug/extract-staging-autodel-rearm.md` — prior auto-delete re-arm / extraction staging design (related deferral/re-arm machinery)

### Carried-forward backlog
- `.planning/ROADMAP.md` §"Phase 999.2", §"Phase 999.3" — original problem statements for XFER-06 and DEL-01
- `.planning/ROADMAP.md` §"Phase 999.1" — payload-size evidence, explicitly deferred (does not satisfy IMP-02)
- `.planning/milestones/v1.7.4-MILESTONE-AUDIT.md` — source of 999.3 and the PyPI failure note

### Prior phase decisions
- `.planning/milestones/v1.7.4-ROADMAP.md` and v1.7.4 phase records (116 import safety, 117 transfer-state safety, 118 durable state) — ambiguous-match rejection, `None` = status unavailable, submitted-unobserved protection, atomic persist

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/python/common/config.py` `Config.Sonarr` / `Config.Radarr` (enabled, url, api_key [secret]) — arr API credentials already present.
- `src/python/web/handler/config.py` — existing arr test-connection call (pattern for HTTP to Sonarr/Radarr).
- `src/python/controller/lftp_manager.py` `submitted_unobserved_file_names()` and `CommandProcessor._is_submitted_unobserved` (409 path) — reuse for DEL-01.
- `src/python/lftp/lftp.py`, `job_status_parser.py` — status returns `None` when unavailable (Phase 117); resync work for XFER-06 lives here.
- `src/python/common/persist.py` atomic `to_file` (Phase 118) — use for persisting per-episode credit (IMP-03) and any hold state.

### Established Patterns
- Webhook evidence gate: `Controller.__check_webhook_imports` (`src/python/controller/controller.py` ~553) — "no transfer evidence" branch is where Days of Hope notices were discarded.
- Auto-delete scheduling/execution: `__schedule_auto_delete` (~680), `__execute_auto_delete` (~750), `auto_delete_manager.py` coverage/deferral (partial-import deferral, 24-attempt give-up).
- Auto-queue acceptance: `src/python/controller/auto_queue.py` `sweep_accept` (~283) with remote/local stability seconds — where transfers currently start on size stability.
- `model_pipeline.py` downloaded-commit logic (references staging-area import).

### Integration Points
- New arr queue client (shared per check cycle, capped backoff) feeding auto-queue acceptance and/or the lftp rename/commit step.
- Model file state + Angular file list (`src/angular/src/app/services/files/model-file.ts`, `view-file.ts`, `pages/files/transfer-row.component.ts`, `common/localization.ts`) for the waiting state + reason and the manual-release confirmation.
- Packaging: `src/python/pyproject.toml` (hatchling build backend, wheel `packages = ["."]`) and the release CI publish job.

</code_context>

<deferred>
## Deferred Ideas

- Bell notification for long holds — not this milestone.
- Backlog 999.1 payload-size evidence — stays deferred (defense in depth only).
- Reliability milestone work — Phase 120+.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` — remove PYTHONWARNINGS cgi filter once webob drops stdlib cgi; blocked upstream and unrelated to 1.7.5 safety scope.

</deferred>

---

*Phase: 119-safety-follow-ups-and-1-7-5-release*
*Context gathered: 2026-10-14*
