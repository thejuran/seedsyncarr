# Phase 130: Release 1.8.1 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-11-19
**Phase:** 130-release-1-8-1
**Areas discussed:** Dependency roll-ins, Smoke test scope, Release notes, PR #156 and sequencing
**Carried forward without discussion:** Phase 126 D-13–D-17 (route, two checkpoints, prod pin by digest, wud, rollback, done criteria)

## Dependency roll-ins
| Question | Options | Selected |
|---|---|---|
| Soupsieve (4 alerts, dev-only usage, #151 major jump) | Roll in fix / Leave + document | Roll in fix (Recommended) |
| Shipped bumps #146 paste, #145 pytz | Only if they fix something / Include both / Exclude both | Only if they fix something (Recommended) |
| Dev PRs + #154 npm group / minimatch | Fix minimatch only / Also cheap dev PRs / Take everything | Fix minimatch only (Recommended) |

## Smoke test scope
| Question | Options | Selected |
|---|---|---|
| Depth | REL-08 + real transfer / REL-08 minimum / Full 1.8.0 checklist | REL-08 + real transfer (Recommended) |
| Arr targets for padded-key check | Sonarr v4 + Radarr / Sonarr v4 only | Sonarr v4 + Radarr (Recommended) |
| Setup meaning | Upgrade in place / Both / Fresh only | Upgrade in place (Recommended) |

## Release notes
| Question | Options | Selected |
|---|---|---|
| Key-fix prominence | Plain Fixed line / Fixed + upgrade tip | Plain Fixed line (Recommended) |
| Shutdown + README items | Shutdown in Fixed, README brief / Shutdown only | Shutdown only |
| Rollback runbook target | 1.8.0 runbook / Short note only | Target 1.8.0 (Recommended) |

## PR #156 and sequencing
| Question | Options | Selected |
|---|---|---|
| Sequencing | Merge #156 first / Fold into release PR | Merge #156 first (Recommended) |
| Who merges | Claude at start / Owner | Claude merges at start (Recommended) |

## Claude's Discretion
- Dependency-fix mechanics, smoke scripting/evidence layout, exact note wording, plan grouping.

## Deferred Ideas
- Open Dependabot PRs #154, #153, #149, #147 (and #146/#145 if not justified) for a later release.
