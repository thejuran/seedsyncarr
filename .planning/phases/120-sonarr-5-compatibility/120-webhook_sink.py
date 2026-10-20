"""Disposable webhook sink that captures raw POST bodies to private files.

Usage (stdlib only; e.g. inside the app image via --entrypoint python3):
    python3 120-webhook_sink.py [<dir> [<port>]]      # defaults: /sink 8080

Binds 0.0.0.0:<port>. <dir> must already exist (create it under umask 077);
the sink never creates it.

POST <any path>:
  - Reads exactly Content-Length bytes. Missing or malformed length -> 411/400.
    Length above 1_048_576 bytes (1 MB) -> 413 without reading or storing it.
  - Writes the body verbatim to <dir>/<UTC timestamp>-<counter>.json, created
    with O_EXCL and mode 0600.
  - Writes a sibling <same stem>.meta (also O_EXCL 0600) holding the request
    path and the User-Agent header. User-Agent is the ONLY header stored; it
    carries the sending application's version (e.g. Sonarr/<version>).
  - Responds 200 "OK".
GET /healthz -> 200 "ok". Anything else -> 404.

Request logging is silenced: no body, header or path is ever printed.
SIGTERM / SIGINT exit cleanly.
"""
import itertools
import os
import signal
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 1_048_576  # 1 MB, same cap as the app's webhook handler
DEFAULT_DIR = "/sink"
DEFAULT_PORT = 8080

_counter = itertools.count(1)
_counter_lock = threading.Lock()


def _next_stem():
    with _counter_lock:
        n = next(_counter)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return "{}-{:04d}".format(ts, n)


def _write_exclusive_0600(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def _single_line(value):
    return value.replace("\r", " ").replace("\n", " ")


class SinkHandler(BaseHTTPRequestHandler):
    sink_dir = DEFAULT_DIR
    timeout = 30  # drop stalled clients

    def _reply(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (http.server naming)
        if self.path == "/healthz":
            self._reply(200, b"ok")
        else:
            self._reply(404, b"not found")

    def do_POST(self):  # noqa: N802 (http.server naming)
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            self.close_connection = True
            self._reply(411, b"length required")
            return
        try:
            length = int(raw_length)
        except ValueError:
            length = -1
        if length < 0:
            self.close_connection = True
            self._reply(400, b"bad length")
            return
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._reply(413, b"payload too large")
            return

        body = self.rfile.read(length)
        if len(body) != length:
            self.close_connection = True
            self._reply(400, b"short body")
            return

        stem = os.path.join(self.sink_dir, _next_stem())
        _write_exclusive_0600(stem + ".json", body)
        user_agent = self.headers.get("User-Agent") or ""
        meta = "path={}\nuser_agent={}\n".format(_single_line(self.path), _single_line(user_agent))
        _write_exclusive_0600(stem + ".meta", meta.encode("utf-8"))
        self._reply(200, b"OK")

    def log_message(self, format, *args):  # noqa: A002 - silence the handler
        pass


def _exit_on_signal(signum, frame):
    sys.exit(0)


def main() -> int:
    sink_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    if not os.path.isdir(sink_dir):
        sys.stderr.write("ERROR sink directory missing\n")
        return 2
    SinkHandler.sink_dir = sink_dir

    signal.signal(signal.SIGTERM, _exit_on_signal)
    signal.signal(signal.SIGINT, _exit_on_signal)
    server = ThreadingHTTPServer(("0.0.0.0", port), SinkHandler)  # noqa: S104 - container-internal sink
    server.daemon_threads = True
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
