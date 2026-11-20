---
phase: 130
reviewers: [codex]
reviewed_at: 2026-11-20T05:28:23Z
plans_reviewed: [130-01-PLAN.md, 130-02-PLAN.md, 130-03-PLAN.md, 130-04-PLAN.md, 130-05-PLAN.md, 130-06-PLAN.md]
---

# Cross-AI Plan Review — Phase 130

## Codex Review (round 1)

## Summary

The six plans provide strong release sequencing, regression traceability, digest verification and rollback preparation. They largely honor D-01–D-20, but need revision before execution: production queue verification can be waived while REL-08 is still marked complete; the placeholder’s “never transfers” guarantee lacks necessary preconditions; and sandbox restoration is incomplete for some allowed starting states. Several verification steps also provide weaker evidence than their acceptance criteria claim. This review checked repository code, CI and the reused teardown; it did not independently refresh external dependency advisories or inspect NAS state.

## Strengths

- **130-01:** Keeps Phase 129’s merge separate, preserves history and explicitly prevents unrelated runtime dependency movement.
- **130-02:** Confines the minimatch fix to the lockfile and compares the resulting UI against a published artifact.
- **130-03:** Connects existing ARR/WEB regressions to recorded fail-before evidence and correctly makes Linux CI authoritative over the limited macOS run.
- **130-04:** Separates publication approval from deployment approval, pauses wud and resolves the release digest through two methods.
- **130-05:** Exercises both container shutdown and in-process restart, including stderr where port-bind failures appear.
- **130-06:** Includes stopped-state backups, compatibility checks in both images, exact-image verification and explicit rollback criteria.

## Concerns

- **HIGH — 130-05 Task 3; 130-06 Task 1, steps 7–12: Passive checks do not satisfy REL-08.**  
  Both plans explicitly acknowledge that Test Connection does not exercise the queue request, yet permit completion on that evidence. Plan 06 also permits an inconclusive approved probe to fall back to passive checks, while its later ambiguity rule says to stop and ask. Owner deployment approval should not silently redefine the locked requirement for a successful production queue check.

- **HIGH — 130-06 Task 1, step 7: The production placeholder is not guaranteed to remain held.**  
  The plan checks auto-queue but does not require enabled Arr targets before creating the file. [`CompletionGate._run()`](/Users/julianamacbook/seedsyncarr/src/python/controller/completion_gate.py:194) returns `not_required` when no integration is enabled. A synthetic name also does not mathematically guarantee no matching queue record. Moreover, “any verdict that is not unavailable” is insufficient natural evidence: `still_downloading` or `ambiguous_match` can be returned before every Arr’s freshness is checked.

- **HIGH — 130-03 Task 2; 130-05 Tasks 1–2: Restoration does not cover every setting the smoke may change.**  
  The smoke can enable Sonarr, but the reused teardown has no Sonarr-enabled capture or restore mechanism. It also explicitly leaves originally empty URLs/keys populated while reporting `ok`; the plan repairs only the expected empty Radarr pair. Mixed Radarr states—such as a populated URL with an empty key—and initially empty Sonarr fields are not handled. Thus D-11 can fail despite a successful second teardown run. See the [existing teardown](/Users/julianamacbook/seedsyncarr/.planning/phases/126-release-1-8-0/126-teardown.sh:209).

- **MEDIUM — 130-03 Task 3; 130-04 Task 3: Two changed filenames do not prove a version-only bundle change.**  
  Arbitrary application changes could exist inside `main-*.js` while only it and `index.html` differ. Research proposed content normalization, but the plans dropped that check. Also, a renamed main bundle appears as removed and added paths in a literal file-manifest comparison; “exactly two differing entries” needs a defined pairing algorithm.

- **MEDIUM — 130-01 Task 1; 130-04 Task 2: Merge checks are not bound to the approved head.**  
  `gh pr merge ... --merge` lacks `--match-head-commit`. A head change between verification and merge could merge unreviewed content. Plan 04 also lacks a final explicit check of the current head and required checks immediately before merging. Recording whatever SHA happens to be `origin/main` afterward is weaker than recording the PR’s actual `mergeCommit`.

- **MEDIUM — 130-04 Task 2: The evidence-edit and branch-switch sequence is fragile.**  
  This task modifies `130-REL-EVIDENCE.md`, then switches to local `main` and pulls, committing evidence only afterward. Those uncommitted changes can block checkout or fast-forward when the incoming merge changes the same file. The plan needs a deliberate way to preserve the approval record while transitioning branches.

- **MEDIUM — 130-02 Tasks 1–2: Package approval is not tied to the resolved artifact.**  
  `npm view` without an exact version examines the current default version; the later resolver may select something different. The plan records `npm audit signatures` output but does not define failure handling for invalid signatures or unexpected provenance. If this checkpoint is retained, its approval must identify the actual version and integrity subsequently installed.

- **MEDIUM — 130-06 Task 1, rollback: Restarting wud can undermine rollback.**  
  After rollback, 1.8.1 remains published and newer than 1.8.0. The normal success path’s rationale—both containers already run the newest release—no longer applies. The plan allows wud to restart without proving its triggers cannot reapply the failed release.

- **MEDIUM — 130-01 Task 2; 130-02 Task 2; 130-04 owner packet: Dependency exposure wording is too absolute.**  
  “Users were never exposed” exceeds the evidence. The repository explicitly advertises a `dev` extra containing webtest, through which soupsieve can be installed. Also, PyPI runtime dependencies are independently resolved from lower-bounded metadata, including `paste>=3.10.1`; the Docker lock does not fix pip users to Paste 3.10.1. Distinguish the standard Docker image, default pip installation and development installations.

- **LOW — 130-03 Task 2; 130-05 Task 1: Some acceptance criteria cannot literally pass.**  
  The copied teardown prints status, image and cleanup-count lines even with an empty capture directory, so “every line must read `ok (not set this session)`” is impossible. Shellcheck is simultaneously a must-have and optional. Several checks search for evidence headings rather than verifying the underlying outcome.

## Suggestions

- Require actual production queue evidence before marking REL-08 complete. If unavailable, leave verification pending or obtain an explicit requirement amendment.
- Before creating a probe, verify enabled Arr targets, candidate eligibility and absence of a matching queue record. Use a unique session name and guaranteed cleanup on interruption.
- Capture and restore every changed field independently, including Sonarr enabled and empty credentials. Verify exact restored values, not merely “different from production.”
- Pair old/new main bundles, normalize only the version literal and its index reference, then require byte equality.
- Bind merges to verified head SHAs and obtain the tag target from the merged PR record.
- Define a clean branch-transition procedure for approval evidence and a rollback-specific wud policy.
- Keep the six-wave structure, but remove redundant test reruns and replace brittle textual checks with a smaller set of executable assertions.

## Risk Assessment

**HIGH as written**, primarily because the production probe and restoration paths can violate their safety claims, and the completion path can mark REL-08 satisfied without a production queue request. With those corrected, overall risk should fall to **MEDIUM**, appropriate for an otherwise well-controlled release involving live credentials, production state and irreversible publication.

---

## Codex Review (round 2, after revision 1)

## 1. Summary

**Substantial improvement, but revise once more before execution.** The strongest fixes are the byte-level bundle comparison, merges bound to verified heads, explicit queue-check deviation reporting, and rollback-specific wud policy.

Remaining gaps concern the production probe’s preconditions, restoration of nonempty malformed keys, and evidence handling across the branch switch. Two additional execution blockers are noted below.

I checked the relevant repository code and reused teardown. I did not refresh external dependency advisories or inspect live NAS state.

## 2. Status of round-1 concerns

| Prior concern | Status | Assessment |
|---|---|---|
| **HIGH: Passive checks accepted as REL-08 completion** | **RESOLVED** | The probe is now the default, automatic fallback is forbidden, and passive evidence requires explicit owner acceptance with “not proven” propagated into evidence, SUMMARY and STATE. Keep REL-08 unmet unless the owner explicitly amends the requirement. |
| **HIGH: Placeholder not guaranteed to remain held** | **PARTIAL** | Enabled Arrs, candidate eligibility, unique naming and cleanup are now specified. However, the precheck queries a different endpoint from the application, assumes one page is sufficient, and does not bind the queried Arr instances to production’s configured URLs. |
| **HIGH: Incomplete sandbox restoration** | **PARTIAL** | Sonarr enabled, empty fields and mixed states are addressed well. Nonempty keys containing padding or invalid characters still cannot necessarily be restored through the normalizing/validating settings API. |
| **MEDIUM: Filenames alone insufficient for bundle proof** | **RESOLVED** | Explicit main-bundle pairing, narrowly constrained byte differences and normalized byte equality provide the missing evidence. |
| **MEDIUM: Merge checks not bound to approved head** | **RESOLVED** | Both merges use `--match-head-commit`, immediate rechecks, PR-derived merge SHAs and parent verification. |
| **MEDIUM: Evidence edits conflict with branch transition** | **PARTIAL** | Pre-merge evidence is committed, but Task 2 step 6 instructs recording the merge after that commit and before step 7’s checkout. This reintroduces an uncommitted evidence edit across the transition. |
| **MEDIUM: Package approval not tied to installed artifact** | **RESOLVED** | Approval identifies exact version and integrity; installation requires matching values; signature/provenance failures stop execution. |
| **MEDIUM: wud can undo rollback** | **RESOLVED** | Rollback explicitly leaves wud stopped pending an owner decision. |
| **MEDIUM: Dependency exposure wording too absolute** | **RESOLVED** | Docker, default pip and developer-extra installations are distinguished, including independently resolved pip runtime dependencies. |
| **LOW: Impossible or weak acceptance criteria** | **PARTIAL** | Dry-run output and mandatory shellcheck are corrected. Many automated verifiers still check recorded text rather than outcomes, although the accompanying acceptance criteria are substantially stronger. |

## 3. Remaining and new concerns

### HIGH — 130-06 Task 1, step 7(b): Probe precheck does not inspect the application’s actual queue inputs

The application requests `/api/v3/queue/details` from each **configured target URL**. See [arr_queue.py:149](/Users/julianamacbook/seedsyncarr/src/python/controller/arr_queue.py:149) and [arr_queue.py:167](/Users/julianamacbook/seedsyncarr/src/python/controller/arr_queue.py:167).

The plan instead requests `/api/v3/queue?pageSize=1000` through assumed container host ports. It neither verifies those containers correspond to production’s configured targets nor establishes that all records were returned.

Consequently, “match count 0” may describe the wrong Arr instance or an incomplete record set. The subsequent gate can see a matching completed record that the precheck missed, undermining the promised no-transfer behavior.

**Fix:** Derive targets from production’s configured URLs, verify instance identity, and inspect the same complete queue data used by the application. Use identical basename normalization and fail closed on incomplete or unparseable responses. Describe no-transfer as conditional on those verified preconditions rather than guaranteed by a prior snapshot.

### MEDIUM — 130-03 Task 2 and 130-05 Task 2: Exact restoration still excludes some nonempty starting keys

The settings handler trims Arr keys and rejects invalid values before storing them. See [config.py:354](/Users/julianamacbook/seedsyncarr/src/python/web/handler/config.py:354).

A pre-smoke key containing surrounding whitespace therefore cannot be restored byte-for-byte through that route; a malformed nonempty key may be rejected outright. The revised disk-repair path covers **empty originals only**. Fingerprinting detects this failure but leaves restoration blocked after mutation.

**Fix:** Provide a controlled restoration path for original values the API cannot reproduce, or detect these states before mutation and stop before changing the sandbox.

### MEDIUM — 130-04 Task 2, steps 6–7: Merge recording again dirties the tree before checkout

Step 5 commits pending evidence. Step 6 then says to record the merge SHA and checks. Step 7 immediately switches branches and cherry-picks commits that modify the same evidence file.

If recorded on disk as instructed, these changes can obstruct checkout or cherry-pick.

**Fix:** Keep merge results in scratch storage until after the transition, or commit them before checkout and include that commit in the replay. Assert a clean tracked tree immediately before checkout.

### MEDIUM — NEW — 130-02 Task 2, steps 2 and 5: Whole-tree cleanliness checks conflict with required evidence edits

Task 1 writes the package facts and owner reply into `130-REL-EVIDENCE.md` without committing them. Task 2 then requires `git diff --stat` to list **only** the Angular lockfile, and later requires the tree to be clean apart from that lockfile.

The required evidence edits violate both checks on the normal execution path.

**Fix:** Commit Task 1’s evidence before Task 2, and scope source-change assertions to the relevant manifests while explicitly allowing current evidence edits.

### MEDIUM — NEW — 130-05 Task 1, steps 6–7: “Sonarr only” is not established

The revised plan allows Radarr to be enabled initially, but never disables it before the “Queue check, Sonarr only” step.

An enabled, unreachable original Radarr can block the expected hold; an enabled, reachable Radarr means the test exercises both integrations despite its label.

**Fix:** Capture the existing state, set `RADARR_ENABLED_SET=1` before temporarily disabling Radarr, and verify Sonarr is the sole enabled target before creating the first root. Restore the original flag through the existing teardown.

## 4. Suggestions

- Correct the five execution gaps above before approval.
- Preserve the revised bundle, merge-binding and wud safeguards.
- Keep requirement satisfaction separate from deployment completion: an accepted passive deviation must not become a REL-08 PASS.
- Add focused harness fixture cases for padded and malformed original keys, alongside the empty/mixed-state cases.

## 5. Risk Assessment

**HIGH pending correction of the production probe precheck.** Most round-1 risks are now substantially reduced. After the probe and restoration gaps are closed and the deterministic sequencing blockers corrected, **MEDIUM** is appropriate for this release involving live credentials, production state and irreversible publication.

---

## Codex Review (round 3, after revision 2)

## 1. Summary

**The five round-2 execution gaps are resolved at the plan level.** The production probe now checks the application’s actual queue inputs; malformed original keys stop the smoke before mutation; evidence survives the branch transition; lockfile checks allow evidence edits; and the Sonarr-only test explicitly disables Radarr.

One new **MEDIUM** concern remains in the fingerprint helper’s handling of failed config reads, plus one **LOW** ambiguity in the precheck dry run. Address the medium concern before execution.

I inspected the repository’s queue client, completion gate, settings handler and reused teardown. This was read-only; I did not inspect live NAS state or refresh dependency advisories. The orchestrator’s branching/worktree ruling is accepted.

## 2. Status of each round-2 concern

| Concern | Status | Assessment |
|---|---|---|
| Passive checks accepted as REL-08 completion | **RESOLVED** | Passive evidence remains an explicit owner-approved deviation. REL-08 stays unchecked without `probe-pass` and owner confirmation. |
| Probe precheck does not inspect actual queue inputs | **RESOLVED** | Uses production’s configured URLs from inside its container, checks application identity, requests `/api/v3/queue/details`, imports `_basename`, rejects malformed responses and acknowledges the snapshot race. These align with [arr_queue.py](/Users/julianamacbook/seedsyncarr/src/python/controller/arr_queue.py:149). |
| Exact restoration excludes malformed nonempty keys | **RESOLVED** | Pre-mutation `precheck` rejects padded, malformed and non-text originals. Fixtures cover these cases. This addresses the normalization and validation in the [settings handler](/Users/julianamacbook/seedsyncarr/src/python/web/handler/config.py:348). |
| Filenames alone insufficient for bundle proof | **RESOLVED** | Explicit main-bundle pairing and normalized byte equality remain intact, including published-image verification. |
| Merge checks not bound to approved head | **RESOLVED** | Immediate rechecks, `--match-head-commit`, PR-derived merge SHAs and parent checks remain intact. |
| Merge recording dirties the tree before checkout | **RESOLVED** | The merge record is committed before checkout; cleanliness and the replay range are recomputed immediately before transition. |
| Package approval not tied to installed artifact | **RESOLVED** | Exact version/integrity binding and stop rules remain intact. |
| wud can undo rollback | **RESOLVED** | Rollback leaves wud stopped pending an owner decision. |
| Dependency exposure wording too absolute | **RESOLVED** | Docker, ordinary pip installation and developer extras remain distinguished. |
| Weak automated acceptance checks | **PARTIAL** | Several verifiers still establish that evidence text exists rather than independently establish the outcome. Detailed action steps and acceptance criteria compensate, but `T*_OK` alone is not sufficient release evidence. |
| Whole-tree cleanliness conflicts with evidence edits | **RESOLVED** | Plan 02 commits checkpoint evidence and scopes subsequent assertions to source manifests. |
| “Sonarr only” not established | **RESOLVED** | Radarr’s restoration flag is written before disabling it; both enabled flags are read back before creating the first root. |

## 3. New concerns

### MEDIUM — 130-03 Task 2, step 4; 130-05 capture and restoration: Config-read failures can masquerade as empty values

The fingerprint contract maps null/empty values to `EMPTY`, but does not explicitly require:

- Successful HTTP status and JSON parsing.
- Expected sections and field presence.
- Boolean types for enabled flags.
- Immediate failure when a field read fails.

With ordinary `curl | jq` shell handling and only `set -u`, a failed request can yield empty output. A valid JSON error object can also produce null for every selected field. Consequently, `precheck` could incorrectly permit mutation, or capture/verification could mistake missing data for legitimate empty settings.

This is particularly consequential because `L0_VERIFY ok` authorizes deletion of restoration backups and key files.

**Fix:** Make all three modes fail closed on transport, HTTP, parsing, schema or type errors. Distinguish a present null field from a missing field. Never write a capture or emit an `ok` marker after any failed read. Add fixtures for `{}`, missing fields and wrong types, plus a simulated failed request. Preserve backups on verification read failure.

### LOW — 130-06 Task 1, step 1a: Sandbox dry-run outcomes do not cover valid restored configurations

Plan 05 deliberately restores the sandbox’s original wiring, including enabled integrations with empty or unreachable configuration. The new precheck dry run accepts only `PRECHECK ok` or `PRECHECK FAIL - no_targets`.

A correctly implemented script can therefore return a legitimate `key`, `url`, `identity` or request failure against the restored sandbox. The plan does not clearly distinguish that environmental result from a script defect.

**Fix:** Separate script validation from live-target readiness. Accept documented, correctly formatted environmental failures for the sandbox dry run, while retaining the strict `PRECHECK ok` requirement against production before probe creation. Use fixtures to exercise the successful parsing/matching path.

## 4. Risk Assessment

**MEDIUM.** The previous HIGH probe-input concern is closed, and no new HIGH concern was found.

Before execution, tighten the fingerprint helper’s read-failure contract. The release otherwise retains appropriate controls for exact-artifact deployment, explicit approvals, rollback and truthful requirement completion.

---

## Codex Review (round 4, after revision 3)

| Round-3 concern | Status | Assessment |
|---|---|---|
| **MEDIUM — config-read failures masquerading as empty values** | **PARTIAL** | Schema/type checks, missing-versus-null handling, redaction detection and failure fixtures substantially address it. Two gaps remain below: transport failures after HTTP headers, and premature deletion of restoration files. |
| **LOW — sandbox dry-run outcomes** | **RESOLVED** | 130-06 now separates fixture validation from environmental readiness, accepts explained environmental failures on the sandbox, and still requires a strict production pass before probe creation. |

**MEDIUM — 130-03 Task 2, step 4: reject every unsuccessful transport**

The new contract classifies a nonzero curl exit as `transport` only **“without a status.”** Curl can receive HTTP 200 and subsequently fail—for example, a truncated transfer or timeout. If the received body happens to be valid, complete JSON, the remaining checks could permit an `ok` despite curl’s failure.

Require curl exit 0 **and** HTTP 2xx before parsing. Preserve `http_<status>` for actual HTTP failures; classify other nonzero curl exits as `transport`, including HTTP 200 followed by a transfer error. Add that fixture. This is a remaining gap in the original MEDIUM concern.

**New MEDIUM — 130-03 Task 2 / 130-05 Task 2, step 5: preservation instructions conflict with teardown**

The new verification-failure path requires keeping both `.l0` files until `L0_VERIFY ok`. However, the reused teardown deletes each original key file immediately after its own successful comparison—see [126-teardown.sh](/Users/julianamacbook/seedsyncarr/.planning/phases/126-release-1-8-0/126-teardown.sh:296). Plan 03 preserves that behavior, including explicit deletion for empty originals.

Consequently, by step 5(d), the original key files may already be gone, so the newly promised preservation cannot occur.

Defer **all** `.l0` deletion to step 5(f), after successful fingerprint verification, and update the permitted teardown changes accordingly. Verify that a simulated final read failure leaves both originals intact.

**Risk assessment: MEDIUM.** No new HIGH concern found. The dry-run revision is sound; close these two failure-path gaps before execution. This was a read-only plan review with inspection of the reused teardown, not live NAS validation.
