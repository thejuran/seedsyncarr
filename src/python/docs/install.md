# Installation

## Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
services:
  seedsyncarr:
    image: ghcr.io/thejuran/seedsyncarr:latest
    container_name: seedsyncarr
    ports:
      - "8800:8800"
    volumes:
      - ./config:/root/.seedsyncarr
      - /path/to/downloads:/downloads
    restart: unless-stopped
```

Start the container:

```bash
docker compose up -d
```

### Volume Mounts

| Mount | Purpose |
|-------|---------|
| `./config:/root/.seedsyncarr` | Persists `settings.cfg` and state across restarts |
| `/path/to/downloads:/downloads` | Local directory where files are synced to |

### Updating

```bash
docker compose pull
docker compose up -d
```

## Docker Run

```bash
docker run -d \
  --name seedsyncarr \
  -p 8800:8800 \
  -v ./config:/root/.seedsyncarr \
  -v /path/to/downloads:/downloads \
  ghcr.io/thejuran/seedsyncarr:latest
```

## pip Install (Bare Metal)

For users who prefer running directly on the host without Docker:

```bash
pip install seedsyncarr
```

!!! note
    The pip install requires LFTP to be installed on the host system. On Debian/Ubuntu: `sudo apt install lftp`. On macOS: `brew install lftp`.

## Post-Install

1. Open [http://localhost:8800](http://localhost:8800)
2. Navigate to **Settings** to configure your seedbox connection (remote address, username, paths)
3. See [Configuration Reference](configuration.md) for all available settings
4. See [Sonarr & Radarr Setup](arr-setup.md) to connect your media managers
