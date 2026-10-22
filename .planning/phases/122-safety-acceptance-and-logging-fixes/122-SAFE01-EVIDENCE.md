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
