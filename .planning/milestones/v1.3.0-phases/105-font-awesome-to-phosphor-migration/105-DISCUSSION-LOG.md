# Phase 105: Font Awesome to Phosphor Migration - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (researcher, planner, executor).
> Decisions captured in `105-CONTEXT.md` — this log preserves how they were reached.

**Date:** 2026-06-01
**Phase:** 105-font-awesome-to-phosphor-migration
**Mode:** discuss (standard)
**Areas discussed:** Inexact icon mapping, Weight/style convention, Test-spec assertions, Visual verification depth

## Pre-discussion grounding (codebase scout)

- Inventoried `fa-*` usage: ~85 lines, ~39 distinct icon classes across `src/angular/src/`.
- Confirmed Phosphor (`@phosphor-icons/web ^2.1.2`) already installed and wired in `angular.json` (regular/bold/fill stylesheets), already used in about/settings/transfer-table — migration is *completion*, not *introduction*.
- Identified 5 edit layers: HTML classes, `options-list.ts` data strings, dynamic `<i class="fa {{icon}}">` bindings, conditional `[class.fa-*]` bindings, `.scss` selectors keyed on `.fa-*`, plus 4 breaking test specs.

## Areas presented

User selected all 4 offered gray areas for discussion.

## Decisions reached

### Inexact icon mapping → D-01
| Options presented | Selected |
|---|---|
| (a) Document full table + sign-off on ambiguous only; (b) Claude picks all, documents table; (c) Sign off on full table | **(a) Document + sign-off on ambiguous only** |
- Rationale: fast on the ~31 obvious 1:1 mappings, user eyes on the ~8 genuine semantic judgment calls (tachometer, floppy-o, hdd-o, file-archive-o, circle-o-notch, th-large, sliders, file-code-o) before code lands.

### Weight / style convention → D-02
| Options presented | Selected |
|---|---|
| (a) Regular `ph` default, preserve special cases; (b) Match surrounding Phosphor weight per location; (c) Fill for status, regular elsewhere | **(a) Regular `ph` default, preserve special cases** |
- Rationale: FA4 was effectively single-weight; regular `ph` is the closest, least-surprising match. Don't introduce new bold/fill the app didn't have for a given icon.

### Test-spec assertions → D-03
| Options presented | Selected |
|---|---|
| (a) Faithful update to Phosphor equivalents; (b) Loosen to library-agnostic; (c) Faithful + add data-testid | **(a) Update to Phosphor equivalents (faithful)** |
- Rationale: specs keep verifying the real rendered icon class; no test-hook churn beyond the migration's scope. Karma floors must hold.

### Visual verification depth → D-04
| Options presented | Selected |
|---|---|
| (a) Dev-server manual smoke test (Phase 104 rhythm); (b) Playwright screenshots per page; (c) Both | **(a) Dev-server manual smoke test** |
- Rationale: matches sibling Phase 104 D-01; lightest reliable proof; covers conditional/toggle icon states a screenshot harness might miss.

## Claude's discretion (not asked)

- Exact Phosphor class for each non-ambiguous icon.
- Commit granularity (dep drop as final atomic commit recommended).
- Bundle-stats capture mechanism.
- Running full Karma suite in addition to targeted specs.

## Deferred / redirected

- DEPS-02 mock-fixture hygiene → Phase 106.
- Backend dep hardening → out of scope (later milestone).
- `data-testid` icon hooks → rejected as scope creep.
- Playwright screenshot-diff harness → deferred (could be its own infra phase).

## Todos reviewed (not folded)

- `2026-04-21-webob-cgi-upstream-unblock` (score 0.6) — backend/upstream-blocked, unrelated. Not folded.
- `2026-04-24-migrate-config-set-to-post-body` (score 0.6) — backend API change, separate milestone. Not folded.
