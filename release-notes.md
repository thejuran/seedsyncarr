A reliability and quality release. Most of this work happens under the hood — the goal was to make SeedSyncarr more dependable, more secure, and easier to maintain going forward, without changing how you use it day to day.

No configuration changes or migrations are required. Existing config files (including encrypted ones) load unchanged.

### Security & Bug Fixes

- **Webhook hardening** — You can now opt in to have the Sonarr/Radarr webhook reject unauthenticated calls when no secret is configured, instead of accepting them. The webhook is also rate-limited, and the config screen no longer hints at whether a secret is set. (Default behavior is unchanged, so existing setups keep working.)
- **Safer file names in logs and the UI** — Crafted file names can no longer forge log entries or inject markup into the confirmation dialogs. The delete/confirm pop-ups now render file names as plain text.
- **Steadier live updates** — Fixed a case where the dashboard's live activity feed could leak or duplicate connections during a reconnect. The feed stays clean over long sessions.
- **More reliable auto-delete** — Hardened the post-import auto-delete so a deletion can't run against files that are still being torn down during shutdown.

### Interface & Performance

- **Lighter, faster frontend** — Removed three end-of-life libraries (jQuery, Font Awesome 4.7, and css-element-queries) and switched all icons to Phosphor. The app ships less code and every icon renders crisply, with no change to how anything looks or works.
- **Smaller production build** — Development-only sample data is now fully excluded from the production bundle.

### Under the Hood

- **More dependable background logging** — Fixed a logging issue that could fail on macOS-style process startup, improving reliability across platforms.
- **Cleaner, more maintainable backend** — Refactored several large internal components (config handling, request dispatch, and the core controller) into smaller, focused pieces. Behavior is identical — this makes future features and fixes faster and safer to ship.
- **Stronger test coverage** — Closed test-coverage gaps and raised the project's minimum coverage bar, so regressions are caught earlier.


**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v1.3.0/CHANGELOG.md
