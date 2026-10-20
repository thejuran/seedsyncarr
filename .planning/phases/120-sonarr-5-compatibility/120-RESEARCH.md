# Phase 120: Sonarr 5 Compatibility - Research

**Researched:** 2026-10-20
**Domain:** Sonarr v3-API compatibility verification (queue/details, system/status, webhook payloads) on Sonarr 5.0.0.2701; fixture-based CI regression tests; conditional patch release
**Confidence:** HIGH (code paths, Sonarr source diff, and live sandbox state all verified this session)

## Summary

SeedSyncarr makes exactly two outbound Sonarr calls, both on `/api/v3`: `GET /api/v3/system/status` for Test Connection (`src/python/web/handler/config.py:157-170`, reads only `version`), and `GET /api/v3/queue/details` for completion evidence (`src/python/controller/arr_queue.py:144`, reads only `outputPath`, `downloadId`, `status`, `sizeleft`/`sizeLeft`). Inbound, the webhook handler (`src/python/web/handler/webhook.py`) reads only `eventType` and `episodeFile.sourcePath`. The Sonarr source at tag `v5.0.0.2701` (commit 7ccafd3, which is `develop` HEAD as of 2026-10-19) has **no differences from v4.0.20.3014 in any field SeedSyncarr reads**. `QueueResource` still serializes the obsolete `sizeleft`/`timeleft` properties, `queue/details` now runs on `IObsoleteQueueService` but keeps the v4 one-record-per-episode shape, and `WebhookImportPayload`/`WebhookEpisodeFile`/`WebhookEventType` are byte-identical [VERIFIED: gh api Sonarr/Sonarr contents diff, this session].

The live sandbox already shows the core behavior working on 5.0.0.2701. The `seedsyncarr-test` log for 2026-10-20 has `Completion hold for '<root>': Still downloading` followed by `Completion hold cleared`, and nine Sonarr/5.0.0.2701 `Download` webhooks matched by `episodeFile.sourcePath` and recorded as imports [VERIFIED: NAS read-only log inspection]. So the phase is mostly **evidence capture plus fixture-based CI tests**, and the expected outcome is "verified; no release needed". The one exception, a **deterministic SON5-01 failure that is not a Sonarr 5 issue**, is below.

**Critical finding: Test Connection will fail on the sandbox as configured.** `seedsyncarr-test` has `sonarr_url = http://sonarr-v5:8989`, which resolves to `172.19.0.6`. `ConfigHandler._validate_url` rejects any private, loopback, reserved or link-local address, so the button returns "URL resolves to a private/reserved IP address" before Sonarr is ever contacted [VERIFIED: resolved inside the container, `is_private=True`]. This is the known Reliability item 5 ("Support intended LAN connection tests"), not a Sonarr 5 incompatibility. The queue client does not apply this check, which is why holds and releases work. A validated workaround exists: the NAS Tailscale address (100.x, CGNAT) passes `_validate_url` (Python 3.11 `is_private=False`) and reaches `sonarr-v5` through published port 8990 from inside `seedsyncarr-test` (`/ping` returned 200) [VERIFIED].

**Primary recommendation:** Plan three waves: (1) CI fixture tests plus a sanitization guard, written against hand-built placeholder fixtures; (2) live capture on the sandbox, with owner/operator steps for the real grab, the Deluge directory tweak and the Test Connection URL, then swap in the sanitized real fixtures; (3) a SON5-05 decision gate that closes "verified; no release needed" unless a Sonarr-5-caused failure appears. Treat the Test Connection private-IP rejection as a known pre-existing limitation, verified with the Tailscale-URL workaround, and surface it to the owner. Do not pull the LAN fix into 1.7.7 without an owner decision.

## User Constraints (no CONTEXT.md; derived from REQUIREMENTS.md / ROADMAP.md scope boundary)

### Locked (from requirements and owner decisions recorded in STATE/ROADMAP)
- Live checks run **only** on the NAS sandbox: `seedsyncarr-test` (1.7.6, compose project `v5test`, `/volume1/docker/v5test/docker-compose.yml`, host port 8801) against `sonarr-v5` (Sonarr 5.0.0.2701, host port 8990, container port 8989). Production `seedsyncarr`, `sonarr` and `radarr` are not touched.
- No API v5 migration (backlog 999.5). No Radarr changes. No webhook signing changes (existing HMAC retained).
- Release is conditional: ship 1.7.7 only if a SON5-01..03 check fails, deploy **by release tag, never `:dev`**. Otherwise close "verified; no release needed" with tests and evidence committed.
- Fixtures: system status, queue details incomplete and complete, Test and Download webhooks. Sonarr version and capture scenario recorded alongside each. No keys, hostnames or personal paths.

### Claude's Discretion (no discuss-phase; planner decides)
- Fixture layout, manifest format, sanitizer and CI guard design (recommendations below).
- Capture mechanics (recommendations below).

### Deferred (OUT OF SCOPE)
- API v5 migration (999.5), LAN connection-test fix (Reliability item 5, Phase 121+), Radarr, production Sonarr upgrade, the `arr-setup.md` doc discrepancy noted under Pitfalls (record it, don't fix it unless the owner promotes it).

## Project Constraints (from CLAUDE.md)

No project `./CLAUDE.md` exists. User-global directives that apply:
- **Security (absolute):** never hardcode secrets, never log sensitive data. Fixtures and evidence must not contain API keys, the seedbox hostname or username, NAS IPs, Tailscale IP or personal paths. Capture scripts must never echo the Sonarr API key (read it from `config.xml` into a shell variable or a 0600 file).
- **Releases:** before any version bump or tag, review open Dependabot alerts (`gh api repos/thejuran/seedsyncarr/dependabot/alerts` with `state=open`) and PRs (`gh pr list --author app/dependabot`). Triage runtime vs dev, then surface them in plain terms. At research time: **0 open alerts returned**; open PRs **#128** (angular npm group, 21 updates), **#125** (testfixtures dev), **#117** (puppeteer dev), all previously deferred as dev/test-only [VERIFIED: gh, this session].
- **Division of labor:** technical choices are Claude's. Product choices go to the owner: whether to grab real content on private trackers, whether to accept the Test Connection workaround, and whether 1.7.7 (if needed) goes to prod.
- **NAS access:** `ssh nas`, docker **only** via `sudo /usr/local/bin/docker ...` (absolute path).
- **Planning format:** follow `/Users/julianamacbook/Documents/Codex/planning/PLANNING-FORMAT.md` when touching STATE/ROADMAP (STATE `last_updated` refresh, truthful status).
- **Memory notes:** CI runs `ruff check src/python/` as a separate gate (whole tree). Deploy by release tag (`:X.Y.Z` plus digest pin). The app log clock is the NAS host clock plus 1h (seen again on the sandbox: log line 14:32 vs file mtime 13:32).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SON5-01 | Test Connection shows success with 5.x version | `config.py:_test_arr_connection` reads only `version`. Live `system/status` returns `version: "5.0.0.2701"`. **Blocked by the private-IP SSRF guard with the current sandbox URL**, so use the Tailscale-URL workaround (§Live capture, Step L1). CI: feed the captured `system_status.json` into the handler test. |
| SON5-02 | Waiting while incomplete, released only when the same download is complete; negatives hold | Gate semantics in `completion_gate.py` (basename(outputPath)==root, one downloadId group, all `status=="completed"` and `sizeleft==0`). Sonarr 5 fields unchanged. Deluge move-on-complete makes the "incomplete and visible" window transient, so an operator tweak is needed (§Pitfall 2). CI: replay the incomplete and complete fixtures through a real `ArrQueueClient` and `CompletionGate`. |
| SON5-03 | Test event accepted, marks nothing; real import marks exactly the right file | `webhook.py` returns "Test OK" before extraction. Download uses `episodeFile.sourcePath` basename and `WebhookManager.process` requires exactly one model path. Already observed live 9 times on 5.0.0.2701. A capture sink is needed to get the bodies (§Live capture L3). |
| SON5-04 | Sanitized fixtures plus manifest; CI exercises them without NAS | Fixture dir under `src/python/tests/fixtures/sonarr5/` (bind-mounted read-only into the CI test container). Manifest plus a generic-pattern sanitization guard test (§Sanitization). |
| SON5-05 | Conditional 1.7.7, deployed by tag; otherwise close "verified; no release needed" | Release runbook from 119.1-03/04/05 (§Release path). Decision gate task with owner checkpoint. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test Connection (`system/status`) | API / Backend (`web/handler/config.py`) | Browser (settings page button calls `/server/config/sonarr/test-connection`, uses **saved** config) | Server makes the outbound call after the SSRF check |
| Completion evidence (`queue/details`) | Backend controller (`controller/arr_queue.py` worker thread → `controller/completion_gate.py`) | Model stream (`hold_reason` → "Waiting" badge) | Gate decides from queue snapshots on the controller thread |
| Import webhook | API / Backend (`web/handler/webhook.py` → `controller/webhook_manager.py`) | Controller (`Controller.__check_webhook_imports`) | Inbound HTTP from Sonarr |
| Fixtures and CI tests | Test tree (`src/python/tests/`) | CI `unittests-python` docker job | No runtime code change expected |
| Live evidence | NAS sandbox (operator plus agent via SSH) | — | Prod is out of scope |

## Standard Stack

No new dependencies. Everything uses what's already in `src/python/pyproject.toml`.

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | ^9.0.3 (+ pytest-timeout, 60 s) | Test runner. Existing tests are `unittest.TestCase` style and run under pytest. |
| ruff | 0.15.22 in CI (local 0.15.9) | Separate CI lint gate: `ruff check src/python/` |
| requests | existing | Mocked (`@patch("controller.arr_queue.requests")`, `@patch('web.handler.config.requests')`) or served by a local `ThreadingHTTPServer` |
| webtest via `BaseTestWebApp` | existing | Integration webhook route tests (`tests/integration/test_web/test_web_app.py`) |
| Python stdlib `json`, `pathlib`, `re`, `http.server` | — | Fixture loading, sanitization guard, local fake Sonarr |

## Package Legitimacy Audit

Not applicable. This phase installs no external packages. Live capture uses only tools already on the NAS (`curl`, `python3`, `sed`) and, optionally, a disposable `python:3-alpine` container for the webhook sink (an official Docker Hub image, not a package-registry install). If the planner prefers not to pull an image, the sink can run as `python3 -m`-style code inside the existing `seedsyncarr-test` image via `docker run --rm --entrypoint python3 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0...` (already present locally).

## Verified Sonarr 5 API / Payload Facts

All verified against the Sonarr source at tag `v5.0.0.2701` (= `develop` 7ccafd3, 2026-10-19), diffed with `v4.0.20.3014` (latest stable, 2026-09-16), and confirmed live on the sandbox where noted.

| Item | SeedSyncarr reads | Sonarr 5.0.0.2701 (v3 API) | Changed vs v4? |
|------|-------------------|---------------------------|----------------|
| `GET /api/v3/system/status` | `version` | `"5.0.0.2701"` (live). Keys include `appName`, `branch: "develop"`, `runtimeVersion: "10.0.13"`, `startupPath`, `appData`, `osName`, `instanceName`, `startTime`, `buildTime`, `urlBase`, `packageAuthor` and more | No |
| `GET /api/v3/queue/details` | list; per record `outputPath`, `downloadId`, `status`, `sizeleft` (fallback `sizeLeft`) | Same `QueueResource`. `Sizeleft`/`Timeleft` still emitted, marked `[Obsolete]`. The camelCase serializer emits **`sizeleft`** and **`timeleft`**; the new `SizeLeft`/`TimeLeft` are commented out ("collides ... case-insensitive") | Controller now uses `IObsoleteQueueService`, which keeps the **one record per episode** shape with the same `downloadId`, `OutputPath = DownloadItem.OutputPath`, `SizeLeft = RemainingSize`, `Status = TryParse(DownloadItem.Status)` |
| `QueueStatus` values | `status.lower() == "completed"` | `unknown, queued, paused, downloading, completed, failed, warning, delay, downloadClientUnavailable, fallback` | No |
| `queue/details` params | none sent | `seriesId`, `episodeIds`, `includeSeries`, `includeEpisode` (no `includeUnknownSeriesItems`); returns queue plus pending releases (pending have no `outputPath` and never match) | No |
| `/api/v5/system/status` | not used | 200 live (v5 API exists; out of scope, 999.5) | n/a |
| Webhook `eventType` | `"Test"`, `"Download"` | `WebhookEventType` serialized with `DefaultNamingStrategy`, so values are PascalCase `Test`, `Download`, `Grab`, `Rename`, ... | No |
| Webhook Download body | `episodeFile.sourcePath` | `WebhookImportPayload`: `series`, `episodes`, `episodeFile` (`id`, `relativePath`, `path`, `quality`, `qualityVersion`, `releaseGroup`, `sceneName`, `size`, `dateAdded`, `languages`, `mediaInfo`, **`sourcePath`**, `recycleBinPath`), `isUpgrade`, `downloadClient`, `downloadClientType`, `downloadId`, `deletedFiles`, `customFormatInfo`, `release`, plus base `instanceName`, `applicationUrl` | Only `release` gains `indexerFlags` in its constructor (not read) |
| "On Import Complete" event | — | **Also `eventType: "Download"`**, but body is `WebhookImportCompletePayload` with `episodeFiles` (list) plus top-level `sourcePath`/`destinationPath`, **no `episodeFile`** | Exists in v4 too. SeedSyncarr treats it as "no source file path; NOT marking", which is safe. Sandbox has `onImportComplete: false` |
| Test body | `eventType` only | `eventType: "Test"`, series `"Test Title"`, path `"C:\\testpath"`, one episode; no `episodeFile` | No |
| Webhook auth | optional HMAC `X-Webhook-Signature` | Sonarr supports static custom headers and basic auth only, **no HMAC** | No. Sandbox `webhook_secret` empty, `webhook_require_secret` False/unset → accepted |

Live sandbox webhook config [VERIFIED]: notification "Seedsyncarr" → `http://seedsyncarr-test:8800/server/webhook/sonarr`, `onDownload: true`, `onUpgrade: true`, `onImportComplete: false`, no headers.

## Architecture Patterns

### System Architecture Diagram

```
                 (operator: grab episode in sonarr-v5 UI / API)
                                   │
 sonarr-v5 ──add torrent──▶ Deluge on seedbox (label tv-v5test)
   │  ▲                           downloadDirectory ~/v5test-incomplete ──move on complete──▶ ~/v5test
   │  │ GET /api/v3/queue/details (every ~30 s, worker thread)            │
   │  └──────────────── ArrQueueClient ◀──┐                               │ remote scan (lftp/scanfs)
   │                                       │                               ▼
   │                         CompletionGate.evaluate(candidates = remote roots in ~/v5test)
   │                           ├─ matching record(s), same downloadId, all completed & sizeleft 0 → PROVEN → AutoQueue transfers
   │                           └─ else HOLD (still_downloading / no_queue_entry / ambiguous_match / sonarr_unavailable)
   │                                       │ hold_reason → model stream → "Waiting" badge
   │                                       ▼
   │                 lftp → /volume1/data/v5test/torrents (= /data/torrents in sonarr-v5 via remote path mapping)
   │                                       │
   ├── Completed Download Handling imports from /data/torrents ◀────────┘
   │
   └──POST /server/webhook/sonarr {eventType: Download, episodeFile.sourcePath}──▶ WebhookHandler
                                             ├─ Test → 200 "Test OK", nothing enqueued
                                             └─ Download → basename(sourcePath) → WebhookManager.process → exactly one model path → imported mark (auto-delete arm)

 Browser Settings "Test Connection" ──▶ /server/config/sonarr/test-connection ──_validate_url (blocks private IPs)──▶ GET /api/v3/system/status → {success, version}
```

### Recommended fixture/test layout

```
src/python/tests/fixtures/sonarr5/
├── manifest.json                    # one entry per fixture: file, endpoint/event, sonarr_version, captured_at (date), scenario, sanitization notes
├── system_status.json               # raw GET /api/v3/system/status body (sanitized)
├── queue_details_incomplete.json    # raw queue/details list while tracked download X is downloading
├── queue_details_complete.json      # raw queue/details list for the SAME download X when completed (before import)
├── webhook_test.json                # raw Test event body
└── webhook_download.json            # raw Download (import) body for download X's episode file
src/python/tests/unittests/test_sonarr5/   (or add to existing test files; see below)
├── __init__.py
├── fixtures.py                      # load_fixture(name) -> bytes/obj via Path(__file__).resolve().parents[2] / "fixtures" / "sonarr5"
├── test_sonarr5_fixture_hygiene.py  # manifest completeness + sanitization guard (SON5-04)
├── test_sonarr5_system_status.py    # SON5-01 via ConfigHandler with mocked requests/socket
├── test_sonarr5_queue.py            # SON5-02 replay: real ArrQueueClient (+ local HTTP server or mocked requests) → CompletionGate
└── test_sonarr5_webhook.py          # SON5-03 via BaseTestWebApp/WebhookHandler + real WebhookManager.process
```

A new `tests/unittests/test_sonarr5/` package keeps the Sonarr 5 evidence in one place. Integration-style webhook route tests may instead go in `tests/integration/test_web/test_handler/` next to `test_webhook.py` to reuse `BaseTestWebApp`. **Fixture bytes are fed raw** (not re-serialized) so the exact Sonarr bytes reach the parser. The CI container bind-mounts `src/python` read-only at `/src` (`src/docker/test/python/compose.yml`), so fixtures are visible and tests must never write next to them. The wheel excludes `tests/` (`scripts/verify-python-package.py` `FORBIDDEN_WHEEL_TOP_LEVEL`), so no packaging impact [VERIFIED].

### Pattern 1: Queue replay through the real client and gate
Mirror `tests/unittests/test_controller/test_arr_queue.py` (`_response(200, _json_chunks(payload))`, `@patch("controller.arr_queue.requests")`, `settle(client, code)`) and `test_completion_gate.py` (`FakeClock`, the "obsession replay" tests at L181-205). For the strongest proof, build a `CompletionGate(context, ArrQueueClient(context, clock), clock)` where the mocked `requests.get` returns the **incomplete fixture bytes**, then the **complete fixture bytes**. Assert:
1. Root R (= basename of fixture `outputPath`): `still_downloading` hold (non-provisional, in `gate.holds`) after the incomplete snapshot.
2. Proven after the complete snapshot (advance `FakeClock` past `REFRESH_INTERVAL_SECS`).
3. Negatives with the **same captured records**: (a) a candidate root with no matching basename gives `no_queue_entry`; (b) a fetch returning HTTP 500, a connection error or invalid JSON gives `sonarr_unavailable` and never proves, including when a proof was cached earlier and the snapshot became unavailable (`test_cached_proof_not_used_while_any_enabled_arr_unavailable` pattern); (c) "unrelated completed download": the complete fixture record for download X plus a held root Y whose name differs stays held (`no_queue_entry`); (d) a mixed snapshot where X's record is incomplete and an unrelated record Z is complete keeps X `still_downloading`.
4. If the captured download is a season pack, all per-episode records share `downloadId`, and one record forced to `downloading` must hold (existing `test_sonarr_per_episode_one_downloading_still_downloading` precedent).

Also assert the client normalizes the fixture to the expected `QueueRecord(basename, download_id, "completed", 0, True, None)`, which proves `sizeleft` (lowercase) is what Sonarr 5 sends.

### Pattern 2: Test Connection with the captured status
Mirror `test_config_handler.py::test_sonarr_success_returns_version` (`@patch('web.handler.config.socket')` returning a public IP like `8.8.8.8`, `@patch('web.handler.config.requests')`, `mock_response.json.return_value = <fixture obj>`). Assert `{"success": true, "version": "5.0.0.2701"}`. Add a companion test that documents the known limitation: a docker-network URL resolving to `172.19.x` returns the private-IP error. This records the current behavior and is not a fix.

### Pattern 3: Webhook fixtures end to end
- Unit: `TestWebhookHandlerRoutes` style with `@patch('web.handler.webhook.request')`, setting `mock_request.json`/`content_length` from the fixture.
- Integration (preferred): `BaseTestWebApp.test_app.post("/server/webhook/sonarr", params=<fixture bytes>, content_type="application/json")`. Test: 200 `Test OK`, `enqueue_import` not called. Download: `enqueue_import` called once with `("Sonarr", basename(episodeFile.sourcePath), provenance="eventType=Download, episodeFile.sourcePath")`.
- "Marks exactly the correct file": run a **real** `WebhookManager(context).enqueue_import(...)` then `.process(name_to_paths)` with `name_to_paths` holding the fixture's root plus child file and one or more decoy roots/children (sibling episode of the same series, similarly named release). Assert the return is exactly `[(root, child_basename)]`.
- HMAC variant: set `webhook_secret`, sign the fixture bytes with `hmac.new(secret, body, sha256).hexdigest()`. This shows the raw Sonarr 5 body verifies byte-for-byte, and that an unsigned body returns 401 (existing behavior retained).

### Anti-Patterns to Avoid
- **Re-serializing fixtures before feeding them** (`json.dumps(json.load(f))`) hides byte-level quirks. Load bytes once, feed raw.
- **Hand-editing real fixtures beyond the sanitization map.** Every change must be a recorded placeholder substitution listed in `manifest.json`.
- **Asserting on Sonarr fields SeedSyncarr does not read.** That makes tests brittle against future Sonarr changes. Assert SeedSyncarr outcomes only.
- **Changing `sonarr_url` on `seedsyncarr-test` in the middle of a hold capture.** A config identity change triggers `_reset_integration_state()` (abandons fetches, clears proofs and fences), which corrupts the evidence sequence.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fake Sonarr for queue tests | New mock framework | Existing `_response`/`_json_chunks`/`settle` helpers, or `ThreadingHTTPServer` like `start_trickle_server` in `test_arr_queue.py` | Already handles worker-thread settle and teardown |
| Gate test harness | New fake gate client | `FakeArrClient`/`FakeClock`/`GateTestBase` in `test_completion_gate.py`, or the real client (Pattern 1) | Proven non-blocking semantics |
| Web route harness | Bottle app setup | `tests/integration/test_web/test_web_app.py::BaseTestWebApp` | Already wires `WebhookHandler` with a mock manager |
| Secret-free value extraction on NAS | Ad-hoc grep that prints values | 119.1 count-only pattern (`grep -cFf <0600 values file>`, temp dir `umask 077`, `rm -rf` after) | Never displays secrets |
| HMAC computation | — | stdlib `hmac`/`hashlib` (existing `_compute_hmac` in `test_webhook_handler.py`) | Matches the handler exactly |

## Live Capture Procedure (recommended for the planner)

Agent-runnable steps are marked **[agent]**. Steps needing the owner or operator are marked **[owner]**. All docker calls use `sudo /usr/local/bin/docker`. Read the Sonarr key with `K=$(sed -n 's:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p' /volume1/docker/v5test/sonarr/config.xml)` and **never** use `/volume1/docker/sonarr/config.xml` (prod). Sonarr base inside the NAS: `http://localhost:8990/api/v3`. Write raw captures to a `umask 077` dir on the NAS, e.g. `/volume1/docker/v5test/results/son5-capture-<ts>/`. The existing `results/` dir already holds the owner's rig `verify-*.txt` fingerprints. **Raw captures contain personal paths and hostnames and must never be committed raw.**

- **L0 Rig fingerprint [agent]:** record `system/status` version (expect 5.0.0.2701), the `sonarr-v5` image digest, and the `seedsyncarr-test` image (`:1.7.6@sha256:da6196e0…`). Repeat at the end. `sonarr-v5` runs `linuxserver/sonarr:develop` with `wud.watch=true`, so it can be auto-updated mid-phase (Pitfall 4). The owner's rig script output (`results/verify-*.txt`, isolation checks) can be re-run by the owner, or referenced as the isolation baseline (last run 2026-10-20 05:13, 0 failures).
- **L1 SON5-01 Test Connection:**
  1. [agent] Show the failure with the current URL: `curl -s http://localhost:8801/server/config/sonarr/test-connection` returns the private-IP error. Record it as the known LAN limitation. `api_token` is empty on the sandbox, so no auth is needed. Rate limit is 5/60 s.
  2. [agent, after owner OK] Temporarily set `sonarr.sonarr_url` to `http://<NAS tailscale0 IPv4>:8990` via `POST /server/config/set` (`{"section":"sonarr","key":"sonarr_url","value":...}`), call test-connection, and expect `{"success": true, "version": "5.0.0.2701"}`. Optionally the owner presses the button in the UI (port 8801) for a screenshot. Restore `http://sonarr-v5:8989` right away. Do this **before or after** L2, never during it. Keep the Tailscale IP out of committed evidence (write `<nas-tailscale-ip>`).
  3. [agent] Capture the raw `system/status` body for the fixture.
- **L2 SON5-02 hold → release on one tracked download:**
  1. [owner] Make the download visible to SeedSyncarr while incomplete. Today Sonarr's Deluge client has `downloadDirectory=~/v5test-incomplete` and `completedDirectory=~/v5test`, and `seedsyncarr-test` scans `~/v5test`. The root only appears once Deluge moves it at completion, so the "Waiting while incomplete" window is sub-second (observed: hold set and cleared within 0.6 s on 2026-10-20). Recommended: temporarily set the sonarr-v5 Deluge client `downloadDirectory` to the completed directory (`~/v5test`) for one capture download, then restore. The owner's isolation check accepts either directory. Check that the Deluge label `tv-v5test` move-completed then becomes a no-op. A Sonarr-side API edit of `downloadclient/{id}` is possible, but the PUT body needs the password field, so the owner may prefer to do it in the UI.
  2. [owner] Pick and grab one real episode. `wanted/missing` is 0, so the owner must choose content (add a series or season, or a re-grab). Indexers include private trackers (ratio/consent), so this is an owner decision. A slow or large torrent widens the window.
  3. [agent] While downloading, poll `queue/details` every ~10 s into timestamped files until a snapshot shows the target `downloadId` with `status` in {downloading, queued, paused} and `sizeleft>0`, and the same root visible in `seedsyncarr-test`. Capture at the same time: (a) `seedsyncarr-test` log line `Completion hold for '<root>': Still downloading` from `/volume1/docker/v5test/seedsyncarr/log/seedsyncarr.log` (host clock +1h); (b) the model stream showing `hold_reason` for the root (`curl -sN --max-time 5 http://localhost:8801/server/stream`). The UI "Waiting" badge comes from `hold_reason`; an owner screenshot is optional.
  4. [agent] Keep polling until the same `downloadId` shows `status:"completed"`, `sizeleft:0` (trackedDownloadState usually `importPending`). Capture that snapshot plus `Completion hold cleared for '<root>'` and the transfer start. The completed state lasts until SeedSyncarr has copied the file and Sonarr imports it, so the window is wide.
  5. Negatives live (optional; CI is authoritative): **missing queue entry**: place a probe file in `~/v5test` (the Phase 119 UAT used a 4-byte remote probe) and observe `No matching queue entry` hold. **API error**: not done live (would mean breaking the sandbox key or URL). **Unrelated completed download**: covered by the snapshot itself if other items are present, otherwise CI only.
  6. [owner] Restore the Deluge `downloadDirectory`.
- **L3 SON5-03 webhooks:**
  1. [agent] Bodies are not logged by SeedSyncarr (it logs only basename and provenance), so add a **capture sink**: a disposable container (`--label wud.watch=false`, network `docker_default`, name e.g. `son5-webhook-sink`, no published port) running a ~15-line Python HTTP server that writes each POST body to a 0600 file and returns 200. Add a **second** sonarr-v5 Webhook connection ("son5-capture", `onDownload`+`onUpgrade`, URL `http://son5-webhook-sink:8080/`) via `POST /api/v3/notification`. Sonarr then sends the real import to both seedsyncarr-test and the sink, and the existing "Seedsyncarr" connection stays untouched.
  2. [agent] Test event to SeedSyncarr: `POST /api/v3/notification/test` with the existing "Seedsyncarr" notification resource (GET `notification/{id}` first). Expect seedsyncarr-test log `Sonarr webhook test event received` and web_access `POST /server/webhook/sonarr ... 200 ... "Sonarr/5.0.0.2701"`, with no `import enqueued` line. Test the "son5-capture" connection the same way to get the Test **body**.
  3. The real import from L2 fires both webhooks. Evidence: sink body (fixture), seedsyncarr-test `Sonarr webhook import enqueued: '<file>'` then `Sonarr import detected ... matched SeedSyncarr file '<root>'` then `Recorded webhook import: '<root>' (child: '<file>')`, and **no** import line for any other root in that window. Note the log already contains a not-found example (`...s03e07... not found in SeedSyncarr model`) from 2026-10-20 13:18; evidence must be scoped to the capture window.
  4. [agent] Teardown: delete the "son5-capture" notification, remove the sink container, `rm -rf` the raw-capture dir once the sanitized fixtures are committed. The owner may prefer to keep the dir until phase close.
- **L4 Sanitize → commit [agent]:** run the sanitizer (below), run the local exact-secret count check (must be 0), copy into `src/python/tests/fixtures/sonarr5/`, fill `manifest.json`, run the tests.

## Sanitization Approach

Values present in real captures that must be replaced [VERIFIED by field inspection plus live config]:
- `queue/details`: `outputPath` (`/home/<seedbox-user>/v5test[-incomplete]/<release>`), `downloadClient` ("Deluge" is fine to keep), `indexer` (private-tracker name, e.g. "... (Prowlarr)"), `statusMessages` (may contain paths), `downloadId` (torrent infohash; replace consistently).
- `system/status`: `instanceName`, `startupPath`, `appData`, `osName`/`osVersion`, `packageAuthor`, `startTime`, `buildTime`, `urlBase`. **Keep `version`, `appName`, `branch`.**
- Webhooks: `instanceName`, `applicationUrl`, `series.path` (`/data/media/tv/...`), `series.images[].url`/`remoteUrl`, `episodeFile.path`, `episodeFile.sourcePath` (`/data/torrents/...`), `deletedFiles[].path`/`recycleBinPath`, `release.indexer`, `downloadClient`, `downloadId`, `series.tvdbId/imdbId/tmdbId` (public IDs, fine to keep but may be neutralized).

Recommended mechanics:
1. **Sanitizer script** (committed, e.g. `.planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py`, following the `119.1-extract_secrets.py` / `118-05-gen_fixtures.py` precedent). Inputs: raw file plus a **local, uncommitted** mapping (JSON) of sensitive substring → placeholder. Placeholders: `/home/user/v5test`, `/data/torrents`, `seedbox.example.invalid`, `http://sonarr.example.invalid:8989`, `Indexer (Prowlarr)`, `DOWNLOADID0000...` (40 hex, consistent across all files for one download). It works on the raw bytes with `str.replace` for path prefixes, then re-dumps with `json.dumps(obj, indent=2, ensure_ascii=False)`. Doing that once at sanitize time is fine; tests then read the committed bytes raw. **Path basenames (release and file names) must be preserved exactly**, because matching depends on them.
2. **Local exact-secret check (not committed):** at L4, extract the real API keys (sandbox and prod Sonarr, from the respective config.xml), seedbox username/host, NAS hostnames/IPs and Tailscale IP into a 0600 values file inside a `umask 077` temp dir. Then `grep -cFf values <fixtures>` must print 0 (rc 1). Delete the temp dir. This mirrors the 119.1 count-only technique and never prints values.
3. **CI guard test (committed, generic patterns, no personal strings in the repo):** `test_sonarr5_fixture_hygiene.py` scans every file in `fixtures/sonarr5/` and fails on:
   - 32-hex tokens `\b[0-9a-f]{32}\b` (Sonarr/Radarr API key shape), case-insensitive;
   - IPv4 literals not in an allowlist (`127.0.0.1`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), checked with `ipaddress`;
   - `/home/` followed by anything other than `user/`; `/volume1/`; `/Users/`;
   - hostnames with real TLDs: any `scheme://host` or bare FQDN whose TLD is not `.invalid`, `.example`, `.test`, `localhost`, or `example.com/org/net`. Allowlist `thetvdb`/`artworks` remote image URLs only if kept (simpler: sanitize them to `https://images.example.invalid/...`);
   - `@` email-like tokens; `X-Api-Key`/`apikey=`.
   Plus manifest checks: every `*.json` except `manifest.json` has exactly one manifest entry with `sonarr_version == "5.0.0.2701"`, a non-empty `scenario`, `captured_at`, `endpoint_or_event`, `sanitized: true`. Every manifest entry's file exists. The two queue fixtures share the target `downloadId`, and the incomplete one has the target record not completed while the complete one has it completed with `sizeleft == 0` (proves "same download, both states").
   Write the guard **RED-first**: commit it with a deliberately dirty sample to show it fails, or include unit tests of the scanner on inline strings, then GREEN against the real fixtures.

## Common Pitfalls

### Pitfall 1: Test Connection fails for a reason unrelated to Sonarr 5
**What goes wrong:** SON5-01 "fails" on the sandbox because `_validate_url` rejects `sonarr-v5` → `172.19.0.6`.
**Why:** SSRF guard blocks private ranges (Reliability item 5, known and deferred).
**How to avoid:** Run the live check with the Tailscale URL (verified to pass validation and reach Sonarr), record the docker-name failure as a pre-existing limitation, and don't count it as a Sonarr 5 failure under SON5-05. **The owner must explicitly agree with that classification**, since the requirement text says "user can press Test Connection ... and see success". Alternative: the owner promotes a minimal LAN fix into 1.7.7. Not recommended, because it conflicts with the Reliability ordering and widens scope.
**Warning sign:** error text "URL resolves to a private/reserved IP address".

### Pitfall 2: The "incomplete and visible" window is transient on the sandbox
**What goes wrong:** Deluge downloads into `~/v5test-incomplete` (not scanned) and moves to `~/v5test` on completion, so there is no sustained "Waiting while downloading" state to capture.
**How to avoid:** Owner temporarily points the download directory at the scanned dir (L2.1), or uses a slow torrent with the same setting.
**Warning sign:** hold set and cleared in under 1 s in the log (already seen 2026-10-20 13:05:21).

### Pitfall 3: Webhook sent to prod SeedSyncarr
`docker_default` is shared with prod. The alias `seedsyncarr` (prod) resolves on the same network. Any new or edited sonarr-v5 connection must target `seedsyncarr-test` or the sink, never `seedsyncarr`. Re-verify the notification URLs after setup and before teardown.

### Pitfall 4: Sonarr 5 version drift during the phase
`sonarr-v5` is `linuxserver/sonarr:develop` with `wud.watch=true` and `wud.trigger.include=dockercompose.v5test`, and develop moves daily (2701 was tagged 2026-10-19). Record `system/status.version` and the image digest at every capture. If it changes, either pin `sonarr-v5` to the 2701 digest with owner approval, or record the actual version in the manifest and requirement evidence. Don't silently claim 2701.

### Pitfall 5: Raw captures leak personal data
`outputPath` holds the seedbox username path, `indexer` names private trackers, and `applicationUrl`/`instanceName` can identify the NAS. Never `git add` raw files. The guard test plus the local exact-secret count are both required. The `seedsyncarr-test` container log previously held the prod seedbox password (recreated on 1.7.6 with 0 matches). Don't copy `docker logs` output into evidence wholesale; quote specific lines only.

### Pitfall 6: Config change resets gate state mid-capture
Any change to `sonarr_url`/`sonarr_api_key`/`enabled` on `seedsyncarr-test` triggers `CompletionGate._reset_integration_state()`. Sequence L1 (URL swap) fully before or after L2.

### Pitfall 7: Import Complete payload looks like a non-import
If someone enables `onImportComplete` on a connection, Sonarr sends `eventType: "Download"` without `episodeFile`. SeedSyncarr logs a warning and does not mark it. That is safe, not a bug. Keep `onImportComplete` off on the capture connection, or capture it as an extra negative fixture (optional).

### Pitfall 8: Docs describe removed fallbacks
`src/python/docs/arr-setup.md` L83-93 still lists `release.releaseTitle`/`series.title` fallbacks that were removed (only `episodeFile.sourcePath` is trusted now). Out of scope for a "no release" close, but worth recording as a follow-up, or folding into 1.7.7 docs if a release happens anyway.

### Pitfall 9: CI lint and suite gates
CI runs `ruff check src/python/` (ruff 0.15.22) as its own job. Run whole-tree ruff locally. Python tests in CI run in the docker test image; local `poetry run pytest` is the quick loop, and CI `unittests-python` is the authority. The fixture dir must not need write access.

## Code Examples

### Fixture loader
```python
# tests/unittests/test_sonarr5/fixtures.py  (pattern; stdlib only)
import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sonarr5"

def fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()

def fixture_json(name: str):
    return json.loads(fixture_bytes(name))
```

### Feeding raw queue bytes to the real client (existing helper style)
```python
# Source: tests/unittests/test_controller/test_arr_queue.py (_response, settle)
raw = fixture_bytes("queue_details_incomplete.json")
resp = _response(200, [raw[i:i + 4096] for i in range(0, len(raw), 4096)])
mock_requests.get.return_value = resp
```

### Webhook body through the web layer
```python
# Source: tests/integration/test_web/test_handler/test_webhook.py (BaseTestWebApp)
resp = self.test_app.post("/server/webhook/sonarr", params=fixture_bytes("webhook_test.json"),
                          content_type="application/json")
self.assertEqual(200, resp.status_int)
self._webhook_manager_mock.enqueue_import.assert_not_called()
```

### NAS key handling (never echo)
```bash
ssh nas 'umask 077; K=$(sed -n "s:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p" /volume1/docker/v5test/sonarr/config.xml);
  curl -s -H "X-Api-Key: $K" http://localhost:8990/api/v3/queue/details > "$D/queue-$(date +%s).json"'
```

## State of the Art

| Old | Current | When | Impact |
|-----|---------|------|--------|
| Sonarr v4 `queue/details` on `IQueueService` | Sonarr 5 keeps `/api/v3/queue/details` on `IObsoleteQueueService` (same per-episode shape); the new per-download queue model lives in `/api/v5` | 5.0 develop | No impact on v3 consumers; v5 migration is 999.5 |
| `sizeleft`/`timeleft` | Still emitted, `[Obsolete]`, "will be replaced by SizeLeft/TimeLeft" | v4 → v5 | SeedSyncarr already falls back to `sizeLeft`. If v3 ever renames, the existing fallback covers `sizeLeft` |
| v3 API | Deprecated in Sonarr 5, still served (verified 200) | 5.0 | Watch item for 999.5 |

## Runtime State Inventory

Not a rename or refactor phase, but live sandbox state changes do happen during capture and must be reversed:

| Category | Items | Action |
|----------|-------|--------|
| Stored data | sonarr-v5 DB gains a series/episode, history and a new notification row; seedsyncarr-test persist gains an imported record | Leave the import (evidence). Delete the "son5-capture" notification at teardown |
| Live service config | sonarr-v5 Deluge `downloadDirectory` (temporary), `seedsyncarr-test` `sonarr_url` (temporary Tailscale URL) | Restore both, and verify with GET plus the owner's isolation script |
| OS-registered state | Disposable sink container | `docker rm -f` at teardown; label `wud.watch=false` |
| Secrets/env vars | None changed | — |
| Build artifacts | None unless 1.7.7 ships | — |

## Release Path (SON5-05, only if a Sonarr-5-caused failure is found)

Established runbook: 119.1-03/04/05 (`.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/`), 118-04/05.
1. Fix RED-first (regression test fails on 1.7.6 behavior), then GREEN. Full suite plus whole-tree ruff.
2. Version sources 1.7.6 → 1.7.7: `package.json` L2; `package-lock.json` L3 and L8 (root plus `packages[""]`, not checked by the verifier, bump by hand); `src/angular/package.json` L3; `src/angular/package-lock.json` L3 and L9; `src/python/pyproject.toml` both `version =` lines (`[project]`, `[tool.poetry]`). `CHANGELOG.md` gets `## [1.7.7] - <date>` above `## [1.7.6]`. `release-notes.md` is rewritten and keeps the exact line `**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md`. Gate: `node scripts/verify-release-metadata.mjs 1.7.7`.
3. Dependabot review (user rule) before bump/tag. Currently 0 open alerts; PRs #128/#125/#117 are dev/test-only and deferred per 999.4.
4. Owner approval checkpoint, then release PR CI (incl. CodeQL) green, merge, annotated tag `v1.7.7`, then tag CI publishes GHCR `:1.7.7` plus PyPI. **PyPI versions cannot be re-uploaded.**
5. Capture the digest. NAS deploy: edit the compose pin to `ghcr.io/thejuran/seedsyncarr:1.7.7@sha256:<digest>` (inode-preserving edit, never `:dev`/`:latest`), `sudo /usr/local/bin/docker compose up -d <svc>`, verify RepoDigests and `.Image`, then confirm startup, a successful scan and arr checks.
6. **Open question for the owner:** "deployed to the NAS" here most plausibly means the **sandbox** `seedsyncarr-test` (compose `/volume1/docker/v5test/docker-compose.yml`), since prod is out of scope and prod Sonarr is v4. Whether 1.7.7 also goes to prod is a separate owner decision.

If no fix is needed: no version bump, no tag. Commit the tests, fixtures and an evidence record (e.g. `120-SON5-EVIDENCE.md`), close the milestone "verified; no release needed", and update STATE/ROADMAP per PLANNING-FORMAT.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Setting sonarr-v5's Deluge `downloadDirectory` to `~/v5test` makes the root visible during download, and the label's move-completed becomes a no-op | Live L2.1 / Pitfall 2 | Window stays transient; owner may need to change the Deluge label directly or use a different approach |
| A2 | Sonarr sends the real import to both webhook connections independently | Live L3.1 | Sink misses the body; fallback is to temporarily re-point "Seedsyncarr" through a forwarding sink |
| A3 | `POST /api/v3/notification/test` with the notification resource triggers the same Test payload as the UI Test button | Live L3.2 | Owner presses Test in the UI instead |
| A4 | The owner accepts classifying the private-IP Test Connection failure as pre-existing (not a SON5-05 trigger) | Pitfall 1 | If not, 1.7.7 must include a LAN-allow fix (scope increase) |
| A5 | "Deploy to the NAS" in SON5-05 means the sandbox container | Release Path | Prod deploy would need its own runbook execution and owner go-ahead |
| A6 | Sonarr's completed state persists until SeedSyncarr copies and Sonarr imports (wide window for capturing the complete snapshot) | L2.4 | Agent must poll faster; risk of missing the complete snapshot |

## Open Questions (owner decisions)

1. **Test Connection classification.** Is "works via a non-private URL; docker-name URL blocked by the known LAN guard" acceptable for SON5-01? Recommendation: yes, and keep the LAN fix in Reliability.
2. **Which real episode to grab, and on which indexer** (private-tracker ratio and consent). Owner picks.
3. **Temporary Deluge download-directory change** for the capture: owner does it, or approves an agent API edit.
4. **If sonarr-v5 auto-updates past 2701:** pin it, or record the newer 5.x version?
5. **SON5-05 deploy target** if 1.7.7 is needed: sandbox only, or prod too?
6. **Keep raw captures on the NAS** after commit (for audit), or delete at teardown?

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `ssh nas` | live capture | ✓ | key auth | — |
| `sudo /usr/local/bin/docker` | inspect/exec/sink | ✓ | — | — |
| sonarr-v5 | SON5-01..03 | ✓ Up 27 h | 5.0.0.2701, develop, .NET 10.0.13 | — |
| seedsyncarr-test | SON5-01..03 | ✓ Up 4 days | 1.7.6@sha256:da6196e0 | — |
| curl / python3 on NAS host | capture, key read | ✓ | — | run inside the seedsyncarr-test image |
| NAS Tailscale address reachable from the container | SON5-01 workaround | ✓ (`/ping` 200) | — | none (LAN fix is out of scope) |
| Local poetry + pytest | tests | ✓ | Poetry 2.3.4; 211 related tests pass in 3.7 s | CI docker job |
| ruff | lint gate | ✓ local 0.15.9 (CI pins 0.15.22) | — | `pip install ruff==0.15.22` in a venv to match CI |
| gh CLI | Dependabot review, Sonarr source | ✓ | — | — |

No blocking gaps.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ^9.0.3 + pytest-timeout (60 s), unittest-style classes |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_sonarr5 tests/integration/test_web/test_handler/test_webhook.py tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_web/test_webhook_handler.py tests/unittests/test_web/test_handler/test_config_handler.py -q -p no:cacheprovider` |
| Full suite command | `cd src/python && poetry run pytest tests/unittests tests/integration -q -p no:cacheprovider` (host-only failures in ssh/scanner tests excepted, CI is authority) **and** `ruff check src/python/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SON5-01 | Captured Sonarr 5 status → `{"success": true, "version": "5.0.0.2701"}`; docker-name private URL → documented error | unit | `pytest tests/unittests/test_sonarr5/test_sonarr5_system_status.py -q` | ❌ Wave 0 |
| SON5-01 | Live Test Connection success on the sandbox (Tailscale URL) | manual/live evidence | curl `localhost:8801/server/config/sonarr/test-connection` output in evidence | n/a |
| SON5-02 | Incomplete fixture → `still_downloading` hold; complete fixture (same downloadId) → proven; no-match → `no_queue_entry`; HTTP error/invalid JSON → `sonarr_unavailable` and no proof; unrelated completed record → hold kept; fixture parses to expected `QueueRecord` with `sizeleft` | unit (real client + gate, mocked requests) | `pytest tests/unittests/test_sonarr5/test_sonarr5_queue.py -q` | ❌ Wave 0 |
| SON5-02 | Live hold then release for one downloadId with both queue snapshots | live evidence | log lines + queue snapshots + stream `hold_reason` | n/a |
| SON5-03 | Test fixture → 200 "Test OK", nothing enqueued; Download fixture → one enqueue with `basename(episodeFile.sourcePath)`; real `WebhookManager.process` with decoys → exactly one `(root, file)`; HMAC-signed fixture accepted, unsigned → 401 | unit + integration | `pytest tests/unittests/test_sonarr5/test_sonarr5_webhook.py tests/integration/test_web/test_handler/test_webhook.py -q` | ❌ Wave 0 |
| SON5-03 | Live Test event and real import on the sandbox | live evidence | seedsyncarr-test log lines in capture window | n/a |
| SON5-04 | Manifest complete (version, scenario per fixture); no keys, IPs, hostnames or personal paths (generic patterns); queue fixtures share downloadId with incomplete/complete states | unit (hygiene) | `pytest tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py -q` | ❌ Wave 0 |
| SON5-04 | Exact-secret count 0 | local-only NAS check | count-only grep, recorded in evidence | n/a |
| SON5-05 | Decision recorded; if release: RED→GREEN regression, `verify-release-metadata.mjs 1.7.7`, CI green, NAS digest match | gate/manual | per release runbook | n/a |

### Sampling Rate
- **Per task commit:** quick run command plus `ruff check src/python/`
- **Per wave merge:** full suite plus ruff
- **Phase gate:** full suite green, ruff clean, CI `unittests-python` and `lint-python` green on the PR or branch before `/bm:verify-work`

### Wave 0 Gaps
- [ ] `src/python/tests/fixtures/sonarr5/` with `manifest.json`. Wave 1 uses **placeholder fixtures hand-built from the verified Sonarr 5 schema** so the tests exist before capture, clearly marked `"scenario": "placeholder — replaced by live capture"`. The hygiene test must **fail** while any placeholder remains (e.g., require `source: "live"` for all entries) so the phase cannot close on placeholders.
- [ ] `src/python/tests/unittests/test_sonarr5/__init__.py`, `fixtures.py`
- [ ] The four test modules listed above
- No framework install needed.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (webhook and queue parsing) | Existing: 1 MB body cap, JSON parse guards, `_to_record` type checks, `sanitize_log_value` (CWE-117). Fixtures add regression coverage only |
| V6 Cryptography | yes (HMAC retained) | stdlib `hmac.compare_digest`. Unchanged |
| V7 Logging / V8 Data Protection | yes | No API key, URL or body logging in `arr_queue`. Fixtures and evidence scrubbed (sanitizer + guard + exact-secret count) |
| V12/V13 SSRF | yes | `_validate_url` unchanged. The Tailscale workaround uses an address the guard already allows; do not weaken the guard in this phase |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Secret or PII leaked via committed fixtures | Information disclosure | Placeholder map, generic-pattern CI guard, local exact-value count = 0 |
| Test rig cross-talk to prod (webhook to `seedsyncarr` alias) | Tampering | Verify notification URLs. The owner's isolation script (0 failures baseline) |
| API key echoed in shell transcripts | Information disclosure | Key read into a variable from the sandbox `config.xml` only, never printed; count-only checks |
| Forged import webhook marking a wrong file | Spoofing/Tampering | Existing exact-one-path matching + optional HMAC. Test with decoys |

## Sources

### Primary (HIGH)
- Sonarr source at tag `v5.0.0.2701` (commit 7ccafd3) via `gh api repos/Sonarr/Sonarr/contents/...`: `src/Sonarr.Api.V3/Queue/QueueResource.cs`, `QueueDetailsController.cs`, `src/NzbDrone.Core/Queue/QueueStatus.cs`, `ObsoleteQueueService.cs`, `src/NzbDrone.Core/Notifications/Webhook/WebhookBase.cs`, `WebhookImportPayload.cs`, `WebhookEpisodeFile.cs`, `WebhookEventType.cs`, `WebhookProxy.cs`, `src/Sonarr.Api.V3/System/SystemController.cs`; diffed against tag `v4.0.20.3014`.
- Live sandbox, read-only: `system/status`, `downloadclient`, `notification`, `remotepathmapping`, `queue/details`, `history`, `/api/v5/system/status`, `v5test` compose, seedsyncarr-test settings (non-secret keys only) and logs, in-container DNS/`ipaddress`/`/ping` checks.
- Codebase: `src/python/controller/arr_queue.py`, `completion_gate.py`, `webhook_manager.py`, `web/handler/webhook.py`, `web/handler/config.py`, tests under `src/python/tests/`, `src/docker/test/python/compose.yml`, `.github/workflows/ci.yml`, `scripts/verify-python-package.py`.
- Planning records: ROADMAP (Phase 120, 999.5, Reliability item 5), REQUIREMENTS, STATE, 119.1-03/04/05 plans, 119.1-VALIDATION.

### Secondary / Tertiary
- None relied on. An early WebFetch of a non-existent `v5-develop` branch URL was discarded in favor of the tag-pinned `gh api` source.

## Metadata

**Confidence breakdown:**
- Sonarr 5 API and payload compatibility: HIGH. Source diff at the exact tag plus live observation.
- Architecture and test patterns: HIGH. Read from the codebase; related tests run green (211 passed).
- Live capture mechanics: MEDIUM. A1-A3, A6 are assumptions about Deluge and Sonarr notification behavior.
- Release path: HIGH. Mirrors the executed 119.1 runbook.

**Research date:** 2026-10-20
**Valid until:** ~2026-10-27 for the live-sandbox facts (sonarr-v5 tracks `develop` and can auto-update); 30 days for the code-path findings.
