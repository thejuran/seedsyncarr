# r/sonarr Announcement Post

**Target:** r/sonarr
**Timing:** 48 hours after r/selfhosted post (per D-06)

---

**Title:** SeedSyncarr: seedbox sync tool that triggers Sonarr imports automatically via webhook

---

If you run Sonarr with a seedbox, you know the gap: Sonarr finds the episode, your torrent client downloads it to the seedbox, but getting it from the seedbox to your local library and triggering the Sonarr import is the missing piece. You end up with manual syncs, cron jobs, or hoping Sonarr's remote path mapping picks it up.

SeedSyncarr closes that gap. It syncs files from your seedbox to your local server using LFTP (parallel connections, segmented downloads -- fast), then calls Sonarr's webhook endpoint to trigger an import scan. The import fires automatically when the sync completes. No manual intervention, no polling.

## How it works with Sonarr

1. Your torrent client downloads an episode to the seedbox
2. SeedSyncarr detects the new file and syncs it to your local download directory via LFTP over SSH
3. When the sync finishes, SeedSyncarr sends a webhook notification to Sonarr
4. Sonarr runs its import scan, matches the file, and moves it into your library

The webhook request is signed with HMAC-SHA256 -- not just a bare HTTP call.

## Features relevant to Sonarr users

- **AutoQueue** -- define patterns to automatically sync only the series and episodes you want
- **Auto-extraction** -- packed releases get extracted automatically after sync
- **Webhook-triggered imports** -- Sonarr import fires on sync completion, not on a timer
- **HMAC-SHA256 authentication** -- webhook requests are cryptographically signed
- **No remote agent** -- nothing to install on the seedbox, just SSH credentials

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

## Links

- **GitHub:** https://github.com/thejuran/seedsyncarr
- **Sonarr/Radarr setup guide:** https://thejuran.github.io/seedsyncarr/arr-setup/
- **Container:** `ghcr.io/thejuran/seedsyncarr:latest`

The docs have a step-by-step guide for configuring the Sonarr webhook integration. Happy to answer questions if anyone has a similar seedbox-to-local workflow.
