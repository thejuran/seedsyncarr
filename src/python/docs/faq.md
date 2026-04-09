# FAQ & Troubleshooting

## Connection refused when accessing the dashboard

**Symptom:** Browser shows "connection refused" or "site can't be reached" at `http://localhost:8800`.

**Solutions:**

1. Verify the container is running: `docker ps | grep seedsyncarr`
2. Check the port mapping in your `docker-compose.yml` matches 8800
3. If running on a remote server, ensure the firewall allows port 8800
4. Check container logs for startup errors: `docker logs seedsyncarr`

## HMAC mismatch / webhook returns 401

**Symptom:** Sonarr or Radarr webhook test returns 401 Unauthorized, or logs show "Invalid webhook signature".

**Solutions:**

1. The `webhook_secret` value in SeedSyncarr's `[General]` config must exactly match the secret configured in your *arr app's webhook settings
2. If you don't need webhook authentication, leave `webhook_secret` empty in both SeedSyncarr and the *arr app
3. Check for trailing whitespace or newlines in the secret value
4. See [Sonarr & Radarr Setup](arr-setup.md) for detailed webhook configuration

## arm64 (Apple Silicon) test caveat

**Symptom:** `make run-tests-python` fails on Apple Silicon Macs with errors related to `rar` extraction.

**Explanation:** The `rar` package used for archive extraction is amd64-only. This affects the local test suite on arm64 machines but does **not** affect the Docker image — the production container runs on both amd64 and arm64 and handles extraction correctly.

**Workaround:** Run tests in Docker or ignore rar-related test failures on arm64. CI runs on amd64 and is unaffected.

## Sonarr/Radarr webhook shows "Test OK" but imports don't work

**Symptom:** The *arr app's webhook test succeeds (200 OK), but actual imports are not detected.

**Solutions:**

1. Ensure the webhook event type is set to **"On Import"** (also called "Download" in the webhook payload)
2. Check that the file name on the seedbox matches what Sonarr/Radarr reports in the webhook payload
3. Verify SeedSyncarr's Sonarr/Radarr integration is **enabled** in Settings
4. Check SeedSyncarr logs for webhook processing: `docker logs seedsyncarr | grep webhook`

## Files sync but are not extracted

**Symptom:** Files download successfully but archives remain packed.

**Solutions:**

1. Check that `auto_extract` is enabled in the `[AutoQueue]` section
2. Verify `extract_path` in `[Controller]` points to a writable directory
3. If using `use_local_path_as_extract_path`, ensure `local_path` is writable
