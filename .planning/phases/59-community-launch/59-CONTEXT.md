# Phase 59: Community Launch - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Announce SeedSyncarr to the self-hosted community with staggered, audience-tailored posts and properly documented deferrals. This phase produces post drafts and deferral reminders — no code changes.

</domain>

<decisions>
## Implementation Decisions

### Post Tone & Framing
- **D-01:** Use "I inherited and rebuilt" framing — lead with the fork story, what was changed (rebrand, *arr integration, security hardening, dark UI), and why
- **D-02:** Include Docker Compose quick start snippet directly in the Reddit post so readers can try it immediately
- **D-03:** Lead the post with the dark mode dashboard screenshot — r/selfhosted values visual posts
- **D-04:** Openly credit SeedSync by name as the fork origin, explain what was kept and rebuilt. Transparency matters to the community

### Timing & Stagger Strategy
- **D-05:** Post to r/selfhosted only AFTER the GitHub Pages docs site is live and verified — all links must work on first impression
- **D-06:** Follow-up posts to Servarr Discord, r/sonarr, and r/radarr go out 48 hours after the Reddit post

### Audience Customization
- **D-07:** Each follow-up post is fully tailored for its audience — not cross-posts or link-backs
- **D-08:** Servarr Discord post emphasizes webhook integration depth — native Sonarr/Radarr webhook support, HMAC auth, and how it fits into an existing *arr stack
- **D-09:** r/sonarr post focuses on the Sonarr webhook integration and automated TV show sync workflow
- **D-10:** r/radarr post focuses on the Radarr webhook integration and automated movie sync workflow

### Deferral Documentation
- **D-11:** awesome-selfhosted PR (LNCH-03) deferred to August 2026 — tracked via calendar reminder only, no in-repo file
- **D-12:** Awesomarr PR (LNCH-04) deferred until 50+ GitHub stars — tracked via calendar reminder only, no in-repo file

### Claude's Discretion
- Exact post titles and body copy — Claude drafts, user reviews before posting
- Reddit post flair selection
- Discord channel selection within Servarr server
- Specific wording of calendar reminders

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above. Reference these project files:

### Project Context
- `.planning/REQUIREMENTS.md` — LNCH-01 through LNCH-04 requirement definitions
- `.planning/ROADMAP.md` — Phase 59 success criteria and dependency on Phase 58
- `README.md` — Current project description and feature list (source material for posts)
- `src/python/docs/index.md` — Docs site home page (link target for posts)
- `doc/images/screenshot-dashboard.png` — Dashboard screenshot to include in Reddit post

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Dashboard screenshot already exists at `doc/images/screenshot-dashboard.png`
- README.md has a polished feature list and quick start that can be adapted for posts
- Docs site at `https://thejuran.github.io/seedsyncarr` is the primary link target

### Established Patterns
- No prior community outreach exists — this is the first announcement

### Integration Points
- Posts link to: GitHub repo, docs site, Docker container registry (ghcr.io)
- No code changes needed — this phase is content-only

</code_context>

<specifics>
## Specific Ideas

- Reddit post format: "I built X to solve Y" but with fork-origin story angle
- Include the Docker Compose snippet from README.md in the Reddit post body
- Screenshot should be the dark mode dashboard (Deep Moss + Amber palette)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 59-community-launch*
*Context gathered: 2026-04-09*
