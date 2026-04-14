# Requirements: SeedSyncarr v1.1.0 UI Redesign

**Defined:** 2026-04-13
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.1.0 Requirements

Port AIDesigner design artifacts into Angular codebase. Triggarr-level visual polish with earthy Deep Moss palette.

### Navigation

- [x] **NAV-01**: Nav bar uses backdrop blur with semi-transparent background
- [x] **NAV-02**: Active page link has amber underline indicator
- [x] **NAV-03**: Connection status badge in nav with pulse animation
- [x] **NAV-04**: Notification bell icon with badge dot in nav

### Dashboard — Stats Strip

- [x] **DASH-01**: Stats strip displays 4 metric cards in responsive grid
- [x] **DASH-02**: Remote Storage card shows free space with progress bar
- [x] **DASH-03**: Local Storage card shows free space with progress bar
- [x] **DASH-04**: Download Speed card shows current speed with peak stat
- [x] **DASH-05**: Active Tasks card shows running count with DL/Queued badges

### Dashboard — Transfer Table

- [x] **DASH-06**: Transfer table has search/filter input with magnifying glass icon
- [x] **DASH-07**: Transfer table has segmented filter buttons (All/Active/Errors)
- [x] **DASH-08**: File rows display status badges (Syncing/Queued/Synced/Failed) with semantic colors
- [x] **DASH-09**: File rows show animated striped progress bars with percentage
- [x] **DASH-10**: File rows display bandwidth and ETA columns
- [x] **DASH-11**: Transfer table has pagination footer with page controls

### Dashboard — Log Pane

- [x] **DASH-12**: Compact terminal log pane at bottom of dashboard
- [x] **DASH-13**: Log entries use monospace font with timestamp, level badge, and message
- [x] **DASH-14**: Log levels colored by severity (green INFO, amber WARN, red ERROR)

### Settings

- [x] **SETT-01**: Settings page uses two-column masonry grid on desktop
- [x] **SETT-02**: All 10 settings sections rendered as card components with icon headers
- [x] **SETT-03**: Boolean settings use styled toggle switches instead of checkboxes
- [x] **SETT-04**: AutoQueue card includes inline pattern list with add/remove
- [x] **SETT-05**: Sonarr/Radarr cards show read-only webhook URL with copy button
- [x] **SETT-06**: Floating save button bar appears at bottom-right

### Logs Page

- [x] **LOGS-01**: Log level filter as segmented button group (ALL/INFO/WARN/ERROR/DEBUG)
- [x] **LOGS-02**: Search field with regex support for filtering log entries
- [x] **LOGS-03**: Auto-scroll toggle, clear, and export .log action buttons
- [x] **LOGS-04**: Status bar footer showing connection status, log count, last updated

### About Page

- [x] **ABUT-01**: App identity card with icon, branded title, version, tagline, build info
- [x] **ABUT-02**: System info table with key-value pairs (Python, Angular, OS, Uptime, PID, Config)
- [x] **ABUT-03**: Link cards grid (GitHub, Docs, Report Issue, Changelog) with hover-to-amber
- [x] **ABUT-04**: License badge and copyright footer

## Future Requirements

### Enhancements

- **ENH-01**: Full-viewport terminal mode for Logs page (expandable from current layout)
- **ENH-02**: Lidarr/Readarr integration cards in Settings
- **ENH-03**: Dark/light theme toggle

## Out of Scope

| Feature | Reason |
|---------|--------|
| Tailwind CSS adoption | Project uses Bootstrap 5 + SCSS; port design tokens, not framework |
| Google Fonts / Phosphor Icons | Keep system font stack + Font Awesome 4.7 for consistency |
| New backend API endpoints | UI redesign only — use existing data from current API |
| Angular→htmx rewrite | Visual kinship via design patterns, not framework change |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 62 | Complete |
| NAV-02 | Phase 62 | Complete |
| NAV-03 | Phase 62 | Complete |
| NAV-04 | Phase 62 | Complete |
| DASH-01 | Phase 63 | Complete |
| DASH-02 | Phase 63 | Complete |
| DASH-03 | Phase 63 | Complete |
| DASH-04 | Phase 63 | Complete |
| DASH-05 | Phase 63 | Complete |
| DASH-06 | Phase 63 | Complete |
| DASH-07 | Phase 63 | Complete |
| DASH-08 | Phase 63 | Complete |
| DASH-09 | Phase 63 | Complete |
| DASH-10 | Phase 63 | Complete |
| DASH-11 | Phase 63 | Complete |
| DASH-12 | Phase 64 | Complete |
| DASH-13 | Phase 64 | Complete |
| DASH-14 | Phase 64 | Complete |
| SETT-01 | Phase 65 | Complete |
| SETT-02 | Phase 65 | Complete |
| SETT-03 | Phase 65 | Complete |
| SETT-04 | Phase 65 | Complete |
| SETT-05 | Phase 65 | Complete |
| SETT-06 | Phase 65 | Complete |
| LOGS-01 | Phase 66 | Complete |
| LOGS-02 | Phase 66 | Complete |
| LOGS-03 | Phase 66 | Complete |
| LOGS-04 | Phase 66 | Complete |
| ABUT-01 | Phase 67 | Complete |
| ABUT-02 | Phase 67 | Complete |
| ABUT-03 | Phase 67 | Complete |
| ABUT-04 | Phase 67 | Complete |

**Coverage:**
- v1.1.0 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation — all 32 requirements mapped to Phases 62-67*
