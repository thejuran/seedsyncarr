---
phase: 61-branding-integration
plan: 03
status: complete
completed: 2026-04-10
---

# Plan 61-03 Summary: Docs Site Favicon + Logo

## What was done

Replaced the two MkDocs Material source images with the new SeedSyncarr branding by overwriting the existing filenames in `src/python/docs/images/`. No `mkdocs.yml` changes were needed because it already references these exact paths.

## Files replaced

| Path | Before | After | Source |
|---|---|---|---|
| `src/python/docs/images/favicon.png` | 1,000 B legacy leaf | **512×512** new arrow mark (295,190 B) | cropped `doc/brand/arrow-mark-square.png` |
| `src/python/docs/images/logo.png` | 1,000 B legacy logo | **128×71** new dark wordmark (4,741 B) | `doc/brand/wordmark-dark.png` |

## Decisions

### Docs favicon source — used cropped arrow mark

Plan 61-03 Task 1 action block named `doc/brand/arrow-mark-square.png` as the source. That file has ~19% padding per side (measured in plan 61-02), and the docs favicon is scaled down by browsers to 16/32 px just like the web app favicon — so CONTEXT.md D-07's "crop to preserve centering at small sizes" principle applies identically.

Reused `/tmp/arrow-cropped.png` (660×660 centered crop generated in plan 61-02) as the source for `sips -Z 512`. This keeps the docs site favicon visually consistent with the Angular web app favicon and avoids a "dot in a field" render at small sizes. The acceptance criterion only constrains final dimensions (`512 x 512`), which is preserved.

### Docs logo — exact sips math as plan predicted

`sips -Z 128 doc/brand/wordmark-dark.png` produced exactly `128 x 71` (within the `128 x (71|72)` tolerance the plan specified). This honors D-10's "~64 px height" target at 2× Retina density for crisp rendering in the Material header.

## Verification

```
$ file src/python/docs/images/favicon.png
PNG image data, 512 x 512, 8-bit/color RGBA, non-interlaced
$ file src/python/docs/images/logo.png
PNG image data, 128 x 71, 8-bit/color RGBA, non-interlaced
$ git diff --quiet src/python/mkdocs.yml; echo $?
0    # mkdocs.yml unchanged
$ git diff --stat src/python/docs/images/
 src/python/docs/images/favicon.png | Bin 1000 -> 295190 bytes
 src/python/docs/images/logo.png    | Bin 1000 -> 4741 bytes
```

- `src/python/mkdocs.yml` untouched (per D-11)
- `src/python/site/` untouched — gitignored build output, MkDocs regenerates on next build (per D-08, D-12). Verified via `git check-ignore`.

All acceptance criteria from 61-03-PLAN.md met. PLSH-05 implemented.
