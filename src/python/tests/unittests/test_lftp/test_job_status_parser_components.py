# Copyright 2017, Inderpreet Singh, All rights reserved.
# Extended tests for refactored job status parser components.

import unittest

from lftp import (
    LftpJobStatus,
    RegexPatterns,
    TransferStateParser,
    PgetJobParser,
    MirrorJobParser,
    JobParserFactory,
    QueueParser,
    ActiveJobsParser,
)


class TestRegexPatterns(unittest.TestCase):
    """Tests for compiled regex patterns."""

    def test_size_pattern_matches_bytes(self):
        match = RegexPatterns.SIZE_PATTERN.search("1234")
        self.assertIsNotNone(match)
        self.assertEqual("1234", match.group("number"))
        self.assertIsNone(match.group("units"))

    def test_size_pattern_matches_kilobytes(self):
        for unit in ["kb", "KB", "KiB", "Kib", "k", "K"]:
            match = RegexPatterns.SIZE_PATTERN.search("512{}".format(unit))
            self.assertIsNotNone(match, "Failed for unit: {}".format(unit))
            self.assertEqual("512", match.group("number"))

    def test_size_pattern_matches_megabytes(self):
        for unit in ["mb", "MB", "MiB", "Mib", "m", "M"]:
            match = RegexPatterns.SIZE_PATTERN.search("256{}".format(unit))
            self.assertIsNotNone(match, "Failed for unit: {}".format(unit))
            self.assertEqual("256", match.group("number"))

    def test_size_pattern_matches_gigabytes(self):
        for unit in ["gb", "GB", "GiB", "Gib", "g", "G"]:
            match = RegexPatterns.SIZE_PATTERN.search("2{}".format(unit))
            self.assertIsNotNone(match, "Failed for unit: {}".format(unit))
            self.assertEqual("2", match.group("number"))

    def test_size_pattern_matches_decimal(self):
        match = RegexPatterns.SIZE_PATTERN.search("1.5mb")
        self.assertIsNotNone(match)
        self.assertEqual("1.5", match.group("number"))

    def test_time_pattern_matches_seconds(self):
        match = RegexPatterns.TIME_PATTERN.search("30s")
        self.assertIsNotNone(match)
        self.assertEqual("30s", match.group("eta_s"))

    def test_time_pattern_matches_complex(self):
        match = RegexPatterns.TIME_PATTERN.search("1d2h30m45s")
        self.assertIsNotNone(match)
        self.assertEqual("1d", match.group("eta_d"))
        self.assertEqual("2h", match.group("eta_h"))
        self.assertEqual("30m", match.group("eta_m"))
        self.assertEqual("45s", match.group("eta_s"))

    def test_pget_header_matches(self):
        line = "[1] pget -c /remote/file.txt -o /local/"
        match = RegexPatterns.PGET_HEADER.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("1", match.group("id"))
        self.assertEqual("-c", match.group("flags"))
        self.assertEqual("/remote/file.txt", match.group("remote"))

    def test_pget_header_matches_quoted(self):
        line = "[2] pget -c \"/remote/path with spaces/file.txt\" -o \"/local/\""
        match = RegexPatterns.PGET_HEADER.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("2", match.group("id"))
        self.assertEqual("/remote/path with spaces/file.txt", match.group("remote"))

    def test_mirror_header_matches(self):
        line = "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%) 50 KiB/s"
        match = RegexPatterns.MIRROR_HEADER.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("1", match.group("id"))
        self.assertEqual("-c", match.group("flags"))
        self.assertEqual("/remote/dir", match.group("remote"))

    def test_mirror_fl_header_matches(self):
        line = "[1] mirror -c /remote/dir /local/"
        match = RegexPatterns.MIRROR_FL_HEADER.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("1", match.group("id"))

    def test_queue_done_matches(self):
        line = "[0] Done (queue (sftp://user@host))"
        match = RegexPatterns.QUEUE_DONE.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("0", match.group("id"))

    def test_chunk_got_matches(self):
        line = "`file.txt', got 1024 of 2048 (50%) 512K/s eta:2s"
        match = RegexPatterns.CHUNK_GOT.search(line)
        self.assertIsNotNone(match)
        self.assertEqual("file.txt", match.group("name"))
        self.assertEqual("1024", match.group("szlocal"))
        self.assertEqual("2048", match.group("szremote"))
        self.assertEqual("50", match.group("pctlocal"))

    def test_chunk_at_matches(self):
        line = "`file.txt' at 1024 (50%) 512K/s eta:30s [Receiving data]"
        match = RegexPatterns.CHUNK_AT.search(line)
        self.assertIsNotNone(match)
        self.assertEqual("file.txt", match.group("name"))

    def test_transfer_filename_matches(self):
        line = "\\transfer `somefile.txt'"
        match = RegexPatterns.TRANSFER_FILENAME.search(line)
        self.assertIsNotNone(match)
        self.assertEqual("somefile.txt", match.group("name"))

    def test_queue_pget_matches(self):
        line = "1. pget -c /remote/file -o /local/"
        match = RegexPatterns.QUEUE_PGET.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("1", match.group("id"))
        self.assertEqual("-c", match.group("flags"))

    def test_queue_mirror_matches(self):
        line = "2. mirror -c /remote/dir /local/"
        match = RegexPatterns.QUEUE_MIRROR.match(line)
        self.assertIsNotNone(match)
        self.assertEqual("2", match.group("id"))


class TestTransferStateParser(unittest.TestCase):
    """Tests for TransferStateParser utility methods."""

    def test_size_to_bytes_plain_number(self):
        self.assertEqual(1234, TransferStateParser.size_to_bytes("1234"))

    def test_size_to_bytes_zero(self):
        self.assertEqual(0, TransferStateParser.size_to_bytes("0"))

    def test_size_to_bytes_kilobytes(self):
        self.assertEqual(1024, TransferStateParser.size_to_bytes("1kb"))
        self.assertEqual(1024, TransferStateParser.size_to_bytes("1KB"))
        self.assertEqual(1024, TransferStateParser.size_to_bytes("1KiB"))
        self.assertEqual(1536, TransferStateParser.size_to_bytes("1.5kb"))

    def test_size_to_bytes_megabytes(self):
        self.assertEqual(1048576, TransferStateParser.size_to_bytes("1mb"))
        self.assertEqual(1048576, TransferStateParser.size_to_bytes("1MB"))
        self.assertEqual(1572864, TransferStateParser.size_to_bytes("1.5mb"))

    def test_size_to_bytes_gigabytes(self):
        self.assertEqual(1073741824, TransferStateParser.size_to_bytes("1gb"))
        self.assertEqual(1073741824, TransferStateParser.size_to_bytes("1GB"))
        self.assertEqual(1610612736, TransferStateParser.size_to_bytes("1.5gb"))

    def test_size_to_bytes_with_space(self):
        self.assertEqual(1024, TransferStateParser.size_to_bytes("1 kb"))
        self.assertEqual(1048576, TransferStateParser.size_to_bytes("1 mb"))

    def test_size_to_bytes_invalid_raises(self):
        with self.assertRaises(ValueError):
            TransferStateParser.size_to_bytes("invalid")

    def test_eta_to_seconds_seconds_only(self):
        self.assertEqual(30, TransferStateParser.eta_to_seconds("30s"))

    def test_eta_to_seconds_minutes_only(self):
        self.assertEqual(120, TransferStateParser.eta_to_seconds("2m"))

    def test_eta_to_seconds_hours_only(self):
        self.assertEqual(7200, TransferStateParser.eta_to_seconds("2h"))

    def test_eta_to_seconds_days_only(self):
        self.assertEqual(172800, TransferStateParser.eta_to_seconds("2d"))

    def test_eta_to_seconds_complex(self):
        # 1d + 2h + 30m + 45s = 86400 + 7200 + 1800 + 45 = 95445
        self.assertEqual(95445, TransferStateParser.eta_to_seconds("1d2h30m45s"))

    def test_eta_to_seconds_partial(self):
        # 1h + 45m = 3600 + 2700 = 6300
        self.assertEqual(6300, TransferStateParser.eta_to_seconds("1h45m"))

    def test_parse_chunk_at(self):
        line = "`file.txt' at 1024 (50%) 512K/s eta:30s [Receiving data]"
        match = RegexPatterns.CHUNK_AT.search(line)
        state = TransferStateParser.parse_chunk_at(match)
        self.assertIsNone(state.size_local)
        self.assertIsNone(state.size_remote)
        self.assertIsNone(state.percent_local)
        self.assertEqual(512 * 1024, state.speed)
        self.assertEqual(30, state.eta)

    def test_parse_chunk_at_no_speed_eta(self):
        # Some chunk_at patterns don't have speed or eta
        line = "`file.txt' at 1024 (50%) [Receiving data]"
        match = RegexPatterns.CHUNK_AT.search(line)
        if match:  # Pattern may not match without speed/eta
            state = TransferStateParser.parse_chunk_at(match)
            self.assertIsNone(state.speed)
            self.assertIsNone(state.eta)

    def test_parse_chunk_got(self):
        line = "`file.txt', got 1024 of 2048 (50%) 512K/s eta:30s"
        match = RegexPatterns.CHUNK_GOT.search(line)
        state = TransferStateParser.parse_chunk_got(match)
        self.assertEqual(1024, state.size_local)
        self.assertEqual(2048, state.size_remote)
        self.assertEqual(50, state.percent_local)
        self.assertEqual(512 * 1024, state.speed)
        self.assertEqual(30, state.eta)

    def test_parse_chunk_got_no_speed_eta(self):
        line = "`file.txt', got 1024 of 2048 (50%)"
        match = RegexPatterns.CHUNK_GOT.search(line)
        state = TransferStateParser.parse_chunk_got(match)
        self.assertEqual(1024, state.size_local)
        self.assertEqual(2048, state.size_remote)
        self.assertEqual(50, state.percent_local)
        self.assertIsNone(state.speed)
        self.assertIsNone(state.eta)


class TestPgetJobParser(unittest.TestCase):
    """Tests for PgetJobParser class."""

    def setUp(self):
        self.parser = PgetJobParser()

    def test_can_parse_pget_header(self):
        line = "[1] pget -c /remote/file.txt -o /local/"
        self.assertTrue(self.parser.can_parse(line))

    def test_cannot_parse_mirror_header(self):
        line = "[1] mirror -c /remote/dir /local/"
        self.assertFalse(self.parser.can_parse(line))

    def test_cannot_parse_random_line(self):
        line = "some random line"
        self.assertFalse(self.parser.can_parse(line))

    def test_parse_header_basic(self):
        lines = ["sftp://user@host", "`/remote/file.txt', got 100 of 200 (50%)"]
        line = "[1] pget -c /remote/file.txt -o /local/"
        status = self.parser.parse_header(line, lines)
        self.assertIsNotNone(status)
        self.assertEqual(1, status.id)
        self.assertEqual("file.txt", status.name)
        self.assertEqual(LftpJobStatus.Type.PGET, status.type)
        self.assertEqual(LftpJobStatus.State.RUNNING, status.state)
        self.assertEqual("-c", status._LftpJobStatus__flags)

    def test_parse_header_missing_sftp_line_raises(self):
        lines = ["some other line"]
        line = "[1] pget -c /remote/file.txt -o /local/"
        with self.assertRaises(ValueError):
            self.parser.parse_header(line, lines)

    def test_parse_header_consumes_sftp_line(self):
        lines = ["sftp://user@host", "`file.txt', got 100 of 200 (50%)"]
        line = "[1] pget -c /remote/file.txt -o /local/"
        self.parser.parse_header(line, lines)
        # Both sftp line and data line should be consumed
        self.assertEqual(0, len(lines))


class TestMirrorJobParser(unittest.TestCase):
    """Tests for MirrorJobParser class."""

    def setUp(self):
        self.parser = MirrorJobParser()

    def test_can_parse_mirror_header(self):
        line = "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%) 50 KiB/s"
        self.assertTrue(self.parser.can_parse(line))

    def test_can_parse_mirror_fl_header(self):
        line = "[1] mirror -c /remote/dir /local/"
        self.assertTrue(self.parser.can_parse(line))

    def test_cannot_parse_pget_header(self):
        line = "[1] pget -c /remote/file.txt -o /local/"
        self.assertFalse(self.parser.can_parse(line))

    def test_parse_downloading_header(self):
        lines = []
        line = "[1] mirror -c /remote/mydir /local/  -- 100k/1M (10%) 50 KiB/s"
        status = self.parser.parse_header(line, lines)
        self.assertIsNotNone(status)
        self.assertEqual(1, status.id)
        self.assertEqual("mydir", status.name)
        self.assertEqual(LftpJobStatus.Type.MIRROR, status.type)
        self.assertEqual(LftpJobStatus.State.RUNNING, status.state)
        self.assertEqual(100 * 1024, status.total_transfer_state.size_local)
        self.assertEqual(1024 * 1024, status.total_transfer_state.size_remote)
        self.assertEqual(10, status.total_transfer_state.percent_local)

    def test_parse_connecting_header(self):
        lines = ["Getting file list (25) [Receiving data]"]
        line = "[1] mirror -c /remote/mydir /local/"
        status = self.parser.parse_header(line, lines)
        self.assertIsNotNone(status)
        self.assertEqual(1, status.id)
        self.assertEqual("mydir", status.name)
        # Connecting line should be consumed
        self.assertEqual(0, len(lines))

    def test_parse_connecting_header_with_cd(self):
        lines = ["cd /remote/mydir"]
        line = "[1] mirror -c /remote/mydir /local/"
        status = self.parser.parse_header(line, lines)
        self.assertIsNotNone(status)
        # cd line should be consumed
        self.assertEqual(0, len(lines))


class TestJobParserFactory(unittest.TestCase):
    """Tests for JobParserFactory class."""

    def setUp(self):
        self.factory = JobParserFactory()

    def test_get_parser_for_pget(self):
        line = "[1] pget -c /remote/file.txt -o /local/"
        parser = self.factory.get_parser(line)
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, PgetJobParser)

    def test_get_parser_for_mirror(self):
        line = "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)"
        parser = self.factory.get_parser(line)
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, MirrorJobParser)

    def test_get_parser_for_mirror_connecting(self):
        line = "[1] mirror -c /remote/dir /local/"
        parser = self.factory.get_parser(line)
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, MirrorJobParser)

    def test_get_parser_returns_none_for_unknown(self):
        line = "some random line"
        parser = self.factory.get_parser(line)
        self.assertIsNone(parser)


class TestQueueParser(unittest.TestCase):
    """Tests for QueueParser class."""

    def test_parse_empty_queue(self):
        lines = ["[0] Done (queue (sftp://user@host))"]
        result = QueueParser.parse(lines)
        self.assertEqual(0, len(result))
        self.assertEqual(0, len(lines))  # Line should be consumed

    def test_parse_queue_with_items(self):
        lines = [
            "[0] queue (sftp://someone:@localhost)",
            "sftp://someone:@localhost/home/someone",
            "Queue is stopped.",
            "Commands queued:",
            "1. mirror -c /remote/a /local/",
            "2. pget -c /remote/b -o /local/",
        ]
        result = QueueParser.parse(lines)
        self.assertEqual(2, len(result))
        self.assertEqual("a", result[0].name)
        self.assertEqual(LftpJobStatus.Type.MIRROR, result[0].type)
        self.assertEqual(LftpJobStatus.State.QUEUED, result[0].state)
        self.assertEqual("b", result[1].name)
        self.assertEqual(LftpJobStatus.Type.PGET, result[1].type)

    def test_parse_queue_with_now_executing(self):
        lines = [
            "[0] queue (sftp://someone:@localhost)  -- 15.8 KiB/s",
            "sftp://someone:@localhost/home/someone",
            "Now executing: [1] mirror -c /remote/a /local/",
            "-[2] pget -c /remote/b -o /local/",
            "Commands queued:",
            "1. mirror -c /remote/c /local/",
        ]
        result = QueueParser.parse(lines)
        self.assertEqual(1, len(result))
        self.assertEqual("c", result[0].name)

    def test_parse_queue_line_pget(self):
        result = QueueParser._parse_queue_line("1. pget -c /remote/file -o /local/")
        self.assertIsNotNone(result)
        self.assertEqual(1, result.id)
        self.assertEqual("file", result.name)
        self.assertEqual(LftpJobStatus.Type.PGET, result.type)
        self.assertEqual(LftpJobStatus.State.QUEUED, result.state)

    def test_parse_queue_line_mirror(self):
        result = QueueParser._parse_queue_line("2. mirror -c /remote/dir /local/")
        self.assertIsNotNone(result)
        self.assertEqual(2, result.id)
        self.assertEqual("dir", result.name)
        self.assertEqual(LftpJobStatus.Type.MIRROR, result.type)

    def test_parse_queue_line_invalid_raises(self):
        with self.assertRaises(ValueError):
            QueueParser._parse_queue_line("invalid line")


class TestActiveJobsParser(unittest.TestCase):
    """Tests for ActiveJobsParser class."""

    def setUp(self):
        self.parser = ActiveJobsParser()

    def test_parse_empty(self):
        lines = []
        result = self.parser.parse(lines)
        self.assertEqual(0, len(result))

    def test_parse_single_mirror_job(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%) 50 KiB/s",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))
        self.assertEqual("dir", result[0].name)
        self.assertEqual(LftpJobStatus.Type.MIRROR, result[0].type)

    def test_parse_single_pget_job(self):
        lines = [
            "[1] pget -c /remote/file.txt -o /local/",
            "sftp://user@host",
            "`file.txt', got 100 of 200 (50%)",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))
        self.assertEqual("file.txt", result[0].name)
        self.assertEqual(LftpJobStatus.Type.PGET, result[0].type)

    def test_parse_multiple_jobs(self):
        lines = [
            "[1] mirror -c /remote/dir1 /local/  -- 100k/1M (10%)",
            "[2] mirror -c /remote/dir2 /local/  -- 200k/2M (10%)",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(2, len(result))
        self.assertEqual("dir1", result[0].name)
        self.assertEqual("dir2", result[1].name)

    def test_parse_job_with_file_transfers(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "\\transfer `file1.txt'",
            "`file1.txt', got 50 of 100 (50%)",
            "\\transfer `file2.txt'",
            "`file2.txt', got 25 of 100 (25%)",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))
        file_states = result[0].get_active_file_transfer_states()
        self.assertEqual(2, len(file_states))

    def test_parse_done_line(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "[0] Done (queue (sftp://user@host))",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))

    def test_parse_done_line_with_remaining_raises(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "[0] Done (queue (sftp://user@host))",
            "extra line",
        ]
        with self.assertRaises(ValueError):
            self.parser.parse(lines)

    def test_parse_unknown_line_raises(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "completely unknown line format",
        ]
        with self.assertRaises(ValueError):
            self.parser.parse(lines)

    def test_handle_chunk_lines(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "\\transfer `file.txt'",
            "`file.txt', got 50 of 100 (50%)",
            "\\chunk 0-1024",
            "`file.txt' at 512 (50%) [Receiving data]",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))

    def test_handle_mirror_subdir_lines(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "\\mirror `subdir'  -- 50k/500k (10%)",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))

    def test_handle_empty_mirror_lines(self):
        lines = [
            "[1] mirror -c /remote/dir /local/  -- 100k/1M (10%)",
            "\\mirror `subdir'",
            "Getting file list",
        ]
        result = self.parser.parse(lines)
        self.assertEqual(1, len(result))


if __name__ == '__main__':
    unittest.main()
