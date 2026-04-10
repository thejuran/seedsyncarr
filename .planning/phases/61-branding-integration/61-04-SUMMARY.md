---
phase: 61-branding-integration
plan: 04
status: complete
completed: 2026-04-10
---

# Plan 61-04 Summary: README Wordmark Picture Block

## What was done

Inserted a centered `<picture>` block as the first visual element of `README.md`, above the existing dashboard screenshot, using GitHub's `prefers-color-scheme` pattern to serve dark/light wordmark variants per CONTEXT.md D-17–D-20.

## Insertion details

### Before (lines 1–3)

```html
<p align="center">
  <img src="doc/images/screenshot-dashboard.png" alt="SeedSyncarr Dashboard" width="800" />
</p>
```

### After (lines 1–11)

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="doc/brand/wordmark-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="doc/brand/wordmark-light.png">
    <img alt="SeedSyncarr" src="doc/brand/wordmark-dark.png" width="480">
  </picture>
</p>

<p align="center">
  <img src="doc/images/screenshot-dashboard.png" alt="SeedSyncarr Dashboard" width="800" />
</p>
```

The new `<picture>` block is **verbatim** the markup from CONTEXT.md D-18 with `width="480"` per D-19.

### Lookout: a second screenshot reference exists lower in the file

The initial Edit attempt failed with "found 2 matches" because `README.md` also has a `## Screenshots` section further down (originally at line 75, now at line 83 after the 8-line insertion above) that duplicates the same screenshot block. The fix was to include the trailing tagline blockquote in the Edit's `old_string` to anchor the match to the top of the file. The `## Screenshots` section below is untouched — verified by direct inspection at lines 81–85 post-edit.

## Verification

```
$ head -15 README.md
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="doc/brand/wordmark-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="doc/brand/wordmark-light.png">
    <img alt="SeedSyncarr" src="doc/brand/wordmark-dark.png" width="480">
  </picture>
</p>

<p align="center">
  <img src="doc/images/screenshot-dashboard.png" alt="SeedSyncarr Dashboard" width="800" />
</p>

> Sync files from your seedbox to your local media server — fast, automated, and integrated with Sonarr and Radarr.

$ grep -c '<p align="center">' README.md
3    # hero picture + hero screenshot + Screenshots section
```

- Picture block appears before the first screenshot (picture at line 6, screenshot at line 10)
- All of: `prefers-color-scheme: dark`, `prefers-color-scheme: light`, `wordmark-dark.png`, `wordmark-light.png`, `alt="SeedSyncarr"`, `width="480"`, `<picture>`, `</picture>` present in first 15 lines
- Tagline blockquote and all badges preserved
- `## Screenshots` section and remaining content below unchanged

All acceptance criteria from 61-04-PLAN.md met. PLSH-07 implemented.
