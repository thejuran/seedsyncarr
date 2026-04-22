# Phase 82: Release Prep (Retro v1.1.0 Notes + v1.1.1 Tag) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 82-release-prep-retro-v110-notes-v111-tag
**Areas discussed:** Changelog style, GitHub Release format, Release artifacts, Version bump scope

---

## Changelog Style

| Option | Description | Selected |
|--------|-------------|----------|
| By category | Keep a Changelog standard sections: Added, Changed, Fixed, Security. Consistent with v1.0.0 entry. | ✓ |
| By phase | One section per phase like the v1.1.0-dev pre-release. More granular but less standard. | |
| Hybrid | Keep a Changelog categories with phase references in parentheses. | |

**User's choice:** By category
**Notes:** User emphasized changelog should be written with a user in mind, not too in the weeds. Entries should describe user-facing outcomes, not implementation details.

---

## GitHub Release Format

| Option | Description | Selected |
|--------|-------------|----------|
| Match changelog | Same categorized content from CHANGELOG.md as release body. Brief intro + categories + "Full changelog" link. | ✓ |
| Brief + link | Short 2-3 sentence summary with link to CHANGELOG.md. Like v1.0.0 style. | |
| Detailed with screenshots | Full list plus embedded screenshots. Most informative but requires assets. | |

**User's choice:** Match changelog
**Notes:** None

---

## Release Artifacts

| Option | Description | Selected |
|--------|-------------|----------|
| Docker only | Tag push triggers Docker publish (already wired). Drop Deb requirement. | |
| Docker + Deb | Add Deb packaging step to CI. Both publish on tag push. | ✓ |
| Docker + manual Deb | Docker via CI, manually build and attach .deb. | |

**User's choice:** Docker + Deb

### Follow-up: Deb target

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Release asset | CI builds .deb on tag push, attaches to GitHub Release. No apt repo needed. | ✓ |
| GitHub Release + apt repo | Same plus publish to GitHub Pages-hosted apt repository. | |
| You decide | Claude picks simplest approach. | |

**User's choice:** GitHub Release asset
**Notes:** User clarified that Docker and Deb should release in tandem from the same tag push — both triggered by the same CI run.

---

## Version Bump Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Straight to 1.1.1 | Bump 1.0.0 → 1.1.1 in one commit. v1.1.0 tag stays as-is. | ✓ |
| Bump 1.1.0 first, then 1.1.1 | Two commits for historical accuracy. | |
| You decide | Claude picks cleanest approach. | |

**User's choice:** Straight to 1.1.1
**Notes:** None

---

## Claude's Discretion

- Debian control file structure and metadata
- Exact categorization of changes into Keep a Changelog sections
- CI job structure for Deb build
- Whether to delete the v1.1.0-dev pre-release
- Order of operations

## Deferred Ideas

None — discussion stayed within phase scope
