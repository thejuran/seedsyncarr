# Requirements: v1.1.1 Post-Redesign Cleanup & Outstanding Work

**Milestone:** v1.1.1
**Goal:** Close all outstanding work and open issues from prior milestones — deferred UAT, pending todos, tech debt, one multiselect regression, a critical auto-delete data-loss bug, a Dependabot alert, and retroactive v1.1.0 release notes — without introducing new user-facing features.

**Version bump rationale:** Patch (v1.1.0 → v1.1.1). Only `SEC-02` is net-new capability (optional Fernet encryption, opt-in, backward-compatible); everything else is fix, validation, infra, or docs. No user-visible feature additions.

---

## v1.1.1 Requirements

### Bug Fixes (FIX)

- [ ] **FIX-01**: When the multiselect bulk-actions bar shows for a selection that includes one or more deleted files, "Re-Queue from Remote" is available in the bar. For mixed selections, the bar shows the union of applicable actions across the selection, disabling individual actions only for rows where they do not apply. Regression from v1.1.0.

- [ ] **FIX-02**: Auto-delete on a pack root does not execute while any child on disk is missing from the per-pack imported-children set. Tracks per-child import state (root, child basename) persisted across restarts, bounded, enumerates on-disk children via BFS at Timer-fire time, and skips+logs on partial coverage. Covers GH #19 (Sonarr silent-rejects leaving orphaned episodes that previously triggered pack-wide deletion).

### Deferred UAT from v1.1.0 (UAT)

- [ ] **UAT-01**: Playwright E2E suite covers per-file selection, shift-range select, page-scoped header select-all, bulk-actions-bar visibility/hiding, and each of the 5 bulk actions (Queue, Stop, Extract, Delete Local, Delete Remote). Five specs from Phase 72 deferred scope, CI-gated via `make run-tests-e2e`.

- [ ] **UAT-02**: Playwright E2E suite covers dashboard filter across every `ViewFile.Status` value (Done parent + Pending sub), URL query-param round-trip (select → URL → reload → state restored), drill-down segment expansion, and silent fallback on invalid filter values. Ten specs from Phase 73 deferred scope, CI-gated.

- [ ] **UAT-03**: Manual runtime UAT validates storage capacity tiles against a live seedbox — local disk via `shutil.disk_usage`, remote via `df -B1 <shlex.quote>` over SSH, `>1%` change gate suppresses spam updates, 80%/95% warning/danger threshold color shifts render correctly, tile hides gracefully when SSH `df` fails. Six items from Phase 74 deferred scope, executed against live infra with findings recorded.

### Security (SEC)

- [ ] **SEC-01**: Dependabot alert #3 (`basic-ftp@<=5.2.2` DoS, GHSA-rp42-5vxx-qpwr) is closed by either: (a) adding an npm override to `^5.3.0` at the root `package.json`, (b) dropping the transitive path, or (c) documenting why the code path is unreachable and dismissing with justification. Verified via `npm ls basic-ftp` and `gh api dependabot/alerts`.

- [ ] **SEC-02**: Config file supports optional Fernet encryption at rest for `api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, and `remote_password`. Keyfile generated on first run with restrictive permissions (0600), decrypt is transparent in `config.py` read path, plaintext values detected at startup are encrypted in place, and users can disable via a config flag to allow manual editing. Backward-compatible with existing plaintext installs.

### Test Infrastructure (TEST)

- [ ] **TEST-01**: CI Python test run produces zero pytest-cache warnings (`-p no:cacheprovider` suppresses the 3 cache-write warnings from the read-only `/src` mount) and zero `webob` `cgi` deprecation warnings (update `webob` or its consumer `bottle` to a version that no longer imports the deprecated `cgi` module). Verified by inspecting CI log stderr.

- [ ] **TEST-02**: Main Playwright E2E suite fails the test run on any CSP violation logged to the browser console. Implemented via a shared fixture that registers `page.on('console')` and the `securitypolicyviolation` DOM event, collects violations, and fails in `afterEach`. Verified by seeding an inline script that violates CSP and asserting the spec fails.

### Tech Debt (TECH)

- [ ] **TECH-01**: `make run-tests-python` builds and runs to completion on arm64 (Apple Silicon) — either by sourcing `rar` from a package that ships arm64 binaries, replacing `rar` with an arm64-available substitute (`unrar`, `unar`), or conditionally skipping the `rar` install on arm64 with a matching skip of any tests that require it. CI amd64 behavior unchanged.

- [ ] **TECH-02**: `WAITING_FOR_IMPORT` enum value is either wired up to the business logic that should set it (with tests) or removed from the model along with any dead code that references it. Chosen resolution is recorded in `PROJECT.md` Key Decisions.

### Documentation (DOCS)

- [ ] **DOCS-01**: v1.1.0 release notes exist in the CHANGELOG and as a GitHub Release (tag `v1.1.0`) with a categorized summary of Phases 62-74 — UI redesign, per-file selection + bulk bar, dashboard filter + URL persistence, storage capacity tiles, SCSS consolidation. Retroactively filed for the 2026-04-19 release that shipped without notes.

---

## Future Requirements

(Deferred to later milestones — not Out of Scope, just not this cycle.)

_None captured at this time._

---

## Out of Scope

- **Rate limiting on all HTTP endpoints** — single-user tool; addressed at reverse proxy per project constraint.
- **Lidarr/Readarr support** — defer to future milestone.
- **Bootstrap @import → @use migration** — blocked until Bootstrap 6.
- **Angular → htmx/Tailwind rewrite** — visual kinship via design patterns, not framework.
- **OAuth / multi-user auth** — single-user self-hosted tool.
- **HTTPS termination** — handled by reverse proxy.
- **New favicon/logo design** — keep existing favicon.png.

---

## Traceability

_Filled by roadmapper — maps each REQ-ID to its owning phase._

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FIX-01 | TBD   | Pending |
| FIX-02 | TBD   | Pending |
| UAT-01 | TBD   | Pending |
| UAT-02 | TBD   | Pending |
| UAT-03 | TBD   | Pending |
| SEC-01 | TBD   | Pending |
| SEC-02 | TBD   | Pending |
| TEST-01 | TBD  | Pending |
| TEST-02 | TBD  | Pending |
| TECH-01 | TBD  | Pending |
| TECH-02 | TBD  | Pending |
| DOCS-01 | TBD  | Pending |

---

*Created: 2026-04-20*
