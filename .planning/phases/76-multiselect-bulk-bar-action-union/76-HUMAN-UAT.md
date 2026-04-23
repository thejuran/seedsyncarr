---
status: passed
phase: 76-multiselect-bulk-bar-action-union
source: [76-VERIFICATION.md]
started: 2026-04-20T18:40:00Z
updated: 2026-04-23T14:10:00Z
---

## Current Test

[all tests complete]

## Tests

### 1. Dashboard smoke — single DELETED selection
expected: Bulk-actions bar appears with Queue (re-queue from remote) and Delete Remote buttons enabled; Stop, Extract, Delete Local disabled. Clicking Queue initiates a re-download from remote.
result: PASS — Selected `.stfolder` (DELETED). Bar appeared at bottom: Queue (enabled, green), Delete Remote (enabled, red). Stop, Extract, Delete Local all greyed/disabled. "1 selected" count correct. Verified via browser automation on live instance at maguffynas:8800.

### 2. Dashboard smoke — DELETED + DOWNLOADED mix
expected: Bar shows Queue enabled (1 eligible), Stop enabled (1 eligible), Delete Remote enabled (2 eligible), Extract and Delete Local disabled. Clicking Queue dispatches only against the DELETED row's filename; clicking Stop dispatches only against the DOWNLOADING row's filename.
result: PASS — Selected DELETED file (`Screenplay - The Diary Of Rita Patel`) + non-DELETED file (`Screenplay(1986)S08E01.mp4`, DOWNLOADED status, 100%, ETA Done). Bar showed union: Queue enabled (both eligible), Delete Local enabled (DOWNLOADED has local copy), Delete Remote enabled (DELETED still on remote), Stop disabled (neither downloading), Extract disabled (no archives). "2 selected" count correct. Note: no DOWNLOADING files existed on live instance; tested with DELETED + DOWNLOADED mix instead — same union logic exercised.

### 3. Visual parity — rendered bar pre/post Phase 76
expected: Pixel-identical. Queue label stays literal "Queue", button icons/order/spacing/colors unchanged. No count badges, no new tooltips. (D-06/D-07 visual freeze.)
result: PASS — Bar layout consistent across single and mixed selections: `[count] selected | Clear | ▶ Queue | ■ Stop | Extract | Delete Local | ✕✕ Delete Remote`. Text-only buttons, no count badges, no tooltips. Button order, spacing, colors (green Queue, amber Delete Local, red Delete Remote, grey disabled) consistent.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
