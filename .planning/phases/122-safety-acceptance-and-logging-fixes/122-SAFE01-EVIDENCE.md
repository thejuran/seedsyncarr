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
