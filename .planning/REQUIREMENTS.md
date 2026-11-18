# Requirements: SeedSyncarr — v1.8.1 Configuration and Shutdown Correctness

**Defined:** 2026-11-18
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.8.1 Requirements

Scope agreed 2026-11-18 (ROADMAP "Next milestone"). Research skipped: small, code-confirmed fixes plus documentation. Check current code before planning each fix.

### Documentation (DOC)

Absorbs backlog item 999.6. README.md only; no application behavior changes.

- [ ] **DOC-01**: User can reach all six repository guides (`docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`) from a prominent README Documentation section; the installation section links repository guides instead of website-only docs; every relative link resolves.
- [ ] **DOC-02**: User reading the README sees accurate default security posture, replacing "Security by default": API authentication off when `api_token` is empty, webhook verification off when `webhook_secret` is empty, `webhook_require_secret` defaults to `False`, encryption at rest off by default (stored secrets plaintext). Defaults rechecked against current code and SECURITY.md at implementation time.
- [ ] **DOC-03**: User reading the README sees HMAC and cleanup claims stated with their conditions: absolute "never deletes" promises replaced by an explanation of import confirmation, optional pruning (off by default) and the safety delay; the whole README reviewed for remaining unconditional claims.
- [ ] **DOC-04**: User following Quick Start is told that the Docker examples publish port 8800 on all host interfaces, that untrusted access needs an authenticating reverse proxy and restricted network access, and that the API token does not protect the UI (which contains that token).

### Arr key handling (ARR)

Code-confirmed mismatch: Test Connection strips the key (`src/python/web/handler/config.py`), queue requests use the stored value as-is. Recurrence in production unknown.

- [ ] **ARR-01**: A Sonarr/Radarr API key entered with leading/trailing whitespace is saved normalized, using the same rule as Test Connection.
- [ ] **ARR-02**: A previously saved whitespace-padded key is normalized when read for queue requests, so Test Connection and queue completion checks agree for the same stored key.
- [ ] **ARR-03**: An empty or invalid key still fails safely in queue completion checks (no unsafe import or deletion decision), and no key value appears in logs.

### Web-service shutdown (WEB)

Confirmed 2026-11-18: an injected `app.stop` failure in `WebAppJob.cleanup` (`src/python/web/web_app_job.py`) skips `server.stop` and `thread.join`.

- [ ] **WEB-01**: When any one web-service cleanup step (`app.stop`, `server.stop`, `thread.join`) fails, the remaining steps still run and the failure is logged.
- [ ] **WEB-02**: Cleanup after a partial startup (server never created, or thread never started) completes without raising, with tests showing clean termination.

### Release (REL)

- [ ] **REL-07**: Release 1.8.1 passes its gates: fail-before/pass-after regressions for ARR and WEB, full test suite, whole-tree `ruff check src/python/`, release CI; open Dependabot alerts and PRs triaged and rolled in by scope and surfaced to the owner before the tag.
- [ ] **REL-08**: The 1.8.1 release image is smoke-tested by digest (setup, queue completion check with a whitespace-padded key, stop/restart), then deployed to NAS production pinned to `:1.8.1`, with a successful scan after deploy.

## Future Requirements

Conditional milestones in ROADMAP.md, activated only on evidence:

- Performance and Usability: bounded scanner investigation; measured UI/webhook efficiency improvements.
- Pipeline Visibility: explain import and cleanup progress from existing status data.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Transfer-architecture replacement | Corrective milestone; boundaries agreed 2026-11-18 |
| Runtime auto-restart expansion | Not a demonstrated gap |
| URL normalization beyond API keys | Only the key mismatch is code-confirmed |
| Blanket test project | Targeted regressions only |
| UI redesign / UI changes | Deferred; UI-REDESIGN brief is not an approved scope |
| Speculative optimization | Performance work requires baseline evidence first |
| Changes to completion/import/deletion safeguards | Must remain intact |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|

**Coverage:**
- v1.8.1 requirements: 11 total
- Mapped to phases: 0
- Unmapped: 11 ⚠️

---
*Requirements defined: 2026-11-18*
*Last updated: 2026-11-18 after initial definition*
