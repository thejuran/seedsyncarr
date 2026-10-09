# Phase 117: Transfer-State Safety - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning

<domain>
## Phase Boundary

SeedSyncarr never makes a re-queue, auto-queue, or delete decision from a transfer state it did not actually observe. Three fixes on the LFTP status → model → auto-queue path, exactly as defined in the approved spec (`docs/superpowers/specs/2026-10-08-safety-patch-design.md` §Phase B):

- **B1** — LFTP `jobs -v` parser never consumes another job's header (XFER-01).
- **B2** — unparseable status is reported as *unavailable* (`None`), never `[]`; error boundary pinned exactly; no downstream consumer collapses unavailable into "no jobs" (XFER-02, XFER-03).
- **B3** — remote and local size-stability gates advance only on the clock of successful scans; UI "last scan" keeps its meaning (XFER-04, XFER-05).

Out of scope (spec): path-mapping redesign, persistence changes, load-side recovery, any version bump/tag (REL-01 is Phase 118).
</domain>

<decisions>
## Implementation Decisions

### UI while status is unavailable
- **D-01:** While LFTP status is unavailable, active downloads keep their **last-known** state/progress frozen — no new UI indicator, no frontend or e2e changes in this phase. Protection (active-downloading list, no re-queue/extract/delete) is held for the full duration of unavailability.
- **D-02:** Note (corrected during discussion): the escalation raise at failure `MAX_CONSECUTIVE_STATUS_ERRORS + 1` is caught by `LftpManager.status()` and returned as `None`, so a persistent parse failure keeps status unavailable indefinitely (not a controller restart). That is already today's behavior for failures ≥3; this phase brings failures 1..2 in line. The freeze-for-the-duration behavior was accepted with this understanding.

### Stability across scan outages (B3)
- **D-03:** Stability is measured **between successful observations only**. Two successful scans with matching sizes, separated by at least the stability window, satisfy the gate — even if failed scans occurred in between. Failed scans can neither advance the clock nor reset it.
- **D-04:** If the first successful scan after recovery shows a **different** size, the stability window restarts (from that successful scan).
- **D-05:** Both the "matching size across an outage → stable" case and the "changed size after outage → window restarts" case are tested for **both** the remote clock (XFER-04) and the local clock (XFER-05).
- **D-06:** The UI-facing `latest_remote_scan_time` / `latest_local_scan_time` (serialized in `web/serialize/serialize_status.py`) keep their current meaning; stability uses a separate successful-scan clock (spec-permitted approach).

### Parser audit scope (B1)
- **D-07:** Audit is limited to **header-swallowing**: fix every confirmed "consume next line" site that can consume another job's header (pget data line in `PgetJobParser.parse_header`, `CHUNK_HEADER` handling, mirror-empty / connecting-line handling, and any equivalent in `QueueParser` / `ActiveJobsParser`).
- **D-08:** Each confirmed site gets its own regression test (fails before fix, passes after), plus checks that valid existing `jobs -v` output still parses unchanged.
- **D-09:** Unrelated parser weaknesses found during the audit are **recorded for later** (deferred), not changed in this patch.

### Carried forward (locked by spec / prior phases)
- Contract: `None` = unavailable at `LftpManager.status()`; `[]` = genuinely no jobs (still clears active state).
- `MAX_CONSECUTIVE_STATUS_ERRORS` (currently 2, `lftp/lftp.py:12`) and the escalation threshold stay unchanged; boundary pinned exactly (1..N tolerated & unavailable, N+1 raises at the `Lftp` layer, success resets).
- Owner planning note: test **downstream behavior**, not just the `None` return — active transfers remain protected with no unintended re-queue, extraction, or deletion while status is unavailable.
- Every targeted regression test must be shown to fail against the old behavior before its fix (REL-01 gate 1).
- CI gate: full Python suite green AND `ruff check src/python/` clean whole-tree; `fail_under` ≥ 88.

### Claude's Discretion
- Exact name/location of the successful-scan clock(s) (e.g. new status properties vs. tracking inside `AutoQueue`).
- Internal structure of the parser "peek before pop" fix.
- Test file organization within existing test modules.

</decisions>

<specifics>
## Specific Ideas

- Owner wording on stability: "Two successful observations with matching sizes, separated by the stability window, satisfy the gate. Failed scans cannot advance it themselves and don't reset it. If the first successful scan after recovery shows a different size, restart the window. Test both cases for the remote and local clocks."
- Owner wording on the audit: "Keep this patch focused on preventing lost or misreported jobs."
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Fix contracts and regression tests
- `docs/superpowers/specs/2026-10-08-safety-patch-design.md` §Phase B (B1, B2, B3) and §Release gate — authoritative fix contracts and required regression tests
- `.planning/REQUIREMENTS.md` — XFER-01..XFER-05 acceptance wording
- `.planning/ROADMAP.md` §"Phase 117: Transfer-State Safety" — success criteria 1-5 and owner planning notes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LftpManager.status()` (`src/python/controller/lftp_manager.py:140`) already returns `Optional[List]` and maps exceptions/stall-backoff to `None` — the downstream `None` contract largely exists.
- `ModelPipeline` (`src/python/controller/model_pipeline.py:163`) only calls `set_lftp_statuses` when statuses is not None; scan results are only applied when `not .failed` (lines 157-161).
- `Controller._update_active_file_tracking` (`src/python/controller/controller.py:421`) only replaces the active-downloading list when statuses is not None.

### Established Patterns
- `Lftp.status()` (`src/python/lftp/lftp.py:298`) is the defect site for B2: tolerated errors return `[]` → should return `None` (type becomes `Optional[List[LftpJobStatus]]`).
- Parser: `PgetJobParser.parse_header` (`src/python/lftp/job_status_parser.py:263`, unconditional `lines.pop(0)` at ~278); `MirrorJobParser` (~380); `QueueParser` (~433-494); `ActiveJobsParser` (~546, ~594) — audit sites.
- `Controller._update_controller_status` (`controller.py:~499-513`) sets `latest_remote_scan_time` / `latest_local_scan_time` from every scan incl. failed ones — B3 defect site.
- `AutoQueue` stability gates (`src/python/controller/auto_queue.py:~255-290`) read those clocks and keep `__remote_size_history` / `__local_idle_history` keyed by scan time.

### Integration Points
- Tests: `src/python/tests/unittests/test_lftp/` (parser, lftp), `src/python/tests/unittests/test_controller/` (`test_auto_queue.py`, `test_lftp_manager.py`, `test_controller_unit.py`, `test_controller.py`).
- Extract dispatch also calls a `.status()` (`controller/extract/extract_process.py:84`) — unrelated (extract dispatch, not LFTP) but confirm during the downstream audit.

</code_context>

<deferred>
## Deferred Ideas

- A visible "transfer status unavailable" indicator in the UI (D-01 chose frozen last-known for this patch) — candidate for a future UI phase.
- Unrelated LFTP parser weaknesses discovered during the B1 audit — record in the phase summary/backlog, not fixed here (D-09).

</deferred>

---

*Phase: 117-transfer-state-safety*
*Context gathered: 2026-10-08*
