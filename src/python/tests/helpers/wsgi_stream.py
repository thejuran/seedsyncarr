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


def open_sse_stream(web_app, path: str = "/server/stream"):
    """
    Open an SSE stream WITHOUT draining it, so a test can simulate a stalled
    consumer: pull one chunk, stall while events are produced server-side,
    then resume pulling later.

    Bottle primes the generator to its first yield when the app is called, so
    by the time this function returns, handler setup() has already run (the
    initial `model-init`/first status/etc. is queued up at the generator's
    first yield point). The generator stays suspended there -- a literal
    stalled consumer -- until the caller calls next() on it.

    The caller owns cleanup and MUST call web_app.stop() and body.close() (if
    body has a close() method) in a finally block, so the stream's cleanup
    (e.g. remove_model_listener) runs on every path, including early returns
    and exceptions.

    Returns:
        (response_started, body) where response_started is a list of
        (status, headers_dict) tuples (populated once the generator is first
        advanced far enough to call start_response) and body is the raw,
        un-iterated WSGI generator/iterable returned by web_app(environ,
        start_response).
    """
    environ = make_wsgi_environ(path=path)

    response_started = []

    def start_response(status, headers, exc_info=None):
        response_started.append((status, dict(headers)))

    body = web_app(environ, start_response)
    return response_started, body
