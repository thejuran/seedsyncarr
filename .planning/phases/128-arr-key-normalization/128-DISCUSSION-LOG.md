# Phase 128: Arr Key Normalization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-18
**Phase:** 128-arr-key-normalization
**Areas discussed:** Bad keys on save, Bad key at queue check, Key in save response

---

## Bad keys on save

| Question | Options | Selected |
|----------|---------|----------|
| Key still invalid after trimming | Refuse with error (Recommended) / Store trimmed, flag later | Refuse with error |
| Whitespace-only key | Refuse like empty (Recommended) / Clear the key | Refuse like empty |

## Bad key at queue check

| Question | Options | Selected |
|----------|---------|----------|
| Empty/invalid stored key at queue check | Skip + log reason (Recommended) / Send anyway | Skip + log reason |
| Warning frequency | Once per key value (Recommended) / Every check | Once per key value |

## Key in save response

| Question | Options | Selected |
|----------|---------|----------|
| Stop echoing secret values in save confirmation | Fix for all secrets (Recommended) / Arr keys only / Defer to backlog | Fix for all secrets |

**Notes:** Slight scope widening beyond Arr keys, approved by owner; recorded in ROADMAP Phase 128.

## Claude's Discretion

- Normalization location (config layer vs call sites), helper naming, wording, test structure.

## Deferred Ideas

None.
