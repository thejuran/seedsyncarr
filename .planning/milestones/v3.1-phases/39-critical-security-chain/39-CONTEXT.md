# Phase 39: Critical Security Chain - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate three attack vectors: RSA private key exposure in the repository, SSH MITM via disabled host key verification, and pickle deserialization RCE in the remote scanner. No new features — strictly closing existing security holes.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User indicated no gray areas need discussion — requirements and success criteria are sufficiently prescriptive. Claude has full discretion on all implementation details:

- RSA key removal approach and .gitignore patterns
- SSH StrictHostKeyChecking mode and known_hosts handling
- Pickle-to-JSON migration strategy and JSON schema for scan results
- Error handling and user-facing messages for SSH verification failures
- Upgrade path and backwards compatibility considerations

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Implementation should follow security best practices and the patterns established in CLAUDE.md.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-critical-security-chain*
*Context gathered: 2026-02-23*
