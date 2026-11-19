---
phase: 127-readme-accuracy
plan: 01
subsystem: docs
tags: [readme, security-docs, documentation]
requires: []
provides:
  - "README Documentation section linking all six repository guides"
  - "README Quick Start Network exposure note"
  - "README security defaults and cleanup conditions stated as the code behaves"
  - "SECURITY.md posture intro and webhook bullet corrected (D-08)"
affects: [README.md, SECURITY.md]
tech-stack:
  added: []
  patterns: ["bold-lead blockquote notes in README", "inline relative links to docs/ guides"]
key-files:
  created: []
  modified: [README.md, SECURITY.md]
decisions:
  - "README Security section states the Sonarr/Radarr signing limit and 401/503 conditions as fact, with no recommendation to set webhook_secret or webhook_require_secret (revised D-03)"
  - "Usage Examples moved above Contributing/Security/License with only the three D-03/D-04 accuracy corrections inside it (D-14 annotation)"
  - "127-check.py left unchanged since 33c50bfc (acceptance path i)"
requirements: [DOC-01, DOC-02, DOC-03, DOC-04]
metrics:
  duration: "~6 min (commits 18:13-18:15 local)"
  completed: 2026-11-18
  tasks: 3
  files: 2
---

# Phase 127 Plan 01: README Accuracy Summary

README now links all six repository guides from a Documentation section after Quick Start. Quick Start says port 8800 is published on all host interfaces. Cleanup is described as optional Post-Import Pruning: off by default, limited to releases SeedSyncarr downloaded, attempted after the delay subject to safeguards, local copy only. Security lists what is off until configured and gives the exact Sonarr/Radarr signing limit (401/503) without recommending a secret. SECURITY.md changed only in its intro sentence and webhook bullet.

## Starting worktree state

`git rev-parse HEAD` (before any edit):

```
1a1e344372a539e51e25991229363809208850fc
```

`git status --porcelain` (before any edit):

```
 M .planning/STATE.md
?? .planning/reconcile-pending.json
```

Both entries are pre-existing and inside `.planning/`. Neither was touched by Tasks 1-3 (STATE.md is updated only by the tracking step after this SUMMARY).

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | README structure, Documentation section, guide links, Quick Start exposure note | d66de370 | README.md |
| 2 | README claims and security wording | f59d8a0f | README.md |
| 3 | SECURITY.md two-spot correction and phase gate | 995ff457 | SECURITY.md |

## Verification (observed output)

- Task 1: `127-check.py structure` printed `structure: OK`. 13 H2 headings in the planned order (About This Fork, Quick Start, Documentation, Features, How It Works, Installation, Configuration, Usage Examples, Screenshots, Related Projects, Contributing, Security, License). `thejuran.github.io` count 0; `"8800:8800"` 1; `-p 8800:8800` 1; `^> \*\*` 2. Usage Examples block diffed byte-identical to the pre-move text after the Task 1 move.
- Task 2: `claims: OK`, `structure: OK`. Forbidden-phrase grep 0; `Security controls` bullet count 1; tables in Security 0; distinct required Security terms 5; `then deletes` 0. Sonarr and Radarr integration bullet is 175 characters (limit 220).
- Task 3 gate command output:
  ```
  all: OK
  All checks passed!
  check script: unchanged since 33c50bfc (path i)
  ```
  `git diff --numstat 091f51f2 -- SECURITY.md` → `2 2`. `X-Webhook-Signature` count in SECURITY.md 1; `Enable \`webhook_require_secret` count 0. Scope group passed with the default baseline (PIN 091f51f2); BASE_REF was not needed.

## Check-script integrity

Path (i): check script unchanged since 33c50bfc. `git diff --quiet 33c50bfcdc7889301274311dec8a158ace7e1d82 -- .planning/phases/127-readme-accuracy/127-check.py` exited 0. No detector rejected accurate text during execution.

## D-07 default recheck

Read `src/python/seedsyncarr.py` `_create_default_config` and `src/python/common/config.py` backfills at implementation time:
`webhook_secret = ""`, `api_token = ""`, `webhook_require_secret = False`, `autodelete.enabled = False`, `autodelete.dry_run = False`, `autodelete.delay_seconds = 60`, `encryption.enabled = False`; backfills set the same values on upgrade. **No difference from the plan's verified_facts.** Also re-read `web/handler/webhook.py` (503 guard when require_secret on and no secret; 401 missing/invalid `X-Webhook-Signature`; skip when no secret), `web/web_app.py` (`/server/webhook/` prefix exempt from Bearer; `_inject_meta_tag` puts `api_token` into the served page), `web/handler/config.py` (only POST `/server/config/set` rate-limited, config-get is not) and `controller/controller.py` `__execute_auto_delete` (rechecks enabled, dry-run logs only, refuses names not in `downloaded_file_names`, defers on held root / active state / partial coverage, max 24 re-arms).

## Final SECURITY.md replacements

Intro sentence:

> SeedSyncarr is designed to be self-hosted on a private network. Some of the protections below are always on (connection-URL guard, CSP headers, rate limiting, log-injection protection); others are off until you configure them (encryption at rest, Bearer auth, webhook signature verification):

Webhook bullet:

> - **Webhook signature verification (opt-in)** — Off unless `webhook_secret` is set. When it is set, each Sonarr/Radarr webhook call must carry an HMAC-SHA256 of the request body in the `X-Webhook-Signature` header; a missing or invalid signature is rejected with 401. With `webhook_require_secret = true` and no `webhook_secret` set, every call is rejected with 503 (a configuration guard, since there is no secret to verify against). Sonarr and Radarr do not sign requests (they send only fixed headers or basic auth), so with a direct Sonarr/Radarr webhook either of those configurations rejects their import webhooks, imports are never confirmed and pruning stops. Verification therefore needs a sender that signs each request, and for direct Sonarr/Radarr webhooks the practical protection is restricting network access to port 8800.

## Deviation from D-14 (reorder only)

Usage Examples was moved as a block (Task 1, verified byte-identical after the move). In Task 2 exactly three spots inside it changed, as required by D-03/D-04 and allowed by the 2026-11-18 annotation on D-14. Line wrapping of the two touched paragraphs changed where the replacement text was a different length; no other words changed.

| Spot | Before | After |
|------|--------|-------|
| 1 ("safely reclaim") | "the signal it uses to safely reclaim the local copy." | "the confirmation Post-Import Pruning waits for." |
| 2 (HMAC-when-configured) | "The webhook is HMAC-verified when a secret is configured." | "Webhook calls are not verified by default (see [Security](#security))." |
| 3 ("then deletes") | "and then deletes the local copy from the downloads directory." | "and then attempts to delete the local copy from the downloads directory, subject to its completion and import safeguards." |

The three bold titles, both webhook paths, the 60 second default and the dry-run sentence ("Enable dry-run mode first to verify which files would be removed before committing to automatic deletion.") are unchanged.

## Requirements

- DOC-01: Documentation section (Task 1), Installation links the two guides, website removed.
- DOC-02: Security controls bullet and expanded Security section (Task 2), SECURITY.md (Task 3).
- DOC-03: Conditioned tagline, About, Features, How It Works, Usage Examples (Task 2).
- DOC-04: Network exposure note (Task 1).
- D-14: satisfied with the noted three-spot deviation above.

## Claims ledger

### Part 1: Finding 4 claims table, plus other claims changed

| Pre-phase line | Claim | Disposition | Section now | Final wording |
|----|----|----|----|----|
| 13 | HMAC-verified webhook drives safe auto-delete, never delete | Qualified | Tagline | "A Sonarr-driven seedbox sync tool where optional auto-delete waits for Sonarr/Radarr to confirm the import." |
| 22 | Same HMAC/safe/never-delete sentence | Removed, points to How It Works | About This Fork | "SeedSyncarr's focus is a Sonarr-driven workflow in which optional local cleanup follows the import confirmation from Sonarr/Radarr (see [How It Works](#how-it-works))." |
| 51 | "for maximum transfer speed" | Qualified | Features | "for fast transfers with parallel connections and segmented downloads" |
| 53 | "automatically extract archives after sync completes" | Kept as accurate (`auto_extract` default True) | Features | unchanged |
| 55 | HMAC-verified webhooks drive safe auto-delete; removes the local copy | Qualified, points to How It Works | Features | "import webhooks from Sonarr/Radarr confirm what reached your library, and optional cleanup can follow (see [How It Works](#how-it-works))" |
| 59 | "Security by default — Fernet..., HMAC..., opt-in Bearer..." | Replaced with always-on controls only | Features | "**Security controls** — always-on CSP headers; rate limiting on the Sonarr/Radarr webhook, POST config-set, test-connection, bulk-command and status endpoints; file names sanitized for CR/LF and control characters before they reach log lines; and an IP-resolution guard on Sonarr/Radarr URLs when testing a connection. Settings that are off until you configure them are listed under [Security](#security)." |
| 63 | "continuously transfers"; "safely reclaim ... never deletes" | Qualified, full conditioned explanation | How It Works | "...transfers new files from the seedbox to your local machine as they appear..."; "Cleanup after import is handled by Post-Import Pruning, which is optional and off by default. When enabled, it applies only to releases SeedSyncarr itself downloaded: after a confirmed import and a safety delay (default 60 seconds), SeedSyncarr attempts to delete the local copy, subject to completion and import safeguards. Deletion is deferred, and can eventually be given up, while a release is still extracting or a pack is only partly downloaded or imported ... A dry-run option logs what would be deleted without deleting anything. Pruning deletes the local copy only; the remote copy on the seedbox is not deleted by it." |
| 111 | Website documentation link | Removed | Installation | "For detailed setup instructions, see [Getting Started](docs/GETTING-STARTED.md) and [Configuration](docs/CONFIGURATION.md)." |
| 115 | "open `http://localhost:8800`" | Kept as accurate (local access) | Configuration | unchanged |
| 121 | "Sonarr / Radarr — webhook URLs and API keys" | Kept as accurate | Configuration | unchanged |
| 172 | "On Import" event | Kept (low risk, label naming) | Usage Examples | unchanged |
| 175-176 | "safely reclaim"; "HMAC-verified when a secret is configured" | Qualified (D-14 spots 1-2) | Usage Examples | "the confirmation Post-Import Pruning waits for. Webhook calls are not verified by default (see [Security](#security))." |
| 183-184 | "then deletes"; dry-run advice | "then deletes" qualified (spot 3); dry-run sentence kept byte-identical per D-14 | Usage Examples | "then attempts to delete the local copy from the downloads directory, subject to its completion and import safeguards." |
| other | "monitor and control all transfers" | Kept as accurate (UI lists every transfer) | Features | unchanged |
| other | "designed for always-on displays" | Kept (describes displays, not a guarantee) | Features | unchanged |
| other | Dry-run sentence "before committing to automatic deletion" | Kept byte-identical (D-14 forbids extra rewording); reads in context after the qualified spot 3 | Usage Examples | unchanged |
| new | Security section content | Added | Security | see Part 2 rows |

### Part 2: Manual-Only Verifications (README rows plus the side-by-side signing row)

| Row | Final README sentence | Source read | Result |
|----|----|----|----|
| No unconditional claims (D-04) | Part 1 table; `grep -i` for never/always/guarantee/maximum/safe/secure/all leaves only "never download" (PUID note, a symptom quote), "all host interfaces" (true), "all transfers" (true), "always-on displays" / "always-on CSP headers" (true) | 127-RESEARCH.md Finding 4 | Matches |
| api_token default | "**API authentication** is off while `api_token` is empty." | seedsyncarr.py `_create_default_config` (`api_token = ""`), config.py backfill | Matches |
| webhook_secret default | "**Webhook verification** is off while `webhook_secret` is empty, so anything that can reach the endpoint can report an import." | seedsyncarr.py (`webhook_secret = ""`); webhook.py `_verify_hmac` returns None when no secret | Matches |
| webhook_require_secret default | "**`webhook_require_secret`** defaults to `False`; on its own that value rejects nothing." | seedsyncarr.py (`= False`), config.py backfill `"False"`; webhook.py guard only fires when True and no secret | Matches |
| Encryption default | "**Encryption at rest** is off by default: stored secrets (seedbox password, API keys, tokens) are plaintext unless `[Encryption] enabled = True` is set." | seedsyncarr.py (`encryption.enabled = False`); SECURITY.md encryption bullet | Matches |
| api_token scope | Quick Start: "`api_token` protects the API but not the UI, and the UI contains that token." Security: "`api_token` does not authenticate the webhook endpoints, which are exempt from the Bearer check." | web_app.py `_AUTH_EXEMPT_PREFIXES` ("/server/webhook/"), `_inject_meta_tag` | Matches |
| Always-on control scopes (D-05) | Security controls bullet (Part 1, line 59 row) | webhook.py add_routes, config.py add_routes (POST config/set, test connections), SECURITY.md rate-limit bullet (bulk, status); IP guard only in test-connection path (Finding 2) | Matches; no opt-in item listed |
| Quick Start exposure note | "Both examples publish port 8800 on all host interfaces, so the web UI, the API and the webhook endpoints are reachable from any network the host is on. For any untrusted network, put SeedSyncarr behind an authenticating reverse proxy and restrict network access to the port. `api_token` protects the API but not the UI, and the UI contains that token." | web_app_job.py bind 0.0.0.0 (Finding 3); compose/run examples have no host IP | Matches; token and `allowed_hostname` not presented as network protection |
| Signing conditions, README vs SECURITY.md side by side | README: "With a direct, unsigned Sonarr/Radarr webhook, a configured `webhook_secret` rejects each call (401), and `webhook_require_secret = true` with no secret set rejects every call (503). In both cases imports are no longer confirmed and pruning stops, so nothing is deleted." SECURITY.md bullet quoted above | webhook.py lines 30-104 | Matches: both give 401 for a configured secret with missing/invalid signature, 503 for `= true` with no secret, both say Sonarr/Radarr do not sign, both scope to direct webhooks, neither recommends turning either setting on |
| Cleanup vs controller | How It Works sentences (Part 1, line 63 row); Usage spot 3 | controller.py `__execute_auto_delete` (enabled recheck, dry-run log, `downloaded_file_names` refusal, deferrals, `_AUTO_DELETE_MAX_REARMS = 24`); docs/CONFIGURATION.md AutoDelete table (local copy only, remote never touched) | Matches; deletion described as attempted, not automatic on timer expiry |
| Guide blurbs (D-13) | Getting Started: "prerequisites, installing with Docker Compose or `docker run`, first run and common setup issues"; Configuration: "every `settings.cfg` option, required vs optional settings, CLI arguments and defaults"; Security: "how to report a vulnerability, the security posture and deployment best practices"; Architecture: "system overview, component diagram, data flow and key abstractions"; Development: "local setup, build commands, code style, branch conventions and the PR process"; Testing: "the pytest, Angular unit and Playwright end-to-end suites, how to run them, coverage and CI integration" | Each guide's headings | Corrected during Task 1: first Getting Started draft said "Docker and source installation" but the guide has no source-install section; first Testing draft omitted coverage. Final blurbs match headings. "every `settings.cfg` option" is slightly broad given the known CONFIGURATION.md gap (`webhook_require_secret` undocumented there, out of scope) — see Known Issues |

## Deviations from Plan

None in scope. The plan executed as written; the D-14 three-spot change is the planned, annotated exception recorded above.

## Known Issues

- The Configuration blurb says the guide covers "every `settings.cfg` option", but docs/CONFIGURATION.md does not document `webhook_require_secret` and its Defaults table omits `encryption.enabled` (known, owner-deferred gap). **Cost if wrong:** a reader looking for `webhook_require_secret` there won't find it; the README Security section and SECURITY.md cover it. A follow-up could soften the blurb to "the `settings.cfg` options" or fill the gap in CONFIGURATION.md.

## Out-of-scope changes not made by this phase

None. The scope group passed against PIN 091f51f2: only README.md and SECURITY.md differ outside `.planning/`.

## Threat Flags

None. Docs-only changes; no new code surface.

## Self-Check: PASSED

- README.md, SECURITY.md modified; commits d66de370, f59d8a0f, 995ff457 present in `git log`.
- `127-check.py all` → `all: OK`; `ruff check src/python/` → `All checks passed!`.

## Post-execution change (code review WR-01, 2026-11-18)

The "check script unchanged since 33c50bfc" statements above held at plan completion only. After code review, commit fbc954ec corrected the README and the SECURITY.md Bearer auth bullet so they name all three routes exempt from `api_token`, and changed `127-check.py` (acceptance path ii). Full diff justification: the owner approved a third SECURITY.md spot (the Bearer auth bullet, replaced in place). The checker now sets that one line aside before the two-spot diff, requires it to name `/server/status`, `/server/stream` and the webhooks, and adds self-tests for both accepting and rejecting it. No existing check was removed. `127-check.py all` passes, including the self-test. See 127-REVIEW.md, section Resolution.
