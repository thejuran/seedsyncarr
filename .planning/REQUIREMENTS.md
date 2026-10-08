# Requirements: SeedSyncarr

**Defined:** 2026-10-08
**Core Value:** Reliable file sync from seedbox to local with automated media library integration
**Milestone:** v1.7.4 Safety Patch — design spec `docs/superpowers/specs/2026-10-08-safety-patch-design.md`

## v1 Requirements

### Import Safety (deletion path)

- [x] **IMPORT-01**: A webhook import whose file name matches more than one distinct model path — across releases, roots differing only by case, a root name equal to a child basename elsewhere, or repeated basenames within one release (e.g. `Pack/Disc1/movie.mkv` + `Pack/Disc2/movie.mkv`) — is rejected: no imported record, no per-child coverage credit, no import badge, no auto-delete timer, and one sanitized warning naming the candidate roots.
- [x] **IMPORT-02**: A webhook import whose file name matches exactly one distinct model path (including repeated references to that same path) behaves exactly as before: recorded, badged, and armed for auto-delete when evidence allows.

### Transfer-State Safety

- [ ] **XFER-01**: A pget job with no data line yet never consumes the following job's header; every job in `jobs -v` output appears in the parsed status with its correct name and state (the parser's other next-line-consuming sites are audited for the same flaw).
- [ ] **XFER-02**: When LFTP status cannot be parsed, it is reported as *unavailable* (never as an empty job list) and actively transferring files keep their last-known state and protection — nothing is re-queued or deleted because of the failure; no downstream consumer converts unavailable back into "no jobs".
- [ ] **XFER-03**: The existing status-error boundary is preserved exactly: failures 1..`MAX_CONSECUTIVE_STATUS_ERRORS` are tolerated (each reported unavailable) and the next failure raises; a successful parse resets the counter; a genuinely empty status still clears active state.
- [ ] **XFER-04**: A file's remote size is considered stable only on the clock of successful remote scans — failed scans spanning the stability window never make a file auto-queue eligible; the UI "last scan" timestamp keeps its current meaning.
- [ ] **XFER-05**: The local-size stability gate likewise advances only on successful local scans.

### Durable State

- [ ] **PERSIST-01**: Saving settings.cfg, the controller persist, or the auto-queue persist never leaves a truncated or partial file: any failure before the atomic replace (serialization, temp creation, write, fsync, replace) leaves the original byte-for-byte intact and removes the temp file.
- [ ] **PERSIST-02**: A successful save produces the correct content with `0600` permissions; after the `os.replace` commit point the new file is committed and the containing directory is fsynced best-effort (a directory-fsync failure is logged, not raised).

### Release

- [ ] **REL-01**: Release 1.7.4 ships only after: each targeted regression fails against the old behavior and passes with its fix; the full Python suite and `ruff check src/python/` pass; the built release image passes a smoke test (startup, transfer status, settings persistence, restart); and the `:1.7.4` tag is deployed to the NAS with startup and config loading verified — a post-deploy scanner error is accepted as the known warm-up condition only after a subsequent successful scan confirms recovery.

## v2 Requirements

- **IMPORT-F1**: Accept a webhook import whose payload file size equals the remote release size (backlog 999.1).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Path-mapping redesign for webhook imports | Patch conservatively rejects ambiguity; full path mapping is a larger change |
| Persistence migration / format changes | Atomic writes only; on-disk format unchanged |
| Backup system / load-side recovery changes | Existing corrupt-file backup-and-reset behavior stays as-is |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMPORT-01 | Phase 116 | Complete |
| IMPORT-02 | Phase 116 | Complete |
| XFER-01 | Phase 117 | Pending |
| XFER-02 | Phase 117 | Pending |
| XFER-03 | Phase 117 | Pending |
| XFER-04 | Phase 117 | Pending |
| XFER-05 | Phase 117 | Pending |
| PERSIST-01 | Phase 118 | Pending |
| PERSIST-02 | Phase 118 | Pending |
| REL-01 | Phase 118 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10 (100% — no orphans, no duplicates)
- Phase 116 Import Safety: IMPORT-01, IMPORT-02
- Phase 117 Transfer-State Safety: XFER-01, XFER-02, XFER-03, XFER-04, XFER-05
- Phase 118 Durable State: PERSIST-01, PERSIST-02, REL-01 (release gate = milestone close)

---
*Requirements defined: 2026-10-08*
*Last updated: 2026-10-08 after roadmap creation (traceability mapped to Phases 116-118)*
