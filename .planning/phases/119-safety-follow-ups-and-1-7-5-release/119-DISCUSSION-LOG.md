# Phase 119: Safety Follow-ups and 1.7.5 Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-10-14
**Phase:** 119-safety-follow-ups-and-1-7-5-release
**Areas discussed:** Items arr can't vouch for, Hold visibility, Retry limit, Matched todo

## Items Sonarr/Radarr can't vouch for
- Options: Strict hold + manual release (recommended) / Hold forever / Exempt non-arr items
- Selection: Option 1 with an explicit override. Existing Queue must not silently bypass safety; require confirmation "Completion could not be verified. Transfer and release this item anyway?"; approval applies only to that transfer attempt. Absent queue entry doesn't prove an item is unrelated to arr, so exemption is unreliable. Record manual release as an explicit exception to IMP-01/02 and a small justified exception to "no UI features".

## Hold visibility
- Options: File status + log (recommended) / Also bell notification / Log only
- Selection: File status + log. Waiting state in the existing file list with reason ("Sonarr unavailable", "Ambiguous match", "Still downloading"). Log on reason change or hold clear, not every retry. Auto-retry and auto-clear on verification. No bell this milestone.

## Retry limit
- Options: Retry indefinitely (recommended) / Give up and flag
- Selection: Retry indefinitely; never release on timeout. Capped backoff, queue checks shared across waiting items; log state changes only.

## Matched todo
- `webob-cgi-upstream-unblock` — left out (unrelated, upstream-blocked).

## Claude's Discretion
- Gating point(s), hold-state data structures, backoff constants, queue-match algorithm (within D-04/D-05), credit persistence format, packaging fix, LFTP resync mechanism.
- Decided without asking: temp-file transfer mandatory for automatic transfers regardless of `use_temp_file`.

## Deferred Ideas
- Bell notification for long holds; backlog 999.1.
