# Requirements: SeedSyncarr — v1.4.1 Scanner Auto-Recovery

**Defined:** 2026-06-21
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1 Requirements

Requirements for milestone v1.4.1. Each maps to a roadmap phase.

### Scanner Resilience

- [ ] **SCAN-01**: A transient remote name-resolution failure during a scan (SSH errors matching `Could not resolve hostname` / `Name or service not known`, and a momentary `Bad hostname`) is classified as **recoverable** so the scanner retries the scan instead of terminating. The list keeps updating once the blip clears.
- [ ] **SCAN-02**: Recoverable scan failures are retried with **bounded backoff** — a capped number of attempts, not an infinite loop.
- [ ] **SCAN-03**: When retries are exhausted (a genuinely wrong / persistently-unresolvable hostname or bad credentials), the error is **surfaced to the user exactly as today** (controller reports the failure / `server.up=False` with the error message) so real configuration problems still stop and prompt — the retry path must never silently mask a permanent config error.

### Controller Recovery

- [ ] **RECOV-01**: If the controller dies from a permanent-class error, it **auto-restarts** via the existing `ServiceRestart` recovery path instead of remaining down (`server.up=False`) indefinitely. Recovery is itself bounded so a genuinely unrecoverable condition does not become a restart loop.

## Future Requirements

(none for this milestone)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New scanner/SSH transport rewrite | Reuse existing `sshcp.py` / `remote_scanner.py` infrastructure; this is a classification + recovery wiring fix, not a transport change |
| Configurable retry counts / backoff in the UI | Sensible hardcoded defaults are sufficient for a single-user self-hosted tool; expose later only if needed |
| Health/alerting/notification on scanner death | Separate concern; this milestone restores automatic recovery, not external alerting |
| Live NAS deploy verification as a gate | NAS local-build is QEMU-blocked; CI multi-arch publish works, deploy verification deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCAN-01 | Phase 114 | Pending |
| SCAN-02 | Phase 114 | Pending |
| SCAN-03 | Phase 114 | Pending |
| RECOV-01 | Phase 114 | Pending |

**Coverage:**
- v1 requirements: 4 total
- Mapped to phases: 4
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-21*
*Last updated: 2026-06-21 after defining milestone v1.4.1 requirements*
