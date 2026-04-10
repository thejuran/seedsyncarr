# Phase 61: Branding Integration - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the legacy green leaf icon with the new SeedSyncarr arrow-mark branding across four surfaces:

1. **Web app favicon** — `src/angular/src/assets/favicon.png` (+ multi-size set + apple-touch-icon + `index.html` link tags)
2. **Docs site** — `src/python/docs/images/favicon.png` and `logo.png` (MkDocs Material already wired via `mkdocs.yml`)
3. **GitHub social preview** — uploaded to the `thejuran/seedsyncarr` repo via `gh api` (not checked into the repo tree)
4. **README header** — logo added above the existing dashboard screenshot, with light/dark mode via `<picture>` tag

Out of scope: logo redesign, marketing site, email templates, CLI splash art, alternate brand marks, Docker Hub description cleanup.

</domain>

<decisions>
## Implementation Decisions

### Source assets (all pre-produced, in `~/Downloads/Seedsyncarr branding/`)

- **D-01:** The six source PNGs will be copied into `doc/brand/` in the repo and committed as canonical originals. Future contributors regenerate sized assets from these sources.
- **D-02:** Assets will be renamed during the copy for discoverability:
  - `image_d29fb7d4-…png` → `doc/brand/arrow-mark-square.png` (1024×1024, square, dark bg)
  - `image_d91ceeb2-…png` → `doc/brand/arrow-mark-rounded.png` (1024×1024, rounded square, dark bg)
  - `image_13559cd8-…png` → `doc/brand/wordmark-dark.png` (1376×768, horizontal lockup, dark bg)
  - `image_9da43036-…png` → `doc/brand/wordmark-light.png` (1376×768, horizontal lockup, white bg)
  - `image_1874209b-…png` → `doc/brand/social-banner.png` (1584×672, banner with tagline)
  - `image_3b77fb04-…png` → `doc/brand/hero.png` (1376×768, stylized hero — kept for future use, not wired up this phase)

### Favicon (PLSH-04, web app)

- **D-03:** Use `arrow-mark-square.png` (NOT the rounded variant) as the base for the browser-tab favicon. Rounded edges would render as artifacts at 16/32 px.
- **D-04:** Generate a multi-size PNG set from `arrow-mark-square.png`:
  - `src/angular/src/assets/favicon.png` — 32×32 (replaces existing 1 KB leaf file at this exact path to satisfy PLSH-04 / success criterion #1)
  - `src/angular/src/assets/favicon-192.png` — 192×192 (Android home screen)
  - `src/angular/src/assets/favicon-512.png` — 512×512 (high-DPI)
- **D-05:** Use `arrow-mark-rounded.png` as the base for the Apple touch icon:
  - `src/angular/src/assets/apple-touch-icon.png` — 180×180 (iOS home screen)
- **D-06:** Update `src/angular/src/index.html` to add the new `<link>` tags next to the existing favicon link:
  - `<link rel="icon" type="image/png" sizes="32x32" href="assets/favicon.png">` (existing path, new content)
  - `<link rel="icon" type="image/png" sizes="192x192" href="assets/favicon-192.png">`
  - `<link rel="icon" type="image/png" sizes="512x512" href="assets/favicon-512.png">`
  - `<link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">`
- **D-07:** Resizing MUST preserve the arrow-mark centering — if source has padding, crop to the visual bounding box before resizing so the 16/32 px versions read as a mark, not a dot in a field.

### Docs site (PLSH-05)

- **D-08:** Replace only the MkDocs **source** files under `src/python/docs/images/`. The built output at `src/python/site/` is `.gitignore`d (verified) — `mkdocs build` in CI / local will regenerate from the new sources.
- **D-09:** `src/python/docs/images/favicon.png` — regenerated from `arrow-mark-square.png` at 512×512 (browsers scale down; Material theme passes the file through as-is).
- **D-10:** `src/python/docs/images/logo.png` — regenerated from `wordmark-dark.png`. The MkDocs Material dark theme is the dark-by-default variant for this docs site, so the dark-bg wordmark is the right pick. Target height ~64 px (Material header); resize preserving aspect ratio.
- **D-11:** No changes to `mkdocs.yml` — it already references these exact filenames.
- **D-12:** No changes to `src/python/site/` (gitignored build artifact).

### GitHub social preview (PLSH-06)

- **D-13:** Use `doc/brand/social-banner.png` (1584×672, banner with arrow + wordmark + tagline) as the social preview.
- **D-14:** Upload via `gh api` to the `thejuran/seedsyncarr` repo. GitHub's `PATCH /repos/{owner}/{repo}` endpoint accepts a `social_preview` upload — the exact invocation is a research item (the planner should confirm the correct API call, since `gh api` with file uploads has subtleties).
- **D-15:** GitHub recommends 1280×640 for social previews. The source is 1584×672 (2.36:1 vs. 2:1). The planner/researcher should decide: upload as-is (GitHub will scale/crop) OR pre-resize/crop to 1280×640 before upload. **Claude's discretion** — prefer uploading as-is if GitHub's scaling is acceptable, otherwise crop centered.
- **D-16:** Success is verified by: (a) `gh api repos/thejuran/seedsyncarr` returning a non-null `social_preview` field, and (b) visual check on the repo page.

### README header (PLSH-07)

- **D-17:** Logo is added **above** the existing dashboard screenshot as the first visual element after any frontmatter. The existing screenshot stays.
- **D-18:** Use GitHub's `<picture>` + `prefers-color-scheme` pattern to serve light/dark variants:
  ```html
  <p align="center">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="doc/brand/wordmark-dark.png">
      <source media="(prefers-color-scheme: light)" srcset="doc/brand/wordmark-light.png">
      <img alt="SeedSyncarr" src="doc/brand/wordmark-dark.png" width="480">
    </picture>
  </p>
  ```
- **D-19:** Target rendered width 480 px (half of 960 content width). Source files stay full-resolution; `width` attribute handles display sizing.
- **D-20:** The `<picture>` block is placed as the FIRST element in README, before the existing `<p align="center"><img ... screenshot .../></p>` block.

### Claude's Discretion

- Exact crop bounds when resizing `arrow-mark-square.png` to 32×32 (preserve center, maximize mark size)
- Whether to use `sips` (macOS built-in) or Python/Pillow for resizing — as long as output is deterministic PNG with no metadata cruft
- Exact sizing for `social-banner.png` upload (as-is vs. pre-cropped to 1280×640) — researcher confirms the GitHub API behavior
- Choice of image tooling in the plan (sips vs. Pillow vs. ImageMagick) — pick the one with fewest dependencies, prefer `sips` if on macOS-only path, prefer Pillow if tests run in Linux CI

### Folded Todos

None.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §"Phase 61: Branding Integration" — goal, success criteria, dependency on Phase 60
- `.planning/REQUIREMENTS.md` — PLSH-04 (web favicon), PLSH-05 (docs logo/favicon), PLSH-06 (social preview), PLSH-07 (README logo)

### Existing target files
- `src/angular/src/assets/favicon.png` — current (legacy leaf, 1 KB) web app favicon to replace
- `src/angular/src/index.html` — current `<link rel="icon">` declaration; must be extended with multi-size + apple-touch-icon links
- `src/python/docs/images/favicon.png` — current docs favicon to replace
- `src/python/docs/images/logo.png` — current docs logo to replace
- `src/python/mkdocs.yml` — references `images/logo.png` and `images/favicon.png` (no changes needed)
- `README.md` — header currently opens with dashboard screenshot; logo `<picture>` block inserted above it
- `.gitignore` — confirms `src/python/site` is ignored (build output)

### Source brand assets (to be copied into `doc/brand/`)
- `~/Downloads/Seedsyncarr branding/image_d29fb7d4-643b-4930-85d3-ef398a58d068.png` → `doc/brand/arrow-mark-square.png`
- `~/Downloads/Seedsyncarr branding/image_d91ceeb2-65a1-430c-96c4-747b0086ccac.png` → `doc/brand/arrow-mark-rounded.png`
- `~/Downloads/Seedsyncarr branding/image_13559cd8-c2ce-4ddc-a257-f45116455b22.png` → `doc/brand/wordmark-dark.png`
- `~/Downloads/Seedsyncarr branding/image_9da43036-7262-486d-ae89-55aa3e7c8dcf.png` → `doc/brand/wordmark-light.png`
- `~/Downloads/Seedsyncarr branding/image_1874209b-df74-4fbc-b2fc-fb757e5b89a8.png` → `doc/brand/social-banner.png`
- `~/Downloads/Seedsyncarr branding/image_3b77fb04-9273-4056-b4c1-bce70d15d453.png` → `doc/brand/hero.png`

### Related prior-phase artifacts
- `.planning/phases/57-readme-community-health/57-01-PLAN.md` — established current README structure; phase 61 adds logo above that existing layout
- `.planning/phases/58-docs-site/` — built the MkDocs site; phase 61 replaces its brand imagery

### External docs (researcher should verify during research step)
- GitHub REST API — repo social preview upload endpoint (`PATCH /repos/{owner}/{repo}` with multipart image) — exact `gh api` invocation is a research item
- GitHub Markdown `<picture>` + `prefers-color-scheme` pattern — documented in GitHub Docs "Managing your profile README" / "Theming in READMEs"
- MkDocs Material docs — logo/favicon configuration (already wired in `mkdocs.yml`, but verify no extra config is needed for PNG vs. SVG)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`mkdocs.yml` logo/favicon keys already configured** — no config changes needed, just swap the PNG files in place.
- **Angular `index.html` already has a `<link rel="icon">`** — extend in place rather than refactor.
- **README already uses `<p align="center"><img ...>`** for the screenshot — same pattern extends cleanly to a `<picture>` logo block above it.

### Established Patterns

- **Docs build output is gitignored** (`src/python/site`) — only source files under `src/python/docs/` are committed. This is confirmed via `git check-ignore`.
- **Images live alongside their consumers** — Angular assets under `src/angular/src/assets/`, docs images under `src/python/docs/images/`. Phase 61 adds a new top-level `doc/brand/` directory specifically for canonical brand sources (distinct from in-app assets).
- **README images live under `doc/images/`** — e.g., `doc/images/screenshot-dashboard.png`. The new `doc/brand/` directory is a sibling convention for brand-specific source files.

### Integration Points

- `src/angular/src/index.html` — add 3 new `<link>` tags (192, 512, apple-touch-icon) next to the existing one
- `README.md` — insert a `<picture>` block as the first visual element (before the screenshot `<p>`)
- `src/angular/src/assets/` — add 3 new files (`favicon-192.png`, `favicon-512.png`, `apple-touch-icon.png`) and overwrite 1 (`favicon.png`)
- `src/python/docs/images/` — overwrite 2 files (`favicon.png`, `logo.png`)
- `doc/brand/` — new directory, 6 committed source files
- `thejuran/seedsyncarr` GitHub repo — social preview uploaded via `gh api` (not a file commit)

</code_context>

<specifics>
## Specific Ideas

- **"The rounded variant is for apple-touch-icon, not the favicon"** — rounded corners would render as visual artifacts at 16/32 px sizes because iOS re-rounds apple-touch-icons automatically but browsers do not round favicons.
- **"Arrow-mark visual bounding box matters"** — if there is whitespace padding in the 1024×1024 source, crop it before resizing to 32×32 so the mark remains recognizable at small sizes.
- **"GitHub README theming via `<picture>` + `prefers-color-scheme`"** — this is the specific GitHub-supported pattern. Standard Markdown `![]()` doesn't support it.
- **"`doc/brand/` is the canonical sources directory"** — this establishes a convention for future brand work. Don't mix brand sources with in-app assets.

</specifics>

<deferred>
## Deferred Ideas

- **Wordmark SVG** — PNG is good enough for all current targets. SVG would be a nice-to-have for infinite-scale rendering but requires an SVG source asset that doesn't exist yet.
- **Docker Hub / GHCR description updates** — branding on the registry page is not in PLSH-04 through PLSH-07. Could be a future phase (Phase 62+: "Registry presence polish").
- **CLI/TUI splash art using the arrow-mark** — interesting but scope creep. File under "future UX polish".
- **`doc/brand/hero.png`** — committed as a canonical source but not wired into any surface this phase. Available for future social posts, blog headers, or a marketing site.
- **Alternate color modes (accent-swap, monochrome)** — no requirement for alternates. Current assets cover light + dark.

### Reviewed Todos (not folded)

None — no pending todos matched this phase's scope.

</deferred>

---

*Phase: 61-branding-integration*
*Context gathered: 2026-04-10*
