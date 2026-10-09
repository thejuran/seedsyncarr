# Phase 117: Transfer-State Safety - Research

**Researched:** 2026-10-08
**Domain:** Python backend. Covers the LFTP `jobs -v` parser, the status-availability contract, and the auto-queue stability clocks.
**Confidence:** HIGH for the code-path analysis (every claim was traced in the repo at `2e5be14`). MEDIUM for the claim that lftp really emits a `\chunk` line with no data line: this comes from reading the lftp source, not from captured output.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### UI while status is unavailable
- **D-01:** While LFTP status is unavailable, active downloads keep their **last-known** state/progress frozen — no new UI indicator, no frontend or e2e changes in this phase. Protection (active-downloading list, no re-queue/extract/delete) is held for the full duration of unavailability.
- **D-02:** Note (corrected during discussion): the escalation raise at failure `MAX_CONSECUTIVE_STATUS_ERRORS + 1` is caught by `LftpManager.status()` and returned as `None`, so a persistent parse failure keeps status unavailable indefinitely (not a controller restart). That is already today's behavior for failures ≥3; this phase brings failures 1..2 in line. The freeze-for-the-duration behavior was accepted with this understanding.

#### Stability across scan outages (B3)
- **D-03:** Stability is measured **between successful observations only**. Two successful scans with matching sizes, separated by at least the stability window, satisfy the gate — even if failed scans occurred in between. Failed scans can neither advance the clock nor reset it.
- **D-04:** If the first successful scan after recovery shows a **different** size, the stability window restarts (from that successful scan).
- **D-05:** Both the "matching size across an outage → stable" case and the "changed size after outage → window restarts" case are tested for **both** the remote clock (XFER-04) and the local clock (XFER-05).
- **D-06:** The UI-facing `latest_remote_scan_time` / `latest_local_scan_time` (serialized in `web/serialize/serialize_status.py`) keep their current meaning; stability uses a separate successful-scan clock (spec-permitted approach).

#### Parser audit scope (B1)
- **D-07:** Audit is limited to **header-swallowing**: fix every confirmed "consume next line" site that can consume another job's header (pget data line in `PgetJobParser.parse_header`, `CHUNK_HEADER` handling, mirror-empty / connecting-line handling, and any equivalent in `QueueParser` / `ActiveJobsParser`).
- **D-08:** Each confirmed site gets its own regression test (fails before fix, passes after), plus checks that valid existing `jobs -v` output still parses unchanged.
- **D-09:** Unrelated parser weaknesses found during the audit are **recorded for later** (deferred), not changed in this patch.

#### Carried forward (locked by spec / prior phases)
- Contract: `None` = unavailable at `LftpManager.status()`; `[]` = genuinely no jobs (still clears active state).
- `MAX_CONSECUTIVE_STATUS_ERRORS` (currently 2, `lftp/lftp.py:12`) and the escalation threshold stay unchanged; boundary pinned exactly (1..N tolerated & unavailable, N+1 raises at the `Lftp` layer, success resets).
- Owner planning note: test **downstream behavior**, not just the `None` return — active transfers remain protected with no unintended re-queue, extraction, or deletion while status is unavailable.
- Every targeted regression test must be shown to fail against the old behavior before its fix (REL-01 gate 1).
- CI gate: full Python suite green AND `ruff check src/python/` clean whole-tree; `fail_under` ≥ 88.

### Claude's Discretion
- Exact name/location of the successful-scan clock(s) (e.g. new status properties vs. tracking inside `AutoQueue`).
- Internal structure of the parser "peek before pop" fix.
- Test file organization within existing test modules.

### Deferred Ideas (OUT OF SCOPE)
- A visible "transfer status unavailable" indicator in the UI (D-01 chose frozen last-known for this patch) — candidate for a future UI phase.
- Unrelated LFTP parser weaknesses discovered during the B1 audit — record in the phase summary/backlog, not fixed here (D-09).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XFER-01 | A pget job with no data line never swallows the next job's header. Every job appears with its correct name and state. The other next-line-consuming sites are audited. | §B1 Site Audit: 10 sites classified. Two confirmed (pget data line, `\chunk`) plus one pathological (mirror-empty "Getting file list"). Fixture shapes are under Code Examples. A probe over all 126 parser tests showed 0 consumed data lines that fail the chunk-data patterns, so peek-before-pop keeps current output unchanged. |
| XFER-02 | Unparseable status is reported as unavailable, never `[]`. Active files keep their state and protection, and no consumer turns unavailable back into "no jobs". | §B2 Consumer Trace. Every consumer except `Lftp.kill()` already guards `None`. `kill()` would crash with a `TypeError` on `None` and must raise `LftpJobStatusParserError` instead. The composed downstream tests are listed under Validation Architecture. |
| XFER-03 | The boundary is pinned: failures 1..2 return unavailable, failure 3 raises, a success resets the counter, and an empty status still clears active state. | §B2 Boundary pinning. A unit-level `Lftp` harness with mocked pexpect already exists (`test_lftp_log_sanitization.py::_make_lftp_with_mocked_process`). 4 integration tests that pin `[]` must flip to `None`. |
| XFER-04 | Remote stability runs only on the successful-scan clock. The UI "last scan" keeps its meaning. | §B3 Clock design. Add `ControllerStatus.latest_successful_remote_scan_time`, set only when `not remote_scan.failed`. AutoQueue stability reads it. The cooldown stays on the UI clock. |
| XFER-05 | The local stability gate also advances only on successful local scans. | §B3. Add `latest_successful_local_scan_time`. Note: the production `LocalScanner` never emits `failed=True` today (it raises a fatal error instead), so this is defense in depth and the tests must inject failed `ScannerResult`s. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

There is no `./CLAUDE.md` in the repo. The user-global `~/.claude/CLAUDE.md` has these directives that apply here:
- **Security (absolute):** never log sensitive data. Keep CWE-117 sanitization (`sanitize_log_value`) on every log line that includes lftp output, filenames or job names. Any new log line in `Lftp.status`/`kill` must follow the existing sanitized pattern.
- **Correctness:** don't swallow exceptions silently; log them at minimum. `Lftp.status` already logs a warning for each tolerated error, so keep it. Guard nullable returns before property access. `Lftp.kill()` iterating `self.status()` is exactly such a site.
- **Follow existing conventions.** Before adding a pattern, check how the repo already solves the problem. Examples: AutoQueue already reads clocks from `context.status.controller.*`, and tests already use the `Controller.__new__` + real `Status()` harness.
- **Division of labor:** technical choices are Claude's. Surface product-visible effects to the owner in plain terms. One small effect exists, see Open Question 1.

Project memory directives:
- CI runs `ruff check src/python/` (whole tree) as a separate gate. Build-verify with ruff on an absolute path: `poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/`. A relative `src/python/` from the wrong cwd gives E902.
- Local full suite hangs in `test_extract_process.py`, and 4 baseline files fail on the host. CI Docker is the full-suite authority. Don't re-diagnose pytest-timeout.
- Deploy by release tag (`:1.7.4`, never `:dev`). The NAS is on 1.7.2/1.7.3. Phase 118 owns the rollback runbook and REL-01.

## Summary

All three defects are confirmed in the code at `2e5be14`, and all three fixes are small and local.

**B1 (parser):** `PgetJobParser.parse_header` pops the line after `sftp://…` without checking it (`job_status_parser.py:277-281`). The `\chunk` handler pops its follower the same way (`:655-660`). lftp's own source shows that both kinds of data line are legitimately absent: `CopyJob::FormatStatus` prints nothing when the copy is `Done()` or `Error()`. When the next line is another job's header, the outcome depends on what follows. A following pget makes the parse raise, because its orphaned `sftp://` line can't be parsed. A following mirror is silently dropped, and its `\transfer` lines get attached to the wrong job. Fix: pop the follower only when it matches `CHUNK_AT`, `CHUNK_AT2` or `CHUNK_GOT`.

**B2 (unavailable vs empty):** this is a one-line defect at `lftp.py:310` (`statuses = []`). Everything downstream already respects `None`: `LftpManager`, `ModelPipeline.feed_model_builder`, `ModelBuilder`, `Controller._update_active_file_tracking`, AutoQueue and auto-delete (via frozen model state). The exception is `Lftp.kill()`, which would hit a `TypeError` on `None`.

**B3 (stability clocks):** `Controller._update_controller_status` sets both UI clocks from failed scans too. Meanwhile `ModelPipeline` keeps the old sizes in the model, because failed scans are not applied. So failed scans age the stability history with no fresh evidence. Fix: add two successful-scan clocks on `ControllerStatus`. These are not serialized, so the UI is unchanged. Point AutoQueue's stability logic at them.

**Primary recommendation:** Commit host-runnable RED tests first. Then make three independent fixes on three disjoint sets of source files (parser, `lftp.py`, and status + controller + auto_queue). Keep the REQUEUE cooldown on the UI clock. Make `Lftp.kill()` raise `LftpJobStatusParserError` when status is unavailable.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parse `jobs -v` text into job statuses (B1) | API / Backend: `lftp/job_status_parser.py` | — | Pure text→struct parsing. No I/O. |
| Status availability contract (`None` vs `[]`) (B2) | API / Backend: `lftp/lftp.py` (`Lftp.status`) | `controller/lftp_manager.py` (exceptions mapped to `None`) | The counter lives in `Lftp`. `LftpManager` is the controller-facing contract. |
| Holding last-known transfer state while unavailable | Backend: `ModelBuilder` keeps `__lftp_statuses`. `Controller` keeps `__active_downloading_file_names` | `ModelPipeline` (None guard) | Freezing works by *not calling* the setters when status is `None`. |
| Scan-success clocks (B3) | Backend: `common/status.py` `ControllerStatus` + `Controller._update_controller_status` | `AutoQueue` (consumer) | Matches the existing pattern: AutoQueue reads clocks from `context.status.controller`. |
| UI "last scan" display | Browser (Angular) via SSE `serialize_status.py` | — | Must stay byte-identical. New fields are NOT added to the serializer. |
| Protection from delete/extract/re-queue | Backend: model state `DOWNLOADING` is outside every deletable/extractable/sweep-accept set | `AutoDeleteManager`, `CommandProcessor` | Frozen `DOWNLOADING` state is the protection mechanism. |

## Standard Stack

No new libraries. The phase uses only what is already in the repo.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 in CI (host poetry venv 3.12; system 3.14) | Runtime | `[VERIFIED: ci.yml setup-python 3.12; poetry venv path py3.12]` |
| pytest | 9.1.1 | Test runner | `[VERIFIED: poetry run python -m pytest --version]` |
| pytest-timeout | installed in poetry venv | 60 s per-test timeout (`pyproject.toml`) | `[VERIFIED: import pytest_timeout ok]` |
| unittest.mock | stdlib | `patch`, `MagicMock`, `patch.object` | Existing convention across the test suite |
| ruff | 0.15.9 host / 0.15.22 CI-pinned | Lint gate | `[VERIFIED: poetry run ruff --version; ci.yml]` |
| re (stdlib) | — | Parser regexes (precompiled in `RegexPatterns`) | Existing |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. slopcheck is not applicable.

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                 every controller cycle (ControllerJob.execute: controller.process() THEN auto_queue.process())
                 ─────────────────────────────────────────────────────────────────────────────────────────────
lftp process ──"jobs -v" text──► Lftp.status()
                                   │ parse OK ──► List[LftpJobStatus] (may be [] = genuinely no jobs); counter := 0
                                   │ parse error #1..2 ──► [B2] None  (today: [])          counter += 1
                                   │ parse error #3+   ──► raise LftpJobStatusParserError   (counter not reset)
                                   ▼
                           LftpManager.status() ── catches LftpError/ParserError, stall backoff ──► Optional[List]
                                   ▼
                           ModelPipeline.update_model()
                             ├─ collect_scan_results() ◄── ScannerProcess queues (pop_latest_result keeps only the LAST result)
                             ├─ feed_model_builder():  remote/local/active applied only if not .failed
                             │                         lftp statuses applied only if not None   (None ⇒ builder keeps last-known)
                             └─ build_and_apply_model(): ModelBuilder → diff → Model; commit DOWNLOADED to persist
                                   ▼
                           Controller._update_active_file_tracking(statuses)   None ⇒ active list unchanged
                           Controller._update_controller_status(remote_scan, local_scan)
                             ├─ UI clocks: latest_remote_scan_time / _failed / _error, latest_local_scan_time  (every scan; unchanged)
                             └─ [B3] latest_successful_{remote,local}_scan_time  (only when not .failed)
                                   ▼
                           AutoQueue.process()
                             ├─ stability history  ◄── [B3] successful-scan clocks (frozen during outages)
                             ├─ sweep_accept (DEFAULT + remote>local + remote-stable + local-idle)
                             ├─ REQUEUE cooldown   ◄── UI remote clock (unchanged)
                             └─ queue_command(QUEUE / EXTRACT) ──► Controller command queue
```

### Recommended Project Structure (files touched)
```
src/python/
├── lftp/job_status_parser.py        # B1: peek-before-pop at pget data line, \chunk, mirror-empty guard
├── lftp/lftp.py                     # B2: status() → Optional[List]; tolerated error → None; kill() raises on None
├── common/status.py                 # B3: two new ControllerStatus properties (not serialized)
├── controller/controller.py         # B3: _update_controller_status sets success clocks when not .failed
├── controller/auto_queue.py         # B3: stability reads success clocks; cooldown unchanged; docstrings
└── tests/
    ├── unittests/test_lftp/test_job_status_parser.py            # B1 full-output regressions (+ existing fixtures unchanged)
    ├── unittests/test_lftp/test_job_status_parser_components.py # B1 component-level (update test_parse_header_consumes_sftp_line? no — still valid)
    ├── unittests/test_lftp/test_lftp_status_contract.py         # NEW: B2 boundary + kill-on-None (host-runnable, mocked pexpect)
    ├── unittests/test_controller/test_transfer_state_safety.py  # NEW: composed B2 downstream + composed B3 controller→AutoQueue
    ├── unittests/test_controller/test_auto_queue.py             # B3 helper updates + D-03/D-04/D-05 cases
    ├── unittests/test_controller/test_lftp_manager.py           # B2 None pass-through
    ├── unittests/test_controller/test_controller_unit.py / test_controller.py  # B3 success-clock setting
    └── integration/test_lftp/test_lftp_protocol.py              # B2: 4 tests flip [] → None (CI-only: needs Docker sshd/testgroup)
```

### Pattern 1: Peek before pop (B1)
**What:** a consume site removes the next line only after a *positive* match on the expected follower shape. Anything else stays in `lines` for the main loop of `ActiveJobsParser.parse` to classify.
**When to use:** every place that reads `lines[0]` and assumes it belongs to the current job.
**Example:**
```python
# Source: repo pattern already used by MirrorJobParser._parse_connecting_header (job_status_parser.py:376-380)
def _is_chunk_data(line: str) -> bool:
    return (RegexPatterns.CHUNK_AT.search(line) is not None or
            RegexPatterns.CHUNK_AT2.search(line) is not None or
            RegexPatterns.CHUNK_GOT.search(line) is not None)

# PgetJobParser.parse_header — replace the unconditional pop at :277-281
if lines and _is_chunk_data(lines[0]):
    data_line = lines.pop(0)
    result_at = RegexPatterns.CHUNK_AT.search(data_line)
    result_at2 = RegexPatterns.CHUNK_AT2.search(data_line)
    result_got = RegexPatterns.CHUNK_GOT.search(data_line)

# ActiveJobsParser._handle_auxiliary_lines, CHUNK_HEADER branch (:655-660)
if result:
    if lines and _is_chunk_data(lines[0]):
        lines.pop(0)
    return True
```
All three chunk regexes start with ``^`(name)'``, so a `[N] …` header can never match. `[VERIFIED: job_status_parser.py:71-99]`

### Pattern 2: `None` = unavailable flows through untouched (B2)
**What:** every consumer guards with `is not None` and *skips the update*, so last-known state persists. Never write `statuses or []`.
```python
# lftp/lftp.py — target shape
def status(self) -> Optional[List[LftpJobStatus]]:
    out = self.__run_command("jobs -v")
    try:
        statuses = self.__job_status_parser.parse(out)
        self.__consecutive_status_errors = 0
    except LftpJobStatusParserError:
        self.__consecutive_status_errors += 1
        if self.__consecutive_status_errors <= MAX_CONSECUTIVE_STATUS_ERRORS:
            self.logger.warning("Ignoring status error (count={}); status unavailable".format(
                self.__consecutive_status_errors))
            return None
        raise
    return statuses

def kill(self, name: str) -> bool:
    statuses = self.status()
    if statuses is None:
        # Unavailable is not "job absent": never report a no-op kill as handled.
        raise LftpJobStatusParserError("Lftp status unavailable; cannot locate job to kill")
    for status in statuses: ...
```

### Pattern 3: Successful-scan clock alongside the UI clock (B3)
```python
# common/status.py — ControllerStatus
latest_successful_local_scan_time = StatusComponent._create_property("latest_successful_local_scan_time")
latest_successful_remote_scan_time = StatusComponent._create_property("latest_successful_remote_scan_time")
# __init__: both = None

# controller/controller.py — _update_controller_status (existing lines unchanged)
if remote_scan is not None:
    ...  # existing UI fields
    if not remote_scan.failed:
        self.__context.status.controller.latest_successful_remote_scan_time = remote_scan.timestamp
if local_scan is not None:
    ...  # existing
    if not local_scan.failed:
        self.__context.status.controller.latest_successful_local_scan_time = local_scan.timestamp

# controller/auto_queue.py — process()
scan_time = AutoQueue.__scan_clock(status.latest_remote_scan_time)                     # cooldown only (unchanged)
remote_stable_time = AutoQueue.__scan_clock(status.latest_successful_remote_scan_time) # stability
local_stable_time = AutoQueue.__scan_clock(status.latest_successful_local_scan_time)   # stability
# __update_remote_size_history(model_files, remote_stable_time); sweep_accept uses remote_stable_time
# __update_local_idle_history(model_files, local_stable_time);   sweep_accept uses local_stable_time
```
**Why this satisfies D-03 and D-04 with no extra logic.** The model's remote and local sizes change only when a *successful* scan is applied (`ModelPipeline.feed_model_builder:157-160`). The success clock is therefore exactly "the timestamp of the data the model currently reflects". During an outage the clock and the sizes both freeze, so the history neither advances nor resets (D-03). At recovery, a matching size keeps its original stamp, and elapsed time is measured between the two successful observations (D-03). A changed size is re-stamped at the recovery scan (D-04). `[VERIFIED: auto_queue.py:395-438; model_pipeline.py:157-162]`

### Anti-Patterns to Avoid
- **`for s in self.status()` or `len(lftp.status())` without a `None` guard.** `Lftp.kill()` (`lftp.py:351`) is the only production instance. Tests (`test_lftp_protocol.py`) also call `len(statuses)` on success paths, which is fine.
- **Reusing `latest_remote_scan_failed` inside AutoQueue to build a clock.** It exists only for the remote side, and it couples AutoQueue to sampling order. Use explicit success-time properties.
- **Adding the new properties to `SerializeStatusJson`.** That violates D-06 and changes the SSE payload. The serializer lists its keys explicitly, so leaving it untouched is enough. `[VERIFIED: serialize_status.py:12-55]`
- **Switching the REQUEUE cooldown to the success clock.** The spec scopes B3 to *stability*. The cooldown is a retry throttle. Moving it would add a new "no retries during a scanner outage" behavior nobody asked for, and it would churn the local-gate test helpers, which advance the remote clock to age the cooldown.
- **Asserting RED tests on attributes that don't exist yet.** For example, reading `status.controller.latest_successful_remote_scan_time` on old code raises `AttributeError`, not `AssertionError`. RED regressions must observe *behavior*: queue commands, model state, active list, parsed job count.

## B1 Site Audit (every next-line-consuming site)

| # | Site (line) | Consumes | Can it take another job's header? | Verdict |
|---|-------------|----------|-----------------------------------|---------|
| 1 | `PgetJobParser.parse_header` sftp line (`:269-271`) | `lines[0]` if `"sftp" in lines[0]`, else raise | Only if lftp omits the session line AND the next header's path contains "sftp". The result is almost always a later raise, not a silent drop. | **Not confirmed.** Defer (D-09), record. |
| 2 | `PgetJobParser.parse_header` data line (`:277-281`) | `lines[0]` **unconditionally** | **YES.** lftp `CopyJob::FormatStatus` returns nothing when `c->Done()\|\|c->Error()\|\|no_status` `[CITED: github.com/lavv17/lftp src/CopyJob.cc]`. An existing fixture already shows a pget with no data line (`test_jobs_missing_pget_data_line`). Next header pget → orphaned `sftp://` line → `ValueError` → whole status fails. Next header mirror (downloading form) → silently dropped, and its `\transfer` lines get attached to the pget job. | **CONFIRMED.** Fix + 2 regressions (pget→pget, pget→mirror). |
| 3 | `MirrorJobParser._parse_connecting_header` (`:376-380`) | `lines[0]` only if it starts with `Getting file list` or `cd ` | No. Headers start with `[`. | Safe. |
| 4 | `QueueParser.parse` single Done line (`:430-433`) | Only if `QUEUE_DONE` matches, else raise | No | Safe. |
| 5 | `QueueParser._parse_queue_body` header lines 1-2 (`:449-454`) | Popped, then validated, raising on mismatch | Raises loudly, never silent | Safe (loud). |
| 6 | `QueueParser._parse_queue_body` line 3 (`:459`) | **Unconditional** pop. Only "Queue is stopped." / "Now executing:" are interpreted. | lftp `CmdExec::FormatStatus` prints "Now executing:" whenever ≥1 queue job runs, and "Queue is stopped." when suspended `[CITED: github.com/lavv17/lftp src/CmdExec.cc]`. All seedsyncarr jobs are queue children, so an active `[N]` header can't be line 3 in a consistent snapshot. In the idle-with-queued-commands case the popped line is "Commands queued:", which leads to a loud failure later. | **Not confirmed** as header-swallowing. Defer (D-09), record. |
| 7 | `QueueParser` "-[N]" executing lines, `Commands queued:`, queued `^\d+\.` / `^cd\s`, trailing Done (`:464-476, 485-497`) | Positive regex matches only | No. Headers start with `[`, not `-`, a digit or `cd`. | Safe. |
| 8 | `ActiveJobsParser._handle_file_transfer` `\transfer` data line (`:592-603`) | **Unconditional** pop, then **raise** if no chunk match | It can pop a header, but it then always raises `ValueError` → whole status unavailable. No job is silently lost. Same lftp cause: a mirror sub-CopyJob prints nothing when done. | **Consumes but fails loudly.** Not a lost-job site. Defer (D-09) and record: "`\transfer` with no data line makes the whole parse fail (after B2: status unavailable, last-known frozen)". |
| 9 | MIRROR_EMPTY follower (`:646-651`) | `lines[0]` if it **contains** `Getting file list`, starts with `cd ` or `mkdir `, or equals `name:` | **YES, but pathological.** The substring check matches a header whose path contains "Getting file list", e.g. `[2] mirror -c "/r/Getting file list" /l/ -- 1/2 (50%)`, which is silently dropped. The substring form is load-bearing for real output `rab: Getting file list (27) …` (`test_queue_and_jobs_4`), so it can't become `startswith`. | **CONFIRMED (low likelihood).** Recommend fixing with a header guard (`not re.match(r"^\[\d+\]\s", lines[0])`) plus 1 regression. Cheap, and it matches the owner's "prevent lost jobs". |
| 10 | `CHUNK_HEADER` follower (`:655-660`) | `lines[0]` **unconditionally** (raises only if none left) | **YES.** `\chunk a-b` is a chunk child job's cmdline. Its status line is the same `CopyJob::FormatStatus`, which prints nothing when the chunk is done or errored `[CITED: lftp src/pgetJob.cc FormatJobs + CopyJob.cc]`. Next header → swallowed (mirror) or raise (pget). Next `\chunk` → that chunk's data line orphaned → "Unable to parse line" → whole status fails. | **CONFIRMED (MEDIUM: derived from lftp source, not captured output).** Fix + regressions (`\chunk`→header, `\chunk`→`\chunk`). |
| 11 | CHMOD (`:663-676`) | `file:` line required (raise otherwise), then `CHMOD_PATTERN` only on positive match | No | Safe. |

**Fixture-preservation probe:** I wrapped the pget data-line and `\chunk` sites and ran all 126 tests under `tests/unittests/test_lftp`. There were 82 consume events and **0** consumed data lines that fail `CHUNK_AT|CHUNK_AT2|CHUNK_GOT`. The peek fix therefore changes the parse of no existing fixture. `[VERIFIED: probe plugin run in this session, 126 passed]`

**Behavior change inherent to fix #10:** a trailing `\chunk` with no lines left currently raises `ValueError("Missing data line for chunk …")`. After the fix it is tolerated. No test pins that raise (grep found none). This is the same root cause, so it belongs in scope.

## B2 Consumer Trace (`None` vs `[]`)

| Consumer | File:line | Behavior on `None` | Collapses to `[]`? |
|----------|-----------|--------------------|--------------------|
| `Lftp.status` | `lftp/lftp.py:298-313` | **Defect:** tolerated errors return `[]` | **YES. Fix here.** |
| `Lftp.kill` | `lftp/lftp.py:351` | `for status in None` → **TypeError**. `_handle_stop` catches only `LftpError` / `LftpJobStatusParserError`. Today, failures 1..2 make `kill` return `False`, `_handle_stop` reports success and **adds the file to `stopped_file_names` while the download continues**. | Would crash. **Fix: raise `LftpJobStatusParserError`** (already caught by `command_processor.py:139` → 500 "Lftp error"). |
| `LftpManager.status` | `controller/lftp_manager.py:140-166` | Returns the value through. Maps `LftpError`/`LftpJobStatusParserError` and stall backoff to `None`. | No `[VERIFIED]` |
| `ModelPipeline.collect_lftp_status` / `update_model` | `model_pipeline.py:82,106-108` | Passes the value through | No |
| `ModelPipeline.feed_model_builder` | `model_pipeline.py:163-164` | `set_lftp_statuses` called only if not None → builder keeps `__lftp_statuses` | No `[VERIFIED]` |
| `ModelBuilder.set_lftp_statuses` / `build_model` | `model_builder.py:62-66,166` | Never receives None. The last-known dict drives `DOWNLOADING` state and transfer speed/eta | No |
| `Controller._update_active_file_tracking` | `controller.py:433-445` | Active list replaced only if not None. `scan_manager.update_active_files` still gets the frozen list, so the active scanner keeps scanning | No `[VERIFIED]` |
| AutoQueue | `auto_queue.py` | Never sees statuses. Reads the model, and frozen `DOWNLOADING` fails `sweep_accept` (`state != DEFAULT`). Auto-extract needs a transition to `DOWNLOADED`. | No |
| Auto-delete / manual delete | `auto_delete_manager.py:132`, `command_processor.py:171-197` | Deletable states = DEFAULT/DOWNLOADED/EXTRACTED. Frozen `DOWNLOADING` is protected | No |
| `ModelPipeline._commit_downloaded_membership` | `model_pipeline.py:271-317` | Commits only DOWNLOADED/EXTRACTED. Frozen DOWNLOADING is never committed | No |
| `ExtractProcess` `dispatch.status()` | `extract/extract_process.py:84` | Unrelated (extract dispatch, not LFTP) | n/a `[VERIFIED: dispatch.py:114-120]` |

**What `[]` does today (the hazard the downstream tests must reproduce).** One tolerated parse error sends `set_lftp_statuses([])`. The builder drops the job, and the root file's state falls to DEFAULT. If `local_size >= remote_size` (preallocated or sparse pget), it becomes DOWNLOADED, gets committed to `downloaded_file_names` and becomes an auto-extract candidate. Otherwise it stays DEFAULT with a partial and becomes a sweep re-queue candidate. In both cases the state is now deletable. Meanwhile `__active_downloading_file_names` empties. `[VERIFIED: model_builder.py:472-492; model_pipeline.py:271-317; auto_queue.py:269-289]`

**Boundary pinning.** `Lftp` does *not* reset the counter on escalation, so failures 3, 4, … all raise until a success. Test this sequence at the `Lftp` layer on a unit harness (pexpect mocked; `_Lftp__run_command` patched to return text):
`err→None, err→None, err→raises, ok([job])→[job], err→None, err→None, ""→[]`
To stay boundary-generic, reference `lftp.lftp.MAX_CONSECUTIVE_STATUS_ERRORS` in a loop rather than hardcoding 2.

## B3 Clock Analysis

- **Defect site:** `controller.py:499-513` sets `latest_remote_scan_time` and `latest_local_scan_time` from every result, including `failed=True`. `[VERIFIED]`
- **Failed results carry `files=[]`** (`scanner_process.py:96-102`). `ModelPipeline` skips applying them (`:157-160`), so the model keeps stale sizes. Stale sizes plus an advancing clock means false stability. `[VERIFIED]`
- **Local scanner never emits `failed`.** `LocalScanner` turns `SystemScannerError` into `ScannerError(recoverable=False)`, which `ScannerProcess.run_loop` re-raises as fatal (`local_scanner.py:32-34`, `scanner_process.py:96-98`). The local fix is defense in depth. Tests must inject `ScannerResult(failed=True)` for the local side. `[VERIFIED]`
- **`pop_latest_result` keeps only the last queued result** (`scanner_process.py:116-128`). A `[success, failed]` pair inside one cycle discards the success for both the model and the clock, which is consistent.
- **Ordering:** `ControllerJob.execute` runs `controller.process()` then `auto_queue.process()` (`controller_job.py:24-25`). Model sizes and the success clock are updated in the same cycle, before AutoQueue samples them. `[VERIFIED]`
- **Production defaults:** remote window 90 s, local window 30 s (`config.py:564-570`). The REQUEUE cooldown is 300 s on the UI remote clock.
- **SSE side effect:** every `StatusComponent` property set notifies `StatusListener`, which enqueues a `Status.copy()`. One extra property set per successful scan means one extra identical SSE status frame per client per scan. This is harmless: the frontend gets the same payload. `[VERIFIED: stream_status.py:17-18; status.py:62-70]`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| A fake lftp for status tests | A custom pexpect stub class | `_make_lftp_with_mocked_process()` pattern (`test_lftp_log_sanitization.py:36-58`) + `patch.object(lftp, "_Lftp__run_command", side_effect=…)` | Already proven. Keeps the real parser and the real counter. |
| Composed model pipeline | Hand-crafted ModelFile states / listener events | Real `ModelBuilder` + `ModelDiffUtil` + `Model` as in `TestAutoQueueComposedPipeline` (`test_auto_queue.py:1798-1855`), or real `ModelPipeline(...)` (ctor takes injected collaborators, `model_pipeline.py:32-58`) | The builder's state rules (DOWNLOADED, DELETED) are what produce the hazard. |
| Controller with a real Status | Full Controller construction | `Controller.__new__(Controller)` + `ctx.status = Status()` (`test_controller.py:46-51`) | Isolates `_update_controller_status` with the real property machinery. |
| Controller with mocked managers | New patch scaffolding | `BaseControllerTestCase` (`tests/unittests/test_controller/base.py`) | Patches all 6 internals; `_make_controller_started()` helper. |
| Malformed `jobs -v` | New invented garbage | `_MALFORMED_JOBS_OUTPUT` / `test_raises_error_on_bad_status` fixture (`bad string uh oh`) | Proven to make the real parser raise. |

## Runtime State Inventory

Not a rename or migration phase, but because this is a patch release, the inventory is answered explicitly:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None. The new successful-scan clocks live in the in-memory `Status`. AutoQueue size/idle histories are in-memory. No persist or config format change. | none |
| Live service config | None | none |
| OS-registered state | None | none |
| Secrets/env vars | None | none |
| Build artifacts | Docker image rebuilt at release (Phase 118 REL-01) | none in this phase |

## Common Pitfalls

### Pitfall 1: The new status fields read as MagicMock in existing AutoQueue tests
**What goes wrong:** `TestAutoQueue`, `TestAutoQueueCommandOrigin` and `TestAutoQueueComposedPipeline` use `context = MagicMock()`. An unset `context.status.controller.latest_successful_remote_scan_time` is a MagicMock, and `float(MagicMock())` is `1.0` `[VERIFIED: python3]`. So `__scan_clock` returns 1.0, not None.
**How to avoid:** set both new fields to `None` in all 5 AutoQueue `setUp`s (`test_auto_queue.py:297, 1777, 1826, 1949, 2193`). Update the helpers `_set_scan` (`:1972-1986`) to accept `failed=False` and set the success clock only when not failed. Update `_cycle` (`:2215-2240`) to set `latest_successful_local_scan_time = local_scan_time`. These helper changes still work on old code, which ignores the new field, so they can land in the RED plan.
**Warning signs:** sweep or cooldown tests flip after the B3 fix.

### Pitfall 2: RED tests that fail for the wrong reason
**What goes wrong:** a test that injects `None` at `LftpManager.status` passes on old code, because downstream already guards. So it is not a regression test. A test that reads a new attribute fails with `AttributeError`.
**How to avoid:** the B2 downstream regressions must route the failure through the **real `Lftp.status`** (mocked pexpect + malformed text), so old code yields `[]`. B3 regressions observe queue commands, not field values. Classify new-contract tests separately (kill-on-None, success-clock-set, serializer-unchanged) as "new" in the evidence file. Phase 116 precedent: RED evidence lists failing tests with `AssertionError`.

### Pitfall 3: The integration tests pin `[]` and run only in CI
**What goes wrong:** `tests/integration/test_lftp/test_lftp_protocol.py:762-830` has 4 tests asserting `[] == self.lftp.status()` on tolerated errors. They need the Docker sshd/`testgroup` and can't run on the host.
**How to avoid:** flip them to `assertIsNone` in the B2 fix plan, and update the docstrings ("swallowed (return [])" → "reported unavailable (None)"). The host-runnable unit file carries the RED proof. CI verifies the integration flips.

### Pitfall 4: The real `Lftp.__init__` issues `set` commands through `__run_command`
**What goes wrong:** when a composed test builds a real `LftpManager` around a real `Lftp`, the manager's `__init__` sets lftp properties, which call `__run_command`. A `side_effect` list meant for `jobs -v` gets drained by those calls.
**How to avoid:** patch `_Lftp__run_command` with a *function* that returns the next scripted `jobs -v` output only when `cmd == "jobs -v"`, and `""` otherwise. Patch `controller.lftp_manager.Lftp` with `return_value=real_lftp`. Use `patch.object` scoped `with` blocks, the same as the existing tests.

### Pitfall 5: Peek-fix side effect at the `\chunk` site
**What goes wrong:** after the fix, a `\chunk` follower that is neither chunk data nor a header is left for the main loop. If lftp ever printed some unknown status form there, the parse would now raise where it used to silently swallow the line.
**How to avoid:** the probe shows no such form in any fixture. All chunk data seen matches `CHUNK_AT`, including `[Connecting...]`, `[Waiting for response...]` and `[ssh_exchange_identification: …]`. Accept the change. With B2, any new raise means "unavailable", never empty.

### Pitfall 6: Ruff path and host suite gaps
**How to avoid:** use `cd src/python && poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/` (absolute path). For the host full suite, use `--ignore` for `test_ssh`, `test_extract`, `test_scan` and `test_system`, plus the 4 documented baseline files (Phase 116 VERIFICATION). CI is authoritative.

## Code Examples

### B1 regression fixtures (modeled on the real `test_jobs_missing_pget_data_line`)
```python
# pget (no data line) followed by a pget header  — old: ValueError on orphaned sftp line → LftpJobStatusParserError
output = """
[0] queue (sftp://seedsyncarrtest:@localhost:22)
sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
Now executing: [4] pget -c /tmp/t/remote/d.txt -o /tmp/t/local/
-[5] pget -c /tmp/t/remote/e.txt -o /tmp/t/local/
[4] pget -c /tmp/t/remote/d.txt -o /tmp/t/local/
sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
[5] pget -c /tmp/t/remote/e.txt -o /tmp/t/local/
sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
`/tmp/t/remote/e.txt' at 10 (5%) [Receiving data]
"""
# expect 2 RUNNING PGET jobs: id 4 "d.txt" TransferState(None×5); id 5 "e.txt" TransferState(None,None,None,None,None)

# pget (no data line) followed by a mirror header with a \transfer — old: mirror silently dropped,
# its \transfer attached to the pget job
output = """
[0] queue (sftp://seedsyncarrtest:@localhost:22)
sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
Now executing: [4] pget -c /tmp/t/remote/d.txt -o /tmp/t/local/
-[3] mirror -c /tmp/t/remote/c /tmp/t/local/ -- 100/1.1k (9%)
[4] pget -c /tmp/t/remote/d.txt -o /tmp/t/local/
sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
[3] mirror -c /tmp/t/remote/c /tmp/t/local/  -- 100/1.1k (9%)
\\transfer `c/ca'
`ca' at 50 (50%) [Receiving data]
"""
# expect pget 4 "d.txt" with NO active file transfers; mirror 3 "c" with active transfer "c/ca"

# \chunk with no data line followed by a mirror header — old: mirror silently dropped
#   ... `/tmp/t/remote/A.rar', got 100 of 1000 (10%)
#   \\chunk 0-499
#   `/tmp/t/remote/A.rar' at 50 (0%) [Receiving data]
#   \\chunk 500-999
#   [2] mirror -c /tmp/t/remote/b /tmp/t/local/  -- 1/2 (50%)
# \chunk followed by \chunk (first has no data) — old: "Unable to parse line" → parser error

# mirror-empty followed by a header whose path contains "Getting file list" — old: silently dropped
#   [1] mirror -c /tmp/t/remote/a /tmp/t/local/  -- 1/2 (50%)
#   \\mirror `sub'
#   [2] mirror -c "/tmp/t/remote/Getting file list" /tmp/t/local/  -- 1/2 (50%)
```
Assert full `LftpJobStatus` equality against golden objects, as the existing tests do (`golden_jobs == statuses_jobs`). Note that `test_parse_header_consumes_sftp_line` (components) still passes, because its data line matches `CHUNK_GOT`.

### B2 boundary (unit, host-runnable)
```python
# Source: pattern from tests/unittests/test_lftp/test_lftp_log_sanitization.py:36-58
from lftp import lftp as lftp_mod
lftp = _make_lftp_with_mocked_process()
with patch.object(lftp, "_Lftp__run_command", return_value=_MALFORMED_JOBS_OUTPUT):
    for i in range(lftp_mod.MAX_CONSECUTIVE_STATUS_ERRORS):
        self.assertIsNone(lftp.status())          # old code: [] → AssertionError (RED)
    with self.assertRaises(LftpJobStatusParserError):
        lftp.status()
```

### B2 composed downstream (RED via real Lftp)
Cycle 1 runs a valid running-pget output for `File.One.rar`. The scans give remote 1000 and local 1000 (preallocated), so the state is DOWNLOADING. Also add `File.Two.mkv` with remote 1000 and local 400. Cycle 2 runs malformed output. Assert:
- both files are still `DOWNLOADING`
- `persist.downloaded_file_names` is unchanged
- AutoQueue (stability 0, auto_extract True) issued no QUEUE/EXTRACT
- `Controller.__active_downloading_file_names` is unchanged and `scan_manager.update_active_files` still lists both files
- `mock_model_builder.set_lftp_statuses` was not called in cycle 2 (controller-level variant)

Old code fails: File.One goes DOWNLOADED (commit + extract), File.Two goes DEFAULT (re-queue), and the active list empties. Preservation: cycle 3 with `""` output yields `[]`, and the active list clears.

### B3 composed (implementation-agnostic RED)
```python
c = Controller.__new__(Controller); ctx = MagicMock(); ctx.status = Status(); c._Controller__context = ctx
aq_ctx = MagicMock(); aq_ctx.status = ctx.status; aq_ctx.config = Config(); remote_stability_seconds = 90 ...
c._update_controller_status(ScannerResult(timestamp=t0, files=[...], failed=False), None)   # + model shows size 100
for t in t0+30 .. t0+300: c._update_controller_status(ScannerResult(timestamp=t, files=[], failed=True), None)
auto_queue.process()  → assert no QUEUE (old: queued once t-t0 ≥ 90)
assert ctx.status.controller.latest_remote_scan_time == last failed t and latest_remote_scan_failed is True   # UI meaning kept
```
`ScannerResult.timestamp` is a `datetime` in production, and `__scan_clock` handles both datetimes and epoch floats.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tolerated status errors → `[]` | → `None` (unavailable) | This phase | Active transfers stay protected through transient parse errors |
| Stability on the "any scan" clock | Stability on the successful-scan clock | This phase | A scanner outage can't make a file look stable |
| Unconditional data-line pops | Peek-before-pop | This phase | No silently lost or misattributed jobs |

**Deprecated/outdated:** none.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | lftp really emits `\chunk a-b` with no following status line (from source reading: chunk = child CopyJob, and `CopyJob::FormatStatus` returns empty when done or errored) | B1 site #10 | Low. If it never happens, the fix is harmless (probe: zero fixture changes) and the regression test still documents the contract. |
| A2 | The queue's line 3 is always "Now executing:" or "Queue is stopped." whenever an active `[N]` job is listed | B1 site #6 | Low. If wrong, a lone trailing mirror header could be dropped. It was recorded as deferred, not fixed. |
| A3 | Keeping the REQUEUE cooldown on the UI clock is the right call (not specified by owner) | B3 / Anti-patterns | Low. The two choices differ only during scanner outages, in retry cadence, not in safety. |
| A4 | Raising from `Lftp.kill()` on unavailable status is acceptable UX: Stop shows an "Lftp error" instead of silently "succeeding" | B2 trace | Low to medium. It is product-visible. See Open Question 1. |

## Open Questions (RESOLVED)

1. **RESOLVED: Plan 05 ships the kill-on-None raise (recommendation accepted; FYI noted for the phase summary).** Stop button during a transient status failure (product-visible, small).
   - What we know: today a Stop clicked during parse failures 1..2 *reports success* and marks the file "stopped", while lftp keeps downloading. After the fix, the Stop returns an error ("Lftp error: …") and nothing is marked, so the user can retry.
   - Recommendation: ship the raise. Returning "not found" would be exactly the "unavailable → no jobs" conversion that XFER-02 forbids. Mention it to the owner in the phase summary as an FYI. Not blocking.

2. **RESOLVED: deferred per D-09; Plan 04 records it in the summary/backlog.** Should site #8 (`\transfer` with no data line → whole-status parse failure) be tolerated in this patch?
   - What we know: it never loses a job silently. After B2 it means "status unavailable", so progress freezes until the next clean poll.
   - Recommendation: defer per D-09 and record it in the summary/backlog. Revisit if NAS logs show "Missing chunk data for filename" warnings.

3. **RESOLVED: Plan 04 Task 2 adds the JOB_HEADER guard (fixed in scope).** Should site #9 (mirror-empty substring) be fixed, given it needs a pathological filename?
   - Recommendation: yes. It is one guard line plus one regression, it is a genuine silent job loss, and it fits "prevent lost jobs". The planner can drop it if scope must shrink. Sites #2 and #10 are mandatory.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| poetry | test/lint runner | ✓ | 2.3.4 | — |
| pytest (poetry venv) | all tests | ✓ | 9.1.1 | — |
| pytest-timeout (poetry venv) | 60 s per-test timeout | ✓ | — | `--timeout-method=thread` |
| ruff (poetry venv) | lint gate | ✓ | 0.15.9 (CI pins 0.15.22) | — |
| Docker sshd + `testgroup` | `tests/integration/test_lftp/*` | ✗ on host | — | CI `make run-tests-python` |
| lftp binary | integration tests only | ✗ on host (not needed for unit tests) | — | CI |

**Missing dependencies with no fallback:** none. Every RED/GREEN regression proposed here runs on the host.
**Missing dependencies with fallback:** the integration tests (4 `[]`→`None` flips) are verified in CI only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + `unittest.TestCase` classes; pytest-timeout 60 s |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]`, `[tool.coverage.report] fail_under = 88` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_controller/test_controller.py tests/unittests/test_controller/test_model_builder.py tests/unittests/test_controller/test_transfer_state_safety.py tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py -q -p no:cacheprovider` (baseline at `2e5be14`, without the new file: **454 passed in 0.64 s** `[VERIFIED]`) |
| Full suite command | Host: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh --ignore=tests/unittests/test_controller/test_extract --ignore=tests/unittests/test_controller/test_scan --ignore=tests/unittests/test_system` (compare to the Phase 116 baseline). CI: `make run-tests-python` (includes integration and coverage) |
| Lint gate | `cd src/python && poetry run ruff check /Users/julianamacbook/seedsyncarr/src/python/`. Baseline: `All checks passed!` `[VERIFIED]` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? | Fails on old code? |
|--------|----------|-----------|-------------------|-------------|--------------------|
| XFER-01 | pget (no data) → pget header: both jobs parsed | unit (full output) | `pytest tests/unittests/test_lftp/test_job_status_parser.py -k missing_pget_data_line -q` | ✅ file / ❌ test | YES (parser error) |
| XFER-01 | pget (no data) → mirror header + `\transfer`: both jobs, transfer on mirror | unit | same file | ❌ | YES (assert) |
| XFER-01 | `\chunk` (no data) → mirror header: job present | unit | same file | ❌ | YES (assert) |
| XFER-01 | `\chunk` → `\chunk`: parses | unit | same file | ❌ | YES (parser error) |
| XFER-01 | mirror-empty → header containing "Getting file list" | unit | same file | ❌ | YES (assert) |
| XFER-01 | All existing parser fixtures unchanged | unit | `pytest tests/unittests/test_lftp -q` | ✅ | passes both |
| XFER-02 | Composed: parse error mid-download → DOWNLOADING kept, no QUEUE/EXTRACT, downloaded set unchanged | composed | `pytest tests/unittests/test_controller/test_transfer_state_safety.py -q` | ❌ Wave 0 | YES |
| XFER-02 | Controller: active list + `update_active_files` unchanged; `set_lftp_statuses` not called on failure | composed (BaseControllerTestCase + real Lftp/LftpManager) | same | ❌ | YES |
| XFER-02 | `LftpManager.status` passes `None` through | unit | `pytest tests/unittests/test_controller/test_lftp_manager.py -q` | ✅ / ❌ test | new (passes both) |
| XFER-02 | `Lftp.kill` on unavailable → raises `LftpJobStatusParserError`, no kill command sent | unit | `pytest tests/unittests/test_lftp/test_lftp_status_contract.py -q` | ❌ | new (old: TypeError path unreachable) |
| XFER-03 | Failures 1..MAX → `None` each; MAX+1 raises; success resets; repeat | unit (mocked pexpect, real parser) | same contract file | ❌ | YES |
| XFER-03 | Genuinely empty output → `[]`, active list clears | unit + composed | contract file + safety file | ❌ | passes both (preservation) |
| XFER-03 | Integration counter tests flip `[]`→`None` | integration | CI only | ✅ (edit) | n/a |
| XFER-04 | Failed remote scans spanning 90 s window → not queued (AutoQueue harness) | unit | `pytest tests/unittests/test_controller/test_auto_queue.py -k Stability -q` | ✅ / ❌ test | YES |
| XFER-04 | D-03: success(100) … failures … success(100) ≥ window → queued | unit | same | ❌ | passes both |
| XFER-04 | D-04: success(100) … failures … success(150) → window restarts from the recovery scan; queued only after +90 s | unit | same | ❌ | YES (old queues during the failure span) |
| XFER-04 | Composed `_update_controller_status(failed)` → AutoQueue does not queue; UI `latest_remote_scan_time`/`_failed` still updated | composed | safety file | ❌ | YES |
| XFER-04 | `_update_controller_status` sets success clock only when not failed | unit | `test_controller.py` / `test_controller_unit.py` | ✅ / ❌ test | new |
| XFER-04 | Serializer output keys unchanged (no success fields leak) | unit | `test_serialize_status.py` | ✅ / ❌ test | passes both |
| XFER-05 | Failed local scans spanning 30 s → local gate holds (D-05 both cases) | unit + composed | auto_queue `-k Local` + safety file | ❌ | YES |
| XFER-05 | With all-successful scans, remote and local gating unchanged | unit | existing `TestAutoQueueStabilityAndSweep` / `TestAutoQueueLocalStabilityGate` | ✅ | passes both |

### Sampling Rate
- **Per task commit:** quick run command + whole-tree ruff (absolute path)
- **Per wave merge:** host full suite (with the documented ignores), no new failures vs baseline
- **Phase gate:** CI `unittests-python` (integration + coverage ≥ 88) and `lint-python` green before `/bm:verify-work`

### Wave 0 Gaps
- [ ] `tests/unittests/test_lftp/test_lftp_status_contract.py`: B2 boundary + kill-on-None (reuse the `_make_lftp_with_mocked_process` pattern and the `_MALFORMED_JOBS_OUTPUT` fixture)
- [ ] `tests/unittests/test_controller/test_transfer_state_safety.py`: composed B2 downstream (real Lftp → real LftpManager → ModelPipeline/ModelBuilder/Model → AutoQueue; plus a BaseControllerTestCase variant) and composed B3 (real `Status` + `Controller.__new__` + AutoQueue)
- [ ] `test_auto_queue.py`: initialize the new fields to None in 5 setUps; add `failed=` to `_set_scan`; make `_cycle` set the local success clock
- [ ] `117-REL01-EVIDENCE.md`: RED section (run against `2e5be14` + test-only commit), then GREEN section. Use the Phase 116 format: command, FAILED lines, summary line, ruff result, requirement table, and "new vs regression" classification

**Recommended plan shape:**
1. **Wave 1:** RED tests + evidence. Test files only.
2. **Wave 2:** three parallel-safe fix plans on disjoint source files:
   - B1: `job_status_parser.py`
   - B2: `lftp.py` + integration flips + `LftpManager` pass-through test
   - B3: `status.py`, `controller.py`, `auto_queue.py`, plus the new-field tests
3. **Wave 3:** GREEN evidence, full host suite, ruff, and the deferred-items record (sites #1, #6, #8).

## Security Domain

`security_enforcement` is absent from config, so it is treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes. `jobs -v` text embeds remote filenames, which seedbox content can influence | Precompiled anchored regexes, positive-match peeking. No new regex beyond a linear `^\[\d+\]\s` header guard (no ReDoS surface). |
| V6 Cryptography | no | — |
| V7 Error Handling & Logging | yes | Keep `sanitize_log_value` on every log line that includes output or names (CWE-117). The parser already logs the full sanitized block on error, so don't add raw-output logs in `Lftp.status`/`kill`. Error text returned to the UI from Stop stays the generic "Lftp error: …" from the existing handler. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Crafted remote filename that makes the parser swallow or misattribute jobs (e.g. "Getting file list" in a path) | Tampering | Peek-before-pop + header guard (B1) |
| Induced parse failure (odd filename) that makes active downloads look finished, leading to extract/delete/re-queue | Tampering / DoS | B2 `None` contract freezes last-known state; delete/extract are gated on non-DOWNLOADING state |
| Log injection via job names | Repudiation | Existing CWE-117 `sanitize_log_value`; keep it in any new or changed log line |
| Persistent parse failure keeps status unavailable indefinitely | DoS (availability of progress UI) | Accepted by owner (D-02). Escalation warning is logged by `LftpManager`. |

## Rollback (for Phase 118's runbook)

This phase is pure code: no persist, config or schema change, and the new status fields are in-memory only. Rolling back means re-pinning the NAS compose image to the previous release tag and running `docker compose up -d seedsyncarr` with the absolute-path sudo docker commands. No data migration is needed. Phase 117 adds **no** downgrade hazard. The Phase 116 `imported_children` downgrade caveat still governs the 1.7.4 release as a whole, and Phase 118 owns the runbook. `[VERIFIED: diff scope — status.py properties are not persisted; no change to *_persist.py]`

## Sources

### Primary (HIGH confidence)
- Repo at `2e5be14`: `lftp/job_status_parser.py`, `lftp/lftp.py`, `controller/{lftp_manager,model_pipeline,model_builder,controller,auto_queue,command_processor,auto_delete_manager,controller_job}.py`, `controller/scan/{scanner_process,local_scanner}.py`, `common/status.py`, `web/serialize/serialize_status.py`, `web/handler/stream_status.py`, `common/config.py`
- Tests: `tests/unittests/test_lftp/*`, `tests/unittests/test_controller/{base,test_auto_queue,test_lftp_manager,test_controller_unit,test_controller}.py`, `tests/integration/test_lftp/test_lftp_protocol.py`
- Session verification: probe over 126 parser tests (0 non-matching consumed data lines); quick run 454 passed; ruff clean; `float(MagicMock()) == 1.0`
- `.github/workflows/ci.yml`, `Makefile`, `src/docker/test/python/{compose.yml,Dockerfile}`, `src/python/pyproject.toml`

### Secondary (MEDIUM confidence)
- lftp source `src/CopyJob.cc` (`FormatStatus` early return on `c->Done()||c->Error()||no_status`), `src/pgetJob.cc` (`FormatStatus`/`FormatJobs`, `\chunk` cmdline for child jobs), `src/CmdExec.cc` (queue "Now executing:" / "Queue is stopped." conditions). Fetched from raw.githubusercontent.com/lavv17/lftp/master.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies; versions probed.
- Architecture: HIGH. Every consumer was traced in code.
- B1 audit: HIGH for sites #2/#9 (fixtures + code). MEDIUM for #10 (lftp source reading).
- Pitfalls: HIGH. The MagicMock-float and integration-pinning issues were verified directly.

**Research date:** 2026-10-08
**Valid until:** 2026-11-07 (stable internal code; re-verify line numbers if other phases touch these files)
