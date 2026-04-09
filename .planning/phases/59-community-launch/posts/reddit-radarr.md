# r/radarr Announcement Post

**Target:** r/radarr
**Timing:** 48 hours after r/selfhosted post (per D-06)

---

**Title:** SeedSyncarr: seedbox sync tool that triggers Radarr imports automatically via webhook

---

If you run Radarr with a seedbox, you know the gap: Radarr grabs the movie, your torrent client downloads it to the seedbox, but syncing it home and triggering the Radarr import is the part that never quite works automatically. You end up with rsync scripts, manual transfers, or hoping remote path mapping handles it.

SeedSyncarr closes that gap. It syncs files from your seedbox to your local server using LFTP (parallel connections, segmented downloads -- handles large movie files well), then calls Radarr's webhook endpoint to trigger an import scan. The import fires automatically when the sync completes.

## How it works with Radarr

1. Your torrent client downloads a movie to the seedbox
2. SeedSyncarr detects the new file and syncs it to your local download directory via LFTP over SSH
3. When the sync finishes, SeedSyncarr sends a webhook notification to Radarr
4. Radarr runs its import scan, matches the file, and moves it into your library

The webhook request is signed with HMAC-SHA256 -- not just a bare HTTP call.

## Features relevant to Radarr users

- **LFTP-based transfers** -- parallel connections and segmented downloads handle large movie files efficiently
- **Auto-extraction** -- packed releases get extracted automatically after sync
- **Webhook-triggered imports** -- Radarr import fires on sync completion, not on a timer
- **HMAC-SHA256 authentication** -- webhook requests are cryptographically signed
- **AutoQueue** -- define patterns to automatically sync only the movies you want
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
- **Radarr/Sonarr setup guide:** https://thejuran.github.io/seedsyncarr/arr-setup/
- **Container:** `ghcr.io/thejuran/seedsyncarr:latest`

The docs have a step-by-step guide for configuring the Radarr webhook integration. Happy to answer questions if anyone has a similar seedbox-to-local workflow.
