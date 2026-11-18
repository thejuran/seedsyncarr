# Phase 127: README Accuracy - Context

**Gathered:** 2026-11-18
**Status:** Ready for planning

<domain>
## Phase Boundary

README.md documentation correction (DOC-01..04): make the six repository guides discoverable, and state security defaults, HMAC/cleanup behavior and Quick Start network exposure as they actually behave. No application behavior changes, no new application tests. Owner-approved scope extension: two SECURITY.md fixes (line ~40 sentence and line ~43 webhook bullet, D-08).

</domain>

<decisions>
## Implementation Decisions

### Headline pitch and cleanup claims (DOC-03)
- **D-01:** Tagline keeps the differentiator as a *conditioned* promise — auto-delete only runs after Sonarr/Radarr confirms the import (e.g. "...where auto-delete waits for Sonarr/Radarr to confirm the import"). No absolute "never deletes" wording anywhere.
- **D-02:** Say it once fully. Tagline = one-line conditioned pitch; the full explanation (import confirmation via inbound webhook → optional Post-Import Pruning, **off by default** → safety delay, default 60 s → dry-run option) lives once in **How It Works**. About This Fork and the Features bullet are shortened and point there instead of repeating the promise.
- **D-03 (revised 2026-11-18 after research):** State the no-secret consequence plainly: without `webhook_secret`, webhook calls are not verified, so anything that can reach the endpoint can report an import. Do NOT recommend setting `webhook_secret` or `webhook_require_secret = true` for Sonarr/Radarr: SeedSyncarr verifies an HMAC of each request body (`X-Webhook-Signature`), and Sonarr/Radarr cannot compute one (they send only fixed headers or basic auth), so doing so rejects every import webhook (401/503) and pruning silently stops. Instead state factually: verification requires a sender that signs each request; Sonarr/Radarr do not, so the practical protection is restricting who can reach port 8800. Owner chose this 2026-11-18.
- **D-04:** Review the entire README for remaining unconditional claims (e.g. "maximum transfer speed", "safely reclaim") and qualify or soften them.

### Security wording (DOC-02)
- **D-05:** Replace the "Security by default" Features bullet with a "Security controls" bullet listing only always-on controls (CSP headers, rate limiting on named endpoints, log-injection sanitizing, *arr connection-URL IP guard) and linking to the Security section.
- **D-06:** Expand the existing `## Security` section (currently a single link) into a short "what's off until you configure it" list: API auth off when `api_token` empty; webhook verification off when `webhook_secret` empty; `webhook_require_secret` defaults to `False`; encryption at rest off by default (stored secrets plaintext; enable via `[Encryption] enabled = True`). Keep the vulnerability-reporting link. Link SECURITY.md for full posture — don't duplicate it as a table.
- **D-07:** Recheck every stated default against current code (`src/python/common/config.py` and the pruning/auto-delete config) and SECURITY.md at implementation time; the wording must match code, not this file.
- **D-08 (scope extension, owner-approved; widened 2026-11-18):** Fix the SECURITY.md sentence "several protections are active by default" (line ~40) so it no longer contradicts the opt-in items it lists, AND correct the "HMAC-verified import webhooks" bullet (line ~43) so it states that Sonarr/Radarr do not sign requests and that a secret or `webhook_require_secret` would reject their webhooks. No other SECURITY.md edits.

### Quick Start exposure (DOC-04)
- **D-09:** Keep `8800:8800` in both the compose and `docker run` examples (no localhost-bind change).
- **D-10:** Add a factual `> **Network exposure**` blockquote under the Quick Start example, same style as the existing PUID/PGID note (not a `[!WARNING]` admonition): port 8800 is published on all host interfaces; for any untrusted network put SeedSyncarr behind an authenticating reverse proxy and restrict network access; `api_token` protects the API but not the UI, and the UI contains that token. Link to the Security section.

### Documentation discoverability (DOC-01)
- **D-11:** Replace the website link (`https://thejuran.github.io/seedsyncarr`) in Installation with links to `docs/GETTING-STARTED.md` and `docs/CONFIGURATION.md`. The website is not referenced as a docs source.
- **D-12:** New `## Documentation` section placed immediately after Quick Start.
- **D-13:** Grouped with one-line blurbs — "Using SeedSyncarr": Getting Started, Configuration, Security (`SECURITY.md`); "Contributing / internals": Architecture, Development, Testing.
- **D-14:** Move `## Usage Examples` from the bottom up to sit with content sections (above Contributing/Security/License). Reorder only.
- **D-15:** Every relative link in README.md (including images under `doc/`) must resolve — verify mechanically.

### Claude's Discretion
- Exact prose wording within the decisions above.
- Exact section order beyond D-12/D-14 constraints.
- Link-check method (script or grep + `test -f`).

</decisions>

<specifics>
## Specific Ideas

- Motivation: a community comment called SeedSyncArr "no documentation" and raised Huntarr-era concerns. The tone is factual and confident, not alarmed. The comment is motivation, not evidence of equivalent vulnerabilities.
- The PUID/PGID blockquote is the style model for the new network-exposure note.
- SECURITY.md already has accurate per-control wording (encryption opt-in, Bearer auth note about UI carrying the token); reuse its facts.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DOC-01..DOC-04 (locked wording)
- `.planning/ROADMAP.md` — Phase 127 success criteria; backlog 999.6 provenance and acceptance criteria

### Files under edit
- `README.md` — the target
- `SECURITY.md` — source of truth for security posture; two spots edited, line ~40 sentence and line ~43 webhook bullet (D-08)

### Guides to link (must exist and resolve)
- `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `SECURITY.md`

### Defaults to verify against
- `src/python/common/config.py` — `api_token`, `webhook_secret` (empty default), `webhook_require_secret` (default `False`, ~line 582), encryption and auto-delete/pruning defaults
- `docs/CONFIGURATION.md` — documented defaults for pruning, safety delay, dry-run

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- SECURITY.md "Security posture" bullets: accurate wording for encryption opt-in, HMAC conditions, Bearer-auth/UI caveat, rate-limited endpoint list.
- README Usage Examples already explain the webhook URL, "HMAC-verified when a secret is configured", and pruning with a 60 s delay and dry-run.

### Established Patterns
- README uses `>` blockquote notes with a bold lead sentence (PUID/PGID note).
- Docs-only phase: CI gates (pytest, whole-tree ruff) still run but are unaffected; verification is a link check plus a claims review.

### Integration Points
- Absolute claims currently at README lines ~13 (tagline), ~22 (About), ~55 and ~59 (Features), ~63 (How It Works), ~111 (website link).

</code_context>

<deferred>
## Deferred Ideas

- Accepting a webhook authentication method Sonarr/Radarr can actually send (fixed shared-secret header or basic auth) — application change, captured as backlog 999.8 on 2026-11-18. Not in this phase.
- `docs/CONFIGURATION.md` gaps (no `webhook_require_secret` entry, no `encryption.enabled` row) — out of scope; README points to SECURITY.md.

</deferred>

---

*Phase: 127-readme-accuracy*
*Context gathered: 2026-11-18*
