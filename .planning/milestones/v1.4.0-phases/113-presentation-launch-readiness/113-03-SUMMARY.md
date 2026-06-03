---
phase: 113-presentation-launch-readiness
plan: "03"
subsystem: docs
tags: [codex-pass, adversarial-audit, install-path, security-claims, content-credibility]
dependency_graph:
  requires: ["113-01"]
  provides: ["113-CODEX-PASS.md"]
  affects: ["113-04-PLAN.md (finalization)"]
tech_stack:
  added: []
  patterns: ["structured-findings-artifact", "claim-by-claim-source-verification"]
key_files:
  created:
    - .planning/milestones/v1.4.0-phases/113-presentation-launch-readiness/113-CODEX-PASS.md
  modified: []
decisions:
  - "D-10: Codex adversarial content pass over Plan-01 drafts captured as written artifact before finalization (LAUNCH-01)"
  - "Manual audit performed (codex tool unavailable in env); methodology documented in 113-CODEX-PASS.md"
metrics:
  duration: "~45 min"
  completed: "2026-06-02"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 113 Plan 03: Codex Adversarial Content Pass — Summary

**One-liner:** Claim-by-claim adversarial content audit of the Plan-01 drafted docs against shipped Dockerfile/pyproject/source, producing 18 structured findings with fix/accept/defer dispositions for Plan-04 finalization.

## What Was Built

`113-CODEX-PASS.md` — a structured adversarial content-audit artifact covering the Plan-01 drafted README.md, SECURITY.md, CONTRIBUTING.md, and CHANGELOG.md. The pass was run manually (the `/codex` tool is unavailable in this environment), with methodology documented in the artifact.

The audit covers four areas:
1. Install-path reproducibility: every documented command/flag/volume/port/apt-dep reconciled against actual source files
2. Security-claim accuracy: all five SECURITY.md security bullets verified against shipped handler source
3. Unsupported assertions and fork-positioning honesty
4. Doc/code drift between README and docs/

## Findings Summary

**2 high-severity findings (fix required before Plan 04 finalization):**

- **CONTENT-01/17:** README Quick Start compose snippet and `docker run` example both mount `~/.seedsyncarr:/root/.seedsyncarr`, but the Dockerfile CMD passes `-c /config` and `setup_default_config.sh` writes to `/config`. A user following the README runs with a disconnected volume. `docs/GETTING-STARTED.md` already has the correct mount (`~/.seedsyncarr:/config`). Fix: change README volume to `~/.seedsyncarr:/config`.

- **CONTENT-16:** The "Trigger a Sonarr import" usage example (README lines 142-154) describes the webhook flow with sender/receiver inverted — it says "SeedSyncarr finishes transferring a file ... Sonarr receives the webhook." In reality, Sonarr fires the inbound webhook to SeedSyncarr's `/server/webhook/sonarr` endpoint. The About section and SECURITY.md both state this correctly; only the usage example is wrong.

**2 medium-severity findings (fix required):**

- **CONTENT-02:** README apt list for pip install (`sudo apt install lftp openssh-client p7zip-full unrar bzip2`) omits `libssl-dev` and `libffi-dev`, which are required build-time dependencies for the `cryptography` Python wheel (a `pyproject.toml` runtime dependency). Users on minimal systems may encounter build failures without these.

- **CONTENT-16:** (noted above; also medium on webhook-flow accuracy grounds)

**Security-claim accuracy verdict: all claims accepted.** All five SECURITY.md security bullets (HMAC fail-closed, Bearer auth, IP-resolution guard, CSP, Fernet encryption) are accurate to the shipped source. The rate-limiting enumeration names exactly five decorator sites confirmed by grep — no blanket "all mutable endpoints" assertion. No security claims require correction.

**Fork-positioning honesty verdict: no violations.** "SeedSyncarr is Sonarr-driven, so it receives import webhooks from those services rather than pushing notifications outbound" correctly frames the missing outbound-push as a chosen scope.

## Deferred Runtime Checks

The following install steps cannot be validated in-sandbox and are flagged for the milestone-end walkthrough:
- `pip install seedsyncarr` against live PyPI (confirm package exists and entry point works)
- `docker pull ghcr.io/thejuran/seedsyncarr:latest` (confirm image is published and current)
- Full `docker compose up` with the corrected volume path (confirm settings.cfg created at `/config`, web UI reachable at `:8800`)
- Python 3.12 pip-install compatibility (pyproject.toml allows 3.11-3.12; verify both work)

## Deviations from Plan

None — plan executed exactly as written. The `/codex` tool was unavailable; the equivalent manual audit was performed per the plan's `<codex_invocation>` fallback clause, and the methodology section of 113-CODEX-PASS.md documents this.

## Known Stubs

None — this plan produces a findings artifact only; no user-facing content is finalized here.

## Threat Flags

None — this plan creates a single internal phase artifact. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Codex content pass | cb9268b | .planning/milestones/v1.4.0-phases/113-presentation-launch-readiness/113-CODEX-PASS.md |

## Self-Check: PASSED

- FOUND: `.planning/milestones/v1.4.0-phases/113-presentation-launch-readiness/113-CODEX-PASS.md`
- FOUND: commit cb9268b
