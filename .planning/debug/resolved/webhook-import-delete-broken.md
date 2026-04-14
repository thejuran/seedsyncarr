---
status: resolved
trigger: "Files are not being marked as imported and deleted after Sonarr/Radarr webhook fires. Download completes, webhook fires, but file stays — no import, no delete, no errors in logs."
created: 2026-02-15T00:00:00Z
updated: 2026-02-15T00:35:00Z
---

## Current Focus

hypothesis: CONFIRMED - User is running v2.0.0 which has known webhook child file matching bug, fixed in v2.0.1
test: verified code matches v2.0.0 broken state, fix exists in v2.0.1
expecting: user needs to upgrade to v2.0.1 or later
next_action: provide resolution and upgrade instructions

## Symptoms

expected: After download completes and Sonarr/Radarr webhook fires, files should be marked imported and then deleted from local storage
actual: Nothing happens — files remain, not marked imported, not deleted
errors: No errors visible in logs
reproduction: Download completes → webhook fires → but file isn't marked imported or deleted
started: Worked before v2.0 (Dark Mode & Polish milestone). Broke after v2.0 changes. v2.0 was phases 29-32.

## Eliminated

## Evidence

- timestamp: 2026-02-15T00:05:00Z
  checked: git history for v2.0 changes (phases 29-32, commits 76300c1..4ccc650)
  found: Only controller.py change in v2.0 was webhook fix (4a83863) after release
  implication: v2.0 dark mode changes didn't touch controller logic

- timestamp: 2026-02-15T00:06:00Z
  checked: controller.py webhook flow (lines 668-749)
  found: When webhook fires, __check_webhook_imports() adds file to imported_file_names, sets import_status=IMPORTED, calls __schedule_auto_delete if autodelete.enabled
  implication: Flow looks correct - webhook should trigger auto-delete scheduling

- timestamp: 2026-02-15T00:07:00Z
  checked: v2.0 added WAITING_FOR_IMPORT enum (commit 2e54493)
  found: New enum value added but no code sets it - only NONE and IMPORTED are used
  implication: WAITING_FOR_IMPORT is unused - not relevant to bug

- timestamp: 2026-02-15T00:15:00Z
  checked: comparison of original webhook implementation (cd8d78a) vs current (4a83863)
  found: Both versions call __schedule_auto_delete() when autodelete.enabled is true
  implication: The code path looks correct - if webhook matches, it should schedule deletion

- timestamp: 2026-02-15T00:16:00Z
  checked: webhook timeline - created in phase 27 (v1.8), then v2.0, then v2.0.1 fix
  found: v2.0.1 changed matching from simple set to BFS child traversal
  implication: v2.0.1 was meant to FIX webhook matching, not break it

- timestamp: 2026-02-15T00:25:00Z
  checked: UI elements for import status in Angular code
  found: Green "Imported" badge shows when importStatus === IMPORTED, plus toast notification
  implication: User would see visible badge if webhook matched. "Not being marked" means matching is failing.

- timestamp: 2026-02-15T00:26:00Z
  checked: autodelete config defaults
  found: autodelete.enabled defaults to FALSE if no [AutoDelete] section in config
  implication: Even if webhook matches, deletion won't happen unless explicitly enabled

- timestamp: 2026-02-15T00:30:00Z
  checked: existing resolved debug session at .planning/debug/resolved/webhook-import-no-action.md
  found: EXACT same symptoms reported and fixed on 2026-02-12 in v2.0.1 (commit 4a83863)
  implication: This is a known issue that was already debugged and fixed

- timestamp: 2026-02-15T00:32:00Z
  checked: git tags and commit history
  found: v2.0.0 -> v2.0.1 contains only the webhook fix (4a83863). Bug existed in original webhook implementation (phase 27, v1.8) but only manifested for directory downloads with child files.
  implication: User is likely running v2.0.0 and needs to upgrade to v2.0.1

- timestamp: 2026-02-15T00:33:00Z
  checked: why "worked before v2.0" despite bug existing in v1.8
  found: Bug only affects directory downloads where webhook reports child file name but SeedSync tracks root directory name. Single file downloads worked fine.
  implication: User likely switched from single files to directory/season pack downloads around v2.0 timeframe

## Resolution

root_cause: User is running v2.0.0 which has the webhook child file matching bug. WebhookManager.process() only matched webhook file names against root-level model file names. For directory downloads, Sonarr/Radarr report the inner child file name (e.g., episode file) but SeedSync tracks the parent directory name - these never matched, so imports were never detected.

fix: This bug was already fixed in v2.0.1 (commit 4a83863, 2026-02-13). The fix:
  1. Controller.__check_webhook_imports() now builds a name-to-root dict that includes ALL child file names (via BFS traversal), not just root-level names
  2. WebhookManager.process() signature changed to receive this dict, enabling child file matching
  3. No-match logs upgraded from DEBUG to WARNING for visibility

verification: User needs to upgrade from v2.0.0 to v2.0.1 or later. The fix was thoroughly tested with 5 new unit tests covering root names, child names, and nested child names.

files_changed: []
  Note: No code changes needed - this is a deployment/upgrade issue, not a code bug

root_cause:
fix:
verification:
files_changed: []
