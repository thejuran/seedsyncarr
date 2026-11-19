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

---

## Codex Re-review (round 2, after revision bc02e508)

## Summary

The revised plan should achieve DOC-01 through DOC-04. Defaults and webhook-signing guidance match the implementation, and the mandatory manual claims ledger substantially improves acceptance quality.

Four prior concerns are **RESOLVED**; two are **PARTIAL**. No HIGH concerns remain. Tighten the remaining link-check coverage and reconcile one new gate inconsistency before execution.

## Strengths

- All four requirements have explicit tasks and acceptance evidence.
- First-run defaults and upgrade backfills agree: API token and webhook secret empty; secret requirement, encryption, pruning, and dry-run `False`; pruning delay `60` seconds.
- Signing guidance is accurate: SeedSyncarr requires a body HMAC, while the current [Sonarr sender](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) and [Radarr sender](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) add configured headers/basic credentials without calculating that signature.
- The API-token caveats match `web_app.py`: webhook routes are exempt, and the UI receives the token.
- Cleanup wording now reflects ownership evidence, completion/import safeguards, deferral, and local-only deletion.
- Scope remains appropriate: README and the two approved SECURITY spots, with application changes and guide expansion deferred.

## Concerns

1. **[MEDIUM — RESOLVED] Prior concern: false security claims could pass keyword checks.**

   The script now expressly limits its claims, adds negative fixtures, and requires manual verification of security defaults, exposure, signing, and cleanup. That addresses the original concern without pretending regex can establish prose truth.

   **Fix status:** Implemented. Retain the mandatory ledger as an acceptance requirement.

2. **[MEDIUM — PARTIAL] Prior concern: “every relative link resolves” exceeds checker coverage.**

   The three original failures are fixed: my probes now reject nonexistent titled links, reference-link targets, and Markdown fragments.

   However, `link_problems()` silently passes both:

   ```html
   <img src='doc/MISSING.png'>
   <a href=docs/MISSING.md>x</a>
   ```

   HTML extraction only recognizes double-quoted attributes. The plan’s assertion that unsupported syntax is reported is broader than the implementation: unsupported detection only counts unparsed `](` forms.

   **Concrete fix:** Parse HTML attributes with the standard-library `HTMLParser`, or explicitly reject unsupported attribute quoting. Add these negative fixtures and narrow the documented syntax guarantee accordingly.

3. **[MEDIUM — RESOLVED] Prior concern: cleanup implies automatic deletion after timer expiry.**

   Task 2 and validation now require attempted deletion subject to safeguards, restricted to releases SeedSyncarr downloaded. The Usage Examples correction is explicitly permitted and documented. This matches `Controller.__execute_auto_delete()`.

   **Fix status:** Implemented.

4. **[MEDIUM — RESOLVED] Prior concern: scope handling could erase unrelated work.**

   The plan records initial state and explicitly prohibits reverting, deleting, or stashing pre-existing/concurrent changes. It distinguishes those from accidental phase edits.

   **Fix status:** Implemented.

5. **[LOW — PARTIAL] Prior concern: brittle acceptance conditions.**

   Task-specific groups, baseline comparisons, and wrapping-independent keyword checks resolve most issues. However, `security_diff_problems()` still rejects a correctly wrapped webhook bullet, and its selftest explicitly enforces that rejection.

   **Concrete fix:** Allow indented continuation lines within the single approved bullet while preserving surrounding content. Alternatively, acknowledge single-line formatting as an intentional constraint rather than claiming acceptance is independent of physical lines.

6. **[LOW — RESOLVED] Prior concern: “setting `webhook_require_secret`” is imprecise.**

   The output instructions now distinguish unsigned requests encountering a configured secret from `webhook_require_secret = true` with no secret, and scope incompatibility to direct unsigned Sonarr/Radarr webhooks.

   **Fix status:** Implemented.

7. **[LOW — NEW] The permitted checker-fix exception contradicts the automated gate.**

   Task 3 permits a justified checker correction with the full diff recorded in SUMMARY, but its automated command ends with `git diff --exit-code f9a166c8 -- …/127-check.py`. Any permitted correction necessarily fails that command.

   **Concrete fix:** Define separate acceptance paths: unchanged checker passes the integrity comparison; a changed checker requires the documented diff review and passing selftests. Make the automated command and acceptance text agree.

## Suggestions

- Update the remaining stale research summary passages referring to one SECURITY sentence and unresolved owner input. Source precedence prevents a blocker, but the document still gives mixed signals.
- Keep the checker narrowly focused; completing a general Markdown parser would exceed this phase’s needs.
- Preserve the new requirements for explicit webhook API-token exemption and precisely scoped rate limiting.

Verification: checker integrity matches `f9a166c8`; structure, claims, and security groups fail on the unedited documents as expected. Full selftest execution was blocked by this session’s read-only filesystem because it creates temporary fixtures; targeted read-only probes ran successfully.

## Risk Assessment

**LOW.** The revised plan has sound factual guidance, bounded documentation scope, and mandatory manual verification. Remaining risks concern incomplete link validation and acceptance friction, rather than application behavior or misleading security defaults.

---

## Codex Re-review (round 3, after revision e7eaa681)

## Summary

The revised plan should achieve **DOC-01 through DOC-04** and follows the revised D-03/D-08 decisions. All three round-2 PARTIAL/NEW concerns are **RESOLVED**.

No HIGH concerns remain. The narrowed detectors still accept some false statements and reject some accurate prose. These are bounded validation weaknesses because the plan explicitly requires a manual claims ledger and permits justified checker corrections.

## Strengths

- **Requirements coverage is complete:** Task 1 covers guide discoverability and exposure; Task 2 covers defaults and conditional cleanup; Task 3 aligns the two approved SECURITY.md passages.
- **Defaults match code:** first-run configuration and upgrade backfills agree on empty API token/webhook secret; `webhook_require_secret`, encryption, pruning and dry-run defaulting to `False`; pruning delay of `60` seconds.
- **Signing guidance is accurate:** SeedSyncarr verifies a body HMAC. Current native [Sonarr](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) and [Radarr](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/NzbDrone.Core/Notifications/Webhook/WebhookProxy.cs) send configured headers/basic credentials without calculating that signature. Distinguishing direct unsigned requests, configured-secret rejection, and require-secret-without-secret rejection is appropriate.
- **Cleanup wording matches the controller:** deletion is attempted subject to ownership, lifecycle and import safeguards; it affects the local copy.
- Scope remains bounded to README and two SECURITY spots. Manual verification, preservation of unrelated work, and explicit checker-integrity acceptance paths are good safeguards.

## Concerns

### Round-2 follow-up

| Prior concern | Status | Evidence and disposition |
|---|---|---|
| **[MEDIUM] HTML link coverage** | **RESOLVED** | `HTMLParser` now extracts single-quoted and unquoted attributes. Both previously missed missing-target probes are rejected. Unsupported-form limitations are documented. Retain these fixtures. |
| **[LOW] Wrapped SECURITY bullet rejected** | **RESOLVED** | An in-memory replacement with an indented continuation line passes and is flattened correctly for content checks. Keep the surrounding-content checks. |
| **[LOW] Checker-fix exception contradicts gate** | **RESOLVED** | The automated command now reports unchanged/changed paths; changed-checker acceptance requires the complete justified diff and passing selftests. No further fix needed. |

### New findings

1. **[LOW — NEW] Contradiction detectors still miss false statements.**

   Direct probes of `contradiction_problems()` returned no problems for:

   ```text
   Sonarr and Radarr do sign every request.
   Sonarr signs every request without a proxy.
   Pruning deletes the remote copy and leaves the local copy alone.
   Encryption is enabled by default, so secrets are never stored as plaintext.
   ```

   The first misses the narrowed signing pattern. The others demonstrate that sentence-wide negation, `REMOTE_KEPT`, and plaintext exceptions can suppress an unrelated false assertion.

   These are **detector-level false passes**, not evidence that each sentence alone satisfies the complete phase gate.

   **Concrete fix:** Add these as negative fixtures and scope exceptions to the relevant assertion where practical. Otherwise explicitly retain them as known manual-review cases. Do not broaden this into a general prose parser.

2. **[LOW — NEW] Accurate prose still triggers false rejection.**

   These probes were rejected:

   ```text
   The API token protects the API, while an authenticating reverse proxy protects the UI.
   ```

   `TOKEN_PROTECTS_UI` incorrectly connects the token to the proxy’s action.

   ```text
   With `webhook_secret` configured, you should restrict access to port 8800.
   ```

   `recommend_problems()` treats any non-negated “should” beside a secret setting as advice to enable that setting—even when the advised action is network restriction.

   **Concrete fix:** Add both as acceptance fixtures. Restrict recommendation detection to advice about changing the secret setting, and prevent token/UI matching across an explicit subject change. The plan’s existing correction path makes these nonblocking.

3. **[LOW — NEW] Explicit HTML anchors have inconsistent quoting support.**

   This valid same-file link is rejected:

   ```html
   <a id='custom'></a>
   [x](#custom)
   ```

   Link attributes use `HTMLParser`, but `anchors_of()` still recognizes only double-quoted `<a name/id>` attributes.

   **Concrete fix:** Reuse HTML attribute parsing for explicit anchors, or document their narrower supported syntax. This does not affect the planned heading-based links.

## Suggestions

- Preserve mandatory manual acceptance; a green checker remains supporting evidence, not proof of accurate prose.
- Correct the stale research/context assertion that `docs/CONFIGURATION.md` lacks an encryption-enabled default row: the current guide contains `[Encryption] enabled`, default `False`. No guide edit is needed.
- Avoid further checker expansion unless the actual README draft exposes a concrete issue.

Verification: the checker matches baseline `33c50bfc`; structure, claims and security groups fail on the unedited documents as expected. Targeted read-only probes confirmed the findings above. Existing recommendation/contradiction selftests passed before temporary-file creation; the complete selftest could not finish because this session’s filesystem is read-only. No files were changed.

## Risk Assessment

**LOW.** The plan’s factual guidance, requirement coverage and scope are sound. Remaining risks are checker false positives and incomplete contradiction detection, mitigated by mandatory source-backed manual review and the documented checker-correction process.
