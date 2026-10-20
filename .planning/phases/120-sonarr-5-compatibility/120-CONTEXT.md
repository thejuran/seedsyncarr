# Phase 120: Sonarr 5 Compatibility - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning
**Source:** Owner answers to the open questions in 120-RESEARCH.md (no discuss-phase run)

<domain>
## Phase Boundary

Show that SeedSyncarr 1.7.6 works with Sonarr 5 on the NAS sandbox (`seedsyncarr-test` against `sonarr-v5`): connection test, download-queue completion evidence, and the import webhook. Lock that behavior in with CI tests built from sanitized, real Sonarr 5 captures. Cut 1.7.7 only if a Sonarr-5-caused failure needs a fix. Production Sonarr, production SeedSyncarr and production Deluge are never touched. No API v5 migration (backlog 999.5). No Radarr changes.

</domain>

<decisions>
## Implementation Decisions

### Test Connection (SON5-01)
- **D-01:** SON5-01 is satisfied when SeedSyncarr's Test Connection succeeds against the sandbox Sonarr 5 instance and displays a 5.x version, using the NAS Tailscale address as the Sonarr URL.
- **D-02:** Evidence records the successful version, the connection method (Tailscale address, written as `<nas-tailscale-ip>` in committed files), and the container-name (`http://sonarr-v5:8989`) failure as the known LAN/private-address issue deferred to the Reliability milestone. That failure is NOT a Sonarr 5 failure and does NOT trigger a release under SON5-05. No LAN-check fix in this phase.
- **D-03:** The sandbox Sonarr URL is restored to its original value right after the Test Connection check, and the check is not run during the SON5-02 capture.

### Temporary Deluge change for the in-progress capture (SON5-02)
- **D-04:** The agent makes the temporary sandbox change itself; no manual owner checkpoint for this step.
- **D-05:** Prefer a per-download folder override (e.g. set the download location on the single capture torrent only) if Deluge supports it. Only if not: record the original sandbox setting before changing it, and make sure no other sandbox downloads are affected.
- **D-06:** Restore the original configuration and verify it was restored, even if the test fails or is stopped (teardown on every exit path). Production Deluge stays untouched.

### Sonarr 5 version drift
- **D-07:** Do not pin `sonarr-v5`. Record the actual build. Check `system/status.version` before and after each test scenario (L1, L2, L3); if it changes mid-scenario, rerun that scenario.
- **D-08:** Label every fixture and evidence record with the exact Sonarr build tested. Fixture manifest and hygiene checks accept any recorded 5.x build rather than hardcoding `5.0.0.2701`; the requirement wording is "the tested Sonarr 5.x build".
- **D-09:** The final conclusion names the specific builds verified and must not imply compatibility with every future Sonarr 5 build.

### Release decision (SON5-05)
- **D-10:** Whether a release is needed stays undecided until SON5-01 through SON5-04 are verified. The planned outcome is a decision step, not a presumed result.
- **D-11:** If a Sonarr-5 compatibility fix is needed: release 1.7.7, deploy `:1.7.7` (by release tag, never `:dev`) to `seedsyncarr-test` only, and verify it there. Production stays on 1.7.6; any production rollout needs separate owner authorization and is out of this phase.
- **D-12:** If no fix is needed: record the compatibility pass with no release; the milestone closes as "verified; no release needed" with tests and evidence committed.

### Claude's Discretion
- **D-13:** Raw (unsanitized) captures on the NAS live in a `umask 077` directory and are deleted at teardown once sanitized fixtures are committed and the exact-secret count check returns 0. They are never committed.
- **D-14:** Episode/indexer for the real grab: the agent chooses a small, quick episode from a public indexer if one is configured on the sandbox. If only private-tracker indexers are available, stop and ask the owner before grabbing (ratio/consent is the owner's call).
- Fixture layout, test module structure, sanitizer mechanics and the CI hygiene guard follow 120-RESEARCH.md.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/120-sonarr-5-compatibility/120-RESEARCH.md` — verified Sonarr 5 field facts, live capture procedure (L0–L4), sanitization approach, pitfalls, release path, validation architecture
- `.planning/REQUIREMENTS.md` — SON5-01..05
- `.planning/ROADMAP.md` — Phase 120 section, scope boundary, backlog 999.5
- Prior release runbook records for 1.7.6 (Phase 119.1) referenced from 120-RESEARCH.md "Release Path"

</canonical_refs>

<specifics>
## Specific Ideas

- Webhook capture via a disposable sink container plus a second sonarr-v5 webhook connection, both removed at teardown; never point any connection at production `seedsyncarr`.
- CI fixtures live under `src/python/tests/fixtures/sonarr5/` with a `manifest.json` recording Sonarr build and capture scenario per file.

</specifics>

<deferred>
## Deferred Ideas

- LAN/private-address support for Test Connection — Reliability milestone item 5.
- API v5 migration — backlog 999.5.
- Production rollout of any 1.7.7 — needs separate authorization.

</deferred>

---

*Phase: 120-sonarr-5-compatibility*
*Context gathered: 2026-10-20 from owner decisions on research open questions*
