# Phase 111: Config-Set Endpoint Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 111-config-set-endpoint-migration
**Mode:** discuss (standard)
**Areas presented:** Empty-value status code, Drop double-encoding, Malformed-body handling, Endpoint path shape

---

## Interaction summary

The user **dismissed** the gray-area `AskUserQuestion` (no selection), repeating the Phase 110
signal: comfort with spec-grounded defaults rather than re-deciding mechanics already constrained
by the requirements (CFG-01..04) and design-spec decision D-4. Per the workflow's answer-validation
rule, a dismissed (not empty-"Other") response means proceed with locked defaults grounded in the
spec and the code surfaces examined during scouting. No areas were interactively deep-dived; the
four presented areas were resolved to defaults and recorded as locked decisions D-01..D-13 in
CONTEXT.md.

The four areas were not arbitrary — each was a genuine implementation fork surfaced by reading the
actual code (`config.py`, `config.service.ts`, `setup_seedsyncarr.sh`, `rest.service.ts`, and the
integration/unit/e2e tests), not generic categories.

---

## Empty-value status code

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve 404 for empty | Match the old route-miss behavior (regex `.+` rejected empty) | |
| Return 400 for empty | Treat empty value as a body-validation error | ✓ (default) |

**Resolution (default):** 400. Under the GET route an empty value was a 404 only as a *route-miss
artifact* of the `<value:re:.+>` regex; with a JSON body the handler now receives the value, so an
empty/missing `value` is correctly a 400 body-validation failure. The one integration test asserting
404 for empty (`test_set_empty_value`) is updated 404→400 as a documented contract refinement.
Whitespace-only stays 400 (existing `ConfigError`). See D-06.

---

## Drop double-encoding

| Option | Description | Selected |
|--------|-------------|----------|
| Drop entirely | JSON body needs no URL-encoding; send/read raw value | ✓ (default) |
| Keep a value transform | Preserve some encode/decode step for parity | |

**Resolution (default):** Drop entirely. The double-encode dance (`encodeURIComponent×2` client-side,
`unquote` server-side) existed *only* to survive URL path segments. With a JSON body there is no URL
encoding at all — Angular sends the raw value, the backend reads it directly, both encode/decode
calls are deleted. See D-04.

---

## Malformed-body handling

| Option | Description | Selected |
|--------|-------------|----------|
| Generic 400, detail logged server-side | Invalid JSON / non-object / absent field → clean 400, no internals leaked | ✓ (default) |
| Specific per-case messages to client | More granular client-facing errors | |

**Resolution (default):** Generic 400 for invalid-JSON / non-object-body / absent required field,
with any internal detail logged server-side only (global code-quality rule: no internals to clients).
Present-but-unknown section/key keep their existing 404. See D-07.

---

## Endpoint path shape

| Option | Description | Selected |
|--------|-------------|----------|
| Bare `POST /server/config/set` (all in body) | Nothing in URL — not even section/key | ✓ (default) |
| `POST /server/config/set/<section>/<key>` (value in body) | Only value leaves the URL | |

**Resolution (default):** Bare `POST /server/config/set`, all of `{section, key, value}` in the body.
Maximizes CFG-01/CFG-02 — nothing credential-bearing (or otherwise) in the URL. Legacy GET route
deleted entirely. Dual-support rejected per D-4 / Out-of-Scope. See D-01, D-02.

---

## Claude's Discretion

- Name/signature of the new body-carrying Angular POST helper (extend `RestService.post` vs add `postJson`).
- Exact generic 400 message strings for malformed-body cases (must leak no internals).
- Whether the backend reads the body via `bottle.request.json` directly or via a small guarded helper.
- The webtest body-POST helper used in the integration suite (`post_json` vs `post(content_type=...)`).
- Message granularity distinguishing "not an object" from "missing field" (both 400).

## Deferred Ideas

- None new in scope. Dual-support GET+POST is **rejected** (not deferred) per D-4 / REQUIREMENTS.md
  Out of Scope — must not be built.
- Folded todo: `2026-04-24-migrate-config-set-to-post-body.md` — this todo *is* Phase 111; close on completion.
- Not folded: `2026-04-21-webob-cgi-upstream-unblock.md` (DEFER-WEBOB) — upstream-blocked, unrelated.
