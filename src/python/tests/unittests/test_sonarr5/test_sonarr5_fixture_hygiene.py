"""Hygiene guard for the committed Sonarr 5 fixtures (SON5-04).

Every fixture under ``tests/fixtures/sonarr5/`` is scanned for shapes that
would leak private data into a public repository: API-key-shaped tokens,
non-documentation IPv4 literals, personal paths, real-TLD hostnames, email
addresses and API-key headers (D-13). Failure messages name the file and the
rule only, never the matched value.

The manifest checks accept any recorded 5.x build rather than a hardcoded one
(D-08), and prove the two queue fixtures show the same download in both states.
"""
import ipaddress
import json
import re
import unittest

from tests.unittests.test_sonarr5.fixtures import (
    FIXTURE_DIR,
    fixture_json,
    manifest,
    manifest_entry,
    queue_target_download_id,
    tested_version as recorded_version,
)

_MANIFEST_NAME = "manifest.json"
_VERSION_RE = re.compile(r"^5\.\d+\.\d+\.\d+$")
_ALLOWED_SOURCES = {"live", "placeholder"}


# Documentation and loopback ranges that may appear in sanitized fixtures.
_IPV4_ALLOWED = tuple(ipaddress.ip_network(n) for n in (
    "127.0.0.1/32", "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",
))
# Dotted quads not glued to further digits or dot-digit groups, so a four-part
# build number such as 5.1.2.3456 never yields a truncated candidate.
_IPV4_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?!\d|\.\d)")
_HEX32_RE = re.compile(r"(?i)\b[0-9a-f]{32}\b")
_HOME_RE = re.compile(r"/home/(?!user/)")
_PERSONAL_RE = re.compile(r"/volume1/|/Users/")
_URL_HOST_RE = re.compile(r"(?i)https?://([^/:\s\"'\\?#]+)")
_REAL_TLDS = (
    "com net org io dev me xyz cc to ws info co uk de nl eu us ch se fi club site top online"
).split()
# Lowercase only, so dotted release names like Show.US.S01E01 are not hosts.
_BARE_FQDN_RE = re.compile(
    r"(?<![\w.-])((?:[a-z0-9-]+\.)+(?:" + "|".join(_REAL_TLDS) + r"))(?![\w-]|\.[a-z0-9])"
)
_ALLOWED_LAST_LABELS = {"invalid", "example", "test", "localhost"}
_ALLOWED_DOMAINS = ("example.com", "example.org", "example.net")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_API_KEY_RE = re.compile(r"(?i)x-api-key|apikey=")

_RULE_ORDER = ("hex32", "ipv4", "home_path", "personal_path", "hostname", "email",
               "api_key_header")


def _manifest_versions() -> set[str]:
    try:
        return {e["sonarr_version"] for e in manifest()["fixtures"]}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


_KNOWN_VERSIONS = _manifest_versions()


def _ipv4_hit(text: str) -> bool:
    for candidate in _IPV4_RE.findall(text):
        if candidate in _KNOWN_VERSIONS:
            continue
        try:
            addr = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if not any(addr in net for net in _IPV4_ALLOWED):
            return True
    return False


def _host_allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
        return True  # IP literals are judged by the ipv4 rule
    except ValueError:
        pass
    if host.rsplit(".", 1)[-1] in _ALLOWED_LAST_LABELS:
        return True
    return any(host == d or host.endswith("." + d) for d in _ALLOWED_DOMAINS)


def _hostname_hit(text: str) -> bool:
    hosts = _URL_HOST_RE.findall(text) + _BARE_FQDN_RE.findall(text)
    return any(not _host_allowed(h) for h in hosts)


def _scan(text: str) -> list[str]:
    """Return the names of the hygiene rules ``text`` hits (never the values)."""
    hits = {
        "hex32": bool(_HEX32_RE.search(text)),
        "ipv4": _ipv4_hit(text),
        "home_path": bool(_HOME_RE.search(text)),
        "personal_path": bool(_PERSONAL_RE.search(text)),
        "hostname": _hostname_hit(text),
        "email": bool(_EMAIL_RE.search(text)),
        "api_key_header": bool(_API_KEY_RE.search(text)),
    }
    return [rule for rule in _RULE_ORDER if hits[rule]]


def _has_placeholders() -> bool:
    return any(e.get("source") == "placeholder" for e in manifest()["fixtures"])


def _fixture_files():
    return sorted(p for p in FIXTURE_DIR.glob("*.json"))


class TestScanner(unittest.TestCase):
    """Each rule fires on dirty input and stays silent on documentation values."""

    def test_hex32_token_flagged(self):
        self.assertEqual(["hex32"], _scan("key 0123456789abcdef0123456789ABCDEF x"))

    def test_forty_hex_download_id_not_flagged(self):
        self.assertEqual([], _scan('"downloadId": "' + "A1" * 20 + '"'))

    def test_private_ipv4_flagged(self):
        self.assertEqual(["ipv4"], _scan("10.1.2.3"))
        self.assertEqual(["ipv4"], _scan("http://100.64.1.2:8989/"))

    def test_documentation_ipv4_not_flagged(self):
        for value in ("192.0.2.10", "127.0.0.1", "203.0.113.7", "198.51.100.1"):
            with self.subTest(value=value):
                self.assertEqual([], _scan(value))

    def test_version_strings_not_flagged_as_ipv4(self):
        for value in (recorded_version(), "5.1.2.3456", '"version": "5.12.0.2999"', "3.46.1", "10.0.13"):
            with self.subTest(value=value):
                self.assertEqual([], _scan(value))

    def test_home_path_flagged(self):
        self.assertEqual(["home_path"], _scan("/home/alice/x"))
        self.assertEqual(["home_path"], _scan("/home/realuser/v5test"))

    def test_placeholder_home_path_not_flagged(self):
        self.assertEqual([], _scan("/home/user/v5test/x"))

    def test_personal_paths_flagged(self):
        self.assertEqual(["personal_path"], _scan("/volume1/docker"))
        self.assertEqual(["personal_path"], _scan("/Users/jane"))

    def test_real_hostnames_flagged(self):
        for value in ("http://nas.local.lan:8989/", "https://tracker.example-real.com/",
                      "seen at tracker.realsite.org today"):
            with self.subTest(value=value):
                self.assertEqual(["hostname"], _scan(value))

    def test_documentation_hostnames_not_flagged(self):
        for value in ("http://sonarr.example.invalid:8989",
                      "https://images.example.invalid/x.jpg",
                      "http://localhost:8080/",
                      "http://sonarr.example.com:8989",
                      "https://example.org/path",
                      "http://host.test/"):
            with self.subTest(value=value):
                self.assertEqual([], _scan(value))

    def test_email_flagged(self):
        self.assertEqual(["email"], _scan("bob@example.com"))

    def test_api_key_header_flagged(self):
        for value in ("X-Api-Key", "x-api-key: abc", "apikey=abc", "APIKEY=abc"):
            with self.subTest(value=value):
                self.assertEqual(["api_key_header"], _scan(value))

    def test_release_names_not_flagged(self):
        for value in ("Placeholder.Show.S01E01.1080p.WEB.h264-GROUP.mkv",
                      "Show.US.S01E01.720p.WEB.h264-GROUP",
                      "/data/torrents/Placeholder.Show.S01E01.1080p.WEB.h264-GROUP/x.mkv",
                      "C:\\testpath"):
            with self.subTest(value=value):
                self.assertEqual([], _scan(value))

    def test_multiple_rules_reported_once_each(self):
        hits = _scan("/volume1/a /Users/b /volume1/c 10.0.0.1 10.0.0.2")
        self.assertEqual(["ipv4", "personal_path"], hits)


class TestFixtureFiles(unittest.TestCase):
    """Every committed fixture passes every hygiene rule."""

    def test_fixture_directory_not_empty(self):
        self.assertTrue(_fixture_files(), "no Sonarr 5 fixtures found")

    def test_fixtures_are_clean(self):
        for path in _fixture_files():
            with self.subTest(file=path.name):
                rules = _scan(path.read_text(encoding="utf-8"))
                self.assertEqual([], rules, f"{path.name}: hygiene rules hit: {rules}")

    def test_fixtures_are_valid_json(self):
        for path in _fixture_files():
            with self.subTest(file=path.name):
                json.loads(path.read_bytes())


class TestManifest(unittest.TestCase):
    """The manifest indexes every fixture and records one 5.x build."""

    def setUp(self):
        self.manifest = manifest()
        self.entries = self.manifest["fixtures"]

    def test_every_fixture_has_exactly_one_entry(self):
        names = [p.name for p in _fixture_files() if p.name != _MANIFEST_NAME]
        for name in names:
            with self.subTest(file=name):
                manifest_entry(name)  # raises KeyError on 0 or >1 entries

    def test_every_entry_file_exists(self):
        for entry in self.entries:
            with self.subTest(file=entry.get("file")):
                self.assertNotEqual(_MANIFEST_NAME, entry["file"])
                self.assertTrue((FIXTURE_DIR / entry["file"]).is_file())

    def test_entry_fields(self):
        for entry in self.entries:
            with self.subTest(file=entry.get("file")):
                self.assertRegex(entry["sonarr_version"], _VERSION_RE)
                self.assertTrue(entry["scenario"].strip())
                self.assertTrue(entry["captured_at"].strip())
                self.assertTrue(entry["endpoint_or_event"].strip())
                self.assertIs(True, entry["sanitized"])
                self.assertIn(entry["source"], _ALLOWED_SOURCES)

    def test_single_recorded_build(self):
        versions = {e["sonarr_version"] for e in self.entries}
        self.assertEqual({recorded_version()}, versions)

    def test_status_version_matches_manifest(self):
        status = fixture_json("system_status.json")
        self.assertEqual(manifest_entry("system_status.json")["sonarr_version"], status["version"])
        self.assertRegex(status["version"], _VERSION_RE)

    def test_queue_fixtures_track_same_download_in_both_states(self):
        target = queue_target_download_id()
        incomplete = [r for r in fixture_json("queue_details_incomplete.json")
                      if r.get("downloadId") == target]
        complete = [r for r in fixture_json("queue_details_complete.json")
                    if r.get("downloadId") == target]
        self.assertTrue(incomplete, "target download missing from incomplete queue fixture")
        self.assertTrue(complete, "target download missing from complete queue fixture")
        for rec in incomplete:
            self.assertNotEqual("completed", str(rec["status"]).lower())
        for rec in complete:
            self.assertEqual("completed", str(rec["status"]).lower())
            self.assertEqual(0, rec["sizeleft"])

    def test_import_webhook_names_target_download(self):
        body = fixture_json("webhook_download.json")
        self.assertEqual(queue_target_download_id(), body["downloadId"])


class TestLiveSource(unittest.TestCase):
    """The phase cannot close while any fixture is still a placeholder."""

    @unittest.skipIf(
        _has_placeholders(),
        "placeholder fixtures present — Phase 120 Plan 06 must replace placeholder "
        "fixtures with live captures before this phase can close",
    )
    def test_all_fixtures_are_live_captures(self):
        for entry in manifest()["fixtures"]:
            with self.subTest(file=entry["file"]):
                self.assertEqual("live", entry["source"])
