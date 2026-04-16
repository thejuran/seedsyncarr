# Storage Capacity Percentage Tiles

**Date:** 2026-04-15
**Status:** Approved

## Summary

Add disk capacity awareness to the Remote Storage and Local Storage dashboard tiles. Currently the tiles show tracked file sizes only. After this change, when capacity data is available, the tiles display a percentage with used/total breakdown. When capacity is unavailable, they fall back to the current tracked-bytes display.

## Decisions

- **Approach:** Dedicated disk capacity service (Approach A) — new `StorageStatus` component on the existing `Status` model, updated by the controller after each scan cycle.
- **Data source (local):** `shutil.disk_usage()` on the configured local path.
- **Data source (remote):** `df -B1 <remote_path>` via the existing `Sshcp.shell()` method, piggybacked onto the scan cycle that already establishes an SSH session.
- **Delivery to frontend:** Piggyback on the existing SSE status stream. No new endpoint or event type.
- **Refresh frequency:** On every scan cycle. The controller only updates the `StorageStatus` properties when values change by >1%, avoiding unnecessary SSE pushes.
- **Fallback (unavailable capacity):** Tile degrades to current display — tracked bytes as the main number, no percentage. No "N/A" shown.
- **Security:** No new attack surface. Reuses the existing authenticated SSH session. `df` is read-only. No user-controlled input in the command.

## Backend — Data Model

Add a `StorageStatus` component to the `Status` class in `src/python/common/status.py`:

```python
class StorageStatus(StatusComponent):
    local_total = StatusComponent._create_property("local_total")       # bytes, None if unknown
    local_used = StatusComponent._create_property("local_used")         # bytes, None if unknown
    remote_total = StatusComponent._create_property("remote_total")     # bytes, None if unknown
    remote_used = StatusComponent._create_property("remote_used")       # bytes, None if unknown
```

Register as `storage = BaseStatus._create_property("storage")` on `Status`, initialized via `__create_component(Status.StorageStatus)`.

The controller updates these properties after each scan cycle:
- **Local:** `shutil.disk_usage(local_path)` — runs inline, near-instant.
- **Remote:** `ssh df -B1 <remote_path>` via existing `Sshcp.shell()`. Parse total/used from the output.

Values start as `None`. Only updated on successful scan. If remote scan fails, remote values stay `None`.

## Backend — Serialization

Extend `SerializeStatusJson.status()` in `src/python/web/serialize/serialize_status.py` to include a `storage` block:

```json
{
  "server": { ... },
  "controller": { ... },
  "storage": {
    "local_total": 500107862016,
    "local_used": 325070000000,
    "remote_total": 2000398934016,
    "remote_used": 1150000000000
  }
}
```

Null values serialize as JSON `null`. No new SSE event type — the existing `StatusStreamHandler` already serializes and sends the full status on every change and on initial connection.

## Frontend — Data Model

Extend `IServerStatus` and `ServerStatusJson` in `src/angular/src/app/services/server/server-status.ts`:

```typescript
// IServerStatus
storage: {
    localTotal: number | null;
    localUsed: number | null;
    remoteTotal: number | null;
    remoteUsed: number | null;
};

// ServerStatusJson
storage: {
    local_total: number | null;
    local_used: number | null;
    remote_total: number | null;
    remote_used: number | null;
};
```

Defaults to all `null`. The `fromJson` parser maps snake_case to camelCase.

## Frontend — Dashboard Stats Service

Extend `DashboardStats` in `src/angular/src/app/services/files/dashboard-stats.service.ts`:

```typescript
remoteCapacityTotal: number | null;
remoteCapacityUsed: number | null;
localCapacityTotal: number | null;
localCapacityUsed: number | null;
```

Inject `ServerStatusService` alongside `ViewFileService`. Use `combineLatest` to merge both streams. When either emits, recompute all stats including capacity fields from the status stream.

## Frontend — Tile Display

Modify `src/angular/src/app/pages/files/stats-strip.component.html`.

**When capacity is available** (e.g. `remoteCapacityTotal` is not null):
- Main number: percentage (e.g. "65%")
- Subtitle: "of 185 GB"
- Sub-line: "120 GB used"
- Progress bar: width = used / total * 100

**When capacity is unavailable** (null):
- Falls back to current display: tracked bytes as main number, "Tracked" as unit
- Progress bar: remote/local ratio (current behavior)

Same pattern for both remote and local tiles. No changes to Download Speed or Active Tasks tiles.

## Testing

### Backend (Python)
- Unit test `StorageStatus` properties — set values, verify listener notification
- Unit test `SerializeStatusJson` — verify storage block serialization, null handling
- Unit test `df` output parsing — happy path, unexpected format, empty output
- Extend `RemoteScanner` tests — verify disk capacity collected after scan

### Frontend (Angular)
- Unit test `ServerStatus.fromJson` — verify storage fields parsed, null handling
- Unit test `DashboardStatsService` — verify capacity fields flow from status, `combineLatest` merging
- Unit test `StatsStripComponent` — verify percentage display when capacity present, verify fallback when null

No new E2E tests — capacity depends on a real SSH connection that E2E cannot provide.
