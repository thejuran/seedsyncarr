"""
WSGI iterator harness for SSE streaming tests.

Calls web_app(environ, start_response) directly to obtain the SSE generator,
then iterates it in the test thread. A Timer calls web_app.stop() after
stop_after_s seconds to terminate the generator loop cleanly.
"""
import io
from threading import Timer


def make_wsgi_environ(path: str = "/server/stream", method: str = "GET") -> dict:
    """Build a minimal Bottle-compatible WSGI environ dict."""
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.url_scheme": "http",
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "HTTP_HOST": "localhost:8080",
    }


def collect_sse_chunks(web_app, path: str = "/server/stream", stop_after_s: float = 0.5):
    """
    Iterate the SSE generator and collect all yielded chunks.

    Timer fires after stop_after_s seconds, calls web_app.stop() which sets
    _stop_flag = True via object.__setattr__, causing the while-not-stop_flag
    loop in __web_stream to exit cleanly.

    Returns:
        (response_started, chunks) where response_started is a list of
        (status, headers_dict) tuples and chunks is a list of bytes/str.
    """
    environ = make_wsgi_environ(path=path)
    Timer(stop_after_s, web_app.stop).start()

    response_started = []

    def start_response(status, headers, exc_info=None):
        response_started.append((status, dict(headers)))

    chunks = list(web_app(environ, start_response))
    return response_started, chunks
