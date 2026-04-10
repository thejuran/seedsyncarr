---
phase: 61-branding-integration
plan: 02
status: complete
completed: 2026-04-10
---

# Plan 61-02 Summary: Web App Favicon Multi-Size Set + index.html

## What was done

Replaced the legacy green leaf favicon with the new SeedSyncarr arrow mark and generated a full multi-size favicon set plus an Apple touch icon. Extended `src/angular/src/index.html` with three new `<link>` tags per CONTEXT.md D-06.

## Tool choice

Used macOS `sips` per plan (no new dependencies, deterministic PNG output). No ImageMagick, no Pillow.

## Padding inspection & crop decision (D-07)

Decoded `doc/brand/arrow-mark-square.png` with a stdlib-only PNG reader to measure the visual bounding box of the arrow mark on the dark background.

- Original: 1024×1024
- Visual bbox: (192,192)-(824,832) = **633×641**
- Padding per side: **18.7%–19.4%** — well above the D-07 10% tolerance

Crop applied (sips `-c 660 660` centered) → `/tmp/arrow-cropped.png` at 660×660. Re-measurement confirmed new padding of 1.5%–2.6% per side with the mark intact at 633×641 inside the crop. This is the source used for the three square favicons.

The rounded variant (`doc/brand/arrow-mark-rounded.png`) was used as-is for the apple-touch-icon since iOS re-rounds the icon automatically (D-05).

## Files generated

| Path | Dimensions | Source |
|---|---|---|
| `src/angular/src/assets/favicon.png` | 32×32 | cropped arrow-mark-square |
| `src/angular/src/assets/favicon-192.png` | 192×192 | cropped arrow-mark-square |
| `src/angular/src/assets/favicon-512.png` | 512×512 | cropped arrow-mark-square |
| `src/angular/src/assets/apple-touch-icon.png` | 180×180 | arrow-mark-rounded (not cropped) |

All four are `PNG image data, NN x NN, 8-bit/color RGBA, non-interlaced`.

The legacy green leaf favicon at `src/angular/src/assets/favicon.png` (1,000 bytes) was overwritten — new file is 2,348 bytes of the new arrow mark.

## index.html diff

Replaced the single existing `<link rel="icon">` line (10) with four lines implementing the full icon set per D-06:

```html
    <link rel="icon" type="image/png" sizes="32x32" href="assets/favicon.png">
    <link rel="icon" type="image/png" sizes="192x192" href="assets/favicon-192.png">
    <link rel="icon" type="image/png" sizes="512x512" href="assets/favicon-512.png">
    <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">
```

All other content in `index.html` is untouched (doctype, html lang, title, base, viewport, theme-color, body, app-root).

## Verification

```
$ file src/angular/src/assets/favicon.png
PNG image data, 32 x 32, 8-bit/color RGBA, non-interlaced
$ file src/angular/src/assets/favicon-192.png
PNG image data, 192 x 192, 8-bit/color RGBA, non-interlaced
$ file src/angular/src/assets/favicon-512.png
PNG image data, 512 x 512, 8-bit/color RGBA, non-interlaced
$ file src/angular/src/assets/apple-touch-icon.png
PNG image data, 180 x 180, 8-bit/color RGBA, non-interlaced
$ grep -c 'rel="icon"' src/angular/src/index.html
3
```

All acceptance criteria from 61-02-PLAN.md met. PLSH-04 implemented.
