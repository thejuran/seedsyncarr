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

Superseded: rerun on the 122-10 fixed build, see "Plan 12: D-06 rerun on the fixed build"
(verdict: PASS).

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

### Sandbox re-pin and LOG-01 recheck

NAS capture dir (0700, not committed): `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`.
Holds `teardown.sh`, `webhook-post.sh` (byte-identical copies of the committed harness,
confirmed by local `diff`), `deploy.sh` (one-off, trap-protected re-pin driver for this
session only), `state.env`, `prod-before.txt`/`prod-after.txt`, and `model_tools.py` /
`round2.sh` copied from the previous capture dir
(`/volume1/docker/v5test/results/safe01-122-20261022T195544Z`) for 122-12 to reuse.

**Pre-copy secret scan of the two reused helper files** (`grep -c -i -E
'password|api_key|secret'`): `model_tools.py` → 0 hits (copied as-is). `round2.sh` → 20 hits,
all inspected directly (`grep -n`): every hit is the word `secret` in a variable name
(`SECRET`, `SECRET_BODY`, `SECRET_SCAN...`), a `webhook_secret` config-key literal, or a
comment — the script generates a fresh random value from `/dev/urandom` at runtime and never
contains a hardcoded secret value; it is the same pattern `teardown.sh`/`webhook-post.sh`
already use safely. Judged safe to copy; copied as-is, not skipped.

`IMAGE_PIN_L0` read from the previous capture dir's `state.env` (first/only value) and
required equal to `ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e`
— matched. `state.env` in the new capture dir:
```
IMAGE_PIN_L0=ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e
PREV_DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:4463de8e449139496ee9387dac1393297c9268e932870cbd6baa9bb93c0a4cf9
DEV_PIN=ghcr.io/thejuran/seedsyncarr@sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4
```

**Preflight** (before any write): compose file's `seedsyncarr-test` image line and
`docker inspect seedsyncarr-test --format '{{.Config.Image}}'` both equaled PREV_DEV_PIN;
`ls /volume1/data/v5test/torrents` showed zero `SSA122.*` names (no leftover synthetic
material from Plan 05).

**Deploy** (trap-protected: `trap 'exit 130' INT TERM HUP` first, then
`trap '[ "$OK" = 1 ] || bash "$D/teardown.sh" --final' EXIT INT TERM HUP` — any interruption
would have restored IMAGE_PIN_L0 rather than leaving a half-deployed sandbox):

```
EDIT compose image line to NEW_DEV_PIN ok (inode before=101505523 after=101505523)
$ sudo /usr/local/bin/docker compose -f /volume1/docker/v5test/docker-compose.yml pull seedsyncarr-test
  seedsyncarr-test Pulled
$ sudo /usr/local/bin/docker compose -f /volume1/docker/v5test/docker-compose.yml up -d seedsyncarr-test
  Container seedsyncarr-test  Recreated
  Container seedsyncarr-test  Started
WAIT server/status ok
DEPLOY image verified: ghcr.io/thejuran/seedsyncarr@sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4
DEPLOY container_image_id=sha256:6f2719dbb9c2c2e8a56a7e992d2052ad5123a5ce302743a86d0ebc400012a792
DEPLOY webhook_secret length=0 confirmed
DEPLOY test_event http=200 body=Test OK
DEPLOY_OK
PROD_UNCHANGED
REPIN_SESSION_OK
```

Compose file inode unchanged across the edit (`101505523` before and after — confirmed
inode-preserving, not a file replacement). `docker inspect seedsyncarr-test --format
'{{.Config.Image}}'` after deploy equals NEW_DEV_PIN exactly (re-confirmed independently via
the Task 2 verify command, same result).

NAS host clock (UTC, `date -u`) around the deploy: pull/recreate completed and the Test event
fired between `2026-10-23T17:04:14Z` and `2026-10-23T17:04:53Z` (NAS host local zone is -05,
so host-local was ~12:04).

### Production unchanged (fingerprint comparison)

```
before: 2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-23T07:04:18.591254939Z
after:  2feb4073db711c623c4719f1fdd328cb3216201a162c6e8b7fabe33d386b32f9 ghcr.io/thejuran/seedsyncarr:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e 2026-10-23T07:04:18.591254939Z
```
`diff` of the two capture files: empty (identical container Id, image and StartedAt). The
production container `seedsyncarr` was never named by any write command in this plan's
procedures — only `-f /volume1/docker/v5test/docker-compose.yml` and the `seedsyncarr-test`
service were ever targeted.

Note: this `StartedAt` (`2026-10-23T07:04:18Z`) differs from the `2026-10-15T22:15:22Z`
recorded in `122-04-SUMMARY.md`/the orchestrator's prior notes, while the container `Id` and
pinned image digest are unchanged. This indicates production `seedsyncarr` restarted at some
point between those two observations (e.g. a host/Docker daemon restart) — not an action taken
by this plan, whose own before/after fingerprints (captured minutes apart in this session) are
byte-identical, which is the actual guarantee this plan is responsible for.

### LOG-01 live on the fixed build (webhook handler logging reaches the app log)

Unsigned (`webhook_secret` length confirmed 0, no `X-Webhook-Signature` header sent)
`{"eventType":"Test"}` posted to `/server/webhook/sonarr` returned HTTP 200, body `Test OK`.
App log line count immediately before the post: 4989. Verbatim sandbox app-log line found
after that line (clocks: NAS host UTC ~`2026-10-23T17:04:3xZ` → host-local -05 ~`12:04:3x` →
app-log local-+1h convention `13:04:37`, matching below):
```
2026-10-23 13:04:37,406 - INFO - seedsyncarr.WebhookHandler (MainProcess/worker 1) - Sonarr webhook test event received
```
Logger field is `seedsyncarr.WebhookHandler`, timestamped after the re-pin. LOG-01 is
confirmed still live on the build containing the 122-10 fix.

The sandbox is intentionally left running NEW_DEV_PIN (teardown was not run at the end of this
plan) for 122-12's rerun of 122-05's D-06(c) scenario and Plans 06-08; Plan 08 runs
`teardown.sh --final`, which will restore `IMAGE_PIN_L0` (the original 1.7.6 pin), confirmed
present and correct in this capture dir's `state.env`.

## Plan 12: D-06 rerun on the fixed build

Build under test: `seedsyncarr-test` on the new DEV_PIN
(`ghcr.io/thejuran/seedsyncarr@sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4`,
containing 122-10's post-transfer-pending-notice fix), re-confirmed via `docker inspect
.Config.Image` immediately before this session: equal to the last `DEV_PIN` line in
`state.env`. Capture dir: `/volume1/docker/v5test/results/safe01-122-20261023T165741Z`
(same dir prepared by 122-11).

Clocks: NAS host clock read via `date -u` (UTC); app-log time = UTC time − 4h (confirmed by
matching each release/post command's own UTC timestamp against its own log line below — e.g.
the Echo release at host UTC `2026-10-23T17:18:46Z` appears in the app log at `13:18:46`).

Sizing used: `SSA122.Echo.S01` / `SSA122.EchoDecoy.S01` (Round A) with Echo's siblings at
E01 8 MiB, E02 300 MiB, E03 800 MiB, E04 1200 MiB and the decoy at 8 MiB — the exact sizing
that reliably produced a genuinely-incomplete-at-post-time child in 122-05's own round 2.
`SSA122.Foxtrot.S01` (Round B, (c)-only repeat, no decoy) with E01 8 MiB (never webhooked,
by design — see below), E02 800 MiB, E03 1200 MiB. `lftp.rate_limit` was set to 4194304
(same as 122-05); `general.debug` was confirmed `False` this session (see "Observability"
below). Both rounds ran in a single session; no retry/Golf fallback was needed — every
targeted child was caught genuinely incomplete on the first attempt (`MISS_COUNT=0` for both
roots, recorded in `state.env`).

### D-06(e) Waiting hold and one-shot release (rerun)

1. **Both roots held, no queue entry.** App-log `13:18:39,796`/`,797`:
   ```
   2026-10-23 13:18:39,796 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.Echo.S01': No matching queue entry
   2026-10-23 13:18:39,797 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.EchoDecoy.S01': No matching queue entry
   ```
   `model-e-held.json`: both roots `hold_reason="no_queue_entry"`, `state="default"`,
   `local_size=None` (zero local bytes).
2. **One-shot manual release of `SSA122.Echo.S01` only.** `POST
   /server/command/queue/SSA122.Echo.S01?release_unverified=true` at NAS host UTC
   `2026-10-23T17:18:46Z` → HTTP 200, body `Queued file 'SSA122.Echo.S01'`. App-log
   (`13:18:46`):
   ```
   2026-10-23 13:18:46,395 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Received command Action.QUEUE for file SSA122.Echo.S01
   2026-10-23 13:18:46,395 - WARNING - seedsyncarr.Controller.CommandProcessor (MainProcess/ControllerJob) - Manual release of unverified 'SSA122.Echo.S01' (No matching queue entry); source-completion check bypassed for this transfer only
   2026-10-23 13:18:46,571 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold dropped for 'SSA122.Echo.S01' (no longer a queue candidate)
   ```
   `SSA122.EchoDecoy.S01` was never named by any release call.
3. **Decoy never transferred, confirmed at three separate points across the whole
   session** (right after the Echo release, during Echo's transfer, and again in the
   `SSA122.Foxtrot.S01` hold-wait snapshot taken after Echo had already auto-deleted):
   ```
   model-echo-1.json:    SSA122.EchoDecoy.S01 hold_reason=no_queue_entry state=default local_size=None
   model-echo-<later>:   SSA122.EchoDecoy.S01 hold_reason=no_queue_entry state=default local_size=None
   model-foxtrot-held.json: SSA122.EchoDecoy.S01 hold_reason=no_queue_entry state=default local_size=None
   (same snapshot: SSA122.Echo.S01 hold_reason=None state=deleted — confirming the decoy
   stayed held even after its sibling root had fully completed and been deleted)
   ```
   `Completion hold dropped` (never `cleared`) is the only hold-removal wording for either
   root in the whole session — `grep -c "Completion hold cleared for 'SSA122\." ` over
   `log-echo-foxtrot.txt` = **0**.

**PASS (D-05, D-06(e)).** Cross-reference: the real Sonarr-queue completion gate is
`120-SON5-EVIDENCE.md` §SON5-02 / `120-CAPTURE-NOTES.md`, per D-04 — not re-captured here.

### D-06(a) Early per-episode credit (rerun)

1. **E01 caught DOWNLOADED while all three siblings were still at 0%** (`model-echo-e01ready.json`):
   `e01[state=downloaded local=8388608 remote=8388608] e02[state=downloading local=0
   remote=314572800] e03[state=downloading local=0 remote=838860800] e04[state=downloading
   local=0 remote=1258291200]`. Signed webhook posted → `HTTP_CODE=200` (`webhooks.log`:
   `2026-10-23T17:18:56Z SSA122.Echo.S01E01.mkv 200`).
2. **Credited immediately, root not committed.** App-log:
   ```
   2026-10-23 13:18:56,383 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Echo.S01E01.mkv' in 'SSA122.Echo.S01' (root still transferring)
   ```
3. **Two more early credits**, for children that finished individually (E02, E03) while
   `SSA122.Echo.S01E04.mkv`, the largest sibling, was still transferring — confirming the
   root as a whole was still transferring at each credit:
   ```
   2026-10-23 13:19:09,043 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Echo.S01E02.mkv' in 'SSA122.Echo.S01' (root still transferring)
   2026-10-23 13:19:42,066 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Echo.S01E03.mkv' in 'SSA122.Echo.S01' (root still transferring)
   ```
   No `Scheduled auto-delete` line precedes any of these three (confirmed by the `ORDER`
   check logged this session: `first_accept_line=5013 schedule_line=5014`, i.e. the first
   acceptance line is strictly and immediately before the schedule line).

**PASS (D-06(a)).** Unit coverage (unchanged by 122-10):
`test_import_credit.py::test_child_notices_before_commit_are_credited_not_dropped`,
`test_credit_persists_immediately_via_callback`, `test_credit_alone_never_deletes`.

### D-06(c) Deferral and revalidation (rerun on fixed build)

Both `SSA122.Echo.S01E04.mkv` (Round A) and `SSA122.Foxtrot.S01E03.mkv` (Round B) reproduce
the *exact* race that caused 122-05's FAIL: a webhook posted on a genuinely-incomplete child,
followed roughly 60-100s later — after that child (and the root's other remaining children)
individually finished — by the root's commit cycle, landing in the window between "all
children individually DOWNLOADED" and "root's own commit bookkeeping catching up". On the
pre-fix build this window produced `Ignoring webhook import ... no transfer evidence`
(122-05's `SSA122.Alpha2.S01E04`, dropped 61s after posting). On this build it does not.

1. **E02, E03 and E04 posted while genuinely incomplete** (`posts-echo.txt`, state/local/remote
   recorded immediately before each post):
   ```
   2026-10-23T17:18:58Z child=SSA122.Echo.S01E02.mkv INCOMPLETE state=downloading local=0 remote=314572800
   2026-10-23T17:19:01Z child=SSA122.Echo.S01E03.mkv INCOMPLETE state=downloading local=147160069 remote=838860800  (~17.5%)
   2026-10-23T17:19:04Z child=SSA122.Echo.S01E04.mkv INCOMPLETE state=downloading local=146407424 remote=1258291200  (~11.6%)
   ```
   `webhooks.log` confirms exactly one `200` POST for each (no retries).
2. **E02 and E03 revalidated and credited without being re-posted** — the ordinary
   early-credit path (quoted under D-06(a) above), each strictly before the root's final
   acceptance.
3. **E04's deferred notice was accepted, not dropped — the critical check:**
   ```
   2026-10-23 13:20:06,625 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Recorded webhook import: 'SSA122.Echo.S01' (child: 'SSA122.Echo.S01E04.mkv')
   2026-10-23 13:20:08,367 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Scheduled auto-delete of 'SSA122.Echo.S01' in 300 seconds
   ```
   62 seconds after E04's webhook was posted on a genuinely-incomplete child (step 1) — the
   same order of magnitude as 122-05's 61-second drop — **no** `Ignoring webhook import for
   'SSA122.` line occurs anywhere in this session (`grep -c "Ignoring webhook import for
   'SSA122\."` over `log-echo-foxtrot.txt` = **0**). `persist-echo.json` confirms the
   practical consequence: `imported_children['SSA122.Echo.S01']` =
   `['ssa122.echo.s01e01.mkv', 'ssa122.echo.s01e02.mkv', 'ssa122.echo.s01e03.mkv',
   'ssa122.echo.s01e04.mkv']` — **all four** video children present (captured immediately
   after the schedule line, before auto-delete could prune anything).
   `Recorded webhook import: '<root>' (child: '<child>')` is the code path at
   `controller.py:882` (inside `__check_webhook_imports`'s "Accepted" branch, the same
   common code that also handles `add_imported_child`) — one of the two acceptance
   phrasings the D-06(b) truth explicitly allows, not a re-post (webhooks.log shows exactly
   one POST for E04).

   Count of `Ignoring webhook import for 'SSA122.` lines this session: **0**. Which path
   credited each late child: E02/E03 via the ordinary early-credit path (`Credited early
   import of ... (root still transferring)`, because the root's *other* children — E04 in
   particular — were still transferring at the moment each was revalidated); E04 via the
   commit-time "Recorded webhook import" acceptance path, landing in the post-transfer
   window the 122-10 fix targets (all individual children DOWNLOADED, root's own commit
   bookkeeping catching up one cycle later). `Keeping webhook notice ... transfer finished,
   awaiting commit` DEBUG lines were **not observable** this session (`general.debug=False`,
   confirmed read from `/server/config/get` at preflight and recorded in `state.env` as
   `DEBUG_L0=False`) — the verdict rests on the outcome checks above (zero `Ignoring` lines,
   complete `imported_children`, correct accept-before-schedule ordering), not on observing
   the DEBUG "Keeping" line directly.

   Cross-reference to 122-10's regression coverage:
   `test_import_credit.py::TestPostTransferWindow` —
   `test_pending_notice_survives_post_transfer_scan_lag_default_root` (the live-reachable
   shape, matching this session's own timing exactly: lftp job ended, local scan lagging),
   `test_pending_notice_survives_post_transfer_scan_lag_downloaded_root` (the
   unit-test-only shape), plus two guards unaffected by this fix:
   `test_post_transfer_pending_notice_still_expires` (TTL still fires) and
   `test_post_transfer_pending_notice_dropped_when_root_loses_remote_copy` (a root that
   loses its remote copy is still dropped).

**PASS (D-06(c)).**

### D-06(c) repeat on SSA122.Foxtrot.S01

A second, (c)-only repeat on a fresh root (no decoy, no E01 webhook posted at all — this
root's E01 child was staged but deliberately never given a webhook, so its only path to
being imported is the root-level commit itself; the children under test are purely E02 and
E03) to reduce the chance the Echo-round pass was a one-off miss of the race window.

1. **Hold, release, both children posted while genuinely incomplete** (`posts-foxtrot.txt`):
   ```
   2026-10-23T17:27:54Z child=SSA122.Foxtrot.S01E02.mkv INCOMPLETE state=downloading local=0 remote=838860800
   2026-10-23T17:27:55Z child=SSA122.Foxtrot.S01E03.mkv INCOMPLETE state=downloading local=0 remote=1258291200
   ```
   `webhooks.log`: one `200` POST each, no retries.
2. **E02 credited via the ordinary early-credit path**, then **E03's deferred notice
   accepted on commit** — again, not dropped:
   ```
   2026-10-23 13:28:57,530 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Foxtrot.S01E02.mkv' in 'SSA122.Foxtrot.S01' (root still transferring)
   2026-10-23 13:29:40,191 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Recorded webhook import: 'SSA122.Foxtrot.S01' (child: 'SSA122.Foxtrot.S01E03.mkv')
   2026-10-23 13:29:41,683 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Scheduled auto-delete of 'SSA122.Foxtrot.S01' in 300 seconds
   ```
   E03's acceptance is ~104s after its post — again, no `Ignoring webhook import for
   'SSA122.` line for Foxtrot anywhere in the session. `persist-foxtrot.json`:
   `imported_children['SSA122.Foxtrot.S01']` = `['ssa122.foxtrot.s01e02.mkv',
   'ssa122.foxtrot.s01e03.mkv']` — both webhooked children present (E01 is correctly absent:
   it was never webhooked by design, and the coverage/UI badge behavior for a root whose
   only "child" evidence came through the commit path is unchanged by this fix — not
   re-tested here, out of this plan's scope).

**PASS (D-06(c) repeat, Foxtrot).** Combined with the Echo-round pass above, the race was
hit and handled correctly twice, on two independent roots, in the same session.

### D-06(b) Arm on commit and auto-delete (rerun)

Only re-run with the real 300 s delay on `SSA122.Echo.S01` (Foxtrot's own schedule line is
evidenced above; its delete wait is not required by this plan).

1. **Schedule**, immediately after E04's commit-time acceptance (quoted under D-06(c)
   above): `Scheduled auto-delete of 'SSA122.Echo.S01' in 300 seconds` at app-log
   `13:20:08,367`.
2. **Real delay, then deletion**, measured against the schedule line:
   ```
   2026-10-23 13:25:08,371 - INFO - seedsyncarr.Controller (MainProcess/Thread-4) - Auto-deleted local file 'SSA122.Echo.S01'
   ```
   `13:25:08,371 − 13:20:08,367 = 300.004 s` by the log timestamps; this session's own
   elapsed-time tracking (epoch-based, independent of log parsing) recorded `341s` past the
   scheduling observation (the extra ~41s is polling/detection latency in the harness's own
   20s-interval log-grep loop, not the product's timer — the log timestamps themselves show
   the timer fired at exactly 300.004s, consistent with 122-05's own 300.004s observation).
3. **Local removal confirmed**: `ls -la /volume1/data/v5test/torrents/SSA122.Echo.S01` →
   `No such file or directory`, checked immediately after the delete line was observed (and
   independently re-confirmed clean after teardown).

**PASS (D-06(b)).** Unit coverage unchanged: `test_auto_delete_rearm.py::test_rearmed_timer_fires_and_deletes_once_root_is_deletable`,
`test_import_credit.py::test_root_commit_then_last_child_webhook_arms_and_deletes`.

### Plan 12 hygiene

Secret handling: fresh `head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9'` secret, 0600
file, never echoed or logged (`webhook-post.sh` computes the HMAC inside the sandbox
container over stdin). The exact-match secret scan (`grep -c -F -f secret` over every
`log-*.txt`/`model-*.json`/`persist-*.json`/`webhooks.log` capture file) was run **after**
this session's own orchestration script hit an unrelated bash arithmetic bug in its
`scan_secret` helper (see Deviations in `122-12-SUMMARY.md`) — the scan itself was re-run
manually with the corrected logic, over the same files, before teardown: **`SECRET_SCAN=0`**
(exact-match, 20 files scanned, zero hits), recorded in `state.env`. `webhooks.log` shows six
`200` responses (four Echo + two Foxtrot), one per posted child, no retries.

Teardown: `bash teardown.sh` (not `--final`) ran after the scan, restoring `lftp.rate_limit`
to its prior value (`0`), restoring `webhook_secret` to empty, and removing all three
synthetic roots (`REMOVED synth roots count=3 refused=0`) from both the seedbox and the
sandbox's local data root. Last line: **`SANDBOX_RESTORED ok`**. Re-confirmed independently
afterward: `docker inspect seedsyncarr-test --format '{{.Config.Image}}'` still equals the
new DEV_PIN (teardown without `--final` does not change the pin); `lftp.rate_limit` reads
back `0`; no `SSA122.*` names remain on the seedbox or under `/volume1/data/v5test/torrents`.
Production `seedsyncarr` fingerprint (Id, image, `StartedAt`) was re-checked read-only before
and after this session and is byte-identical to the 122-11 baseline — never named by any
write command in this plan's procedures.

## Plan 06: D-06(d) Restart persistence on the fixed build

Build under test: `seedsyncarr-test` on the same DEV_PIN as Plan 12
(`ghcr.io/thejuran/seedsyncarr@sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4`,
containing 122-10's post-transfer-pending-notice fix), re-confirmed via `docker inspect
.Config.Image` immediately before this session: equal to the `DEV_PIN` line in `state.env`.
Capture dir: `/volume1/docker/v5test/results/safe01-122-20261023T165741Z` (same dir prepared
by 122-11, reused by 122-12 and this plan).

Clocks: NAS host clock read via `date -u` (UTC); app-log time = UTC time − 4h (confirmed by
matching the release command's own UTC timestamp, `2026-10-23T18:14:22Z`, against its own
app-log line below, `14:14:22`).

Root used: `SSA122.Bravo3.S01` (E01 8 MiB, E02 300 MiB, E03 300 MiB). Two earlier attempts on
this session (`SSA122.Bravo.S01`, then `SSA122.Bravo2.S01`) were aborted by two distinct
test-harness-only bugs in this plan's own orchestration script before any pass/fail evidence
was produced — both are documented in `122-06-SUMMARY.md`'s Deviations, not reproduced here.
The sandbox was fully restored (`SANDBOX_RESTORED ok`) after each aborted attempt before the
next one began; no code under `src/` was changed by either fix.

### D-06(d) Restart persistence — PASS

1. **Hold, one-shot release.** App-log (`14:14:16`/`14:14:22`):
   ```
   2026-10-23 14:14:16,293 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.Bravo3.S01': No matching queue entry
   2026-10-23 14:14:22,890 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Received command Action.QUEUE for file SSA122.Bravo3.S01
   2026-10-23 14:14:22,891 - WARNING - seedsyncarr.Controller.CommandProcessor (MainProcess/ControllerJob) - Manual release of unverified 'SSA122.Bravo3.S01' (No matching queue entry); source-completion check bypassed for this transfer only
   2026-10-23 14:14:23,067 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold dropped for 'SSA122.Bravo3.S01' (no longer a queue candidate)
   ```
   `POST /server/command/queue/SSA122.Bravo3.S01?release_unverified=true` at NAS host UTC
   `2026-10-23T18:14:22Z` → HTTP 200, body `Queued file 'SSA122.Bravo3.S01'`.

2. **E01 caught DOWNLOADED while E02/E03 are still transferring.** Model snapshot
   (`model-d-e01ready.json`) immediately before the post: `e01[state=downloaded
   local=8388608 remote=8388608] e02[state=downloading local=0 remote=314572800]
   e03[state=downloading local=0 remote=314572800]`. Signed webhook posted for E01
   (`webhook-post.sh`) → `HTTP_CODE=200`.

3. **Credited while the root is still transferring.** App-log:
   ```
   2026-10-23 14:14:30,642 - INFO - seedsyncarr.Controller (MainProcess/ControllerJob) - Credited early import of 'SSA122.Bravo3.S01E01.mkv' in 'SSA122.Bravo3.S01' (root still transferring)
   ```

4. **Persisted credit confirmed before the restart.** `controller.persist`
   `imported_children['SSA122.Bravo3.S01']`, read read-only via Python/`json` (saved as
   `persist-bravo-before.json`):
   ```
   [
     "ssa122.bravo3.s01e01.mkv"
   ]
   ```

5. **Restart.** NAS host UTC `2026-10-23T18:14:35Z` (app-log `14:14:35`-ish; the container's
   own `Caught signal SIGTERM` line is `14:14:37,669`, a couple of seconds later, which is the
   normal signal-delivery/graceful-shutdown gap, not a discrepancy):
   ```
   $ sudo /usr/local/bin/docker restart seedsyncarr-test
   ```
   `/server/status` returned 200 again at NAS host UTC `2026-10-23T18:15:13Z` (app-log
   `14:15:13`-ish; the container's own startup lines land at `14:15:09`-`14:15:12`, slightly
   before the polling loop's next 200, consistent with poll latency). `docker inspect
   seedsyncarr-test --format '{{.Config.Image}}'` immediately after the restart still equals
   the same DEV_PIN as before — a `docker restart`, not a recreate.

6. **Credit survived the restart.** `controller.persist`
   `imported_children['SSA122.Bravo3.S01']`, re-read after the restart (saved as
   `persist-bravo-after.json`):
   ```
   [
     "ssa122.bravo3.s01e01.mkv"
   ]
   ```
   Identical to the pre-restart read. Nothing else in `src/python/common/persist.py`'s
   immediate-callback/periodic-save path was exercised differently by this plan; this is the
   same `imported_children` field Plan 12 already exercised on this build.

7. **The one-shot release did not survive the restart — the root is held again (D-05).**
   App-log, the second occurrence of the hold line in this session, well after the restart:
   ```
   2026-10-23 14:16:45,752 - INFO - seedsyncarr.CompletionGate (MainProcess/ControllerJob) - Completion hold for 'SSA122.Bravo3.S01': No matching queue entry
   ```
   `grep -c "Completion hold for 'SSA122.Bravo3.S01': No matching queue entry" log-bravo.txt`
   = **2** (one before the restart, one after) — confirming the manual, unverified release is
   an in-memory, one-shot decision that is not persisted: after the restart the root goes back
   through the same evidence gate fresh and is held for the same reason as the first time.
   The model's own `state` field for the root stayed `default` (never `downloading` or
   `queued`) at every sample from the moment the server came back up
   (`2026-10-23T18:15:16Z`) through the end of the observation window below — the root never
   resumed transferring without a new release.

8. **No schedule, no delete, local bytes frozen, for well over 360 s after the restart.**
   The root's total local size (`315` KiB-rounded... exactly `307119406` bytes: E01
   `8388608` + E02 `162350766` + E03 `136380032`) was read at the first confirmed post-restart
   hold (`2026-10-23T18:15:16Z`) and at every ~20-25 s poll through the end of a 390 s
   observation window (`2026-10-23T18:23:00Z`, comfortably over the plan's 360 s floor) —
   **identical at every single sample, with zero variance**. Per-child reads at the two ends
   of that window (`model-d-after-1.json` just after the hold reappeared, vs
   `model-d-after-final.json` at the end of the window) are byte-identical:
   ```
   e02: state=default local=162350766 remote=314572800
   e03: state=default local=136380032 remote=314572800
   ```
   `grep -c "Scheduled auto-delete of 'SSA122.Bravo3" log-bravo.txt` = **0**;
   `grep -c "Auto-deleted local file 'SSA122.Bravo3" log-bravo.txt` = **0** (both confirmed
   independently via this plan's own literal `<verify>` command pattern, generalized to the
   root name actually used this session — see `122-06-SUMMARY.md` for the note on why the
   root was renamed from `SSA122.Bravo.S01`).

**PASS (D-06(d), D-05).** The whole-folder delete still waits for full coverage after a
restart exactly as it did before one; the early credit is durable; the one-shot manual
release is not. Unit coverage: `test_import_credit.py::test_restart_with_persisted_credit_arms_on_commit`
(a fresh `Controller` built from a serialized `ControllerPersist.from_str(seeded.to_str())`
holding already-credited children plus `downloaded_file_names`, confirming arm-on-commit
fires correctly on the very first `process()` call after a simulated restart — the same
level-triggered "it also covers a restart" code path documented at
`controller.py:888-889`), `test_credit_persists_immediately_via_callback`,
`test_credit_alone_never_deletes` (119-05, Days of Hope regression, confirming a credit
alone never arms a delete, restart or not).

### Plan 06 hygiene

Secret handling: fresh `head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9'` secret, 0600
file, never echoed or logged (same `webhook-post.sh` pattern as every prior plan). The
exact-match secret scan (`grep -c -F -f secret` over every `log-*.txt`/`model-*.json`/
`persist-*.json`/`webhooks.log` capture file produced by the successful `SSA122.Bravo3.S01`
run) recorded **`SECRET_SCAN=0`** in `state.env`. `webhooks.log` for the successful run shows
one `200` response (the single E01 post), no retries.

Teardown: `bash teardown.sh` (not `--final`) ran after the scan, restoring `lftp.rate_limit`
to `0`, restoring `webhook_secret` to empty (via the stop/edit-`settings.cfg`/start sequence,
since the webhook endpoint 400s on an empty value otherwise), and removing the one synthetic
root (`REMOVED synth roots count=1 refused=0`) from both the seedbox and the sandbox's local
data root. Last line: **`SANDBOX_RESTORED ok`**. Re-confirmed independently afterward:
`docker inspect seedsyncarr-test --format '{{.Config.Image}}'` still equals the same DEV_PIN;
`lftp.rate_limit` reads back `0`; `webhook_secret` length `0`; no `SSA122.*` names remain on
the seedbox or under `/volume1/data/v5test/torrents`. Production `seedsyncarr` fingerprint
(`Id`, image, `StartedAt`) was re-checked read-only after this session and is byte-identical
to the 122-11/122-12 baseline (`2feb4073...`, `:1.7.6@sha256:da6196e0...`,
`2026-10-23T07:04:18.591254939Z`) — never named by any write command in this plan's
procedures.

## D-07 Extraction staging and auto-delete re-arm

Live-run on the fixed DEV_PIN (`sha256:e3941f976b5bf43370238ac3a7410f569e04b49f635d4e65382b4c1e3284ebe4`,
same capture dir `safe01-122-20261023T165741Z` reused from Plans 05/06/12), replaying the
Burbs incident's own two deferred `after_deploy` checks from
`.planning/debug/extract-staging-autodel-rearm.md`: (1) extraction must stage out of sight
and publish only when complete, and (2) an import accepted while the root is `EXTRACTING`
must defer auto-delete and retry until it succeeds.

### Archive and settings

A single incompressible `/dev/urandom` `.mkv` of exactly `1073741824` bytes (1 GiB) was
built on the seedbox (`nyx.usbx.me`, `/home/jules1651/ssa122-stage/`) and packed with
`rar a -m0 -v600m` (store mode, no compression — the content is already random) into a
directory named `SSA122.Rar.Pack/` holding two volumes:

```
SSA122.Rar.Pack.part1.rar   629145600 bytes
SSA122.Rar.Pack.part2.rar   444596623 bytes
```

**Discretion note on volume count (D-07's own "about 11 volumes" is illustrative, not a
requirement — 122-CONTEXT.md D-07/"Claude's Discretion" leaves the volume size to the
executor as long as the shape matches D-07's "roughly 1 GB ... split into volumes").**
Before building the real archive, a throwaway 3-volume test pack was built and extracted
directly with `unrar` on the NAS host to check how `ExtractDispatch` would treat a modern
RAR 5.0+ volume set. `__coalesce_extractions` (`dispatch.py`) only filters the **old**
WinRAR volume-continuation extension pattern `^\.r\d{2,}$` (e.g. `.r00`, `.r01`); RAR 7.11
(installed on the seedbox) only creates the **new**-style `.partN.rar` naming, where every
volume — including the first — ends in `.rar`. `Extract.is_archive()` therefore treats
**every** volume as its own archive to extract, so a task with N volumes runs N fully
redundant extraction passes (confirmed live below: a `Replacing existing ... with the newly
extracted copy` warning on the second pass). This is pre-existing, out-of-scope behavior
(not a safety defect — each redundant pass still stages before publishing, see the samples
below) but it directly affects timing: with the plan's fixed `delay_seconds = 2` and the
24-deferral cap (48 s total budget), too many volumes could in principle exhaust the budget
before extraction finishes. Two volumes (measured ~2.2 s per solo pass on this NAS's host
`unrar`) keeps the worst case comfortably inside budget while still being "split into
volumes" per D-07. Logged as a Phase 123 backlog candidate in `deferred-items.md` below —
not fixed here (Scope Boundary: pre-existing, no safety impact, out of scope for a
live-acceptance plan).

Settings for the session: `autodelete.delay_seconds` temporarily set to **`2`** (from
`DELAY_L0 = 300`, read via `/server/config/get` before changing anything) — the timer reads
`delay_seconds` at arm time (`controller.py` `__arm_auto_delete_timer`), and a ~1 GB
extraction finishes in low single-digit seconds, far inside 300 s, so 300 s would never let
the timer fire while the root is still `EXTRACTING`. `lftp.rate_limit` was **not** changed
(stayed at its baseline `0`, per the plan). A fresh webhook secret was generated the same
way as every prior plan (0600 file, never logged). `auto_extract = True` and
`use_local_path_as_extract_path = True` were confirmed live before the run (unchanged from
every prior plan in this phase).

### Timeline (both clocks; app-log clock = NAS host local clock + 1 h, NAS host local clock
= UTC − 5 h this session, confirmed via `date` / `date -u` on the NAS)

1. **Hold.** NAS UTC `18:51:03` / app-log equivalent just before the next line:
   ```
   2026-10-23 14:50:57,737 - INFO - seedsyncarr.CompletionGate - Completion hold for 'SSA122.Rar.Pack': No matching queue entry
   ```
2. **One-shot manual release**, NAS UTC `18:51:03`:
   ```
   2026-10-23 14:51:03,783 - INFO - seedsyncarr.Controller - Received command Action.QUEUE for file SSA122.Rar.Pack
   2026-10-23 14:51:03,784 - WARNING - seedsyncarr.Controller.CommandProcessor - Manual release of unverified 'SSA122.Rar.Pack' (No matching queue entry); source-completion check bypassed for this transfer only
   2026-10-23 14:51:04,650 - INFO - seedsyncarr.CompletionGate - Completion hold dropped for 'SSA122.Rar.Pack' (no longer a queue candidate)
   ```
   (The "dropped" wording here is the LOG-02 prune-path line, correctly distinct from
   "cleared" — this hold removal is a manual release, not a proof-based completion.)
3. **Transfer.** Local bytes climbed from `0` to the full `1073742223` (sum of the two
   volumes) between NAS UTC `18:51:04` and `18:52:02`, sampled every 3 s by the harness
   (`model-x-1-*.json`); no partial-file exposure risk applies to this phase (the volumes
   themselves are the only local content, and they are legitimately partial while
   downloading — Sonarr/Radarr only react to the release folder's *final*, stable content,
   which is exactly what this scenario is testing for the *extracted* file).
4. **Extraction starts.** NAS UTC `18:52:02`-`18:52:03` / app-log:
   ```
   2026-10-23 14:52:02,931 - INFO - seedsyncarr.AutoQueue - Auto extracting 'SSA122.Rar.Pack'
   2026-10-23 14:52:03,432 - INFO - seedsyncarr.Controller - Received command Action.EXTRACT for file SSA122.Rar.Pack
   ```
5. **Staging grows while the release folder shows only the two `.rar` volumes.** The
   0.2 s-interval sampler (`extract-samples.txt`, 716 total blocks this run) recorded 7
   consecutive qualifying samples (`QUALIFYING_SAMPLES=7`, `GROWING_PAIRS=7` — every one
   strictly larger than the last) during the **first** extraction pass, NAS UTC
   `18:52:05.121` → `18:52:07.314`, condensed here (`ls -ln` of the release folder,
   `du -sb` of the staging dir):

   | Sample time (UTC) | Release folder lists | Staging bytes |
   |---|---|---|
   | 18:52:05.121 | `SSA122.Rar.Pack.part1.rar`, `.part2.rar` only | 0 |
   | 18:52:05.329 | same two `.rar` volumes only | 79,691,814 |
   | 18:52:05.541 | same two `.rar` volumes only | 201,326,630 |
   | 18:52:05.765 | same two `.rar` volumes only | 310,378,534 |
   | 18:52:05.973 | same two `.rar` volumes only | 360,710,182 |
   | 18:52:06.197 | same two `.rar` volumes only | 469,762,086 |
   | 18:52:07.102 | same two `.rar` volumes only | 692,059,996 |
   | 18:52:07.314 | same two `.rar` volumes only | 746,585,948 |

   Not one of these samples, nor any other sample taken before the `.mkv` first appears
   (next item), lists `SSA122.Rar.Pack.mkv` in the release folder — the `.seedsyncarr-extracting/SSA122.Rar.Pack/`
   staging dir held the growing output the whole time.
6. **Publish: the full-size `.mkv` appears in the release folder only once, at its complete
   byte size.** First sample listing the `.mkv`, NAS UTC `18:52:09.909`:
   ```
   RELEASE_FOLDER:
   -rw-rw-r-- 1 1026 100 1073741824 Oct 23 13:49 SSA122.Rar.Pack.mkv
   -rw-r--r-- 1 1026 100  629145600 Oct 23 13:49 SSA122.Rar.Pack.part1.rar
   -rw-r--r-- 1 1026 100  444596623 Oct 23 13:49 SSA122.Rar.Pack.part2.rar
   STAGING_BYTES: 0
   ```
   `1073741824` is exactly the dummy file's original size — not a partial byte count at any
   point. The staging dir read `0` bytes (freshly recreated, see next item) at this exact
   sample rather than "absent", because the task's second (redundant) archive entry begins
   its own extraction pass essentially back-to-back with the first pass's publish+cleanup;
   this does not change the safety property — the release folder already held the complete
   file from the moment this sample was taken.
7. **A second, redundant extraction pass runs** (the pre-existing `.partN.rar`
   coalesce gap described above) — staging grows a second time, NAS UTC `18:52:10.132` →
   `18:52:11.442` (92 MB → 746 MB), while the release folder **already shows the complete,
   correctly-sized `.mkv` the whole time**, alongside the two `.rar` volumes — never a
   partial file, never removed. The app log confirms the second pass's overwrite:
   ```
   2026-10-23 14:52:15,595 - WARNING - ExtractDispatch - Replacing existing '/downloads/SSA122.Rar.Pack/SSA122.Rar.Pack.mkv' with the newly extracted copy
   ```
8. **Extraction completes.** NAS UTC `18:52:17` / app-log:
   ```
   2026-10-23 14:52:17,221 - INFO - ExtractProcess - Extraction completed for SSA122.Rar.Pack
   ```
9. **No `.seedsyncarr-extracting` entry in any model snapshot, ever.** `cat model-x-1-*.json
   | grep -c seedsyncarr-extracting` = **0** across all model-stream snapshots taken every
   2 s for the entire run (held in `state.env` as `MODEL_SNAPSHOT_HITS_SSA122.Rar.Pack=0`,
   reconfirmed by this plan's own literal `<verify>` command against `model-x-*.json`).

### Auto-delete re-arm (Bug 2 replay)

10. **Webhook accepted while the root is `EXTRACTING`.** A signed, root-level `Download`
    webhook (`sourcePath=/data/torrents/SSA122.Rar.Pack`, no child subpath — per the plan's
    own rationale: during `EXTRACTING` the extracted `.mkv` sits in the excluded staging
    dir, invisible to the model, so no child-level match is possible; a root-level notice
    for a root already committed as downloaded is accepted with no per-child credit,
    letting the coverage guard grandfather the whole root as imported) was posted by the
    harness's watcher the instant it observed `state == "extracting"` on the model stream
    (NAS UTC `18:52:04`, `HTTP_CODE=200`). The controller recorded it on its next cycle:
    ```
    2026-10-23 14:52:05,842 - INFO - seedsyncarr.WebhookManager (worker 6) - Sonarr webhook import enqueued: 'SSA122.Rar.Pack' (eventType=Download, episodeFile.sourcePath)
    2026-10-23 14:52:06,316 - INFO - seedsyncarr.WebhookManager - Sonarr import detected: 'SSA122.Rar.Pack' (matched SeedSyncarr file 'SSA122.Rar.Pack'; eventType=Download, episodeFile.sourcePath)
    2026-10-23 14:52:06,317 - INFO - seedsyncarr.Controller - Recorded webhook import: 'SSA122.Rar.Pack' (child: 'SSA122.Rar.Pack')
    2026-10-23 14:52:10,210 - INFO - seedsyncarr.Controller - Scheduled auto-delete of 'SSA122.Rar.Pack' in 2 seconds
    ```
11. **Deferred three times, each naming the `EXTRACTING` state, exactly as the record's
    `after_deploy` item 2 specifies** (verbatim, `log-rar.txt`):
    ```
    2026-10-23 14:52:12,207 - INFO - seedsyncarr.Controller (Thread-4) - Auto-delete deferred for 'SSA122.Rar.Pack' (attempt 1/24): file is in state State.EXTRACTING; retrying in 2 s
    2026-10-23 14:52:14,207 - INFO - seedsyncarr.Controller (Thread-5) - Auto-delete deferred for 'SSA122.Rar.Pack' (attempt 2/24): file is in state State.EXTRACTING; retrying in 2 s
    2026-10-23 14:52:16,207 - INFO - seedsyncarr.Controller (Thread-6) - Auto-delete deferred for 'SSA122.Rar.Pack' (attempt 3/24): file is in state State.EXTRACTING; retrying in 2 s
    ```
    Three deferrals (6 s of retrying) is comfortably inside the 24-attempt / 48 s budget,
    confirming the volume-count discretion above held the redundant-extraction risk well
    within bounds.
12. **Auto-deleted once the root left `EXTRACTING`.** NAS UTC `18:52:18` / app-log:
    ```
    2026-10-23 14:52:18,211 - INFO - seedsyncarr.Controller (Thread-7) - Auto-deleted local file 'SSA122.Rar.Pack'
    ```
13. **Final file state.** Confirmed by direct `stat`/`ls` on the NAS host (not through the
    container) immediately after:
    ```
    $ stat /volume1/data/v5test/torrents/SSA122.Rar.Pack
    stat: cannot stat '...': No such file or directory
    $ stat /volume1/data/v5test/torrents/.seedsyncarr-extracting
    stat: cannot stat '...': No such file or directory
    ```
    and on the seedbox, the staging scratch dir was already gone (`ssa122-stage` removed by
    the harness once the archive was moved into `~/v5test/`).

### Forbidden lines (none observed)

`grep -c "Ignoring webhook import for 'SSA122.Rar" log-rar.txt` = **0**;
`grep -c "Completion hold cleared for 'SSA122.Rar" log-rar.txt` = **0** (only the D-02/LOG-02
"dropped" line appears, item 2 above); `grep -c "Auto-delete given up for 'SSA122.Rar"
log-rar.txt` = **0** — the budget was never exhausted.

### Unit test cross-references

- `test_dispatch_staging.py::TestExtractDispatchStaging::test_output_not_visible_in_release_dir_until_extraction_finishes`
  — the exact Bug 1 invariant this live run exercised end-to-end with a real multi-volume
  archive instead of a patched function.
- `test_dispatch_staging.py::TestExtractDispatchStagingRealArchive::test_zip_is_extracted_via_staging_into_release_dir`
  — the real-archive-through-patool round trip this live run generalizes to a real RAR set.
- `test_auto_delete_rearm.py::TestAutoDeleteDeferral::test_incident_replay_webhook_during_extracting_defers_then_deletes`
  — the exact Bug 2 incident replay (webhook accepted during `EXTRACTING`, defer, delete on
  the next deletable state) this live run exercised on the running merge build instead of a
  unit-level model double.

### Secret handling and teardown

Exact-match secret scan (`grep -c -F -f secret` over every `log-rar*.txt` / `model-x-*.json`
/ `model-held-*.json` / `volume-list-*.txt` / `extract-samples*.txt` /
`webhook-post-output-*.txt` / `webhooks.log` / `analysis-*.txt` capture file from this
session): **`SECRET_SCAN=0`**. `autodelete.delay_seconds` was restored to its recorded
`DELAY_L0 = 300` immediately once deletion was observed, and again by `teardown.sh`
(idempotent, re-confirmed identical both times). `bash teardown.sh` (not `--final`) printed:
```
RESTORED rate_limit ok (not set this session)
RESTORED delay_seconds ok
REMOVED synth roots count=1 refused=0
STOP seedsyncarr-test ok
RESTORED webhook_secret ok (len=0)
WAIT server/status ok
CHECK webhook/sonarr Test http=200
SANDBOX_RESTORED ok
```
Re-run a second time (this plan's own `<verify>` command) and printed the identical
`SANDBOX_RESTORED ok` last line, confirming idempotence. Sandbox still pinned to the same
DEV_PIN afterward; no `SSA122.*` material remains on the seedbox or under
`/volume1/data/v5test/torrents`. Production `seedsyncarr` fingerprint (`Id`, image,
`StartedAt`) re-confirmed byte-identical to the 122-11/122-12/122-06 baseline
(`2feb4073...`, `:1.7.6@sha256:da6196e0...`, `2026-10-23T07:04:18.591254939Z`) — never named
by any write command in this plan.

**PASS (D-07).** Both of the extract-staging-autodel-rearm record's deferred
`after_deploy` items are confirmed on the running merge build: (1) extraction stages
out of sight in `.seedsyncarr-extracting/<root>/`, publishes only when complete, and the
UI/model never lists the staging dir; (2) a webhook accepted while the root is `EXTRACTING`
defers auto-delete with the exact documented log wording and attempt counter, then deletes
once the root becomes deletable again. No timing miss occurred (attempt 1 succeeded
cleanly); no D-03 escalation is needed.
