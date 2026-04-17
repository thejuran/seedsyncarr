---
created: 2026-04-17T04:26:15.351Z
title: Add dashboard filter for every torrent status
area: ui
files: []
---

## Problem

The dashboard currently lacks a way to filter torrents by every possible status. Users need full filtering coverage so they can isolate torrents in any state (e.g., downloading, seeding, paused, queued, stalled, checking, error, completed) without scrolling through the full list.

Target: include this in the next milestone.

## Solution

TBD — explore during next milestone planning. Likely approaches:
- Status filter chips or multi-select above the torrent list
- Enumerate all statuses emitted by the backend (verify full set vs. qBittorrent/Transmission states)
- Persist selected filters across sessions
- Ensure "all" / "none" quick toggles exist
