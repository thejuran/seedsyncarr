import os
import re
from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from common import AppError
from .job_status import LftpJobStatus

class LftpJobStatusParserError(AppError):
    pass

class RegexPatterns:
    """
    Compiled regex patterns for parsing LFTP job status output.
    All patterns are compiled once at module load time for efficiency.
    """
    # Size and time unit patterns
    SIZE_UNITS = ("b|B|"
                  "k|kb|kib|K|Kb|KB|KiB|Kib|"
                  "m|mb|mib|M|Mb|MB|MiB|Mib|"
                  "g|gb|gib|G|Gb|GB|GiB|Gib")
    TIME_UNITS = r"(?P<eta_d>\d*d)?(?P<eta_h>\d*h)?(?P<eta_m>\d*m)?(?P<eta_s>\d*s)?"

    # Compiled patterns for size and time parsing
    SIZE_PATTERN = re.compile(r"(?P<number>\d+\.?\d*)\s*(?P<units>{})?".format(SIZE_UNITS))
    TIME_PATTERN = re.compile(TIME_UNITS)

    # Common patterns
    QUOTED_FILE_NAME = r"`(?P<name>.*)'"
    QUEUE_DONE = re.compile(r"^\[(?P<id>\d+)\]\sDone\s\(queue\s\(.+\)\)")

    # Pget header pattern
    PGET_HEADER = re.compile(
        r"^\[(?P<id>\d+)\]\s+"
        r"pget\s+"
        r"(?P<flags>.*?)\s+"
        r"(?P<lq>['\"]|)(?P<remote>.+)(?P=lq)\s+"
        r"-o\s+"
        r"(?P<rq>['\"]|)(?P<local>.+)(?P=rq)$"
    )

    # Mirror header patterns
    MIRROR_HEADER = re.compile(
        r"^\[(?P<id>\d+)\]\s+"
        r"mirror\s+"
        r"(?P<flags>.*?)\s+"
        r"(?P<lq>['\"]|)(?P<remote>.+)(?P=lq)\s+"
        r"(?P<rq>['\"]|)(?P<local>.+)(?P=rq)\s+"
        r"--\s+"
        r"(?P<szlocal>\d+\.?\d*\s?({sz})?)"
        r"\/"
        r"(?P<szremote>\d+\.?\d*\s?({sz})?)\s+"
        r"\((?P<pctlocal>\d+)%\)"
        r"(\s+(?P<speed>\d+\.?\d*\s?({sz}))\/s)?$".format(sz=SIZE_UNITS)
    )

    # Mirror file list header (connecting or receiving file list)
    MIRROR_FL_HEADER = re.compile(
        r"^\[(?P<id>\d+)\]\s+"
        r"mirror\s+"
        r"(?P<flags>.*?)\s+"
        r"(?P<lq>['\"]|)(?P<remote>.+)(?P=lq)\s+"
        r"(?P<rq>['\"]|)(?P<local>.+)(?P=rq)$"
    )

    # Transfer filename pattern
    TRANSFER_FILENAME = re.compile(r"\\transfer\s" + QUOTED_FILE_NAME)

    # Chunk patterns - 'at' format with optional speed/eta
    CHUNK_AT = re.compile(
        r"^" + QUOTED_FILE_NAME + r"\s+"
        r"at\s+"
        r"\d+\s+"
        r"(?:\(\d+%\)\s+)?"
        r"((?P<speed>\d+\.?\d*\s?({sz}))\/s\s+)?"
        r"(eta:(?P<eta>{eta})\s+)?"
        r"\s*\[(?P<desc>.*)\]$".format(sz=SIZE_UNITS, eta=TIME_UNITS)
    )

    # Chunk patterns - 'at' format minimal
    CHUNK_AT2 = re.compile(
        r"^" + QUOTED_FILE_NAME + r"\s+"
        r"at\s+"
        r"\d+\s+"
        r"(?:\(\d+%\))"
    )

    # Chunk patterns - 'got' format
    CHUNK_GOT = re.compile(
        r"^" + QUOTED_FILE_NAME + r",\s+"
        r"got\s+"
        r"(?P<szlocal>\d+)\s+"
        r"of\s+"
        r"(?P<szremote>\d+)\s+"
        r"\((?P<pctlocal>\d+)%\)"
        r"(\s+(?P<speed>\d+\.?\d*\s?({sz}))\/s)?"
        r"(\seta:(?P<eta>{eta}))?".format(sz=SIZE_UNITS, eta=TIME_UNITS)
    )

    # Chunk header pattern
    CHUNK_HEADER = re.compile(
        r"\\chunk\s"
        r"(?P<start>\d+)"
        r"-"
        r"(?P<end>\d+)"
    )

    # Chmod patterns
    CHMOD_HEADER = re.compile(r"chmod\s(?P<name>.*)")
    CHMOD_PATTERN = re.compile(QUOTED_FILE_NAME + r"\s\[\]")

    # Mirror subdir pattern
    MIRROR_SUBDIR = re.compile(
        r"\\mirror\s" + QUOTED_FILE_NAME + r"\s+"
        r"--\s+"
        r"(?P<szlocal>\d+\.?\d*\s?({sz})?)"
        r"\/"
        r"(?P<szremote>\d+\.?\d*\s?({sz})?)\s+"
        r"\((?P<pctlocal>\d+)%\)"
        r"(\s+(?P<speed>\d+\.?\d*\s?({sz}))\/s)?$".format(sz=SIZE_UNITS)
    )

    # Empty mirror pattern
    MIRROR_EMPTY = re.compile(r"\\mirror\s" + QUOTED_FILE_NAME + r"\s*$")

    # Queue header patterns
    QUEUE_HEADER1 = re.compile(
        r"^\[\d+\] queue \(sftp://.*@.*\)(?:\s+--\s+(?:\d+\.\d+|\d+)\s(?:{})\/s)?$".format(SIZE_UNITS)
    )
    QUEUE_HEADER2 = re.compile(r"^sftp://.*@.*$")

    # Queued command patterns
    QUEUE_PGET = re.compile(
        r"^(?P<id>\d+)\.\s+"
        r"pget\s+"
        r"(?P<flags>.*?)\s+"
        r"(?P<lq>[\'\"]|)(?P<remote>.+)(?P=lq)\s+"
        r"(?:-o\s+)"
        r"(?P<rq>[\'\"]|)(?P<local>.+)(?P=rq)$"
    )

    QUEUE_MIRROR = re.compile(
        r"^(?P<id>\d+)\.\s+"
        r"mirror\s+"
        r"(?P<flags>.*?)\s+"
        r"(?P<lq>[\'\"]|)(?P<remote>.+)(?P=lq)\s+"
        r"(?P<rq>[\'\"]|)(?P<local>.+)(?P=rq)$"
    )

class TransferStateParser:
    """
    Utility class for parsing transfer state information from LFTP output.
    """

    @staticmethod
    def size_to_bytes(size: str) -> int:
        """
        Parse the size string and return number of bytes.

        :param size: Size string like "1.5mb", "1024", "2KiB"
        :return: Number of bytes
        """
        if size == "0":
            return 0
        result = RegexPatterns.SIZE_PATTERN.search(size)
        if not result:
            raise ValueError("String '{}' does not match the size pattern".format(size))
        number = float(result.group("number"))
        unit = (result.group("units") or "b")[0].lower()
        multipliers = {'b': 1, 'k': 1024, 'm': 1024 * 1024, 'g': 1024 * 1024 * 1024}
        if unit not in multipliers.keys():
            raise ValueError("Unrecognized unit {} in size string '{}'".format(unit, size))
        return int(number * multipliers[unit])

    @staticmethod
    def eta_to_seconds(eta: str) -> int:
        """
        Parse the time string and return number of seconds.

        :param eta: ETA string like "1d2h3m4s", "30m", "1h45m"
        :return: Number of seconds
        """
        result = RegexPatterns.TIME_PATTERN.search(eta)
        if not result:
            raise ValueError("String '{}' does not match the eta pattern".format(eta))
        # the [:-1] below removes the last character (the unit letter)
        eta_d = int((result.group("eta_d") or '0d')[:-1])
        eta_h = int((result.group("eta_h") or '0h')[:-1])
        eta_m = int((result.group("eta_m") or '0m')[:-1])
        eta_s = int((result.group("eta_s") or '0s')[:-1])
        return eta_d * 24 * 3600 + eta_h * 3600 + eta_m * 60 + eta_s

    @staticmethod
    def parse_chunk_at(match) -> LftpJobStatus.TransferState:
        """
        Parse transfer state from 'at' format chunk data.

        :param match: Regex match object from CHUNK_AT pattern
        :return: TransferState with available data
        """
        speed = None
        if match.group("speed"):
            speed = TransferStateParser.size_to_bytes(match.group("speed"))
        eta = None
        if match.group("eta"):
            eta = TransferStateParser.eta_to_seconds(match.group("eta"))
        return LftpJobStatus.TransferState(None, None, None, speed, eta)

    @staticmethod
    def parse_chunk_got(match) -> LftpJobStatus.TransferState:
        """
        Parse transfer state from 'got' format chunk data.

        :param match: Regex match object from CHUNK_GOT pattern
        :return: TransferState with size, percent, speed, and eta
        """
        size_local = int(match.group("szlocal"))
        size_remote = int(match.group("szremote"))
        percent_local = int(match.group("pctlocal"))
        speed = None
        if match.group("speed"):
            speed = TransferStateParser.size_to_bytes(match.group("speed"))
        eta = None
        if match.group("eta"):
            eta = TransferStateParser.eta_to_seconds(match.group("eta"))
        return LftpJobStatus.TransferState(size_local, size_remote, percent_local, speed, eta)

class BaseJobParser(ABC):
    """
    Abstract base class for job-specific parsers.
    """

    @abstractmethod
    def can_parse(self, line: str) -> bool:
        """
        Check if this parser can handle the given line.

        :param line: Line to check
        :return: True if this parser can handle the line
        """
        pass

    @abstractmethod
    def parse_header(self, line: str, lines: List[str]) -> Optional[LftpJobStatus]:
        """
        Parse a job header line and return the job status.

        :param line: Header line to parse
        :param lines: Remaining lines (may be modified)
        :return: LftpJobStatus or None if parsing failed
        """
        pass

class PgetJobParser(BaseJobParser):
    """
    Parser for pget (single file download) jobs.
    """

    def can_parse(self, line: str) -> bool:
        return RegexPatterns.PGET_HEADER.match(line) is not None

    def parse_header(self, line: str, lines: List[str]) -> Optional[LftpJobStatus]:
        result = RegexPatterns.PGET_HEADER.search(line)
        if not result:
            return None

        # Next line must be the sftp line
        if len(lines) < 1 or "sftp" not in lines[0]:
            raise ValueError("Missing the 'sftp' line for pget header '{}'".format(line))
        lines.pop(0)  # pop the 'sftp' line

        # Data line may not exist
        result_at = None
        result_at2 = None
        result_got = None
        if lines:
            data_line = lines.pop(0)
            result_at = RegexPatterns.CHUNK_AT.search(data_line)
            result_at2 = RegexPatterns.CHUNK_AT2.search(data_line)
            result_got = RegexPatterns.CHUNK_GOT.search(data_line)

        id_ = int(result.group("id"))
        name = os.path.basename(os.path.normpath(result.group("remote")))
        flags = result.group("flags")
        status = LftpJobStatus(
            job_id=id_,
            job_type=LftpJobStatus.Type.PGET,
            state=LftpJobStatus.State.RUNNING,
            name=name,
            flags=flags
        )

        transfer_state = self._parse_transfer_data(result, result_at, result_at2, result_got, name)
        status.total_transfer_state = transfer_state
        return status

    def _parse_transfer_data(
            self, header_result, result_at, result_at2, result_got, name: str
    ) -> LftpJobStatus.TransferState:
        """Parse transfer data from various chunk formats."""
        if result_at:
            if header_result.group("remote") != result_at.group("name"):
                raise ValueError("Mismatch between pget names '{}' vs '{}'".format(
                    header_result.group("remote"), result_at.group("name")
                ))
            return TransferStateParser.parse_chunk_at(result_at)

        elif result_at2:
            if header_result.group("remote") != result_at2.group("name"):
                raise ValueError("Mismatch between pget names '{}' vs '{}'".format(
                    header_result.group("remote"), result_at2.group("name")
                ))
            return LftpJobStatus.TransferState(None, None, None, None, None)

        elif result_got:
            got_group_basename = os.path.basename(os.path.normpath(result_got.group("name")))
            if got_group_basename != name:
                raise ValueError("Mismatch: filename '{}' but chunk data for '{}'".format(
                    name, got_group_basename
                ))
            return TransferStateParser.parse_chunk_got(result_got)

        # No data line at all
        return LftpJobStatus.TransferState(None, None, None, None, None)

class MirrorJobParser(BaseJobParser):
    """
    Parser for mirror (directory download) jobs.
    """

    def can_parse(self, line: str) -> bool:
        return (RegexPatterns.MIRROR_HEADER.match(line) is not None or
                RegexPatterns.MIRROR_FL_HEADER.match(line) is not None)

    def parse_header(self, line: str, lines: List[str]) -> Optional[LftpJobStatus]:
        # Try the more specific mirror header first
        result = RegexPatterns.MIRROR_HEADER.search(line)
        if result:
            return self._parse_downloading_header(result)

        # Try the file list header (connecting state)
        result = RegexPatterns.MIRROR_FL_HEADER.search(line)
        if result:
            return self._parse_connecting_header(result, lines)

        return None

    def _parse_downloading_header(self, result) -> LftpJobStatus:
        """Parse mirror header when download is in progress."""
        id_ = int(result.group("id"))
        name = os.path.basename(os.path.normpath(result.group("remote")))
        flags = result.group("flags")
        status = LftpJobStatus(
            job_id=id_,
            job_type=LftpJobStatus.Type.MIRROR,
            state=LftpJobStatus.State.RUNNING,
            name=name,
            flags=flags
        )
        size_local = TransferStateParser.size_to_bytes(result.group("szlocal"))
        size_remote = TransferStateParser.size_to_bytes(result.group("szremote"))
        percent_local = int(result.group("pctlocal"))
        speed = None
        if result.group("speed"):
            speed = TransferStateParser.size_to_bytes(result.group("speed"))
        transfer_state = LftpJobStatus.TransferState(
            size_local, size_remote, percent_local, speed, None
        )
        status.total_transfer_state = transfer_state
        return status

    def _parse_connecting_header(self, result, lines: List[str]) -> LftpJobStatus:
        """Parse mirror header when connecting or getting file list."""
        # There may be a 'Connecting' or 'cd' line ahead, but not always
        if lines and (
                lines[0].startswith("Getting file list") or
                lines[0].startswith("cd ")
        ):
            lines.pop(0)  # pop the connecting line
        id_ = int(result.group("id"))
        name = os.path.basename(os.path.normpath(result.group("remote")))
        flags = result.group("flags")
        return LftpJobStatus(
            job_id=id_,
            job_type=LftpJobStatus.Type.MIRROR,
            state=LftpJobStatus.State.RUNNING,
            name=name,
            flags=flags
        )

class JobParserFactory:
    """
    Factory for creating appropriate job parsers based on line content.
    """

    def __init__(self):
        self._parsers = [
            PgetJobParser(),
            MirrorJobParser()
        ]

    def get_parser(self, line: str) -> Optional[BaseJobParser]:
        """
        Get the appropriate parser for the given line.

        :param line: Line to find a parser for
        :return: Parser that can handle the line, or None
        """
        for parser in self._parsers:
            if parser.can_parse(line):
                return parser
        return None

class QueueParser:
    """
    Parser for LFTP queue output.
    """

    @staticmethod
    def parse(lines: List[str]) -> List[LftpJobStatus]:
        """
        Parse queue section of LFTP jobs output.

        :param lines: Lines to parse (will be modified)
        :return: List of queued job statuses
        """
        queue = []

        if len(lines) == 1:
            if not RegexPatterns.QUEUE_DONE.match(lines[0]):
                raise ValueError("Unrecognized line '{}'".format(lines[0]))
            lines.pop(0)

        if lines:
            queue = QueueParser._parse_queue_body(lines)

        return queue

    @staticmethod
    def _parse_queue_body(lines: List[str]) -> List[LftpJobStatus]:
        """Parse the main body of the queue section."""
        queue = []

        # Look for the header lines
        if len(lines) < 2:
            raise ValueError("Missing queue header")

        line = lines.pop(0)
        if not RegexPatterns.QUEUE_HEADER1.match(line):
            raise ValueError("Missing queue header line 1: {}".format(line))
        line = lines.pop(0)
        if not RegexPatterns.QUEUE_HEADER2.match(line):
            raise ValueError("Missing queue header line 2: {}".format(line))
        if not lines:
            raise ValueError("Missing queue status")

        # Look for 'Now executing' lines
        line = lines.pop(0)
        if re.match("Queue is stopped.", line):
            pass  # Nothing to do
        elif re.match("Now executing:", line):
            # Remove any more lines associated with 'now executing'
            while lines and re.match(r"^-\[\d+\]", lines[0]):
                lines.pop(0)

        # Look for the actual queue
        if lines and re.match("Commands queued:", lines[0]):
            lines.pop(0)
            if not lines:
                raise ValueError("Missing queued commands")
            queue = QueueParser._parse_queued_commands(lines)

        # Look for the done line
        if lines and RegexPatterns.QUEUE_DONE.match(lines[0]):
            lines.pop(0)

        return queue

    @staticmethod
    def _parse_queued_commands(lines: List[str]) -> List[LftpJobStatus]:
        """Parse individual queued commands."""
        queue = []

        while lines:
            line = lines[0]
            if re.match(r"^\d+\.", line):
                lines.pop(0)
                status = QueueParser._parse_queue_line(line)
                if status:
                    queue.append(status)
            elif re.match(r"^cd\s.*$", line):
                # 'cd' line after pget, ignore
                lines.pop(0)
            else:
                # no match, exit loop
                break

        return queue

    @staticmethod
    def _parse_queue_line(line: str) -> Optional[LftpJobStatus]:
        """Parse a single queue line."""
        result_pget = RegexPatterns.QUEUE_PGET.match(line)
        result_mirror = RegexPatterns.QUEUE_MIRROR.match(line)

        if result_pget:
            type_ = LftpJobStatus.Type.PGET
            result = result_pget
        elif result_mirror:
            type_ = LftpJobStatus.Type.MIRROR
            result = result_mirror
        else:
            raise ValueError("Failed to parse queue line: {}".format(line))

        id_ = int(result.group("id"))
        name = os.path.basename(os.path.normpath(result.group("remote")))
        flags = result.group("flags")
        return LftpJobStatus(
            job_id=id_,
            job_type=type_,
            state=LftpJobStatus.State.QUEUED,
            name=name,
            flags=flags
        )

class ActiveJobsParser:
    """
    Parser for active LFTP jobs output.
    """

    def __init__(self):
        self._factory = JobParserFactory()

    def parse(self, lines: List[str]) -> List[LftpJobStatus]:
        """
        Parse active jobs section of LFTP jobs output.

        :param lines: Lines to parse (will be modified)
        :return: List of running job statuses
        """
        jobs = []
        prev_job = None

        while lines:
            line = lines.pop(0)

            # First line must be a valid job header
            if not prev_job:
                parser = self._factory.get_parser(line)
                if not parser:
                    raise ValueError("First line is not a matching header '{}'".format(line))

            # Try to parse as a job header
            parser = self._factory.get_parser(line)
            if parser:
                status = parser.parse_header(line, lines)
                if status:
                    jobs.append(status)
                    prev_job = status
                    continue

            # Try to parse as file transfer data
            if self._handle_file_transfer(line, lines, prev_job):
                continue

            # Try to handle mirror/chunk/chmod lines
            if self._handle_auxiliary_lines(line, lines, prev_job):
                continue

            # Check for done line
            result = RegexPatterns.QUEUE_DONE.match(line)
            if result:
                if lines:
                    raise ValueError("There are more lines after the 'Done' line")
                continue

            # If we got here, we don't know how to parse this line
            raise ValueError("Unable to parse line '{}'".format(line))

        return jobs

    def _handle_file_transfer(
            self, line: str, lines: List[str], prev_job: Optional[LftpJobStatus]
    ) -> bool:
        """Handle file transfer lines."""
        result = RegexPatterns.TRANSFER_FILENAME.search(line)
        if not result:
            return False

        name = result.group("name")
        if not lines:
            raise ValueError("Missing chunk data for filename '{}'".format(name))
        data_line = lines.pop(0)

        result_at = RegexPatterns.CHUNK_AT.search(data_line)
        result_at2 = RegexPatterns.CHUNK_AT2.search(data_line)
        result_got = RegexPatterns.CHUNK_GOT.search(data_line)

        file_status = self._parse_file_transfer_state(name, result_at, result_at2, result_got)
        if file_status:
            prev_job.add_active_file_transfer_state(name, file_status)
        return True

    def _parse_file_transfer_state(
            self, name: str, result_at, result_at2, result_got
    ) -> Optional[LftpJobStatus.TransferState]:
        """Parse file transfer state from chunk match results."""
        basename = os.path.basename(os.path.normpath(name))

        if result_at:
            if result_at.group("name") != basename:
                raise ValueError("Mismatch: filename '{}' but chunk data for '{}'".format(
                    name, result_at.group("name")
                ))
            return TransferStateParser.parse_chunk_at(result_at)

        elif result_at2:
            if result_at2.group("name") != basename:
                raise ValueError("Mismatch: filename '{}' but chunk data for '{}'".format(
                    name, result_at2.group("name")
                ))
            return LftpJobStatus.TransferState(None, None, None, None, None)

        elif result_got:
            if result_got.group("name") != basename:
                raise ValueError("Mismatch: filename '{}' but chunk data for '{}'".format(
                    name, result_got.group("name")
                ))
            return TransferStateParser.parse_chunk_got(result_got)

        raise ValueError("Missing chunk data for filename '{}'".format(name))

    def _handle_auxiliary_lines(
            self, line: str, lines: List[str], prev_job: Optional[LftpJobStatus]
    ) -> bool:
        """Handle mirror, chunk, chmod, and other auxiliary lines."""
        # Mirror subdir line (ignore)
        if RegexPatterns.MIRROR_SUBDIR.search(line):
            return True

        # Empty mirror line
        result = RegexPatterns.MIRROR_EMPTY.search(line)
        if result:
            name = result.group("name")
            if lines:
                if ("Getting file list" in lines[0] or
                        lines[0].startswith("cd ") or
                        lines[0] == "{}:".format(name) or
                        lines[0].startswith("mkdir ")):
                    lines.pop(0)
            return True

        # Chunk header line (ignore with next line)
        result = RegexPatterns.CHUNK_HEADER.search(line)
        if result:
            if not lines:
                raise ValueError("Missing data line for chunk '{}'".format(line))
            lines.pop(0)
            return True

        # Chmod line
        result = RegexPatterns.CHMOD_HEADER.search(line)
        if result:
            name = result.group("name")
            if not lines or not lines[0].startswith("file:"):
                raise ValueError("Missing 'file:' line for chmod '{}'".format(name))
            lines.pop(0)
            if lines:
                result_chmod = RegexPatterns.CHMOD_PATTERN.search(lines[0])
                if result_chmod:
                    name_chmod = result_chmod.group("name")
                    if name != name_chmod:
                        raise ValueError("Mismatch in names chmod '{}'".format(name))
                    lines.pop(0)
            return True

        return False

class LftpJobStatusParser:
    """
    Parses the output of lftp's "jobs -v" command into a list of LftpJobStatus objects.

    This is the main entry point for parsing LFTP job status output.
    """

    def __init__(self):
        self.logger = logging.getLogger("LftpJobStatusParser")
        self._active_jobs_parser = ActiveJobsParser()

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("LftpJobStatusParser")

    @staticmethod
    def _size_to_bytes(size: str) -> int:
        """
        Parse the size string and return number of bytes.
        Maintained for backward compatibility.
        """
        return TransferStateParser.size_to_bytes(size)

    @staticmethod
    def _eta_to_seconds(eta: str) -> int:
        """
        Parse the time string and return number of seconds.
        Maintained for backward compatibility.
        """
        return TransferStateParser.eta_to_seconds(eta)

    def parse(self, output: str) -> List[LftpJobStatus]:
        """
        Parse LFTP jobs -v output and return list of job statuses.

        :param output: Raw output from 'jobs -v' command
        :return: List of LftpJobStatus objects
        """
        statuses = list()
        lines = self._preprocess_lines(output)

        try:
            statuses += QueueParser.parse(lines)
            statuses += self._active_jobs_parser.parse(lines)
        except ValueError as e:
            self.logger.error("LftpJobStateParser error: {}".format(str(e)))
            self.logger.error("Status:\n{}".format(output))
            raise LftpJobStatusParserError("Error parsing lftp job status")
        return statuses

    @staticmethod
    def _preprocess_lines(output: str) -> List[str]:
        """
        Preprocess raw output into cleaned lines ready for parsing.

        :param output: Raw output string
        :return: List of cleaned lines
        """
        lines = [s.strip() for s in output.splitlines()]
        lines = list(filter(None, lines))  # remove blank lines
        # remove all lines before the first 'jobs -v'
        start = next((i + 1 for i, line in enumerate(lines) if line == "jobs -v"), 0)
        lines = lines[start:]
        # remove any remaining 'jobs -v' lines
        lines = list(filter(lambda s: s != "jobs -v", lines))
        # remove any remaining log lines
        lines = filter(
            lambda s: not re.match(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}.*\s->\s.*$", s),
            lines
        )
        return list(lines)
