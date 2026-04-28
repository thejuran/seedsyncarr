import json
import logging
import time
import functools
from threading import Lock
from typing import Callable, List

from bottle import HTTPResponse

logger = logging.getLogger(__name__)


def rate_limit(max_requests: int, window_seconds: float) -> Callable:
    """
    Sliding-window rate limiter decorator factory.

    Args:
        max_requests: Maximum allowed requests within the window.
        window_seconds: Window duration in seconds.

    Returns:
        A decorator that wraps a Bottle handler. Returns HTTP 429 when
        the limit is exceeded.
    """
    def decorator(func: Callable) -> Callable:
        request_times: List[float] = []
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            with lock:
                request_times[:] = [t for t in request_times if now - t < window_seconds]
                if len(request_times) >= max_requests:
                    logger.warning("Rate limit exceeded for %s", func.__name__)
                    return HTTPResponse(
                        body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
                        status=429,
                        content_type="application/json"
                    )
                request_times.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator
