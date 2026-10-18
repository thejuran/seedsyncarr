---
status: complete
phase: 119-safety-follow-ups-and-1-7-5-release
source: [119-VERIFICATION.md]
started: 2026-10-15T16:25:50Z
updated: 2026-10-18T18:51:00Z
---

## Current Test

[complete — walkthrough 20261018-184100-close-out-outstanding-uat on the 1.7.6 sandbox (seedsyncarr-test, :8801) with a 4-byte remote probe file; prod untouched]

## Tests

### 1. Waiting badge renders for a held file
expected: A DEFAULT file with a hold reason shows a secondary-styled 'Waiting' badge; hovering shows the reason label (e.g. 'Sonarr unavailable') as the title; the same label appears in the file-meta line.
result: pass — 2026-10-18 on 1.7.6. Probe held after the 90 s remote-stability window ("Completion hold … No matching queue entry"); gray WAITING badge whose title is "No matching queue entry"; meta line "uat-hold-probe.txt • 4 B • No matching queue entry".

### 2. Manual-release confirm modal through the UI
expected: Queue on a 428-held file shows the modal with verbatim text 'Completion could not be verified. Transfer and release this item anyway?' plus the file preview; OK re-dispatches once with release_unverified; Cancel sends no request.
result: pass — 2026-10-18 on 1.7.6. Queue refused (bulk per-file 428, logged "Completion could not be verified: No matching queue entry"); dialog "Release unverified transfer" with the verbatim text plus "uat-hold-probe.txt", Cancel focused by default. Cancel: no further request, row stayed Waiting. Release (the OK button): exactly one re-dispatch, WARN "Manual release of unverified … bypassed for this transfer only", hold cleared, file Synced 4 B and persisted across reload. Note: the confirm button is labeled "Release", not "OK".

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
