---
status: resolved
trigger: "The 'Queue' action is not available when selecting a file/folder row by clicking on the row itself, but IS available when selecting via the checkbox. Both selection methods should expose the same set of actions."
created: 2026-02-07T00:00:00Z
updated: 2026-02-07T16:39:30Z
---

## Current Focus

hypothesis: CONFIRMED - Row click uses ViewFile.isSelected property (old selection system) while checkboxes use FileSelectionService (new bulk selection system). The file-actions-bar shows actions only for ViewFile.isSelected files, but the "Queue" action logic in file-actions-bar.component.ts has overly restrictive conditions compared to the inline actions.
test: Compare isQueueable() logic in file-actions-bar.component.ts vs file.component.ts
expecting: Different queueable conditions explaining the missing Queue action
next_action: Fix the isQueueable() method in file-actions-bar.component.ts

## Symptoms

expected: Same actions (including "Queue") should be available regardless of whether item is selected by clicking the row or by clicking the checkbox
actual: Selecting via row click does not expose the "Queue" action. Selecting via checkbox does.
errors: No errors in browser console
reproduction: In the SeedSync web UI, click on a file/folder row to select it → observe "Queue" is not present. Deselect, then select the same file/folder using the checkbox → "Queue" is now present.
started: Unknown when this started, may have always been this way

## Eliminated

## Evidence

- timestamp: 2026-02-07T00:00:01Z
  checked: file-list.component.html line 56
  found: Row click triggers onSelect(file) which calls ViewFileService.setSelected()
  implication: Row click uses the old ViewFile.isSelected property system

- timestamp: 2026-02-07T00:00:02Z
  checked: file-list.component.html line 1-23
  found: selectedFile$ observable is derived from files.find(f => f.isSelected) and passed to app-file-actions-bar
  implication: The file-actions-bar component displays for ViewFile.isSelected files (row click selection)

- timestamp: 2026-02-07T00:00:03Z
  checked: file.component.html line 3-8
  found: Checkbox uses isSelected() computed signal and emits checkboxToggle event, which uses FileSelectionService
  implication: Checkbox click uses the new bulk selection system (FileSelectionService), NOT ViewFile.isSelected

- timestamp: 2026-02-07T00:00:04Z
  checked: file-actions-bar.component.ts line 28-31
  found: isQueueable() returns true only when file.status === ViewFile.Status.DEFAULT
  implication: Queue action is only enabled for DEFAULT status files

- timestamp: 2026-02-07T00:00:05Z
  checked: file.component.ts line 130-132
  found: isQueueable() returns true when file.isQueueable property is true (computed from ViewFileService based on status and remoteSize)
  implication: The inline action buttons use file.isQueueable which has broader criteria

- timestamp: 2026-02-07T00:00:06Z
  checked: view-file.service.ts line 404-407
  found: isQueueable is true for [DEFAULT, STOPPED, DELETED] statuses when remoteSize > 0
  implication: Files with STOPPED or DELETED status should be queueable, but file-actions-bar only allows DEFAULT

- timestamp: 2026-02-07T00:00:07Z
  checked: Compared all action methods in file-actions-bar.component.ts vs file.component.ts
  found: ALL action methods have inconsistent logic - file-actions-bar has hardcoded status checks, while file.component uses the computed is* properties from ViewFile
  implication: The entire file-actions-bar component is using incorrect/outdated action availability logic

## Resolution

root_cause: The file-actions-bar.component.ts has hardcoded action availability logic (e.g., isQueueable() only checks for DEFAULT status) instead of using the computed is* properties from ViewFile (isQueueable, isStoppable, isExtractable, etc.). This means files with STOPPED or DELETED status that should be queueable are not showing the Queue button. In contrast, the inline action buttons in file.component.ts correctly use file.isQueueable which is computed from broader criteria in view-file.service.ts.

fix: Replaced all hardcoded action availability methods in file-actions-bar.component.ts to use ViewFile's computed is* properties:
- isQueueable(): now uses file.isQueueable (allows DEFAULT, STOPPED, DELETED with remoteSize > 0)
- isStoppable(): now uses file.isStoppable (allows QUEUED, DOWNLOADING)
- isExtractable(): now uses file.isExtractable && file.isArchive (allows DEFAULT, STOPPED, DOWNLOADED, EXTRACTED with localSize > 0)
- isLocallyDeletable(): now uses file.isLocallyDeletable (allows DEFAULT, STOPPED, DOWNLOADED, EXTRACTED with localSize > 0)
- isRemotelyDeletable(): now uses file.isRemotelyDeletable (allows DEFAULT, STOPPED, DOWNLOADED, EXTRACTED, DELETED with remoteSize > 0)

verification: All 101 unit tests pass. Angular build successful. The file-actions-bar now uses the same action availability logic as the inline action buttons in file rows.

files_changed: ['src/angular/src/app/pages/files/file-actions-bar.component.ts']
