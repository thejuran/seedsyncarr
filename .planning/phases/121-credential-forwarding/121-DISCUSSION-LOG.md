# Phase 121: Credential Forwarding - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-21
**Phase:** 121-credential-forwarding
**Areas discussed:** Which requests get the token, Update check hardening, Existing users' exposed token, How we prove it

Pre-discussion research (research_before_questions on): common Angular practice is to gate Authorization on the parsed request origin; `startsWith` checks are bypassable (`//host`, look-alike hosts). Sources: timdeschryver.dev "Watch out what you expose with Angular Interceptors", ngtips.com/http/access-control.

---

## Which requests get the token

| Option | Description | Selected |
|--------|-------------|----------|
| Own server + /server/ only | Narrowest; matches the roadmap's "/server/* endpoint" wording | ✓ |
| Own server, any path | Simpler; same-origin non-API paths also get the token | |
| Explicit allowlist | Configurable host list; borders on auth redesign | |

**User's choice:** Own server + /server/ only
**Notes:** Claude decided, without asking: URL parsing, fail closed when an address can't be parsed, and "own origin" means `location.origin`.

---

## Update check hardening

| Option | Description | Selected |
|--------|-------------|----------|
| Rule fix only | One mechanism; regression test pinned to the GitHub URL | ✓ |
| Rule fix + separate path | Update check bypasses interceptors as a second guard | |

| Option | Description | Selected |
|--------|-------------|----------|
| Leave credentials/cookies as is | No cookie auth; cookies aren't sent cross-origin | ✓ |
| Explicitly strip | Guards against a risk that doesn't exist today | |

---

## Existing users' exposed token

| Option | Description | Selected |
|--------|-------------|----------|
| Disclose + recommend rotating | Full facts, rotation recommended | |
| Disclose, rotation optional | Full facts; rotation optional, mainly for instances reachable beyond the LAN | ✓ |
| Mention fix only | One line, no exposure details | |

| Option | Description | Selected |
|--------|-------------|----------|
| Rotate NAS token at 1.8.0 deploy | Deploy first, then rotate, then confirm UI, auth calls and a scan | ✓ |
| No | Keep current token | |

---

## How we prove it

| Option | Description | Selected |
|--------|-------------|----------|
| Unit tests + one E2E with a token | Full unit case table, plus a token-configured Playwright run with the GitHub request intercepted | ✓ |
| Unit tests only | Meets the roadmap wording; no real-browser token proof | |
| Unit + manual NAS check | Manual network-tab check in the sandbox; not repeatable | |

---

## Claude's Discretion

- URL parsing over prefix checks; fail closed; `location.origin` as the own origin
- How the E2E token run is wired (separate project, config variant or Docker config)
- Helper structure inside `auth.interceptor.ts`

## Deferred Ideas

- Token rotation UI (regenerate from Settings): new capability, not scheduled
- Release-note text and NAS token rotation are executed in Phase 126
