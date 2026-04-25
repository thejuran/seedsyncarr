---
created: 2026-04-14T00:00:00Z
title: Encrypt stored credentials at rest in config file
area: security
files:
  - src/python/common/config.py
---

## Problem

API keys for Sonarr, Radarr, and other services plus the SeedSyncarr API token and webhook secret are stored as plaintext in the INI config file. If an attacker gains read access to the filesystem (container escape, backup exposure, shared volume misconfiguration), all connected service credentials are immediately compromised.

## Solution

Add optional encryption at rest for sensitive config values:

1. Generate a machine-specific key on first run (e.g. derived from a random secret stored in a separate keyfile with restrictive permissions).
2. Encrypt sensitive fields (`api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password`) before writing to the config file using Fernet (symmetric, from `cryptography` library).
3. Decrypt transparently on read in `config.py`.
4. Migration path: detect plaintext values on startup and encrypt them in place.
5. Keep this optional — users who prefer plaintext (for manual editing) can disable it.
