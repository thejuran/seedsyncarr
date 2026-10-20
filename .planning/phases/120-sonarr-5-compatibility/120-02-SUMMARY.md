---
phase: 120-sonarr-5-compatibility
plan: 02
subsystem: operator-tooling
tags: [sonarr5, sanitizer, webhook-sink, operator-tooling]
requires: []
provides:
  - ".planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py (raw capture -> placeholder fixture, counts-only stderr)"
  - ".planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py (disposable 0600 webhook body capture)"
affects: [120-05, 120-06]
tech-stack:
  added: []
  patterns: ["stdlib-only operator script with fail-closed entrypoint (119.1 precedent)", "O_EXCL 0600 file creation", "silenced BaseHTTPRequestHandler.log_message"]
key-files:
  created:
    - .planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py
    - .planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py
  modified: []
decisions:
  - "Sanitizer writes NO output file when RESIDUAL > 0 (exit 2): a partly sanitized capture never lands on disk"
  - "startTime/buildTime are kept as-is per the plan action (RESEARCH listed them for replacement; ISO timestamps are not personal)"
  - "Image URLs without a host (Sonarr's relative /MediaCover/... url) are left untouched; only hosted url/remoteUrl are rewritten to https://images.example.invalid, keeping path and query"
metrics:
  duration: ~15min
  completed: 2026-10-20
  tasks: 2
  files: 2
---

# Phase 120 Plan 02: Fixture Sanitizer and Webhook Sink Summary

This plan adds two stdlib-only operator scripts that Plans 05 and 06 need. The first is a fixture sanitizer. It substitutes mapping keys longest-first, re-validates the JSON, neutralises identity fields by key, writes its output with O_EXCL and mode 0600, and prints only counts. It exits 2 if any mapping key survives. The second is a disposable webhook sink. It saves each POST body byte-for-byte to a 0600 file, plus a sidecar file holding only the User-Agent, and rejects bodies over 1 MB with a 413.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Fixture sanitizer script with local self-check | 70330ff | 120-sanitize_fixtures.py |
| 2 | Disposable webhook sink script with local self-check | 63ffc94 | 120-webhook_sink.py |

## Verification (observed output)

**Task 1, sanitizer** (self-check run from the scratchpad):
- Derived sample (`/home/user/` changed to `/home/sampleuser/`, `Indexer (Prowlarr)` changed to `SampleTracker (Prowlarr)`) with a 2-key mapping: `rc=0`, stderr exactly `REPLACED n=2 RESIDUAL=0`, `roundtrip OK`. The output was byte-for-byte identical to the source sample (`cmp`). Output mode was `600`.
- A mapping that leaves out `/home/sampleuser/` and includes a key still present in the text: `rc=2`, `REPLACED n=2 RESIDUAL=1`, no output file written.
- Running against an existing output file: `rc=3`, `ERROR FileExistsError`. The existing file was not overwritten.
- A mapping with an empty key: `rc=3`, `ERROR ValueError`.
- Identity and image pass: `instanceName` became `Sonarr`, `applicationUrl` became `""`, `startupPath` became `/app/sonarr/bin`, and `buildTime` was kept. The relative image `url` was unchanged. The remote image host was rewritten to `images.example.invalid` with its path and query kept. Path basenames were unchanged.
- Greps: `O_EXCL`=2, `ensure_ascii=False`=1, `reverse=True`=1. The only stderr writes are the `REPLACED`/`RESIDUAL` line and the `ERROR <class>` line. There are no `print(` calls.
- `ruff check` on the script: `All checks passed!`

**Task 2, sink** (self-check run on 127.0.0.1:18080):
- `post=200`, `bytes OK` (`cmp` against the sample), body mode `600`, meta mode `600`, meta grep count for `Sonarr/5.0.0.2701` was `1`, `big=413`, `files=1`, `/healthz` returned `ok`, the sink exited cleanly on SIGTERM (`sink_exit=0`), stdout and stderr were both 0 bytes.
- Greps: `O_EXCL`=3, `1_048_576`=2, `def log_message`=1. The only headers read are `Content-Length` and `User-Agent`.
- `ruff check` on the script: `All checks passed!`

Nothing under `src/python/` changed, so the whole-tree `ruff check src/python/` gate is unaffected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Self-checks ran against stand-in samples, not the `src/python/tests/fixtures/sonarr5/` files**
- **Found during:** Task 1
- **Issue:** Both `<verify>` blocks read `src/python/tests/fixtures/sonarr5/queue_details_incomplete.json` and `webhook_test.json`. Plan 01 creates those files, and it runs in parallel in another worktree, so they don't exist in this worktree. The verify blocks also hardcode a scratchpad path from another session.
- **Fix:** I generated scratchpad copies of both fixtures from Plan 01's spec: the same record keys, the placeholder values, 40-hex ids ending in 1 and 2, `/home/user/v5test/...` output paths, and the Sonarr Test body. I then ran the same self-check steps against them. The scripts don't depend on the fixtures; only the self-check uses them.
- **Follow-up:** after the wave merges, run the Task 1 roundtrip once against the real Plan 01 fixture. One case could fail the roundtrip: a hosted `images[].url`, or any of the neutralised keys holding a non-placeholder value. That would mean the fixture breaks the placeholder convention, not that the sanitizer is wrong.

**2. [Rule 2 - Security] The sanitizer writes no output on a residual**
- **Found during:** Task 1
- **Issue:** The plan's action text writes the output and then counts residuals. That would leave a partly sanitized capture on disk whenever exit is 2.
- **Fix:** The script counts residuals on the rendered text first and writes the O_EXCL 0600 file only when `RESIDUAL=0`. The exit codes and stderr contract are unchanged.

**3. [Rule 2 - Robustness] Sink handles missing and malformed lengths**
- **Found during:** Task 2
- **Fix:** A missing `Content-Length` returns 411. A malformed or negative length, or a short body, returns 400. A 30 s socket timeout drops stalled clients. If the sink directory is missing, the script prints `ERROR sink directory missing` and exits 2 rather than creating the directory.

**4. [Cosmetic] Docstring reworded**
- The acceptance criterion expects exactly one `ensure_ascii=False`, and the docstring repeated the literal call. I described it in prose instead.

## Known Stubs

None.

## Threat Flags

None. T-120-04..07 are mitigated as the register describes. The sink binds 0.0.0.0 by design; the threat model already covers this (shared network, no published port, capture window only).

## Self-Check: PASSED

- FOUND: .planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py
- FOUND: .planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py
- FOUND: 70330ff
- FOUND: 63ffc94
