# Phase 127: README Accuracy - Research

**Researched:** 2026-11-18
**Domain:** Documentation accuracy (README.md, two SECURITY.md spots under the widened D-08; originally one sentence), verified against Python/Angular source
**Confidence:** HIGH (every default and control below was read from source in this session)

> **Revision note (2026-11-18, after the owner decision).** D-03 was revised and D-08 widened in 127-CONTEXT.md after this research was written. 127-CONTEXT.md is authoritative. Passages below that quote the earlier D-03 ("recommend setting a secret") or the earlier D-08 (one sentence, numstat `1 1`) are marked SUPERSEDED in place. The verification block in Validation Architecture is replaced by `.planning/phases/127-readme-accuracy/127-check.py`. Findings 1 to 6 (facts read from source) stand unchanged.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Headline pitch and cleanup claims (DOC-03)
- **D-01:** Tagline keeps the differentiator as a *conditioned* promise — auto-delete only runs after Sonarr/Radarr confirms the import (e.g. "...where auto-delete waits for Sonarr/Radarr to confirm the import"). No absolute "never deletes" wording anywhere.
- **D-02:** Say it once fully. Tagline = one-line conditioned pitch; the full explanation (import confirmation via inbound webhook → optional Post-Import Pruning, **off by default** → safety delay, default 60 s → dry-run option) lives once in **How It Works**. About This Fork and the Features bullet are shortened and point there instead of repeating the promise.
- **D-03 (SUPERSEDED 2026-11-18; see revised D-03 in 127-CONTEXT.md):** ~~State the no-secret consequence plainly: without `webhook_secret`, webhook calls are not verified, so anything that can reach the endpoint can report an import. Recommend setting a secret, and `webhook_require_secret = true` to reject calls when no secret is configured.~~ Revised decision: keep the consequence sentence; do NOT recommend `webhook_secret` or `webhook_require_secret = true` for Sonarr/Radarr; state that verification needs a sender that signs each request, that Sonarr/Radarr do not, and that the practical protection is restricting who can reach port 8800.
- **D-04:** Review the entire README for remaining unconditional claims (e.g. "maximum transfer speed", "safely reclaim") and qualify or soften them.

#### Security wording (DOC-02)
- **D-05:** Replace the "Security by default" Features bullet with a "Security controls" bullet listing only always-on controls (CSP headers, rate limiting on named endpoints, log-injection sanitizing, *arr connection-URL IP guard) and linking to the Security section.
- **D-06:** Expand the existing `## Security` section (currently a single link) into a short "what's off until you configure it" list: API auth off when `api_token` empty; webhook verification off when `webhook_secret` empty; `webhook_require_secret` defaults to `False`; encryption at rest off by default (stored secrets plaintext; enable via `[Encryption] enabled = True`). Keep the vulnerability-reporting link. Link SECURITY.md for full posture — don't duplicate it as a table.
- **D-07:** Recheck every stated default against current code (`src/python/common/config.py` and the pruning/auto-delete config) and SECURITY.md at implementation time; the wording must match code, not this file.
- **D-08 (SUPERSEDED 2026-11-18; see widened D-08 in 127-CONTEXT.md):** ~~Fix the single SECURITY.md sentence "several protections are active by default" so it no longer contradicts the opt-in items it lists. No other SECURITY.md edits.~~ Widened decision: fix that sentence AND correct the "HMAC-verified import webhooks" bullet so it states that Sonarr/Radarr do not sign requests and that a secret or `webhook_require_secret` would reject their webhooks. No other SECURITY.md edits.

#### Quick Start exposure (DOC-04)
- **D-09:** Keep `8800:8800` in both the compose and `docker run` examples (no localhost-bind change).
- **D-10:** Add a factual `> **Network exposure**` blockquote under the Quick Start example, same style as the existing PUID/PGID note (not a `[!WARNING]` admonition): port 8800 is published on all host interfaces; for any untrusted network put SeedSyncarr behind an authenticating reverse proxy and restrict network access; `api_token` protects the API but not the UI, and the UI contains that token. Link to the Security section.

#### Documentation discoverability (DOC-01)
- **D-11:** Replace the website link (`https://thejuran.github.io/seedsyncarr`) in Installation with links to `docs/GETTING-STARTED.md` and `docs/CONFIGURATION.md`. The website is not referenced as a docs source.
- **D-12:** New `## Documentation` section placed immediately after Quick Start.
- **D-13:** Grouped with one-line blurbs — "Using SeedSyncarr": Getting Started, Configuration, Security (`SECURITY.md`); "Contributing / internals": Architecture, Development, Testing.
- **D-14:** Move `## Usage Examples` from the bottom up to sit with content sections (above Contributing/Security/License). Reorder only.
- **D-15:** Every relative link in README.md (including images under `doc/`) must resolve — verify mechanically.

### Claude's Discretion
- Exact prose wording within the decisions above.
- Exact section order beyond D-12/D-14 constraints.
- Link-check method (script or grep + `test -f`).

### Deferred Ideas (OUT OF SCOPE)
- (Updated 2026-11-18 to match 127-CONTEXT.md.) Accepting a webhook authentication method Sonarr/Radarr can send (fixed shared-secret header or basic auth): application change, backlog 999.8.
- `docs/CONFIGURATION.md` gaps (no `webhook_require_secret` entry, no `encryption.enabled` defaults row): out of scope; README points to SECURITY.md.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | Six guides reachable from a prominent Documentation section; installation links repo guides, not the website; every relative link resolves | All six guide files exist (verified `ls docs/`); all 10 current relative links/images resolve; website link at README.md:111; link-check script in Validation Architecture |
| DOC-02 | Accurate default security posture replaces "Security by default" | Defaults table (Finding 1) with file:line for every value; always-on controls confirmed (Finding 2); target bullet at README.md:59 |
| DOC-03 | HMAC and cleanup claims conditioned; whole README reviewed | Auto-delete flow traced (webhook → evidence gate → `enabled` check → delay timer → `dry_run` check); full claim inventory (Finding 4); **critical caveat: Sonarr/Radarr cannot produce the HMAC signature (Finding 6)** |
| DOC-04 | Quick Start explains 8800 on all interfaces, reverse proxy, API token does not protect the UI | Bind is `0.0.0.0` (web_app_job.py:27); both examples publish `8800:8800` with no host IP (README.md:36, :77); token injected into the served HTML as a meta tag (web_app.py:219-223) (Finding 3) |
</phase_requirements>

## Summary

This is a prose-only phase: README.md gets restructured and its security/cleanup claims qualified, and two spots in SECURITY.md change: the line 40 sentence and the line 43 webhook bullet (SUPERSEDED 2026-11-18: this summary originally said one sentence; D-08 was widened). Every default the README will state was checked in code: `api_token` and `webhook_secret` default to empty, `webhook_require_secret` to `False`, `[Encryption] enabled` to `False`, `[AutoDelete] enabled` to `False`, `dry_run` to `False` and `delay_seconds` to `60`. The values agree across `seedsyncarr.py` `_create_default_config()`, `common/config.py` `from_dict()` backfills, `docs/CONFIGURATION.md` and `SECURITY.md`. All four "always-on" controls named in D-05 exist and have no config switch. Rate limiting covers exactly the endpoints SECURITY.md lists. The *arr IP guard applies only to the Test Connection endpoints, not to the live queue requests, so README wording must say "when testing a connection".

**One finding conflicted with a locked decision; the owner resolved it on 2026-11-18 by revising D-03 and widening D-08 (see Open Questions (RESOLVED)).** SeedSyncarr verifies webhooks by computing HMAC-SHA256 over the request body and comparing it with an `X-Webhook-Signature` header (`webhook.py:73-104`). Sonarr's webhook sender does no signing. It can only send Basic-auth credentials and static custom headers (Sonarr source `WebhookProxy.cs`; PR #7371). A static header cannot match a per-body HMAC. So a user who follows D-03's "set a secret" advice with Sonarr/Radarr pointed directly at SeedSyncarr will get every import webhook rejected with 401. Setting `webhook_require_secret = true` without a secret rejects every call with 503. Either way, import confirmation and pruning stop working. The README must not recommend these settings without saying what the sender must do. SECURITY.md:43 has the same implied assumption. (SUPERSEDED 2026-11-18: ~~D-08 limits SECURITY.md edits to one sentence.~~ The widened D-08 also corrects that bullet.)

Docs-only. No CI job lints Markdown or checks links (`.github/workflows/ci.yml` is the only workflow; no markdown/lychee step). No test pins README or SECURITY.md text (grep of `src/python/tests`, `src/angular/src` and `src/e2e` found no references). pytest and whole-tree `ruff check src/python/` are unaffected but still run in CI.

**Primary recommendation:** Plan one docs plan (README restructure plus the two SECURITY.md spots) with a mechanical verification block. (SUPERSEDED 2026-11-18: ~~First, settle the D-03 webhook-secret wording with the owner (see Open Question 1).~~ Settled: the owner chose the factual wording; see revised D-03.) The recommended factual wording: verification needs a sender that signs the body, Sonarr/Radarr do not sign natively, so with a direct Sonarr/Radarr webhook the protection is network restriction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Guide discoverability | Static docs (README.md) | — | Pure Markdown links to files in repo |
| Stated security defaults | Static docs (README.md, SECURITY.md:40) | API/Backend (source of truth: `seedsyncarr.py`, `common/config.py`) | Docs must mirror backend defaults; no code change |
| Webhook verification / auto-delete behaviour described | Static docs | API/Backend (`web/handler/webhook.py`, `controller/controller.py`) | Behaviour is read, not changed |
| UI carries API token | Static docs | Frontend server (`web_app.py` meta-tag injection) + Browser (`auth.interceptor.ts`) | Fact explained in the DOC-04 note |

## Standard Stack

Not applicable. No libraries are installed. The only tools are `python3` (stdlib) and `grep` for verification.

## Package Legitimacy Audit

No external packages are installed in this phase. Slopcheck is not applicable.

## Key Findings (verified against repo)

### Finding 1: Security and cleanup defaults (D-06, D-07)

| Setting | Default | First-run source | Upgrade backfill | CONFIGURATION.md | SECURITY.md | Agree? |
|---------|---------|------------------|------------------|------------------|-------------|--------|
| `[General] api_token` | `""` (auth off) | `src/python/seedsyncarr.py:388` | `common/config.py:578-579` | line 85 (and 17, 211) | line 44 | Yes |
| `[General] webhook_secret` | `""` (verification skipped) | `seedsyncarr.py:387` | `config.py:575-576` | line 84 (and 16, 210) | line 43 | Yes |
| `[General] webhook_require_secret` | `False` | `seedsyncarr.py:390` | `config.py:582-587` | **Not documented anywhere in CONFIGURATION.md** | line 43 ("opt-in") | Code and SECURITY agree; CONFIGURATION.md silent |
| `[Encryption] enabled` | `False` (secrets plaintext) | `seedsyncarr.py:435` | `config.py:647` | line 68 and 177; **missing from the Defaults table (lines 206-237)** | line 42 | Yes (table gap only) |
| `[AutoDelete] enabled` (UI: "Post-Import Pruning" → "Enable auto-delete") | `False` | `seedsyncarr.py:431` | `config.py:636` | line 64/169, 235 | — | Yes |
| `[AutoDelete] dry_run` | `False` | `seedsyncarr.py:432` | `config.py:637` | line 170, 236 | — | Yes |
| `[AutoDelete] delay_seconds` | `60` (must be ≥ 1) | `seedsyncarr.py:433` | `config.py:638` | line 171, 237 | — | Yes |
| `[Web] port` | `8800` | `seedsyncarr.py:414` | — | line 124 | — | Yes |

**Disagreements found:** none on values. There are two **omissions in docs/CONFIGURATION.md**. `webhook_require_secret` is not in its INI example, its General table or its Defaults table. `encryption.enabled` is missing from the Defaults table. This matters because the new Documentation section sends readers to CONFIGURATION.md, where they won't find `webhook_require_secret`. The phase scope is README plus two SECURITY.md spots, so fixing CONFIGURATION.md is out of scope. (SUPERSEDED 2026-11-18: ~~the owner must decide (Open Question 2).~~ Decided: no CONFIGURATION.md edits in this phase.) The README can point to SECURITY.md for `webhook_require_secret` instead of CONFIGURATION.md.

**Where these are set:** none of `webhook_secret`, `webhook_require_secret` or `[Encryption] enabled` has a Settings UI control (grep of `src/angular/src/app/pages/settings` finds only the API-token display/regenerate at settings-page.component.html:418-443). They are set in `settings.cfg` (Docker: `/config/settings.cfg`). README wording should say "in `settings.cfg`".

**Startup warnings exist** (`seedsyncarr.py:488-509`): the log warns when `webhook_secret` is unset, and when `api_token` is unset ("Application is bound to 0.0.0.0 without an API token"). The README can mention this.

### Finding 2: Always-on controls for the D-05 "Security controls" bullet

None of these has a config switch. Each is applied unconditionally in code.

| Control | Location | Exact scope (for accurate wording) |
|---------|----------|-----------------------------------|
| CSP header | `src/python/web/web_app.py:142-163` (`after_request` hook) | `Content-Security-Policy` on every response, plus `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff`. Layered with Angular hash-based meta CSP. |
| Rate limiting | `web/rate_limit.py:17`; decorators at `web/handler/webhook.py:38-39` (Sonarr/Radarr webhooks, 60/60s), `web/handler/config.py:152-163` (POST `/server/config/set` 60/60s; Sonarr/Radarr test-connection 5/60s), `web/handler/controller.py:69-72` (`/server/command/bulk` 10/60s), `web/handler/status.py:15-18` (`/server/status` 60/60s) | Matches SECURITY.md:47 exactly. Single-file commands, restart and autoqueue endpoints are **not** rate-limited, so don't say "rate-limited API". Name the endpoints or say "rate limiting on webhook, config, test-connection, bulk-command and status endpoints". |
| Log-injection sanitizing (CWE-117) | `common/types.py:17` `sanitize_log_value`; applied at call sites in 18 non-test files (webhook, controller, model_pipeline, arr_queue, file_operation_manager, …) | Per-call-site, not a global log filter. One known exception is `web/handler/controller.py:192-194`, which uses `repr()` (still neutralises CR/LF). Use SECURITY.md:48's wording ("file names are sanitized for CR/LF and control characters before reaching log lines"). Do not claim "all log output". |
| *arr connection-URL IP guard | `web/handler/config.py:182` `_validate_url` (uses `socket.getaddrinfo` at :280); only call site `config.py:372` inside `_test_arr_connection` | **Scoped to the Test Connection endpoints only.** `controller/arr_queue.py` uses `sonarr_url`/`radarr_url` for live queue checks without this guard. README wording must be "an IP-resolution guard on Sonarr/Radarr URLs when testing a connection" (SECURITY.md:45 already says "When you test a Sonarr/Radarr connection"). |

### Finding 3: UI carries the API token; port exposure (DOC-04)

- **Server injects the token into the UI shell:** `web_app.py:219-223` `_inject_meta_tag` writes `<meta name="api-token" content="{html-escaped api_token}">` into `index.html`, served by `__index` (`web_app.py:225-235`). Serving `index.html` and static files is not gated by the Bearer check, which applies to `/server/*` paths.
- **Browser reads it:** `src/angular/src/app/services/utils/auth.interceptor.ts:4-48` reads `meta[name="api-token"]` and attaches `Authorization: Bearer <token>`. The Settings page also reads it for display/copy (`settings-page.component.ts:103-105`).
- **Auth exemptions:** `web_app.py:59-65`. `/server/stream`, `/server/status` and every `/server/webhook/*` path skip the Bearer check. **Consequence for D-03:** setting `api_token` does not protect the webhook endpoints. Only `webhook_secret` does (if the sender can sign; see Finding 6).
- **Bind address:** `web/web_app_job.py:27` `host="0.0.0.0"`. Docker examples publish `"8800:8800"` (README.md:36) and `-p 8800:8800` (README.md:77) without a host IP, so Docker publishes on all host interfaces (standard Docker behaviour [CITED: docs.docker.com port publishing; well-established]).
- **Host-header check:** `allowed_hostname` (`web_app.py:~100-110`) restricts the `Host` header only when set. It is not network access control; don't present it as one.

### Finding 4: README.md inventory (current, 184 lines)

**Section order:**
| Line | Section |
|------|---------|
| 1-11 | Wordmark `<picture>` + dashboard screenshot |
| 13 | Tagline blockquote |
| 15-18 | Badges |
| 20 | `## About This Fork` |
| 24 | `## Quick Start` (compose 26-40; PUID/PGID note 42-47) |
| 49 | `## Features` |
| 61 | `## How It Works` |
| 67 | `## Installation` (`### Docker` 69, `### pip` 90, website link 111) |
| 113 | `## Configuration` |
| 124 | `## Screenshots` |
| 132 | `## Related Projects` |
| 136 | `## Contributing` |
| 140 | `## Security` (single link) |
| 144 | `## License` |
| 148 | `## Usage Examples` (AutoQueue 150, Sonarr import 163, cleanup 179) |

**Recommended target order (meets D-12/D-14):** wordmark/screenshot → tagline → badges → About This Fork → Quick Start (+ PUID/PGID note + new Network exposure note) → **Documentation** → Features → How It Works → Installation → Configuration → **Usage Examples** → Screenshots → Related Projects → Contributing → Security (expanded) → License.

**Unconditional or inaccurate claims to fix (D-01..D-04):**
| Line | Current text (abridged) | Problem | Fix direction |
|------|------------------------|---------|---------------|
| 13 | "HMAC-verified import webhook drives safe auto-delete — so you never delete a file that didn't make it into your library" | HMAC is off by default; pruning is off by default; absolute promise | D-01 conditioned tagline, drop "HMAC-verified" |
| 22 | Same "HMAC-verified … safe auto-delete … never delete" sentence | Duplicate absolute promise | D-02: shorten, point to How It Works |
| 51 | "for maximum transfer speed" | Unconditional superlative | "for fast transfers with parallel connections and segmented downloads" |
| 53 | "automatically extract archives after sync completes" | Accurate (`auto_extract` default True, `seedsyncarr.py:419`); acceptable | Optional: "can automatically extract" |
| 55 | "HMAC-verified import webhooks drive safe auto-delete; once your media library confirms the import, SeedSyncarr removes the local copy" | HMAC conditional; removal only if pruning enabled | D-02: shorten, "optional cleanup after import confirmation — see How It Works" |
| 59 | "Security by default — Fernet-encrypted secrets at rest, HMAC-verified import webhooks, opt-in Bearer auth, …" | Encryption and HMAC are off by default | D-05: "Security controls" bullet, always-on items only |
| 63 | "continuously transfers new files" / "safely reclaim the local copy, so it never deletes a file that didn't make it into your library" | Absolute; omits pruning off by default, delay, dry-run | D-02: full conditioned explanation lives here |
| 111 | `[documentation](https://thejuran.github.io/seedsyncarr)` | Website link (D-11) | Replace with GETTING-STARTED + CONFIGURATION links |
| 115 | "open `http://localhost:8800`" | Fine (local); remote users use host address | Optional: "`http://<host>:8800`" |
| 121 | "Sonarr / Radarr — webhook URLs and API keys" | Accurate: Settings shows a copyable webhook URL (settings-page.component.html:299-308) | Keep |
| 175-176 | "the signal it uses to safely reclaim the local copy. The webhook is HMAC-verified when a secret is configured." | "safely reclaim" absolute; HMAC note implies Sonarr can be configured to sign | Qualify; align with Finding 6 outcome |
| 172 | `"On Import" event` | Handler accepts only `eventType == "Download"` (`webhook.py` ~line 146), which is what Sonarr's "On Import"/"On File Import" trigger sends [ASSUMED label naming varies by Sonarr version] | Keep; low risk |
| 183-184 | "Enable dry-run mode first to verify which files would be removed" | Accurate (`controller.py:1363-1368` logs `DRY-RUN: Would delete local file`) | Mention that dry-run results appear in the log |

Claims checked and **accurate**: arm64 + amd64 images (`ci.yml:199`); `pip install seedsyncarr` (PyPI 200 OK, latest 1.8.0); "Requires Python 3.11 or 3.12" (`src/python/pyproject.toml:10` `>=3.11,<3.13`); "You don't need to install anything on the remote server" (scanfs script copied to `remote_path_to_scan_script`, not user-installed; acceptable).

**Facts available for the How It Works rewrite (D-02):**
- Auto-delete is scheduled only for roots that passed the import "evidence gate" from webhook import credits, and only if `autodelete.enabled` (`controller.py:1031-1037`).
- `enabled` is re-checked when the timer fires (`controller.py:1355`), as is `dry_run` (`:1363`).
- If the release is still mid-lifecycle, deletion is deferred and retried every `delay_seconds` up to 24 times (CONFIGURATION.md:171).
- Only releases SeedSyncarr itself downloaded are eligible; the **remote copy is never touched** (CONFIGURATION.md:169). This is a factual, verifiable "never" and is safe to keep.

**Relative links/images (all resolve today):** `LICENSE` (18, 146), `SECURITY.md` (59, 142), `CONTRIBUTING.md` (138), `doc/brand/wordmark-dark.png` (3, 5), `doc/brand/wordmark-light.png` (4), `doc/images/screenshot-dashboard.png` (10, 129). New links to add: `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md` (all exist). Same-file anchors (e.g. `#security`, `#how-it-works`) will be added; the checker must validate them against GitHub's slugging (lowercase, spaces → `-`, punctuation dropped).

**Tagline copies elsewhere:** none. The pyproject description is "Fast file syncing from remote servers with a web UI, powered by LFTP" (`src/python/pyproject.toml:8,48`), with no absolute claims. pyproject has no `readme` field, so PyPI's long description is unaffected.

### Finding 5: SECURITY.md sentence for D-08

`SECURITY.md:40` (exact):
> SeedSyncarr is designed to be self-hosted on a private network, and several protections are active by default:

It introduces the bullet list at lines 42-48, which mixes opt-in items (encryption at rest :42 "Off by default"; HMAC webhooks :43 "when a secret is configured"; Bearer auth :44 "when `api_token` is set") with always-on items (IP guard :45, CSP :46, rate limiting :47, log-injection :48). It is followed by line 50: "**This is not a substitute for network isolation.** …"

Suggested replacement (one line, discretionary wording):
> SeedSyncarr is designed to be self-hosted on a private network. Some of the protections below are always on (connection-URL guard, CSP headers, rate limiting, log-injection protection); others are off until you configure them (encryption at rest, Bearer auth, webhook verification):

Constraint (SUPERSEDED 2026-11-18): ~~the `git diff --numstat SECURITY.md` result must be `1	1	SECURITY.md`.~~ Under the widened D-08 two spots change: this intro sentence and the "HMAC-verified import webhooks" bullet. `127-check.py security` enforces that by content (only those two baseline lines are replaced).

### Finding 6 (CRITICAL, affects D-03): Sonarr/Radarr cannot produce SeedSyncarr's webhook signature

- **SeedSyncarr's check** (`web/handler/webhook.py:73-104`): if `webhook_secret` is set, it computes `hmac.new(secret, body_bytes, sha256).hexdigest()` and requires it in `X-Webhook-Signature`. A missing header returns 401 "Missing webhook signature"; a mismatch returns 401.
- **Sonarr's sender** (`src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs`, develop): sends JSON with optional Basic-auth credentials and user-defined static headers (`foreach header in settings.Headers → request.Headers.Add`). **No hashing or signing of the payload.** [VERIFIED: raw.githubusercontent.com Sonarr develop source] Custom headers arrived via Sonarr PR #7371, merged 2024-11-15 [VERIFIED: github.com/Sonarr/Sonarr/pull/7371]; Radarr shares the form [CITED: spiderhash.io guide; MEDIUM].
- **Origin of the mismatch:** the Phase 40 plan (`.planning/milestones/v3.1-phases/40-credential-endpoint-security/40-03-PLAN.md:122`) assumed "Sonarr/Radarr both send webhook signatures". 40-03-SUMMARY.md:142 tells users to put a static `X-Webhook-Signature: <hmac-hex-digest>` custom header in Sonarr. A static value can match only one fixed body, so real import payloads fail. [VERIFIED by code reading; not run against a live Sonarr in this session]
- **Consequences for README wording:**
  - "Set `webhook_secret`" → with a direct Sonarr/Radarr webhook, every import call is rejected with 401, so imports are never confirmed and pruning never runs. The failure is safe (no deletions) but breaks the feature silently except for WARNING log lines.
  - "Set `webhook_require_secret = true`" (without a secret) → every call is rejected with 503, with the same effect.
  - D-03's first half ("without `webhook_secret`, anything that can reach the endpoint can report an import") is accurate and should stay. (SUPERSEDED 2026-11-18: ~~Its recommendation half needs owner input (Open Question 1).~~ Resolved: no recommendation; see revised D-03.)
- **Mitigating fact for the "anyone can report an import" statement:** a forged import only yields a deletion if pruning is enabled, the name matches a release SeedSyncarr downloaded and passes the evidence gate, and the delay elapses. Remote copies are never touched. This keeps the tone factual, not alarmed.

## Architecture Patterns

### Edit flow
```
Source of truth (code)                  Docs under edit                   Verification
seedsyncarr.py defaults ─┐
common/config.py backfill├─► README.md sections ──► link resolver (python3 stdlib)
web_app.py / webhook.py ─┘   SECURITY.md:40, :43 ──► forbidden/required phrase greps
                                                   ──► section-order + diff-scope checks
```

### Pattern: blockquote note (style model for D-10)
README.md:42-47 is a `>` blockquote whose first sentence is bold and ends with a period, followed by plain prose wrapped at ~80 columns. The Network exposure note must copy this exactly: `> **Network exposure.** …` or `> **Port 8800 is published on all host interfaces.** …`. Don't use a `> [!WARNING]` admonition (D-10).

### Pattern: link style
Existing links are inline relative (`[SECURITY.md](SECURITY.md)`). Use the same for guides: `[Getting Started](docs/GETTING-STARTED.md)`. Don't use the website or absolute GitHub URLs for repo files.

### Anti-Patterns to Avoid
- **Restating the security posture as a table** (D-06 forbids duplicating SECURITY.md).
- **Repeating the cleanup promise in About, Features and How It Works** (D-02: once, in How It Works).
- **Calling `allowed_hostname` or `api_token` network protection.** Neither stops reachability of the UI.
- **Saying "all endpoints are rate-limited"**, or saying the IP guard covers all *arr traffic. Both are false (Finding 2).
- **Editing CONFIGURATION.md, GETTING-STARTED.md or any other SECURITY.md line.** Out of scope without owner approval.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Link checking | A committed script under `src/python/` (would fall under whole-tree ruff and expand scope) | An inline `python3 - <<'EOF'` check in the plan's verify step, or a scratch file outside the repo | No new repo artifact; stdlib only |
| Security posture detail | New prose re-deriving controls | Link to SECURITY.md; reuse its sentences (lines 42-48) | SECURITY.md is the vetted source of truth |

## Common Pitfalls

### Pitfall 1: Recommending a webhook secret that Sonarr/Radarr can't satisfy
**What goes wrong:** Users set `webhook_secret` (or `webhook_require_secret = true`), all imports are rejected, and pruning silently stops.
**How to avoid:** Open Question 1 is resolved (revised D-03: no recommendation). State what the sender must send (`X-Webhook-Signature` = hex HMAC-SHA256 of the raw body).
**Warning signs:** Prose that says "set a secret in Sonarr".

### Pitfall 2: Over-claiming always-on controls
**What goes wrong:** The IP guard or rate limiting described as broader than it is.
**How to avoid:** Use the scopes in Finding 2 verbatim.

### Pitfall 3: Broken anchors after section reorder
**What goes wrong:** `[Security](#security)` style links break if headings are renamed.
**How to avoid:** Run the anchor check in Validation Architecture.

### Pitfall 4: SECURITY.md diff larger than the two approved spots (originally: one sentence)
**How to avoid (SUPERSEDED 2026-11-18):** ~~`git diff --numstat SECURITY.md` must show `1 1`.~~ Two approved spots change under the widened D-08; `127-check.py security` checks that nothing else in SECURITY.md differs from the baseline.

### Pitfall 5: Memory note "Badge labels: three sites" doesn't apply
README changes don't touch UI badges. No e2e or fixture coupling: no test references README/SECURITY.md.

## Code Examples

### Webhook verification (what the README must describe accurately)
```python
# Source: src/python/web/handler/webhook.py:84-104
secret = self.__config.general.webhook_secret
if not secret:
    return None  # verification skipped
expected = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
provided_signature = request.headers.get("X-Webhook-Signature", "")
# missing → 401, mismatch → 401 (constant-time compare)
```

## State of the Art

| Old (README today) | Current behaviour | Impact |
|--------------------|-------------------|--------|
| "Security by default … Fernet-encrypted secrets" | Encryption opt-in since its introduction (SECURITY.md:42 already says so; README never updated) | DOC-02 fix |
| Website docs link | Repo guides (`docs/*.md`, generated-by gsd-doc-writer) are the maintained docs | DOC-01 fix |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Radarr's webhook sender behaves like Sonarr's (no payload signing) | Finding 6 | **CONFIRMED 2026-11-18** (Codex cross-AI review read Radarr `src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs`, develop: it serializes the body and adds configured headers/basic credentials; no body HMAC). No longer an assumption |
| A2 | Sonarr's "On Import"/"On File Import" label maps to `eventType: "Download"` | Finding 4, line 172 | Low. Label naming only |
| A3 | No user currently runs a signing proxy in front of SeedSyncarr (so "Sonarr can't sign" is the common case) | Finding 6 | Medium. Affects tone of the D-03 wording only |

## Open Questions (RESOLVED)

All three questions are closed. No open question remains for planning or execution.

1. **D-03 recommendation vs Sonarr's inability to sign (owner decision, product).**
   - What we know: SeedSyncarr requires a per-body HMAC; Sonarr/Radarr send only static headers or Basic auth. Following "set `webhook_secret`" or "set `webhook_require_secret = true`" disables import confirmation for direct Sonarr/Radarr webhooks.
   - What's unclear: whether the owner wants the README to (a) state the limitation and recommend network restriction as the practical protection for direct *arr webhooks, keeping the secret for setups with a signing sender/proxy, or (b) keep the D-03 recommendation as written (not recommended: it misleads users into breaking pruning).
   - Recommendation: **(a)**. Keep D-03's consequence sentence. Replace "recommend setting a secret" with: "Webhook verification needs a sender that signs each request (HMAC-SHA256 of the body in `X-Webhook-Signature`); Sonarr and Radarr don't sign natively, so for direct *arr webhooks, restrict who can reach port 8800." Separately, consider a backlog item to accept a static shared-secret header or Basic auth, which Sonarr can send. That would be a behaviour change, out of scope here. SECURITY.md:43 implies Sonarr can sign; D-08 forbids editing it, so it stays inconsistent unless the owner extends scope.
   - **RESOLVED (owner, 2026-11-18): option (a).** D-03 was revised in 127-CONTEXT.md (state the limit; do not recommend a secret or `webhook_require_secret = true` for Sonarr/Radarr; name restricting access to port 8800). D-08 was widened to also correct the SECURITY.md webhook bullet, so the two files agree. Accepting an authentication method Sonarr/Radarr can send is captured as backlog 999.8 (not in this phase).
2. **CONFIGURATION.md omits `webhook_require_secret` and the `encryption.enabled` default row.** The new Documentation section sends readers there. Options: leave as-is and point README's `webhook_require_secret` mention at SECURITY.md (in scope), or have the owner approve a small CONFIGURATION.md addition (scope extension). Recommendation: in-scope option now, and note it for a later docs pass.
   - **RESOLVED (owner, 2026-11-18): in-scope option.** Recorded under Deferred Ideas in 127-CONTEXT.md. No `docs/CONFIGURATION.md` edits in this phase; the README points to SECURITY.md for `webhook_require_secret`.
3. **Phase-40 SUMMARY guidance** (`40-03-SUMMARY.md:142`) is archival and not user-facing; no action.
   - **RESOLVED: no action.** Archived planning history is not edited.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | Link/anchor check | ✓ | system | grep + `test -f` |
| grep / git | Phrase and diff-scope checks | ✓ | system | — |
| ruff | CI parity (unaffected) | ✓ | 0.15.9 | — |
| lychee / markdown-link-check | — | ✗ | — | Not needed; stdlib script |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None for prose. Mechanical shell/python3 checks. Existing CI: pytest, `ruff check src/python/`, Angular, e2e (all unaffected) |
| Config file | none. No Wave 0 install needed |
| Quick run command | the link + phrase check block below (< 2 s) |
| Full suite command | same block + `ruff check src/python/` (sanity; expects no change) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Six guides linked; Documentation heading after Quick Start and before Features; no website link; all relative links + anchors resolve | mechanical | link resolver + `grep -c` checks below | n/a (inline) |
| DOC-02 | "Security by default" gone; `api_token`, `webhook_secret`, `webhook_require_secret`, `[Encryption]` stated with off/False defaults | grep | `! grep -qi "security by default" README.md` + presence greps | n/a |
| DOC-03 | No "never delete(s)"/"safely reclaim"/"maximum transfer speed"; How It Works mentions off by default, 60, dry-run | grep | absence + presence greps | n/a |
| DOC-04 | Network-exposure note in Quick Start (between `## Quick Start` and the next `##`) mentions all interfaces, reverse proxy, UI contains token | grep/awk | section-scoped grep below | n/a |
| D-08 | (SUPERSEDED row: was "one-line change, numstat `1 1`".) Widened D-08: only the intro sentence and the webhook bullet change; "several protections are active by default" gone | git/python | `python3 .planning/phases/127-readme-accuracy/127-check.py security` | yes |
| Scope | Only README.md, SECURITY.md (+ .planning) changed | git | `git diff --name-only main -- . ':!.planning'` | n/a |
| Claims review (D-04) | Human/LLM read-through against Finding 4 table | manual | checklist in PLAN verify | — |

### Verification block (SUPERSEDED: replaced by `127-check.py`; kept for history, do not copy)

The block below predates the revised D-03 and widened D-08. Its last lines expect `1  1  SECURITY.md`, which is no longer correct. Use `.planning/phases/127-readme-accuracy/127-check.py` instead.

```bash
cd /Users/julianamacbook/seedsyncarr
# 1. Relative links, images and same-file anchors resolve
python3 - <<'EOF'
import re, os, sys
t = open('README.md').read()
def slug(h):
    h = h.strip().lower()
    h = re.sub(r'[^\w\- ]', '', h)
    return h.replace(' ', '-')
anchors = {slug(m) for m in re.findall(r'^#{1,6}\s+(.+)$', t, re.M)}
links = re.findall(r'\]\(([^)\s]+)\)', t) + re.findall(r'(?:src|srcset)="([^"]+)"', t)
bad = []
for l in links:
    if re.match(r'(https?:|mailto:)', l): continue
    if l.startswith('#'):
        if l[1:] not in anchors: bad.append(l)
        continue
    if not os.path.exists(l.split('#')[0]): bad.append(l)
print('BAD:', bad) if bad else print('links OK', len(links))
sys.exit(1 if bad else 0)
EOF
# 2. Required guide links present
for g in docs/GETTING-STARTED.md docs/CONFIGURATION.md SECURITY.md docs/ARCHITECTURE.md docs/DEVELOPMENT.md docs/TESTING.md; do
  grep -q "]($g" README.md || echo "MISSING LINK $g"; done
# 3. Forbidden phrases (expect no output)
grep -n -i -E "never delete|security by default|maximum transfer speed|safely reclaim|thejuran\.github\.io" README.md
grep -n "several protections are active by default" SECURITY.md
# 4. Required statements
for p in api_token webhook_secret webhook_require_secret "\[Encryption\]" "reverse proxy" "dry-run" "60"; do
  grep -q -i -- "$p" README.md || echo "MISSING TERM $p"; done
# 5. Section order: Quick Start < Documentation < Features; Usage Examples < Contributing
awk '/^## /{print NR": "$0}' README.md
# 6. Network-exposure note inside Quick Start section
awk '/^## Quick Start/{f=1;next} /^## /{f=0} f' README.md | grep -i -E "all (host )?interfaces" >/dev/null || echo "MISSING exposure note"
# 7. Scope
git diff --numstat main -- SECURITY.md      # expect: 1  1  SECURITY.md
git diff --name-only main -- . ':!.planning' # expect: README.md SECURITY.md
```

### Sampling Rate
- (Updated 2026-11-18; see 127-VALIDATION.md.) **Per task commit:** that task's `127-check.py` group (`structure`, then `claims`, then `all`).
- **Phase gate:** `127-check.py all` green, `ruff check src/python/` clean, and the manual read-through in 127-VALIDATION.md done before `/bm:verify-work`.

### Wave 0 Gaps
None. No test infrastructure is needed; checks are inline.

## Security Domain

Docs-only, so no ASVS control changes. The relevant risk is **misinformation**: users relying on stated protections that are off, or following advice that disables a feature.

| ASVS Category | Applies | Note |
|---------------|---------|------|
| V2 Authentication | Documentation only | README must state Bearer auth is off when `api_token` is empty, the webhook paths are exempt, and the UI carries the token |
| V5 Input Validation | No | — |
| V6 Cryptography | Documentation only | Encryption at rest opt-in; HMAC requires a signing sender |
| V14 Configuration | Yes (docs) | Accurate defaults; exposure note |

| Threat | STRIDE | Mitigation in this phase |
|--------|--------|--------------------------|
| Forged import webhook when no secret is set | Spoofing | State plainly (D-03); recommend network restriction |
| Over-trusting `api_token` as UI protection | Elevation of privilege | DOC-04 note |
| Secret-recommendation breaking pruning (Finding 6) | Denial of service (self-inflicted) | Accurate wording per the revised D-03 (Open Question 1, resolved) |

## Project Constraints (from CLAUDE.md)

- No `./CLAUDE.md` in the repo. CLAUDE.local.md requires a Codex cross-AI plan review run **in parallel with** bm-plan-checker on every plan-phase, with `127-REVIEWS.md` committed. This affects the orchestrator, not plan content.
- Global: the owner is a PM. Technical choices are Claude's; product wording choices go to the owner with plain-language tradeoffs (Open Question 1 was handled this way and is resolved).
- Memory: one PR per phase. CI runs whole-tree `ruff check src/python/` separately from pytest (unaffected here, but note it in plan verify).
- Project skills: only `aidesigner-frontend` (UI generation), which doesn't apply.

## Sources

### Primary (HIGH)
- Repo source read this session: `src/python/seedsyncarr.py:378-436, 488-509`; `src/python/common/config.py:260-276, 380-398, 570-650`; `src/python/web/web_app.py:59-65, 100-163, 219-235`; `src/python/web/web_app_job.py:27`; `src/python/web/handler/webhook.py:30-104`; `web/handler/config.py:150-163, 182, 280, 372`; `web/handler/controller.py:65-72, 186-194`; `web/handler/status.py:12-18`; `common/types.py:17`; `controller/controller.py:1031-1037, 1355-1368`; `src/angular/src/app/services/utils/auth.interceptor.ts`; `settings-page.component.ts:103-105`; `options-list.ts:188-211`; `docs/CONFIGURATION.md`; `SECURITY.md`; `README.md`; `.github/workflows/ci.yml`; `src/python/pyproject.toml`
- Sonarr source `WebhookProxy.cs` (develop): https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs
- Sonarr PR #7371 (custom webhook headers, merged 2024-11-15): https://github.com/Sonarr/Sonarr/pull/7371

### Secondary (MEDIUM)
- https://spiderhash.io/blog/how-to-receive-webhooks-from-sonarr/ — Sonarr/Radarr webhook form fields; no HMAC signing
- PyPI JSON API: seedsyncarr 1.8.0 published

## Metadata

**Confidence breakdown:**
- Defaults and controls: HIGH (read from source with line numbers)
- README inventory: HIGH (line-numbered read; link check executed)
- Sonarr signing gap: HIGH for Sonarr (source read), MEDIUM for Radarr (A1)

**Research date:** 2026-11-18
**Valid until:** until next change to README.md, SECURITY.md, `web/handler/webhook.py` or default config (stable)
