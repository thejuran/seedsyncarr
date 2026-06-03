# Phase 113: Presentation & Launch Readiness - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild SeedSyncarr's **public-facing surface** so the project's genuine quality is evident
within 30 seconds to a skeptical r/selfhosted reader. **Hostile take first** (a framed
cynical-reader teardown AND an explicit codex adversarial pass over the drafted README/docs,
per D-5), then the rewrite is driven by those critiques. Covers LAUNCH-01..06:

- **LAUNCH-01** — cynical-reader teardown artifact + codex pass over the drafted README/docs,
  both captured *before* the rewrite is finalized.
- **LAUNCH-02** — README that explains what SeedSyncarr is in seconds (clear one-liner,
  above-the-fold screenshot, honest feature list, accurate install/quickstart, security posture
  as a stated selling point, fork-relationship note).
- **LAUNCH-03** — README/docs display current, real screenshots of the redesigned UI captured
  via Playwright against the deployed branch build; any staged state flagged.
- **LAUNCH-04** — `SECURITY.md` with a vulnerability-reporting policy + a short honest
  threat-model / posture note.
- **LAUNCH-05** — accurate community-health files (`CONTRIBUTING.md`, issue templates, PR
  template, correct `LICENSE`).
- **LAUNCH-06** — clean v1.4.0 release-notes entry + copy-paste-ready GitHub repo-metadata text
  (About description, topics/tags, homepage link) drafted for manual maintainer application.

**This is the presentation track — sequenced last** (independent of code phases 110-112; it
reflects the hardened code so README/SECURITY.md claims are accurate).

**Hard boundaries:**
- **Screenshots (LAUNCH-03) are captured at the milestone-end walkthrough**, NOT during phase
  execution — against the NAS-deployed `launch-hardening` branch build (D-8).
- **Repo-metadata application + the actual git push/publish are manual maintainer actions
  outside phase execution** — Phase 113 only *drafts* the metadata text (GitHub web-UI settings
  cannot be edited from the session).
- **No release/tag/version work inside the phase** — the single `v1.4.0` tag is a milestone-end
  orchestrator/maintainer action on branch `launch-hardening` after walkthrough + CI green +
  maintainer sign-off.

</domain>

<decisions>
## Implementation Decisions

### README scope & shape
- **D-01:** **Targeted rewrite, not a wholesale restructure.** Keep the existing structure that
  already works (wordmark, above-the-fold dashboard screenshot, feature list, Docker/pip install,
  config, usage examples). Surgically: sharpen the one-liner to the owned angle, add the
  fork-relationship note, pull the security posture up as a stated selling point (near the top,
  not just a bottom-of-file link), and trim any feature claim that overstates.
- **D-02:** The sharpened one-liner / value prop carries the **owned axis** from the comparison
  report §9: a **Sonarr-driven workflow where an HMAC-verified import webhook drives safe
  auto-delete** — "so you never delete a file that didn't make it into your library." Do NOT
  claim a blanket "unique *arr integration."

### Fork-relationship note (LAUNCH-02)
- **D-03:** Credit the **original SeedSync (ipsingh06)** as the origin. **Do NOT name the
  nitrobass24 sibling fork directly**, and **do NOT claim to be the only / sole maintained fork**
  (a hostile reader disproves that instantly by finding the sibling). Acknowledge other forks
  exist *generically* ("like other active forks, it modernizes the original"), then state the
  owned-axis differentiator. Honesty guardrails from comparison report §9 apply: frame the
  absence of outbound-push as a **scope choice, not a deliberate advantage**.
- **D-04:** Reference framing for the note (planner adapts wording, holds the constraints):
  > "SeedSyncarr is a fork of SeedSync (ipsingh06). Like other active forks, it modernizes the
  > original; SeedSyncarr's focus is a Sonarr-driven workflow where an HMAC-verified import
  > webhook drives safe auto-delete — so you never delete a file that didn't reach your library."

### Screenshots (LAUNCH-03)
- **D-05:** **Three canonical screenshots:** Dashboard (above-the-fold hero), Settings page
  (incl. the new POST config-set / remote / Sonarr-Radarr config), and Logs view — covering the
  golden paths and the redesigned UI.
- **D-06:** Captured via Playwright at the **milestone-end walkthrough** against the real
  NAS-deployed branch build. **No `USE_MOCK_MODEL` dev fixtures** — real product only.
- **D-07:** **Capture-time judgment, not a pre-locked staging policy:** shoot the real NAS state;
  **if a screenshot looks bad, iterate on the spot** (start a real transfer to populate an idle
  dashboard, reframe, retake). D-8 permits a representative/arranged real state as long as it's
  honest; flag it only if genuinely needed. (Resolved with the user — no rigid staging rule in
  CONTEXT.)

### SECURITY.md (LAUNCH-04)
- **D-08:** Keep the existing vulnerability-reporting policy (honesty pass on the dates/contact),
  and **add a concise "Security posture" section**: what's protected by default (Fernet-encrypted
  secrets at rest, HMAC-verified import webhooks, Bearer auth, SSRF guards, CSP, rate limiting)
  and what the **opt-in knobs** are for (`api_token` → auth on non-loopback binds;
  `webhook_require_secret` → fail-closed webhooks). A few honest paragraphs that read as maturity
  and double as a selling point — not a full structured threat-model table, not over-promising
  ("not a substitute for network isolation").

### Community-health (LAUNCH-05)
- **D-09:** **Bar = rename + add CoC + freshen.** Concretely:
  - **LICENSE rename** (from HR-05): `LICENSE.txt` → `LICENSE` so GitHub's license detector
    recognizes it (currently shows "No license"); update the `README.md:118` badge link from
    `LICENSE.txt` to `LICENSE`. (Content is already correct Apache 2.0 — this is a rename, not a
    missing license.)
  - **Add `CODE_OF_CONDUCT.md`** — standard Contributor Covenant.
  - **Lightly freshen `CONTRIBUTING.md`** (currently ~1.4KB, thin) to reflect the real workflow:
    dev setup, how to run tests / `ruff` / Karma, PR expectations.
  - **Keep** the existing issue templates (`bug_report.yml`, `feature_request.yml`) and PR
    template as-is.

### Hostile-take-first sequencing (LAUNCH-01) — spec-locked
- **D-10:** The cynical-reader teardown (a framed "r/selfhosted commenter" critique of
  positioning, credibility, first impression) and the **codex adversarial pass** over the
  drafted README/docs (technical-claims accuracy, broken/incomplete install steps, unsupported
  assertions) are **both produced and captured as written artifacts before the rewrite is
  finalized** (D-5). The codex content pass here is *separate* from the orchestrator's per-phase
  codex *plan* review (D-6) — it targets content credibility, not engineering approach.

### Release notes & repo metadata (LAUNCH-06) — spec-locked
- **D-11:** Write a clean **v1.4.0 release-notes entry** (CHANGELOG.md currently tops out at
  [1.3.0] — add a [1.4.0] section summarizing the launch-hardening work: config-set POST
  migration, defensive guards, presentation rebuild) so the releases page is presentable.
- **D-12:** Draft **copy-paste-ready GitHub repo-metadata text** (About description, topics/tags,
  homepage link) as a phase artifact **for the maintainer to apply manually** — the phase does
  not (cannot) apply it to the GitHub web UI.

### Claude's Discretion
- Exact wording of the rewritten README sections (within D-01..D-04 constraints).
- The Contributor Covenant version and exact CONTRIBUTING.md structure (within D-09).
- The artifact filenames/locations for the cynical-reader teardown and codex-pass capture
  (e.g. `113-TEARDOWN.md`, `113-CODEX-PASS.md` in the phase dir) — planner/executor picks.
- Topic/tag selection for the repo-metadata draft (within self-hosted / *arr / seedbox / sync
  domain).
- Whether the security-posture content lives only in SECURITY.md or is also briefly mirrored in
  the README security-selling-point block (D-01 says README states it plainly; SECURITY.md holds
  the detail — avoid verbatim duplication).

</decisions>

<specifics>
## Specific Ideas

- The maintainer is sensitive to **"vibe-coded" criticism** (solo-developed since the fork). The
  whole phase is framed to pre-empt the harshest *fair* r/selfhosted reviewer: README first, then
  they run the obvious tooling (Phase 110 already confirmed those run clean — ruff 0, Semgrep 0,
  gitleaks 0).
- **Substance is genuinely strong** and should be surfaced, not undersold: post-v1.3.0 audit found
  zero active functional bugs; secrets Fernet-encrypted; HMAC-verified webhook; SSRF hardening;
  CSP + Bearer auth + rate limiting; Python coverage ~89%. The launch risk is *presentation
  underselling real quality*, not hidden defects.
- **Fork honesty over bravado** (user instruction, 2026-06-02): name the origin, don't name the
  sibling, never claim to be the only/active fork. Acknowledge siblings generically; compete only
  on the owned axis.
- The deeper test suite is a **contributor** signal, not a user-facing pitch — keep it out of the
  user-facing value prop (comparison report §9.5).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope (the locked acceptance contract)
- `.planning/REQUIREMENTS.md` — LAUNCH-01..06 (lines 44-54), the "Future Requirements" /
  "Out of Scope" tables (lines 56-78). Note: "New user-facing features" and "Broad refactoring"
  are out of scope; this is presentation + the single folded HR-05 rename.
- `.planning/ROADMAP.md` §"Phase 113: Presentation & Launch Readiness" (line 366) — phase goal +
  LAUNCH-01..06 mapping.
- `docs/superpowers/specs/2026-06-02-launch-hardening-design.md` — the approved design spec.
  Esp. §3.2 "In scope — Presentation track" (lines 95-121: content surface, D-5 hostile-take,
  D-8 screenshots, repo-metadata-as-text), §2 D-1/D-5/D-6/D-8 decision rows, §5 Definition of Done
  item 4 (README/SECURITY/community-health/release-notes survived both critiques; screenshots real),
  and §6 Risks (screenshots-misrepresent / mock-data mitigation).

### Discovery findings gating this phase
- `.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md` — the
  triaged hostile-reader artifact. **HR-05 (lines 99-107)** is the only finding folded to Phase 113:
  `LICENSE.txt` → `LICENSE` rename + README badge link fix (LAUNCH-05 / D-09). The "Tools run clean"
  rollup (lines 27-32) is launch-positive evidence the README/SECURITY copy can lean on.

### Positioning source (the fork-relationship + security-differentiator decisions)
- `reports/comparison-nitrobass24-seedsync-2026-06-02.md` §9 "Where we landed (positioning)"
  (lines 193-228) — the owned-axis claim (Sonarr-driven + HMAC-verified safe-delete), the honesty
  guardrails (outbound-push-as-scope-choice, no blanket "unique *arr"), and the differentiators to
  lead with (encryption at rest, SSRF hardening). §8/§8b give the *arr-integration and
  staging-directory depth behind the positioning.

### Current presentation surface (what the rewrite edits)
- `README.md` (154 lines) — targeted rewrite target. Badge link to fix at line 118.
- `SECURITY.md` — reporting policy present; add the posture section (D-08).
- `CONTRIBUTING.md` (~1.4KB) — freshen (D-09). `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.yml`
  + `.github/pull_request_template.md` — keep as-is.
- `CHANGELOG.md` — tops at [1.3.0]; add the [1.4.0] entry (D-11).
- `LICENSE.txt` — rename to `LICENSE` (D-09 / HR-05).
- `doc/images/screenshot-dashboard.png` — current single screenshot; replaced/augmented by the
  3-shot set at walkthrough (D-05).
- Supporting docs (accuracy cross-check only): `docs/GETTING-STARTED.md`, `docs/CONFIGURATION.md`,
  `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Presentation baseline already exists** — README, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md,
  issue templates, PR template are all present. Phase 113 is **audit/rewrite, not
  create-from-scratch**. The one structural gap is the LICENSE *naming* (HR-05) and the missing
  CODE_OF_CONDUCT.md.
- **Playwright MCP is available** for the walkthrough screenshot capture (D-8) against the NAS
  build — produces consistent framing of the real product.
- **Phase 110 "tools run clean" evidence** (ruff/Semgrep/gitleaks 0 findings; pip/npm CVEs are
  dev-only) is reusable copy material for honest security/quality claims.
- **Brand assets exist** — `doc/brand/wordmark-{dark,light}.png` referenced in the README header.

### Established Patterns
- The repo uses GitHub-native community-health locations (`.github/ISSUE_TEMPLATE/`, root
  `CONTRIBUTING.md`/`SECURITY.md`/`LICENSE`); follow those conventions for new files
  (`CODE_OF_CONDUCT.md` at repo root).
- CHANGELOG follows "Keep a Changelog" format with `## [version] - date` headings and
  Security/Fixed/Changed subsections — the [1.4.0] entry matches that shape.
- Shields.io badges (CI, Release, Docker, License) sit under the wordmark; the License badge uses
  GitHub's license API, which is exactly why the `LICENSE.txt` rename matters.

### Integration Points
- **No production code integration** — this phase touches Markdown/docs/repo-metadata + one file
  rename (`LICENSE.txt` → `LICENSE`) + one README link edit. It does NOT modify Python/Angular
  source, configs, or tests.
- The README/SECURITY security claims must stay **accurate to the hardened code shipped in Phases
  111-112** (config-set is POST-only; startup warnings fire; webhook HMAC + opt-in fail-closed) —
  this is why presentation is sequenced last.
- Screenshots integrate at the **milestone-end walkthrough**, downstream of phase execution.

</code_context>

<deferred>
## Deferred Ideas

- **Fuller structured threat-model** (assets/trust-boundaries/mitigations table, explicit
  non-goals) — considered for SECURITY.md but deferred in favor of the concise posture section
  (D-08). Can revisit if a future security milestone wants it.
- **Expanded community-health set** (SUPPORT.md, FUNDING, discussions pointers, architecture-deep
  CONTRIBUTING) — deferred; D-09 bar is rename + CoC + light freshen.
- **External's user-facing gaps** noted in comparison report §9.6 (multi-instance *arr routing,
  Discord/Telegram notification presets, staging + post-download validation) — explicitly NOT
  built here; future feature-milestone candidates only if they fit the author's workflow. Outbound
  push is *not* worth building for a Sonarr-driven user.

### Reviewed Todos (not folded)
- `2026-04-24-migrate-config-set-to-post-body.md` (score 0.9, area: security) — **not folded.**
  Keyword-matched on "config/set/post/phase/111"; this work already shipped as **Phase 111**
  (CFG-01..04). Not a Phase 113 (presentation) item.
- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.9, area: testing) — **not folded.** This is
  `DEFER-WEBOB` in REQUIREMENTS.md "Future Requirements" — blocked on an upstream webob release
  (PR #466), not actionable, and not presentation scope.

</deferred>

---

*Phase: 113-presentation-launch-readiness*
*Context gathered: 2026-06-02*
