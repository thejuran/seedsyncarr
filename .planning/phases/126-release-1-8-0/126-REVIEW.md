---
phase: 126-release-1-8-0
reviewed: 2026-10-28T23:38:23Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - CHANGELOG.md
  - SECURITY.md
  - package.json
  - release-notes.md
  - src/angular/package.json
  - src/python/pyproject.toml
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 126: Code Review Report

**Reviewed:** 2026-10-28T23:38:23Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

I reviewed the 123b26f..HEAD diff for the 1.8.0 release files and checked the user-facing claims against the code at `v1.7.6` and `v1.8.0`.

**Claims confirmed against code:**
- **Version consistency.** `package.json`, `src/angular/package.json`, `src/angular/package-lock.json` (both version fields) and both version fields in `pyproject.toml` all read 1.8.0. `npm run verify:release-metadata -- 1.8.0` passes. No stray `1.7.6` remains outside the changelog and release notes. The published v1.8.0 release body has the `{{VERSION}}` placeholder resolved to `blob/v1.8.0/CHANGELOG.md`.
- **SECURITY.md SSRF paragraph.** It matches `src/python/web/handler/config.py` `_validate_url` / `_classify_resolved_address`: these allow LAN ranges, CGNAT, ULA and public addresses. They refuse link-local and metadata addresses, unspecified, multicast and reserved addresses, and loopback on any port other than 8989/7878. They also refuse URLs with bad characters, credentials, query strings or a parser disagreement. The paragraph is correctly narrowed from "test or connect" to "test". `_validate_url` is called only from `_test_arr_connection`.
- **Token sent to GitHub, "1.0.0 through 1.7.6".** In `v1.0.0` and `v1.7.6`, `auth.interceptor.ts` attached the token to every request (`if (token)`), and `version-check.service.ts` calls `api.github.com`. In 1.8.0 the interceptor only attaches the token for same-origin `/server/` requests and fails closed on unparseable URLs. No other external HttpClient destination exists in `src/angular/src/app`. The claim holds.
- **Rollback statement that file formats are unchanged.** `git diff v1.7.6..v1.8.0` touches no config or persist serialization code. The persist filenames in the runbook (`controller.persist`, `autoqueue.persist`) match `seedsyncarr.py:41-42`.
- **Dependencies.** `gh api .../dependabot/alerts?state=open` returns 0. certifi moved from 2026.1.4 to 2026.10.23 in `poetry.lock`, which matches the "CA bundle refreshed" line. Angular's `cdk` 22.2.4 / `core` 22.2.3 combination is valid (cdk peer `^22 || ^23`). The vite override is 7.3.7 and resolves to 7.3.7.
- **Secrets.** None in any reviewed file.

**Gaps found:** 1.8.0 is already published, so every finding below is follow-up material, not a blocker. There is one dependency-range problem in test tooling and four small accuracy or completeness gaps in the published text.

**CONVENTION checks:** Skipped. No reviewed file is `.js/.cjs/.mjs/.ts/.tsx`, so no rule pack applies.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `@types/jasmine` bumped to a major ahead of the Jasmine runtime the tests actually use

**File:** `src/angular/package.json:39` (`"@types/jasmine": "^7.0.0"`), together with `:45` (`"jasmine-core": "^6.3.0"`)
**Issue:** The lockfile resolves `@types/jasmine` 7.0.0 and top-level `jasmine-core` 6.3.0. The test runner is Karma (`karma.conf.js:7,9`, `require('karma-jasmine')`), and it loads its own nested `node_modules/karma-jasmine/node_modules/jasmine-core` at **4.6.1**. That means the type definitions now describe Jasmine 7 while the specs run on Jasmine 4.6. The type mismatch existed before (types 6 vs runtime 4.6), but this bump widens it. Spec code can now type-check against matchers or APIs that are missing at runtime. Those specs compile cleanly and then fail with a `TypeError` in the browser, or they silently skip expectations. This is a test-reliability risk, and Dependabot-style bumps like this one will keep reintroducing it.
**Fix:** Pin the types to the runtime that actually executes:
```json
"@types/jasmine": "~4.6.0"
```
Alternatively, upgrade the runtime so all three agree: add `"jasmine-core": "^6.3.0"` to `overrides` so karma-jasmine uses the top-level copy, and set `@types/jasmine` to `~6.0.0`. Then add a Dependabot `ignore` rule for `@types/jasmine` major versions until the runtime moves.

## Info

### IN-01: Release notes overstate how many metadata addresses the old check missed

**File:** `release-notes.md:5`
**Issue:** The notes say Test Connection "now refuses ... a handful of cloud-metadata addresses the previous check missed." 1.8.0 adds exactly two metadata addresses (`config.py:45-47`). Only one of them was actually missed by 1.7.6. The 1.7.6 guard (`addr.is_private or is_loopback or is_reserved or is_link_local`) already refused `fd00:ec2::254`, because `is_private` is True for fc00::/7 (verified on Python 3.12). Only `100.100.100.200` (`is_private` False in 100.64/10) got through. The CHANGELOG wording ("blocked even though they sit inside ... ranges that are otherwise allowed") is accurate because it describes 1.8.0's new allow-list. The release-notes paraphrase is not accurate.
**Fix:** In the next release notes, or by editing the published release body: "...and also refuses multicast addresses, deprecated IPv6 site-local addresses, and the Alibaba Cloud metadata address (100.100.100.200), which the previous check missed."

### IN-02: `playwright` direct-dependency range left behind `@playwright/test`

**File:** `src/angular/package.json:55` (`"playwright": "^1.58.2"`) and `:38` (`"@playwright/test": "^1.64.1"`)
**Issue:** The lockfile currently resolves both to 1.64.1, so nothing is broken today. But the declared floor for `playwright` is six minors behind `@playwright/test`. A fresh resolution, or a lock regeneration with a constrained registry, could install mismatched `playwright` and `playwright-core` builds, and those expect different browser revisions. The bump also looks incomplete, since the other direct Playwright range was raised.
**Fix:** Raise it to `"playwright": "^1.64.1"`, or remove the direct `playwright` dependency if only `@playwright/test` is used.

### IN-03: Backup runbook omits `secrets.key`

**File:** `release-notes.md:28,35`
**Issue:** The runbook backs up `settings.cfg`, `controller.persist` and `autoqueue.persist`. When encryption is enabled, `settings.cfg` can only be read with `/config/secrets.key` (`seedsyncarr.py:43,67`). An upgrade does not touch the keyfile, so the documented path works. However, a user who loses or recreates the config folder during the upgrade (for example by recreating a bind mount) ends up with an encrypted `settings.cfg` copy and no key to decrypt it. The runbook calls this a complete "copy of your settings."
**Fix:** In future runbooks: "Copy `settings.cfg`, `controller.persist`, `autoqueue.persist`, and `secrets.key` if it exists (only present when encryption is enabled)."

### IN-04: SECURITY.md heading could be read as covering runtime *arr connections

**File:** `SECURITY.md:45`
**Issue:** The body correctly says the guard runs "When you test a Sonarr/Radarr connection." The heading ("IP-resolution guard on *arr connection URLs") and the closing phrase ("scoped to the *arr connection URL") read more broadly. The runtime queue polling at `src/python/controller/arr_queue.py:277` sends `X-Api-Key` to the saved URL without this check. That is acceptable for an admin-configured URL, but a reader could assume the guard covers it. The release notes (line 44) do state the distinction.
**Fix:** Rename the heading to "IP-resolution guard on *arr Test Connection". Add one clause to the body: "The saved URL used for regular queue polling is not re-checked; it is trusted as admin configuration."

## Set aside (needs ruling)

### SA-01: The summary sentence leaves out the logging fixes

**Where:** `release-notes.md:1`, `CHANGELOG.md:9-12`
**Why excluded:** This is a matter of editorial completeness, not a factual error. The lead says the release "repairs three smaller startup, shutdown and browser-tab issues," but both documents also ship the webhook-test-log and "dropped" hold-label fixes (LOG-01/02). Those fixes appear in the bullets, so nothing is hidden.
**Effect if left as is:** A reader who skims only the lead underestimates the release slightly. There is no operational impact.
**Needs:** A ruling from the developer on whether release-note leads should list every Fixed category. Options: accept, or adopt it as a rule for future releases.

---

_Reviewed: 2026-10-28T23:38:23Z_
_Reviewer: Claude (bm-code-reviewer)_
_Depth: standard_
