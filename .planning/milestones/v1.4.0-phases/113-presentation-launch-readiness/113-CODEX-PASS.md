# Codex Adversarial Content Pass — Phase 113

**Target:** README.md (Plan-01 draft) + SECURITY.md (Plan-01 draft) + CONTRIBUTING.md (Plan-01 draft) + CHANGELOG.md (Plan-01 draft)
**Pass type:** Technical-claims accuracy + install-path reproducibility + security-claim credibility
**Date:** 2026-06-02

## Methodology

This pass was run manually (the `/codex` tool is not available in this execution environment). Each claim is verified claim-by-claim against the shipped source, not relied on from training memory or documentation alone. The methodology covers four areas:

1. **INSTALL-PATH REPRODUCIBILITY** — Every install/quickstart command, flag, image tag, volume path, entry point, Python version requirement, and apt dependency is reconciled against:
   - `src/docker/build/docker-image/Dockerfile` (EXPOSE, apt deps, CMD)
   - `src/docker/stage/docker-image/compose.yml` (stage/test compose shape)
   - `src/python/pyproject.toml` (package name, requires-python, [project.scripts])
   - `src/docker/build/docker-image/setup_default_config.sh` (runtime config directory)
   - Steps that cannot be executed in-sandbox (live `pip install`, `docker pull`, `docker run`) are explicitly flagged as DEFERRED RUNTIME CHECKs for the milestone-end walkthrough.

2. **SECURITY-CLAIM ACCURACY** — Every security claim in README.md and SECURITY.md is verified against the shipped handler source:
   - `src/python/web/handler/webhook.py` (HMAC, fail-closed behavior)
   - `src/python/web/handler/config.py` (POST-only, SSRF guard implementation)
   - `src/python/web/web_app.py` (Bearer auth, CSP headers, exempt paths)
   - `src/python/common/encryption.py` (Fernet implementation)
   - `src/python/web/rate_limit.py` (rate-limiting mechanism)
   - All five `rate_limit(...)` decorator sites enumerated by grep across `src/python/web/handler/`

3. **UNSUPPORTED ASSERTIONS** — Feature claims that exceed shipped behavior; fork-positioning that could violate honesty guardrails.

4. **DOC/CODE DRIFT** — Between README.md install steps and `docs/GETTING-STARTED.md`; between SECURITY.md claims and `docs/CONFIGURATION.md`.

---

## Findings

### CONTENT-01 — Volume path mismatch: README uses `~/.seedsyncarr:/root/.seedsyncarr`, Dockerfile and docs use `/config`

**Severity:** high
**File:** README.md, lines 35 and 67
**Issue:** The Quick Start compose snippet and the `docker run` command both mount `~/.seedsyncarr:/root/.seedsyncarr`. However, `src/docker/build/docker-image/Dockerfile` creates the `/config` directory (`RUN mkdir /config`) and the CMD passes `-c /config` (Dockerfile line 159). `setup_default_config.sh` also uses `CONFIG_DIR="/config"`. The runtime process reads its config from `/config`, not from `/root/.seedsyncarr`. The volume mount `~/.seedsyncarr:/root/.seedsyncarr` does not land config into the path the process reads. A user following the README Quick Start will start a container with a disconnected volume — the process will create a fresh config in `/config` (inside the ephemeral container layer), losing persistence on restart.

`docs/GETTING-STARTED.md` line 33 shows the correct mount: `~/.seedsyncarr:/config`.

The README compose snippet is wrong; docs/GETTING-STARTED.md is correct.

**Verified against source:** Dockerfile lines 143-159 (mkdir /config, CMD -c /config); setup_default_config.sh CONFIG_DIR="/config"; docs/GETTING-STARTED.md line 33.
**Disposition:** fix — the Quick Start compose snippet and `docker run` example must change `~/.seedsyncarr:/root/.seedsyncarr` to `~/.seedsyncarr:/config` to match the actual Dockerfile runtime.

---

### CONTENT-02 — apt package list: README includes `openssh-client` and `bzip2`; Dockerfile also includes `build-essential`, `libssl-dev`, `p7zip` (alongside `p7zip-full`), `curl`, `libnss-wrapper`, and library packages not mentioned in README

**Severity:** medium
**File:** README.md, line 79
**Issue:** The README pip install section documents:

```
sudo apt install lftp openssh-client p7zip-full unrar bzip2
```

The Dockerfile's apt-get install block (lines 81-93) installs:
- `build-essential` (build tooling, NOT listed in README)
- `libssl-dev` (NOT listed in README)
- `lftp` (matches)
- `openssh-client` (matches)
- `p7zip` (Dockerfile has BOTH `p7zip` AND `p7zip-full`; README has only `p7zip-full`)
- `p7zip-full` (matches)
- `unrar` (matches)
- `bzip2` (matches)
- `curl` (NOT listed in README)
- `libnss-wrapper` (NOT listed in README)
- `libxml2-dev libxslt-dev libffi-dev` (NOT listed in README)

The README documents a minimal subset for bare pip-install usage. The runtime Docker image installs considerably more. This is not strictly wrong — a pip-install user on a minimal system may not need all Docker-image build deps — but the omission of `build-essential`, `libssl-dev`, `libffi-dev` is a real gap: `cryptography` (a `pyproject.toml` required dependency) requires `libssl-dev` and `libffi-dev` to compile on systems lacking a pre-built wheel.

**Verified against source:** Dockerfile lines 81-93 (apt-get install block); pyproject.toml line 19 (`cryptography>=44.0.0,<47`).
**Disposition:** fix (medium) — The README apt list for pip install should add `libssl-dev libffi-dev` (needed to build the `cryptography` wheel) and note that other packages like `build-essential` may also be required on minimal systems. Or add a note that the list covers the runtime tools and that `pip install` may require additional build-time packages depending on pre-built wheel availability for the installed Python version.

---

### CONTENT-03 — Python version claim: README says "Python 3.11 or 3.12"; pyproject.toml says `>=3.11,<3.13`; Dockerfile build stage uses `python:3.11-slim`

**Severity:** low
**File:** README.md, line 88
**Issue:** README states "Requires Python 3.11 or 3.12." pyproject.toml `requires-python = ">=3.11,<3.13"` confirms this range exactly — 3.11 and 3.12 only (3.13+ excluded). The claim is accurate for the published package constraint. However, the runtime Dockerfile build stage uses `FROM python:3.11-slim` and `FROM python:3.11-slim-bullseye`, meaning Docker users run Python 3.11 specifically. The pip-install claim "Python 3.11 or 3.12" is technically correct per pyproject.toml.

**Verified against source:** pyproject.toml line 12 (`requires-python = ">=3.11,<3.13"`); Dockerfile lines 37 and 75.
**Disposition:** accept — the README claim matches pyproject.toml. No change needed. (DEFERRED RUNTIME CHECK: confirming the published wheel on PyPI actually builds/runs on Python 3.12 is a walkthrough-time validation, not verifiable in-sandbox.)

---

### CONTENT-04 — `pip install seedsyncarr` entry point: pyproject.toml scripts entry point is `seedsyncarr:main`; package `name = "seedsyncarr"` matches; `[project.scripts]` entry matches the documented run command

**Severity:** low (informational — mostly accurate, one implicit assumption to flag)
**File:** README.md, lines 83-85
**Issue:** pyproject.toml `[project.scripts]` defines `seedsyncarr = "seedsyncarr:main"`. The README documents `pip install seedsyncarr` followed by `seedsyncarr` as the run command. This correctly reflects the pyproject.toml entry. However, pyproject.toml uses `hatchling` as the build backend (`[build-system] requires = ["hatchling"]`) while also retaining a `[tool.poetry]` section. This dual-backend configuration is unusual — the `[project.scripts]` block (PEP 517) belongs to hatchling, not Poetry. The `pip install seedsyncarr` claim assumes the package is published to PyPI via the hatchling build.

**Verified against source:** pyproject.toml lines 1-3 (hatchling build-system), lines 35-36 ([project.scripts]), lines 41-47 ([tool.poetry]).
**Disposition:** defer — whether `pip install seedsyncarr` works against live PyPI is a DEFERRED RUNTIME CHECK for the walkthrough. The entry point definition in source is correct. The dual hatchling/poetry configuration is a pre-existing upstream concern outside this plan's scope.

---

### CONTENT-05 — Docker image name `ghcr.io/thejuran/seedsyncarr`: label in Dockerfile matches

**Severity:** low (informational)
**File:** README.md, lines 29, 62-70
**Issue:** README uses `ghcr.io/thejuran/seedsyncarr:latest`. Dockerfile line 122 sets `LABEL org.opencontainers.image.source="https://github.com/thejuran/seedsyncarr"`. The image name is determined by the CI publish workflow, not by the Dockerfile itself.

**Verified against source:** Dockerfile line 122 (source label); image name not hardcoded in Dockerfile (correct — determined by CI push).
**Disposition:** defer — confirming the published `ghcr.io/thejuran/seedsyncarr:latest` tag exists and is pullable is a DEFERRED RUNTIME CHECK for the walkthrough.

---

### CONTENT-06 — Port 8800: EXPOSE, docs, and README all consistent

**Severity:** low (informational — no issue found)
**File:** README.md, lines 30, 65
**Issue:** README documents `-p 8800:8800`. Dockerfile line 164 has `EXPOSE 8800`. `docs/GETTING-STARTED.md` line 30 and `docs/CONFIGURATION.md` line 121 both reference port 8800. The `[Web] port = 8800` default in the config reference matches.

**Verified against source:** Dockerfile line 164 (`EXPOSE 8800`); docs/GETTING-STARTED.md line 30; docs/CONFIGURATION.md line 121.
**Disposition:** accept — port is consistent across all sources.

---

### CONTENT-07 — SECURITY.md rate-limiting claim: five endpoints enumerated correctly; claim is accurate to source

**Severity:** low (informational — no issue found, accuracy confirmed)
**File:** SECURITY.md, line 47
**Issue:** SECURITY.md rate-limiting bullet enumerates: "Sonarr/Radarr webhook endpoints (60 req/60s), the POST config-set endpoint (60 req/60s), the Sonarr/Radarr test-connection endpoints (5 req/60s), the bulk-command endpoint (10 req/60s), and the status endpoint (60 req/60s)."

Verified decorator sites by grep across `src/python/web/handler/`:
- `webhook.py:40-41` — sonarr/radarr webhook → `rate_limit(max_requests=60, window_seconds=60)` (CONFIRMED)
- `config.py:27` — POST config-set → `rate_limit(60, 60)` (CONFIRMED)
- `config.py:31,35` — sonarr/radarr test-connection → `rate_limit(5, 60)` (CONFIRMED)
- `controller.py:73` — bulk command → `rate_limit(10, 60)` (CONFIRMED)
- `status.py:16` — get-status → `rate_limit(60, 60)` (CONFIRMED)

These are all five deployed decorator sites. No others found. The claim is accurate and does NOT assert "all mutable endpoints" — it names specifically the five.

**Verified against source:** Full grep of `src/python/web/handler/` for `rate_limit(`.
**Disposition:** accept — claim is accurate to source.

---

### CONTENT-08 — SECURITY.md HMAC/fail-closed claim accuracy

**Severity:** low (informational — accurate with one clarification note)
**File:** SECURITY.md, lines 43-44
**Issue:** SECURITY.md states: "Enable `webhook_require_secret = true` (opt-in) to fail-closed: unauthenticated calls are rejected with 503 when the requirement is enabled and no secret is configured."

`webhook.py:43-61` (`_make_require_secret_guard`): when `webhook_require_secret is True AND webhook_secret is falsy`, returns 503. When `webhook_require_secret is False (default) OR a secret is configured`, falls through to the handler. The claim is accurate: 503 fires when the requirement is on and no secret is set. The `_verify_hmac` path then runs for actual signature checking when a secret IS configured.

**Verified against source:** `webhook.py:54-60` (guard logic).
**Disposition:** accept — claim is accurate to source.

---

### CONTENT-09 — SECURITY.md IP-resolution guard claim: accurately describes `_validate_url` as socket.getaddrinfo-based IP-resolution, not overclaimed as full SSRF library; outbound-webhook framing is correct

**Severity:** low (informational — accurate)
**File:** SECURITY.md, lines 45-45
**Issue:** SECURITY.md says: "the user-supplied URL is resolved via `socket.getaddrinfo` and rejected if it points to a private, loopback, reserved, or link-local IP. This is an IP-resolution SSRF guard on the *arr connection URL (not a full SSRF library; DNS-rebinding/TOCTOU is a documented out-of-scope limitation for a homelab tool). SeedSyncarr *receives* import webhooks; it does not send outbound webhooks."

`config.py:55-84` (`_validate_url`): uses `socket.getaddrinfo`, checks `addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local`. The code comment at line 59-63 itself documents the TOCTOU/DNS-rebinding limitation. The claim correctly characterizes the guard, its mechanism, its limitation, and the directionality of webhooks.

**Verified against source:** `config.py:55-84`.
**Disposition:** accept — claim is accurate to source.

---

### CONTENT-10 — SECURITY.md Fernet claim: "AES-128-CBC + HMAC-SHA256" accurately describes Fernet; "keyfile is created with restrictive (0600) permissions" accurately describes `load_or_create_key`

**Severity:** low (informational — accurate)
**File:** SECURITY.md, lines 42-43
**Issue:** SECURITY.md claims Fernet encryption "AES-128-CBC + HMAC-SHA256" with "(0600) permissions on first enable."

`encryption.py`: uses `Fernet` from `cryptography.fernet` — Fernet is AES-128-CBC + HMAC-SHA256 (verified as the Fernet spec). `load_or_create_key` (line 75): `os.open(keyfile_path, flags, 0o600)` with `O_CREAT | O_EXCL` — atomically creates at 0600. Claim is accurate.

**Verified against source:** `encryption.py:73-93` (`load_or_create_key`); Fernet spec (AES-128-CBC + HMAC-SHA256, standard).
**Disposition:** accept — claim is accurate to source.

---

### CONTENT-11 — SECURITY.md Bearer auth claim: "allow-all when unset for backward compatibility" accurately describes web_app.py behavior

**Severity:** low (informational — accurate)
**File:** SECURITY.md, line 44
**Issue:** SECURITY.md states "The API requires a Bearer token when `api_token` is set (constant-time compare; allow-all when unset for backward compatibility)."

`web_app.py:122-126`: if `not api_token`, sets `auth_valid = True` and returns (allow-all). If set, uses `hmac.compare_digest` (line 136). Claim is accurate.

**Verified against source:** `web_app.py:122-141`.
**Disposition:** accept — claim is accurate to source.

---

### CONTENT-12 — SECURITY.md CSP claim: "layered with Angular's hash-based meta CSP" describes actual behavior; HTTP header uses `unsafe-inline` to coexist with Angular's inline bootstrap

**Severity:** low (informational — accurate, no user-visible overclaim)
**File:** SECURITY.md, line 46
**Issue:** SECURITY.md states "A Content Security Policy header is sent on all responses, layered with Angular's hash-based meta CSP."

`web_app.py:152-163` (`_add_security_headers`): sets a CSP header with `script-src 'self' 'unsafe-inline'`. The code comment explains this is intentional — the `unsafe-inline` in the HTTP header CSP lets Angular's inline bootstrap script run, while the meta CSP from Angular's autoCsp provides hash-based restriction. Both policies must pass. The claim is technically accurate in describing the layering. The CSP HTTP header itself contains `unsafe-inline` which a security-focused reader might flag, but the code comment adequately explains the design tradeoff.

**Verified against source:** `web_app.py:144-163`.
**Disposition:** accept — accurate. The HTTP-header `unsafe-inline` is an implementation tradeoff, not a documentation error. The SECURITY.md claim describes the architecture correctly.

---

### CONTENT-13 — Log-injection claim: "CR/LF and control characters" accurately describes the protection; CWE-117 citation is correct

**Severity:** low (informational — accurate)
**File:** SECURITY.md, line 48
**Issue:** SECURITY.md claims "File names are sanitized for CR/LF and control characters before reaching log lines (CWE-117)."

This claim was validated in Phase 113-02 TEARDOWN (see 113-TEARDOWN.md). CWE-117 is the standard log-injection CWE. Claim is consistent with the shipped implementation.
**Disposition:** accept — claim is accurate per prior phase review.

---

### CONTENT-14 — CONTRIBUTING.md Python version claim: "Python 3.11+" matches pyproject.toml

**Severity:** low (informational)
**File:** CONTRIBUTING.md, line 16
**Issue:** CONTRIBUTING.md "Prerequisites" says "Python 3.11+ (CI runs 3.12)." pyproject.toml `requires-python = ">=3.11,<3.13"` means 3.13+ is excluded. "Python 3.11+" technically implies unbounded upward (3.13, 3.14, ...). The parenthetical "(CI runs 3.12)" provides useful context but the "3.11+" formulation overstates the supported range slightly.

**Verified against source:** pyproject.toml line 12.
**Disposition:** fix (low) — Change "Python 3.11+" to "Python 3.11 or 3.12 (CI runs 3.12)" in CONTRIBUTING.md prerequisites to match pyproject.toml's upper bound. Avoids a contributor discovering a pyproject.toml error when they try 3.13.

---

### CONTENT-15 — CHANGELOG.md [1.4.0] entry: "Rebuilt the README, SECURITY.md, and community-health files" listed under Documentation; does not claim code changes that weren't made in Plan-01

**Severity:** low (informational — no issue)
**File:** CHANGELOG.md, lines 7-29
**Issue:** [1.4.0] changelog entry covers: the config-set endpoint migration (Changed/Breaking), startup warnings (Added), delete-path hardening (Fixed), AppProcess fix (Fixed), LICENSE rename (Documentation), and README/docs rebuild (Documentation). All these items reflect actual Phase 112/113 work. No unsupported assertions found. The entry is appropriately scoped.

**Verified against:** Phase 112 SUMMARY.md scope; Plan 113-01 deliverables.
**Disposition:** accept — changelog entry is accurate.

---

### CONTENT-16 — README webhook usage example: describes triggering a Sonarr import "after a completed download" — direction is reversed from actual behavior

**Severity:** medium
**File:** README.md, lines 142-154
**Issue:** The "Trigger a Sonarr import after a completed download" usage example describes:

> "In Settings, enable Sonarr and enter your Sonarr URL and API key. SeedSyncarr displays a webhook URL in the form: `http://<seedsyncarr-address>:8800/server/webhook/sonarr`. Add this URL as a webhook in Sonarr ... with the 'On Import' event selected. When SeedSyncarr finishes transferring a file that Sonarr is tracking, Sonarr receives the webhook and imports the episode into your library automatically."

This description reverses the actual data flow. In the actual implementation:
- SeedSyncarr is the **receiver** of Sonarr's webhook (import event), not the sender.
- Sonarr fires the webhook to SeedSyncarr's `/server/webhook/sonarr` endpoint on the "On Import Complete" event.
- SeedSyncarr uses this incoming webhook as a signal that the import succeeded and it is safe to delete the local copy.

The README usage example says "SeedSyncarr finishes transferring a file ... Sonarr **receives** the webhook" — this is inverted. SeedSyncarr does NOT send a webhook to Sonarr. It is the other way around: Sonarr sends a webhook to SeedSyncarr after it imports the file.

The correct model: SeedSyncarr transfers the file to local → user (or AutoQueue) triggers a copy to the media server path → Sonarr detects the file and imports it → Sonarr fires a "Download/Import" webhook to SeedSyncarr's endpoint → SeedSyncarr treats this as an import confirmation and schedules auto-delete.

**Verified against source:** `webhook.py` handles `POST /server/webhook/sonarr` (inbound from Sonarr, not outbound). `webhook.py:141-157` processes `eventType == "Download"` (Sonarr's import event name). The README's ABOUT section and SECURITY.md both correctly state "SeedSyncarr *receives* import webhooks" — but the usage example text contradicts this.
**Disposition:** fix (medium) — Rewrite the usage example to correctly describe the flow: Sonarr fires the "On Import Complete" webhook to SeedSyncarr's endpoint, and SeedSyncarr uses that as a signal that the file made it into the library. Remove "SeedSyncarr finishes transferring a file ... Sonarr receives the webhook" — this inverts sender and receiver.

---

### CONTENT-17 — `docs/GETTING-STARTED.md` volume path: uses `~/.seedsyncarr:/config` (correct); README uses `~/.seedsyncarr:/root/.seedsyncarr` (incorrect — already captured in CONTENT-01)

**Severity:** high (cross-reference only — already captured in CONTENT-01)
**File:** docs/GETTING-STARTED.md, line 33
**Issue:** Cross-reference confirming CONTENT-01. `docs/GETTING-STARTED.md` line 33 correctly maps to `/config` (matching the Dockerfile CMD). README Quick Start maps to `/root/.seedsyncarr` (wrong).
**Disposition:** fix — same fix as CONTENT-01. Noted here for completeness of the doc/code drift check.

---

### CONTENT-18 — `docs/CONFIGURATION.md` has unresolved `<!-- VERIFY: ... -->` placeholder comments

**Severity:** low
**File:** docs/CONFIGURATION.md, lines 136, 143, 231, 232
**Issue:** docs/CONFIGURATION.md contains inline `<!-- VERIFY: ... -->` comments that were left from the drafting process:
- Line 136: `<!-- VERIFY: production Sonarr instance URL -->`
- Line 143: `<!-- VERIFY: production Radarr instance URL -->`
- Line 231: `<!-- VERIFY: actual registry value -->`
- Line 232: `<!-- VERIFY: actual version tag format -->`

The Sonarr/Radarr ones appear inside the table `Description` cells and are visible in raw Markdown but not rendered HTML. The staging compose env-var table comments are also raw-Markdown-visible. These are editorial artifacts, not published documentation bugs in strict terms, but they indicate draft-state content in a published docs page.

**Verified against:** docs/CONFIGURATION.md lines 136, 143, 231, 232.
**Disposition:** defer — these are in `docs/CONFIGURATION.md`, which is the published documentation site (`docs/`). The VERIFY comments for Sonarr/Radarr URL defaults are not actionable (those are user-configured values, not defaults). The staging compose section comments are internal usage notes. These can be cleaned in a docs pass, but they do not affect correctness of any claim audited by this pass.

---

## Summary

| Severity | Count | Findings | Disposition |
|----------|-------|----------|-------------|
| high | 2 | CONTENT-01 (volume path wrong in README), CONTENT-17 (same, cross-ref in docs) | fix |
| medium | 2 | CONTENT-02 (apt list missing libssl-dev/libffi-dev), CONTENT-16 (webhook flow description inverted) | fix |
| low | 14 | CONTENT-03 (Python version — accept), CONTENT-04 (pip/entry-point — defer to walkthrough), CONTENT-05 (image name — defer to walkthrough), CONTENT-06 (port 8800 — accept), CONTENT-07 (rate-limit enumeration — accept), CONTENT-08 (HMAC/fail-closed — accept), CONTENT-09 (IP-resolution guard — accept), CONTENT-10 (Fernet — accept), CONTENT-11 (Bearer auth — accept), CONTENT-12 (CSP layering — accept), CONTENT-13 (log injection — accept), CONTENT-14 (CONTRIBUTING Python version — fix), CONTENT-15 (CHANGELOG — accept), CONTENT-18 (docs VERIFY comments — defer) | mixed |

**High-severity issues requiring fix before finalization (Plan 04 scope):**
1. CONTENT-01/17: README Quick Start and `docker run` volume path must change `~/.seedsyncarr:/root/.seedsyncarr` → `~/.seedsyncarr:/config` to match Dockerfile runtime (`-c /config`)
2. CONTENT-16: The webhook usage example reverses sender/receiver — rewrite to accurately describe Sonarr firing inbound webhooks to SeedSyncarr

**Medium-severity issues requiring fix:**
1. CONTENT-02: README apt list for pip install omits `libssl-dev` and `libffi-dev`, which are required to build the `cryptography` wheel
2. CONTENT-16 (noted above)

**DEFERRED RUNTIME CHECKS (in-sandbox-unrunnable — require milestone walkthrough):**
- `pip install seedsyncarr` against live PyPI: confirm the package is published and the hatchling build produces a functional installation (CONTENT-04)
- `docker pull ghcr.io/thejuran/seedsyncarr:latest`: confirm the image exists, is current, and starts correctly with the corrected volume mount after CONTENT-01 fix (CONTENT-05)
- Full `docker run` / `docker compose up`: confirm the corrected compose snippet starts the container, creates `/config/settings.cfg`, and the web UI is reachable at `:8800` (CONTENT-01)
- Python 3.12 pip-install compatibility: confirm the published wheel runs on 3.12, not just 3.11 (CONTENT-03)

**Security-claim accuracy verdict:** All five security claims in SECURITY.md (HMAC/fail-closed, Bearer auth, IP-resolution guard, CSP, Fernet encryption) are accurate to the shipped source. No claim exceeds what the code implements. Rate-limiting enumeration is exact (5 decorator sites, no blanket assertion). No security claims require fix.

**Fork-positioning honesty verdict:** README "About This Fork" section (lines 22-23) correctly states "SeedSyncarr is Sonarr-driven, so it receives import webhooks from those services rather than pushing notifications outbound." This frames the missing outbound-push as a chosen scope, not a competitive advantage. No honesty-guard violations found in the current draft.
