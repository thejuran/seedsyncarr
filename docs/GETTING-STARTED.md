<!-- generated-by: gsd-doc-writer -->
# Getting Started

## Prerequisites

SeedSyncarr is distributed as a Docker image and does not require a local runtime environment for end users. The only prerequisite is:

- **Docker** — any recent version with Docker Compose V2 support (`docker compose` subcommand)

If you intend to build from source or contribute, you will also need:

- **Python** `>= 3.11` (CI runs 3.12)
- **Node.js** `>= 22`
- **Poetry** — Python dependency management (`pip install poetry`)

---

## Installation Steps

### Docker (recommended)

1. Create a `docker-compose.yml` with the following content:

```yaml
services:
  seedsyncarr:
    image: ghcr.io/thejuran/seedsyncarr:latest
    container_name: seedsyncarr
    restart: unless-stopped
    ports:
      - "8800:8800"
    volumes:
      - ~/.seedsyncarr:/config
      - /path/to/downloads:/downloads
```

2. Replace `/path/to/downloads` with the local directory where you want files synced to.

3. Pull and start the container:

```bash
docker compose up -d
```

### Run directly with Docker (without Compose)

```bash
docker run -d \
  --name seedsyncarr \
  --restart unless-stopped \
  -p 8800:8800 \
  -v ~/.seedsyncarr:/config \
  -v /path/to/downloads:/downloads \
  ghcr.io/thejuran/seedsyncarr:latest
```

---

## First Run

1. Start the container using one of the installation methods above.
2. Open `http://localhost:8800` in your browser. The SeedSyncarr web UI will load.
3. Navigate to **Settings** and fill in the required remote server fields:
   - **Remote Address** — hostname or IP of your seedbox
   - **Remote Username** — SSH/SFTP username
   - **Remote Password** — password (or enable SSH key auth)
   - **Remote Path** — the directory on the remote server to sync from
4. Click **Save**. SeedSyncarr will begin scanning the remote server and queuing files for download.

The application refuses to start syncing until the four required settings above are replaced from their `<replace me>` placeholder values. All other settings have sensible defaults and can be tuned later.

---

## Common Setup Issues

**Container exits immediately or fails to connect**

Verify that the `/config` volume mount is writable and that `settings.cfg` was created on first run:

```bash
ls ~/.seedsyncarr
# Expected: settings.cfg  controller.persist  autoqueue.persist
```

If the file does not exist, check Docker volume permissions (`chown` the host directory so the container user can write to it).

**"Connection refused" when opening the web UI**

Confirm the port mapping is correct and the container is running:

```bash
docker ps | grep seedsyncarr
```

The container exposes port `8800`. If another service occupies that port on your host, change the host side of the mapping (e.g., `"8900:8800"`).

**SSH connection to remote server fails**

- Confirm the remote host is reachable from the Docker container's network.
- Verify the username, password, and port in Settings match your seedbox credentials.
- To use SSH key authentication instead of a password, set `use_ssh_key = True` in `settings.cfg` and ensure the key is present in the SSH config of the user running the container.

**Files are detected but never downloaded**

AutoQueue is enabled by default and will queue all discovered remote files. If you have enabled **Patterns Only** mode in AutoQueue settings, ensure at least one pattern matches files on the remote server.

---

## Next Steps

- See [CONFIGURATION.md](CONFIGURATION.md) for the full reference of all `settings.cfg` options, including Sonarr/Radarr integration, AutoQueue patterns, and AutoDelete.
- See [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the sync daemon, web UI, and LFTP transfer engine fit together.
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to set up a development environment and run the test suite.
