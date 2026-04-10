# Phase 61: Branding Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 61-branding-integration
**Areas discussed:** Favicon, Docs logo, Social preview, README logo, README layout, Favicon sizes, Source assets, Docs build

---

## Favicon (web + docs)

| Option | Description | Selected |
|--------|-------------|----------|
| Square mark (d29fb7d4) | 1024×1024 arrow-mark on dark bg, no rounding — cleanest for browser tab | |
| Rounded mark (d91ceeb2) | 1024×1024 arrow-mark with rounded corners — reads as app icon | |
| Use both: square = favicon, rounded = apple-touch-icon | Best of both; adds `<link rel="apple-touch-icon">`. Covers all platforms. | ✓ |

**User's choice:** Use both — square for favicon set, rounded for apple-touch-icon.
**Notes:** Dual-asset strategy lets iOS home-screen icons be rounded (native look) while keeping browser-tab favicons crisp at small sizes.

---

## Docs site logo (MkDocs Material)

| Option | Description | Selected |
|--------|-------------|----------|
| Horizontal wordmark dark (13559cd8) | Arrow + "SeedSyncarr" on dark bg — fits docs dark theme | ✓ |
| Arrow-mark only (d29fb7d4) | Just the square icon — loses wordmark | |
| Horizontal wordmark white (9da43036) | White bg version — only if docs is light-mode default | |

**User's choice:** Horizontal wordmark dark.
**Notes:** MkDocs Material theme for this docs site is dark-first, so the dark-bg wordmark matches the header. Full brand name visible.

---

## GitHub social preview

| Option | Description | Selected |
|--------|-------------|----------|
| Banner with tagline (1874209b) | 1584×672, arrow + wordmark + full product tagline — closest to 2:1 | ✓ |
| Hero with app-icon (3b77fb04) | 1376×768, stylized vertical hero | |

**User's choice:** Banner with tagline.
**Notes:** Social banner communicates the full product value proposition in a single image — better for cold link shares on Reddit / HN / *arr forums.

---

## README logo (light/dark mode)

| Option | Description | Selected |
|--------|-------------|----------|
| Both light + dark via `<picture>` | Uses 9da43036 (white bg) for light, 13559cd8 (dark bg) for dark via `prefers-color-scheme` | ✓ |
| Dark only (13559cd8) | Single image — simpler markdown | |
| Arrow-mark only (d29fb7d4) | Just the square icon, centered | |

**User's choice:** Both light + dark via `<picture>`.
**Notes:** GitHub's `<picture>` + `prefers-color-scheme` pattern is well-supported and gives a polished experience to both theme preferences.

---

## README layout (logo position)

| Option | Description | Selected |
|--------|-------------|----------|
| Logo above screenshot | Centered logo first, existing dashboard screenshot below | ✓ |
| Logo replaces screenshot | Logo only, drop screenshot | |
| Logo to left of title heading | Smaller inline logo | |

**User's choice:** Logo above screenshot.
**Notes:** Preserves the Phase 57 README structure (screenshot-first product visual) while adding branding as the literal first impression.

---

## Favicon sizes

| Option | Description | Selected |
|--------|-------------|----------|
| Single 512×512 PNG per target | Simplest; browsers scale down | |
| Multi-size PNG set (32, 192, 512) + apple-touch-icon 180 | Industry standard; adds multiple files + multiple `<link>` tags | ✓ |

**User's choice:** Multi-size PNG set + apple-touch-icon 180.
**Notes:** Gives best visual quality across browsers, Android home screens, and iOS home screens. Worth the extra files.

---

## Source assets (commit originals?)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, commit sources to `doc/brand/` | Future contributors can regenerate sized assets from canonical originals | ✓ |
| No, only commit resized/target files | Repo stays lean, originals stay in Downloads | |

**User's choice:** Yes, commit to `doc/brand/`.
**Notes:** Establishes `doc/brand/` as the canonical brand source directory. Lets future phases regenerate assets without hunting for the originals.

---

## Docs build output (source vs. built)

| Option | Description | Selected |
|--------|-------------|----------|
| Sources only | Replace only `src/python/docs/images/`; `site/` is gitignored build artifact | ✓ |
| Both sources and built output | Keep committed site in sync until next rebuild | |

**User's choice:** Sources only.
**Notes:** Verified `src/python/site` is gitignored via `git check-ignore`. `mkdocs build` regenerates the output from sources.

---

## Claude's Discretion

- Exact crop bounds when resizing `arrow-mark-square.png` to 32×32 (preserve center, maximize mark)
- Image tooling choice (sips vs. Pillow vs. ImageMagick)
- Whether to upload `social-banner.png` to GitHub as-is (1584×672) or pre-crop to 1280×640
- Exact `gh api` invocation for uploading the social preview (researcher will confirm)

## Deferred Ideas

- Wordmark SVG
- Docker Hub / GHCR description updates (Phase 62+ candidate)
- CLI/TUI splash art
- `doc/brand/hero.png` committed but not wired into any surface this phase
- Alternate color modes (monochrome, accent swap)
