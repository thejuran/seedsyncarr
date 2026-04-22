# Phase 82: Release Prep (Retro v1.1.0 Notes + v1.1.1 Tag) - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Write retroactive v1.1.0 release notes, bump all version strings to 1.1.1, add Deb packaging to CI, and tag v1.1.1 with a categorized changelog covering every milestone requirement.

</domain>

<decisions>
## Implementation Decisions

### Changelog Style
- **D-01:** Use Keep a Changelog standard sections (Added, Changed, Fixed, Security) — no per-phase breakdowns, no phase references.
- **D-02:** Entries must be user-facing — describe what changed from the user's perspective, not internal implementation details. Avoid jargon like "SCSS consolidation" in favor of descriptions like "Unified color theme across all pages."

### GitHub Release Format
- **D-03:** GitHub Release body mirrors the CHANGELOG.md entry for each version. Add a brief intro line summarizing the release, then the categorized list, then a "Full changelog" link.
- **D-04:** Both v1.1.0 and v1.1.1 get GitHub Releases. v1.1.0 tag already exists — create the Release on the existing tag. v1.1.1 gets a new tag + Release.

### Release Artifacts
- **D-05:** Docker images and .deb package publish from the same CI tag-push trigger. Docker already wired via `publish-docker-image` job; add a new CI job for Deb packaging.
- **D-06:** .deb attached as a GitHub Release asset (no apt repository). Built in CI, uploaded via `gh release upload`.
- **D-07:** .deb targets amd64. ARM64 Deb is not required (Docker covers arm64).

### Version Bump
- **D-08:** Bump straight from 1.0.0 → 1.1.1 in a single commit. No retroactive 1.1.0 version bump — the v1.1.0 tag stays on its existing commit as-is.
- **D-09:** Files to bump: `package.json` (root), `src/angular/package.json`, `src/python/pyproject.toml`, and `debian/control` (new file created for Deb packaging).

### Claude's Discretion
- Debian control file structure and metadata (package name, description, dependencies, maintainer)
- Exact categorization of each v1.1.0 and v1.1.1 change into Keep a Changelog sections
- CI job structure for Deb build (which runner, build steps, artifact upload)
- Whether to delete the `v1.1.0-dev` pre-release after v1.1.0 proper is published
- Order of operations (changelog first vs version bump first vs tag first)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Release & CI
- `.github/workflows/ci.yml` — Current CI pipeline; `publish-docker-image` job (line 149) is the model for the new Deb job
- `Makefile` — Docker image build/release targets (`docker-image-release`)
- `CHANGELOG.md` — Existing changelog with v1.0.0 entry (the style template)

### Version Files
- `package.json` — Root package.json, currently at `1.0.0`
- `src/angular/package.json` — Angular app version, currently at `1.0.0`
- `src/python/pyproject.toml` — Python package version, currently at `1.0.0`
- `src/angular/src/app/common/version.ts` — Reads version from package.json at runtime (no direct edit needed)

### Existing Releases (for format reference)
- GitHub Release `v1.0.0` — Brief feature-list format with "See README" link
- GitHub Release `v1.1.0-dev` — Pre-release with per-phase breakdown (NOT the target format)

### Requirements
- `.planning/REQUIREMENTS.md` — DOCS-01 is the owning requirement; full v1.1.1 requirement list for changelog content
- `.planning/ROADMAP.md` §Phase 82 — Success criteria (5 items)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CI `publish-docker-image` job: model for the new Deb publish job (same `if: startsWith(github.ref, 'refs/tags/v')` trigger)
- `Makefile` targets: `docker-image-release` shows the build/push pattern

### Established Patterns
- CI uses `ubuntu-latest` runners, `actions/checkout@v4`, `docker/setup-buildx-action@v3`
- Release naming: `v1.0.0 — SeedSyncarr` (title format)
- Changelog: Keep a Changelog with comparison links at bottom

### Integration Points
- Tag push triggers: `publish-docker-image` (Docker) + new Deb job (to be added)
- `gh release create` for GitHub Release creation
- Version consistency: root `package.json` version flows to Angular app via `version.ts`

</code_context>

<specifics>
## Specific Ideas

- Changelog wording should be user-facing, not developer-facing. "New file selection and bulk actions" not "Implemented ViewFileSelectionService with BehaviorSubject-based state management."
- v1.1.0 covers Phases 62-74: UI redesign (Triggarr Style), per-file selection + bulk bar, dashboard filter + URL persistence, storage capacity tiles
- v1.1.1 covers 12 requirements: FIX-01, FIX-02, UAT-01–03, SEC-01–02, TEST-01–02, TECH-01–02, DOCS-01

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 82-release-prep-retro-v110-notes-v111-tag*
*Context gathered: 2026-04-22*
