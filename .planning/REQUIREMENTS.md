# Requirements: SeedSyncarr v1.0.0 Rebrand

**Defined:** 2026-04-08
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.0.0 Requirements

Requirements for SeedSyncarr rebrand launch.

### Rebrand

- [ ] **RBND-01**: User can pull `ghcr.io/thejuran/seedsyncarr` Docker image and run the app
- [ ] **RBND-02**: All UI text, page titles, and about page show "SeedSyncarr" (not "SeedSync")
- [ ] **RBND-03**: CI pipeline runs in new repo with tests, E2E, Docker build all green
- [ ] **RBND-04**: Debian package installs as `seedsyncarr` with `~/.seedsyncarr` config directory
- [ ] **RBND-05**: v1.0.0 tag exists on new repo with published Docker images (amd64 + arm64)
- [ ] **RBND-06**: Old `thejuran/seedsync` repo is archived with pointer to SeedSyncarr

### Hardening

- [ ] **HARD-01**: Zero verbose/unnecessary comments or docstrings in source code
- [ ] **HARD-02**: No planning docs, modernization reports, or analysis files in repo
- [ ] **HARD-03**: Test coverage has no meaningful gaps; assertions verify behavior (not just "no crash")
- [ ] **HARD-04**: E2E tests cover real user workflows including unhappy paths
- [ ] **HARD-05**: Code reads as hand-written — no generated-looking patterns, consistent style throughout
- [ ] **HARD-06**: Zero open Dependabot alerts, zero lint warnings (Python + TypeScript)

### Presentation

- [ ] **PRES-01**: README leads with value prop, screenshot, and Docker Compose one-liner install
- [ ] **PRES-02**: README has CI badge, version badge, Docker pulls badge, license badge
- [ ] **PRES-03**: README cross-links to Triggarr
- [ ] **PRES-04**: MkDocs docs site live at `thejuran.github.io/seedsyncarr`
- [ ] **PRES-05**: Docs include installation guide, configuration reference, FAQ/troubleshooting
- [ ] **PRES-06**: Docs include Sonarr/Radarr setup guide as flagship page
- [ ] **PRES-07**: GitHub Discussions enabled with support category
- [ ] **PRES-08**: Issue templates (YAML forms) for bug report and feature request
- [ ] **PRES-09**: CONTRIBUTING.md, SECURITY.md, and CHANGELOG.md present
- [ ] **PRES-10**: Repo has descriptive topic tags (*arr, selfhosted, seedbox, etc.)

### Launch

- [ ] **LNCH-01**: r/selfhosted announcement post published ("I built X to solve Y" format)
- [ ] **LNCH-02**: *arr community outreach (Servarr Discord, r/sonarr, r/radarr) staggered 24-48h after Reddit
- [ ] **LNCH-03**: awesome-selfhosted PR submitted (deferred to August 2026 per 4-month rule)
- [ ] **LNCH-04**: Awesomarr PR submitted (deferred until 50+ stars)

### Polish

- [ ] **PLSH-01**: All minor/patch Dependabot PRs merged (mkdocs-material, pyinstaller, pytest-cov)
- [ ] **PLSH-02**: Major Dependabot bumps reviewed and resolved (pytest 7→9, testfixtures 10→11, Angular npm bundle)
- [ ] **PLSH-03**: All dependency updates pass CI with zero test failures
- [ ] **PLSH-04**: Web app favicon replaced with new branding icon (green/orange arrow mark)
- [ ] **PLSH-05**: MkDocs docs site logo and favicon replaced with new branding
- [ ] **PLSH-06**: GitHub repo social preview set to branding banner with tagline
- [ ] **PLSH-07**: README header includes project logo

## Future Requirements

- **LIDARR-01**: Lidarr integration (same *arr webhook pattern as Sonarr/Radarr)
- **READARR-01**: Readarr integration (same *arr webhook pattern)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Lidarr/Readarr support | Defer to post-launch milestone |
| Angular/htmx rewrite | Visual kinship via design patterns, not framework |
| OAuth/multi-user auth | Single-user self-hosted tool |
| New logo/favicon design | Moved to Phase 61 (branding assets provided) |
| Git history migration | Fresh start — no history carries over |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RBND-01 | Phase 53 | Pending |
| RBND-02 | Phase 53 | Pending |
| RBND-03 | Phase 53 | Pending |
| RBND-04 | Phase 53 | Pending |
| RBND-05 | Phase 53 | Pending |
| RBND-06 | Phase 54 | Pending |
| HARD-01 | Phase 55 | Pending |
| HARD-02 | Phase 55 | Pending |
| HARD-05 | Phase 55 | Pending |
| HARD-06 | Phase 55 | Pending |
| HARD-03 | Phase 56 | Pending |
| HARD-04 | Phase 56 | Pending |
| PRES-01 | Phase 57 | Pending |
| PRES-02 | Phase 57 | Pending |
| PRES-03 | Phase 57 | Pending |
| PRES-07 | Phase 57 | Pending |
| PRES-08 | Phase 57 | Pending |
| PRES-09 | Phase 57 | Pending |
| PRES-10 | Phase 57 | Pending |
| PRES-04 | Phase 58 | Pending |
| PRES-05 | Phase 58 | Pending |
| PRES-06 | Phase 58 | Pending |
| LNCH-01 | Phase 59 | Pending |
| LNCH-02 | Phase 59 | Pending |
| LNCH-03 | Phase 59 | Pending |
| LNCH-04 | Phase 59 | Pending |
| PLSH-01 | Phase 60 | Pending |
| PLSH-02 | Phase 60 | Pending |
| PLSH-03 | Phase 60 | Pending |
| PLSH-04 | Phase 61 | Pending |
| PLSH-05 | Phase 61 | Pending |
| PLSH-06 | Phase 61 | Pending |
| PLSH-07 | Phase 61 | Pending |

**Coverage:**
- v1.0.0 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-09 — added PLSH-01 to PLSH-07 for Phases 60-61*
