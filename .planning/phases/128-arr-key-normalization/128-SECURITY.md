---
phase: 128
slug: arr-key-normalization
status: verified
threats_open: 0
asvs_level: 1
created: 2026-11-19
---

# Phase 128 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser / API client -> POST /server/config/set | Untrusted section, key and value; the value may be a secret | Sonarr/Radarr API keys and other secrets (sensitive) |
| server -> HTTP response body -> browser console | The settings page logs the save response text | Save confirmation and refusal text (must contain no secrets) |
| server -> application log | Warning on refused secret saves, skip log on bad keys | Section/key names, exception class (non-sensitive) |
| in-memory config -> ArrQueueClient -> Sonarr/Radarr HTTP | The stored key becomes the outbound X-Api-Key header | API key (sensitive) |
| ArrQueueClient -> CompletionGate | The fetch outcome decides release or hold of a completion | Queue evidence (affects import/deletion safety) |
| test process -> log capture | Parity test proves no key material is written | Fake probe keys only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-128-01 | Tampering | is_valid_arr_api_key | mitigate | `common/arr_api_key.py:10,24` allowlist `[\x21-\x7e]+` with fullmatch; CR/LF/NUL rows pinned in test_arr_api_key.py:22-24 | closed |
| T-128-02 | Information disclosure | normalize/is_valid helpers | mitigate | `common/arr_api_key.py:13-24` pure, no logger, no raise; non-str guarded | closed |
| T-128-03 | Denial of service | is_valid_arr_api_key regex | accept | One character class, single quantifier, no nesting — linear time | closed |
| T-128-04 | Information disclosure | config set success body | mitigate | `web/handler/config.py:364-365,377-378` "<section>.<key> updated" for all secret_fields(); sweep test_config.py:286; confirmed live on sandbox (UAT test 2) | closed |
| T-128-05 | Information disclosure | config set refusal body | mitigate | `web/handler/config.py:353,356,359,374` fixed strings only; pinned test_config_handler.py:267 | closed |
| T-128-06 | Information disclosure | refused-secret warning log | mitigate | `web/handler/config.py:370-372` logs section, key, type(e).__name__ only | closed |
| T-128-07 | Tampering | stored Arr key | mitigate | `web/handler/config.py:347-360` refusal returns before set_property (line 367); confirmed live (UAT test 3) | closed |
| T-128-08 | Tampering | request value type | mitigate | Existing guards at `config.py:317,327,331`; since review fix WR-01 (31d013e0) non-text Arr keys are refused with 400 at line 352 (stricter than plan's "stringified then validated") | closed |
| T-128-09 | Elevation of privilege | config set endpoint auth | accept | Auth/rate limiting unchanged; add_routes (`config.py:155-169`) not in phase diff | closed |
| T-128-10 | Information disclosure | start_fetch skip log | mitigate | `controller/arr_queue.py:203,205` fixed format with target.label only; sweep test_arr_queue.py:742 | closed |
| T-128-11 | Information disclosure | requests InvalidHeader quoting | mitigate | Validation before thread (`arr_queue.py:199-206` vs 222) and before requests.get (`config.py:394-395` vs 415) | closed |
| T-128-12 | Tampering | header injection | mitigate | Only X-Api-Key sites (`arr_queue.py:291`, `config.py:417`) are behind is_valid_arr_api_key | closed |
| T-128-13 | EoP / data loss | unsafe import/deletion on bad key | mitigate | `arr_queue.py:206` returns None -> `completion_gate.py:219-221,323` HOLD("<code>_unavailable"); completion_gate.py unchanged; TestBadKeyFailsSafe | closed |
| T-128-14 | Denial of service | log flooding | mitigate | `arr_queue.py:201-205` WARNING once per key token per arr, DEBUG after; tests test_arr_queue.py:700,717,732 | closed |
| T-128-15 | Information disclosure | warn-once memory | mitigate | `arr_queue.py:165,200-202` stores opaque k<n> token only | closed |
| T-128-16 | Information disclosure | key hygiene regression | mitigate | test_arr_key_parity.py:250 root-logger + response-body probe sweep; live sandbox log grep found 0 key hits (UAT test 4) | closed |
| T-128-17 | Tampering | path drift | mitigate | Single RULE_CASES table drives parity test (test_arr_key_parity.py:23,170,213); ARR_API_KEY_CHARS defined once (`arr_api_key.py:10`) | closed |
| T-128-18 | Repudiation | unreported gate failure | mitigate | 128-04-SUMMARY.md:52-71 records local 86.47% as not passed; Linux coverage 92.63% recorded in 128-UAT.md test 1 | closed |
| T-128-19 | Information disclosure | secrets in test fixtures | accept | Test keys are obvious fakes (abcDEF123, goodKEY1, LEAKPROBE…, Probe-SECRET-128x) | closed |
| T-128-SC | Tampering | package installs | accept | pyproject.toml and poetry.lock unchanged since b79b06fb | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-128-01 | T-128-03 | Single-class regex has no backtracking risk | Plan 128-01 threat model; rationale re-verified by bm-security-auditor | 2026-11-19 |
| AR-128-02 | T-128-09 | Endpoint auth and rate limiting are out of this phase's scope and unchanged | Plan 128-02 threat model; re-verified | 2026-11-19 |
| AR-128-03 | T-128-19 | Only fake keys appear in tests | Plan 128-04 threat model; re-verified | 2026-11-19 |
| AR-128-04 | T-128-SC | No new or changed dependencies | Plans 128-01..04 threat models; re-verified | 2026-11-19 |

*Accepted risks do not resurface in future audit runs.*

**Observation (not a gap):** the module-level `_KEY_TOKENS` map (`arr_queue.py:46`) holds raw keys as dictionary keys in memory to issue opaque tokens. It already held valid keys before this phase, and now invalid keys reach it too. It is never logged or serialized.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-19 | 20 | 20 | 0 | bm-security-auditor (fable); 6 phase test files 300 passed / 158 subtests |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-19
