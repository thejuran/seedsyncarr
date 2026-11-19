# Requirements: SeedSyncarr — v1.8.1 Configuration and Shutdown Correctness

**Defined:** 2026-11-18
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.8.1 Requirements

Scope agreed 2026-11-18 (ROADMAP "Next milestone"). Research skipped: small, code-confirmed fixes plus documentation. Check current code before planning each fix.

### Documentation (DOC)

Absorbs backlog item 999.6. README.md only; no application behavior changes.

- [x] **DOC-01**: User can reach all six repository guides (`docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`) from a prominent README Documentation section; the installation section links repository guides instead of website-only docs; every relative link resolves.
- [x] **DOC-02**: User reading the README sees accurate default security posture, replacing "Security by default": API authentication off when `api_token` is empty, webhook verification off when `webhook_secret` is empty, `webhook_require_secret` defaults to `False`, encryption at rest off by default (stored secrets plaintext). Defaults rechecked against current code and SECURITY.md at implementation time.
- [x] **DOC-03**: User reading the README sees HMAC and cleanup claims stated with their conditions: absolute "never deletes" promises replaced by an explanation of import confirmation, optional pruning (off by default) and the safety delay; the whole README reviewed for remaining unconditional claims.
- [x] **DOC-04**: User following Quick Start is told that the Docker examples publish port 8800 on all host interfaces, that untrusted access needs an authenticating reverse proxy and restricted network access, and that the API token does not protect the UI (which contains that token).

### Arr key handling (ARR)

Code-confirmed mismatch: Test Connection strips the key (`src/python/web/handler/config.py`), queue requests use the stored value as-is. Recurrence in production unknown.

- [ ] **ARR-01**: A Sonarr/Radarr API key entered with leading/trailing whitespace is saved normalized, using the same rule as Test Connection.
- [ ] **ARR-02**: A previously saved whitespace-padded key works for queue requests without the user resaving it (normalized on read); save, Test Connection and queue completion checks use one consistent normalization rule.
- [ ] **ARR-03**: An empty or invalid key still fails safely in queue completion checks (no unsafe import or deletion decision), and no key value appears in logs.

### Web-service shutdown (WEB)

Confirmed 2026-11-18: an injected `app.stop` failure in `WebAppJob.cleanup` (`src/python/web/web_app_job.py`) skips `server.stop` and `thread.join`.

- [ ] **WEB-01**: When any one web-service cleanup step (`app.stop`, `server.stop`, `thread.join`) fails, the remaining steps still run and the failure is logged.
- [ ] **WEB-02**: Cleanup after a partial startup (server never created, or thread never started) completes without raising; after any failure, cleanup attempts every applicable step and terminates cleanly, with tests showing it.

### Release (REL)

- [ ] **REL-07**: Release 1.8.1 passes its gates: fail-before/pass-after regressions for ARR and WEB, full test suite, whole-tree `ruff check src/python/`, release CI; dependency work limited to triage and justified fixes: open Dependabot alerts and PRs triaged and surfaced to the owner before the tag, only justified fixes rolled in.
- [ ] **REL-08**: The 1.8.1 release image is smoke-tested by digest (setup, queue completion check with a whitespace-padded key, stop/restart), then deployed to NAS production using that exact smoke-tested image digest (`:1.8.1@sha256:…`), followed by a successful scan and queue check and owner confirmation.

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
| DOC-01 | Phase 127 | Complete |
| DOC-02 | Phase 127 | Complete |
| DOC-03 | Phase 127 | Complete |
| DOC-04 | Phase 127 | Complete |
| ARR-01 | Phase 128 | Pending |
| ARR-02 | Phase 128 | Pending |
| ARR-03 | Phase 128 | Pending |
| WEB-01 | Phase 129 | Pending |
| WEB-02 | Phase 129 | Pending |
| REL-07 | Phase 130 | Pending |
| REL-08 | Phase 130 | Pending |

**Coverage:**
- v1.8.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-18*
*Last updated: 2026-11-18 after roadmap creation (Phases 127–130; 11/11 requirements mapped)*
