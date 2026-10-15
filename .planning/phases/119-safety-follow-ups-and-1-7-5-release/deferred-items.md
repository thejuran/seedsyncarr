# Phase 119 deferred items

## Secrets printed to container stdout on every start (found during 119-10 smoke)

- **Where:** `src/docker/build/docker-image/setup_default_config.sh` lines 27 and 36, `cat ${SETTINGS_FILE}`.
  The lines date from `98871f5` (v1.0.0) and are present in v1.7.4 and v1.7.5.
- **Effect:** `docker logs <container>` holds the full `settings.cfg`, including `remote_password`,
  `sonarr_api_key`, `radarr_api_key`, `webhook_secret` and `api_token`. These are plaintext unless
  `[Encryption] enabled = True`. Production (1.7.4) on the NAS has encryption off, so its current
  docker logs contain the seedbox password and both arr keys in plaintext (counts verified, values
  not printed). The app's own plain-file logs under `/volume1/docker/seedsync/log` do not contain them.
- **Not a 1.7.5 regression; not fixed in 1.7.5** (fixing it needs a new release). Raised to the
  owner at the 119-10 checkpoint.
- **Likely fix (follow-up):** drop both `cat` lines, or print only section headers or redacted
  values, and add a test that the entrypoint output never contains a `secret=True` property value.
  Consider rotating the seedbox password and arr keys after the fix ships, because older container
  logs keep the values until each container is recreated.

## Transient re-hold after a completed transfer (cosmetic, found during 119-10 smoke)

- When lftp finishes and before the next local scan sees the full file, the root's model state is
  briefly `default`. While an arr is enabled, the completion gate re-evaluates the root during
  that window and can log one `Completion hold for '<name>': …` followed by `… cleared` about 5 s
  later. The model briefly carries a `hold_reason`. Nothing is re-transferred.
- Candidate fix: skip gate evaluation for roots with a just-completed transfer until the local
  scan settles, or treat lftp completion as `downloaded` for gating purposes.
