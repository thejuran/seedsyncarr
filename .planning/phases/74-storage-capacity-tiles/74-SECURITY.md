---
phase: 74
slug: storage-capacity-tiles
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-20
---

# Phase 74 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| local host → remote seedbox (SSH) | `df -B1 <remote_path>` is shell-executed over an authenticated SSH session; `remote_path` comes from `config.lftp.remote_path` (user-controlled). | Shell-argument string (must be quoted) |
| remote shell output → df parser | `df` stdout is filesystem metadata treated as untrusted input. | Bytes → parsed `(total, used)` ints or `(None, None)` |
| local mount point → `shutil.disk_usage` | Watched local path may be unmounted or inaccessible. | Filesystem call → `(total, used)` ints or `(None, None)` on `OSError`/`ValueError` |
| scanner → controller → Status → SSE | Capacity values flow through `StorageStatus` component into the authenticated `/status` SSE broadcast. | `Optional[int]` per field, emitted as JSON `number \| null` |
| backend SSE → `ServerStatus.fromJson` | Frontend parses the JSON `storage` block; backend may be deploy-skewed and omit the key. | Optional `storage` object → `number \| null` fields |
| `DashboardStats` → template | Numeric capacity fields flow into template expressions; divisions by `capacityTotal` must tolerate `0` and `null`. | Typed `number \| null` into `\| number`, `\| fileSize`, `[style.width.%]` bindings |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-74-01 | Information Disclosure | `SerializeStatusJson.status()` storage block | accept | Same exposure class as existing tracked-bytes; `/status` SSE auth gate (Phase 50) is the sole control. | closed |
| T-74-02 | Tampering | `Status.StorageStatus` properties | accept | Process-internal writer; controller is sole mutator; `Cannot reassign component` guard tested in Plan 01 tests. | closed |
| T-74-03 | Denial of Service | None defaults crashing client | mitigate | All 4 fields default to `None` (`status.py:134-138`); serializer emits `int \| null` without str-wrap (`serialize_status.py:46-52`); frontend guards null via 3-part `@if` in `stats-strip.component.html:10,51`. | closed |
| T-74-04 | Injection | JSON key collision | accept | Fixed string-constant keys in serializer; numeric values only; no user-controlled string reaches the payload. | closed |
| T-74-05 | **Injection (command injection)** | `RemoteScanner.scan()` df call | mitigate | `remote_scanner.py:130` — `"df -B1 {}".format(shlex.quote(self.__remote_path_to_scan))`. `shlex.quote` appears at line 91 (original scan) and line 130 (new df call) — both user-path invocations are quoted. Regression test asserts hostile `;` paths produce the quoted-single-quotes form, not an injection vector. | closed |
| T-74-06 | Tampering / DoS | malformed df output → `_parse_df_output` | mitigate | `remote_scanner.py:31-51` — static parser returns `(None, None)` on `UnicodeDecodeError`, `<2` non-empty lines, `<3` parts, and int-conversion failures. Never raises. 7 parser unit tests cover documented failure modes. | closed |
| T-74-07 | Information Disclosure | capacity values in SSE payload | accept | Same class as T-74-01. | closed |
| T-74-08 | Denial of Service | SSE flood from noisy capacity updates | mitigate | `controller.py:621-632` — `_should_update_capacity` uses strict `> 0.01` gate; `None → value` always passes (cold-load recovery); `0 → 0` blocked. Applied per-side at lines 644-665. | closed |
| T-74-09 | Denial of Service | unmounted local path → `shutil.disk_usage` | mitigate | `local_scanner.py:34-39` — `shutil.disk_usage(self.__local_path)` wrapped in `except (OSError, ValueError)` with WARN log; returns `(None, None)`; scan proceeds. | closed |
| T-74-10 | Tampering | malformed/deploy-skewed backend JSON | mitigate | `server-status.ts:97-100` — `json.storage?.local_total ?? null` (all 4 fields); `ServerStatusJson.storage` typed optional at line 123. Missing-key and null survive without throwing. | closed |
| T-74-11 | Information Disclosure | `DashboardStats` broadcast | accept | Intentional feature goal — capacity intentionally visible to all dashboard-authenticated clients. | closed |
| T-74-12 | XSS | template interpolation of capacity | accept | All 4 fields typed `number \| null`; template uses `\| number`, `\| fileSize` pipes and `[style.width.%]` numeric bindings; no `innerHTML`, no attribute-level string injection. Angular default escaping applies. | closed |
| T-74-13 | Denial of Service | `combineLatest` memory leak | mitigate | `dashboard-stats.service.ts:63` — `.pipe(takeUntil(this.destroy$))`; `ngOnDestroy` at lines 105-108 calls `destroy$.next()` + `destroy$.complete()`. | closed |
| T-74-14 | Denial of Service | divide-by-zero in template expression | mitigate | `stats-strip.component.html:10` Remote tile and `:51` Local tile both apply the 3-part guard `total !== null && used !== null && total > 0` before evaluating `used / total * 100`. | closed |
| T-74-15 | XSS | capacity values in DOM | accept | Same as T-74-12 (numeric-only binding path). | closed |
| T-74-16 | Information Disclosure | rendered capacity via DOM inspection | accept | Same disclosure class; upstream auth gate. | closed |
| T-74-17 | Content injection | `var(--bs-warning, #ffc107)` fallback | accept | Hard-coded fallback hex strings in SCSS; CSS custom-property names controlled by Bootstrap 5.3 import chain; no user input in the pipeline. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## ASVS L1 Coverage

| Control | Requirement | Status |
|---------|-------------|--------|
| V5.1.3 | Input validation at trust boundary (df output parser) | CLOSED — T-74-06 |
| V5.2.2 | Sanitize shell invocation arguments | CLOSED — T-74-05 (`shlex.quote` on both SSH shell calls) |
| V5.3.1 | Output encoding (no raw DOM injection) | CLOSED — T-74-12, T-74-15 (numeric typed bindings only) |
| V11.1.1 | Business-logic limits (SSE flood gate) | CLOSED — T-74-08 (>1% delta) |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-74-01 | T-74-01, T-74-07, T-74-11, T-74-16 | Capacity totals/used bytes visible to authenticated dashboard viewers. Same exposure class as existing tracked-bytes and scan-time fields. Self-hosted single-user context; `/status` SSE auth gate (Phase 50) is the sole control. | phase-74 threat model | 2026-04-20 |
| AR-74-02 | T-74-02 | `Status` model is process-internal; only the controller process mutates it; reassign guard is unit-tested. No cross-process attack surface. | phase-74 threat model | 2026-04-20 |
| AR-74-03 | T-74-04 | JSON keys are fixed string constants; values are numeric or `null`; no user-controlled string reaches the serialized payload. | phase-74 threat model | 2026-04-20 |
| AR-74-04 | T-74-12, T-74-15 | Capacity fields are `number \| null`; template uses pipes and numeric bindings only; Angular's default escaping applies. | phase-74 threat model | 2026-04-20 |
| AR-74-05 | T-74-17 | CSS custom property fallbacks are hard-coded hex strings; `--bs-warning` / `--bs-danger` are Bootstrap 5.3 conventions owned by the project's SCSS import chain. No user input can inject into this pipeline. | phase-74 threat model | 2026-04-20 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-20 | 17 | 17 | 0 | gsd-security-auditor (sonnet) |

### 2026-04-20 Notes

**Implementation deviation (documented, not a gap):** For T-74-08, the plan specified "paired-measurement atomic writes" (both `total` and `used` written together when either exceeds the gate). The implementation at `controller.py:651-665` applies independent per-field gates instead — this is strictly more conservative (sub-1% changes on one field do not force a write of the other) and does not weaken SSE-flood prevention. The divide-by-zero guard in the template (T-74-14) compensates for any transient consistency skew between `total` and `used`.

**Highest-risk mitigation (T-74-05) verified with dual-occurrence check:** `shlex.quote(self.__remote_path_to_scan)` is applied to both the pre-existing main-scan SSH call (`remote_scanner.py:91`) and the new df call (`remote_scanner.py:130`). Regression test in `test_remote_scanner.py` passes hostile `;`-bearing paths and asserts the quoted-single-quotes form.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-20
