# Phase 110: Hostile-Reader Discovery Pass - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A **bounded hostile-reader discovery pass** that produces a single triaged, severity-ranked
findings artifact (SCAN-01) in which every finding is explicitly marked either
"fold into a v1.4.0 fix phase" (with the target phase) or "parked" (with a one-line rationale)
(SCAN-02). The pass is conducted by reading the entry points, running the project's existing
tooling under launch framing, and skimming the highest-traffic source files — answering the
question "what would a skeptical engineer on Reddit (r/selfhosted) flag if they browsed this
public repo today?"

**This phase gates the fix scope for Phases 111 (config-set migration) and 112 (defensive
guards).** Its output is the input to their detailed planning.

**Hard boundary — NO production code lands in this phase.** This is discovery/analysis only.
The deliverable is a Markdown findings artifact, nothing else. No source files, configs, tests,
docs, or `.gitignore` changes are made here — those happen in 111/112/113. (The bounded
exception: writing the findings artifact itself and the standard GSD phase artifacts.)

**Scope bound (D-3):** Only *genuinely high-visibility* findings fold into the fix phases.
Everything else is parked with written rationale. The pass must not balloon scope — its
discipline is the explicit fold/park disposition on every finding.

**No release/tag/version work** — the single `v1.4.0` tag is a milestone-end action on branch
`launch-hardening` after the NAS walkthrough + CI green + maintainer sign-off, never inside a phase.

</domain>

<decisions>
## Implementation Decisions

> The user declined the gray-area discussion (dismissed the AskUserQuestion), signalling comfort
> with spec-grounded defaults rather than re-deciding mechanics the design spec already constrains.
> The decisions below are therefore locked defaults grounded in the approved design spec (D-1..D-10,
> SCAN-01/02) and CONCERNS.md. The planner/researcher implement to these.

### Tooling depth & set
- **D-01:** The discovery pass runs the spec-named tooling under launch framing, plus the cheap,
  obvious additions a hostile reader would themselves run — no bespoke/new tooling is introduced:
  - **`ruff check` whole-tree** over `src/python/` (per the CI lint gap note: whole-tree, not just phase files).
  - **Shield** (`/shield:shield`) for Semgrep SAST + gitleaks secret-scan + dependency audit in one pass; the `shield:audit` reasoning skill triages its findings.
  - **`pip-audit`** (or the project's existing dependency-audit path) against the Python lockfile/deps.
  - **`npm audit`** against the Angular tree (`src/angular/`) — a Reddit reader will run it on a JS project.
  - **Entry-point + high-traffic read:** `seedsyncarr.py`, `web/web_app.py`, the `controller/` coordinator, the README and repo root (what a browser sees first).
- **D-02:** Tool runs are **read-only / report-only**. The pass records what each tool reports; it
  does not apply fixes, autofix, or `--fix` anything. Findings flow into the artifact, fixes flow
  into 111/112.

### Fold-vs-park threshold
- **D-03:** The fold bar is: **"a skeptical r/selfhosted engineer would visibly hold this against
  the project on launch day"** — i.e. real correctness/security holes, a red/failing or skipped
  test, credential-leaking surfaces, or repo-hygiene tells they would screenshot. These fold in
  (with a target phase).
- **D-04:** Latent, well-mitigated, invisible-to-a-reader, or externally-blocked items are
  **parked with a one-line rationale**, mirroring how CONCERNS.md already separates active defects
  from residual edge-cases. Examples expected to park: DEFER-SHUTDOWN, DEFER-STREAMQUEUE,
  DEFER-TESTHARDEN, DEFER-WEBOB, the NAS-QEMU local-build limitation (all already parked in
  REQUIREMENTS.md "Future Requirements" / "Out of Scope").

### Artifact structure & home
- **D-05:** The deliverable is a **new `110-FINDINGS.md` in the phase directory**
  (`.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md`).
  Do **NOT** edit `.planning/codebase/CONCERNS.md` — that is a codebase-map artifact owned by
  `/gsd:map-codebase`; the findings pass *cross-references* its entries by description/line but
  does not mutate it.
- **D-06:** Artifact structure: findings **grouped/ranked by severity** (a Critical/High/Medium/Low
  or equivalent scheme), each finding carrying: a stable ID, a one-line title, the
  file(s)/location, a 1-2 sentence "why a hostile reader flags this", and an explicit
  **disposition line** — `FOLD → Phase 111|112|113` **or** `PARK — <rationale>`. Where a finding
  already exists in CONCERNS.md or REQUIREMENTS.md, cite that source so dispositions are traceable.
- **D-07:** The artifact includes a short **summary/rollup** at the top: counts by severity and by
  disposition (how many fold into each target phase, how many parked), so the maintainer reads the
  scope impact in one glance (satisfies SCAN-01's "a maintainer can read a triaged findings artifact").

### Pre-named fix scope interaction
- **D-08:** The six fix items the design spec already commits — config-set GET→POST (CFG/Phase 111),
  the two unsafe-default startup warnings + delete-path hardening + AppProcess spawn fix +
  `.gitignore` + legacy-fallback warning (GUARD/Phase 112) — are treated as **locked and
  confirm-only**. The pass verifies each is real and correctly targeted (and records it in the
  artifact as already-folded with its phase), but does **not** re-litigate D-2/D-4/D-7 or
  down-scope them. The pass's additive value is surfacing *new* findings beyond these six and
  giving everything an explicit disposition.
- **D-09:** A concrete already-known launch-visible gap to confirm and fold: **`LICENSE` file is
  missing at repo root** (verified absent during discussion). This reads as "not a serious project"
  to a hostile reader and is squarely a LAUNCH-05 item → expected disposition `FOLD → Phase 113`.

### Claude's Discretion
- Exact severity scheme labels and the finding-ID prefix (e.g. `HR-01` vs `SCAN-F01`) — planner/executor picks.
- Whether Shield runs via the `/shield:shield` orchestrator or individual tool invocations, and how its consolidated JSON is summarized into the artifact — provided the four tool classes in D-01 are covered.
- Ordering/sectioning within the artifact beyond the severity-ranked + disposition requirements in D-06/D-07.
- Whether to include a brief "what was checked but came up clean" appendix (useful as launch-confidence evidence, but optional).

</decisions>

<specifics>
## Specific Ideas

- The framing is explicitly adversarial and audience-specific: **"what would a skeptical
  r/selfhosted engineer flag"** — not a generic code review. The maintainer is sensitive to
  "vibe-coded" criticism, so the pass should think like the harshest fair reviewer who will
  actually browse the repo (README first, then entry points, then run the obvious tools).
- The substance is already strong: the post-v1.3.0 CONCERNS.md audit found **zero active functional
  bugs**, secrets are Fernet-encrypted, shell paths are `shlex.quote`-escaped, the web layer ships
  Bearer auth + HMAC + CSP + rate limiting, Python coverage ~89%. So the pass is hunting for the
  *residual* launch-visible items and presentation tells, not expecting a pile of bugs — and a
  near-clean result is itself a valid, launch-positive outcome to record.
- The single most launch-visible "this is vibe-coded" gotcha is a **red test in the suite**
  (the AppProcess spawn failure) — already folded to Phase 112 (GUARD-04). The pass confirms it.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope (the locked acceptance contract)
- `.planning/REQUIREMENTS.md` — SCAN-01 (line 18: the triaged-artifact requirement + named tooling), SCAN-02 (line 19: every finding fold/park with target/rationale), and the "Future Requirements" / "Out of Scope" tables (lines 56-78) that pre-park DEFER-* and the QEMU/dual-GET items.
- `.planning/ROADMAP.md` §"Phase 110: Hostile-Reader Discovery Pass" — phase goal + the SCAN-01/02 mapping.
- `docs/superpowers/specs/2026-06-02-launch-hardening-design.md` — the approved design spec. Esp. §3.1 item 7 (the hostile-reader code pass, D-3 bound), the D-1..D-10 decision table (§2), §3.3 (explicitly parked items), and §5 (Definition of Done items 3 = "hostile-reader pass ran; findings fixed or parked with rationale").

### Audit baseline (cross-reference, do NOT mutate)
- `.planning/codebase/CONCERNS.md` — the 2026-06-02 post-v1.3.0 audit. The findings pass extends/cross-references this; it is the prior art for what is already known (Tech Debt, Security Considerations, Fragile Areas, Test Coverage Gaps). **Owned by `/gsd:map-codebase` — do not edit it from this phase.**
- `.planning/codebase/STRUCTURE.md` §"Directory Layout" — entry points and high-traffic file map (seedsyncarr.py, web/web_app.py, controller/).
- `.planning/codebase/STACK.md`, `.planning/codebase/INTEGRATIONS.md` — for the dependency-audit and integration-surface framing.

### Downstream consumers of this artifact
- The `110-FINDINGS.md` this phase writes is consumed by `/gsd:plan-phase 111` and `/gsd:plan-phase 112` (folded findings inform their detailed plans). Phase 113 (LAUNCH) consumes any `FOLD → Phase 113` presentation findings (e.g. missing LICENSE, D-09).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **CONCERNS.md is the head-start.** Most of what a hostile reader would find on the *code* side is
  already enumerated there (legacy `~/.seedsync` fallback, untracked `.orchestrator.json`/`.playwright-mcp/`,
  opt-in auth/webhook defaults, `ignore_errors=True` delete swallow, AppProcess spawn). The pass
  confirms these and their dispositions rather than rediscovering from zero.
- **Shield plugin is installed** (`/shield:shield` orchestrator + `shield:audit` reasoning skill) —
  the primary SAST/secrets/dep-audit vehicle. `ruff` is already a dev dependency (`pyproject.toml:30`)
  and CI runs `ruff check src/python/` as a gate.
- **Presentation baseline already exists:** README.md (154 lines), SECURITY.md, CONTRIBUTING.md,
  CHANGELOG.md, `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` are all present —
  so Phase 113 is mostly audit/rewrite, not create-from-scratch. **Exception confirmed: `LICENSE`
  is absent at repo root** (D-09) — the one structural community-health gap.

### Established Patterns
- The project separates *active defects* from *residual/latent* items in CONCERNS.md, and uses
  explicit DEFER-* IDs in REQUIREMENTS.md for parked work. The findings artifact mirrors this
  convention (severity + explicit disposition) rather than inventing a new taxonomy.
- The CI lint gate is whole-tree `ruff check src/python/` (a separate gate from pytest) — the pass
  runs ruff the same whole-tree way, not scoped to a subset.

### Integration Points
- No code integration — this is an analysis phase. The only "integration" is that `110-FINDINGS.md`
  becomes a canonical ref for the `discuss`/`plan` steps of Phases 111-113.

</code_context>

<deferred>
## Deferred Ideas

- Any *new* finding the pass surfaces that is real-but-launch-invisible is parked in the artifact
  itself (that is the SCAN-02 mechanism), not lost.
- Items already parked upstream and expected to remain parked: DEFER-SHUTDOWN, DEFER-STREAMQUEUE,
  DEFER-TESTHARDEN, DEFER-WEBOB (REQUIREMENTS.md "Future Requirements"); NAS local-build QEMU and
  dual-GET-config-set (REQUIREMENTS.md "Out of Scope").

### Reviewed Todos (not folded)
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.6, area: security) — **not folded into
  Phase 110.** Its match reasons cite "phase, 111"; STATE.md confirms it is already in scope as
  **Phase 111** (CFG-01..04), not this discovery phase. The discovery pass will record the
  underlying issue (SEC-09, credentials in URL) in the artifact as already-folded → Phase 111, but
  the todo itself belongs to 111's planning, not 110's scope.

</deferred>

---

*Phase: 110-hostile-reader-discovery-pass*
*Context gathered: 2026-06-02*
