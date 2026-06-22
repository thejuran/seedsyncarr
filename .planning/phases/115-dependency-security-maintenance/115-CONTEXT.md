# Phase 115: Dependency & Security Maintenance - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Clear all **8 open Dependabot security alerts** and merge all **7 open Dependabot dependency PRs** (#60–#66), each gated on CI green (DEPS-01, DEPS-02). This is dependency/security maintenance against manifests and lockfiles (`/src/python` requirements, `/src/angular` package files) plus GitHub PR operations — **no code changes to `src/python/` application logic**. Verification differs from a code-path phase: success is CI-green-per-merge and **0 open alerts after**, not a behavioral assertion.

**Live state verified 2026-06-22 (start of phase):**
- All 7 PRs (#60–#66) open, `MERGEABLE`, and CI-green on the active gates (Lint Angular, Lint Python, Python unit tests, Angular unit tests, Build Docker Image, E2E on Docker amd64, Release metadata). Publish/CodeQL jobs show "skipping" — they are post-merge/scheduled, not blocking gates.
- 8 open alerts: **3 HIGH** (undici TLS-cert-validation bypass via dropped requestTls in SOCKS5 ProxyAgent; piscina prototype-pollution gadget → RCE via inherited `options.filename`; hono CORS middleware reflects any Origin with credentials on wildcard default) + **5 MEDIUM** (1× undici cross-user info disclosure via shared-cache whitespace bypass; 4× hono: body-limit bypass on Lambda, Lambda@Edge repeated-header drop, serve-static Windows path traversal via encoded backslash, Lambda Set-Cookie merge).
- **Drift from roadmap:** PR #65 is now **hono 4.12.23 → 4.12.26** (roadmap text said 4.12.25). Newer patch, still remediates the CORS HIGH. Not a blocker — treat the live PR version as authoritative.
</domain>

<decisions>
## Implementation Decisions

### Merge mechanism
- **D-01:** Merge each PR with `gh pr merge --squash` (the branch is already CI-verified). For each PR: confirm CI still green, then squash-merge. This is one-at-a-time and deterministic — matches "each gated on CI green."
- **D-02:** After each merge, later PR branches fall behind `main`. If GitHub still reports a later PR `MERGEABLE`, proceed. If a merge invalidates a later PR's CI (Dependabot rebases it), **wait for that PR to go green again before merging it** — never merge a red or stale-CI PR.
- **D-03:** Do **not** use blanket `gh pr merge --auto` on all 7 at once. Async out-of-order merges make the "CI green per merge" ordering unverifiable and reduce control if #64 interacts badly with another merge.

### Merge order
- **D-04:** Merge **security-critical (HIGH-alert-closing) PRs first**, then the low-risk Python dev-dep bumps. Order: **#64 (npm group, includes piscina→RCE fix) → #65 (hono CORS) → #66 (undici TLS) → #60 (pyinstaller) → #61 (ruff) → #62 (testfixtures) → #63 (pytest)**. Rationale: closes the 3 HIGH alerts soonest; if the phase must stop mid-way, the most important fixes have already landed.
- **D-05:** #64 is the highest-risk PR (18-update npm group). Its full gate (Angular unit tests, Build Docker Image, E2E on Docker amd64, Lint Angular) is **green as of 2026-06-22** — the Angular-build / Karma / Playwright regression watch-out from STATE.md is satisfied by live CI. Still merge it first and re-confirm CI immediately before the merge.

### Post-merge verification (end-state gate)
- **D-06:** After all 7 merges, the phase is "done" only when: (a) re-querying Dependabot alerts returns **0 open**, (b) all 7 PRs show `MERGED`, and (c) `ruff check src/python/` run **locally** against the new ruff (0.15.17 from #61) is clean whole-tree.
- **D-07:** The local whole-tree ruff run is the belt-and-suspenders STATE.md asked for: CI runs `ruff check src/python/` as a **separate gate from pytest**, and a ruff minor bump can introduce new lint rules. CI only checks the merge commit; the local run independently confirms the new version is clean across the whole tree before declaring the phase complete.

### Claude's Discretion
- Exact `gh` invocation flags (e.g. `--squash` vs repo default, deleting the source branch on merge).
- Whether to poll CI between merges with `gh pr checks` vs `gh pr view --json mergeStateStatus`.
- How long to wait for a Dependabot rebase if a later PR goes stale (bounded — surface to operator if a PR won't return green).

### No release/tag/version work
- **D-08:** No release, tag, or version-bump work happens inside this phase (per ROADMAP + STATE.md). v1.4.1 tagging is a milestone-completion concern, not a Phase 115 concern.
</decisions>

<specifics>
## Specific Ideas

- "Merge all 7 for a full cleanup" — the locked decision from 2026-06-21 (STATE.md). No PR is to be deferred; the goal is 0 open alerts and an empty Dependabot queue.
- The safety contract is **CI green per merge** — the real gate lives on GitHub, not in a local diff review. A merge must never happen against a red or stale-CI PR.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & locked decisions
- `.planning/STATE.md` — "Decisions" section: Phase 115 derivation (DEPS-01/DEPS-02), the per-PR breakdown (#60–#66), the "merge all 7" decision (2026-06-21), and the ruff separate-gate watch-out. This is the authoritative scope source — there is no separate `### Phase 115` detail block in ROADMAP.md beyond the one-line entry.
- `.planning/ROADMAP.md` — Phase 115 one-line entry (line ~381): the 8-alert / 7-PR goal statement.

### CI gate definition
- `.github/workflows/ci.yml` — defines the active CI gates a PR must pass (Lint Angular/Python, Python unit tests, Angular unit tests, Build Docker Image, E2E on Docker amd64, Release metadata). This is what "CI green" means for D-01/D-02.

### Live state (not a file — query at plan/execute time)
- `gh pr list --state open` and `gh api repos/thejuran/seedsyncarr/dependabot/alerts` — re-verify the live PR and alert state at execution; the dependency landscape can shift between planning and merging (Dependabot opens/supersedes PRs).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- GitHub CI (`.github/workflows/ci.yml`) is the verification engine — no new test code needed. The phase consumes existing CI, it does not add to it.
- `gh` CLI (authenticated as `thejuran`) drives the PR merges and alert queries.

### Established Patterns
- Prior Dependabot cleanups were done as **quick tasks** (260528-khw, 260604-g9c, 260604-gmy in STATE.md), not full phases — this is the same mechanical pattern, elevated to a phase because v1.4.1 scopes it as DEPS-01/DEPS-02 with an explicit "0 alerts after" success bar.
- Two separate manifests: `/src/python` (pip dev-deps) and `/src/angular` (npm). PRs are manifest-scoped, so Python and JS merges don't conflict with each other.

### Integration Points
- No application-code integration. The only "integration" is lockfile/manifest updates that the build + test CI must continue to pass — already confirmed green per-PR.
</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- `2026-04-21-webob-cgi-upstream-unblock.md` (matched score 0.9 on "testing/python/release" keywords) — **reviewed, NOT folded.** Removing the `PYTHONWARNINGS` cgi filter is blocked on upstream webob 2.0 dropping its stdlib `cgi` import (DEFER-WEBOB). It is not a Dependabot PR/alert and cannot be actioned in this phase. Stays deferred exactly as recorded in STATE.md "Deferred Items."
</deferred>

---

*Phase: 115-dependency-security-maintenance*
*Context gathered: 2026-06-22*
