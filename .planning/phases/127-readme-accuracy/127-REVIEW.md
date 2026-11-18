---
phase: 127-readme-accuracy
reviewed: 2026-11-18T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - README.md
  - SECURITY.md
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 127: Code Review Report

**Reviewed:** 2026-11-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the README.md and SECURITY.md changes in `1a1e3443..HEAD`. Each changed claim was checked against the code:

- `src/python/seedsyncarr.py` (`_create_default_config`, `_emit_startup_warnings`)
- `src/python/common/config.py`
- `src/python/web/handler/webhook.py`
- `src/python/web/web_app.py` (auth hook, exemptions, CSP, token meta injection)
- `src/python/controller/controller.py` (import evidence gate, auto-delete schedule/defer/execute)
- `src/python/controller/model_pipeline.py` and `model_builder.py` (how the "downloaded" list is populated)
- the rate-limit decorators in `web/handler/*`

These claims are accurate:

- The defaults: `api_token=""`, `webhook_secret=""`, `webhook_require_secret=False`, `autodelete.enabled=False`, `dry_run=False`, `delay_seconds=60`, `encryption.enabled=False`.
- The webhook behavior: 401 when the `X-Webhook-Signature` header is missing or wrong while a secret is set; 503 when the secret is required but none is set; HMAC-SHA256 over the raw body.
- The bounded deferral of 24 re-arms followed by give-up, and that pruning deletes only the local copy.
- The five rate-limited endpoints and their budgets.
- All relative links and anchors resolve, including `docs/*.md`, `CONTRIBUTING.md`, `LICENSE`, `#how-it-works` and `#security`.

Two security claims still overstate the protection. Both were introduced or restated in this phase:

1. **`api_token` coverage.** Both files say the token covers the whole API, with webhooks as the only exception. In fact `/server/stream`, which carries live application logs and the full file model, and `/server/status` are also exempt.
2. **Which releases pruning can delete.** The docs say pruning only touches releases SeedSyncarr "itself downloaded". The code's actual test is weaker: any complete local copy whose name matches a remote item qualifies.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `api_token` described as covering the whole API, but the SSE stream (live logs and file model) and status endpoint stay unauthenticated

**File:** `README.md:53`, `README.md:207-208`, `SECURITY.md:44`
**Issue:** README line 207-208 says "`api_token` does not authenticate the webhook endpoints, which are exempt from the Bearer check". That presents the webhooks as the only exception. SECURITY.md:44 says "The `/server/*` API requires a Bearer token when `api_token` is set". `web_app.py:59-61` also exempts `/server/stream` and `/server/status` from the Bearer check, whatever `api_token` is set to:

```python
_AUTH_EXEMPT_PATHS = {
    "/server/stream",      # SSE — EventSource cannot send custom headers (R003)
    "/server/status",      # Health check
}
```

`/server/stream` carries `LogStreamHandler`, which forwards every application log record with a 3 s replay cache, and `ModelStreamHandler`, which sends every remote and local file name, size and state. A user who sets `api_token`, believing the README's list of exceptions, still leaks live logs and the full seedbox/library inventory to anything that can reach port 8800. This is the misleading-into-unsafe-setup case the phase exists to fix.

**Fix:** Name all the exemptions in both files, e.g. README:

```markdown
- **API authentication** is off while `api_token` is empty. Even when it is set, it does not
  cover the webhook endpoints, the live event stream (`/server/stream`, which carries
  application logs and the file list) or the status endpoint (`/server/status`).
```

In SECURITY.md:44, replace "The `/server/*` API requires a Bearer token" with "The `/server/*` API, except the webhook endpoints, `/server/stream` (SSE: logs and file model) and `/server/status`, requires a Bearer token…". Also tighten the README:53 network-exposure note: "`api_token` protects most of the API but not the UI, the event stream or the webhooks."

### WR-02: "Only releases SeedSyncarr itself downloaded" overstates the auto-delete evidence gate, including in the forged-import risk statement

**File:** `README.md:86`, `README.md:221-223`
**Issue:** README:86 says pruning "applies only to releases SeedSyncarr itself downloaded". README:222-223 says a forged import can only cause a deletion when "the name matches a release SeedSyncarr downloaded". The gate the code enforces is weaker than that:

- `model_pipeline.py:205-227` adds a root to `downloaded_file_names` whenever it shows up in `DOWNLOADED` state. `model_builder.py:466` and `518-525` set `DOWNLOADED` purely by `local_size >= remote_size` for a name present on both sides. Nothing checks that lftp ever transferred it.
- `controller.py:828-970` commits a root to the downloaded list on webhook evidence ("Committing '{}' to downloaded list on import evidence") when it has a complete local copy of a remote release.

A local item in `/downloads` that SeedSyncarr never transferred therefore passes the evidence gate if a same-named item exists on the seedbox and the local copy is at least as large. Examples: a folder copied in by hand, a leftover from another sync tool, or a migration from upstream SeedSync with a fresh persist file. A genuine or forged import webhook can then get it deleted once pruning is on. The doc's security reassurance ("can only lead to a deletion when … a release SeedSyncarr downloaded") is the one a user relies on when deciding to leave webhooks unverified.

**Fix:** State the actual condition, e.g. README:86:

```markdown
When enabled, it applies only to items that exist on the seedbox and have a complete
local copy in your downloads directory (normally releases SeedSyncarr transferred;
a matching copy placed there by other means also qualifies).
```

Make the same change in README:222-223: "…and the name matches an item with a complete local copy of a seedbox release…". Alternatively, tighten the code so `downloaded_file_names` only records lftp-observed transfers. That is a separate behavior change and needs a ruling (see SA-01).

## Info

### IN-01: "nothing is deleted" / "pruning stops" is absolute, but timers armed before the secret was set still fire

**File:** `README.md:219-220`, `SECURITY.md:43`
**Issue:** Setting `webhook_secret` or `webhook_require_secret` only rejects new webhook calls. Auto-delete timers armed by imports accepted earlier, including their up-to-24 deferral re-arms, still run `__execute_auto_delete`. Nothing in that path re-checks webhook config (`controller.py:1321+`). "So nothing is deleted" is therefore not strictly true right after the change.
**Fix:** "…so no new imports are confirmed and no new deletions are scheduled (deletions already scheduled still run)."

### IN-02: "Both examples" is a forward reference

**File:** `README.md:49`
**Issue:** The network-exposure note sits right after the Quick Start compose example. The second example (`docker run`) only appears later under Installation (line 99), so at this point "Both examples" refers to something the reader hasn't seen yet.
**Fix:** "The Quick Start compose file and the `docker run` example below both publish port 8800…"

### IN-03: List of opt-in protections omits `allowed_hostname` (Host-header check)

**File:** `README.md:205-213`, `SECURITY.md:40`
**Issue:** `web_app.py:95-110` enforces a Host-header allowlist on `/server/*` only when `allowed_hostname` is set; the default is `""`, so it is off. It defends against DNS rebinding against the unauthenticated UI and API. Both "off until you configure them" lists leave it out, so they are incomplete.
**Fix:** Add a bullet: "**Host-header check** is off while `allowed_hostname` is empty."

### IN-04: Exposure guidance differs between the two files

**File:** `README.md:51-52`, `SECURITY.md:44`, `SECURITY.md:50`
**Issue:** README says to use an authenticating reverse proxy "for any untrusted network". SECURITY.md:50 says "if you expose it beyond localhost", and SECURITY.md:44 says "Set `api_token` for any non-loopback bind". The README never tells the user to set `api_token`, even though the default compose binds all interfaces.
**Fix:** Pick one threshold, either "beyond localhost" or "any network you don't fully trust", and use it in both files. Add "set `api_token`" to the README network-exposure note.

### IN-05: Mitigation advice skips the option the docs themselves describe (proxy-checked basic auth or header)

**File:** `README.md:216-221`, `SECURITY.md:43`
**Issue:** Both files note that Sonarr/Radarr can send basic auth or fixed custom headers, then name "restricting who can reach port 8800" as the only practical protection. An authenticating reverse proxy in front of `/server/webhook/*` can check exactly those credentials, and README:51 already recommends such a proxy.
**Fix:** Append: "…or have an authenticating reverse proxy check the basic-auth credentials or custom header Sonarr/Radarr send."

## Set aside (needs ruling)

### SA-01: Code-level evidence gate is weaker than "downloaded by SeedSyncarr"

**Where:** `src/python/controller/model_pipeline.py:205-227`, `src/python/controller/controller.py:828-970`, `docs/CONFIGURATION.md:169`
**Why excluded:** This is a code and behavior question, outside this docs-only phase's file scope. `docs/CONFIGURATION.md:169` repeats the same overclaim ("Only releases SeedSyncarr itself downloaded are ever eligible") but is not in this review's file list.
**Effect if left as is:** With pruning on, a complete local copy SeedSyncarr never transferred (same name as a seedbox item) can be deleted by an import webhook, whether genuine or forged when webhooks are unverified.
**Needs:** A ruling. Either fix the docs everywhere (README, SECURITY, CONFIGURATION) to describe the real gate, or make the code record only lftp-observed transfers as "downloaded".

### SA-02: Stale delay figure in the controller comment

**Where:** `src/python/controller/controller.py:31-32`
**Why excluded:** This is a source comment, not part of the reviewed docs.
**Effect if left as is:** The comment says "At the default 300 s delay this waits ~2 h", but the default is 60 s (about 24 minutes before give-up). A maintainer reading it could misjudge the give-up window. The docs are unaffected; README does not quote the window.
**Needs:** Accept, or fix in a later code phase.

---

_Reviewed: 2026-11-18T00:00:00Z_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
