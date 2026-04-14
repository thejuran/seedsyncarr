---
phase: 66
slug: logs-page
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-14
---

# Phase 66 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User search input -> RegExp constructor | Untrusted user string used to construct regex | Plain text search query |
| LogService SSE stream -> Component display | Server-sent log data rendered in DOM | Log records (level, message, logger, traceback) |
| ConnectedService -> Status bar display | Server connection state rendered in UI | Boolean connection flag |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-66-01 | Denial of Service | RegExp constructor in recomputeFilteredLogs | mitigate | `try/catch` around `new RegExp()` (line 249-253). `hasNestedQuantifiers()` (line 262-264) rejects catastrophic backtracking patterns. `MAX_SEARCH_LENGTH=200` + `maxlength="200"` caps input length. | closed |
| T-66-02 | Information Disclosure | Export .log download | accept | Export contains only data already visible to the authenticated user. Newline sanitization (`s.replace(/[\r\n]/g, ' ')` line 156) prevents log injection in exported files. | closed |
| T-66-03 | Tampering | Log entries rendered in template | accept | Angular `{{ }}` interpolation auto-escapes HTML. No `[innerHTML]` usage. No XSS vector. | closed |
| T-66-04 | Spoofing | Status bar connection indicator | accept | ConnectedService reads from authenticated SSE stream (Phase 50 API token auth). Display-only indicator. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-66-01 | T-66-02 | Export only surfaces data already visible to the authenticated user in-browser. No privilege escalation. | gsd-secure-phase | 2026-04-14 |
| AR-66-02 | T-66-03 | Angular template binding auto-escapes by default. Log messages use interpolation, not innerHTML. | gsd-secure-phase | 2026-04-14 |
| AR-66-03 | T-66-04 | Connection state sourced from authenticated SSE stream. Spoofing requires compromising the SSE connection itself, already protected by API token auth. | gsd-secure-phase | 2026-04-14 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-14 | 4 | 4 | 0 | gsd-secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-14
