# r/selfhosted Announcement Post

**Target:** r/selfhosted
**Suggested flair:** "Project" or "Show and Tell" (verify available flairs before posting)
**Image:** Upload `doc/images/screenshot-dashboard.png` as the post image on Reddit
**Prerequisite:** Verify https://thejuran.github.io/seedsyncarr loads before posting (per D-05)

---

**Title:** I inherited and rebuilt SeedSync into SeedSyncarr -- a seedbox sync tool with native Sonarr/Radarr webhook integration

---

[Screenshot: dark mode dashboard -- upload doc/images/screenshot-dashboard.png as Reddit image]

I inherited a seedbox sync tool called [SeedSync](https://github.com/IrealiTY/seedsync) (by IrealiTY) and rebuilt it from the ground up. The result is SeedSyncarr -- an LFTP-based file sync tool that bridges your seedbox and local media server, with native Sonarr and Radarr webhook integration.

The original SeedSync had a solid foundation: an LFTP sync engine and a web UI for monitoring transfers. That core is still there. What I rebuilt: a full rebrand to SeedSyncarr, native Sonarr and Radarr webhook integration (so imports trigger automatically after sync), security hardening with HMAC-SHA256 webhook authentication and Content Security Policy headers, a dark mode UI with a Deep Moss and Amber palette designed for always-on displays, an Angular 21 upgrade, and a comprehensive test suite.

## What it does

- **LFTP-based transfers** -- parallel connections, segmented downloads, maximum speed from your seedbox
- **Sonarr and Radarr integration** -- webhook-driven import notifications after sync completes, so your media library updates automatically
- **AutoQueue** -- pattern-based file selection syncs only what you want
- **Auto-extraction** -- automatically unpacks archives post-sync
- **Web UI** -- dark mode dashboard, responsive, designed for always-on displays
- **Docker images for amd64 and arm64** -- runs anywhere you run containers
- **No remote agent** -- just SSH credentials, nothing to install on the seedbox

## Quick start

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

Open `http://localhost:8800`, add your seedbox SSH credentials, and you're syncing.

## Links

- **GitHub:** https://github.com/thejuran/seedsyncarr
- **Docs:** https://thejuran.github.io/seedsyncarr
- **Container:** `ghcr.io/thejuran/seedsyncarr:latest`

If you run a Sonarr or Radarr stack, there's a dedicated setup guide in the docs for configuring webhook-driven imports. Happy to answer questions or take feedback -- this has been a labor of love and I'd like to make it useful for more people.
