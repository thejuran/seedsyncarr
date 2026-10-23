# Phase 122 SAFE-01 evidence (live acceptance on the PR #134 staging image)

Purpose: completes the extraction/import half of `119-VERIFICATION.md` (the browser half passed
2026-10-18, `119-HUMAN-UAT.md`). Production (`seedsyncarr`, 1.7.6) is read-only/untouched throughout
this phase; all live checks run against the sandbox container `seedsyncarr-test` only.

Clocks: the sandbox/production app-log clock is the NAS host clock + 1 h. Every log excerpt in this
file states both the NAS host-clock time and the app-log time where they differ.

One-PR-per-phase note (owner decision, 2026-10-22, recorded in `122-03-SUMMARY.md` and the
`<orchestrator_amendment>` on `122-04-PLAN.md`): draft PR #134 carries the whole phase and is merged
once, after Plan 09, with owner approval. This supersedes `122-CONTEXT.md` D-01's "merge first"
sequencing. The build under test for every SAFE-01 live check in Plans 04-08 is therefore PR #134's
own CI staging image, identified by `PR_HEAD_SHA` below, not a merge commit.

## Build under test

- **PR:** https://github.com/thejuran/seedsyncarr/pull/134 (draft; state OPEN; not merged)
- **PR_HEAD_SHA:** `28942cc2b65c6c01929d154d8ffa99be4540a9f8`
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/39841124970 (run_number 400), conclusion **success**
- **"Build Docker Image" job:** conclusion **success** (started 2026-10-22T19:38:27Z, completed 2026-10-22T19:43:42Z; `make docker-image --push` pushed the multi-arch staging image `ghcr.io/thejuran/seedsyncarr:400`). `publish-docker-image-dev` did not run (its `if: github.ref == 'refs/heads/main'` gate is false for a `pull_request` event) — expected, not a failure.
- **No later push exists:** `gh run list --workflow=ci.yml --branch gsd/phase-122-safety-acceptance-and-logging-fixes` returns exactly one completed run (databaseId `39841124970`, headSha `28942cc2b65c6c01929d154d8ffa99be4540a9f8`), matching `gh pr view 134`'s current `headRefOid`. The equivalence guard (plan's `<orchestrator_amendment>`) holds: the staging image at tag `400` is still built from `PR_HEAD_SHA`.
- **Digest resolution (two independent methods, cross-checked, identical result):**
  - `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:400` → index `Digest: sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9` (`application/vnd.oci.image.index.v1+json`; `linux/amd64` + `linux/arm64` manifests plus their attestation manifests).
  - Anonymous GHCR registry lookup (no `read:packages` scope needed; `gh api .../packages/...` still 403s, confirmed consistent with `119-REL03-EVIDENCE.md`):
    ```
    TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io" \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
    curl -s -I -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.oci.image.index.v1+json" \
      "https://ghcr.io/v2/thejuran/seedsyncarr/manifests/400" | grep -i docker-content-digest
    # -> docker-content-digest: sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9
    ```
- **DEV_PIN** (variable name kept per the orchestrator amendment, so later plans and the teardown/deploy harness work unchanged):
  ```
  DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9
  ```

## Sandbox deploy

NAS capture dir (0700, not committed): `/volume1/docker/v5test/results/safe01-122-20261022T195544Z`. Holds
`teardown.sh`, `webhook-post.sh` (copies of the committed harness), `deploy.sh` (one-off,
trap-protected deploy driver for this session only), `state.env`, and the before/after
production-fingerprint captures below.

### Original pin (IMAGE_PIN_L0)

Recorded before any change, cross-checked two ways (must match, and did):
```
compose file (seedsyncarr-test image line): ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
docker inspect seedsyncarr-test .Config.Image: ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
```
`IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`

### Deploy (trap-protected: `trap 'exit 130' INT TERM HUP` first, then
`trap '[ "$OK" = 1 ] || bash "$D/teardown.sh" --final' EXIT INT TERM HUP`)

NAS host clock (UTC, `date -u`) around the deploy: pre `2026-10-22T19:56:19Z`, post
`2026-10-22T19:57:18Z` (NAS local zone is -05, so host-local was ~14:56-14:57).

```
$ sudo /usr/local/bin/docker compose -f /volume1/docker/v5test/docker-compose.yml pull seedsyncarr-test
  seedsyncarr-test Pulled
$ sudo /usr/local/bin/docker compose -f /volume1/docker/v5test/docker-compose.yml up -d seedsyncarr-test
  Container seedsyncarr-test  Recreated
  Container seedsyncarr-test  Started
DEPLOY server/status ok
DEPLOY image verified: ghcr.io/thejuran/seedsyncarr@sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9
DEPLOY container_image_id=sha256:a28482fbde5c2e3f0a567512b12e49de2b397d1d48c19b4ea318aa3aa466f559
DEPLOY webhook_secret length=0 confirmed
DEPLOY test_event http=200 body=Test OK
DEPLOY_OK
```

`docker inspect seedsyncarr-test --format '{{.Config.Image}}'` after deploy equals DEV_PIN exactly
(re-confirmed independently via the Task 3 verify command, same result).

### Production unchanged (fingerprint comparison)

```
before: 2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-15T22:15:22.819680413Z
after:  2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-15T22:15:22.819680413Z
```
`diff` of the two capture files: empty (identical container Id, image and StartedAt). The
production container `seedsyncarr` was never named by any write command in this plan's
procedures.

### LOG-01 live (webhook handler logging reaches the app log)

Unsigned (`webhook_secret` length confirmed 0, no `X-Webhook-Signature` header sent)
`{"eventType":"Test"}` posted to `/server/webhook/sonarr` returned HTTP 200, body `Test OK`.
Verbatim sandbox app-log line immediately after (clocks: NAS host UTC `2026-10-22T19:57:18Z`
→ NAS host local -05 `14:57:18` → app-log local-+1h convention `15:57`, matching below):
```
2026-10-22 15:57:15,115 - INFO - seedsyncarr.WebhookHandler (MainProcess/worker 1) - Sonarr webhook test event received
```
Logger field is `seedsyncarr.WebhookHandler` — a true descendant of the `seedsyncarr` app
logger (not the pre-fix `web.handler.webhook` module logger, which never reached any handler).
This is the first time this line has ever been observed in a running build; LOG-01 is confirmed
live on the PR #134 staging image.

### Known issue for Plans 05-08 (not a blocker for this plan)

The seedbox (`nyx.usbx.me`) refused TCP connections on port 22 from the NAS during this plan's
execution (`ssh -v nyx.usbx.me` → `connect to address 46.232.211.130 port 22: Connection refused`,
checked twice a few seconds apart). This plan creates no synthetic material and does not need
seedbox reachability (`122-teardown.sh`'s seedbox cleanup step is only exercised when `SYNTH_ROOTS`
is non-empty, which it is not this session). Plans 05-08 do need the seedbox for D-04's synthetic
files and D-07's multi-part RAR — re-check reachability before those plans create any synthetic
material, since this was a live TCP-level refusal, not an auth failure.

## Plan 05: D-06 import/auto-delete scenarios on SSA122 synthetic roots

Clocks for this plan: NAS host clock read via `date -u` (UTC); the app-log clock is
host-local (UTC-05) + 1h, i.e. **app-log time = UTC time − 4h**, confirmed by matching the
release command's own UTC timestamp against its own log line in both runs below. Both
clocks are stated at each milestone.

Build under test: unchanged from Plan 04 — `seedsyncarr-test` on `DEV_PIN`
(`ghcr.io/thejuran/seedsyncarr@sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9`),
re-confirmed via `docker inspect .Config.Image` immediately before each run below.

Two executions were needed. Run 1 (`SSA122.Alpha.S01` / `SSA122.Decoy.S01`, sibling sizes
8/48/160/200 MiB) fully and cleanly evidenced (e), (a) and (b) — its own `lftp.rate_limit`
setting took effect (log: `rate_limit changed: 0 -> 4194304`) but the real aggregate
transfer throughput still far exceeded the nominal 4 MiB/s cap (all four children finished
within ~17s of release), so no child's webhook landed on it while that specific child was
still incomplete — only while the **root** was still incomplete, which is the (a) early-credit
condition, not the (c) deferral condition. Run 2 (`SSA122.Alpha2.S01`, no decoy — (e) was
already evidenced in run 1 — sibling sizes raised to 300/800/1200 MiB specifically to widen
the incomplete-child window) reliably produced three genuinely-incomplete-at-post-time child
webhooks and surfaced a real defect on the fourth. CHECK_STATUS recorded for the session:
**FAIL** (D-06(c)); SAFE-01 is not marked passed, per D-03.

### D-06(e) Waiting hold and one-shot release — PASS

Run 1, `SSA122.Alpha.S01` (held) and `SSA122.Decoy.S01` (decoy, held throughout).

1. **Both roots held, no queue entry.** UTC 20:20:4x; app-log:
   ```
   2026-10-22 16:20:47,797 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.Alpha.S01': No matching queue entry
   2026-10-22 16:20:47,798 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.Decoy.S01': No matching queue entry
   ```
   Model snapshot (`model-e-held.json`) at this point: both roots present with
   `hold_reason: "no_queue_entry"`, `state` not `downloading`/`queued`, zero local bytes.
2. **One-shot manual release of `SSA122.Alpha.S01` only.** `POST
   /server/command/queue/SSA122.Alpha.S01?release_unverified=true` at UTC
   `2026-10-22T20:20:53Z` → `http=200 body=Queued file 'SSA122.Alpha.S01'`. App-log:
   ```
   2026-10-22 16:20:53,844 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Received command Action.QUEUE for file SSA122.Alpha.S01
   2026-10-22 16:20:53,845 - WARNING - seedsyncarr.Controller.CommandProcessor (MainProcess/ControllerJob) - Manual release of unverified 'SSA122.Alpha.S01' (No matching queue entry); source-completion check bypassed for this transfer only
   2026-10-22 16:20:54,017 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold dropped for 'SSA122.Alpha.S01' (no longer a queue candidate)
   ```
   `SSA122.Decoy.S01` was never named by any release call. No `Completion hold cleared for
   'SSA122.` line occurs anywhere in either run's log (grep count 0 in both
   `log-SSA122.Alpha.S01-run1.txt` and `log-SSA122.Alpha2.S01-run2-fail.txt`) — the only hold
   removal for a synthetic root in either run is the one **dropped** line quoted above, which
   is the correct wording (D-16/D-17): the manual-release path bypasses the proof gate
   entirely, so it is never a proven "cleared" release. The real Sonarr-queue proof-based
   release path (which does log "cleared") is covered by citation to
   `120-SON5-EVIDENCE.md` §SON5-02 and `120-CAPTURE-NOTES.md`, per D-04.
3. **Decoy never transferred.** Across every model snapshot taken through the rest of run 1
   (`model-a-1.json` .. `model-a-4.json`, `model-a-e01ready.json`), `SSA122.Decoy.S01` stays
   at `hold_reason: "no_queue_entry"` with no local bytes. Teardown's synthetic-root cleanup
   confirmed both `SSA122.Alpha.S01` and `SSA122.Decoy.S01` absent afterward
   (`REMOVED synth roots count=2 refused=0`).

**PASS (D-05, D-06(e)).** Cross-reference: the real Sonarr-queue completion gate ("Still
downloading" hold, release only after Sonarr reports completion) is `120-SON5-EVIDENCE.md`
§SON5-02 / `120-CAPTURE-NOTES.md`, per D-04 — not re-captured here.

Unit coverage: `test_completion_gate.py::test_zero_candidates_no_queue_entry` (Waiting hold),
`test_hold_dropped_when_no_longer_candidate` and `test_hold_dropped_when_no_arr_enabled`
("dropped" wording), `test_hold_cleared_when_proven` ("cleared" wording, proof-based only),
`test_hold_start_logged_once_with_sanitized_name_and_label`.

### D-06(a) Early per-episode credit — PASS

Run 1, `SSA122.Alpha.S01` (children E01 8 MiB, E02 48 MiB, E03 160 MiB, E04 200 MiB).

1. **E01 caught DOWNLOADED while siblings transfer.** Model snapshot at UTC `20:21:03`
   (`model-a-e01ready.json`): `e01[state=downloaded local=8388608 remote=8388608]
   e02[state=downloaded local=50331648 remote=50331648]
   e03[state=downloading local=0 remote=167772160]
   e04[state=downloading local=0 remote=209715200]` — the root as a whole is still
   transferring (E03/E04 incomplete). Signed webhook posted for E01 (`webhook-post.sh`,
   HMAC-SHA256, `X-Webhook-Signature`) → `HTTP_CODE=200`.
2. **Credited, root not committed.** App-log:
   ```
   2026-10-22 16:21:04,326 - INFO - seedsyncarr.WebhookManager (MainProcess/ControllerJob) - Sonarr import detected: 'SSA122.Alpha.S01E01.mkv' (matched SeedSyncarr file 'SSA122.Alpha.S01'; eventType=Download, episodeFile.sourcePath)
   2026-10-22 16:21:04,327 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Alpha.S01E01.mkv' in 'SSA122.Alpha.S01' (root still transferring)
   ```
   At this timestamp `SSA122.Alpha.S01` is **not yet** in the persisted `downloaded`/
   `imported` sets (confirmed: no `Committing 'SSA122.Alpha.S01'...` or `Scheduled
   auto-delete...` line precedes it).
3. **Two more early credits before commit**, each for a child that (per the pre-post
   snapshot) had itself already finished while the root overall was still transferring:
   ```
   2026-10-22 16:21:06,354 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Alpha.S01E02.mkv' in 'SSA122.Alpha.S01' (root still transferring)
   2026-10-22 16:21:08,434 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Alpha.S01E03.mkv' in 'SSA122.Alpha.S01' (root still transferring)
   ```
   Code path: `controller.py:893` `__credit_early_child` — writes
   `imported_children[root]` only; never touches `downloaded_file_names` or
   `imported_file_names` and never schedules a delete by itself (verified: no `Scheduled
   auto-delete` line precedes the commit, see D-06(b) below).

**PASS (D-06(a)).** Unit coverage:
`test_import_credit.py::test_child_notices_before_commit_are_credited_not_dropped`,
`test_credit_persists_immediately_via_callback`, `test_credit_alone_never_deletes`
(119-05, Days of Hope regression).

### D-06(c) Deferral and revalidation — **FAIL**

Run 2, `SSA122.Alpha2.S01` only (sibling sizes raised to E01 8 MiB, E02 300 MiB, E03 800 MiB,
E04 1200 MiB, specifically to widen the window in which a child's own webhook lands while
that child is genuinely still incomplete — run 1's smaller/faster siblings never produced
that condition, see the run-1 note above).

1. **Three webhooks posted on genuinely-incomplete children**, confirmed from the model
   snapshot taken immediately before each post:
   - E02 at UTC `20:50:31`: `state=downloading local=0 remote=314572800` (0%)
   - E03 at UTC `20:50:35`: `state=downloading local=133005312 remote=838860800` (~16%)
   - E04 at UTC `20:50:37`: `state=downloading local=145620992 remote=1258291200` (~12%)

   None of these three posts produced an `Ignoring webhook import` line at the time of
   posting. App-log (webhook enqueue/detect only shown for E04 here; E02/E03 analogous):
   ```
   2026-10-22 16:50:37,863 - INFO - seedsyncarr.WebhookManager (MainProcess/worker 1) - Sonarr webhook import enqueued: 'SSA122.Alpha2.S01E04.mkv' (eventType=Download, episodeFile.sourcePath)
   2026-10-22 16:50:38,089 - INFO - seedsyncarr.WebhookManager (MainProcess/ControllerJob) - Sonarr import detected: 'SSA122.Alpha2.S01E04.mkv' (matched SeedSyncarr file 'SSA122.Alpha2.S01'; eventType=Download, episodeFile.sourcePath)
   ```
2. **E02 and E03 revalidated and credited later, without being re-posted** — exactly the
   D-06(c) contract:
   ```
   2026-10-22 16:50:43,809 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Alpha2.S01E02.mkv' in 'SSA122.Alpha2.S01' (root still transferring)
   2026-10-22 16:51:16,285 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Alpha2.S01E03.mkv' in 'SSA122.Alpha2.S01' (root still transferring)
   ```
   (`webhooks.log` confirms exactly one POST each for E02 and E03 — the credit above is not
   a re-post, it is the deferred notice being revalidated and accepted on a later cycle.)
3. **E04's deferred notice was dropped, not credited — the forbidden line occurred:**
   ```
   2026-10-22 16:51:38,396 - WARNING - seedsyncarr.Controller (MainProcess/ControllerJob) - Ignoring webhook import for 'SSA122.Alpha2.S01': not downloaded by SeedSyncarr (no transfer evidence)
   ```
   61 seconds after E04's webhook was posted on a genuinely-incomplete child (step 1), with
   no re-post in between (`webhooks.log` shows exactly one POST for E04). This is the exact
   line D-06(c)'s truth forbids. `persist.imported_children['SSA122.Alpha2.S01']` confirms
   the practical consequence: `['ssa122.alpha2.s01e01.mkv', 'ssa122.alpha2.s01e02.mkv',
   'ssa122.alpha2.s01e03.mkv']` — E04 is permanently absent; the dropped notice is never
   retried (`controller.py:794`/`804` pop the pending-notice key in the same branch that
   logs "Ignoring", with no replacement kept).

   The root still committed and armed shortly after (via the arm-on-commit path, since E02
   and E03's credits were already recorded):
   ```
   2026-10-22 16:51:40,916 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Import credit for 'SSA122.Alpha2.S01' applied on commit
   2026-10-22 16:51:41,677 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Scheduled auto-delete of 'SSA122.Alpha2.S01' in 300 seconds
   ```
   but with `imported_children` short one video child. The auto-delete BFS/coverage guard
   (`auto_delete_manager.py` `run_bfs_and_coverage`, `partial_coverage` check against
   `persist.imported_children`) requires every on-disk video child to appear in
   `imported_children[root]` before it will allow deletion — so the practical effect of this
   defect is **not** an unsafe premature delete (coverage would see 3 of 4 children and
   defer, per the already-tested `test_partial_coverage_defers_then_succeeds` /
   `test_gives_up_after_max_rearms_with_one_warning` behavior), it is that the root can never
   reach full coverage again (E04's only notice is gone) and would eventually give up
   deferring, stranding the local copy — the same operator-cleanup-burden shape as the
   original Days of Hope incident this phase's safeguards were built to close, not a data-loss
   regression. The scenario was stopped at the forbidden-line check (per the plan's explicit
   fail condition) before the real 300 s delay elapsed, so the "gives up" tail was not
   separately observed live; it is covered by `test_gives_up_after_max_rearms_with_one_warning`.

**Diagnosis.** `controller.py:762-782` (inside `__check_webhook_imports`, `controller.py:650`)
gates acceptance on two independently-sourced `ModelFile` fields for the **root directory**:
`has_evidence` (`root_file.local_size >= root_file.remote_size`, populated in
`model_builder.py:275-278` `_fill_model_file` directly from the scanner's own directory-level
size measurement) and `transferring` (`root_file.state in (DOWNLOADING, QUEUED)`, where a
directory's `state` is set in `model_builder.py:505-525` `_check_downloaded_state` →
`_are_all_children_downloaded` (`model_builder.py:527-547`) **purely from each child's own
state**, independent of the directory's own `local_size`/`remote_size` fields). These two
sources can disagree for one build cycle: once every child individually reports
`DOWNLOADED` the directory's `state` flips to `DOWNLOADED` (failing the `transferring` check),
but the directory's own aggregate `local_size` (a separately-scanned quantity) can still read
less than `remote_size` for that same cycle (failing `has_evidence` too) — landing a pending
notice processed in that exact window in neither the has-evidence/commit branch nor the
early-credit/pending branch, only the "Ignoring" branch. This is untested today: the existing
`model_builder.py` directory-state tests
(`test_build_children_state_downloaded_full`/`_full_extra`) always construct the directory's
own local/remote `SystemFile` sizes consistently with its children's, so this specific
cross-field race is not exercised by the current suite, and `test_foreign_local_only_dir_never_credited`
(the one existing test of the "Ignoring" line) covers an unrelated, correctly-rejected case
(a foreign local-only directory with no remote copy at all, `remote_size is None`).

**Proposed fix (not applied — owner decision required per D-03):** narrow the `transferring`
check at `controller.py:778-782` to also treat a directory root as "still in its transfer
lifecycle" when `_are_all_children_downloaded`-equivalent evidence says every known child is
individually `DOWNLOADED` but the root's own `downloaded_file_names`/commit bookkeeping hasn't
caught up yet — i.e., prefer crediting/deferring over "Ignoring" whenever the root is a
directory that SeedSyncarr has an active lifecycle record for (recently released, present in
`__root_lifecycle_generation`), rather than relying solely on the two separately-scanned size
fields. Alternatives: (2) make the directory's own `local_size`/`remote_size` bottom-up sums
of its children inside `model_builder.py` instead of trusting the scanner's own directory-level
measurement (larger blast radius — other local_size/remote_size consumers, e.g. ETA/UI,
would change); (3) in the coverage guard specifically, treat an `Ignoring`-dropped child as
provable from on-disk completeness directly rather than only from a surviving webhook notice.
Each option needs its own red/green regression before any change.

**FAIL (D-06(c)).** SAFE-01 is not marked passed on this run, per D-03.

Unit coverage (existing, confirms the parts of the contract that did work):
`test_import_credit.py::test_pending_notice_reevaluated_when_child_becomes_downloaded`,
`test_pending_notice_discarded_when_resolved_path_changes`,
`test_foreign_local_only_dir_never_credited` (the one pre-existing "Ignoring" test — an
unrelated, correctly-rejected case, not this race).

### D-06(b) Arm on commit and auto-delete — PASS

Run 1, `SSA122.Alpha.S01`.

1. **Commit and arm**, immediately following the three early credits (D-06(a) above — no
   `Scheduled auto-delete` line precedes any of them):
   ```
   2026-10-22 16:21:09,523 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Import credit for 'SSA122.Alpha.S01' applied on commit
   2026-10-22 16:21:10,069 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Scheduled auto-delete of 'SSA122.Alpha.S01' in 300 seconds
   2026-10-22 16:21:10,624 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Recorded webhook import: 'SSA122.Alpha.S01' (child: 'SSA122.Alpha.S01E04.mkv')
   2026-10-22 16:21:10,944 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Scheduled auto-delete of 'SSA122.Alpha.S01' in 300 seconds
   ```
   (The fourth child, E04, happened to finish and get its own webhook accepted via the plain
   "Recorded webhook import" path in the same cycle the root was already marked downloaded by
   the independent scan-driven commit — one of the two phrasings the truth explicitly allows
   ("Import credit... and/or Recorded webhook import"). It re-armed the same 300 s timer,
   benign and idempotent.)
2. **Real 300 s delay, then deletion** — measured against the **second** (later) schedule
   line, `16:21:10,944`:
   ```
   2026-10-22 16:26:10,948 - INFO - seedsyncarr.Controller (MainProcess/Thread-5) - Auto-deleted local file 'SSA122.Alpha.S01'
   ```
   `16:26:10,948 − 16:21:10,944 = 300.004 s` — the configured `delay_seconds=300` (unchanged
   this plan; only `lftp.rate_limit` was altered, confirmed in `state.env`'s
   `DELAY_L0=300`/no `DELAY_SET`). This line is independently timestamped **15 minutes**
   before this session's teardown ran (`STOP seedsyncarr-test` at app-log `16:41:16` — the
   deletion is the product's own Timer firing, not an artifact of cleanup).
3. **Local removal confirmed.** The synthetic root cleanup step of `teardown.sh` reported
   `REMOVED synth roots count=2 refused=0` (both `SSA122.Alpha.S01` and `SSA122.Decoy.S01`
   confirmed absent on the seedbox and under `/downloads` by its own read-back `ls`/stat-style
   checks) when it ran 15 minutes later — consistent with the root already having been deleted
   by the Timer, not by teardown.

**PASS (D-06(b)).** Unit coverage: `test_auto_delete_rearm.py::test_rearmed_timer_fires_and_deletes_once_root_is_deletable`,
`test_fresh_webhook_arm_resets_counter`; `test_import_credit.py::test_root_commit_then_last_child_webhook_arms_and_deletes`,
`test_arm_on_commit_without_further_webhook`.

### Hygiene and secret handling

Both runs' webhook secrets were generated fresh (`head -c 24 /dev/urandom | base64 | tr -dc
'A-Za-z0-9'`, 0600 file, never echoed/logged — `webhook-post.sh` computes the HMAC signature
inside the sandbox container over stdin and only ever prints the resulting hex digest and HTTP
status). `webhooks.log` for both runs shows eight `200` responses (four per run), one per
child, no retries. The run-1 exact-secret scan (`grep -c -F -f secret ...`) could not be
re-run after the fact: run 1's own harness bug (an incorrect "wait for commit" sentinel, fixed
before run 2 — see the Plan 05 SUMMARY) caused `teardown.sh` to run, and delete the secret
file, before that check's turn; run 2's scan was similarly pre-empted by stopping immediately
on the forbidden `Ignoring` line (per the plan's explicit fail-fast instruction), before its
own evidence-save/secret-scan phase. For both runs, a substitute hygiene scan was run instead
over every captured log/model/persist/webhooks file:
`grep -i -E 'password|api_key|Authorization|X-Webhook-Signature'` — **zero hits** in both runs
(`log-SSA122.Alpha.S01-run1.txt`, `log-SSA122.Alpha2.S01-run2-fail.txt`, all `model-a-*.json`/
`model-a2-*.json`, `webhooks.log`). Combined with the code-level guarantee above (the secret
is never passed to the logged HTTP request or printed by the signing script), these capture
files are judged safe to quote verbatim in this evidence file. SECRET_SCAN=0 is recorded
in the Plan 05 SUMMARY as a hygiene-scan result, not an exact-match scan, for both runs.

## Re-pin after 122-10 fix (build under test for Plans 12, 06-08)

Why: 122-05's D-06(c) scenario (`SSA122.Alpha2.S01`) **FAILED** against the original PR #134
staging image (DEV_PIN `sha256:4463de8e...`) — a revalidated pending child notice (E04) was
dropped between its root's transfer ending and its commit, with the forbidden "Ignoring webhook
import ... no transfer evidence" line. 122-10 landed a narrow fix on the same branch/PR (see
`122-10-SUMMARY.md`). Equivalence guard: 122-10 changed `src/python/controller/controller.py`,
so the previous DEV_PIN no longer covers the code that will ship — every SAFE-01 live check from
this point on must run against a build that includes the fix.

### Build under test (re-pin)

- **PR:** https://github.com/thejuran/seedsyncarr/pull/134 (still OPEN, not merged; same branch
  `gsd/phase-122-safety-acceptance-and-logging-fixes`, no new PR opened)
- **NEW_HEAD_SHA:** `81df6b7cb6b15c6d510a3f102631380720415beb` — confirmed equal to
  `gh pr view 134 --json headRefOid -q .headRefOid` both immediately after the push and again
  immediately before the digest lookup below (equivalence guard: no later push occurred in
  between; the newest CI run on the branch has this same headSha).
- **122-10 commits carried by this push** (already landed on the branch prior to this plan;
  this plan's job was to push and confirm CI, not to author them):
  - `f51e55fa7f180b8dc267b834be50a217f7a33bd3` — `test(122-10): reproduce pending notice dropped between transfer end and commit (D-06c)`
  - `73bd59980e3efc56878b651db159fb80954fc926` — `fix(122-10): keep revalidated pending import notice between transfer end and commit (D-06c)`
  - `git merge-base --is-ancestor 73bd599 81df6b7` exits 0 — the fix commit is an ancestor of NEW_HEAD_SHA.
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/39872162737 (run_number 401), conclusion **success**, headSha `81df6b7cb6b15c6d510a3f102631380720415beb`.
- **No later push exists:** `gh run list --workflow=ci.yml --branch gsd/phase-122-safety-acceptance-and-logging-fixes` shows run 401 (databaseId `39872162737`) as the newest entry, headSha matching `gh pr view 134`'s current `headRefOid` exactly; the only other run on the branch is the earlier run 400 (`28942cc2...`, superseded).
- **Per-check conclusions** (`gh pr checks 134`, all pass or expected-skip):

  | Check | Result |
  |---|---|
  | Analyze (actions) | pass |
  | Analyze (javascript-typescript) | pass |
  | Analyze (python) | pass |
  | Angular unit tests | pass |
  | Build Docker Image | pass (27m26s) |
  | CodeQL | pass |
  | End-to-end tests on Docker Image (amd64) | pass |
  | Lint (Angular) | pass |
  | Lint (Python) | pass |
  | Release metadata verifier tests | pass |
  | Verify Python package | pass |
  | Verify release metadata | pass |
  | Python unit tests | pass |
  | Publish GitHub Release / Publish Docker Image / Publish Docker Image (:dev) / Publish Documentation / Publish to PyPI | skipping (expected — `if: github.ref == 'refs/heads/main'` gates are false for a `pull_request` event) |

  `gh pr checks 134` exits 0 (all required checks pass; only the publish-* jobs, which do not run on PRs, show `skipping`).
- **Digest resolution (two independent methods, cross-checked, identical result):**
  - `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:401` → index `Digest: sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4` (`application/vnd.oci.image.index.v1+json`; `linux/amd64` + `linux/arm64` manifests plus their attestation manifests).
  - Anonymous GHCR registry lookup (same method as Plan 04; `gh api .../packages` still 403s):
    ```
    TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io" \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
    curl -s -I -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.oci.image.index.v1+json" \
      "https://ghcr.io/v2/thejuran/seedsyncarr/manifests/401" | grep -i docker-content-digest
    # -> docker-content-digest: sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4
    ```
  - Both 64-hex digests are identical: `e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4`.
- **New DEV_PIN:**
  ```
  DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4
  ```
  This differs from the previous DEV_PIN, as required.
- **Superseded DEV_PIN (Plans 04-05 evidence):** `ghcr.io/thejuran/seedsyncarr@sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9`
  (built from `PR_HEAD_SHA` `28942cc2b65c6c01929d154d8ffa99be4540a9f8`, run 400 — this image does
  **not** contain the 122-10 fix; D-06(c) evidence captured against it is superseded by the
  rerun this plan prepares the sandbox for).
- No new PR was created (`gh pr list --head gsd/phase-122-safety-acceptance-and-logging-fixes --json number -q '.[].number'` prints only `134`); no merge; no `gh pr ready` call.
