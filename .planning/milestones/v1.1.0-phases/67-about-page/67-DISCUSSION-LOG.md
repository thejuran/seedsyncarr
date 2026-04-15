# Phase 67: About Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 67-about-page
**Areas discussed:** System info data, Identity card content, Link cards targets, License correction

---

## System Info Data

| Option | Description | Selected |
|--------|-------------|----------|
| New backend endpoint | Add a /server/status API that returns runtime info | |
| Static + existing | Use only data available without new backend work | ✓ |
| You decide | Claude picks the best approach | |

**User's choice:** Static + existing
**Notes:** User asked about security risk of showing config path. Explained minimal risk since UI is local-network/authenticated. Moot point since static approach was chosen.

### Config Path

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, show real path | Display actual config directory path from server | |
| Show generic path | Show static label like ~/.seedsyncarr | |
| You decide | Claude picks | |

**User's choice:** Asked "is there a risk?" — resolved via explanation, static approach makes this moot.

---

## Identity Card Content

### App Icon

| Option | Description | Selected |
|--------|-------------|----------|
| Brand favicon | Use actual SeedSyncarr arrow-mark favicon from doc/brand/ | ✓ |
| Phosphor icon | Use ph-arrows-merge Phosphor icon matching mockup | |
| You decide | Claude picks whichever looks best | |

**User's choice:** Brand favicon

### Tagline

| Option | Description | Selected |
|--------|-------------|----------|
| Use mockup text | 'Sync files from your seedbox...with automated precision.' | |
| Use README tagline | 'Sync files from your seedbox...integrated with Sonarr and Radarr.' | ✓ |
| You decide | Claude picks | |

**User's choice:** Use README tagline

---

## Link Cards Targets

### Changelog Destination

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Releases | Link to github.com/thejuran/seedsyncarr/releases | ✓ |
| CHANGELOG.md | Link to the CHANGELOG.md file in the repo | |
| You decide | Claude picks | |

**User's choice:** GitHub Releases

### Link Target

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, new tabs | All external links open in new tabs | ✓ |
| You decide | Claude picks based on UX best practices | |

**User's choice:** Yes, new tabs

---

## License Correction

| Option | Description | Selected |
|--------|-------------|----------|
| Fix to Apache 2.0, keep copyright | Show Apache 2.0 badge + existing copyright text | |
| Fix license, update copyright | Show Apache 2.0 badge + different copyright text | |
| You decide | Claude matches LICENSE.txt exactly | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Claude's Discretion

- License badge text and copyright format (match LICENSE.txt)
- Fade-in-up animation timing
- System info table hover effect
- Identity card ambient glow
- Fork attribution note styling
- Responsive breakpoints for link cards

## Deferred Ideas

- Backend /server/status endpoint for live system info — future phase
- Build info injection (commit hash, build date) at Docker build time — future enhancement
