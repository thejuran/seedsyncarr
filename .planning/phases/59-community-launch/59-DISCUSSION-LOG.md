# Phase 59: Community Launch - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 59-community-launch
**Areas discussed:** Post tone & framing, Timing & stagger strategy, Audience customization, Deferral documentation

---

## Post Tone & Framing

| Option | Description | Selected |
|--------|-------------|----------|
| "I inherited and rebuilt" | Lead with forking SeedSync, what you changed, and why. Authentic open-source story. | ✓ |
| "I built this to solve Y" | Lead with the problem and present SeedSyncarr as the solution. Classic r/selfhosted format. | |
| "Here's my stack" | Lead with the technical stack. More technical, less narrative. | |

**User's choice:** "I inherited and rebuilt"

| Option | Description | Selected |
|--------|-------------|----------|
| High-level + link to docs | Keep the post focused on what/why, link to docs for setup. | |
| Include setup snippet | Include Docker Compose quick start directly in the post. | ✓ |
| You decide | Claude picks the right balance. | |

**User's choice:** Include setup snippet

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, lead with screenshot | Dark mode dashboard screenshot at the top. | ✓ |
| Yes, but inline | Screenshot in post body, not hero image. | |
| No screenshot | Text-only post. | |

**User's choice:** Yes, lead with screenshot

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, credit openly | Mention SeedSync by name, explain what was kept/rebuilt. | ✓ |
| Brief mention | Acknowledge existing project without detail. | |
| No mention | Present as standalone project. | |

**User's choice:** Yes, credit openly

---

## Timing & Stagger Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| After docs site is live | Post only after GitHub Pages is deployed and verified. | ✓ |
| Same day as push | Post same day you push. Docs will deploy via CI within minutes. | |
| You decide | Claude picks based on best first impression. | |

**User's choice:** After docs site is live

| Option | Description | Selected |
|--------|-------------|----------|
| 24 hours | Post follow-ups the next day. | |
| 48 hours | Two days later. More breathing room. | ✓ |
| You decide per audience | Claude staggers based on each community. | |

**User's choice:** 48 hours

---

## Audience Customization

| Option | Description | Selected |
|--------|-------------|----------|
| Same core, different lead | Same description, each post leads with what matters to that audience. | |
| Fully tailored | Each post written from scratch for its audience. | ✓ |
| Cross-post with note | Link to Reddit post with brief tailored intro. | |

**User's choice:** Fully tailored

| Option | Description | Selected |
|--------|-------------|----------|
| Webhook integration depth | Focus on native Sonarr/Radarr webhook support, HMAC auth, *arr stack fit. | ✓ |
| Alternative to existing tools | Position against rclone, syncthing, explain why LFTP + *arr is different. | |
| You decide | Claude picks the right angle. | |

**User's choice:** Webhook integration depth

---

## Deferral Documentation

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub issues with labels | Create GitHub issues with "deferred" label and target date/condition. | |
| DEFERRED.md in repo | Single markdown file listing deferred submissions. | |
| Calendar reminder only | Set calendar/todo reminders. No in-repo tracking. | ✓ |

**User's choice:** Calendar reminder only

---

## Claude's Discretion

- Exact post titles and body copy
- Reddit post flair selection
- Discord channel selection within Servarr server
- Specific wording of calendar reminders

## Deferred Ideas

None — discussion stayed within phase scope
