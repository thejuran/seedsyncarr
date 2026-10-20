# Requirements: SeedSyncarr — v1.7.7 Sonarr 5 Compatibility

**Defined:** 2026-10-20
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

Live checks run only on the NAS sandbox: `seedsyncarr-test` (1.7.6) against the `sonarr-v5` container (Sonarr 5.x `develop`, 5.0.0.2701 at milestone start, port 8990; the tested build is recorded per capture). Production Sonarr and SeedSyncarr are not touched.

## v1 Requirements

### Sonarr 5 compatibility

- [ ] **SON5-01**: User can press Test Connection for a Sonarr 5 instance and see success with its 5.x version reported.
- [ ] **SON5-02**: A held file stays "Waiting" while its tracked download is incomplete in Sonarr 5's queue and is released only once that same download shows complete. Both the incomplete and completed queue states for one tracked download are captured live. A missing queue entry, a Sonarr API error, or an unrelated completed download never releases the hold.
- [ ] **SON5-03**: Sonarr 5's webhook Test event is accepted and marks nothing imported; a real Sonarr 5 import is accepted and marks exactly the correct file imported.
- [ ] **SON5-04**: Sanitized fixtures captured from Sonarr 5 (system status, queue details incomplete/complete, Test and Download webhooks) are committed with the Sonarr version and capture scenario recorded alongside each, and CI exercises SeedSyncarr's handling of them without needing the NAS.
- [ ] **SON5-05**: If any SON5-01..03 check fails, the smallest compatibility fix ships as 1.7.7 and is deployed to the NAS by release tag; if all pass, no release is cut and the milestone closes as "verified; no release needed" with tests and evidence committed.

## Future Requirements

- Move the Sonarr integration to API v5 (v3 is deprecated in Sonarr 5, not removed) — backlog 999.5.

## Out of Scope

| Feature | Reason |
|---------|--------|
| API v5 migration | v3 still works on Sonarr 5; tracked as backlog 999.5 |
| Upgrading production Sonarr to v5 | Owner decision: sandbox only; Sonarr 5 is beta with no downgrade path |
| Radarr changes | No Radarr v5 in scope; Radarr integration unchanged |
| Webhook signing changes | Inbound webhook shape unchanged in Sonarr 5; existing HMAC behavior retained |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SON5-01 | Phase 120 | Pending |
| SON5-02 | Phase 120 | Pending |
| SON5-03 | Phase 120 | Pending |
| SON5-04 | Phase 120 | Pending |
| SON5-05 | Phase 120 | Pending |

**Coverage:**
- v1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-20*
*Last updated: 2026-10-20 after initial definition*
