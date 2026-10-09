# Phase 118: Durable State - Context

**Gathered:** 2026-10-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Two parts, in order:

1. **Code (PERSIST-01, PERSIST-02):** `Persist.to_file` (`src/python/common/persist.py:47`, sole writer of `settings.cfg`, controller persist, auto-queue persist) writes atomically: serialize (`to_str()`) before touching the filesystem → `0600` temp file in the target's directory → write/flush/fsync → `os.replace(temp, target)` as the commit point → best-effort directory fsync (logged, not raised). Any failure before or during `os.replace` leaves the original byte-for-byte intact, removes the temp file, and raises. On-disk format, load-side behavior, and the corrupt-file backup-and-reset path are unchanged.
2. **Release gate (REL-01):** this is the milestone's final code phase, so it closes with the 1.7.4 release gate across Phases 116-118, ending with the tested `:1.7.4` image running on the NAS.

Out of scope (spec): path-mapping redesign, persistence migration or format changes, backup systems, load-side recovery changes.
</domain>

<decisions>
## Implementation Decisions

### Release flow (REL-01)
- **D-01:** Order is **tag → CI-built image → smoke-test that exact image → deploy the same digest to the NAS**. Code + regression evidence first; then merge to main and push the annotated `v1.7.4` tag; CI builds and pushes `ghcr.io/thejuran/seedsyncarr:1.7.4`; smoke-test that pulled image (startup, transfer status, settings persistence, restart); then deploy the identical digest to the NAS (owner note: "deploy to the NAS the exact image that passed testing (same tag/digest)").
- **D-02:** **One owner approval checkpoint before pushing the tag** (the tag push publishes the release). The plan must include it as a `checkpoint:human-verify`/decision gate — the executor never pushes the tag or deploys unattended.
- **D-03:** NAS deploy pins compose to `:1.7.4` (never `:dev`), via `ssh nas` and the absolute `sudo /usr/local/bin/docker compose ...` path. Flag the wud `watch.digest` side effect. A post-deploy scanner error is accepted as the known warm-up condition **only after** a subsequent successful scan in the log confirms recovery.
- **D-04:** Version bump to `1.7.4` in `package.json` and `src/python/pyproject.toml` (both `version` lines) lands before the tag.

### Merge to main
- **D-05:** Push local `main` (including the 11 unpushed planning commits 7f7be28..c734c10), then **merge `safety-patch-1.7.4` into `main` preserving history**, and tag from `main`. No squash — evidence files reference per-fix commit SHAs.

### Rollback runbook
- **D-06:** Write a **full rollback runbook into `release-notes.md` for 1.7.4**: before upgrade, back up the three persist files; to roll back to 1.7.3 — disable auto-delete, stop the service, restore the backups, re-pin `:1.7.3`, keep auto-delete off until imports are reconciled (reason: Phase 116's duplicate-basename skip means 1.7.3 could read a missing import record as "fully imported").
- **D-07:** Release notes also call out the Phase 117 user-visible change: pressing Stop while LFTP status is temporarily unavailable now returns an error (retry once status recovers) instead of a false success. Release notes follow the existing plain-language `release-notes.md` style ("What changed for you" / "Should you update?").

### Carried forward (locked by spec / prior phases)
- Each targeted regression must be shown to fail against the old behavior before its fix (REL-01 gate 1) — same RED → fix → GREEN evidence format as `117-REL01-EVIDENCE.md`.
- CI gate: full Python suite + `ruff check src/python/` whole-tree + coverage `fail_under` ≥ 88. CI Docker is the full-suite authority; the local host suite hangs in `test_extract_process.py` (use the established deselect/ignore list).
- Known deferred item: backlog 999.2 (LFTP command-stream resync after timeout) stays out of 1.7.4.

### Claude's Discretion
- Temp-file naming/creation mechanism (e.g. `tempfile.mkstemp(dir=...)`), and how each failure point is injected in tests.
- Smoke-test mechanics (docker run against the pulled image with a scratch config dir).
- CHANGELOG.md entry wording.

</decisions>

<specifics>
## Specific Ideas

- Owner planning note: "Run the REL-01 release gates against the combined changes from all three phases, and deploy to the NAS the exact image that passed testing (same tag/digest)."
- Owner rule (memory): never dismiss a post-deploy scanner error automatically — confirm a later clean scan.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Fix contract and release gate
- `docs/superpowers/specs/2026-10-08-safety-patch-design.md` §Phase C and §Release gate (1.7.4) — atomic-write contract, failure contract, regression tests, release gate steps
- `.planning/REQUIREMENTS.md` — PERSIST-01, PERSIST-02, REL-01
- `.planning/ROADMAP.md` §"Phase 118: Durable State" — success criteria 1-5, owner planning notes

### Prior evidence and deferred items
- `.planning/phases/116-import-safety/116-REL01-EVIDENCE.md` and `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md` — RED/GREEN evidence format; REL-01 must cover every regression from 116-118
- `.planning/phases/117-transfer-state-safety/117-07-SUMMARY.md` — Stop behavior change to document; deferred parser sites
- `release-notes.md` — style for the 1.7.4 notes + rollback runbook
- `.github/workflows/ci.yml` — tag-triggered image build/push to GHCR

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Persist` base class (`src/python/common/persist.py`): abstract `to_str()`/`from_str()`; `to_file` is the single write path, currently `open(path, "w")` + write + `os.chmod(0o600)`.

### Established Patterns
- Phase 116/117 evidence pattern: RED tests committed first, RED evidence recorded against unfixed code, fix, GREEN evidence; whole-tree ruff; host suite with documented ignores.

### Integration Points
- All three persisted files go through `Persist.to_file`; callers unchanged.
- Release: `package.json` + `src/python/pyproject.toml` versions; `release-notes.md`; `CHANGELOG.md`; GHCR image via CI on `v*` tag; NAS compose at `/volume1/docker/docker-compose.yml`, container `seedsyncarr`, logs at `/volume1/docker/seedsync/log`.

</code_context>

<deferred>
## Deferred Ideas

- Backlog 999.2 — LFTP command-stream resync after timeout (not in 1.7.4).

</deferred>

---

*Phase: 118-durable-state*
*Context gathered: 2026-10-09*
