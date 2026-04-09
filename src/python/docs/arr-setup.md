# Sonarr & Radarr Setup

SeedSyncarr integrates with Sonarr and Radarr via webhooks. When a download is imported in your *arr app, it sends a webhook notification to SeedSyncarr, which then knows which file to look for on the seedbox.

## Prerequisites

- SeedSyncarr running and accessible on your network (default port: 8800)
- Sonarr and/or Radarr installed and configured

## Step 1: Enable Integration in SeedSyncarr

In the SeedSyncarr web UI, go to **Settings** and configure:

### For Sonarr

| Setting | Value |
|---------|-------|
| **Enabled** | `true` |
| **Sonarr URL** | Your Sonarr base URL (e.g., `http://sonarr:8989` or `http://192.168.1.100:8989`) |
| **Sonarr API Key** | Found in Sonarr under **Settings > General > API Key** |

### For Radarr

| Setting | Value |
|---------|-------|
| **Enabled** | `true` |
| **Radarr URL** | Your Radarr base URL (e.g., `http://radarr:7878` or `http://192.168.1.100:7878`) |
| **Radarr API Key** | Found in Radarr under **Settings > General > API Key** |

## Step 2: Configure Webhooks in Sonarr

1. In Sonarr, go to **Settings > Connect**
2. Click the **+** button to add a new connection
3. Select **Webhook**
4. Configure the webhook:

| Field | Value |
|-------|-------|
| **Name** | `SeedSyncarr` (or any name you prefer) |
| **On Import** | Enabled (checked) |
| **URL** | `http://<seedsyncarr-host>:8800/server/webhook/sonarr` |

Replace `<seedsyncarr-host>` with the hostname or IP where SeedSyncarr is running. If both are in Docker on the same network, use the container name (e.g., `http://seedsyncarr:8800/server/webhook/sonarr`).

5. Click **Test** — you should see a `200 OK` response. SeedSyncarr logs will show: "Sonarr webhook test event received"
6. Click **Save**

## Step 3: Configure Webhooks in Radarr

1. In Radarr, go to **Settings > Connect**
2. Click the **+** button to add a new connection
3. Select **Webhook**
4. Configure the webhook:

| Field | Value |
|-------|-------|
| **Name** | `SeedSyncarr` |
| **On Import** | Enabled (checked) |
| **URL** | `http://<seedsyncarr-host>:8800/server/webhook/radarr` |

5. Click **Test** — you should see a `200 OK` response
6. Click **Save**

## Optional: Webhook Authentication (HMAC)

For additional security, you can enable HMAC-SHA256 signature verification on webhooks.

1. In SeedSyncarr **Settings**, set a `webhook_secret` value in the `[General]` section
2. SeedSyncarr will then require an `X-Webhook-Signature` header on all webhook requests
3. The signature is an HMAC-SHA256 hex digest of the request body, using your secret as the key
4. Sonarr and Radarr do not natively send this header — this feature is for use with webhook proxies or custom setups

!!! warning
    If `webhook_secret` is set in SeedSyncarr but the *arr app does not send the `X-Webhook-Signature` header, all webhook requests will be rejected with `401 Unauthorized`.

!!! tip
    Leave `webhook_secret` empty (the default) if your *arr apps connect directly to SeedSyncarr on a trusted network.

## How It Works

When Sonarr or Radarr imports a download, they send a webhook with `eventType: "Download"`. SeedSyncarr extracts the file name from the payload:

**Sonarr title extraction (in order of priority):**

1. `episodeFile.sourcePath` (basename) — most accurate, the actual file name
2. `release.releaseTitle` — the release group name
3. `series.title` — the series name (least specific)

**Radarr title extraction (in order of priority):**

1. `movieFile.sourcePath` (basename) — most accurate, the actual file name
2. `release.releaseTitle` — the release group name
3. `movie.title` — the movie name (least specific)

The extracted title is matched against files on the seedbox to trigger sync.

## Event Types

| Event | SeedSyncarr Response |
|-------|---------------------|
| `Test` | Returns `200 OK` with body "Test OK" — used when first configuring the webhook |
| `Download` (Import) | Extracts file title and enqueues for sync |
| All other events | Returns `200 OK` and ignores — no processing |

## Troubleshooting

- **Test returns 401:** Your `webhook_secret` is set but the request lacks a valid signature. See [HMAC mismatch FAQ](faq.md#hmac-mismatch-webhook-returns-401).
- **Test succeeds but imports are not detected:** Ensure the event is "On Import" (not "On Grab"). Only `Download` events trigger file matching.
- **Payload too large (413):** Webhook payloads are limited to 1 MB. This should never happen with standard *arr webhooks.
