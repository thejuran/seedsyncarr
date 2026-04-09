# Servarr Discord Announcement

**Target:** Servarr Discord (discord.gg/SkXFKr5gHj)
**Channel:** Look for #third-party-tools, #showcase, or #community-projects. If none exists, use #general with a note.
**Timing:** 48 hours after r/selfhosted post (per D-06)
**Format:** Discord markdown (backticks for code, keep under 2000 chars or use thread)

---

**SeedSyncarr -- LFTP-based seedbox sync with native Sonarr + Radarr webhook integration**

Built a seedbox sync tool that fits into an existing *arr stack. SeedSyncarr uses LFTP to sync files from your seedbox over SSH, then fires webhook notifications to Sonarr and Radarr to trigger media imports automatically.

**How it fits the stack:**

SeedSyncarr sits between your torrent client (on the seedbox) and your Sonarr/Radarr instances (local). When a sync completes, it calls the configured webhook endpoint on Sonarr or Radarr to trigger an import scan. It runs alongside your existing setup -- no conflicts, no overlap with what Sonarr and Radarr already do.

**Webhook integration details:**

- HMAC-SHA256 webhook authentication -- requests are signed, not just sent
- Bearer token API authentication with TOFU SSH
- Auto-delete after successful import (configurable)
- Per-instance webhook configuration for Sonarr and Radarr separately

**Security:**

- Hash-based Content Security Policy headers
- DNS rebinding prevention
- Path traversal guards on all file operations
- SSRF protection on *arr endpoint URLs

**Quick start:**

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

**Links:**
- GitHub: https://github.com/thejuran/seedsyncarr
- Sonarr/Radarr setup guide: https://thejuran.github.io/seedsyncarr/arr-setup/

Fork of SeedSync (by IrealiTY), rebuilt with *arr integration, security hardening, dark mode UI, and a full test suite. Open to feedback -- especially from anyone running a multi-instance *arr setup.
