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


def rate_limit(
    max_requests: int,
    window_seconds: float,
    *,
    logger: logging.Logger,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R | HTTPResponse]]:
    """Sliding-window rate limit decorator factory.

    The caller must pass its own app-tree logger so a rate-limit warning
    reaches the persisted app log and the UI log stream instead of a
    detached module logger (LOG-01; 122-14 WR-01).
    """
    if logger is None:
        raise TypeError("rate_limit requires a logger")
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
