---
phase: 126-release-1-8-0
plan: 02
subsystem: release-ops
tags: [release, smoke-harness, nas-sandbox, idempotent-teardown, count-only-secrets, positive-control, puppeteer]

# Dependency graph
requires:
  - phase: 126-01
    provides: release/1.8.0 local branch with every open Dependabot PR rolled in
provides:
  - 126-teardown.sh (idempotent sandbox restore, extended with radarr_url/radarr_enabled
    and value-free *arr API key restore, SSA126.-prefixed synthetic-root cleanup,
    probe126 throwaway container/dir cleanup, --revert-image)
  - 126-webhook-post.sh (generalized signed sonarr|radarr Download|Test webhook poster)
  - 126-extract_secrets.py (verbatim copy of 119.1's count-only secret extractor)
  - 126-token-probe.mjs (browser-side GitHub-token-leak probe, positive-control proven)
  - 126-SMOKE-EVIDENCE.md harness section (sha256s, positive-control PASS, dry-run, prod
    fingerprint before/after)
affects: [126-04, 126-05, 126-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CORS-preflight-aware request interception for an Authorization-header browser
      check: answer OPTIONS with Access-Control-Allow-Headers/-Methods and exclude the
      preflight itself from the measured count, or the browser silently drops the real
      request and the probe is vacuous"
    - "networkidle2 (not networkidle0) navigation wait for apps holding a long-lived SSE
      connection open"
    - "Positive-control-first proof for any probe that measures the absence of a
      header/value: run it against a known-leaking build first and require a non-zero
      result before trusting a zero result on the fixed build"

key-files:
  created:
    - .planning/phases/126-release-1-8-0/126-teardown.sh
    - .planning/phases/126-release-1-8-0/126-webhook-post.sh
    - .planning/phases/126-release-1-8-0/126-extract_secrets.py
    - .planning/phases/126-release-1-8-0/126-token-probe.mjs
    - .planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md
  modified: []

key-decisions:
  - "Probe-dir cleanup uses a plain `rm -rf`, not `sudo rm -rf`: the NAS's passwordless
    sudoers rule covers only the docker/docker-compose absolute paths, and the probe
    dirs are already owned by the SSH session's own uid/gid (PUID/PGID-mapped), so no
    sudo is needed or safe to assume non-interactively"
  - "sonarr_api_key/radarr_api_key restore written as two explicit literal blocks
    (matching the sonarr_url/radarr_url style already in the file) instead of one
    generic parameterized function, so the required literal 'RESTORED sonarr_api_key'/
    'RESTORED radarr_api_key' text is present for static verification"
  - "Token probe answers CORS preflight OPTIONS requests to api.github.com separately
    from the real request and excludes the preflight from GITHUB_REQUESTS, otherwise the
    browser drops the authenticated request after a failed preflight and the probe
    always reports WITH_AUTH=0 regardless of real behavior"

patterns-established:
  - "Positive-control-first proof for absence-of-header probes (run against a
    known-leaking build before trusting a zero result on the target build)"

requirements-completed: [REL-06]

# Metrics
duration: 22min
completed: 2026-10-28
---

# Phase 126 Plan 02: 1.8.0 Sandbox Smoke Harness Summary

**Extended teardown/webhook/secret-extractor scripts plus a new puppeteer-based browser
token-leak probe, with the probe's positive control proven live against a throwaway 1.7.6
container (WITH_TOKEN=1) and the extended teardown proven safe in a no-op dry run against
the live sandbox — production never touched.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-10-28T20:05:51Z
- **Completed:** 2026-10-28T20:27:43Z
- **Tasks:** 2 completed
- **Files modified:** 5 (4 harness files + 1 evidence doc)

## Accomplishments

- `126-teardown.sh`: copied `125-teardown.sh` as the base and added `get_radarr_url`/
  `set_radarr_url` and `get_radarr_enabled`/`set_radarr_enabled` mirroring the existing
  `sonarr_url` pair; added value-free `sonarr_api_key`/`radarr_api_key` restore from 0600
  `<capture-dir>/{sonarr,radarr}_key.l0` files (jq `--rawfile`, single-field read-back
  comparison, never the full config response); copied 122's `SSA126.`-prefixed
  synthetic-root cleanup block; added `seedsyncarr-probe126*` container and
  `/volume1/docker/probe126-*` dir cleanup; replaced `--final` with `--revert-image`
  (image-pin restore is now opt-in since the sandbox is allowed to stay on the published
  1.8.0 tag by default per D-11)
- `126-webhook-post.sh`: generalized `122-webhook-post.sh` to `<capture-dir> <sonarr|radarr>
  <Download|Test> <root> <child-or-root>`, rejecting any other source/eventType/root
  prefix with exit 2; Radarr Download body uses `movieFile.sourcePath`/`instanceName:
  "Radarr"` (confirmed against `src/python/web/handler/webhook.py`); Test body is
  `{"eventType":"Test","instanceName":"<Sonarr|Radarr>"}`; HMAC stays stdin-only
- `126-extract_secrets.py`: byte-identical copy of `119.1-extract_secrets.py`
  (sha256 `c35768d7...baef6` on both sides)
- `126-token-probe.mjs`: new puppeteer script; intercepts every request to
  `api.github.com`, prints exactly one line (`GITHUB_REQUESTS=<n> WITH_AUTH=<n>
  WITH_TOKEN=<n>`), never a header value; exit 0 when at least one GitHub request was
  observed, exit 3 when none were (inconclusive, not a pass)
- Positive control run live on the NAS: a throwaway `seedsyncarr-probe126-ctl` container
  on the exact 1.7.6 digest (`sha256:da6196e0...`), `api_token` set to a synthetic value,
  probed through an SSH tunnel from the Mac — result `GITHUB_REQUESTS=1 WITH_AUTH=1
  WITH_TOKEN=1`, confirming the pre-SEC-02 interceptor leaks the app token to GitHub and
  that the probe correctly detects it
- Cleaned up the throwaway container and scratch dir via `126-teardown.sh`; confirmed
  zero `seedsyncarr-probe126*` containers and no `/volume1/docker/probe126-*` dir remain
- Teardown dry run against the live sandbox with a fresh, empty capture dir: every
  restore line printed `ok (not set this session)`, the sandbox stayed on its current
  image, exit 0
- Production fingerprint (`docker inspect seedsyncarr`) recorded before and after the
  entire session: identical container Id, image and `StartedAt`

## Task Commits

1. **Task 1: Write 126-teardown.sh, 126-webhook-post.sh and copy 126-extract_secrets.py**
   - `a199948c` (chore)
2. **Task 2: 126-token-probe.mjs with a positive control on 1.7.6, teardown dry run on
   the live sandbox** - `a69cb7b9` (chore) — also carries a Rule 3 fix to `126-teardown.sh`
   (see Deviations)

**Plan metadata:** this SUMMARY.md commit (next)

_No TDD tasks in this plan (release-engineering tooling, not application behavior); no
test→feat→refactor cycle applies._

## Files Created/Modified

- `.planning/phases/126-release-1-8-0/126-teardown.sh` - extended idempotent sandbox
  restore (radarr_url/radarr_enabled/api-key restore, SSA126 synth-root cleanup,
  probe126 cleanup, --revert-image)
- `.planning/phases/126-release-1-8-0/126-webhook-post.sh` - generalized signed
  sonarr/radarr Download/Test webhook poster
- `.planning/phases/126-release-1-8-0/126-extract_secrets.py` - verbatim copy, sha256
  identical to 119.1's extractor
- `.planning/phases/126-release-1-8-0/126-token-probe.mjs` - puppeteer GitHub-token-leak
  probe
- `.planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md` - harness section: sha256s,
  positive-control transcript and PASS verdict, cleanup confirmation, dry-run transcript,
  production fingerprint before/after

## Decisions Made

- Probe-dir cleanup uses plain `rm -rf` instead of `sudo rm -rf` (see Deviations #6) —
  matches the NAS's actual passwordless-sudo scope (docker/docker-compose only)
- `sonarr_api_key`/`radarr_api_key` restore written as two explicit literal blocks rather
  than one generic parameterized function, so the acceptance-mandated literal `RESTORED
  sonarr_api_key`/`RESTORED radarr_api_key` text is present in the script source for
  static verification — also keeps this block's style consistent with the file's
  existing `sonarr_url`/`radarr_url` blocks rather than introducing a one-off abstraction
- Synthetic-root prefix check uses an anchored bash regex (`[[ "$name" =~ ^SSA126\. ]]`)
  instead of a shell case-glob, so the literal `^SSA126` text required by the acceptance
  criteria is present and the check reads as an explicit anchored match

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Generic API-key restore function didn't satisfy the literal-text acceptance gate**
- **Found during:** Task 1, running the acceptance-criteria grep checks
- **Issue:** A single parameterized `restore_api_key()` function printed `"RESTORED
  ${field} ok"` — the literal substring `RESTORED sonarr_api_key` never appears in the
  script source (only the runtime-interpolated form does), so the plan's static
  `grep -c 'RESTORED sonarr_api_key'` acceptance check failed (0 matches)
- **Fix:** Rewrote as two explicit blocks (one per key) with literal echo text, matching
  the existing `sonarr_url`/`radarr_url` restore style in the same file
- **Cost if wrong:** None materially — this only affects whether a later evidence/CI
  grep can statically confirm the restore path exists; the runtime restore logic itself
  was already correct either way
- **Files modified:** `126-teardown.sh`
- **Commit:** `a199948c` (part of Task 1 commit; fixed before commit)

**2. [Rule 1 - Bug] Synthetic-root prefix check didn't contain the required literal `^SSA126` text**
- **Found during:** Task 1, running the acceptance-criteria grep checks
- **Issue:** The case-glob form `case "$name" in SSA126.*)` is functionally correct but
  contains no literal `^` character, so `grep -c '\^SSA126' 126-teardown.sh` (an
  acceptance criterion) returned 0
- **Fix:** Switched to an anchored bash regex, `[[ ! "$name" =~ ^SSA126\. ]]`, which is
  both functionally equivalent and satisfies the literal-text check
- **Cost if wrong:** None — same refuse/accept behavior either way; purely a
  verifiability improvement
- **Files modified:** `126-teardown.sh`
- **Commit:** `a199948c` (part of Task 1 commit; fixed before commit)

**3. [Rule 3 - Blocking] shellcheck SC2318 warning in the original `restore_api_key` helper**
- **Found during:** Task 1, running shellcheck
- **Issue:** `local src="$1" ... file="$D/${src}_key.l0"` used `$src` in the same `local`
  statement that assigns it, which shellcheck flags as potentially not seeing the new
  value
- **Fix:** Split into two `local` statements (moot once the function was later removed
  entirely per deviation #1, but the fix was applied and verified clean before that)
- **Cost if wrong:** None — shellcheck-only, no runtime behavior change
- **Files modified:** `126-teardown.sh`
- **Commit:** `a199948c` (part of Task 1 commit; fixed before commit)

**4. [Rule 1 - Bug] Token probe timed out against a real app holding a persistent SSE connection**
- **Found during:** Task 2, first live run against the throwaway 1.7.6 container
- **Issue:** `page.goto({waitUntil: "networkidle0"})` never resolves when the page keeps
  one network connection permanently open (SeedSyncarr's live model-stream SSE
  connection) — the probe failed with `ERROR TimeoutError` on every real-app run
- **Fix:** Switched to `networkidle2` (tolerates up to 2 persistent connections) with an
  explicit 45s navigation timeout, keeping the plan's "network idle plus 5s" wait after
- **Cost if wrong:** If under-tolerant, the probe would falsely report 0 GitHub requests
  (exit 3, inconclusive) on a working app, blocking the smoke rather than passing it
  silently — the live positive-control run below confirms it resolves correctly
- **Files modified:** `126-token-probe.mjs`
- **Commit:** `a69cb7b9`

**5. [Rule 1 - Bug] Mocked GitHub response didn't satisfy a CORS preflight, silently dropping the real authenticated request**
- **Found during:** Task 2, local sanity test before the live NAS run (an authenticated
  fetch reported `WITH_AUTH=0` when it should have reported `1`)
- **Issue:** A cross-origin request carrying a non-safelisted `Authorization` header
  always triggers a CORS preflight `OPTIONS` request first. The original mock answered
  every `api.github.com` request (including the preflight) with only
  `Access-Control-Allow-Origin: *`, which is insufficient for a preflight
  (`Access-Control-Allow-Headers`/`-Methods` are also required); the browser silently
  dropped the real authenticated request after the failed preflight, which would have
  made the probe report `WITH_AUTH=0`/`WITH_TOKEN=0` on every build regardless of actual
  interceptor behavior — a vacuous probe (the exact failure mode threat T-126-08 exists
  to catch)
- **Fix:** Answer `OPTIONS` requests to `api.github.com` with
  `Access-Control-Allow-Methods`/`-Headers` and exclude the preflight itself from
  `GITHUB_REQUESTS`; verified with three local sanity cases (authenticated fetch,
  unauthenticated fetch, no GitHub call at all) before re-running against the NAS
- **Cost if wrong:** Exactly the T-126-08 failure mode — a vacuous probe that always
  reports a false pass regardless of whether 1.8.0 actually fixed the leak; caught here
  specifically because the plan mandates a positive control before trusting the probe
- **Files modified:** `126-token-probe.mjs`
- **Commit:** `a69cb7b9`

**6. [Rule 3 - Blocking] `sudo rm -rf` for probe-dir cleanup hangs under non-interactive SSH**
- **Found during:** Task 2, the first live teardown run after the positive control
  (`REMOVED probe dir FAIL`, container removed but directory left behind)
- **Issue:** The NAS's passwordless sudoers rule (per the owner's global CLAUDE.md) only
  covers the `docker`/`docker-compose` absolute paths; a non-interactive `sudo rm -rf`
  call has no TTY for a password prompt and fails silently (stderr suppressed by the
  script's own `2>/dev/null`)
- **Fix:** Switched to a plain `rm -rf` for the probe dirs — confirmed safe by inspecting
  the dir's contents (`ls -la`), which showed every file owned by the SSH session's own
  uid/gid (1026:100), matching the throwaway container's `PUID`/`PGID`, so no elevated
  privilege is actually needed
- **Cost if wrong:** If some future throwaway image wrote root-owned files into the probe
  dir, this plain `rm -rf` would leave those files behind (same `REMOVED probe dir FAIL`
  outcome as the bug fixed here, not data loss or incorrect removal) — re-verified live
  this session, not merely inferred
- **Files modified:** `126-teardown.sh`
- **Commit:** `a69cb7b9`

---

**Total deviations:** 6 auto-fixed (2 Rule 1 bugs, 1 Rule 1 live-session finding re-fixed
as a bug in the committed script, 3 Rule 3 blocking issues; grouped above as 2 Rule 1 bug
fixes to the probe script, 1 shellcheck/Rule 3 cleanup, 2 acceptance-gate Rule 3/Rule 1
fixes to the teardown script's text, and 1 Rule 3 NAS-sudo environment fix)
**Impact on plan:** All six fixes were necessary either for correctness (the probe would
otherwise be silently vacuous, or the teardown script would silently leave scratch dirs
behind) or for the plan's own static-verification acceptance gates to pass. No scope
creep — nothing outside the four harness files and the evidence doc was touched.

## Issues Encountered

None beyond the auto-fixed deviations above. Every automated `<verify>` command in both
tasks was run and its real output observed (`T1_OK`, `T2_OK`), not assumed.

## User Setup Required

None - no external service configuration required. The NAS positive control and dry run
both ran against existing infrastructure (`seedsyncarr-test`, a throwaway container) that
the owner has already authorized for sandbox use in this phase's CONTEXT.md.

## Next Phase Readiness

- The three new D-12a capabilities this phase's harness needed (radarr wiring restore,
  Test-event webhook posting, browser-side token check) are now built and proven —
  Plan 126-04's sandbox smoke on the exact published `:1.8.0` digest can use them
  directly
- `126-teardown.sh`'s `--revert-image` flag is ready for use once the sandbox is repinned
  to `:1.8.0` and later needs restoring to `IMAGE_PIN_L0` (1.7.6)
- The token probe is proven non-vacuous (positive control PASS on 1.7.6); running it
  against the published 1.8.0 digest in Plan 126-04 should report `WITH_TOKEN=0` per
  Phase 121's fix — if it reports `WITH_TOKEN>=1` instead, that is a real regression, not
  a probe artifact
- No blockers carried forward

---
*Phase: 126-release-1-8-0*
*Completed: 2026-10-28*

## Self-Check: PASSED

- FOUND: .planning/phases/126-release-1-8-0/126-teardown.sh
- FOUND: .planning/phases/126-release-1-8-0/126-webhook-post.sh
- FOUND: .planning/phases/126-release-1-8-0/126-extract_secrets.py
- FOUND: .planning/phases/126-release-1-8-0/126-token-probe.mjs
- FOUND: .planning/phases/126-release-1-8-0/126-SMOKE-EVIDENCE.md
- FOUND: a199948c (chore: Task 1 harness scripts)
- FOUND: a69cb7b9 (chore: Task 2 token probe + positive control)
