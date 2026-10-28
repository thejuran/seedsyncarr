# Phase 125: LAN Connection Tests - Pattern Map

**Mapped:** 2026-10-27
**Files analyzed:** 5 (1 source, 2 test, 1 release-notes, 1 new sandbox script)
**Analogs found:** 5 / 5 (one is a self-analog: the function being edited is its own best style reference; one has no in-repo precedent and falls back to RESEARCH.md's verified reference implementation)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/python/web/handler/config.py` (`_validate_url`, `_test_arr_connection`) | controller (SSRF-guard validator inside a bottle route handler) | request-response | itself, pre-change (`config.py:58-88`, `137-158`) | exact (in-place classifier replacement, not a new file) |
| `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` (`TestValidateUrl`, `TestConfigHandlerTestSonarrConnection`/`...Radarr...`) | test | request-response | itself, pre-change (same file, `TestValidateUrl` class `526-653`; flip-pattern precedent `154-217`) | exact (extend in place) |
| `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` (`test_docker_network_url_rejected_by_lan_guard_known_limitation`, module docstring) | test | request-response | itself, pre-change (`1-12`, `76-94`) — **discovered during mapping, not named in CONTEXT/RESEARCH's file list but is the exact motivating-case regression test and WILL go red/wrong-direction if left untouched** | exact |
| `CHANGELOG.md` (new `## [Unreleased]` / 1.8.0-draft entry) | config (release-notes document, no runtime tier) | batch (static text edit) | `CHANGELOG.md:1-53` (`[1.7.6]` entry: heading, intro paragraph, `### Changed`/`### Fixed` bullets) | role-match (no existing "draft/Unreleased mid-milestone" entry in this repo; closest precedent is commit `401c3c8` adding a full `[1.4.0]` entry early — same heading/bullet shape, different timing) |
| New sandbox live-check script (D-09) — e.g. `.planning/phases/125-lan-connection-tests/125-livecheck.sh` | test (manual/live sandbox verification, not CI) | request-response (curl against `seedsyncarr-test`) | `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh`, `.planning/phases/123-startup-and-shutdown-lifecycle/123-teardown.sh` | exact (same `state.env` idiom, same restore-and-verify idiom, same digest-pin discipline) |

## Pattern Assignments

### `src/python/web/handler/config.py` (controller / validator, request-response)

**Analog:** itself, current body — the whole phase is a bounded in-place rewrite of one `@staticmethod`, not a new pattern import from elsewhere in the codebase.

**Imports pattern** (lines 1-19):
```python
import json
import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin

import requests
import bottle
from bottle import HTTPResponse

from common import Context, overrides, Config, ConfigError
from ..web_app import IHandler, WebApp
from ..serialize import SerializeConfig
from ..rate_limit import rate_limit

# Printable ASCII without space -- the only characters `requests` accepts in
# a header value without raising InvalidHeader, whose message would embed
# the raw key (122-14, CR-01).
_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")
```
`ipaddress` is already imported — no new import line needed for the classifier. Add the two new module-level constants (`_ALLOWED_PRIVATE_NETWORKS`, `_ALLOWED_LOOPBACK_PORTS`) directly below `_API_KEY_CHARS`, following the exact same "module-level `_SCREAMING_SNAKE` constant with a one-line rationale comment above it" convention already used here and confirmed elsewhere in the codebase (see **Shared Patterns → Module-level constant naming** below).

**Current implementation to replace** (lines 58-88) — this is the method body the plan's action section targets:
```python
    @staticmethod
    def _validate_url(url: str) -> str | None:
        """Validate URL for SSRF protection. Returns error string or None if valid.

        Known limitation: DNS rebinding (TOCTOU) — getaddrinfo resolves at validation
        time while requests.get resolves again at request time. A DNS rebinding attack
        could bypass this check. Mitigating this requires socket-level interception
        (e.g., ssrfpy or pysafecurl), which is out of scope for a homelab tool.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return "Only http and https URLs are allowed"

        hostname = parsed.hostname
        if not hostname:
            return "Invalid URL: no hostname"

        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                try:
                    addr = ipaddress.ip_address(ip_str)
                    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
                        return "URL resolves to a private/reserved IP address"
                except ValueError:
                    pass
        except socket.gaierror:
            return "Cannot resolve hostname"

        return None
```
**What must change, concretely:** the single `if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local: return "..."` line is replaced by a call into the ordered classifier from RESEARCH.md's Pattern 1 (already verified against Python 3.11.18/3.12.16 this session) — loopback-and-port gate first, then the five named `_ALLOWED_PRIVATE_NETWORKS`, then `is_global and not (reserved/multicast/link_local/unspecified)`, else a category-specific refusal. The `try/except ValueError` around `ip_address(ip_str)` and the outer `try/except socket.gaierror` stay exactly as-is — only the body of the inner `if` block changes shape. The `parsed.port` access needed for D-02's port gate must be read with its own `try/except ValueError` (Pitfall 1 — `.port` is lazily validated and independent of `.hostname`, which never raises), returning `"Invalid URL: invalid port"` in the existing "pure function returns an error string before any socket/network call" style already used by the scheme and hostname checks above it.

**Caller / integration point — the only call site, and where the port comes from** (lines 137-158, `_test_arr_connection`):
```python
    def _test_arr_connection(self, service_name: str, raw_url: str | None, api_key: str | None) -> HTTPResponse:
        """Shared logic for testing Sonarr/Radarr API connections."""
        if not raw_url or not raw_url.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} URL is required".format(service_name)}),
                content_type="application/json"
            )
        ...
        # SSRF protection: validate URL before making any outbound request
        error_msg = ConfigHandler._validate_url(raw_url.strip())
        if error_msg is not None:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": error_msg}),
                content_type="application/json"
            )
```
No change needed here — `_validate_url` stays a single pure call before any `requests` call, same signature, same "error string or None" contract. `_test_arr_connection` itself is unaware of port vs. IP classification; `urlparse(url).port` is read *inside* `_validate_url`, which already has `parsed` in scope.

**Error-handling / never-leak-the-key boundary** (lines 198-220) — unaffected by this phase, cited only because the new `ValueError`-from-`.port` failure mode (Pitfall 1) must NOT be allowed to propagate past this boundary the way the old code never touched `.port` at all:
```python
        except Exception as e:
            # requests embeds header values, including the API key, in
            # InvalidHeader and similar messages, so this boundary logs only
            # the exception type, never the message or a traceback
            # (122-14, CR-01; D-14 of 122-CONTEXT).
            self.logger.error(
                "Unexpected error testing %s connection (%s)",
                service_name, type(e).__name__
            )
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "An unexpected error occurred"}),
                content_type="application/json"
            )
```
This `try/except` wraps only `requests.get(...)` (starts after line 158) — `_validate_url` runs *before* it. The malformed-port `ValueError` must therefore be caught *inside* `_validate_url` itself (per Pitfall 1), not rely on this outer handler.

---

### `src/python/tests/unittests/test_web/test_handler/test_config_handler.py` (test, request-response)

**Analog:** itself, current body — the `socket.getaddrinfo`-stubbing harness is already exactly right for every new case; no new test infrastructure is needed.

**Harness / imports pattern** (lines 1-9):
```python
import json
import socket
import unittest
from unittest.mock import MagicMock, patch

import requests

from common import Config, ConfigError
from web.handler.config import ConfigHandler
```

**Core harness pattern — `TestValidateUrl`** (class starts line 526, representative case lines 538-543):
```python
class TestValidateUrl(unittest.TestCase):
    """Full-path coverage for the SSRF guard ConfigHandler._validate_url (COVMED-02).
    ...
    """

    @patch('web.handler.config.socket')
    def test_rejects_ipv4_private(self, mock_socket):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
        mock_socket.gaierror = socket.gaierror
        result = ConfigHandler._validate_url("http://host.example/")
        self.assertIn("private/reserved", result)
```
**This exact test must flip from reject to accept** under D-01 (`10.0.0.1` is now allowed) — this is the template for every "stub one resolved IP, call `_validate_url` directly (no handler, no bottle), assert on the returned string" case the planner adds. Nine existing assertions change outcome this way (full list in RESEARCH.md Pitfall 3); none need new mocking infrastructure, only new expected values and, for the two private-IP-port-8989/7878 handler-level tests below, an added `requests` mock.

**Flip-to-accept-with-mocked-requests pattern — `TestConfigHandlerTestSonarrConnection`** (lines 154-217): `setUp` (156-160), the test that must flip (192-200), and the already-correct sibling pattern to copy the `requests` mock from (202-217):
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

    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_sonarr_accepts_public_ip(self, mock_socket, mock_requests):
        mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        mock_socket.gaierror = socket.gaierror
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.2"}
        mock_requests.get.return_value = mock_response
        mock_requests.ConnectionError = requests.ConnectionError
        mock_requests.Timeout = requests.Timeout
        self.config.sonarr.sonarr_url = "http://sonarr.example.com:8989"
        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)
        self.assertTrue(body["success"])
```
`test_sonarr_rejects_private_ip` resolves to `127.0.0.1` **on Sonarr's own default port 8989** — exactly the case D-02 makes allowed. The flipped version needs the `@patch('web.handler.config.requests')` decorator and the `mock_requests.get`/`ConnectionError`/`Timeout` setup copied verbatim from `test_sonarr_accepts_public_ip`, because today's rejection short-circuits before any real `requests.get` call and the flipped assertion will reach it. The identical pair exists for Radarr at lines 314-338 (`test_radarr_rejects_private_ip` / `test_radarr_accepts_public_ip`, port 7878).

**D-04 replacement test (mixed-resolution, "any refused" premise):** `test_rejects_multi_address_when_any_private` (lines 616-624) loses its premise entirely under D-01 (`8.8.8.8` and `10.0.0.1` both become allowed). Copy its exact two-address-list-via-`getaddrinfo.return_value` shape but pair one now-allowed address with one still-refused address (RESEARCH.md's suggestion: `[8.8.8.8, 169.254.169.254]`) to keep D-04's fail-closed behavior covered.

---

### `src/python/tests/unittests/test_sonarr5/test_sonarr5_system_status.py` (test, request-response)

**Not named in CONTEXT.md/RESEARCH.md's file list, but discovered this session — it is the exact Phase-120-era "known limitation" regression test for the motivating case, and it will silently assert the OLD (wrong) behavior if not touched.**

**Analog:** itself, current body.

**Module docstring to update** (lines 1-12) — the two paragraphs describing the LAN-guard limitation as deferred must be rewritten now that this phase fixes it:
```python
"""Sonarr 5 Test Connection compatibility (SON5-01).

Feeds the recorded Sonarr 5 ``GET /api/v3/system/status`` body to the real
``ConfigHandler`` Test Connection path. The expected version always comes from
the fixture manifest (``fixtures.tested_version()``), never from a literal, so the
tests hold unchanged when the fixture is replaced by a newer capture (D-01, D-08).

The LAN-guard test records a known limitation rather than a fix: a Sonarr
reached by docker-network container name resolves to a private address, which
the SSRF guard rejects before Sonarr is contacted. Relaxing that guard is
deferred to the Reliability milestone (D-02).
"""
```

**The test that must flip from reject to accept** (lines 76-94):
```python
    @patch('web.handler.config.requests')
    @patch('web.handler.config.socket')
    def test_docker_network_url_rejected_by_lan_guard_known_limitation(self, mock_socket, mock_requests):
        """Known limitation (D-02, deferred to Reliability item 5).

        A Sonarr addressed by docker-network container name resolves to a
        private bridge address. The SSRF guard rejects it before any request is
        made. This documents current behavior; it is not a fix.
        """
        _resolve_to(mock_socket, "172.19.0.6")
        _bind_request_errors(mock_requests)
        self.config.sonarr.sonarr_url = "http://sonarr-v5:8989"

        response = self.handler._ConfigHandler__handle_test_sonarr_connection()
        body = json.loads(response.body)

        self.assertFalse(body["success"])
        self.assertIn("private", body["error"])
        mock_requests.get.assert_not_called()
```
This is the literal `http://sonarr-v5:8989` → `172.19.0.6` scenario named in LAN-01 and in the Phase 120 D-02 failure record. Under this phase it must become an accept assertion (rename away from `..._known_limitation`, e.g. `test_docker_network_url_accepted_by_lan_guard`, add a `mock_response`/`mock_requests.get.return_value` success stub using the existing `_bind_request_errors` helper already imported, and assert `body["success"]` true / `mock_requests.get.assert_called_once()`). The existing `_resolve_to`/`_bind_request_errors` module helpers (lines 31-38) are reused as-is.

**Already-correct precedent for the "allowed range, assert `_validate_url` returns None directly" shape** (lines 96-99) — copy this exact shape for the new allowed-range unit assertions if any land in this file rather than `test_config_handler.py`:
```python
    @patch('web.handler.config.socket')
    def test_cgnat_address_passes_url_validation(self, mock_socket):
        _resolve_to(mock_socket, _CGNAT_EXAMPLE_IP)
        self.assertIsNone(ConfigHandler._validate_url("http://{}:8990".format(_CGNAT_EXAMPLE_IP)))
```
This test (CGNAT `100.64.0.1`, D-01's "must not regress" range) already passes today and needs no change — it is the live proof that the CGNAT range was never touched by the old `is_private`-only guard and must stay untouched by the new classifier.

---

### `CHANGELOG.md` (config/release-notes, batch)

**Analog:** the existing per-version entry format — no in-repo precedent for a mid-milestone "Unreleased/1.8.0-draft" entry exists (checked: no `## [Unreleased]` heading anywhere in current `CHANGELOG.md`; the one historical case of adding an early entry, commit `401c3c8` "add [1.4.0] CHANGELOG entry", added a dated, numbered entry directly, not an `Unreleased` placeholder — this phase's case is different because other 1.8.0 phases haven't landed yet).

**Existing entry shape to copy (heading, intro paragraph, bullet-category structure)** (lines 1-12):
```markdown
# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.7.6] - 2026-10-15

A security release. Every container start printed the whole settings file,
secrets included, to the container log. This release stops that and closes
two related paths that could write credentials to the application log. There
are no transfer, import or UI changes over 1.7.5.

### Security
```
**What to add:** insert a new top section immediately under the `The format is based on...` line, before `## [1.7.6]`. Follow Keep a Changelog's own `## [Unreleased]` convention for the heading (no date yet — Phase 126 replaces it with `## [1.8.0] - <date>` per D-10), with a `### Changed` bullet using D-10's locked wording: "Test Connection now accepts local network and Docker container addresses, localhost only on 8989/7878, and metadata/link-local destinations stay blocked." Match the existing prose register (plain sentences, no marketing tone, user-facing not implementation-facing) demonstrated by the `[1.7.6]` and `[1.7.5]` entries already in the file.

---

### New sandbox live-check script (D-09) — role: test, request-response

**Analog:** `.planning/phases/120-sonarr-5-compatibility/120-teardown.sh` and `.planning/phases/123-startup-and-shutdown-lifecycle/123-teardown.sh` — both are the established "idempotent sandbox restore + verify" idiom this phase's much smaller D-09 check should reuse, not reinvent.

**Header / scope-declaration comment pattern** (120-teardown.sh lines 1-23, 123-teardown.sh lines 1-33) — both scripts open with a block comment stating: usage, what `state.env` keys mean, what a missing key implies, and an explicit scope boundary ("Production is never touched"). Copy this shape for the new script's header, stating D-09's actual scope: positive check on `seedsyncarr-test` against `http://sonarr-v5:8989` (no config change needed — it's already the baseline), negative check against `http://169.254.169.254` (one temporary `config/set`, then restore), production read-only.

**`state_get`/`fail` idiom** (120-teardown.sh lines 38-45):
```bash
FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }

state_get() {
  # Last KEY=value wins; values are plain tokens/paths written by the capture scripts.
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
```
123-teardown.sh additionally has a paired `state_set` (lines 71-75) for scripts that need to persist a flag across a later idempotent rerun — not needed for this phase's one-shot D-09 check, but available if the planner wants the negative-case value saved before the restore.

**Restore-and-verify-by-read-back idiom (the exact shape D-09's negative case needs)** (120-teardown.sh lines 62-75, the `sonarr_url` restore):
```bash
cur="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty' 2>/dev/null)"
if [ "$cur" != "$TARGET_URL" ]; then
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "{\"section\":\"sonarr\",\"key\":\"sonarr_url\",\"value\":\"$TARGET_URL\"}" \
    "$SSY/server/config/set"
  cur="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty' 2>/dev/null)"
fi
if [ "$cur" = "$TARGET_URL" ]; then
  echo "RESTORED sonarr_url ok"
else
  echo "RESTORED sonarr_url FAIL"
  fail sonarr_url
fi
```
This is the literal `config/get` → (conditionally) `config/set` → read-back-verify pattern RESEARCH.md's own Code Examples section already adapted for D-09 (set to the refused address, test-connection, restore, verify). Reuse it verbatim with `TARGET_URL="http://sonarr-v5:8989"` as the value being restored TO, matching 120-teardown.sh's own baseline exactly (confirms D-09's positive case needs no setup — only a GET to `/server/config/sonarr/test-connection`).

**Terminal convention (exit code / last line contract)** (120-teardown.sh lines 193-199, identical idiom in 123-teardown.sh lines 254-259):
```bash
if [ -z "$FAILED" ]; then
  echo "SANDBOX_RESTORED ok"
  exit 0
fi
echo "SANDBOX_RESTORED FAIL $FAILED"
exit 1
```
Keep this exact final-line contract (`SANDBOX_RESTORED ok` / `SANDBOX_RESTORED FAIL <comma-list>`, `exit 0`/`exit 1`) so any orchestration tooling that already greps for it keeps working unchanged.

**Image-pin digest discipline** (123-teardown.sh lines 196-215, `--final` branch) — not strictly needed for D-09 (which doesn't say this script does the deploy/pin-restore, only the functional check before and after), but the pattern to follow if the planner folds the "restore the sandbox image pin to its original value afterwards" step (D-09) into the same script: read the pin from `state.env` (`IMAGE_PIN_L0`), rewrite only the `image:` line via `awk` (inode-preserving edit, never `sed -i`), `compose pull` + `compose up -d`, then verify via `docker inspect --format '{{.Config.Image}}'`.

## Shared Patterns

### Module-level constant naming
**Source:** `src/python/web/handler/config.py:19` (`_API_KEY_CHARS`), `src/python/controller/controller.py:37-65` (`_AUTO_DELETE_MAX_REARMS`, `_AUTO_DELETE_TERMINAL_SKIPS = frozenset({...})`, `_PENDING_NOTICE_MAX`), `src/python/controller/auto_delete_manager.py:14-27` (`_VIDEO_EXTENSIONS = frozenset({...})`, `_AUTO_DELETE_BFS_NODE_LIMIT`), `src/python/web/serialize/serialize_config.py:8-19` (`_SENSITIVE_FIELDS`, `_ALWAYS_BLANK_FIELDS`)
**Apply to:** `_ALLOWED_PRIVATE_NETWORKS` and `_ALLOWED_LOOPBACK_PORTS` in `config.py`
```python
_AUTO_DELETE_TERMINAL_SKIPS = frozenset({"bfs_limit", "duplicate_basename"})
_VIDEO_EXTENSIONS = frozenset({
    ...
})
```
Every private, module-scope set/collection constant in this codebase is `_SCREAMING_SNAKE_CASE`, defined at module top (not class-nested), using `frozenset({...})` for membership-checked sets. `_ALLOWED_LOOPBACK_PORTS = frozenset({8989, 7878})` from RESEARCH.md's Pattern 1 already matches this exactly; `_ALLOWED_PRIVATE_NETWORKS` as a plain tuple of `ipaddress.ip_network(...)` objects (iterated, not membership-hashed) is the right shape since `ip_network` objects aren't hashable the same way plain values are for a `frozenset({8989, 7878})`-style check — keep it a `tuple`, as RESEARCH.md's own example already does.

### Never leak the API key into logs or error text (122-14, CR-01)
**Source:** `src/python/web/handler/config.py:208-216`
**Apply to:** any new refusal-message code path added inside `_validate_url`/`_test_arr_connection`
```python
        except Exception as e:
            self.logger.error(
                "Unexpected error testing %s connection (%s)",
                service_name, type(e).__name__
            )
```
D-07 explicitly requires the new refusal messages never echo the API key (hostname/IP echoing is fine, mirroring `_sanitize_redirect_location`'s existing precedent). No new code path in this phase touches the API key, so this is a "don't regress" constraint, not new code — but it governs message-string wording choices for the classifier's refusal branches.

### Pure-validator contract: return error string or `None`, never raise past the boundary
**Source:** `src/python/web/handler/config.py:58-88` (current `_validate_url`), reinforced by Pitfall 1's requirement that `.port` access gets its own `try/except ValueError`
**Apply to:** the rewritten `_validate_url` body
Every early-return branch in `_validate_url` returns a `str` error message or falls through to `return None` at the end — there is no exception-raising branch today, and the new `.port`-read line must preserve that invariant (catch `ValueError` locally, return a string) rather than letting an uncaught exception reach `_test_arr_connection`'s route dispatch, which — unlike the `requests.get` call — is NOT wrapped in a try/except at this call site.

### `socket.getaddrinfo` stub harness for every validator unit test
**Source:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py:538-543` and every other `@patch('web.handler.config.socket')` test in that file and in `test_sonarr5_system_status.py`
**Apply to:** every new/flipped test in both test files
```python
@patch('web.handler.config.socket')
def test_name(self, mock_socket):
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("<ip>", 0))]
    mock_socket.gaierror = socket.gaierror
    result = ConfigHandler._validate_url("http://host.example/")
```
This is the one and only resolution-stubbing idiom in the codebase for this code path; no alternative (real DNS, `dnspython`, etc.) is used or should be introduced. For port-dependent cases (D-02), vary the URL's own port (`"http://host.example:8989/"`) rather than the resolved IP, since the port comes from `urlparse`, not from `getaddrinfo`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `CHANGELOG.md` "Unreleased/1.8.0-draft" entry heading | config | batch | No prior mid-milestone draft-entry precedent in this repo's CHANGELOG (checked via `git log -- CHANGELOG.md`); fall back to Keep a Changelog's standard `## [Unreleased]` convention plus this repo's own per-version bullet/prose style (see Pattern Assignments above). Low risk: the heading text is cosmetic and Phase 126 (D-10) rewrites it to the final `## [1.8.0] - <date>` form anyway. |

## Metadata

**Analog search scope:** `src/python/web/handler/`, `src/python/tests/unittests/test_web/test_handler/`, `src/python/tests/unittests/test_sonarr5/`, `src/python/controller/`, `src/python/common/`, `src/python/web/serialize/`, `CHANGELOG.md`, `.planning/phases/120-sonarr-5-compatibility/`, `.planning/phases/123-startup-and-shutdown-lifecycle/`, repo-wide `git log -- CHANGELOG.md`
**Files scanned:** `config.py`, `test_config_handler.py`, `test_sonarr5_system_status.py`, `test_web_app_builder_logging.py` (confirmed unaffected, Pitfall 4 — patches `_validate_url` wholesale so needs no edits, only a build-verify pass), `arr_queue.py` (confirmed D-06 scope — never imports `_validate_url`), `controller.py`, `auto_delete_manager.py`, `serialize_config.py`, `rate_limit.py`, `encryption.py`, `120-teardown.sh`, `123-teardown.sh`, `CHANGELOG.md` (full top section + git history of the file)
**Pattern extraction date:** 2026-10-27

## Conventions

Derived via the shared `gsd-tools.cjs verify conventions --derive` module, scoped to `src/python/web/handler` (the directory containing the one file this phase edits in place):

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| File-name casing | — (tied) | 50% | 1.00 | contested hotspot |
| Identifier casing | Pascal | 100% | 0.00 | named contract |
| Export style | — | — | — | insufficient data |
| Import style | — | — | — | insufficient data |

Two additional Python-specific axes resolved cleanly within this scope: wildcard imports are 100% explicit (never `from x import *`), and import relativity is 100% relative (`from ..web_app import ...`, `from .serialize import ...`) — both **named contracts**, not contested. File-name casing is a 50/50 snake/camel split within this narrow scope (likely an artifact of mixing `.py` source files with other asset types in the scanned directory) and export/import-style axes had zero qualifying samples in this scope — both report `insufficient-data`/`contested`, meaning neither constrains this phase's one in-place edit (`config.py` itself is already snake_case and the phase adds no new file).

**Contested hotspots (author's choice):** this repo's prototype intentional-contested split is the CJS↔SDK dual resolver inside the GSD tooling itself (`bin/lib/**` is CJS `module.exports`/`require`; `sdk/src/**` is ESM `export`/`import`) — each half is internally consistent per-directory and contested only when compared repo-wide. The same principle applies here: match the local directory's style (this file is already consistent snake_case Python with relative imports) rather than importing a different convention from elsewhere in the tree.
