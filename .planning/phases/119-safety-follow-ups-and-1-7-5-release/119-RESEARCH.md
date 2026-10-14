# Phase 119: Safety Follow-ups and 1.7.5 Release - Research

**Researched:** 2026-10-14
**Domain:** Python transfer pipeline safety (lftp/pexpect, auto-queue, auto-delete, webhook import evidence), Sonarr/Radarr queue API, hatchling packaging, release gate
**Confidence:** HIGH for the arr queue semantics, lftp internals, packaging fix and codebase integration points (verified against source, the live NAS and a local build). MEDIUM for a few design choices that are Claude's discretion (backoff constants, pending-notice TTL).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Root cause framing (from diagnosis, confirmed in discussion)
- **D-01:** The Obsession defect is a *transfer started before the seedbox download finished*. The NAS already runs with `use_temp_file = True`; lftp copied what existed on the seedbox, completed its pget against the short remote file, and renamed the temp file to the final name. The fix must gate the transfer (start and/or release-to-final-path) on proven seedbox completion — not only re-check before marking local completion.
- **D-02:** Temp-file transfer (write under a non-importable name, rename only after completion is verified) becomes mandatory for automatic transfers regardless of the `use_temp_file` setting, so an interrupted, retried, crashed or restart-recovered copy is never at an importable path (IMP-01). Planner decides whether the setting is removed, ignored, or forced, and how the rename is deferred until verification passes.

#### Completion evidence (IMP-02)
- **D-03:** Sonarr/Radarr download-queue state is the primary completion evidence. Size and mtime stability are supporting evidence only and can never establish completion on their own.
- **D-04:** Each of these keeps completion unproven and the item held: Sonarr/Radarr API unavailable or erroring; ambiguous queue match (more than one candidate release); no queue entry found; queue entry still downloading/queued/paused. Elapsed time never grants completion.
- **D-05:** A successful API response alone is insufficient — planning must pin down the specific queue fields and matching rules that prove download completion. Planning MUST verify the actual Sonarr v3/v4 and Radarr v3 queue/API semantics needed to identify a release and establish completion (fields, status values, download-client completion signal, how the seedbox path/title maps to the queue entry, behaviour after import when the entry leaves the queue). The incident diagnosis establishes the problem, not the solution details.
- **D-06:** The arr URLs and API keys already exist in config (`Config.Sonarr` / `Config.Radarr`, currently used only by the web test-connection handler) and are configured on the NAS. No new user setup step; API keys stay secrets (never logged).

#### Items Sonarr/Radarr can't vouch for
- **D-07:** Items whose completion can't be established (including items with no queue entry — absence does not prove an item is unrelated to Sonarr/Radarr) are held, never auto-transferred. No exemption for "non-arr" items.
- **D-08:** Manual release override: the user can deliberately release a held item. The existing Queue action must NOT silently bypass safety — releasing a held/unverified item requires an explicit confirmation: "Completion could not be verified. Transfer and release this item anyway?" The approval applies only to that one transfer attempt (not persisted for future attempts/re-queues).
- **D-09:** Manual release is a recorded, explicit exception to IMP-01/IMP-02 and a small, owner-approved exception to the phase's "no UI features" boundary. Normal automatic transfers keep the strict checks. The override bypasses source-completion verification only: the local copy must still finish transferring (temp-file + verified local completion) before it becomes importable.

#### Hold visibility
- **D-10:** A held item shows as waiting in the existing file list, using existing status display, with its reason available there: "Sonarr unavailable" / "Radarr unavailable", "Ambiguous match", "Still downloading" and "No matching queue entry" (required). No new screen, no bell notification this milestone.
- **D-11:** Log on hold start, reason change, and hold clear — not on every retry. When verification succeeds the hold clears automatically and the transfer proceeds.

#### Retry behaviour
- **D-12:** Retry indefinitely; never release because a timeout expired. Resume automatically when Sonarr/Radarr returns.
- **D-13:** Capped retry backoff, and queue checks shared across waiting items (one queue fetch per arr per check cycle, not one API request per file per scan), so an outage doesn't hammer the APIs.

#### Early per-episode credit (IMP-03)
- **D-14:** Credit and persist an import notice only for a uniquely identified, fully transferred episode while siblings still transfer; credit survives restart. Credit alone never authorizes whole-folder deletion — deletion requires both a complete folder transfer and import coverage of every required video. Existing ambiguous-filename rejection (Phase 116, IMPORT-01/02) stays in force.

#### Carried-forward requirements (no new decisions needed)
- **D-15:** XFER-06, DEL-01, REL-02, REL-03 as written in REQUIREMENTS.md / ROADMAP.md success criteria. REL-03 smoke checks: startup, real transfer, import visibility and webhook handling, automatic cleanup, settings persistence, restart; successful scan after any startup scanner error (other startup errors need their own resolution).

### Claude's Discretion
- Exact gating point(s) in the pipeline (auto-queue acceptance vs. lftp completion/rename vs. both), data structures for hold state, backoff constants, queue-match algorithm (subject to D-04/D-05), persistence format for per-episode credit, PyPI packaging fix approach, LFTP resync mechanism.

### Specific Ideas (verbatim)
- Confirmation text for manual release (verbatim): "Completion could not be verified. Transfer and release this item anyway?"
- Hold reasons as user-facing labels: "Sonarr unavailable", "Radarr unavailable", "Ambiguous match", "Still downloading".
- Incident evidence to turn into regressions: Obsession — remote 55,477,377,022 B, Radarr imported 54,676,946,944 B, re-queue at 20:47:48 then import at 20:48:32; Days of Hope — three Sonarr notices rejected "no transfer evidence" ~1 min before the root committed, then 24 partial-import deferrals and give-up.

### Deferred Ideas (OUT OF SCOPE)
- Bell notification for long holds — not this milestone.
- Backlog 999.1 payload-size evidence — stays deferred (defense in depth only).
- Reliability milestone work — Phase 120+.
- Reviewed todo not folded: `2026-04-21-webob-cgi-upstream-unblock.md` (blocked upstream, unrelated).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XFER-06 | After an LFTP status timeout, status stays unavailable until the command stream is verifiably resynchronized | §Pattern 4 (sentinel resync). `echo` quote removal verified live on lftp 4.9.2. Fake-stream regression design in §Validation |
| DEL-01 | Pending auto-delete timer cannot delete a submitted-unobserved transfer; defers and retries | §Pattern 5. The submitted set is read cross-thread, so a lock is required (Pitfall 6). Defer through the existing `__defer_auto_delete` |
| IMP-01 | Incomplete/unverified copy never at an importable path (transfer, retries, crash, restart) | §Pattern 2. Force temp-file mode. lftp renames temp→final only on completed transfer (verified in lftp 4.9.2 `FileCopy.cc`). Gate before submission, so no copy exists until completion is proven |
| IMP-02 | Completion from reliable evidence: arr queue identification; unavailable/ambiguous/missing → hold visibly; manual one-shot release | §Arr Queue Semantics (verified from Sonarr v4/v3 and Radarr source plus the live NAS). §Pattern 1 (CompletionGate), §Pattern 3 (hold visibility and 428 confirm flow) |
| IMP-03 | Per-episode import credit persisted while siblings transfer; survives restart; whole-folder delete still needs full transfer and coverage | §Pattern 6 (child-evidence credit, pending-notice re-evaluation, arm-on-commit) |
| REL-02 | Valid member paths, packaging checks, clean install, PyPI publish | §Pattern 7. Root cause reproduced locally (200 of 204 wheel members `./`-prefixed). `only-include` fix built, checked and installed in a clean Python 3.12 venv |
| REL-03 | Release via Docker/GitHub/PyPI; red-then-green regressions; full suite, ruff, CI; smoke tests; NAS verification | §Validation Architecture, §Release Gate, §Dependabot triage |
</phase_requirements>

## Summary

The highest-risk item is IMP-02. It is now pinned down against Sonarr and Radarr source code and the live NAS (Sonarr **4.0.20.3014**, Radarr **6.4.4.10685**, both with Completed Download Handling on, with a Deluge client labelled `tv-sonarr` / `radarr` and remote path mapping `/home/jules1651/downloads/deluge` → `/data/torrents/`). In both apps, each queue record's `outputPath` is `RemapRemoteToLocal(save_path) + torrent.Name`, so its **basename equals the SeedSyncarr root name exactly**. That basename is the reliable matching key. `title` is not reliable: Sonarr strips the file extension from it, Radarr does not. `status` is the download client's verdict, serialized as camelCase. For Deluge, `completed` means `is_finished && state != Checking`. `trackedDownloadState` describes the arr's *import* pipeline. It can still read `downloading` after the client has finished, when path validation fails, so it must not be used as the completion signal. Once the arr imports everything, the entry leaves the queue (`Imported` is filtered out). Absence is therefore ambiguous, and per D-04 it holds. `GET /api/v3/queue/details` returns the entire queue unpaged in both apps, including unknown-series and unknown-movie items. It is the right single fetch per arr per cycle.

IMP-01 needs no rename deferral inside lftp. lftp 4.9.2 renames `*.lftp` → final name only when the transfer finishes (`FileCopyPeerFDStream::Do`, after `verify->Done()`). Killed, crashed or interrupted transfers leave the temp name in place, and `pget -c` resumes the temp file through `<temp>.lftp-pget-status`. Two changes together make an unverified copy unable to reach an importable path. First, force temp-file mode in LftpManager and ScanManager, whatever the config value. Second, gate **submission** on proven completion. The one exception is the owner-approved manual release. Seedbox completion only moves one way (a finished torrent does not become unfinished), so a proof taken at submission still holds when lftp renames.

XFER-06 needs a sentinel resync. lftp's `echo` performs shell-style quote removal (verified live: `echo SYNC-"12"-END` prints `SYNC-12-END`). The terminal's echo of the typed command contains the quotes and its output does not, so `expect` on the unquoted form can match only lftp's real output. DEL-01 needs an explicit guard plus a lock on LftpManager's submitted set, because the Timer thread reads a set the controller thread mutates. IMP-03 has three parts. Child-level evidence credits only `imported_children`. Notices whose child is not yet visible as DOWNLOADED are re-evaluated. Auto-delete is armed when the root later commits. REL-02's root cause is `packages = ["."]`. Replacing it with `only-include` for the real top-level modules produces 0 `./` members, a 78-file clean install and a working `seedsyncarr --help` on Python 3.12 (verified locally).

**Primary recommendation:** Add a Controller-owned `CompletionGate`, backed by a single `ArrQueueClient` that fetches `/api/v3/queue/details` once per arr per cycle with capped backoff. Apply it in the AutoQueue sweep (before the cooldown stamp) and again at QUEUE execution time in `CommandProcessor` (AUTO: skip and hold; USER: 428 unless `release_unverified`). Force temp-file mode. Split the work into the plans the ROADMAP requires: IMP-01+02, IMP-03, XFER-06+DEL-01, REL-02+REL-03.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Arr queue fetch, match, completion verdict | API / Backend (controller thread, new `controller/arr_queue.py` + `controller/completion_gate.py`) | — | Secrets (API keys) and HTTP stay server-side. Must run on the controller thread to share the cycle and avoid locks |
| Transfer start gating (AUTO) | Backend: `AutoQueue.process` sweep + `CommandProcessor._handle_queue` | — | Sweep pre-filter keeps cooldown semantics. Execution-time re-check is defense in depth |
| Manual release (USER, one-shot) | Backend: `CommandProcessor` + web handler flag | Browser: confirm modal in `BulkActionDispatcher` | The browser only asks. The backend enforces that USER queue on an unverified item fails 428 without the flag |
| Hold visibility | Backend: `ModelFile.hold_reason` via `ModelBuilder` | Browser: `ViewFile.holdReason` → `transfer-row` badge/label | Model diff → SSE already carries state. No new endpoint |
| Temp-file enforcement | Backend: `LftpManager`, `ScanManager` | lftp process (renames on completion) | lftp owns the rename. SeedSyncarr forces the setting |
| LFTP stream resync | Backend: `lftp/lftp.py` | — | All commands share one pexpect stream |
| Auto-delete submitted guard | Backend: `Controller.__execute_auto_delete` (Timer thread) | `LftpManager` (lock-protected set) | Cross-thread read |
| Per-episode credit persistence | Backend: `Controller.__check_webhook_imports` → `ControllerPersist.imported_children` | `Persist.to_file` (atomic, every 30 s and at exit) | Existing persisted structure, no format change |
| Packaging | Build/CI: `src/python/pyproject.toml`, `.github/workflows/ci.yml` | — | hatchling config + CI check step |

## Arr Queue Semantics (D-05: the owner's highest-priority item)

All items below are `[VERIFIED]` against source on GitHub (Sonarr `main` = v4, Sonarr `v3` branch, Radarr `develop` = v6) and/or the live NAS, unless tagged otherwise.

### Endpoint
- **Use `GET {url}/api/v3/queue/details`** with header `X-Api-Key: <key>`.
  - Sonarr v4 `QueueDetailsController.GetQueue(int? seriesId, List<int> episodeIds, ...)` returns `queue.Concat(pending)`. It is **unpaged and unfiltered**, so unknown-series items are included. `[VERIFIED: Sonarr main src/Sonarr.Api.V3/Queue/QueueDetailsController.cs]`
  - Radarr `QueueDetailsController.GetQueue(int? movieId, bool includeMovie)` returns the same: unpaged, all items. `[VERIFIED: Radarr develop]`
  - Sonarr v3 has `QueueDetailsModule` (`/queue/details`). `[VERIFIED: Sonarr v3 branch]` For Radarr 3.x/4.x, the presence of `/queue/details` is `[ASSUMED]`. The NAS runs 6.4.4, where it is verified.
  - Live NAS: both apps answered `GET /api/v3/queue/details` with HTTP 200 and `[]` (queue empty at research time). `[VERIFIED: NAS probe 2026-10-14]`
- **Avoid `/api/v3/queue`** (paged). The default `pageSize` is 10 (`PagingResource`: `PageSize ?? 10`). The server rebuilds and re-sorts the whole queue on every page request, so a multi-page walk can tear while the queue changes. Unknown items are excluded unless `includeUnknownSeriesItems=true` / `includeUnknownMovieItems=true`. `[VERIFIED: Sonarr QueueController.GetQueue]`

### Record fields that matter (JSON camelCase via `JsonStringEnumConverter(JsonNamingPolicy.CamelCase)` `[VERIFIED: STJson.cs]`)
| JSON field | Meaning | Use |
|---|---|---|
| `outputPath` | `RemapRemoteToLocal(host, torrent.save_path) + torrent.Name` (Deluge `GetItems`) | **Match key:** basename == SeedSyncarr root name |
| `downloadId` | Deluge torrent hash, uppercased | **Group key:** Sonarr emits one record *per episode* with the same downloadId (`QueueService.MapQueue`) |
| `status` | `QueueStatus`, mapped from the client's `DownloadItemStatus`: `unknown, queued, paused, downloading, completed, failed, warning, delay, downloadClientUnavailable, fallback`. Sonarr v3 emits a string via `FirstCharToLower()`, giving the same values | **Completion signal:** `completed` only |
| `sizeleft` | `torrent.total_size - torrent.total_done` (obsolete-marked property, still emitted; the `SizeLeft` property is commented out because of a case collision) | Must be `0` (corroborates `completed`) |
| `trackedDownloadState` | Arr *import* pipeline: `downloading, importBlocked, importPending, importing, imported, failedPending, failed, ignored` | **Not** a completion signal. Stays `downloading` when the client is complete but `ValidatePath` fails |
| `title` | Sonarr: `RemoveFileExtension(torrent.Name)`. Radarr: `torrent.Name` unchanged | Do **not** match on it |
| `size`, `protocol`, `downloadClient`, `statusMessages`, `errorMessage` | informational | log/debug only (sanitized) |

Deluge client mapping (`Deluge.GetItems`, identical in Sonarr and Radarr) `[VERIFIED]`:
- `state == Error` → `warning`
- `is_finished && state != Checking` → **`completed`**
- `state == Queued` → `queued`
- `state == Paused` → `paused`
- everything else → `downloading`

The client is listed only if the torrent carries the configured label (`tv-sonarr` / `radarr` on the NAS), because `GetTorrentsByLabel` is used when a category is set.

### Queue lifecycle facts
- The queue contains every **labelled** torrent the arr tracks, grabbed by the arr or not. Exceptions: state `Imported`, `Failed` and `Ignored` are dropped (`DownloadMonitoringService.DownloadIsTrackable`). If Completed Download Handling is **off**, `completed` items are dropped too. CDH is `True` on both NAS arrs. `[VERIFIED]`
- After the arr imports *everything* in a download, the record **disappears**. A partial Sonarr import (some episodes) keeps the record (`ImportPending`/`ImportBlocked`). `[VERIFIED: CompletedDownloadService.VerifyImport]`
- The arr refreshes the client roughly every 60 s (RefreshMonitoredDownloads). A "completed" verdict can therefore lag Deluge by about a minute. That is acceptable, since holding is safe. `[ASSUMED interval; the debounce/refresh cadence was not traced]`
- Pending/delay releases (`status: delay`) have no `downloadId`/`outputPath`. Ignore records with an empty `outputPath` or `downloadId`.
- The NAS also has SABnzbd/iPlayarr usenet clients in both arrs. Their records have unrelated `outputPath`s. A basename collision with a torrent is possible but rare. It is handled as **ambiguous → hold**, not filtered by protocol (the gate stays generic for other users' setups).

### Exact matching rule (recommended)
1. For each **enabled** arr, the snapshot must be a successful fetch with valid JSON (list of dicts). Otherwise that arr is *unavailable*.
2. `key(record) = basename(outputPath)`: strip trailing `/` and `\`, split on both separators. Compare **case-sensitively** with the SeedSyncarr root name (Linux filesystem, exact torrent name).
3. Candidates = all records across all enabled arrs whose key == root name and whose `downloadId` is non-empty. Group by `downloadId.upper()`.
4. Verdict, in this order:
   - **Proven:** exactly one group, every record has `status.lower() == "completed"` and numeric `sizeleft == 0`, **and every enabled arr's snapshot is available**.
   - **Unavailable** (`"Sonarr unavailable"` / `"Radarr unavailable"`): any enabled arr has no usable snapshot. This applies even if the other arr proves it; see Assumption A3.
   - **Ambiguous** (`"Ambiguous match"`): more than one distinct `downloadId` group.
   - **No queue entry** (`"No matching queue entry"`): zero candidates.
   - **Still downloading** (`"Still downloading"`): one group, but any record has status ≠ `completed` or `sizeleft` ≠ 0. That covers `queued/paused/downloading/warning/failed/delay/unknown/...`.

### The completion predicate, stated exactly
`proven(root) ⇔ all_enabled_arr_snapshots_ok ∧ |{downloadId(r) : r ∈ R}| = 1 ∧ ∀ r ∈ R: lower(r.status) = "completed" ∧ r.sizeleft = 0`, where `R = { r ∈ ⋃ snapshots : basename(r.outputPath) = root ∧ r.downloadId ≠ "" }`.

A successful HTTP response with no matching record is **not** proof (D-04/D-05).

### Obsession replay against this predicate
At 20:17:31 Deluge was still downloading. Radarr's record would have shown `status: downloading`, `sizeleft ≈ 800 MB` → **Still downloading** → held. Deluge finished at 20:22:45, and Radarr's next refresh would read `completed`/`sizeleft 0` → proven → transfer of the full 55,477,377,022 B file. The 54,676,946,944 B copy could never have been produced.

## Standard Stack

### Core (no new runtime dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | `>=2.33.0` (already a runtime dep) | Arr queue HTTP | Already used by `web/handler/config.py` `_test_arr_connection` `[VERIFIED: pyproject.toml]` |
| pexpect | `>=4.9.0` (existing) | lftp stream / resync | Existing wrapper |
| hatchling | 1.32.4 (resolved by `python -m build` 2026-10-14) | Wheel/sdist backend | Existing backend; fix is config-only `[VERIFIED: local build]` |
| lftp | 4.9.2 in the shipped image (Debian bookworm `apt lftp`) | Transfers | `[VERIFIED: NAS container lftp --version]` |

### Supporting (CI/build-time only)
| Tool | Purpose | When |
|------|---------|------|
| `build` (pypa) | `python -m build` (already in CI) | publish-pypi job |
| `twine check` | Metadata/render check | New CI packaging-verify step. Use **non-strict**: `--strict` fails only on the missing `long_description` warning. Adding `readme` is optional; see Open Q4 |

**No `npm install` / `pip install` of new packages is planned.** Package Legitimacy Audit: not applicable. No external packages are added. (`build`/`twine` are PyPA tools used only in CI. `build` is already used there.)

## Architecture Patterns

### System Architecture Diagram

```
                 ┌──────────────── controller thread (ControllerJob.execute every cycle) ────────────────┐
 remote scan ──► ModelPipeline.update_model ──► Model (ModelFile.state, + hold_reason) ──SSE──► Angular list
 lftp `jobs -v` ─(Lftp.__run_command; resync if unsynced)─► status | None
                                                     │
 AutoQueue.process: sweep candidates (DEFAULT, remote>local, stability ok, not stopped/downloaded)
        │
        ▼
 CompletionGate.evaluate(candidate names) ── needs refresh? (interval elapsed & backoff ok) ──► ArrQueueClient
        │                                                                                  GET /api/v3/queue/details
        │                                                              Sonarr ◄───────────────┘ Radarr (each enabled arr, once)
        │  verdict per root: PROVEN | HOLD(reason)
        ├── HOLD  → record hold_reason (log on start/change), no cooldown stamp, not queued
        └── PROVEN → cooldown stamp → Command(QUEUE, AUTO)
                                   │
 web: POST /server/command/bulk {action:queue, files, release_unverified?} ─► Command(QUEUE, USER[, release])
                                   ▼
 CommandProcessor._handle_queue: gate re-check
        AUTO & !proven → skip quietly (hold stays)       USER & !proven & !release → fail 428 (+reason)
        proven or USER+release → LftpManager.queue (temp-file forced) → lftp pget/mirror → *.lftp
                                                                         └─ rename to final name only on completion
 Sonarr/Radarr poll /data/torrents ─► import ─► webhook ─► __check_webhook_imports
        root committed → normal path │ root transferring & child DOWNLOADED → credit child (persist)
        child not yet visible → pending notice (re-evaluated each cycle)
        root commits later with credited children → mark imported + arm auto-delete
 Timer ─► __execute_auto_delete: downloaded? state ok? submitted-unobserved? (NEW) coverage? → delete_local
```

### Recommended Project Structure (new/changed files)
```
src/python/controller/
├── arr_queue.py          # NEW: ArrQueueClient: fetch/validate /api/v3/queue/details per arr; no logging of keys
├── completion_gate.py    # NEW: CompletionGate: snapshot cache, backoff, match/verdict, hold registry + transition logs
├── controller.py         # construct gate (patchable at controller.controller.*), expose evaluate API, DEL-01 guard, IMP-03
├── auto_queue.py         # sweep: gate before cooldown stamp
├── command_processor.py  # QUEUE: gate re-check, AUTO skip / USER 428 / release flag
├── lftp_manager.py       # force use_temp_file; lock around submitted set; add-before-queue ordering
├── scan_manager.py       # force temp suffix for local/active scanners
├── model_builder.py      # set_hold_reasons(); apply to root DEFAULT files
src/python/lftp/lftp.py   # unsynced flag + sentinel resync
src/python/model/file.py  # hold_reason attribute (participates in __eq__)
src/python/web/serialize/serialize_model.py   # "hold_reason" key
src/python/web/handler/controller.py          # release_unverified on single + bulk queue
src/angular/src/app/services/files/{model-file,view-file,view-file.service}.ts
src/angular/src/app/pages/files/transfer-row.component.{ts,html}
src/angular/src/app/services/files/bulk-action-dispatcher.service.ts + services/server/bulk-command.service.ts
src/angular/src/app/common/localization.ts
src/e2e/tests/fixtures/seed-state.ts           # seed queue calls must pass the release flag (Pitfall 2)
src/python/pyproject.toml, .github/workflows/ci.yml
```

### Pattern 1: CompletionGate (shared per-cycle snapshot, capped backoff)
**What:** One object on the controller thread. `evaluate(names) -> Dict[name, Verdict]` refreshes each enabled arr's snapshot **only if** at least one name needs a verdict, the per-arr refresh interval has elapsed (recommend 30 s), and backoff allows. Backoff on failure: 30 → 60 → 120 → 240 → 300 s cap; reset on success. Use `time.monotonic()`. Keep `holds: Dict[name, reason]`. Log at INFO on hold start, reason change and clear only (D-11). Also keep an in-memory `verified: Dict[name, remote_size_at_proof]` so a re-queue in the same process (lftp job error, partial) does not re-hold after the arr has already imported and dropped the record. Invalidate the entry if the model's `remote_size` differs. Never persist manual approvals (D-08).
**Where it lives:** Construct it in `Controller.__init__`, next to the other managers, so tests can `patch('controller.controller.CompletionGate')` (D-05 pattern). AutoQueue already holds a `controller` reference (same thread), so add `Controller.evaluate_completion(names)` and `Controller.completion_verdict(name)`.
**Example (shape only):**
```python
# Source: derived from Sonarr/Radarr QueueService + Deluge.GetItems (see Arr Queue Semantics)
def _verdict(self, root: str) -> Verdict:
    for arr in self._enabled_arrs():
        if self._snapshots.get(arr) is None:
            return Verdict.hold("{} unavailable".format(arr.label))      # "Sonarr unavailable"
    groups: Dict[str, List[dict]] = {}
    for arr in self._enabled_arrs():
        for rec in self._snapshots[arr]:
            if _basename(rec["outputPath"]) == root and rec["downloadId"]:
                groups.setdefault(rec["downloadId"].upper(), []).append(rec)
    if not groups:
        return Verdict.hold("No matching queue entry")
    if len(groups) > 1:
        return Verdict.hold("Ambiguous match")
    (recs,) = groups.values()
    if all(r["status"].lower() == "completed" and r["sizeleft"] == 0 for r in recs):
        return Verdict.proven()
    return Verdict.hold("Still downloading")
```
**HTTP client rules:**
- `requests.get(url.rstrip('/') + '/api/v3/queue/details', headers={'X-Api-Key': key}, timeout=(3.05, 10), allow_redirects=False)`.
- Treat non-200, `requests.RequestException` and JSON/shape errors as unavailable.
- Validate types at the boundary: list of dicts, `outputPath`/`downloadId`/`status` are `str`, `sizeleft` is a number. Skip malformed records, and treat the arr as unavailable if the payload is not a list.
- Cap response size. Stream it, or reject `len(resp.content)` above ~8 MB.
- Log failures as `"<Arr> queue check failed: <ExceptionType>"` or a status code. **Never** log the URL with credentials, the key, headers or the body.
- **Do not** reuse `ConfigHandler._validate_url`. It rejects private IPs, and the NAS arr URLs are `http://192.168.7.233:8989/7878` (Pitfall 4).

### Pattern 2: Gate at submission + forced temp file (IMP-01)
**What:** No lftp job is submitted for an AUTO transfer until `proven`. lftp writes `<name>.lftp` and renames it only after a successful transfer (`FileCopyPeerFDStream::Do` → `rename(stream->full_name, new_name)` once `verify->Done()`). On a kill, crash or `cmd:at-exit "kill all"`, the temp file stays non-importable, and `pget -c` resumes from `<name>.lftp.lftp-pget-status` (`pgetJob.cc`: `status_file = local->full_name + ".lftp-pget-status"`, `LoadStatus()` when `pget_cont`). `[VERIFIED: lftp v4.9.2 source]`
**How to force:**
- In `LftpManager.__init__`, `self.__lftp.use_temp_file = True` (ignore config).
- In `ScanManager`, pass `use_temp_file=True` to `LocalScanner` and `ActiveScanner`.
- Keep `Config.Lftp.use_temp_file` parseable, because the loader requires the key (`test_config.py` missing-key checks).
- Remove or relabel the Settings checkbox (`options-list.ts:139-143`). Recommend relabel to read-only text, or remove it; see Open Q3.
- Log once at startup if the config says False: "Temp-file transfers are always on in 1.7.5; use_temp_file=False is ignored".
**Why not `xfer:verify-command`:** lftp has a native hook that runs before the rename (`xfer:verify` + `xfer:verify-command`; on non-zero exit, no rename and the job errors) `[VERIFIED: lftp.1 man + FileCopy.cc]`. It would need a subprocess plus IPC back into SeedSyncarr per file, including mirror children. Start-gating already proves completion before any byte is written. Do not use the hook in 1.7.5. Record it as the defense-in-depth option for Phase 120+.

### Pattern 3: Hold visibility + one-shot manual release
- **Model:**
  - Add `ModelFile.hold_reason: Optional[str]` (frozen like the other fields). `__eq__` already compares every `__dict__` key, so diffs and SSE updates follow automatically.
  - Add `ModelBuilder.set_hold_reasons(Dict[str,str])`, mirroring `set_submitted_files`: change-detected, and it marks `has_changes`. Apply the reason only to root files whose built state is `DEFAULT`.
  - Feed it from `ModelPipeline.feed_model_builder` using the gate's `holds`.
  - Serialize as `"hold_reason"`, a machine code or label string. Recommend sending a stable code (`sonarr_unavailable`, `radarr_unavailable`, `ambiguous_match`, `still_downloading`, `no_queue_entry`) and mapping it to the verbatim labels in `localization.ts`.
- **UI:**
  - `ModelFileJson.hold_reason?`, `ModelFile.hold_reason`, then `ViewFile.holdReason` in `view-file.service.ts`.
  - In `transfer-row`, when `status === DEFAULT && holdReason`, the badge label becomes **"Waiting"** (an existing secondary style, e.g. `badge bg-secondary`). Show the reason in the existing `file-meta` line and as the badge `title`.
  - Keep `BADGE_LABELS` unchanged for every existing state. Grep `src/e2e` for label tables if any label changes (memory: badge labels live in three places).
- **Release flow:**
  - Backend `Controller.Command` gains `release_unverified: bool = False`.
  - The single endpoint accepts `?release_unverified=true`. The bulk body accepts `"release_unverified": true`.
  - `CommandProcessor._handle_queue`:
    - USER, not proven, no flag → `(False, "Completion could not be verified: <label>", 428)`.
    - AUTO, not proven → skip quietly (`True`), so the hold stays.
    - USER with flag → submit and log WARNING "Manual release of unverified '<name>' (<reason>)".
  - The flag lives only on that Command object, and nothing is persisted.
- **Angular:**
  - `BulkActionDispatcher.dispatchQueue` collects results with `error_code === 428`.
  - If any, it calls `ConfirmModalService.confirm({ title, body: "Completion could not be verified. Transfer and release this item anyway?" + preview, okBtn: "Release" })`.
  - On OK, it re-dispatches `queue` for exactly those files with `release_unverified: true`.
  - 428 is not transient in `BulkActionResult.isTransientFailure` (only 0/429/5xx count), so selection handling is unaffected.

### Pattern 4: LFTP sentinel resync (XFER-06)
```python
# Source: lftp echo quote-removal verified live (lftp 4.9.2: `echo SYNC-"12"-END` -> `SYNC-12-END`)
def __resync(self) -> bool:
    nonce = secrets.token_hex(8)
    self.__process.sendline('echo SEEDSYNCARR-SYNC-"{}"-END'.format(nonce))   # tty echo keeps the quotes
    marker = re.escape("SEEDSYNCARR-SYNC-{}-END".format(nonce)).encode()
    try:
        self.__process.expect(marker, timeout=self.__resync_timeout)             # only lftp's output matches
        self.__process.expect(self.__expect_pattern, timeout=self.__resync_timeout)  # the fresh prompt after it
    except pexpect.exceptions.TIMEOUT:
        return False          # stay unsynced; a later call retries with a NEW nonce
    self.__synced = True
    return True
```
- Set `__synced = False` on **every** `pexpect.TIMEOUT` in `__run_command`, in both expect sites.
- At the top of `__run_command`: `if not self.__synced and not self.__resync(): raise LftpError("lftp command stream not synchronized")`.
- `status()` catches that case and returns `None`. Do not count it toward `MAX_CONSECUTIVE_STATUS_ERRORS` (timeouts don't count today either).
- `queue()` raises, so `LftpManager.queue` never adds the name to the submitted set, and the command fails with 500 as today.
- Resync timeout: ~15 s, shorter than 180 s, so a still-wedged lftp trips LftpManager's 30 s stall breaker less often.
- Stale prompts and old sentinels are consumed by `expect` scanning forward. An old nonce never matches a new marker.

### Pattern 5: DEL-01 guard
- Inside `__execute_auto_delete`, under `__model_lock`, after the evidence and state checks: `if file_name in self.__lftp_manager.submitted_unobserved_file_names(): defer_reason = "transfer submitted, awaiting lftp status"`. It re-arms through the existing `__defer_auto_delete`, so the existing 24-attempt budget and shutdown ordering apply.
- In `LftpManager`, protect `__submitted_unobserved` with a `threading.Lock` (add/clear/discard/snapshot).
- Recommended: add the name to the set **before** calling `lftp.queue` and discard it on `LftpError`. That shrinks the window in which lftp has a job the Timer cannot see. Keep the docstring contract ("cleared by any successful status").
- Once a successful status is observed (even an empty one), the set clears. The next firing then passes if the state is `DOWNLOADED/DEFAULT/EXTRACTED` and coverage holds. This matches "the job need not appear active if it already finished".

### Pattern 6: IMP-03 early per-episode credit
In `__check_webhook_imports`, replace the `continue` on "no transfer evidence" with:
1. **Child credit** (child-level match only: `matched_name.lower() != root_name.lower()`). Find the unique non-dir node under the root whose `name.lower() == matched_name.lower()`. Uniqueness is already guaranteed by `WebhookManager.process` ambiguity rejection. Credit iff all of:
   - `root.remote_size is not None`
   - `root.state in (DOWNLOADING, QUEUED)`, i.e. SeedSyncarr is actively transferring it (foreign-dir guard, incident 2026-08-21)
   - `child.state == DOWNLOADED`, which means no active transfer and `local >= remote` (`_determine_child_state`)
   - `child.remote_size is not None and child.local_size == child.remote_size`

   Then: `persist.add_imported_child(root, matched.lower())` **only**. Do **not** add to `downloaded_file_names` or `imported_file_names`, because `_commit_downloaded_membership` rule 2 would commit a still-transferring root. Do **not** schedule auto-delete. Log INFO "Credited early import of '<child>' in '<root>' (root still transferring)".
2. **Pending notice:** if the root is transferring but the child is not yet DOWNLOADED in the model (scan lag; Sonarr can only import a renamed, complete file), keep `(root, matched_name)` in a bounded in-memory pending list. Recommend max 1000 entries, with a TTL of 6 h on the monotonic clock. Re-evaluate it each cycle through the same function. It is dropped when credited, accepted through the root-committed path, or expired (WARNING on expiry).
3. **Arm on commit** (level-triggered, each cycle): for each root in `imported_children` that is in `downloaded_file_names` and **not** in `imported_file_names`, add it to `imported_file_names`, `_set_import_status`, and `__schedule_auto_delete` if enabled. This covers restart: credit is persisted, and the root commits later.
4. Coverage stays as is: `AutoDeleteManager.run_bfs_and_coverage` requires every on-disk video in `imported_children[root]`. Deletion still requires `downloaded_file_names` membership plus the state guard. Credit alone cannot delete (D-14).
- **Persistence:** `imported_children` is already serialized by `ControllerPersist.to_str`/`from_str`, and `Persist.to_file` is atomic. No format change is needed. Save cadence is every 30 s (`MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS`) plus at exit, so a crash within 30 s of a credit can lose it (Open Q5).

### Pattern 7: Packaging fix (REL-02)
```toml
# src/python/pyproject.toml. Verified locally 2026-10-14: 0 './' members, 82 wheel files,
# clean py3.12 install, `seedsyncarr --help` works, imports ok.
[tool.hatch.build.targets.wheel]
only-include = ["common", "controller", "lftp", "model", "ssh", "system", "web", "seedsyncarr.py", "scan_fs.py"]
exclude = ["**/__pycache__"]

[tool.hatch.build.targets.sdist]
only-include = ["common", "controller", "lftp", "model", "ssh", "system", "web", "seedsyncarr.py", "scan_fs.py", "pyproject.toml"]
```
- Root cause: `packages = ["."]` writes every member as `./…` (200 of 204 members in a rebuilt 1.7.4 wheel), and it ships `tests/`, `docs/`, `poetry.lock`, `pyproject.toml` and `PKG-INFO` inside the wheel. `[VERIFIED: local rebuild of HEAD]`
- Add a CI job `verify-python-package` on **every** push/PR, not only tags, so the next failure surfaces before a tag. Steps:
  - `python -m build`
  - `twine check dist/*`
  - assert there are no wheel/sdist members starting with `./` or containing `..` (a small inline Python check)
  - `python -m venv /tmp/v && /tmp/v/bin/pip install dist/*.whl && /tmp/v/bin/seedsyncarr --help`
  - Gate `publish-pypi` on it.
- Bump `version` to 1.7.5 in **both** `[project]` and `[tool.poetry]`. CI stamps only `^version =` lines, which hits both, but keep the repo consistent.
- Top-level module names (`common`, `model`, `web`, …) are pre-existing namespace pollution in site-packages. Do not rename them in a patch release; flag it for the Reliability milestone.

### Anti-Patterns to Avoid
- **Matching on `title`:** Sonarr strips the extension, so `X.mkv` → `X`.
- **Treating `trackedDownloadState` as completion:** it can read `downloading` on a completed download.
- **Using `/api/v3/queue` paged** with the default `pageSize=10`.
- **Treating an empty queue or a missing record as complete.**
- **Re-checking only at commit time:** this is explicitly insufficient (IMP-01).
- **Stamping the AutoQueue cooldown before the gate:** a released hold would then wait up to `REQUEUE_COOLDOWN_SECONDS = 300` extra.
- **Early child credit via `imported_file_names`:** this triggers `_commit_downloaded_membership` rule 2 and commits a partial root.
- **Reading LftpManager's set from the Timer without a lock:** `sorted(set)` can raise `RuntimeError: Set changed size during iteration`.
- **Logging arr responses, URLs with keys, or `X-Api-Key`.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deferring the lftp temp→final rename | A custom staging dir + SeedSyncarr rename | lftp `xfer:use-temp-file` (forced) + gate before submit | lftp already renames atomically and only on success. A custom rename would mean replacing the transfer engine (out of scope) |
| Download-complete detection | Remote mtime/size heuristics (999.1) | Arr `status == completed && sizeleft == 0` via `/queue/details` | Sparse files plateau at piece boundaries. Size and mtime are supporting evidence only (D-03) |
| Atomic persistence | New writer | `Persist.to_file` (Phase 118) | Already atomic, with fsync |
| Confirm dialog | New modal | `ConfirmModalService.confirm` | Existing pattern for delete confirmations |
| Ambiguity detection for webhook names | New matcher | `WebhookManager.process` (Phase 116) | Already rejects multi-path basenames |
| Retry/defer for auto-delete | New timer loop | `__defer_auto_delete` / `_AUTO_DELETE_MAX_REARMS` | Shutdown ordering is already proven |

## Runtime State Inventory

Not a rename/refactor phase, but several behavior changes touch runtime state:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `controller.persist` `imported_children` gains early credits (same schema). The NAS persist holds Days of Hope `imported_children = [part.4]` and Obsession `downloaded=True, imported=False` | None for the format. The old Done-group roots will not self-heal (the dropped Sonarr notices never recur), so they need manual cleanup by the owner. Mention it in the release notes |
| Live service config | NAS `settings.cfg`: `use_temp_file = True`, `remote_stability_seconds = 90`, `local_stability_seconds = 30`, Sonarr/Radarr enabled with private-IP URLs | None. Verify that the container can reach `192.168.7.233:8989/7878` in the smoke test |
| OS-registered state | None. Verified: no new services or schedulers | None |
| Secrets/env vars | `sonarr_api_key` / `radarr_api_key` (`secret=True`, possibly encrypted in settings.cfg) | Read through the Config object only. Never log |
| Build artifacts | PyPI has no 1.7.4. The last PyPI release predates 1.7.4 | The 1.7.5 publish must succeed. Do not re-run the 1.7.4 job |

## Common Pitfalls

### Pitfall 1: Gate blocks all auto-queue when no arr is enabled
**What goes wrong:** Public users without Sonarr/Radarr get every item held ("unavailable"), and USER Queue requires confirmation every time.
**Why:** D-07 has no "non-arr" exemption, but CONTEXT does not address the *arr integration disabled entirely* configuration.
**How to avoid:** Get an owner decision (Open Q1) before planning finalizes. The planner must implement exactly one documented behavior with a test.

### Pitfall 2: e2e and integration tests queue unverified items
**What goes wrong:** `src/e2e/tests/fixtures/seed-state.ts` POSTs `/server/command/queue/<file>` and expects 2xx. With the gate, the e2e harness (no arr configured) gets 428, and seeding plus most dashboard e2e specs fail. Python `integration/test_controller/test_controller.py` (25 QUEUE uses) and the unit suites (`test_controller_unit.py` 15, `test_transfer_state_safety.py` 9, `test_auto_queue.py` 45) will also change behavior.
**How to avoid:**
- e2e seed helpers pass `?release_unverified=true`.
- `tests/unittests/test_controller/base.py` patches `controller.controller.CompletionGate`, default verdict PROVEN, so existing tests keep their meaning. New tests assert the gate's interaction explicitly.
- Integration tests pass the flag, or patch the gate to PROVEN.
- AutoQueue tests need a controller stub method for the verdict.

### Pitfall 3: Cooldown stamped before the hold check
**What goes wrong:** An item verified at T+31 s still waits up to 300 s.
**How to avoid:** In `AutoQueue.process`, the order is filter stopped/downloaded → gate → cooldown → queue. A held item never stamps `__last_queue_attempt`.

### Pitfall 4: Reusing the SSRF validator
**What goes wrong:** `ConfigHandler._validate_url` rejects private/loopback IPs, and the NAS arrs live at `192.168.7.233`, so every check would be "unavailable" forever.
**How to avoid:** The arr URL is operator configuration, not request input, so do not apply the private-IP rejection. Keep `http/https` scheme validation and `allow_redirects=False`.

### Pitfall 5: Restart after the arr already imported everything
**What goes wrong:** The pack's videos are imported (record gone), the root is still DOWNLOADING (subs/extras), SeedSyncarr restarts, and the re-queue holds with "No matching queue entry" forever.
**How to avoid:** Accept it as an edge case. It is visible and the user can manually release. The in-memory `verified` cache covers the same-process case. Do not persist approvals (D-08). Persisting *proofs* is an option, but adds schema and is not recommended for 1.7.5.

### Pitfall 6: Cross-thread submitted set
**What goes wrong:** The Timer thread reads `submitted_unobserved_file_names()` while the controller thread adds or clears. `sorted(set)` can raise mid-iteration and kill the Timer callback silently, which means no defer and no delete.
**How to avoid:** Add a lock in LftpManager. Return a snapshot list.

### Pitfall 7: Resync matching the tty echo
**What goes wrong:** pexpect sees the echoed command line `echo X` before lftp's output, so a naive `expect("X")` matches the echo, and the stream is declared synced while still desynchronized.
**How to avoid:** Use the quote-split sentinel (Pattern 4) so the echoed text and the output differ.

### Pitfall 8: Early credit committing a partial root
**What goes wrong:** Adding the root to `imported_file_names` during IMP-03 makes `_commit_downloaded_membership` commit it to `downloaded_file_names` while it is still DOWNLOADING. That breaks re-queue and arms deletion.
**How to avoid:** Write child credit to `imported_children` only. Use arm-on-commit (Pattern 6, step 3).

### Pitfall 9: Integration tests asserting final names mid-transfer
**What goes wrong:** With forced temp files, in-flight files are `*.lftp`. CI-only integration tests (`integration/test_controller`, `integration/test_lftp`) that inspect partial local files by final name will change behavior.
**How to avoid:** Grep those suites for mid-transfer `os.path` checks. The local scanner maps `.lftp` → name, so model-level assertions are unaffected.

### Pitfall 10: Ruff version skew
**What goes wrong:** Local ruff is 0.15.9, CI pins 0.15.22.
**How to avoid:** Run `ruff check src/python/` with the pinned 0.15.22 (`pip install ruff==0.15.22` in a scratch venv) whole-tree before each push.

## Code Examples

### Fake pexpect stream for the XFER-06 regression
```python
# Pattern for tests/unittests/test_lftp/test_lftp_resync.py. Drives the REAL Lftp.__run_command.
class _FakeStream:
    """Byte buffer that emulates a pty: sendline appends the echoed command, then
    scripted output becomes available; expect() regex-searches the buffer and consumes it."""
    def __init__(self, prompt=b"lftp u@h:~> "):
        self.buf, self.prompt, self.before, self.after = b"", prompt, b"", b""
        self.pending = []   # scripted chunks released on each sendline
    def isalive(self): return True
    def sendline(self, s):
        self.buf += s.encode() + b"\r\n"
        if self.pending: self.buf += self.pending.pop(0)
    def expect(self, pattern, timeout=None):
        rx = re.compile(pattern if isinstance(pattern, bytes) else pattern.encode())
        m = rx.search(self.buf)
        if not m:
            self.before = self.buf
            raise pexpect.exceptions.TIMEOUT("fake")
        self.before, self.after, self.buf = self.buf[:m.start()], m.group(0), self.buf[m.end():]
        return 0
```
Regression script (fails before, passes after):
1. `jobs -v` times out with an empty buffer.
2. A delayed stale prompt arrives.
3. The next `status()` must NOT return `[]`. Before the fix it matches the stale prompt and parses empty output → `[]`.
4. After the fix it resyncs, then runs `jobs -v` and returns the real job list.
5. Assert the submitted set and DOWNLOADING state are kept while unsynced.

### Incident regressions to encode
- **Obsession:**
  - Model root `Obsession…mkv`, remote 55,477,377,022, stable for 90 s.
  - Radarr snapshot record `{outputPath: "/data/torrents/Obsession…mkv", downloadId: "ABC", status: "downloading", sizeleft: 800430078}` → the sweep issues **no** QUEUE command and `hold_reason == "still_downloading"`.
  - Then the snapshot shows `completed/0` → QUEUE is issued.
  - Also cover: arr raises ConnectionError → hold "Radarr unavailable" with no command, and backoff grows (assert the fetch count across cycles).
- **Days of Hope:**
  - Root dir DOWNLOADING with children p1..p3 DOWNLOADED and p4 DOWNLOADING.
  - Webhooks for p3, p1, p2 → `imported_children[root] == {p1,p2,p3}`, no timer, root not in `imported_file_names`.
  - Persist round trip (`to_str`/`from_str`) keeps them.
  - The root commits, then the p4 webhook arrives → timer armed → coverage passes → delete.
  - Variant: no p4 webhook arrives before commit → arm-on-commit fires, coverage defers until p4 credited.
  - Negative: a foreign local-only dir (no remote) never gets credit.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Size stability (`remote_stability_seconds`) as the queue gate | Arr queue `completed` + `sizeleft == 0`; stability kept as supporting | 1.7.5 | Sparse-file plateau can no longer start a transfer |
| `packages = ["."]` | `only-include` explicit modules | 1.7.5 | Valid wheel member paths; no tests/docs in the wheel |
| Paged `/api/v3/queue` (pageSize 10) | `/api/v3/queue/details` (unpaged) | Available since Sonarr v3 | One request per arr per cycle |
| Sonarr v3 `status` as a string | v4 `QueueStatus` enum, camelCase | Sonarr v4 | Same wire values (`completed`); compare case-insensitively |

**Deprecated/outdated:**
- `sizeleft`/`timeleft` are `[Obsolete("Will be replaced by SizeLeft")]` in Sonarr v4 and Radarr, but still emitted. Read `sizeleft`, falling back to `sizeLeft` if present. If neither is present, the arr has changed its API: treat it as not proven and log once.

## Dependabot / Release Triage (user CLAUDE.md release rule)

Open alerts (queried 2026-10-14):
- **#93** `source-map-js` < 1.2.2, npm, **development** scope (`src/angular/package-lock.json`, pulled in by `sass` and `@angular/build` → postcss), high. It is build-time only and **unrelated to the PyPI packaging failure**. Per REL-02 ("evaluated only as relevant"), it is not part of the packaging repair. Under the release rule it is cheap: a lockfile bump of the transitive dependency via `npm update source-map-js` or an `overrides` entry. Owner decides (Open Q6).

Open Dependabot PRs:

| PR | Change | Scope | Notes |
|----|--------|-------|-------|
| #123 | cryptography 50.0.1→50.0.2 | **runtime** | Wheels rebuilt with OpenSSL 4.0.3. No open alert; possibly security-relevant. Owner decides |
| #124 | pytz | runtime | Data update |
| #125 | testfixtures | dev | — |
| #122 | 8 npm dev bumps, incl. `sass` 1.105.1 | dev | Major `@types/jasmine` 7 included |
| #117 | puppeteer | dev | — |

The scope boundary forbids "unrelated dependency churn". Surface the list to the owner at the release checkpoint as plain-English choices.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Radarr 3.x/4.x also expose `/api/v3/queue/details` (verified for Radarr develop/v6 and the live 6.4.4, and Sonarr v3/v4) | Arr Queue Semantics | Very old Radarr installs get "Radarr unavailable" holds. Mitigation: on 404, the planner may fall back to paged `/queue?includeUnknownMovieItems=true&pageSize=1000` with a `totalRecords` check |
| A2 | Arr refreshes the download-client state about every 60 s | Arr Queue Semantics | Only affects hold duration, not safety |
| A3 | Proof requires **all enabled** arrs to have a fresh snapshot (strict reading of D-04) | Pattern 1 | Stricter than necessary: a Sonarr outage also holds movies. Owner may prefer "proof from any arr suffices when the match is unique" |
| A4 | Root state DOWNLOADING/QUEUED is required for early child credit (foreign-dir guard) | Pattern 6 | A notice arriving after an lftp job error (root DEFAULT, partial) is not credited until re-queue. Pending re-evaluation covers it |
| A5 | Pending-notice TTL 6 h / cap 1000; backoff 30→300 s; refresh 30 s; resync timeout 15 s | Patterns 1, 4, 6 | Tunable constants (discretion) |
| A6 | HTTP 428 as the "needs confirmation" code | Pattern 3 | Any non-transient 4xx works. Must not be 409 (already used for state conflicts) |

## Open Questions (owner/product decisions; bring to the plan checkpoint)

1. **Behavior when neither Sonarr nor Radarr is enabled** (public users, e2e)
   - Known: D-07 holds unverifiable items, and there is no arr to ask.
   - Unclear: should all auto-queue be held ("Completion check not configured"), or keep pre-1.7.5 behavior when the integration is off?
   - Recommendation: strict hold, with a fifth label "Sonarr/Radarr not configured", because it matches D-07. The planner needs the owner's answer, since it changes the product for non-arr users.
2. **One arr down, other arr proves it** (A3)
   - Recommendation: strict (hold) for 1.7.5.
3. **Settings checkbox "Rename unfinished/downloading files"**
   - Options: remove it, or make it read-only "Always on".
   - Recommendation: remove it from `options-list.ts` and keep the config key for compatibility. This is a tiny UI removal; confirm it counts as part of the owner-approved exception.
4. **`twine check --strict`**
   - Strict fails only on the missing `long_description`.
   - Recommendation: non-strict `twine check` plus member-path assertions plus clean install. Optionally add `readme`, which requires a file under `src/python/`.
5. **Credit crash window**
   - Persist runs every 30 s, so a hard crash within 30 s of a credit loses it.
   - Recommendation: accept it (clean restarts persist at exit). Alternatively the controller could request an immediate persist through a callback. Not recommended for a patch.
6. **Dependabot #93 and runtime PRs (#123 cryptography, #124 pytz)**
   - Roll in or defer, per the user's release rule. #93 is dev-only and cheap.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| poetry + project venv | host unit tests | ✓ | — | — |
| ruff | lint gate | ✓ (0.15.9) | CI pins 0.15.22 | Install 0.15.22 in a scratch venv |
| python3.12 | clean-install packaging check | ✓ | /opt/homebrew/bin/python3.12 | — |
| Docker daemon (local) | `make run-tests-python`, Angular/e2e containers | ✗ (daemon down at research time) | client 29.4.3 | CI is the authority for the full suite, Angular and e2e. Start Docker Desktop for local container runs |
| lftp (local) | — | ✗ | — | Unit tests mock pexpect. Integration runs in CI |
| NAS (`ssh nas`), Sonarr 4.0.20, Radarr 6.4.4 | queue-semantics verification, smoke, deploy | ✓ | — | — |
| gh CLI | Dependabot triage, release | ✓ | — | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 (unittest.TestCase style), pytest-timeout 60 s; Angular Karma/Jasmine (CI Docker); Playwright e2e (CI) |
| Config file | `src/python/pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_lftp tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_auto_delete_rearm.py tests/unittests/test_controller/test_auto_queue.py tests/unittests/test_controller/test_transfer_state_safety.py tests/unittests/test_controller/test_import_ambiguity.py -q -p no:cacheprovider` (baseline 288 passed in 0.35 s, 2026-10-14) |
| Full suite command | Host: `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py` (118 convention). Authority: CI `unittests-python` (`make run-tests-python`) |
| Lint | `ruff check src/python/` whole tree with ruff 0.15.22 |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XFER-06 | Stale prompt after timeout never yields trusted `[]`; resync then real status | unit (fake stream, RED first) | `pytest tests/unittests/test_lftp/test_lftp_resync.py -q` | ❌ Wave 0 |
| XFER-06 | Unsynced + resync fail → status None, queue raises, submitted set untouched | unit | same file + `test_lftp_manager.py` | ❌ / ✅ extend |
| DEL-01 | Timer + status None + submitted root → defers; after successful status → deletes | unit (RED first) | `pytest tests/unittests/test_controller/test_auto_delete_rearm.py -q -k submitted` | ✅ extend |
| DEL-01 | Submitted set thread-safe snapshot | unit | `pytest tests/unittests/test_controller/test_lftp_manager.py -q -k lock` | ✅ extend |
| IMP-01 | LftpManager forces use_temp_file True even when config False; scanners get the suffix | unit | `pytest tests/unittests/test_controller/test_lftp_manager.py tests/unittests/test_controller/test_scan_manager.py -q -k temp` | ✅ extend |
| IMP-02 | Arr client: shape validation, unavailable on errors/non-200/bad JSON, no key in logs | unit (mock `requests.get`) | `pytest tests/unittests/test_controller/test_arr_queue.py -q` | ❌ Wave 0 |
| IMP-02 | Gate verdict matrix: proven / still downloading / no entry / ambiguous / unavailable; Sonarr per-episode grouping; backoff growth/reset; one fetch per arr per cycle | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -q` | ❌ Wave 0 |
| IMP-02 | Obsession replay: sweep holds while downloading, queues after completed; hold_reason in model; no cooldown stamp while held | unit (RED first) | `pytest tests/unittests/test_controller/test_auto_queue.py -q -k completion` | ✅ extend |
| IMP-02 | USER queue unverified → 428; with flag → submitted once; flag not persisted; AUTO re-check skips | unit | `pytest tests/unittests/test_controller/test_controller_unit.py tests/unittests/test_web/test_handler/test_controller_handler.py -q -k release` | ✅ extend |
| IMP-02 | hold_reason serialized; model diff on reason change | unit | `pytest tests/unittests/test_web/test_serialize/test_serialize_model.py tests/unittests/test_controller/test_model_builder.py -q -k hold` | ✅ extend |
| IMP-02 | UI: Waiting badge + reason; 428 → confirm → re-dispatch with flag | Angular unit | CI `make run-tests-angular` (specs: `transfer-row.component.spec.ts`, `bulk-action-dispatcher.service.spec.ts`, `view-file.service.spec.ts`, `model-file.spec.ts`) | ✅ extend |
| IMP-03 | Days of Hope replay: early credit, no timer, persist round trip, arm-on-commit, coverage passes | unit (RED first) | `pytest tests/unittests/test_controller/test_import_credit.py -q` | ❌ Wave 0 |
| IMP-03 | Ambiguous basename still rejected; foreign dir never credited; credit alone never deletes | unit | same + `test_import_ambiguity.py` | ✅ extend |
| REL-02 | No `./` members, twine check, clean-venv install, `seedsyncarr --help` | CI job + local script | `python -m build && twine check dist/* && <member-check> && pip install dist/*.whl` | ❌ Wave 0 (CI job) |
| REL-03 | Full suite, ruff, CI green; smoke on release image; NAS digest match + scan recovery | manual/CI | 118-style runbook (`118-REL01-EVIDENCE.md`) | ✅ precedent |

### Sampling Rate
- **Per task commit:** the quick run command plus `ruff check src/python/`.
- **Per wave merge:** host full suite plus ruff 0.15.22.
- **Phase gate:** CI green (python, angular, lint, e2e, packaging-verify) before `/bm:verify-work`. Each targeted regression is shown red before its fix (REL-03).

### Wave 0 Gaps
- [ ] `tests/unittests/test_lftp/test_lftp_resync.py`: fake-stream harness (XFER-06)
- [ ] `tests/unittests/test_controller/test_arr_queue.py`: client fixtures, using a real-shape JSON sample built from the QueueResource fields above (IMP-02)
- [ ] `tests/unittests/test_controller/test_completion_gate.py` (IMP-02)
- [ ] `tests/unittests/test_controller/test_import_credit.py` (IMP-03)
- [ ] `tests/unittests/test_controller/base.py`: add a `CompletionGate` patcher defaulting to PROVEN (keeps 100+ existing tests meaningful)
- [ ] CI `verify-python-package` job (REL-02)
- [ ] e2e `seed-state.ts` release flag (Pitfall 2)

## Release Gate (REL-03): established process (from Phase 118)
1. Merge to `main`, keeping history. Bump versions: `package.json`, `src/angular/package.json`, and `package-lock.json` (root `version` + `packages[""].version`). These are all checked by `scripts/verify-release-metadata.mjs`. Also bump the `CHANGELOG.md` `## 1.7.5` heading, `release-notes.md`, and `pyproject.toml` (both version lines).
2. One owner approval before pushing the annotated `v1.7.5` tag. Include the Dependabot list and the plain-English release notes. The release notes should mention: temp-file always on; held items and manual release; Done-group roots from the incidents need manual cleanup.
3. Tag CI publishes the GHCR multi-arch `:1.7.5` (`publish-docker-image` **rebuilds**, so smoke the pulled tag, not staging), the GitHub release, and PyPI.
4. Smoke the exact `:1.7.5` image: startup, real transfer (verify `.lftp` temp then rename), import visibility and webhook handling, automatic cleanup, settings persistence, restart. Also verify a held item shows "Waiting" with its reason when the arr is unreachable.
5. NAS:
   - Pin compose to `:1.7.5`. Never `:dev`. Keep the digest pin and the wud semver filter.
   - Confirm `RepoDigests` matches the published index digest.
   - Verify a successful scan after any startup scanner error.
   - Verify the container reaches the arr URLs (no "unavailable" holds in steady state).
   - Use `sudo /usr/local/bin/docker …`.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | Existing web auth covers the new flag |
| V4 Access Control | yes | `release_unverified` accepted only on existing authenticated command endpoints. The backend enforces it; the UI only prompts |
| V5 Input Validation | yes | Arr JSON shape validation at the boundary; bulk `release_unverified` must be a strict bool; the lftp queue name escape stays |
| V7 Error Handling & Logging | yes | `sanitize_log_value` on outputPath/title/root names; never log key, headers, body or URL with a key; generic errors to clients |
| V6 Cryptography | no | — (encrypted settings untouched) |
| V12/V13 API | yes | Response-size cap and timeouts on outbound arr calls; 428 for the confirm path |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leak through logs/exceptions | Information disclosure | Log exception type only; header auth, never a query string |
| Log injection through torrent names in arr responses | Tampering | `sanitize_log_value` (CWE-117 pattern from Phase 116) |
| Oversized/malformed arr response stalls the controller | DoS | `(3.05, 10)` timeouts, size cap, type validation, backoff |
| Bypass of the gate through the API flag | Elevation | Same trust level as the existing Queue; WARNING log on every manual release |
| lftp command injection through names | Tampering | Existing `escape()` (rejects `\n\r\0`). The sentinel uses a hex nonce only |

## Sources

### Primary (HIGH confidence)
- Sonarr `main` (v4) source: `QueueResource.cs`, `QueueService.cs`, `QueueStatus.cs`, `QueueController.cs`, `QueueDetailsController.cs`, `TrackedDownload.cs`, `TrackedDownloadService.cs`, `DownloadMonitoringService.cs`, `CompletedDownloadService.cs`, `Deluge.cs`, `DelugeTorrent.cs`, `DelugeProxy.cs`, `STJson.cs`, `PagingResource.cs`, via https://github.com/Sonarr/Sonarr
- Sonarr `v3` branch: `QueueResource.cs` (string status, `FirstCharToLower`), `QueueDetailsModule.cs`
- Radarr `develop` source: `QueueResource.cs`, `QueueService.cs`, `QueueController.cs`, `QueueDetailsController.cs`, `Deluge.cs`, via https://github.com/Radarr/Radarr
- Live NAS probe 2026-10-14 (read-only): Sonarr 4.0.20.3014, Radarr 6.4.4.10685, `/queue/details` 200, Deluge labels, CDH on, remote path mappings, SeedSyncarr settings (no secrets printed)
- lftp v4.9.2 source (`FileCopy.cc` TempFileName/rename-after-verify, `pgetJob.cc` status file and continue) and the `lftp.1` man page (`xfer:use-temp-file`, `xfer:temp-file-name`, `xfer:verify`, `xfer:verify-command`), https://github.com/lavv17/lftp ; https://lftp.yar.ru/lftp-man.html
- Live lftp 4.9.2 in the NAS container: `echo SYNC-"12"-END` → `SYNC-12-END`; defaults `xfer:use-temp-file no`, `xfer:temp-file-name .in.*`
- Local build reproduction: `python -m build` (hatchling 1.32.4) of HEAD → 200 of 204 `./` members; `only-include` fix → 0, clean py3.12 install OK
- Codebase: files listed in Recommended Project Structure; `gh api` Dependabot alerts/PRs

### Secondary (MEDIUM)
- Debug diagnosis `.planning/debug/done-group-no-auto-delete.md` (incident timelines, specialist review)

### Tertiary (LOW)
- Arr download refresh cadence (~60 s), recalled from memory, not traced

## Metadata

**Confidence breakdown:**
- Arr queue semantics: HIGH (source in three branches plus live endpoint)
- lftp temp-file and resync: HIGH (source plus live echo test). The resync mechanism is new code, validated by the fake-stream test and CI integration
- Packaging: HIGH (reproduced and fixed locally)
- IMP-03 design: MEDIUM-HIGH (integration points verified; constants are discretion)
- Product edge cases (no arr configured, one arr down): needs owner input

**Research date:** 2026-10-14
**Valid until:** 2026-11-13 (arr APIs are stable; re-check if Sonarr v5 ships to the NAS)
