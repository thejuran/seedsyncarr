# Future milestone: UI Redesign (pipeline-first)

Drafted 2026-10-21. **Not active.** No phase numbers or release version assigned. Activate only after Reliability, and decide its order relative to Performance and Usability at that time.

**Design source:** Claude Design canvas "SeedSyncarr Dashboard Redesign": https://claude.ai/artifact/GEwUAJppnyCFWUNM7V1kcr. It is private to the owner, so share it before handing it to anyone else. The canvas holds desktop, phone and iPhone Duo screens, a states board and a style sheet. Board names below refer to it.

## Goal

Make the UI show what SeedSyncarr is for: a file's progress from seedbox → local → imported → local copy cleaned up. Make problems visible at a glance and actionable from the row. The redesign is mostly frontend work. The backend changes are listed under **Backend dependencies**.

## Why (problems in the current UI)

- **Import and auto-delete are invisible.** The core feature (import-webhook-driven safe auto-delete) never appears. `import_status` and `hold_reason` reach the frontend, but only a single status badge is shown.
- **Rows repeat themselves.** The release name appears twice (the second line in bright amber mono) and the size appears twice. Progress, Bandwidth and ETA show "100% / – / Done" on every finished row.
- **Errors are hidden.** Filters show no counts, so failures are hidden behind the "Errors" drop-down. The row has no per-row actions; even a single file needs the checkbox and the bulk bar.
- **Styling and navigation.** Uppercase 11px tracked labels and grey ETA text look below 4.5:1 contrast (not measured). Settings appears twice (nav link and gear icon). Filler copy ("Managing synchronization between Seedbox and Local Array", "Data Content").
- **Settings are hard to scan.** Ten cards in a masonry layout, intervals in milliseconds, and checkboxes that silently change other fields.

## Ordered scope (priorities, not assigned phase numbers)

1. [ ] **Style foundation.** Add the new tokens from the "Style sheet" board to `common/_bootstrap-variables.scss`:
   - secondary text `#b4c2a4`, nav surface `#171d16`
   - status text colors `#6fbf78` / `#d9a75a` / `#e07a7a` and the destructive fill `#b84d4d`

   Switch to sentence case throughout and drop the uppercase tracked labels. Use mono only for numbers and release names. **Done when:** tokens exist, there are no uppercase label styles left, and every text/surface pair meets 4.5:1 (measured).
2. [ ] **Pipeline status model (frontend).** Derive a 4-step lifecycle per file (on seedbox, synced, imported, local copy cleaned up) plus one status label and a reason line, from `status`, `import_status`, `hold_reason` and the `DELETED` state. Keep it in one pure function or pipe with a full mapping table and unit tests. **Done when:** every `ViewFile.Status` × `ImportStatus` × hold-reason combination maps to exactly one step, label and reason, and the tests cover the table.
3. [ ] **Dashboard.** Boards: "Dashboard (A — sentence case)", "Multi-select", "Row ⋯ menu", "Loading · Empty queue · No search match", "Lost connection…", "Seedbox unreachable".
   - Compact summary strip (free space, speed with sparkline, a pipeline count breakdown).
   - An attention banner that appears only when needed.
   - Filter tabs with counts.
   - New row layout: title, year and quality tags, the dim release name, the pipeline track, status and reason, size, a contextual action (Retry / Release anyway) and a ⋯ menu.
   - Bulk bar with a per-action count.
   - Banners for lost service connection and an unreachable seedbox.
   - Empty, loading and no-match states.
   - The log pane collapses to a single "latest event" line.

   **Done when:** all of the above match the boards, and the existing E2E specs are updated and pass.
4. [ ] **Settings.** Boards: "Settings", "Settings — validation and failed tests".
   - Sections follow the pipeline (Seedbox, Local storage, AutoQueue, Sonarr & Radarr, Auto-delete), then Performance and Security, with a side menu.
   - Intervals shown in seconds; the stored config stays in ms.
   - Radio choices replace the linked checkboxes.
   - LFTP limits and the scanner script path go under "Advanced".
   - Sonarr/Radarr cards show connection status, the webhook URL with Copy, and where to paste it.
   - Inline field validation, and actionable test-failure messages.
   - An unsaved-changes bar that stays in view.

   **Done when:** every existing option is reachable, saves round-trip unchanged, and the Settings E2E specs pass.
5. [ ] **Logs and About.** Boards: "Logs", "About".
   - Logs: level filters with counts, regex as a toggle, a Live toggle, Clear moved into the ⋯ menu, and inline tracebacks.
   - About: a "Copy for bug report" button. Either wire up Python, OS and uptime, or remove those rows; they show "—" today.

   **Done when:** the Logs and About E2E specs pass and nothing shows a "—" placeholder.
6. [ ] **Phone and iPhone Duo.** Boards: "Phone — …" and the "iPhone Duo" section.
   - Phone (<600px): bottom tab bar, transfer cards, Settings as a list of sections with summaries, collapsed tracebacks.
   - Duo open screen (≈951×669 pt, landscape): two panes split along the 40-pt fold, list on the left and detail on the right.
   - Duo cover screen (466×678 pt): quick-check dashboard.
   - Decide on a tablet layout (~768px) during planning.

   **Done when:** layouts are verified at 390, 466, 768, 951 and 1440 widths, and all touch targets on phone are at least 44px. Duo point sizes are unconfirmed by Apple (951×669 comes from Apple's simulator, as measured by a third-party site; dividing the pixel count by 3 gives 890×626). Re-check before implementing.
7. [ ] **Dialogs and feedback.** Boards: "Confirmation dialogs", "Toasts · Notifications panel".
   - Delete-from-seedbox dialog lists the files, warns about un-imported ones, and needs a checkbox before it enables.
   - Confirmation dialog for regenerating the API token.
   - Clearer release-anyway copy.
   - Toasts with Retry and Details.
   - Notification panel items with action links.

   Update `common/localization.ts`. **Done when:** every destructive action has a confirmation dialog with the new copy, and the copy is covered by tests.
8. [ ] **First-run setup.** Board: "First run — nothing set up". A guided checklist shown when no seedbox is configured. **Done when:** a fresh container reaches its first sync through the checklist without visiting Settings.

## Backend dependencies (verify before planning)

- **Release-name parsing.** Nothing parses title, year or quality tags today. Add a small parser, frontend or backend (decide during planning), that falls back to the raw name when it can't parse. No external metadata lookups.
- **"Local copy cleaned up" step.** It looks derivable from `ModelFile.State.DELETED` plus `import_status == imported`. Confirm that `import_status` survives local deletion and restarts, and that the UI can tell an auto-delete from a manual local delete. If it can't, add a minimal field.
- **Pipeline counts and free space.** Free space can come from the existing capacity stats. The waiting and failed counts can be computed on the client.
- **About system info.** Python version, OS/arch and uptime need a small status endpoint, unless those rows are dropped.

## Change summary (Angular components touched)

| Area | Files |
|---|---|
| Tokens / global | `common/_bootstrap-variables.scss`, `_bootstrap-overrides.scss`, `_common.scss`, `styles.scss` |
| Nav / shell | `pages/main/app.component.*` (drop duplicate Settings link, connection badge → dot, phone tab bar), `notification-bell.component.*` |
| Dashboard | `pages/files/stats-strip.*`, `transfer-table.*`, `transfer-row.*`, `bulk-actions-bar.*`, `dashboard-log-pane.*`, `files-page.*`; new pipeline-status pipe/service; new row-menu component |
| Settings | `pages/settings/settings-page.*`, `option.*`, `options-list.ts` (grouping, units, radios) |
| Logs / About | `pages/logs/logs-page.*`, `pages/about/about-page.*` |
| Copy | `common/localization.ts` |
| Services | `services/files/view-file.service.ts` (lifecycle mapping), confirm-modal service (checkbox-confirm variant) |
| Tests | Angular specs for the above; Playwright E2E for dashboard, settings, logs and about |

## Done when

Every scoped item has its stated evidence, the existing Python, Angular and E2E suites pass, and coverage floors hold. Contrast and touch targets are measured. A live walkthrough on the built image covers sync, hold, release, import, auto-delete, a failed transfer and retry, and the settings round-trip.

## Boundaries

Visual and interaction redesign only. Retain LFTP, the SSE model stream, the config format and the API contracts, apart from the small additions above. No new frontend framework or component library. Keep the Deep Moss palette; no light theme in this milestone.
