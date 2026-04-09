---
status: partial
phase: 58-docs-site
source: 58-01-SUMMARY.md, 58-02-SUMMARY.md
started: 2026-04-09T13:45:00Z
updated: 2026-04-09T13:50:00Z
---

## Current Test

[testing paused — 1 item outstanding]

## Tests

### 1. MkDocs Build Succeeds
expected: Running `mkdocs build --strict` from `src/python/` exits 0 with no errors or warnings. All 6 pages build (index, install, configuration, arr-setup, faq, changelog link).
result: pass

### 2. Docs Home Page Content
expected: `src/python/docs/index.md` contains a feature list, Docker Compose quick start snippet, and "Next Steps" links to install.md, configuration.md, arr-setup.md, and faq.md. All internal links resolve.
result: pass

### 3. Installation Guide Coverage
expected: `src/python/docs/install.md` covers Docker Compose (recommended), docker run, and pip install paths. Volume mount table explains config and downloads mounts. Post-install steps link to configuration and arr-setup.
result: pass

### 4. Configuration Reference Completeness
expected: `src/python/docs/configuration.md` documents all 8 config sections (General, Lftp, Controller, Web, AutoQueue, Sonarr, Radarr, AutoDelete) with every field, type, and description matching the Config class in config.py.
result: pass

### 5. Sonarr & Radarr Setup Guide
expected: `src/python/docs/arr-setup.md` provides step-by-step webhook setup for both Sonarr and Radarr, includes correct endpoint URLs (`/server/webhook/sonarr`, `/server/webhook/radarr`), HMAC authentication section, title extraction priority chains, event type reference table, and troubleshooting links.
result: pass

### 6. FAQ & Troubleshooting
expected: `src/python/docs/faq.md` contains at least 3 troubleshooting entries including connection refused, HMAC mismatch, and arm64 test caveat. HMAC section correctly states Sonarr/Radarr don't natively send X-Webhook-Signature.
result: pass

### 7. README Docs Link Updated
expected: README.md contains a link to `https://thejuran.github.io/seedsyncarr` (the GitHub Pages docs site), replacing the old wiki link.
result: pass

### 8. Live Docs Site Loads
expected: After push and CI deploy, `https://thejuran.github.io/seedsyncarr` loads the MkDocs Material site with all pages accessible. Navigation works, dark/light mode toggle works.
result: blocked
blocked_by: server
reason: "not deployed — requires push to remote and CI deploy"

## Summary

total: 8
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps

[none yet]
