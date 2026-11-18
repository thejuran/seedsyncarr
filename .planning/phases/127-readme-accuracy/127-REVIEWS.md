---
phase: 127
reviewers: [codex]
reviewed_at: 2026-11-18
plans_reviewed: [127-01-PLAN.md]
---

# Cross-AI Plan Review — Phase 127

## Codex Review

## Summary

The plan covers DOC-01 through DOC-04 and correctly follows the revised D-03/D-08 decisions. The stated defaults match the code. The webhook-signing correction is also sound.

**Recommend proceeding after tightening the validation contract and cleanup wording.** No application changes are needed. The current checker fails on the unedited documentation as expected, but targeted probes demonstrate false passes.

## Strengths

- All four requirements have concrete implementation tasks: guide discoverability, security defaults, conditional cleanup claims, and network exposure.
- Defaults agree between `seedsyncarr.py` and `common/config.py`: empty API token and webhook secret; `webhook_require_secret`, encryption, pruning, and dry-run all `False`; pruning delay `60` seconds.
- Revised signing guidance is correct. Both [Sonarr’s sender](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) and [Radarr’s sender](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) serialize the body and add configured headers/basic credentials without computing a body HMAC. This also resolves research assumption A1.
- The API-token/UI caveat matches `web_app.py`: webhook routes are exempt from Bearer authentication, and the UI receives the token in a meta tag.
- Scope is appropriate: README plus the two authorized SECURITY spots. Deferred application authentication changes and configuration-guide gaps remain excluded.
- Explicit source precedence prevents the stale research recommendations from overriding the revised decisions.

## Concerns

1. **[MEDIUM] The claims checker passes materially false security statements.**  
   I exercised `group_claims()` with an in-memory fixture stating authentication and verification are **ON when their secrets are empty**, encryption is **ON by default**, Sonarr/Radarr **sign every request**, and pruning deletes remote copies. It passed. Keyword presence and proximity do not establish the asserted relationships. The exposure check likewise requires “UI” without checking that the token does **not** protect it.

   **Fix:** Treat these checks explicitly as presence checks. Expand mandatory manual verification to cover every DOC-02/DOC-04 assertion, signing conditions, and local-only cleanup—not merely unconditional claims and secret recommendations. Add a few negative fixtures for these demonstrated contradictions if retaining stronger automated acceptance claims.

2. **[MEDIUM] The link checker does not substantiate “every relative link resolves.”**  
   `check_links()` passed all three probes:
   - A nonexistent target with a Markdown link title.
   - A reference-style link to a nonexistent target.
   - An existing file with a nonexistent fragment.

   **Fix:** Either support these forms or explicitly reject unsupported link syntax. Check fragments in linked Markdown files, or constrain new links to fragment-free file targets and validate that constraint. Current simple links are supported, but the acceptance claim is broader than the implementation.

3. **[MEDIUM] Cleanup wording still implies deletion follows automatically when the delay expires.**  
   Task 2 requires wording that pruning “waits … and then deletes,” while preserving the equivalent Usage Examples statement. The controller additionally checks download ownership, lifecycle state, pending transfers, and directory import coverage; deletion can be deferred or abandoned. `docs/CONFIGURATION.md:171` already explains this distinction.

   **Fix:** Say pruning applies only to releases SeedSyncarr downloaded and **attempts deletion after the configured delay, subject to completion/import safeguards**. Permit the corresponding small Usage Examples correction. Detailed retry mechanics can remain in the configuration guide.

4. **[MEDIUM] The scope-failure instruction could erase unrelated work.**  
   Task 3 says to revert any file outside scope reported by the checker. `group_scope()` includes branch changes and untracked files, so it cannot establish that the executor created those changes.

   **Fix:** Record the starting worktree state and revert only accidental changes attributable to this phase. Report pre-existing or concurrent changes separately.

5. **[LOW] Several acceptance conditions are unnecessarily brittle or inconsistent.**  
   Examples include exact physical SECURITY line numbers/counts, a three-matching-lines grep that depends on paragraph wrapping, and `git diff --stat` expectations that fail after task commits. Validation also requests `all` after every task, although unfinished later tasks necessarily keep it red.

   **Fix:** Use task-specific check groups until completion; use one explicit phase baseline consistently; replace line-count greps with content checks. Preserve the two approved SECURITY edits by comparing unchanged surrounding content rather than requiring particular wrapping.

6. **[LOW] “Setting `webhook_require_secret`” is imprecise.**  
   Setting it to `False` does not reject requests. Rejection occurs when it is **True with no secret** (503), or when a configured secret encounters an unsigned/invalidly signed request (401).

   **Fix:** Spell out these conditions consistently in README and SECURITY, and qualify incompatibility as applying to **direct, unsigned Sonarr/Radarr webhooks**.

## Suggestions

- Require the README to state explicitly that `api_token` does not authenticate webhook endpoints; the plan records this fact but does not require it in the output.
- Name rate limiting precisely as applying to **POST config-set**, rather than broadly to “config” endpoints.
- Mark the research’s obsolete decisions and open questions as superseded. The plan handles precedence correctly, but standalone research remains misleading.
- Keep manual claims review as a required acceptance artifact. A prose checker should supplement that review.

## Risk Assessment

**MEDIUM.** Runtime regression risk is low because the deliverable is documentation only. The remaining risk is accepting inaccurate security or cleanup guidance because the mechanical gate passes. Tightening the manual acceptance checklist, correcting the cleanup conditions, and making scope handling non-destructive would reduce overall risk to **LOW**.
