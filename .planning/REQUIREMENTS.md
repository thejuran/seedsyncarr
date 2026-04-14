# Requirements: SeedSyncarr v1.1.0 UI Redesign

**Defined:** 2026-04-13
**Core Value:** Reliable file sync from seedbox to local with automated media library integration

## v1.1.0 Requirements

Port AIDesigner design artifacts into Angular codebase. Triggarr-level visual polish with earthy Deep Moss palette.

### Navigation

- [ ] **NAV-01**: Nav bar uses backdrop blur with semi-transparent background
- [ ] **NAV-02**: Active page link has amber underline indicator
- [ ] **NAV-03**: Connection status badge in nav with pulse animation
- [ ] **NAV-04**: Notification bell icon with badge dot in nav

### Dashboard — Stats Strip

- [ ] **DASH-01**: Stats strip displays 4 metric cards in responsive grid
- [ ] **DASH-02**: Remote Storage card shows free space with progress bar
- [ ] **DASH-03**: Local Storage card shows free space with progress bar
- [ ] **DASH-04**: Download Speed card shows current speed with peak stat
- [ ] **DASH-05**: Active Tasks card shows running count with DL/Queued badges

### Dashboard — Transfer Table

- [ ] **DASH-06**: Transfer table has search/filter input with magnifying glass icon
- [ ] **DASH-07**: Transfer table has segmented filter buttons (All/Active/Errors)
- [ ] **DASH-08**: File rows display status badges (Syncing/Queued/Synced/Failed) with semantic colors
- [ ] **DASH-09**: File rows show animated striped progress bars with percentage
- [ ] **DASH-10**: File rows display bandwidth and ETA columns
- [ ] **DASH-11**: Transfer table has pagination footer with page controls

### Dashboard — Log Pane

- [ ] **DASH-12**: Compact terminal log pane at bottom of dashboard
- [ ] **DASH-13**: Log entries use monospace font with timestamp, level badge, and message
- [ ] **DASH-14**: Log levels colored by severity (green INFO, amber WARN, red ERROR)

### Settings

- [ ] **SETT-01**: Settings page uses two-column masonry grid on desktop
- [ ] **SETT-02**: All 10 settings sections rendered as card components with icon headers
- [ ] **SETT-03**: Boolean settings use styled toggle switches instead of checkboxes
- [ ] **SETT-04**: AutoQueue card includes inline pattern list with add/remove
- [ ] **SETT-05**: Sonarr/Radarr cards show read-only webhook URL with copy button
- [ ] **SETT-06**: Floating save button bar appears at bottom-right

### Logs Page

- [ ] **LOGS-01**: Log level filter as segmented button group (ALL/INFO/WARN/ERROR/DEBUG)
- [ ] **LOGS-02**: Search field with regex support for filtering log entries
- [ ] **LOGS-03**: Auto-scroll toggle, clear, and export .log action buttons
- [ ] **LOGS-04**: Status bar footer showing connection status, log count, last updated

### About Page

- [ ] **ABUT-01**: App identity card with icon, branded title, version, tagline, build info
- [ ] **ABUT-02**: System info table with key-value pairs (Python, Angular, OS, Uptime, PID, Config)
- [ ] **ABUT-03**: Link cards grid (GitHub, Docs, Report Issue, Changelog) with hover-to-amber
- [ ] **ABUT-04**: License badge and copyright footer

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
| NAV-01 | Phase 62 | Pending |
| NAV-02 | Phase 62 | Pending |
| NAV-03 | Phase 62 | Pending |
| NAV-04 | Phase 62 | Pending |
| DASH-01 | Phase 63 | Pending |
| DASH-02 | Phase 63 | Pending |
| DASH-03 | Phase 63 | Pending |
| DASH-04 | Phase 63 | Pending |
| DASH-05 | Phase 63 | Pending |
| DASH-06 | Phase 63 | Pending |
| DASH-07 | Phase 63 | Pending |
| DASH-08 | Phase 63 | Pending |
| DASH-09 | Phase 63 | Pending |
| DASH-10 | Phase 63 | Pending |
| DASH-11 | Phase 63 | Pending |
| DASH-12 | Phase 64 | Pending |
| DASH-13 | Phase 64 | Pending |
| DASH-14 | Phase 64 | Pending |
| SETT-01 | Phase 65 | Pending |
| SETT-02 | Phase 65 | Pending |
| SETT-03 | Phase 65 | Pending |
| SETT-04 | Phase 65 | Pending |
| SETT-05 | Phase 65 | Pending |
| SETT-06 | Phase 65 | Pending |
| LOGS-01 | Phase 66 | Pending |
| LOGS-02 | Phase 66 | Pending |
| LOGS-03 | Phase 66 | Pending |
| LOGS-04 | Phase 66 | Pending |
| ABUT-01 | Phase 67 | Pending |
| ABUT-02 | Phase 67 | Pending |
| ABUT-03 | Phase 67 | Pending |
| ABUT-04 | Phase 67 | Pending |

**Coverage:**
- v1.1.0 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation — all 32 requirements mapped to Phases 62-67*
