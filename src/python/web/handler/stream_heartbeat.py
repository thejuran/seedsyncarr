# Copyright 2017, Inderpreet Singh, All rights reserved.

import time
from typing import Optional

from ..web_app import IStreamHandler
from ..serialize import Serialize
from common import overrides


class SerializeHeartbeat(Serialize):
    """
    Serializer for heartbeat events
    """
    __EVENT_PING = "ping"

    def ping(self, timestamp: float) -> str:
        return self._sse_pack(event=SerializeHeartbeat.__EVENT_PING, data=str(timestamp))


class HeartbeatStreamHandler(IStreamHandler):
    """
    Stream handler that sends periodic heartbeat/ping events to keep
    the SSE connection alive through proxies and firewalls.

    Without periodic activity, idle SSE connections may be closed by:
    - Reverse proxies (nginx default: 60s)
    - Load balancers
    - Firewalls
    - Browser connection timeouts

    The client can also use these heartbeats to detect stale connections
    and proactively reconnect.
    """
    # Send heartbeat every 15 seconds - frequent enough to keep most
    # proxies/firewalls happy, but not so frequent as to waste bandwidth
    HEARTBEAT_INTERVAL_S = 15

    def __init__(self):
        self._serialize = SerializeHeartbeat()
        self._last_heartbeat_time: Optional[float] = None

    @overrides(IStreamHandler)
    def setup(self):
        # Send initial heartbeat immediately on connection
        self._last_heartbeat_time = None

    @overrides(IStreamHandler)
    def get_value(self) -> Optional[str]:
        current_time = time.time()

        # Send heartbeat if enough time has passed
        if (self._last_heartbeat_time is None or
                (current_time - self._last_heartbeat_time) >= self.HEARTBEAT_INTERVAL_S):
            self._last_heartbeat_time = current_time
            return self._serialize.ping(current_time)

        return None

    @overrides(IStreamHandler)
    def cleanup(self):
        pass
