import unittest
import json
from datetime import datetime
from pytz import timezone

from .test_serialize import parse_stream
from common import Status
from web.serialize import SerializeStatus


class TestSerializeStatus(unittest.TestCase):
    def test_event_names(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        self.assertEqual("status", out["event"])

        status.server.up = False
        status.server.error_msg = "Bad stuff happened"
        out = parse_stream(serialize.status(status))
        self.assertEqual("status", out["event"])

    def test_server_status_up(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(True, data["server"]["up"])

        status.server.up = False
        status.server.error_msg = "Bad stuff happened"
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(False, data["server"]["up"])

    def test_server_status_error_msg(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(None, data["server"]["error_msg"])

        status.server.up = False
        status.server.error_msg = "Bad stuff happened"
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual("Bad stuff happened", data["server"]["error_msg"])

    def test_controller_status_latest_local_scan_time(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["controller"]["latest_local_scan_time"])

        timestamp = datetime(2018, 11, 9, 21, 40, 18, tzinfo=timezone('UTC'))
        status.controller.latest_local_scan_time = timestamp
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(str(1541799618.0), data["controller"]["latest_local_scan_time"])

    def test_controller_status_latest_remote_scan_time(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["controller"]["latest_remote_scan_time"])

        timestamp = datetime(2018, 11, 9, 21, 40, 18, tzinfo=timezone('UTC'))
        status.controller.latest_remote_scan_time = timestamp
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(str(1541799618.0), data["controller"]["latest_remote_scan_time"])

    def test_controller_status_latest_remote_scan_failed(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["controller"]["latest_remote_scan_failed"])

        status.controller.latest_remote_scan_failed = True
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(True, data["controller"]["latest_remote_scan_failed"])

    def test_controller_status_latest_remote_scan_error(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["controller"]["latest_remote_scan_error"])

        status.controller.latest_remote_scan_error = "remote server went boom"
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual("remote server went boom", data["controller"]["latest_remote_scan_error"])

    def test_storage_local_total(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["storage"]["local_total"])

        status.storage.local_total = 500_000_000_000
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(500_000_000_000, data["storage"]["local_total"])

    def test_storage_local_used(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["storage"]["local_used"])

        status.storage.local_used = 123_000_000_000
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(123_000_000_000, data["storage"]["local_used"])

    def test_storage_remote_total(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["storage"]["remote_total"])

        status.storage.remote_total = 2_000_000_000_000
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(2_000_000_000_000, data["storage"]["remote_total"])

    def test_storage_remote_used(self):
        serialize = SerializeStatus()
        status = Status()
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertIsNone(data["storage"]["remote_used"])

        status.storage.remote_used = 1_300_000_000_000
        out = parse_stream(serialize.status(status))
        data = json.loads(out["data"])
        self.assertEqual(1_300_000_000_000, data["storage"]["remote_used"])
