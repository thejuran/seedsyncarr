# Phase 120 SON5 evidence (Sonarr 5 compatibility: live sandbox + CI on live fixtures)

Fixture commit: `6e0341f` (tree `a24c592b9b90`, branch `main`, `test(120-06): replace Sonarr 5 placeholder
fixtures with sanitized live captures`), pushed to `origin/main`. Recorded 2026-10-20.

Hygiene: this file records names, counts, status words, HTTP codes, versions and test names only. No API key,
password, seedbox username or host, NAS hostname, LAN or Tailscale address, real downloadId or private tracker
URL appears here. The NAS Tailscale address is written as `<nas-tailscale-ip>`, docker-network client addresses
as `<docker-ip>`, seedbox home paths as `~/...`, and image digests are truncated to 12 hex characters. Live
results come from `120-CAPTURE-NOTES.md` (Plan 05) and the Plan 06 executor run; the raw captures they cite were
deleted from the NAS after this evidence was taken (see SON5-04).

Scope: the NAS sandbox only, `seedsyncarr-test` (1.7.6, port 8801) against `sonarr-v5` (port 8990). Production
(`seedsyncarr`, `sonarr`, `radarr`, Deluge client settings) was not changed, and no production configuration
file was read for any purpose in Plans 05 or 06.

## Builds verified

| Check point | `system/status.version` |
|-------------|-------------------------|
| L0 rig fingerprint (attempt 2, 15:18:19 host) | 5.0.0.2701 |
| After L1 Test Connection (15:19:22) | 5.0.0.2701 |
| L3 setup before / after (15:19:53 / 15:19:58; repeated 15:41 and 16:01) | 5.0.0.2701 / 5.0.0.2701 |
| L0 re-baseline for the capture run (15:39, 16:00) | 5.0.0.2701 |
| `V_BEFORE` around the L2 completion capture (16:01:31) | 5.0.0.2701 |
| `V_AFTER` around the L2 completion capture and webhook (16:05:31) | 5.0.0.2701 |
| Plan 06 pre-flight (fresh session) | 5.0.0.2701 |

- `sonarr-v5`: image id `8b59d172e9b4`, configured `linuxserver/sonarr:develop`, RepoDigest
  `linuxserver/sonarr@sha256:096c4c08d947…`, branch `develop`, runtime .NET 10.0.13, package
  `5.0.0.2701-ls199`. Webhook user agent `Sonarr/5.0.0.2701 (alpine 3.24.2)`.
- `seedsyncarr-test`: image id `5b801f8397d6`, `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a…`.
- The build never changed during the run (D-07), so no scenario was rerun for build drift and all five fixtures
  share one build (D-08).

**D-09:** These results apply to Sonarr **5.0.0.2701** (the `develop`-branch build above) only. They
do not imply compatibility with other or future Sonarr 5 builds. A later 5.x build needs its own capture before the same
claim can be made for it.

## SON5-01 — Test Connection

Live (attempt 2, 15:18:19 – 15:19:22 host; attempt 1 at 15:15 produced identical results):

- Container-name URL `http://sonarr-v5:8989`: `success=false`, error `URL resolves to a private/reserved IP
  address`. The docker name resolves to a private bridge address and SeedSyncarr's SSRF guard refuses it before
  contacting Sonarr. **Classification (D-02):** the known LAN/private-address limitation, Reliability milestone
  item 5 (LAN connection tests). It is the same against any Sonarr version and is **not** a Sonarr 5 failure.
- Tailscale URL `http://<nas-tailscale-ip>:8990`: `POST /server/config/set` http=200, then Test Connection
  `success=true version=5.0.0.2701`. Tailscale-address count inside the saved result = 0.
- Restore: `POST /server/config/set` back to `http://sonarr-v5:8989` http=200; read-back `RESTORED sonarr_url ok`.

CI (`tests/unittests/test_sonarr5/test_sonarr5_system_status.py`, `TestSonarr5SystemStatus`, on the live
`system_status.json`):
- `test_sonarr5_status_fixture_returns_success_with_recorded_version`
- `test_fixture_version_matches_manifest`
- `test_docker_network_url_rejected_by_lan_guard_known_limitation` (documents D-02; not a fix)
- `test_cgnat_address_passes_url_validation`
- `test_status_fixture_extra_keys_are_present_and_harmless`

## SON5-02 — Completion hold on Sonarr 5 queue state

Live, one tracked download: `Hacks.S04E01.1080p.HEVC.x265-MeGusta` (single episode, ~359 MB), grabbed through
sonarr-v5 (`GRAB http=200` at 15:44:28 host). MODE A (per-torrent Deluge options on the capture torrent only;
the Deluge client settings were never changed). Restore read-back: `DELUGE per-torrent mode, no client change
(downloadDirectory matches L0: yes)` and, in the Plan 06 pre-flight, `DELUGE_DIR_MATCHES_L0 yes`.

Milestones (app clock = host clock + 1h):

1. **Incomplete, held.** `queue/details` at 15:57:14 host: `status=downloading`, `trackedDownloadState=downloading`,
   `sizeleft=165052416`. Log:
   ```
   2026-10-20 16:55:50,109 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
   ```
   Model stream extract: `root=Hacks.S04E01.1080p.HEVC.x265-MeGusta hold_reason=still_downloading`.
2. **Complete in Sonarr.** `queue/details` at 16:02:22 host, same downloadId (`PAIR_OK 1`): `status=completed`,
   `sizeleft=0`, `trackedDownloadState=importPending`.
3. **Released and queued only after completion.**
   ```
   2026-10-20 17:03:20,525 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta': Still downloading
   2026-10-20 17:03:21,095 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold cleared for 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
   2026-10-20 17:03:21,096 - INFO - seedsyncarr.AutoQueue (MainProcess/ControllerJob) - Auto queueing 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'
   ```

An earlier `Completion hold cleared` at 17:01:49 app clock was the gate's prune path (the root left the stability
sweep when its remote size changed), not a release: no queue or transfer happened before 17:03:21, the root was
re-held on the gate's older snapshot at 17:03:20, and it was released only on the `completed`/`sizeleft=0`
snapshot (`completion_gate.py` prune path; full account in `120-CAPTURE-NOTES.md`). This is version-independent
and is logged as an observability wording item, not a Sonarr 5 failure.

Live negatives were not run (no seedbox shell for a probe file; breaking the key or URL would corrupt the
capture). CI is authoritative for them.

CI (`tests/unittests/test_sonarr5/test_sonarr5_queue.py`, on the live queue fixtures):
- Positive (`TestSonarr5QueueReplay`): `test_sonarr5_queue_fixture_normalizes_with_lowercase_sizeleft`,
  `test_incomplete_fixture_holds_still_downloading`, `test_same_download_complete_fixture_releases`,
  `test_unrelated_root_never_released_by_other_download`
- Negatives (`TestSonarr5QueueNegatives`): `test_http_500_holds_sonarr_unavailable_never_proves`,
  `test_connection_error_holds_sonarr_unavailable`, `test_invalid_json_holds_sonarr_unavailable`,
  `test_cached_proof_not_used_when_snapshot_becomes_unavailable`, `test_mixed_snapshot_keeps_target_held`,
  `test_season_pack_one_record_downloading_holds`, `test_missing_queue_entry_holds`

The live queue held only the tracked download, so the "unrelated completed download" record used by
`test_mixed_snapshot_keeps_target_held` is now derived from the captured record with a different downloadId and
root (test-side adjustment, classification (i); no production code changed).

## SON5-03 — Webhooks

Test events (both connections, no import):
- To `Seedsyncarr` (sandbox connection) at 15:19:53, 15:41:46 and 16:01 host: `POST notification/test` http=200;
  access log
  ```
  2026-10-20 16:19:53,363 - INFO - web_access (MainProcess/worker 29) - <docker-ip> - - [20/Oct/2026:16:19:53 -0400] "POST /server/webhook/sonarr HTTP/1.1" 200 7 "-" "Sonarr/5.0.0.2701 (alpine 3.24.2)"
  ```
  The 7-byte body is `Test OK`. `import enqueued` = 0 and `Recorded webhook import` = 0 in each window.
- To `son5-capture` (the disposable sink) at 15:19:55, 15:41:54 and 16:01 host: http=200, body `eventType=Test`
  (keys `applicationUrl,episodes,eventType,instanceName,series`), sink user agent
  `Sonarr/5.0.0.2701 (alpine 3.24.2)`.

Real import (16:05:21 host): sink caught `eventType=Download`, `isUpgrade=false`, same downloadId, child
`Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv`, user agent `Sonarr/5.0.0.2701 (alpine 3.24.2)`. SeedSyncarr log:
```
2026-10-20 17:05:21,785 - INFO - seedsyncarr.WebhookManager (MainProcess/worker 3) - Sonarr webhook import enqueued: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv' (eventType=Download, episodeFile.sourcePath)
2026-10-20 17:05:22,069 - INFO - seedsyncarr.WebhookManager (MainProcess/ControllerJob) - Sonarr import detected: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv' (matched SeedSyncarr file 'Hacks.S04E01.1080p.HEVC.x265-MeGusta'; eventType=Download, episodeFile.sourcePath)
2026-10-20 17:05:22,069 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Recorded webhook import: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta' (child: 'Hacks.S04E01.1080p.HEVC.x265-MeGusta.mkv')
```
`IMPORT_LINES single=1 total=1 mine=1`.

The handler-level `Sonarr webhook test event received` line was never logged; its module logger is not attached
to the app logger. That is pre-existing and version-independent (deferred-items.md), so Test-event acceptance is
proven from the access log plus zero import lines.

CI (`tests/unittests/test_sonarr5/test_sonarr5_webhook.py`, on the live webhook fixtures):
- `TestSonarr5WebhookWebLayer`: `test_fixture_build_is_sonarr5`, `test_test_event_returns_test_ok_without_enqueue`,
  `test_download_event_enqueues_source_path_basename_once`, `test_signed_raw_download_body_is_accepted`,
  `test_unsigned_download_body_is_rejected`, `test_signature_over_reserialized_json_is_rejected`
- `TestSonarr5WebhookExactFile`: `test_download_marks_exactly_one_file_among_decoys`,
  `test_same_basename_under_two_roots_is_rejected`

## SON5-04 — Sanitized live fixtures in CI

Manifest (`src/python/tests/fixtures/sonarr5/manifest.json`): 5 entries, all `"source": "live"`, all
`"sonarr_version": "5.0.0.2701"`, `captured_at` 2026-10-20, `sanitized: true`, `queue_target_download_id` = the
40-hex placeholder.

| File | Scenario | Build |
|------|----------|-------|
| `system_status.json` | `GET system/status` during the SON5-01 run (Tailscale Test Connection success) | 5.0.0.2701 |
| `queue_details_incomplete.json` | `GET queue/details` while the root downloads (`downloading`, sizeleft>0); seedsyncarr-test holding `still_downloading` | 5.0.0.2701 |
| `queue_details_complete.json` | `GET queue/details`, same download, `completed`, sizeleft 0, `importPending`, before release | 5.0.0.2701 |
| `webhook_test.json` | Sonarr connection Test event (built-in test payload) | 5.0.0.2701 |
| `webhook_download.json` | Download (import) webhook for the same download, single episode file | 5.0.0.2701 |

Sanitization (on the NAS; raw bytes never left it): `120-sanitize_fixtures.py` per file with a 0600 mapping of
14 keys (downloadId upper/lower → placeholder, 9 sandbox indexer names → `Indexer (Prowlarr)` / `Indexer`, the
two Deluge seedbox directories → `/home/user/v5test[-incomplete]`, the artwork host → `images.example.invalid`),
plus key-based neutralisation of identity fields.
```
SANITIZE system_status.json REPLACED n=0 RESIDUAL=0 exit=0
SANITIZE queue_details_incomplete.json REPLACED n=2 RESIDUAL=0 exit=0
SANITIZE queue_details_complete.json REPLACED n=2 RESIDUAL=0 exit=0
SANITIZE webhook_test.json REPLACED n=0 RESIDUAL=0 exit=0
SANITIZE webhook_download.json REPLACED n=3 RESIDUAL=0 exit=0
BASENAMES_PRESERVED ok queue_details_incomplete.json paths=1
BASENAMES_PRESERVED ok queue_details_complete.json paths=1
BASENAMES_PRESERVED ok webhook_test.json paths=1
BASENAMES_PRESERVED ok webhook_download.json paths=3
STATUS_VERSION 5.0.0.2701 match
CLEAN_OUTPUTPATH_PREFIX ['/data/torrents']
CHECKS ok
```
Sonarr's own remote path mapping already reported `outputPath` as the container-local `/data/torrents/<root>`, so
no seedbox path was present in the captures; the seedbox-directory mapping keys matched nothing (precaution only).

Exact-secret count (119.1 pattern; `umask 077` temp dir removed by trap; sandbox-only sources: sandbox Sonarr
API key from `/volume1/docker/v5test/sonarr/config.xml`, seedbox user and host from
`/volume1/docker/v5test/seedsyncarr/settings.cfg`, the Deluge host from the sandbox Sonarr download client, NAS
hostname, two NAS LAN IPv4 addresses, Tailscale IPv4, the real downloadId upper and lower case, 9 indexer names):
```
VALUES lines=19 expected=19
queue_details_complete.json:0
queue_details_incomplete.json:0
system_status.json:0
webhook_download.json:0
webhook_test.json:0
EXACT_SECRET_COUNT total=0 rc=1
RAW_CONTROL_COUNT total=6 (expected >0)
```
The control count over the raw queue/webhook files shows the values file does find the real values that the
sanitizer removed. No production configuration file was read; a production API key in a fixture would still fail
CI through the generic `hex32` hygiene rule.

Hygiene guard: `test_sonarr5_fixture_hygiene.py` is strict. The `skipIf` gate and `_has_placeholders` helper were
removed; `TestLiveSource::test_all_fixtures_are_live_captures` PASSED in CI.

Local (host, project venv): `tests/unittests/test_sonarr5` 49 passed, 0 skipped, 0 failed (58 subtests).
Full `tests/unittests tests/integration`: 1823 passed, 62 skipped, 21 failed, 43 errors. All failures/errors are
host-only and outside this change: `test_ssh/test_sshcp.py` (11 F), `test_scan/test_scanner_process.py`
(3 F + 3 E), `test_extract/test_extract_process.py` (6 F), `test_system/test_scanner.py` (1 F, latin-1 filename),
and `tests/integration/test_lftp` (40 E, `getgrnam(): name not found: 'testgroup'`, needs the Docker test
environment). The unittest set matches the host baseline previously recorded for pre-phase commit `3618be6` (21 failed + 3 errors; not rerun here). CI is the
authority. `ruff check src/python/`: All checks passed.

CI on `6e0341f`: https://github.com/thejuran/seedsyncarr/actions/runs/39498893798 — conclusion **success**;
`Python unit tests` success (1944 passed, 2 skipped; both skips are unrelated integration tests), `Lint (Python)`
success, E2E amd64/arm64 success. CodeQL run 39498891573: success.

Raw captures: after the push and green CI, all three capture dirs
(`son5-capture-20261020-151245`, `-151815`, `-163945`) were removed from `/volume1/docker/v5test/results/`:
```
RAW_DIR_DELETED
remaining=0
```

## Sandbox restoration

Plan 05 teardown (monitor EXIT trap at 16:05:31 and a fresh-session read-back):
```
RESTORED sonarr_url ok
DELUGE per-torrent mode, no client change (downloadDirectory matches L0: yes)
RESTORED notifications count=1 son5-capture-present=0
NOTIF_URLS_OK
REMOVED sink (absent)
CHECK sonarr_url=http://sonarr-v5:8989
SANDBOX_RESTORED ok
exit=0
```

Plan 06 pre-flight (fresh `ssh nas` session, before any sanitize work):
```
VERSION 5.0.0.2701
NOTIF_COUNT 1 NAMES Seedsyncarr
SINK_CONTAINERS 0
SSY sonarr_url=http://sonarr-v5:8989
DELUGE_DIR_MATCHES_L0 yes
QUEUE_TOTAL 0
```
Baseline matched, so the teardown script was not rerun (no teardown gap). The captured torrent keeps seeding in
Deluge (owner requirement); nothing removed it.

## SON5-05 decision

Rule (D-10): a check is a **Sonarr-5-caused failure** only if (a) the live sandbox result for SON5-01..03 differed
from the expected behavior, AND (b) the CI test on the live fixture shows SeedSyncarr misreading a Sonarr 5 field
or payload (Task 1 classification (ii)), AND (c) the cause is not the pre-existing LAN guard (D-02) and not a
sandbox/rig problem.

| Req | Live sandbox result | CI on live fixture | Classification |
|-----|---------------------|--------------------|----------------|
| SON5-01 | Tailscale URL: `success=true version=5.0.0.2701`. Container-name URL: private-IP rejection | 5/5 pass | **Pass.** Container-name failure is the pre-existing LAN guard (D-02, Reliability item 5), excluded by (c) |
| SON5-02 | Held `still_downloading` while incomplete; released and queued only after the same download showed `completed`, sizeleft 0 | 11/11 pass (4 positive, 7 negative) | **Pass.** The 17:01:49 prune-log wording is version-independent observability, no early transfer |
| SON5-03 | Test events: 200 `Test OK`, 0 imports. Download event: exactly one `Recorded webhook import` for the right file | 8/8 pass | **Pass.** Missing handler log line is pre-existing and version-independent |

Task 1 produced one test failure, classified (i): a placeholder-only assumption (a second, unrelated queue record)
that the single-download live queue does not contain. The test now derives that record from the captured one.
No production code misread any Sonarr 5 field or payload, so there is no classification (ii) failure.

Decision: verified; no release needed (D-12). Builds verified: Sonarr 5.0.0.2701 (`linuxserver/sonarr:develop`,
image `8b59d172e9b4`). No version bump, no tag, no deploy.

Production stays on 1.7.6; it was not touched. No `120-SON5-05-RELEASE-NEEDED.md` is created.

Owner confirmation: pending (Task 3 checkpoint).

## Follow-ups (not fixed here)

- **Reliability item 5, LAN connection tests:** Test Connection rejects a docker-network or LAN Sonarr URL as a
  private address (D-02). Users on the same docker network must use a routable address (here, Tailscale) today.
- **`src/python/docs/arr-setup.md` lines 83-93:** stale fallback text (RESEARCH Pitfall 8); update when the LAN
  item lands.
- **Backlog 999.5:** move the Sonarr integration to API v5 (this phase verified the v3 API that Sonarr 5 still
  serves).
- **Webhook handler logger not attached** (deferred-items.md): `Sonarr webhook test event received` and other
  handler INFO lines never reach the app log.
- **Completion-gate prune message** (deferred-items.md): `Completion hold cleared` is logged both for a proof
  release and for a hold dropped from the candidate set; suggest a distinct "dropped" message.
- **Capture-script trap pattern:** `trap '...' EXIT INT TERM HUP` does not exit on a signal; staged scripts should
  use `trap 'exit 130' INT TERM HUP` plus an EXIT trap (fixed in practice during Plan 05).
