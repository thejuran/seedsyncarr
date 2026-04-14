---
created: 2026-02-04T11:07
title: Fix Safari URL bar color bleed
area: ui
files:
  - src/angular/src/index.html
---

## Problem

Safari automatically samples colors from the top of webpages to tint its browser chrome (URL bar, tabs). The SeedSync header's green/teal color is being picked up, causing an unwanted green tint in Safari's UI.

Screenshot: `/Users/julianamacbook/Desktop/Safari Color Bleed.png`

## Solution

Add a `theme-color` meta tag to `src/angular/src/index.html` to explicitly control what color Safari uses:

```html
<meta name="theme-color" content="#1a1a2e">
```

Use a neutral dark color that matches the app's dark theme rather than letting Safari sample the header.
