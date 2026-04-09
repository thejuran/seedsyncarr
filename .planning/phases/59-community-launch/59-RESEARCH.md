# Phase 59: Community Launch - Research

**Researched:** 2026-04-09
**Domain:** Community outreach — content creation, platform norms, deferral tracking
**Confidence:** HIGH

## Summary

Phase 59 is a content-only phase. No code changes. The deliverables are: one r/selfhosted post, three follow-up posts (Servarr Discord, r/sonarr, r/radarr), and two documented deferrals with calendar reminders.

All decisions are locked in CONTEXT.md. The research task is to surface platform-specific norms, post structure patterns, and pitfalls the planner needs to schedule correctly.

The key planning risk is getting the stagger timing right: r/selfhosted goes first (after docs are live), the three follow-up posts go out 48 hours later. The deferral reminders are calendar-only — no in-repo artifacts.

**Primary recommendation:** Write all five posts and both calendar reminders as discrete deliverables. The planner should treat "verify docs site is live" as a hard prerequisite gate before any post is marked ready.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Post Tone & Framing**
- D-01: Use "I inherited and rebuilt" framing — lead with the fork story, what was changed (rebrand, *arr integration, security hardening, dark UI), and why
- D-02: Include Docker Compose quick start snippet directly in the Reddit post so readers can try it immediately
- D-03: Lead the post with the dark mode dashboard screenshot — r/selfhosted values visual posts
- D-04: Openly credit SeedSync by name as the fork origin, explain what was kept and rebuilt. Transparency matters to the community

**Timing & Stagger Strategy**
- D-05: Post to r/selfhosted only AFTER the GitHub Pages docs site is live and verified — all links must work on first impression
- D-06: Follow-up posts to Servarr Discord, r/sonarr, and r/radarr go out 48 hours after the Reddit post

**Audience Customization**
- D-07: Each follow-up post is fully tailored for its audience — not cross-posts or link-backs
- D-08: Servarr Discord post emphasizes webhook integration depth — native Sonarr/Radarr webhook support, HMAC auth, and how it fits into an existing *arr stack
- D-09: r/sonarr post focuses on the Sonarr webhook integration and automated TV show sync workflow
- D-10: r/radarr post focuses on the Radarr webhook integration and automated movie sync workflow

**Deferral Documentation**
- D-11: awesome-selfhosted PR (LNCH-03) deferred to August 2026 — tracked via calendar reminder only, no in-repo file
- D-12: Awesomarr PR (LNCH-04) deferred until 50+ GitHub stars — tracked via calendar reminder only, no in-repo file

### Claude's Discretion
- Exact post titles and body copy — Claude drafts, user reviews before posting
- Reddit post flair selection
- Discord channel selection within Servarr server
- Specific wording of calendar reminders

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LNCH-01 | r/selfhosted announcement post published ("I built X to solve Y" format) | Post structure, flair, screenshot-first framing, Docker Compose snippet |
| LNCH-02 | *arr community outreach (Servarr Discord, r/sonarr, r/radarr) staggered 24-48h after Reddit | Platform norms for each channel; 48h stagger confirmed by D-06 |
| LNCH-03 | awesome-selfhosted PR submitted (deferred to August 2026 per 4-month rule) | 4-month rule verified in awesome-selfhosted CONTRIBUTING.md; calendar reminder only |
| LNCH-04 | Awesomarr PR submitted (deferred until 50+ stars) | 50-star minimum verified in awesome-arr CONTRIBUTING.md; calendar reminder only |
</phase_requirements>

---

## Standard Stack

This phase has no software stack. Deliverables are text files (post drafts) and calendar reminders.

| Deliverable | Format | Location |
|-------------|--------|----------|
| r/selfhosted post | Markdown draft | `.planning/phases/59-community-launch/posts/reddit-selfhosted.md` |
| Servarr Discord post | Markdown draft | `.planning/phases/59-community-launch/posts/discord-servarr.md` |
| r/sonarr post | Markdown draft | `.planning/phases/59-community-launch/posts/reddit-sonarr.md` |
| r/radarr post | Markdown draft | `.planning/phases/59-community-launch/posts/reddit-radarr.md` |
| Deferral reminders | Markdown doc | `.planning/phases/59-community-launch/posts/deferrals.md` |

The post drafts live in the planning directory only — they are content for the user to copy/paste, not committed to the repo.

---

## Architecture Patterns

### Post Structure: r/selfhosted (LNCH-01)

r/selfhosted welcomes "I built X" posts from creators. The community values screenshots, working links, and honest framing over marketing language. [ASSUMED — consistent across multiple sources but subreddit rules not directly fetched from Reddit]

**Recommended structure:**

1. Screenshot as hero image (uploaded to Reddit or imgur — Reddit native image post preferred)
2. Title format: `I inherited and rebuilt SeedSync — now it's SeedSyncarr, a seedbox sync tool with native Sonarr/Radarr integration`
3. Opening paragraph: fork origin story (SeedSync credit), what changed, why
4. Feature bullet list: 5-7 items max, LFTP speed, webhook integration, dark UI, Docker packaging
5. Docker Compose quick start snippet (verbatim from README.md)
6. Closing links: GitHub repo + docs site
7. Flair: "Project" or "Show and Tell" (subreddit-specific — user should verify current available flairs on Reddit before posting) [ASSUMED]

**Screenshot logistics:** Reddit allows image posts natively. Upload `doc/images/screenshot-dashboard.png` as the post image, then add the text body. Alternatively: use an imgur link in a text post if the screenshot needs to accompany a longer body — text + image posts have better engagement in this community. [ASSUMED — community norm based on general Reddit knowledge]

**SeedSync attribution note:** Crediting SeedSync openly (D-04) is the right call for this community. r/selfhosted users are experienced open-source consumers; they notice forks and appreciate honesty. "Forked from X, here's what I kept and why I rebuilt the rest" is a strong framing signal. [ASSUMED]

### Post Structure: Servarr Discord (LNCH-02, D-08)

The Servarr Discord server (discord.gg/SkXFKr5gHj) covers Lidarr, Prowlarr, Radarr, Sonarr, and Whisparr. [VERIFIED: discord.com/invite/SkXFKr5gHj found in search results]

**Channel selection (Claude's discretion):** The `#third-party-tools` or `#community-projects` channel is the typical home for tool announcements in Servarr-like servers. The user should look for a `#showcase`, `#tools`, or `#third-party` channel once on the server. If none exists, `#general` with a note that it's a tool announcement is acceptable. Do not post in support channels. [ASSUMED]

**Recommended structure:**

1. Brief one-liner hook: "I built SeedSyncarr — LFTP-based seedbox sync with native Sonarr + Radarr webhook integration"
2. Key technical differentiator for this audience: webhook depth (HMAC auth, import detection, auto-delete after successful import)
3. How it fits the *arr stack: runs alongside Sonarr/Radarr, no conflict, complements not replaces
4. Docker Compose snippet (shorter than Reddit version — channel posts should be concise)
5. Links: GitHub + docs `/arr-setup.md` page directly

**Discord formatting notes:** Discord supports markdown. Use backticks for code blocks. Keep the message under 2000 characters or use a thread. No image embed unless the server supports it — link to the GitHub README screenshot. [ASSUMED]

### Post Structure: r/sonarr and r/radarr (LNCH-02, D-09, D-10)

Both subreddits are smaller and more focused than r/selfhosted. Posts here are most welcomed when they solve a specific problem the audience recognizes. [ASSUMED]

**r/sonarr recommended structure:**
1. Title: `SeedSyncarr: seedbox sync tool that triggers Sonarr imports automatically via webhook`
2. Problem framing: "Sonarr finds the episode, your client downloads it to the seedbox — but the import never fires unless you manually sync or wait"
3. Solution: SeedSyncarr syncs from seedbox, then calls Sonarr's webhook to trigger the import, including HMAC auth for security
4. Short feature list (TV-focused: automatic TV show sync, series pattern detection via AutoQueue)
5. Docker Compose snippet
6. Link to docs `/arr-setup.md`

**r/radarr recommended structure (same pattern, movie-focused):**
1. Title: `SeedSyncarr: seedbox sync tool that triggers Radarr imports automatically via webhook`
2. Problem framing: same structure, movies instead of episodes
3. Solution: same webhook story
4. Short feature list (movie-focused: batch sync, Radarr webhook import trigger)
5. Docker Compose snippet
6. Link to docs `/arr-setup.md`

### Deferral Documentation Pattern (LNCH-03, LNCH-04)

Per D-11 and D-12, deferrals are tracked via calendar reminder only — no in-repo file.

The deliverable for this phase is a single `deferrals.md` file in the planning directory that:
1. Documents the deferral reason and condition for each
2. Specifies the exact calendar reminder text the user should set
3. Is NOT committed to the main repo (planning files stay in `.planning/`)

**awesome-selfhosted deferral (LNCH-03):**
- Condition: 4-month rule from v1.0.0 tag date [VERIFIED: awesome-selfhosted CONTRIBUTING.md states "first released more than 4 months ago" as requirement]
- Target: August 2026 (assuming v1.0.0 tag in April 2026)
- Calendar reminder text: "Submit SeedSyncarr to awesome-selfhosted — 4-month rule elapsed. PR format: Add SeedSyncarr to File Transfer. Check CONTRIBUTING.md first."

**Awesomarr deferral (LNCH-04):**
- Condition: 50+ GitHub stars [VERIFIED: awesome-arr CONTRIBUTING.md states minimum 50 stars requirement]
- Calendar reminder text: "Check SeedSyncarr star count — submit to awesome-arr when 50+ stars reached. PR format: Add SeedSyncarr to Complimenting Apps."

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Deferral tracking | GitHub issues, DEFERRED.md, or in-repo labels | Calendar reminder (D-11, D-12) — user decided |
| Cross-posting | Single post + link-backs | Fully tailored per-audience posts (D-07) |

---

## Common Pitfalls

### Pitfall 1: Posting Before Docs Are Live
**What goes wrong:** Reader clicks the docs link, gets a 404 or GitHub Pages "no site" page. First impression is broken. Post gains negative comments about broken links.
**Why it happens:** Phase 59 depends on Phase 58 (docs site setup). If the CI pipeline hasn't deployed yet, `thejuran.github.io/seedsyncarr` may not resolve.
**How to avoid:** D-05 locks this — r/selfhosted post only goes out after user manually verifies `https://thejuran.github.io/seedsyncarr` loads correctly in a browser.
**Warning signs:** GitHub Pages deployment can take 1-10 minutes after the first push. Check the "Actions" tab and "Pages" section in GitHub repo settings.

### Pitfall 2: Cross-Posting Instead of Tailoring
**What goes wrong:** r/sonarr and r/radarr readers see a generic r/selfhosted repost. Comments call out "this was already posted on r/selfhosted." Engagement drops.
**Why it happens:** It's faster to copy/paste. D-07 explicitly forbids this.
**How to avoid:** Each post must lead with the audience's specific pain point (TV show imports vs. movie imports vs. *arr stack integration).

### Pitfall 3: Posting to r/sonarr/r/radarr Too Soon
**What goes wrong:** Follow-ups posted at the same time as r/selfhosted look like spam. The stagger is intentional: let the Reddit post gain traction, then bring it to focused audiences.
**How to avoid:** D-06 mandates 48 hours between r/selfhosted and all follow-ups. The plan should reflect this as a hard timing constraint, not just a note.

### Pitfall 4: Submitting Deferrals Early
**What goes wrong:** awesome-selfhosted will reject a PR for a project under 4 months old. Awesomarr PR with under 50 stars creates a negative first impression with that community.
**How to avoid:** Deferrals are not tasks to "do later" — they are explicitly documented as out-of-scope for this phase per D-11 and D-12. The only action is setting the calendar reminders.

### Pitfall 5: Missing the Servarr Discord Channel
**What goes wrong:** Posting in a support channel (e.g., `#sonarr-support`) instead of a community/tools channel looks like spam and may be deleted by moderators.
**How to avoid:** The user should browse Servarr Discord channel list before posting. The planner's task should include a "verify channel selection" step.

---

## Code Examples

### Docker Compose Snippet (from README.md — use verbatim in posts)

```yaml
services:
  seedsyncarr:
    image: ghcr.io/thejuran/seedsyncarr:latest
    container_name: seedsyncarr
    restart: unless-stopped
    ports:
      - "8800:8800"
    volumes:
      - ~/.seedsyncarr:/root/.seedsyncarr
      - /path/to/downloads:/downloads
```

[VERIFIED: from `/Users/julianamacbook/seedsyncarr/README.md`]

### Links to Include in All Posts

- GitHub: `https://github.com/thejuran/seedsyncarr`
- Docs: `https://thejuran.github.io/seedsyncarr`
- *arr setup guide (for *arr-focused posts): `https://thejuran.github.io/seedsyncarr/arr-setup/`
- Container: `ghcr.io/thejuran/seedsyncarr`

[ASSUMED — docs URL pattern based on MkDocs default; `arr-setup.md` confirmed in `src/python/docs/` structure from CONTEXT.md]

### Key Features to Highlight (drawn from README.md)

[VERIFIED: from `/Users/julianamacbook/seedsyncarr/README.md`]

- LFTP-based transfers (parallel connections, segmented downloads)
- Sonarr and Radarr integration via webhooks — import notifications
- AutoQueue — pattern-based file selection
- Auto-extraction — unpack archives post-sync
- Web UI — dark mode (Deep Moss + Amber), responsive dashboard
- Docker packaging — amd64 and arm64
- No remote agent required — SSH credentials only

### Security Features (for Servarr Discord — technically-minded audience)

[VERIFIED: from `/Users/julianamacbook/seedsyncarr/.planning/PROJECT.md`]

- HMAC-SHA256 webhook authentication
- Bearer token API auth with TOFU SSH
- Hash-based CSP, DNS rebinding prevention
- Path traversal guards, SSRF protection on *arr endpoints

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| "I built this" straightforward | "I inherited and rebuilt" with fork story | More authentic for open-source communities |
| Cross-posting to multiple subs | Fully tailored per-audience posts | Better engagement, avoids spam perception |
| Submit to lists immediately | Wait for 4-month rule / star threshold | awesome-selfhosted enforces 4-month rule |

---

## Environment Availability

Step 2.6: SKIPPED — this phase is content-only. No external tools, CLIs, runtimes, or services are required for the implementation tasks (writing post drafts and deferral reminders). The user posts manually; no automation tooling is needed.

---

## Validation Architecture

Step 4: SKIPPED — `workflow.nyquist_validation` is not set in config.json (key absent), but this phase has no automatable acceptance criteria. The success criteria are human-observable: posts published, links verified working, calendar reminders set. No test framework applies.

The planner should model success criteria as manual verification checklist items, not automated tests.

---

## Security Domain

This phase produces only text content (post drafts and calendar reminders). There is no code execution, no API calls, no secrets handling. ASVS categories V2–V6 do not apply.

The only security-relevant note: post content should not include the user's actual API keys, webhook secrets, or SSH credentials. The Docker Compose snippet in the post is deliberately minimal (no secrets hardcoded) — this is already correct in the README source.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | r/selfhosted allows "I built X" posts and welcomes creator announcements | Architecture Patterns — r/selfhosted post | Low — this is a stable community norm; if wrong, user adjusts flair/framing before posting |
| A2 | r/selfhosted flair options include "Project" or "Show and Tell" | Architecture Patterns — r/selfhosted post | Low — flair names may differ; user verifies on Reddit before posting |
| A3 | Servarr Discord has a `#third-party-tools`, `#showcase`, or equivalent channel | Architecture Patterns — Servarr Discord | Medium — user must browse channels before posting |
| A4 | r/sonarr and r/radarr accept tool announcement posts with genuine community value | Architecture Patterns — r/sonarr and r/radarr | Low — these are focused subreddits; tool posts with clear use-case are standard |
| A5 | Docs URL for *arr setup guide follows MkDocs default path `/arr-setup/` | Code Examples — links | Low — user verifies before posting |
| A6 | Reddit text post with imgur/inline image works better than image-only post for longer content | Architecture Patterns — r/selfhosted post | Low — user can adjust format based on Reddit's current UI behavior |

**Verified claims in this research:**
- awesome-selfhosted 4-month rule [VERIFIED: awesome-selfhosted-data/CONTRIBUTING.md via web search]
- Awesomarr 50-star minimum [VERIFIED: awesome-arr CONTRIBUTING.md via WebFetch]
- Servarr Discord server invite URL [VERIFIED: discord.com/invite/SkXFKr5gHj in web search results]
- Docker Compose snippet [VERIFIED: README.md in repo]
- Feature list [VERIFIED: README.md in repo]
- Security features [VERIFIED: PROJECT.md in repo]

---

## Open Questions

1. **What flair should the r/selfhosted post use?**
   - What we know: r/selfhosted has post flairs; "I built X" posts are typical for this sub
   - What's unclear: exact flair names (may be "Project", "Show and Tell", "Release", or similar)
   - Recommendation: User checks available flairs on Reddit before submitting; planner notes this as a human-verify step

2. **Which Servarr Discord channel is correct for tool announcements?**
   - What we know: Servarr Discord has 41,000+ members and covers Radarr, Sonarr, Prowlarr, Lidarr, Whisparr
   - What's unclear: specific channel names for community tool showcases
   - Recommendation: User browses channel list before posting; planner includes "verify channel" step

3. **Is the docs site live at the time this phase executes?**
   - What we know: Phase 59 depends on Phase 58 (docs site setup); D-05 locks the gate
   - What's unclear: whether Phase 58 will have been completed and CI deployed before Phase 59 tasks run
   - Recommendation: The first task in Phase 59 should be a manual verification step — confirm `https://thejuran.github.io/seedsyncarr` loads

---

## Sources

### Primary (HIGH confidence)
- `/Users/julianamacbook/seedsyncarr/README.md` — feature list, Docker Compose snippet, project description
- `/Users/julianamacbook/seedsyncarr/.planning/phases/59-community-launch/59-CONTEXT.md` — all locked decisions
- `/Users/julianamacbook/seedsyncarr/.planning/REQUIREMENTS.md` — LNCH-01 through LNCH-04 definitions
- `awesome-selfhosted-data/CONTRIBUTING.md` (via web search) — 4-month rule confirmed
- `Ravencentric/awesome-arr` CONTRIBUTING.md (via WebFetch) — 50-star minimum confirmed
- `discord.com/invite/SkXFKr5gHj` (via web search result) — Servarr Discord server URL confirmed

### Secondary (MEDIUM confidence)
- Web search results for r/selfhosted community norms — "I built X" format is standard, screenshot posts perform well

### Tertiary (LOW confidence / ASSUMED)
- Servarr Discord channel names for tool announcements — A3 in Assumptions Log
- Reddit flair names for r/selfhosted — A2 in Assumptions Log
- Docs URL path for arr-setup guide — A5 in Assumptions Log

---

## Metadata

**Confidence breakdown:**
- Post content and framing: HIGH — source material (README, PROJECT.md, CONTEXT.md) fully verified
- Platform norms: MEDIUM — web-search verified for general patterns, specific channel names assumed
- Deferral criteria: HIGH — both 4-month rule and 50-star minimum verified from official CONTRIBUTING.md sources
- Timing strategy: HIGH — fully specified in CONTEXT.md decisions

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable domain — platform rules change slowly)
