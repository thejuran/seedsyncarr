"""Read-only loader for the committed Sonarr 5 fixtures.

Fixture bytes are returned raw so tests can feed the exact recorded payloads to
the production parsers. The directory is mounted read-only in the CI container,
so nothing here writes next to the fixtures.
"""
import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sonarr5"

_MANIFEST_NAME = "manifest.json"
_STATUS_FIXTURE = "system_status.json"


def fixture_bytes(name: str) -> bytes:
    """Return the raw bytes of a fixture file."""
    return (FIXTURE_DIR / name).read_bytes()


def fixture_json(name: str):
    """Return a fixture file parsed as JSON."""
    return json.loads(fixture_bytes(name))


def manifest() -> dict:
    """Return the parsed fixture manifest."""
    return fixture_json(_MANIFEST_NAME)


def manifest_entry(name: str) -> dict:
    """Return the single manifest entry for ``name``.

    Raises KeyError when the file has no entry or more than one.
    """
    matches = [e for e in manifest()["fixtures"] if e.get("file") == name]
    if len(matches) != 1:
        raise KeyError(f"{name}: expected 1 manifest entry, found {len(matches)}")
    return matches[0]


def tested_version() -> str:
    """Return the recorded Sonarr build the fixtures were captured from."""
    return manifest_entry(_STATUS_FIXTURE)["sonarr_version"]


def queue_target_download_id() -> str:
    """Return the downloadId tracked across both queue fixtures and the import webhook."""
    return manifest()["queue_target_download_id"]
