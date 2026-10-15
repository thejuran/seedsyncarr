"""
Sonarr/Radarr download-queue client used as completion evidence.

Fetches GET {url}/api/v3/queue/details for every enabled arr and normalizes
each queue entry into a QueueRecord. All HTTP work runs on a daemon worker
thread ("ArrQueueFetch-<code>"); the caller never waits for it.

Thread model: every public method of ArrQueueClient is called only on the
controller thread. start_fetch() spawns a worker and returns at once; poll()
reads the worker's posted result from a per-target handoff slot and returns at
once. The handoff slot (guarded by a leaf lock that is taken alone, never held
across I/O or logging and never while any controller lock is held) is the only
state shared with workers. At most one worker per target is ever alive: a
worker blocked in a read that cannot be interrupted (urllib3 waits for a full
chunk on a Content-Length body) is reported overrun after FETCH_DEADLINE_SECS
and abandoned, and no new worker is started for that target until it exits.

The api key, URL, request headers and response bodies are never logged.
"""

import hashlib
import hmac
import json
import os
import threading
import time
import urllib.parse
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

import requests

from common import Context, sanitize_log_value


FETCH_IDLE = "idle"
FETCH_PENDING = "pending"
FETCH_DONE = "done"
FETCH_OVERRUN = "overrun"

DEFECT_MISSING_DOWNLOAD_ID = "missing_download_id"
DEFECT_BAD_STATUS = "bad_status"
DEFECT_BAD_SIZELEFT = "bad_sizeleft"


# Per-process random secret for the API-key change-detection fingerprint (an
# HMAC, not a stored password hash). It only has to be stable within one
# process, because the fingerprint is compared in memory and never persisted
# or logged.
_FINGERPRINT_SECRET = os.urandom(32)


class ArrTarget(NamedTuple):
    label: str
    code: str
    url: str
    api_key: str

    @property
    def identity(self) -> Tuple[str, str, str]:
        """
        Configuration identity: (code, normalized url, key fingerprint).
        The fingerprint lets a rotated key be detected without keeping or
        comparing the raw key; it is never logged.
        """
        fingerprint = hmac.new(_FINGERPRINT_SECRET, self.api_key.encode("utf-8"),
                               hashlib.sha256).hexdigest()[:16]
        return self.code, self.url.rstrip("/"), fingerprint


class QueueRecord(NamedTuple):
    basename: Optional[str]
    download_id: Optional[str]
    status: Optional[str]
    sizeleft: Optional[float]
    valid: bool
    defect: Optional[str]


class FetchOutcome(NamedTuple):
    state: str
    fetch_id: Optional[int]
    records: Optional[List[QueueRecord]]


class _Fetch:
    """The current (or abandoned) fetch for one target code. Controller-thread only."""
    __slots__ = ("thread", "fetch_id", "started", "abandoned", "label")

    def __init__(self, thread: threading.Thread, fetch_id: int, started: float, label: str):
        self.thread = thread
        self.fetch_id = fetch_id
        self.started = started
        self.abandoned = False
        self.label = label


class _Unattributable(Exception):
    """A queue entry that cannot be attributed to any root."""


def _basename(output_path: str) -> Optional[str]:
    stripped = output_path.rstrip("/\\")
    if not stripped:
        return None
    name = stripped.replace("\\", "/").rsplit("/", 1)[-1]
    return name or None


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_record(rec) -> Optional[QueueRecord]:
    """
    Normalize one queue entry. Returns None when the entry cannot be attributed
    to any root (not an object, or an outputPath that is present but not a
    string); the caller then rejects the whole snapshot. Entries with missing or
    ill-typed completion fields are kept with valid=False and a defect code.
    """
    if not isinstance(rec, dict):
        return None
    if "outputPath" in rec and rec["outputPath"] is not None and not isinstance(rec["outputPath"], str):
        return None
    output_path = rec.get("outputPath")
    basename = _basename(output_path) if output_path else None

    defect = None
    download_id = rec.get("downloadId")
    if not isinstance(download_id, str) or not download_id:
        download_id = None
        defect = defect or DEFECT_MISSING_DOWNLOAD_ID
    status = rec.get("status")
    if not isinstance(status, str):
        status = None
        defect = defect or DEFECT_BAD_STATUS
    sizeleft = rec["sizeleft"] if "sizeleft" in rec and rec["sizeleft"] is not None else rec.get("sizeLeft")
    if not _is_number(sizeleft):
        sizeleft = None
        defect = defect or DEFECT_BAD_SIZELEFT
    return QueueRecord(basename, download_id, status, sizeleft, defect is None, defect)


class ArrQueueClient:
    QUEUE_PATH = "/api/v3/queue/details"
    TIMEOUT = (3.05, 10)
    MAX_RESPONSE_BYTES = 8 * 1024 * 1024
    FETCH_DEADLINE_SECS = 20.0
    CHUNK_BYTES = 64 * 1024

    def __init__(self, context: Context, clock: Callable[[], float] = time.monotonic):
        self.__context = context
        self.__clock = clock
        self.logger = context.logger.getChild("ArrQueueClient")
        self.__fetches: Dict[str, _Fetch] = {}
        self.__results: Dict[str, Tuple[int, Optional[List[QueueRecord]]]] = {}
        self.__results_lock = threading.Lock()
        self.__fetch_seq = 0

    def enabled_targets(self) -> List[ArrTarget]:
        """Enabled arrs, Sonarr first. Read from config on every call."""
        config = self.__context.config
        targets = []
        if config.sonarr.enabled:
            targets.append(ArrTarget("Sonarr", "sonarr",
                                     config.sonarr.sonarr_url or "",
                                     config.sonarr.sonarr_api_key or ""))
        if config.radarr.enabled:
            targets.append(ArrTarget("Radarr", "radarr",
                                     config.radarr.radarr_url or "",
                                     config.radarr.radarr_api_key or ""))
        return targets

    def start_fetch(self, target: ArrTarget) -> Optional[int]:
        """
        Start a queue fetch for `target` on a daemon worker and return its id.

        Returns immediately. The worker's result is delivered through poll(); a
        worker blocked in urllib3 waiting for a 64 KiB chunk that a trickling
        Content-Length body never fills cannot be interrupted, so poll()
        abandons it after FETCH_DEADLINE_SECS and its target stays reported as
        not startable until it exits.

        Returns None without starting anything when the URL is not http/https
        or when a worker for the same target is still alive (abandoned or not).
        """
        scheme = urllib.parse.urlsplit(target.url).scheme.lower()
        if scheme not in ("http", "https"):
            self.logger.warning("%s queue check skipped: URL must use http or https", target.label)
            return None
        code = target.code
        prior = self.__fetches.get(code)
        if prior is not None and prior.thread.is_alive():
            self.logger.debug("%s queue fetch from a previous attempt is still in flight; "
                              "not starting another", target.label)
            return None

        self.__fetch_seq += 1
        fetch_id = self.__fetch_seq
        started = self.__clock()
        with self.__results_lock:
            stale = self.__results.pop(code, None)
        if stale is not None:
            self.logger.debug("%s queue fetch: discarding stale result", target.label)
        worker = threading.Thread(name="ArrQueueFetch-" + code, target=self.__fetch_worker,
                                  args=(target, fetch_id, started), daemon=True)
        self.__fetches[code] = _Fetch(worker, fetch_id, started, target.label)
        worker.start()
        return fetch_id

    def poll(self, code: str) -> FetchOutcome:
        """
        Latest fetch state for `code`. Never blocks: takes the leaf handoff
        lock once and does no I/O. FETCH_DONE and FETCH_OVERRUN are each
        reported exactly once per fetch id.
        """
        with self.__results_lock:
            posted = self.__results.pop(code, None)
        f = self.__fetches.get(code)
        if posted is not None:
            if f is not None and not f.abandoned and posted[0] == f.fetch_id:
                del self.__fetches[code]
                return FetchOutcome(FETCH_DONE, posted[0], posted[1])
            label = f.label if f is not None else code
            self.logger.debug("%s discarded late queue result for an abandoned fetch (id %d)",
                              label, posted[0])
        if f is None:
            return FetchOutcome(FETCH_IDLE, None, None)
        if f.abandoned:
            if not f.thread.is_alive():
                del self.__fetches[code]
            return FetchOutcome(FETCH_IDLE, None, None)
        if self.__clock() - f.started > self.FETCH_DEADLINE_SECS:
            f.abandoned = True
            self.logger.warning("%s queue fetch exceeded the %.0f s deadline; treating as unavailable",
                                f.label, self.FETCH_DEADLINE_SECS)
            return FetchOutcome(FETCH_OVERRUN, f.fetch_id, None)
        if f.thread.is_alive():
            return FetchOutcome(FETCH_PENDING, f.fetch_id, None)
        # The worker may have posted its result and exited between the pop at
        # the top of this call and the liveness check above; re-check the slot
        # before declaring that it ended without a result.
        with self.__results_lock:
            late = self.__results.pop(code, None)
        del self.__fetches[code]
        if late is not None and late[0] == f.fetch_id:
            return FetchOutcome(FETCH_DONE, late[0], late[1])
        self.logger.warning("%s queue fetch ended without a result; treating as unavailable", f.label)
        return FetchOutcome(FETCH_DONE, f.fetch_id, None)

    def abandon(self, code: str) -> bool:
        """
        Abandon the outstanding fetch for `code` (if any): poll() never reports
        it and its late result is discarded. The worker is not stopped; it
        closes its own response when its read returns.
        """
        f = self.__fetches.get(code)
        if f is None or f.abandoned:
            return False
        f.abandoned = True
        self.logger.debug("%s queue fetch abandoned (id %d)", f.label, f.fetch_id)
        return True

    def in_flight(self, code: str) -> bool:
        """True while a worker for `code` is alive, abandoned or not."""
        f = self.__fetches.get(code)
        return f is not None and f.thread.is_alive()

    def __fetch_worker(self, target: ArrTarget, fetch_id: int, started: float):
        """Worker thread body. Never raises; posts exactly one result."""
        value: Optional[List[QueueRecord]] = None
        try:
            response = requests.get(target.url.rstrip("/") + self.QUEUE_PATH,
                                    headers={"X-Api-Key": target.api_key},
                                    timeout=self.TIMEOUT,
                                    allow_redirects=False,
                                    stream=True)
            try:
                value = self.__read_records(target, response, started)
            finally:
                response.close()
        except requests.RequestException as e:
            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
        except Exception as e:
            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
        finally:
            with self.__results_lock:
                self.__results[target.code] = (fetch_id, value)

    def __deadline_exceeded(self, target: ArrTarget, started: float) -> bool:
        if self.__clock() - started > self.FETCH_DEADLINE_SECS:
            self.logger.warning("%s queue fetch exceeded the %.0f s deadline; treating as unavailable",
                                target.label, self.FETCH_DEADLINE_SECS)
            return True
        return False

    def __read_records(self, target: ArrTarget, response, started: float) -> Optional[List[QueueRecord]]:
        """Bounded streamed read + validation. Runs on the worker thread."""
        if self.__deadline_exceeded(target, started):
            return None
        if response.status_code != 200:
            self.logger.warning("%s queue check failed: HTTP %d", target.label, response.status_code)
            return None

        buf = bytearray()
        for chunk in response.iter_content(chunk_size=self.CHUNK_BYTES):
            buf.extend(chunk)
            if len(buf) > self.MAX_RESPONSE_BYTES:
                self.logger.warning("%s queue response exceeded %d bytes; treating as unavailable",
                                    target.label, self.MAX_RESPONSE_BYTES)
                return None
            if self.__deadline_exceeded(target, started):
                return None

        try:
            payload = json.loads(bytes(buf))
        except (ValueError, UnicodeDecodeError) as e:
            self.logger.warning("%s queue check failed: %s", target.label, type(e).__name__)
            return None
        if not isinstance(payload, list):
            self.logger.warning("%s queue check failed: unexpected payload type %s",
                                target.label, type(payload).__name__)
            return None

        records: List[QueueRecord] = []
        try:
            for raw in payload:
                record = _to_record(raw)
                if record is None:
                    raise _Unattributable()
                records.append(record)
        except _Unattributable:
            self.logger.warning("%s queue snapshot rejected: unparseable record", target.label)
            return None

        for record in records:
            if not record.valid:
                self.logger.debug("%s queue record has defect %s for '%s'", target.label, record.defect,
                                  sanitize_log_value(record.basename or ""))
        return records
