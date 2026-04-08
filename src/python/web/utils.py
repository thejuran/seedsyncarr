# Copyright 2017, Inderpreet Singh, All rights reserved.

import logging
from queue import Queue, Empty, Full
from typing import TypeVar, Generic, Optional


T = TypeVar('T')


# Default maximum queue size to prevent unbounded memory growth
DEFAULT_QUEUE_MAXSIZE = 1000


class StreamQueue(Generic[T]):
    """
    A queue that transfers events from one thread to another.
    Useful for web streams that wait for listener events from other threads.
    The producer thread calls put() to insert events. The consumer stream
    calls get_next_event() to receive event in its own thread.

    Uses a bounded queue with configurable maxsize to prevent memory growth
    from slow or disconnected clients. When the queue is full, oldest events
    are dropped to make room for new ones.
    """
    def __init__(self, maxsize: int = DEFAULT_QUEUE_MAXSIZE):
        """
        Initialize the stream queue.

        :param maxsize: Maximum number of events to hold. When exceeded, oldest
                        events are dropped. Set to 0 for unlimited (not recommended).
        """
        self.__queue = Queue(maxsize=maxsize)
        self.__maxsize = maxsize
        self.__dropped_count = 0
        self.__logger = logging.getLogger("StreamQueue")

    def put(self, event: T):
        """
        Add an event to the queue.
        If the queue is full, drops the oldest event to make room.
        """
        if self.__maxsize > 0:
            # Try to add without blocking
            try:
                self.__queue.put(event, block=False)
            except Full:
                # Queue is full - drop oldest event and retry
                try:
                    self.__queue.get(block=False)
                    self.__dropped_count += 1
                    if self.__dropped_count % 100 == 1:
                        self.__logger.warning(
                            "StreamQueue overflow: dropped {} events total".format(
                                self.__dropped_count
                            )
                        )
                except Empty:
                    pass
                # Now try to add again (should succeed after removing one)
                try:
                    self.__queue.put(event, block=False)
                except Full:
                    # Still full (shouldn't happen), drop this event
                    self.__dropped_count += 1
        else:
            # Unlimited queue (original behavior, not recommended)
            self.__queue.put(event)

    def get_next_event(self) -> Optional[T]:
        """
        Returns the next event if there is one, otherwise returns None
        :return:
        """
        try:
            return self.__queue.get(block=False)
        except Empty:
            return None

    def get_dropped_count(self) -> int:
        """
        Returns the total number of events that have been dropped due to
        queue overflow. Useful for monitoring.
        :return: Number of dropped events
        """
        return self.__dropped_count

    def get_queue_size(self) -> int:
        """
        Returns the current number of events in the queue.
        Useful for monitoring.
        :return: Current queue size
        """
        return self.__queue.qsize()

    def get_maxsize(self) -> int:
        """
        Returns the maximum queue size.
        :return: Maximum queue size (0 means unlimited)
        """
        return self.__maxsize
