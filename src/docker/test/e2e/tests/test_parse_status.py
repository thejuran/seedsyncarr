"""
Unit tests for parse_status.py

Covers:
  92-01-04 (E2EINFRA-04): specific exception handling only
    (json.JSONDecodeError, KeyError, TypeError) — no bare except
  92-01-05 (E2EINFRA-05): functional correctness for all code paths
    without requiring Docker
"""

import importlib.util
import io
import json
import runpy
from pathlib import Path
from unittest.mock import patch

PARSE_STATUS_PATH = (
    Path(__file__).parent.parent / "parse_status.py"
).resolve()


# ---------------------------------------------------------------------------
# Helper: run parse_status as __main__ with controlled stdin and argv
# ---------------------------------------------------------------------------

def _run(stdin_text: str, check_type: str) -> str:
    """
    Execute parse_status.py's __main__ block with the given stdin and argv.
    Returns captured stdout (stripped).
    """
    fake_stdin = io.StringIO(stdin_text)
    captured = io.StringIO()

    with (
        patch("sys.stdin", fake_stdin),
        patch("sys.argv", ["parse_status.py", check_type]),
        patch("sys.stdout", captured),
    ):
        runpy.run_path(str(PARSE_STATUS_PATH), run_name="__main__")

    return captured.getvalue().strip()


# ---------------------------------------------------------------------------
# 92-01-04: specific exception handling — no bare except
# ---------------------------------------------------------------------------

class TestExceptionHandlingIsSpecific:
    """E2EINFRA-04: parse_status.py must catch only json.JSONDecodeError,
    KeyError, and TypeError — not SystemExit or KeyboardInterrupt."""

    def test_module_source_does_not_contain_bare_except(self):
        source = PARSE_STATUS_PATH.read_text()
        lines = source.splitlines()
        bare_except_lines = [
            line.strip() for line in lines if line.strip() == "except:"
        ]
        assert bare_except_lines == [], (
            f"Found bare 'except:' in parse_status.py: {bare_except_lines}"
        )

    def test_module_source_contains_specific_json_decode_error(self):
        source = PARSE_STATUS_PATH.read_text()
        assert "json.JSONDecodeError" in source, (
            "parse_status.py must explicitly handle json.JSONDecodeError"
        )

    def test_module_source_contains_specific_key_error(self):
        source = PARSE_STATUS_PATH.read_text()
        assert "KeyError" in source, (
            "parse_status.py must explicitly handle KeyError"
        )

    def test_module_source_contains_specific_type_error(self):
        source = PARSE_STATUS_PATH.read_text()
        assert "TypeError" in source, (
            "parse_status.py must explicitly handle TypeError"
        )

    def test_invalid_json_prints_false_not_traceback(self):
        """JSONDecodeError from malformed stdin is caught and prints False."""
        result = _run("not-valid-json", "server_up")
        assert result == "False", (
            f"Expected 'False' for invalid JSON input, got {result!r}"
        )

    def test_missing_key_prints_false_not_traceback(self):
        """KeyError when JSON is valid but missing expected key."""
        result = _run("{}", "server_up")
        assert result == "False", (
            f"Expected 'False' for missing key, got {result!r}"
        )

    def test_empty_stdin_prints_false_not_traceback(self):
        """Empty stdin causes JSONDecodeError — must be caught."""
        result = _run("", "server_up")
        assert result == "False", (
            f"Expected 'False' for empty stdin, got {result!r}"
        )


# ---------------------------------------------------------------------------
# 92-01-05: functional correctness — all code paths
# ---------------------------------------------------------------------------

class TestServerUpCodePath:
    """parse_status.py server_up path returns True/False correctly."""

    def test_server_up_true_when_server_up_is_true(self):
        payload = json.dumps({"server": {"up": True}})
        result = _run(payload, "server_up")
        assert result == "True", (
            f"Expected 'True' for server.up=true, got {result!r}"
        )

    def test_server_up_false_when_server_up_is_false(self):
        payload = json.dumps({"server": {"up": False}})
        result = _run(payload, "server_up")
        assert result == "False", (
            f"Expected 'False' for server.up=false, got {result!r}"
        )

    def test_server_up_false_when_server_key_missing(self):
        payload = json.dumps({"other": "data"})
        result = _run(payload, "server_up")
        assert result == "False", (
            f"Expected 'False' for missing 'server' key, got {result!r}"
        )

    def test_server_up_false_when_up_key_missing(self):
        payload = json.dumps({"server": {}})
        result = _run(payload, "server_up")
        assert result == "False", (
            f"Expected 'False' for missing 'up' key inside server, got {result!r}"
        )


class TestRemoteScanDoneCodePath:
    """parse_status.py remote_scan_done path returns True/False correctly."""

    def test_remote_scan_done_true_when_scan_time_present(self):
        payload = json.dumps(
            {"controller": {"latest_remote_scan_time": "2026-01-01T00:00:00"}}
        )
        result = _run(payload, "remote_scan_done")
        assert result == "True", (
            f"Expected 'True' when latest_remote_scan_time is set, got {result!r}"
        )

    def test_remote_scan_done_false_when_scan_time_is_null(self):
        payload = json.dumps({"controller": {"latest_remote_scan_time": None}})
        result = _run(payload, "remote_scan_done")
        assert result == "False", (
            f"Expected 'False' when latest_remote_scan_time is null, got {result!r}"
        )

    def test_remote_scan_done_false_when_controller_key_missing(self):
        payload = json.dumps({"server": {"up": True}})
        result = _run(payload, "remote_scan_done")
        assert result == "False", (
            f"Expected 'False' when controller key missing, got {result!r}"
        )

    def test_remote_scan_done_false_when_scan_time_key_missing(self):
        payload = json.dumps({"controller": {}})
        result = _run(payload, "remote_scan_done")
        assert result == "False", (
            f"Expected 'False' when latest_remote_scan_time key missing, got {result!r}"
        )


class TestUnknownCheckType:
    """Unknown check_type argument prints False."""

    def test_unknown_check_type_prints_false(self):
        payload = json.dumps({"server": {"up": True}})
        result = _run(payload, "unknown_check")
        assert result == "False", (
            f"Expected 'False' for unknown check_type, got {result!r}"
        )


class TestModuleImportSafety:
    """E2EINFRA-05: importing parse_status.py must not execute main logic."""

    def test_import_produces_no_output_and_no_side_effects(self, capsys):
        spec = importlib.util.spec_from_file_location(
            "parse_status_importtest", str(PARSE_STATUS_PATH)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        captured = capsys.readouterr()
        assert captured.out == "", (
            f"Importing parse_status.py produced unexpected stdout: {captured.out!r}"
        )
        assert captured.err == "", (
            f"Importing parse_status.py produced unexpected stderr: {captured.err!r}"
        )

    def test_import_does_not_raise(self):
        spec = importlib.util.spec_from_file_location(
            "parse_status_importtest2", str(PARSE_STATUS_PATH)
        )
        module = importlib.util.module_from_spec(spec)
        # Should not raise even without sys.argv having a check_type argument
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise AssertionError(
                f"Importing parse_status.py raised an exception: {exc}"
            ) from exc
