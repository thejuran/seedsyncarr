# Phase 116: Import Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-10-08
**Phase:** 116-import-safety
**Mode:** default (compressed — finding surfaced first, three decisions asked in one turn)

## Finding presented
`AutoDeleteManager.run_bfs_and_coverage` builds `on_disk_videos` as a set of lowercased basenames, so `Disc1/movie.mkv` + `Disc2/movie.mkv` collapse and one recorded import covers both. Import-side rejection stops new bad credits but not legacy pre-1.7.4 records.

## Duplicate-name packs
- Options: Yes, keep them (Recommended) / No, find another way (path-mapping)
- Selected: Yes, keep them — such packs never auto-delete; manual removal.

## Delete-time guard
- Options: Add the delete-time guard (Recommended) / Import-side fix only
- Selected: Add the guard. Owner notes: reject duplicate case-insensitive basenames across distinct file paths, leave pack untouched, log why; add a regression proving legacy "fully covered" records cannot override the guard.

## Visibility
- Options: Log warning only (Recommended) / Also show in the UI
- Selected: Log only. Owner notes: include filename, candidate releases, and that no import credit or automatic cleanup was authorized; for within-pack duplicates include the distinct relative paths; keep names sanitized; no UI work.

## Todos
- webob-cgi-upstream-unblock: reviewed, not folded (keyword-only match).

## Claude's Discretion
- Multi-path lookup structure/location; log level/wording beyond required content; retriable vs terminal skip classification (must never delete).
