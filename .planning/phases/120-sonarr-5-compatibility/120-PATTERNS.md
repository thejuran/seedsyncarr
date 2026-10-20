# Phase 120: Sonarr 5 Compatibility - Pattern Map

**Mapped:** 2026-10-20
**Files analyzed:** 15 (6 fixture data files, 6 test-package files, 1 sanitizer script, 1 optional sink script, 1 evidence doc)
**Analogs found:** 11 / 15 (the fixture data files and the fixture loader have no in-repo precedent; there is no `src/python/tests/fixtures/` dir and no `Path(__file__)` loader in `tests/` today)

No runtime source file is expected to change (RESEARCH: no field SeedSyncarr reads differs on 5.x). If SON5-05 finds a Sonarr-5-caused failure, the fix files follow the 119.1 release runbook and are out of this map.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/tests/fixtures/sonarr5/manifest.json` | config (test data index) | static / file-I/O | none (RESEARCH §Sanitization field list) | no analog |
| `src/python/tests/fixtures/sonarr5/system_status.json` | test fixture | request-response body | `test_config_handler.py` L205 inline `{"version": "4.0.2"}` | partial |
| `src/python/tests/fixtures/sonarr5/queue_details_incomplete.json` | test fixture | request-response body | `test_arr_queue.py::_record` L113-131 (record shape) | partial |
| `src/python/tests/fixtures/sonarr5/queue_details_complete.json` | test fixture | request-response body | same as above | partial |
| `src/python/tests/fixtures/sonarr5/webhook_test.json` | test fixture | event body | `tests/integration/.../test_webhook.py` L50 inline `{"eventType": "Test"}` | partial |
| `src/python/tests/fixtures/sonarr5/webhook_download.json` | test fixture | event body | `test_webhook.py` L25-28 inline Download body | partial |
| `src/python/tests/unittests/test_sonarr5/__init__.py` | package marker | — | `tests/unittests/test_controller/__init__.py` (0 bytes) | exact |
| `src/python/tests/unittests/test_sonarr5/fixtures.py` | utility (test helper) | file-I/O (read-only) | none; RESEARCH §Code Examples "Fixture loader" | no analog |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py` | test | batch scan (file-I/O) | `test_arr_queue.py::test_no_secret_in_logs` L569+ (secret-absence assertions) | partial |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` | test | request-response | `tests/unittests/test_web/test_handler/test_config_handler.py` L150-230 | exact |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py` | test | request-response replay through worker thread | `test_arr_queue.py` L106-200 + `test_completion_gate.py` L131-205, L439-464 | exact |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_webhook.py` | test | event-driven (inbound HTTP) | `tests/integration/test_web/test_handler/test_webhook.py` + `test_webhook_handler.py` L207-296 + `test_webhook_manager.py` L100-136 | exact |
| `.planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py` | utility (operator script) | transform (file-I/O) | `.planning/phases/119.1-.../119.1-extract_secrets.py` | role-match |
| `.planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py` (optional, if the sink body is kept as a file rather than inline in the plan) | utility (disposable HTTP server) | request-response | `test_arr_queue.py::TrickleHandler` L33-66 | role-match |
| `.planning/phases/120-sonarr-5-compatibility/120-SON5-EVIDENCE.md` | evidence doc | — | `.planning/phases/119.1-.../119.1-REL04-EVIDENCE.md` | exact |

## Pattern Assignments

### `src/python/tests/unittests/test_sonarr5/__init__.py` (package marker)

**Analog:** `src/python/tests/unittests/test_controller/__init__.py` is an empty file (0 bytes). Create it empty. Tests import absolutely from the `src/python` root (`pyproject.toml` `[tool.pytest.ini_options] pythonpath = ["."]`), e.g. `from tests.unittests.test_sonarr5.fixtures import fixture_bytes`.

---

### `src/python/tests/unittests/test_sonarr5/fixtures.py` (utility, read-only file-I/O)

**Analog:** none in repo. Use RESEARCH §Code Examples verbatim:

```python
import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sonarr5"

def fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()

def fixture_json(name: str):
    return json.loads(fixture_bytes(name))
```

`parents[2]` from `tests/unittests/test_sonarr5/fixtures.py` is `tests/`, so the path resolves to `tests/fixtures/sonarr5/`. Add a `manifest()` helper (`fixture_json("manifest.json")`) and a `tested_version()` helper that returns the manifest's recorded build so the other tests never hardcode `5.0.0.2701` (D-08). Read-only: the CI container bind-mounts `src/python` at `/src` with `read_only: true` (`src/docker/test/python/compose.yml` L10-13), so nothing may write next to the fixtures.

---

### `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` (test, request-response) — SON5-01

**Analog:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`

**Imports** (L1-9):
```python
import json
import socket
import unittest
from unittest.mock import MagicMock, patch

import requests

from common import Config, ConfigError
from web.handler.config import ConfigHandler
```

**setUp with a real Config** (L150-156):
```python
class TestConfigHandlerTestSonarrConnection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.sonarr.enabled = False
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        self.config.sonarr.sonarr_api_key = "testapikey123"
        self.handler = ConfigHandler(self.config)
```

**Success-with-version pattern** (L214-229), feed the fixture instead of `{"version": "4.0.2"}`:
```python
@patch('web.handler.config.requests')
@patch('web.handler.config.socket')
def test_sonarr_success_returns_version(self, mock_socket, mock_requests):
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
    mock_socket.gaierror = socket.gaierror
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"version": "4.0.2"}
    mock_requests.get.return_value = mock_response
    mock_requests.ConnectionError = requests.ConnectionError
    mock_requests.Timeout = requests.Timeout
    response = self.handler._ConfigHandler__handle_test_sonarr_connection()
    body = json.loads(response.body)
    self.assertTrue(body["success"])
    self.assertEqual("4.0.2", body["version"])
```
Adaptation: `mock_response.json.side_effect = lambda: json.loads(fixture_bytes("system_status.json"))` (raw bytes, parsed only the way `requests` would). Assert `body["version"] == tested_version()` and that it starts with `"5."`. Also assert `mock_requests.get` was called with a URL ending `/api/v3/system/status` (handler L157-162: `"{}/api/v3/system/status".format(url)`, `headers={"X-Api-Key": api_key}`, `timeout=10`, `allow_redirects=False`).

**Private-IP limitation companion test** (L188-196), use a docker-network address such as `172.19.0.6`:
```python
@patch('web.handler.config.socket')
def test_sonarr_rejects_private_ip(self, mock_socket):
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
    mock_socket.gaierror = socket.gaierror
    self.config.sonarr.sonarr_url = "http://sonarr.local:8989"
    response = self.handler._ConfigHandler__handle_test_sonarr_connection()
    body = json.loads(response.body)
    self.assertFalse(body["success"])
    self.assertIn("private", body["error"])
```
Name it so it reads as documented current behavior (D-02, deferred to Reliability), e.g. `test_docker_network_url_rejected_by_lan_guard_known_limitation`, and assert `requests.get` is never called. Optional CGNAT companion: `100.64.0.1` passes `_validate_url` (TestValidateUrl at L498+ shows the `_validate_url` call style). Use a documentation-range or CGNAT example, never the real Tailscale IP.

Note: the handler rate-limits test-connection at 5 per 60 s (`TestConfigHandlerRateLimit` L468). A fresh `ConfigHandler` per test in `setUp` keeps the counter clean.

---

### `src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py` (test, replay through real client + gate) — SON5-02

**Analogs:** `src/python/tests/unittests/test_controller/test_arr_queue.py` (client) and `test_completion_gate.py` (gate).

**Imports** (test_arr_queue.py L1-19, test_completion_gate.py L1-22). Reuse helpers by import, as `test_completion_gate.py` already does:
```python
from controller.arr_queue import FETCH_DONE, ArrQueueClient, ArrTarget, QueueRecord
from controller.completion_gate import CompletionGate, Verdict
from tests.unittests.test_controller.test_arr_queue import (
    FakeClock, _bind_exceptions, _response, settle,
)
```
(`test_completion_gate.py` L17-22 imports `settle`/`start_trickle_server` from `test_arr_queue` the same way.)

**Mock response with raw chunks** (test_arr_queue.py L134-143):
```python
def _response(status=200, chunks=None):
    resp = MagicMock()
    resp.status_code = status
    resp.iter_content.side_effect = lambda chunk_size=None: iter(chunks or [])
    return resp

def _json_chunks(payload, parts=2) -> List[bytes]:
    raw = json.dumps(payload).encode("utf-8")
    ...
```
Do NOT use `_json_chunks` for fixtures (it re-serializes). Chunk the raw bytes: `[raw[i:i + 4096] for i in range(0, len(raw), 4096)]` (RESEARCH anti-pattern: never `json.dumps(json.load(f))`).

**Client setUp with a mocked context** (test_arr_queue.py L171-187):
```python
class BaseArrQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.logger = MagicMock()
        self.context.logger.getChild.return_value = self.logger
        cfg = self.context.config
        cfg.sonarr.enabled = True
        cfg.sonarr.sonarr_url = SONARR_URL
        cfg.sonarr.sonarr_api_key = API_KEY
        cfg.radarr.enabled = False
        ...
        self.clock = FakeClock()
        self.client = ArrQueueClient(self.context, clock=self.clock)
        self.sonarr = ArrTarget("Sonarr", "sonarr", SONARR_URL, API_KEY)

    def tearDown(self):
        for code in ("sonarr", "radarr"):
            settle(self.client, code)
```
Set `cfg.radarr.enabled = False` so only Sonarr is a target. Use the `.invalid`/`.example` placeholder URL and a non-32-hex key string (the existing `API_KEY = "s3cr3t-api-key-0123456789abcdef"` at L22 is fine).

**Normalization assertion** (test_arr_queue.py L239-262), the "fixture parses to `QueueRecord(... True, None)`" check:
```python
@patch("controller.arr_queue.requests")
class TestArrQueueFetch(BaseArrQueueTestCase):
    def test_start_fetch_then_poll_returns_records_on_200_list(self, mock_requests):
        resp = _response(200, _json_chunks(payload, 2))
        _bind_exceptions(mock_requests)
        mock_requests.get.return_value = resp
        fid = self.client.start_fetch(self.sonarr)
        self.assertTrue(settle(self.client, "sonarr"))
        outcome = self.client.poll("sonarr")
        self.assertEqual(FETCH_DONE, outcome.state)
        self.assertEqual([QueueRecord("Show.S01E01.mkv", "ABC123", "completed", 0, True, None), ...], outcome.records)
```
Expected values come from the fixture (`os.path.basename(outputPath)`, `downloadId`, `sizeleft`), never hardcoded release names.

**Unavailable scenarios** to copy for negatives: `test_fetch_unavailable_on_non_200` (L336), `..._on_connection_error` (L347), `..._on_invalid_json` (L364). Use `_bind_exceptions(mock_requests)` (L146-149) before setting `side_effect = requests.ConnectionError(...)`.

**Gate replay pattern** (test_completion_gate.py L181-205, "obsession replay"):
```python
def test_obsession_replay_completed_proves(self):
    self.client.responses["radarr"] = [_rec(ROOT, "ABC", "downloading", 800430078)]
    _decide(self.gate, {ROOT: SIZE})
    self.client.responses["radarr"] = [_rec(ROOT, "ABC", "completed", 0)]
    self.at(31)
    verdict = _decide(self.gate, {ROOT: SIZE})[ROOT]
    self.assertTrue(verdict.proven)
    self.assertFalse(verdict.held)
    self.assertEqual({}, self.gate.holds)
```
And step 1 asserts `HOLD("still_downloading")` plus `self.gate.holds == {ROOT: "still_downloading"}` (L188-193). `HOLD = Verdict.hold` (L128).

**Real client inside the gate** (test_completion_gate.py L439-464, `TestRealClientNonBlocking`): `self.gate = CompletionGate(self.context, self.client)` with `self.client = ArrQueueClient(self.context)`. For the replay, pass the same clock to both: `ArrQueueClient(ctx, clock=clock)` and `CompletionGate(ctx, client, clock=clock)` (`CompletionGate.__init__` signature, `completion_gate.py` L126-127). Two pitfalls:
- `FakeClock` in `test_arr_queue.py` (L106-111) is **callable**; the one in `test_completion_gate.py` (L91-93) is not (the gate base wraps it in `lambda: self.clock.now`). Import the callable one.
- The real client fetches on a worker thread, so `_decide` (two back-to-back `evaluate` calls, L111-114) is not enough. Do `gate.evaluate(c)`, then `settle(client, "sonarr")`, then `gate.evaluate(c)`. Advance the clock past `CompletionGate.REFRESH_INTERVAL_SECS` (30.0, `completion_gate.py` L123) before swapping in the complete fixture, as `self.at(31)` does.

**Negative precedents to mirror with captured records:**
- No matching basename gives `no_queue_entry`: `test_zero_candidates_no_queue_entry` L210-212.
- Unavailable never proves even with a cached proof: `test_cached_proof_not_used_while_any_enabled_arr_unavailable` L570-574 (prove, `at(31)`, make fetch fail, assert `HOLD("sonarr_unavailable")`).
- Season pack, one record downloading: `test_sonarr_per_episode_one_downloading_still_downloading` L227-232.
- Mixed snapshot (X incomplete, unrelated Z complete) keeps X held: build by concatenating the fixture's X record with a modified copy (only `outputPath` basename and `downloadId` changed). Load with `fixture_json`, re-dump with `json.dumps(...).encode()` only for these synthetic variants and say so in a comment.

---

### `src/python/tests/unittests/test_sonarr5/test_sonarr5_webhook.py` (test, inbound event) — SON5-03

**Analog 1 (web layer, preferred):** `src/python/tests/integration/test_web/test_handler/test_webhook.py`
```python
from tests.integration.test_web.test_web_app import BaseTestWebApp

class TestWebhookIntegration(BaseTestWebApp):
    @property
    def _webhook_manager_mock(self):
        return self.web_app_builder.webhook_handler._WebhookHandler__webhook_manager

    def test_sonarr_download_enqueues_via_web_layer(self):
        resp = self.test_app.post_json("/server/webhook/sonarr", body)
        self.assertEqual(200, resp.status_int)
        self._webhook_manager_mock.enqueue_import.assert_called_once_with(
            "Sonarr", "Show.S01E01-GROUP",
            provenance="eventType=Download, episodeFile.sourcePath"
        )
```
(L6-34). Replace `post_json(..., body)` with `self.test_app.post("/server/webhook/sonarr", params=fixture_bytes("webhook_download.json"), content_type="application/json")` so raw bytes go through. `BaseTestWebApp` (`tests/integration/test_web/test_web_app.py` L13-62) uses a **real** `Config()` at `self.context.config` and a `MagicMock()` webhook manager. Secrets are toggled the way `TestWebhookFailClosed._set_require_secret` does (L69-72): `self.context.config.general.webhook_secret = ...`, `...webhook_require_secret = ...`. `test_require_secret_on_with_secret_runs_hmac` (L91-97) shows the 401 on a missing signature with `expect_errors=True`.

Response text: the Test path returns body `"Test OK"` (`web/handler/webhook.py` L141-143); Download returns `"OK"` (L171).

**Analog 2 (HMAC helper):** `src/python/tests/unittests/test_web/test_webhook_handler.py` L18-20:
```python
def _compute_hmac(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
```
Header name is `X-Webhook-Signature` (`webhook.py` L96). Via webtest: `self.test_app.post(url, params=raw, content_type="application/json", headers={"X-Webhook-Signature": _compute_hmac(secret, raw)})`. Copy the helper locally (it is private to that module), or import it.

**Analog 3 (real manager, exact-one-file):** `src/python/tests/unittests/test_controller/test_webhook_manager.py`
```python
def _lookup(*entries):
    result = {}
    for basename, path, root in entries:
        result.setdefault(basename.lower(), {})[path] = root
    return result
...
self.mock_context = MagicMock()
self.mock_context.logger = MagicMock()
self.manager = WebhookManager(context=self.mock_context)
...
name_to_paths = _lookup(
    ("ShowDir", "ShowDir", "ShowDir"),
    ("Episode.S01E01.mkv", "ShowDir/Episode.S01E01.mkv", "ShowDir"),
)
self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
result = self.manager.process(name_to_paths)
self.assertEqual([("ShowDir", "Episode.S01E01.mkv")], result)
```
(L7-15, L21-24, L122-136). Feed `basename(fixture episodeFile.sourcePath)` into `enqueue_import`, build the lookup from the fixture root plus decoys (sibling episode, near-identical release name), and assert the result is exactly one `(root, child)` tuple. Ambiguity precedent: `test_ambiguous_name_across_roots_is_rejected_with_one_warning` L186.

---

### `src/python/tests/unittests/test_sonarr5/test_sonarr5_fixture_hygiene.py` (test, batch scan) — SON5-04

**Analog (partial):** `test_arr_queue.py::test_no_secret_in_logs` L569-600 shows the repo's secret-absence style: drive every scenario, then assert the secret never appears in the captured text. There is no existing file-scanning hygiene test, so the scanner rules come from RESEARCH §Sanitization step 3.

Structure to follow (unittest class, stdlib only: `json`, `re`, `ipaddress`, `pathlib`):
- Iterate `sorted(FIXTURE_DIR.glob("*.json"))`; use `self.subTest(file=p.name)` per file so one failure names the file.
- Patterns: `\b[0-9a-f]{32}\b` (case-insensitive), IPv4 literals checked with `ipaddress.ip_address` against the allowlist (`127.0.0.1`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), `/home/` not followed by `user/`, `/volume1/`, `/Users/`, URL hosts whose TLD is not `.invalid`/`.example`/`.test`/`localhost`/`example.com|org|net`, `@` email tokens, `X-Api-Key`/`apikey=`.
- **Scanner self-tests on inline strings** (RED-first): a separate `TestScanner` class feeds known-dirty strings (a fake 32-hex token, `10.1.2.3`, `/home/alice/`) and asserts each is flagged, so the guard is proven to bite without committing a dirty file.
- Manifest checks, per D-08: every non-manifest `*.json` has exactly one manifest entry; `sonarr_version` matches `^5\.\d+\.\d+\.\d+$` (not a hardcoded `5.0.0.2701`); `system_status.json`'s `version` equals its manifest entry's `sonarr_version`; non-empty `scenario`, `captured_at`, `endpoint_or_event`; `sanitized is True`; `source == "live"` (fails while Wave-1 placeholders remain); the two queue fixtures share the target `downloadId`, with the target not completed in one and `completed`/`sizeleft == 0` in the other.
- Failure messages must name the file and pattern only, never echo the matched value (mirrors the 119.1 hygiene rule of "names and counts only").

---

### Fixture data files (`system_status.json`, `queue_details_*.json`, `webhook_*.json`, `manifest.json`)

No in-repo analog. Shape references:
- Queue record keys match `test_arr_queue.py::_record` L113-131 (`id`, `title`, `size`, `trackedDownloadState`, `protocol`, `outputPath`, `downloadId`, `status`, `sizeleft`), plus the Sonarr 5 fields listed in RESEARCH §Verified facts. Lowercase `sizeleft` is what Sonarr 5 emits.
- Download body: `episodeFile.sourcePath` is the only read field (`test_webhook.py` L25-28); the full `WebhookImportPayload` key list is in RESEARCH.
- Wave-1 placeholders carry `"source": "placeholder"` and `"scenario": "placeholder — replaced by live capture"` in the manifest. Use placeholder values from RESEARCH (`/home/user/v5test/...`, `/data/torrents/...`, `http://sonarr.example.invalid:8989`, `Indexer (Prowlarr)`, 40-hex `DOWNLOADID...`-style id). Path basenames must be preserved exactly from the capture.

---

### `.planning/phases/120-sonarr-5-compatibility/120-sanitize_fixtures.py` (operator script, transform)

**Analog:** `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-extract_secrets.py`

**Module docstring with usage and hygiene contract** (L1-19): state the invocation, what goes to stdout vs stderr, and that values are never printed:
```python
"""Read-only, value-free secret extractor for count-only log checks.

Usage (stdin script inside the app image, config dir mounted read-only at /c):
    python3 - < 119.1-extract_secrets.py > <0600 values file> 2> <fields file>
...
STDERR carries only field NAMES and counts:
    FIELDS <names> N=<set fields> LINES=<value lines written>
On any exception it prints only `ERROR <ExceptionClassName>` to stderr and
exits 3; exception messages are never printed ...
"""
```

**main() + fail-closed entrypoint** (L67-74):
```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - class name only, never the message
        sys.stderr.write("ERROR {}\n".format(type(exc).__name__))
        sys.exit(3)
```

**Value-shape guard** (L56-58): reject unexpected shapes instead of writing them:
```python
for line in lines:
    if "\n" in line or line == "":
        raise ValueError("unexpected value shape")
```

Adaptation for 120: args are `<raw file> <mapping json (0600, uncommitted)> <out file>`; apply ordered `str.replace` for each mapping key on the decoded text; `json.loads` to prove still-valid JSON; write `json.dumps(obj, indent=2, ensure_ascii=False) + "\n"`; stderr reports only `REPLACED <n> placeholders=<placeholder names>` and a count of residual mapping keys (must be 0), never the keys themselves. Stdlib only, so it runs on the NAS host `python3` or inside the 1.7.6 image (RESEARCH §Package audit). Second precedent for the "stdin script inside the image" style: `.planning/phases/118-durable-state/118-05-gen_fixtures.py` L1-8.

---

### `.planning/phases/120-sonarr-5-compatibility/120-webhook_sink.py` (optional, disposable HTTP sink)

**Analog:** `test_arr_queue.py::TrickleHandler` / `start_trickle_server` L33-81:
```python
class TrickleHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server naming)
        ...
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - silence the handler
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0), TrickleHandler)
```
Adaptation: `do_POST` reads exactly `Content-Length` bytes (cap at 1 MB like `_WEBHOOK_MAX_BODY_BYTES`, `webhook.py` L19), writes them with `os.open(path, O_WRONLY|O_CREAT|O_EXCL, 0o600)` to a timestamped file, returns 200 `OK`. Keep `log_message` silenced so no body or header is printed. Bind `0.0.0.0:8080` in the container (no published port).

---

### `.planning/phases/120-sonarr-5-compatibility/120-SON5-EVIDENCE.md` (evidence doc)

**Analog:** `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-REL04-EVIDENCE.md`
- Header L1-11: tree/commit recorded, date, and an explicit **Hygiene** paragraph ("only test names, exception class names and counts are recorded; no secret value...").
- `## ` per gate, `### Step N:` per live step (L478-614 smoke-test layout), each with a fenced `$ command` / result block.
- Count-only exact-secret check format (L770-795):
```
$ grep -cFf $SECRETS_DIR/values $T/log; echo rc=$?
container log vs values: count=0 rc=1
```
For 120: one section per SON5-01..05, each recording the Sonarr build from `system/status.version` before and after (D-07), `<nas-tailscale-ip>` in place of the address (D-02), quoted log lines scoped to the capture window, and the final "verified builds" statement (D-09).

## Shared Patterns

### Mocked context + child logger
**Source:** `test_arr_queue.py` L172-175, `test_completion_gate.py` L134-137
**Apply to:** queue and gate tests
```python
self.context = MagicMock()
self.logger = MagicMock()
self.context.logger.getChild.return_value = self.logger
```

### Patching `requests` and re-binding real exception classes
**Source:** `test_arr_queue.py` L146-149; `test_config_handler.py` L206-209
**Apply to:** system-status and queue tests
```python
mock_requests.RequestException = requests.RequestException
mock_requests.ConnectionError = requests.ConnectionError
mock_requests.Timeout = requests.Timeout
```
Patch target is the module under test: `@patch("controller.arr_queue.requests")`, `@patch('web.handler.config.requests')`, `@patch('web.handler.config.socket')` (with `mock_socket.gaierror = socket.gaierror`).

### Raw bytes, never re-serialized
**Apply to:** all fixture-consuming tests. Load via `fixture_bytes`; chunk for `iter_content`; `post(params=raw)` for webtest; `json.loads(raw)` only where the production code itself parses (the `response.json()` mock).

### Version is read, not hardcoded (D-08)
**Apply to:** system-status test, hygiene test, evidence doc. Source of truth is the manifest entry's `sonarr_version`; tests assert the `^5\.` shape and equality with the fixture.

### Count-only secret handling on the NAS
**Source:** `119.1-04-PLAN.md` L82 and L130 (fail-closed rule), `119.1-REL04-EVIDENCE.md` L770-795
**Apply to:** sanitizer run, L4 exact-secret check, capture commands. The values file must be non-empty with the expected line count, otherwise abort; `rc=1` with count 0 is the only PASS, `rc=2` aborts; delete the temp dir afterwards; `umask 077` (D-13).

### Docstring-led test classes
**Source:** `test_webhook.py` L7-17, `test_webhook_handler.py` L23-31
**Apply to:** every new test class. One docstring naming the requirement (SON5-0x) and the recorded Sonarr build source.

## Conventions

Derived with `gsd-tools verify conventions --derive --scope src/python` (the `src/python/tests` scope returned `skipped: no-app-files`).

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| file-name casing | none (other 45 / snake 42 / camel 29) | 39% | 0.985 | contested hotspot |
| identifier casing | none (camel 426 / Pascal 289 / CONSTANT 47) | 54% | 0.613 | contested hotspot |
| export style | cjs | 100% (34 files, JS tooling only) | 0 | named contract (not relevant to Python) |
| import style | cjs | n=2 | — | insufficient data |
| py wildcard import | explicit | 100% | 0 | named contract |
| py import relativity | none (relative 49 / absolute 28) | 64% | 0.946 | contested hotspot |

**Contested hotspots (author's choice):** match the local directory. In `src/python/tests/**` every file is `test_<snake>.py`, classes are `TestPascal`, helpers are `_snake`, and imports are **absolute** from the `src/python` root (`from controller.arr_queue import ...`, `from tests.unittests.test_controller.test_arr_queue import ...`); relative imports belong to the runtime packages. Same idea as the CJS/SDK dual-resolver split (`bin/lib/**` CJS vs `sdk/src/**` ESM): each half is consistent within its own directory and only contested repo-wide. Explicit imports only, no wildcards. `ruff check src/python/` runs whole-tree in CI.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tests/fixtures/sonarr5/manifest.json` | config | static | No fixture directory or manifest exists in `src/python/tests/` |
| `tests/fixtures/sonarr5/*.json` (5 files) | test data | static | All current tests build payloads inline; shape refs given above |
| `tests/unittests/test_sonarr5/fixtures.py` | utility | file-I/O | No test reads files relative to `__file__`; use RESEARCH loader |
| Hygiene scanner rules | test | batch | No file-scanning guard exists; rules from RESEARCH §Sanitization |

## Metadata

**Analog search scope:** `src/python/tests/**` (unittests, integration, helpers), `src/python/web/handler/{config,webhook}.py`, `src/python/controller/{arr_queue,completion_gate,webhook_manager}.py`, `.planning/phases/118-*`, `119-*`, `119.1-*`, `src/docker/test/python/compose.yml`, `src/python/pyproject.toml`
**Files scanned:** 18
**Pattern extraction date:** 2026-10-20
