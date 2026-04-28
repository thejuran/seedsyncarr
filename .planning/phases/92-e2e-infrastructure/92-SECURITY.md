---
phase: 92
slug: e2e-infrastructure
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-27
---

# Phase 92 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| compose.yml healthcheck | curl runs inside myapp container against localhost:8800 | HTTP status response (operational state only) |
| run_tests.sh variable init | Shell variable initialization within test script | None — no external input |
| stdin to parse_status.py | curl stdout piped to Python within Docker test network | JSON status response from /server/status |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-92-01 | I (Information Disclosure) | compose.yml healthcheck curl | accept | Healthcheck runs inside container against localhost:8800. /server/status is read-only, returns operational state only, no secrets. | closed |
| T-92-02 | D (Denial of Service) | healthcheck retries | accept | 12 retries with 5s interval = 60s max wait. Test infrastructure only, not production. Generous timeouts prevent false negatives on arm64/QEMU. | closed |
| T-92-03 | T (Tampering) | parse_status.py stdin | accept | Input from curl piping /server/status within Docker test network. Not user-controlled. json.load handles untrusted JSON safely (no code execution). | closed |
| T-92-04 | I (Information Disclosure) | parse_status.py error handling | mitigate | Specific exceptions (json.JSONDecodeError, KeyError, TypeError, OSError) replace bare except:. Prevents masking SystemExit/KeyboardInterrupt. Output always "True" or "False" — no sensitive data on error path. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-92-01 | T-92-01 | Healthcheck curl confined to container localhost; /server/status exposes no secrets | gsd-security-audit | 2026-04-27 |
| AR-92-02 | T-92-02 | Test-only infrastructure; generous retries prevent CI flake on slow emulators | gsd-security-audit | 2026-04-27 |
| AR-92-03 | T-92-03 | stdin source is curl within controlled Docker network; json.load is safe against code execution | gsd-security-audit | 2026-04-27 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-27 | 4 | 4 | 0 | gsd-security-audit |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-27
