# Phase 113: Presentation & Launch Readiness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 113-presentation-launch-readiness
**Areas discussed:** README scope & shape, Fork-relationship note, Screenshot set, SECURITY.md threat-model, Community-health bar

---

## README scope & shape

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted rewrite | Keep working structure; sharpen one-liner, add fork note, security up as selling point, trim overstated claims | ✓ |
| Full above-the-fold rebuild | Restructure the top half: new hero, why-this-fork section, security/quality block | |
| Let codex teardown decide | Draft minimally; let the cynical-reader/codex pass dictate aggressiveness | |

**User's choice:** Targeted rewrite (Recommended)
**Notes:** Keeps wordmark, above-fold screenshot, Docker/pip, usage examples; adds sharper one-liner (Sonarr-driven + HMAC safe-delete), fork-relationship note, security-as-selling-point moved up; trims any overstated feature claim. → CONTEXT D-01, D-02.

---

## Fork-relationship note

> Initial question (name the upstream / sibling) was sent back for clarification. User instruction: *"not sure I want to invoke the other directly but just don't say it's the only one."* Reformulated around: credit origin, don't name nitrobass24, don't claim sole/only maintained fork.

| Option | Description | Selected |
|--------|-------------|----------|
| Credit origin + generic "one of several" | Credit ipsingh06/SeedSync, acknowledge "like other active forks" without naming them, then owned angle | ✓ |
| Credit origin only, no fork-count claim | Acknowledge SeedSync lineage, say nothing about other forks at all | |
| Fold into existing 'Related Projects' | Put origin credit in the Related Projects section, differentiator in the intro | |

**User's choice:** Credit origin + generic "one of several" (Recommended)
**Notes:** Honesty over bravado — name the origin (ipsingh06/SeedSync), do NOT name the nitrobass24 sibling, do NOT claim to be the only/active fork (hostile reader disproves instantly). Frame absence of outbound-push as scope choice, not advantage (comparison report §9 guardrails). → CONTEXT D-03, D-04.

---

## Screenshot set

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard + Settings + Logs | Three real screenshots covering the golden paths | ✓ |
| Dashboard + Settings | Two: hero + config flow, no logs | |
| Dashboard only (dark + light) | One view, two themes, showcases dark-mode | |

**User's choice:** Dashboard + Settings + Logs (Recommended)
**Notes:** Captured via Playwright at walkthrough vs the real NAS build; no mock fixtures. → CONTEXT D-05, D-06.

### Screenshot staging (follow-up)

> Follow-up question on staging-vs-as-is fallback was sent back for clarification. User instruction: *"i meant at walkthrough if the screenshots look bad we will try something else."*

**User's choice:** Capture-time judgment — no pre-locked staging policy. Shoot the real NAS state; if a screenshot looks bad, iterate on the spot (start a real transfer, reframe, retake). D-8 permits a representative real state; flag only if genuinely needed. → CONTEXT D-07.

---

## SECURITY.md threat-model

| Option | Description | Selected |
|--------|-------------|----------|
| Concise posture section | Short 'Security posture' block: what's protected + what opt-in knobs are for | ✓ |
| Minimal note | One paragraph naming headline protections, pointer to docs | |
| Fuller threat model | Structured: assets, trust boundaries, mitigations table, explicit non-goals | |

**User's choice:** Concise posture section (Recommended)
**Notes:** Protected-by-default (Fernet at rest, HMAC webhooks, SSRF guards, CSP, rate limits) + opt-in knobs (api_token, webhook_require_secret); "not a substitute for network isolation." Reads as maturity, doubles as selling point, no over-promising. → CONTEXT D-08.

---

## Community-health bar

| Option | Description | Selected |
|--------|-------------|----------|
| Rename + add CoC + freshen | LICENSE rename + badge fix, add Contributor Covenant CoC, lightly freshen CONTRIBUTING | ✓ |
| Minimum viable (rename only) | Just LICENSE rename + badge fix | |
| Full community-health set | Rename + CoC + expanded CONTRIBUTING + SUPPORT.md + funding/discussions | |

**User's choice:** Rename + add CoC + freshen (Recommended)
**Notes:** LICENSE.txt → LICENSE (+ README:118 badge link) from HR-05; add CODE_OF_CONDUCT.md (Contributor Covenant); freshen CONTRIBUTING.md (dev setup, run tests/ruff/karma, PR flow); keep issue + PR templates as-is. → CONTEXT D-09.

---

## Claude's Discretion

- Exact wording of rewritten README sections (within D-01..D-04 constraints).
- Contributor Covenant version + exact CONTRIBUTING.md structure (within D-09).
- Artifact filenames/locations for the cynical-reader teardown and codex-pass capture.
- Topic/tag selection for the repo-metadata draft.
- Whether security-posture content is briefly mirrored in the README block vs. detail-only in SECURITY.md (avoid verbatim duplication).

## Deferred Ideas

- Fuller structured threat-model for SECURITY.md — deferred in favor of concise posture (D-08).
- Expanded community-health set (SUPPORT.md, funding, discussions, arch-deep CONTRIBUTING) — beyond the D-09 bar.
- External's user-facing gaps (multi-instance *arr routing, notification presets, staging + post-download validation) — future feature-milestone candidates only; outbound push not worth building for a Sonarr-driven user.

### Reviewed Todos (not folded)
- `2026-04-24-migrate-config-set-to-post-body.md` — already shipped as Phase 111; not a presentation item.
- `2026-04-21-webob-cgi-upstream-unblock.md` — DEFER-WEBOB, blocked on upstream; not presentation scope.
