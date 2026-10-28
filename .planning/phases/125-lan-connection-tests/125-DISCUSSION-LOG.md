# Phase 125: LAN Connection Tests - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 125-CONTEXT.md. This log preserves the discussion.

**Date:** 2026-10-27
**Phase:** 125-lan-connection-tests
**Mode:** discuss (default)
**Areas discussed:** localhost / 127.0.0.1, What stays blocked, Error wording, Proof of done

## localhost / 127.0.0.1

| Option | Selected |
|--------|----------|
| Only on ports 8989/7878 (Recommended) | ✓ |
| Keep blocking loopback | |
| Any port | |

## What stays blocked

| Option | Selected |
|--------|----------|
| Yes, this list: link-local/metadata, unspecified/reserved, multicast refused; private LAN, IPv6 ULA, Tailscale 100.64/10, public allowed (Recommended) | ✓ |
| Also block Tailscale range | |

## Error wording

| Option | Selected |
|--------|----------|
| Name the reason (Recommended) | ✓ |
| One generic message | |

## Proof of done

| Option | Selected |
|--------|----------|
| Tests + live sandbox check on seedsyncarr-test with http://sonarr-v5:8989, restore pin + fresh-session check (Recommended) | ✓ |
| Automated tests only | |

## Claude's Discretion
- Mixed-resolution rule (refuse if any address is refused), IPv6 equivalents, IPv4-mapped bypass handling, failure response shape unchanged, helper structure, exact message strings, test placement, sandbox scripting, CHANGELOG entry for the release notes.

## Deferred Ideas
- DNS-rebinding hardening (still out of scope)
- Configurable extra loopback ports (not requested)
