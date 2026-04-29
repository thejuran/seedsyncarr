import json
import logging
import math
import time
import functools
from collections import deque
from collections.abc import Callable
from threading import Lock
from typing import ParamSpec, TypeVar

from bottle import HTTPResponse

_P = ParamSpec("_P")
_R = TypeVar("_R")

logger = logging.getLogger(__name__)


def rate_limit(max_requests: int, window_seconds: float) -> Callable[[Callable[_P, _R]], Callable[_P, _R | HTTPResponse]]:
    if max_requests < 1:
        raise ValueError("max_requests must be >= 1, got {}".format(max_requests))
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0, got {}".format(window_seconds))

    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R | HTTPResponse]:
        request_times: deque[float] = deque()
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R | HTTPResponse:
            with lock:
                now = time.time()
                cutoff = now - window_seconds
                while request_times and request_times[0] < cutoff:
                    request_times.popleft()
                if len(request_times) >= max_requests:
                    retry_after = max(1, math.ceil(request_times[0] - cutoff))
                    logger.warning("Rate limit exceeded for %s", func.__name__)
                    return HTTPResponse(
                        body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
                        status=429,
                        headers={"Retry-After": str(retry_after)},
                        content_type="application/json"
                    )
                request_times.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator
