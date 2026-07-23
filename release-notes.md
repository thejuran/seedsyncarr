A reliability release driven by a real incident: a download that finished on the seedbox was silently never synced, because leftover tracking from an earlier download of the same release name blacklisted it — and the dashboard gave no hint anything was stuck.

Existing config and persist files (including encrypted ones) load unchanged, with no migration step.

### What changed for you

- **Re-grabbing a release you've had before now works** — Previously, if Sonarr/Radarr re-grabbed a release that SeedSyncarr had already synced and imported in the past, the file was silently skipped forever. Now, a release that has been gone from both the seedbox and local storage for over 24 hours and then re-appears is treated as a fresh download and syncs automatically.
- **Interrupted syncs recover** — A transfer killed mid-download (container restart, lftp crash) whose partial file disappeared used to be marked Deleted and never re-queued. It now simply re-queues.
- **No more phantom "imported" marks** — Import detection now requires the actual imported-file path in the webhook payload. An event without it can no longer mark a file imported (and arm auto-delete) by title coincidence, and every import mark is logged with the exact webhook event that caused it.
- **Stuck files are visible** — A file that exists on the seedbox but is intentionally not being downloaded now shows an amber "Skipped (remote)" badge instead of blending in with deleted files.
- **Sturdier dashboard** — The initial file list loads as one snapshot instead of hundreds of individual events (much faster first render with large libraries), a single bad update can no longer silently freeze the file list, and the System Event Log no longer shows an endless spinner when there are simply no recent events.

### Should you update?

Yes — especially if you use the Sonarr/Radarr webhook integration or ever re-download releases. The fixes remove a silent data-flow failure mode where a wanted download never arrives and nothing tells you.

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md
