---
phase: 73
slug: dashboard-filter-for-every-torrent-status
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-19
---

# Phase 73 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| URL → component state | `ngOnInit` reads `?segment=` and `?sub=` query params and feeds them into `activeSegment` / `activeSubStatus`. This is the single new attack surface in Phase 73. | Attacker-controlled string → typed `Segment` union / `ViewFile.Status \| null` |
| component state → URL | `Router.navigate` writes `queryParams` derived from internal, already-validated `activeSegment` / `activeSubStatus`. | Typed, bounded enum values → URL query string |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-73-01-01 | Tampering | `segmentedFiles$` filter logic (internal) | accept | URL boundary covered by T-73-03-01; internal consumer only. | closed |
| T-73-01-02 | Information Disclosure | filtered file list | accept | Pure client-side derivation over data already delivered by `ViewFileService.filteredFiles`. | closed |
| T-73-02-01 | XSS | sub-button labels in template | accept | Static string literals; no interpolation, no `[innerHTML]`. | closed |
| T-73-02-02 | Tampering | `(click)` handlers on new buttons | accept | Handler arguments are compile-time literals. No user input reaches handlers from template. | closed |
| T-73-03-01 | Tampering | URL `?segment` value | mitigate | `SEGMENTS` readonly array + `isSegment()` type guard (`transfer-table.component.ts:21-24`); `ngOnInit` uses `isSegment(segParam) ? segParam : "all"` (`transfer-table.component.ts:179`). Invalid silently coerces to `"all"` per D-11. | closed |
| T-73-03-02 | Tampering | URL `?sub` value | mitigate | `SEGMENT_STATUSES` per-segment readonly allow-list (`transfer-table.component.ts:28-43`); `ngOnInit` validates `allowed.includes(subParam as ViewFile.Status)` (`transfer-table.component.ts:184-188`). Mismatched or unknown subs silently coerce to `null`. | closed |
| T-73-03-03 | Open redirect / path manipulation | `Router.navigate` in `_writeFilterToUrl` | mitigate | `this.router.navigate([], { relativeTo: this.route, queryParamsHandling: "merge", replaceUrl: true })` (`transfer-table.component.ts:374-379`). Empty commands + `relativeTo` prevents cross-route navigation. | closed |
| T-73-03-04 | XSS (reflected) | template rendering of `activeSegment` / `activeSubStatus` | accept | Values consumed only in `[class.active]` and `(click)` bindings; never rendered via `{{ }}` or `[innerHTML]`. | closed |
| T-73-03-05 | Information Disclosure | URL leakage of filter state | accept | URL reveals filter only; no PII, no credentials. Self-hosted single-user app. | closed |
| T-73-03-06 | Denial of Service | repeated `Router.navigate` reflow | accept | Each filter click calls `navigate` exactly once; `replaceUrl: true` caps history growth; `_writeFilterToUrl` does not subscribe to `filterState$`, so no feedback loop. | closed |
| T-73-04-01 | (test-only) | jest mocks | accept | Mock objects used only in tests; never imported by production code. | closed |
| T-73-04-02 | Tampering | mock query-param state leak between tests | mitigate | `beforeEach` resets `mockRouter` and clears `mockQueryParamMap` (`transfer-table.component.spec.ts:144-146`); `createWithQuery` helper clears+reassigns the map before each `createComponent` (`transfer-table.component.spec.ts:958-962`). | closed |
| T-73-05-01 | (e2e-only) | Playwright locators | accept | Locators scoped to `.segment-filters` and `.btn-sub`; no production paths added. | closed |
| T-73-05-02 | Tampering | URL round-trip e2e test | accept | Regex-based URL containment assertion; no new attack surface. Validated surface mitigated by T-73-03-01 / T-73-03-02. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## ASVS L1 Coverage

| Control | Requirement | Status |
|---------|-------------|--------|
| V5.1.3 | Input validation at trust boundary | CLOSED — T-73-03-01 + T-73-03-02 |
| V5.3.1 | Output encoding (no raw DOM injection) | CLOSED — T-73-03-04 |
| V8.1.1 | Open redirect prevention | CLOSED — T-73-03-03 |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-73-01 | T-73-03-05 | URL reveals active filter only (e.g., `?segment=errors&sub=stopped`). No PII, no credentials, no file names. Acceptable for self-hosted single-user context. | phase-73 threat model | 2026-04-19 |
| AR-73-02 | T-73-01-02 | Client-side derivation over already-delivered data; no new disclosure surface. | phase-73 threat model | 2026-04-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-19 | 14 | 14 | 0 | gsd-security-auditor (sonnet) |

### 2026-04-19 Notes

Implementation diverges from Plan 03 draft in one tighter direction: the executor refactored `VALID_SEGMENTS` / `VALID_SUBS_PER_SEGMENT` (named in the plan) into a module-level `SEGMENTS` readonly array + standalone `isSegment()` type guard (`transfer-table.component.ts:21-24`), and reused the existing `SEGMENT_STATUSES` constant (`transfer-table.component.ts:28-43`) as the per-segment sub allow-list. Single source of truth; mitigations for T-73-03-01 and T-73-03-02 remain fully satisfied.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-19
