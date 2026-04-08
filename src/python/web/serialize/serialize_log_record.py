import json
import logging
import re

from .serialize import Serialize

class SerializeLogRecord(Serialize):
    """
    This class defines the serialization interface between python backend
    and the EventSource client frontend for the log stream.
    """
    # Event keys
    __EVENT_RECORD = "log-record"

    # Data keys
    __KEY_TIME = "time"
    __KEY_LEVEL_NAME = "level_name"
    __KEY_LOGGER_NAME = "logger_name"
    __KEY_MESSAGE = "message"
    __KEY_EXCEPTION_TRACEBACK = "exc_tb"

    def __init__(self):
        super().__init__()
        # logging formatter to generate exception traceback
        self.__log_formatter = logging.Formatter()

    @staticmethod
    def _redact_sensitive(message: str) -> str:
        """
        Scrub credential patterns from a log message string before it reaches
        the SSE stream.  Four patterns are handled:

        1. LFTP ``-u username,password`` argument — the password is the token
           immediately after the comma.  Only the password portion is replaced
           so the username is still visible for debugging.

        2. Generic ``password=<value>`` / ``password: <value>`` patterns that
           may appear in exception messages or other log output.

        3. SSH topology: ``sftp://user@host/path`` URLs emitted by LFTP — the
           entire ``user@host/path`` portion is replaced with redacted tokens
           while the ``sftp://`` scheme prefix is preserved.

        4. SSH topology: bare ``user@host`` tokens in SSH/SCP command output
           (e.g. ``['ssh', '-p', '22', 'user@host', 'cmd']``).  The lookbehind
           ``(?<=[\\s'\\"\\[])`` ensures the token is preceded by whitespace,
           a quote, or an opening bracket — which prevents false positives on
           filenames such as ``file@720p.mkv`` where ``@`` is preceded by a
           word character.
        """
        # LFTP: -u username,secretpass  →  -u username,**REDACTED**
        message = re.sub(r'(-u\s+\S+,)\S+', r'\1**REDACTED**', message)
        # Generic: password=secret  /  password: secret (case-insensitive)
        message = re.sub(
            r'(password[=:]\s*)\S+', r'\1**REDACTED**', message,
            flags=re.IGNORECASE
        )
        # SSH topology: sftp://user@host URLs (LFTP connection strings)
        message = re.sub(r'sftp://\S+@\S+', 'sftp://**REDACTED**@**REDACTED**', message)
        # SSH topology: user@host tokens (preceded by whitespace/quote/bracket, not mid-word)
        # Covers: 'user@host', "user@host:path", lftp user@host:~>
        # Does NOT match: file@720p.mkv or release@1.0.tar.gz (RHS must start with a
        # letter, not a digit — hostnames start with letters, version strings do not)
        message = re.sub(
            r"(?<=[\s'\"\[])(\w[\w.\-]*)@([a-zA-Z][\w.\-]*)",
            '**REDACTED**@**REDACTED**',
            message
        )
        return message

    def record(self, record: logging.LogRecord) -> str:
        json_dict = dict()
        json_dict[SerializeLogRecord.__KEY_TIME] = str(record.created)
        json_dict[SerializeLogRecord.__KEY_LEVEL_NAME] = record.levelname
        json_dict[SerializeLogRecord.__KEY_LOGGER_NAME] = record.name
        json_dict[SerializeLogRecord.__KEY_MESSAGE] = SerializeLogRecord._redact_sensitive(
            record.getMessage()
        )
        exc_text = None
        if record.exc_text:
            exc_text = SerializeLogRecord._redact_sensitive(record.exc_text)
        elif record.exc_info:
            exc_text = SerializeLogRecord._redact_sensitive(
                self.__log_formatter.formatException(record.exc_info)
            )
        json_dict[SerializeLogRecord.__KEY_EXCEPTION_TRACEBACK] = exc_text

        record_json = json.dumps(json_dict)
        return self._sse_pack(event=SerializeLogRecord.__EVENT_RECORD, data=record_json)
