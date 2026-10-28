# Phase 126: Release 1.8.0 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-10-28
**Phase:** 126-release-1-8-0
**Areas discussed:** Dependency roll-ins, Release notes framing, Sandbox smoke scope, Prod deploy & rollback

Pre-discussion Dependabot snapshot shown to the owner: 9 open alerts, all dev-scope npm (vite ×5, follow-redirects ×2, MCP SDK ×2), and 8 open PRs: #136 certifi (runtime), #135, #138, #130, #131 (23-package bundle incl. Angular framework patch bumps that ship in the UI + @types/jasmine major), #141, #125, #117. PR #128 (999.4) is closed.

---

## Dependency roll-ins

| Option | Description | Selected |
|--------|-------------|----------|
| 3 alert PRs | #135, #138, #130; clears all 9 alerts; others wait | |
| Alert PRs + #131 bundle | Adds Angular framework patches + 23-package bundle | |
| Everything open | Also #131, #141, #125, #117; empties the queue | ✓ |
| certifi only | Leave dev alerts open | |

**If a dev update breaks the build/tests:** Drop it and note it / Fix it in-phase / **Ask me ✓**

---

## Release notes framing

| Question | Options | Selected |
|----------|---------|----------|
| Coverage of 121–124 | Security + short Fixed / Security + Test Connection only / Full detail | Security + short Fixed |
| Token-to-GitHub note | Suggest rotating / State it, no advice / Don't mention | Suggest rotating |
| Lead item | Security first / Behaviour change first | Security first |

---

## Sandbox smoke scope

| Question | Options | Selected |
|----------|---------|----------|
| Where | seedsyncarr-test sandbox / Fresh scratch setup | seedsyncarr-test sandbox |
| Sonarr | v4 matching prod (+ v5 Test Connection) / v5 only / Both full | v4 matching prod |
| Extras | Add 1.8.0 spot checks / Standard only | Add 1.8.0 spot checks |

---

## Prod deploy & rollback

| Question | Options | Selected |
|----------|---------|----------|
| Approvals | Before tag + before prod / Before prod only / Before tag only | Before tag + before prod |
| On failure | Roll back if broken, else ask / Always ask / Always roll back | Roll back if broken, else ask |
| Done when | Successful scan + arr check / Also wait for a real import | Successful scan + arr check |

---

## Claude's Discretion

- Mechanics of landing the Dependabot changes on the release branch
- Smoke scripting and evidence layout
- Exact release-note wording within the decided structure
- Plan/wave grouping

## Deferred Ideas

None.
