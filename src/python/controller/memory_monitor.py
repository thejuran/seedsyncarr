# Copyright 2017, Inderpreet Singh, All rights reserved.

import logging
import sys
import time
from dataclasses import dataclass
from typing import Optional, Dict, Callable

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    # resource module not available on Windows
    HAS_RESOURCE = False


@dataclass
class MemoryStats:
    """Container for memory statistics snapshot."""
    timestamp: float
    process_memory_mb: float
    # Data structure sizes
    downloaded_files_count: int
    extracted_files_count: int
    model_files_count: int
    lftp_statuses_count: int
    stream_queues_stats: Dict[str, Dict[str, int]]


class MemoryMonitor:
    """
    Monitors memory usage and data structure sizes to detect potential leaks.

    This utility periodically logs resource usage and the sizes of key data
    structures that could grow unbounded if not properly managed.
    """

    # Default interval between logs (5 minutes)
    DEFAULT_LOG_INTERVAL_SECONDS = 300

    def __init__(self, log_interval_seconds: int = DEFAULT_LOG_INTERVAL_SECONDS):
        """
        Initialize the memory monitor.

        :param log_interval_seconds: Minimum seconds between log outputs
        """
        self.logger = logging.getLogger("MemoryMonitor")
        self.__log_interval = log_interval_seconds
        self.__last_log_time: Optional[float] = None
        self.__data_source_callbacks: Dict[str, Callable[[], int]] = {}
        self.__stream_queue_callbacks: Dict[str, Callable[[], Dict[str, int]]] = {}
        self.__stats_history: list = []
        self.__max_history_size = 100

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("MemoryMonitor")

    def register_data_source(self, name: str, size_callback: Callable[[], int]):
        """
        Register a data source to monitor.

        :param name: Name of the data source (for logging)
        :param size_callback: Callable that returns the current size/count
        """
        self.__data_source_callbacks[name] = size_callback

    def register_stream_queue(self, name: str, stats_callback: Callable[[], Dict[str, int]]):
        """
        Register a stream queue to monitor.

        :param name: Name of the queue (for logging)
        :param stats_callback: Callable that returns dict with 'size', 'dropped', 'maxsize'
        """
        self.__stream_queue_callbacks[name] = stats_callback

    def get_process_memory_mb(self) -> float:
        """
        Get the current process memory usage in MB.

        :return: Memory usage in megabytes
        """
        if HAS_RESOURCE:
            # On Unix-like systems, use resource module
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            # maxrss is in kilobytes on Linux, bytes on macOS
            if sys.platform == 'darwin':
                return rusage.ru_maxrss / (1024 * 1024)
            else:
                return rusage.ru_maxrss / 1024
        else:
            # Fallback: try to read from /proc on Linux
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            # VmRSS is in kB
                            return int(line.split()[1]) / 1024
            except (FileNotFoundError, IOError):
                pass
            return 0.0

    def collect_stats(self) -> MemoryStats:
        """
        Collect current memory and data structure statistics.

        :return: MemoryStats snapshot
        """
        # Collect data source sizes
        data_sizes = {}
        for name, callback in self.__data_source_callbacks.items():
            try:
                data_sizes[name] = callback()
            except Exception as e:
                self.logger.debug("Error collecting {} size: {}".format(name, e))
                data_sizes[name] = -1

        # Collect stream queue stats
        queue_stats = {}
        for name, callback in self.__stream_queue_callbacks.items():
            try:
                queue_stats[name] = callback()
            except Exception as e:
                self.logger.debug("Error collecting {} stats: {}".format(name, e))
                queue_stats[name] = {'size': -1, 'dropped': -1, 'maxsize': -1}

        stats = MemoryStats(
            timestamp=time.time(),
            process_memory_mb=self.get_process_memory_mb(),
            downloaded_files_count=data_sizes.get('downloaded_files', 0),
            extracted_files_count=data_sizes.get('extracted_files', 0),
            model_files_count=data_sizes.get('model_files', 0),
            lftp_statuses_count=data_sizes.get('lftp_statuses', 0),
            stream_queues_stats=queue_stats
        )

        # Store in history
        self.__stats_history.append(stats)
        if len(self.__stats_history) > self.__max_history_size:
            self.__stats_history.pop(0)

        return stats

    def log_stats_if_due(self) -> bool:
        """
        Log memory statistics if enough time has passed since the last log.

        :return: True if stats were logged, False otherwise
        """
        current_time = time.time()
        if self.__last_log_time is not None:
            elapsed = current_time - self.__last_log_time
            if elapsed < self.__log_interval:
                return False

        stats = self.collect_stats()
        self.__last_log_time = current_time

        # Collect all data source values
        data_values = {}
        for name, callback in self.__data_source_callbacks.items():
            try:
                data_values[name] = callback()
            except Exception:
                data_values[name] = -1

        # Log the statistics
        self.logger.info(
            "Memory stats: process={:.1f}MB, downloaded_files={}, "
            "extracted_files={}, model_files={}, lftp_statuses={}".format(
                stats.process_memory_mb,
                stats.downloaded_files_count,
                stats.extracted_files_count,
                stats.model_files_count,
                stats.lftp_statuses_count
            )
        )

        # Log eviction stats if any evictions have occurred
        downloaded_evictions = data_values.get('downloaded_evictions', 0)
        extracted_evictions = data_values.get('extracted_evictions', 0)
        if downloaded_evictions > 0 or extracted_evictions > 0:
            self.logger.info(
                "Collection evictions: downloaded={}, extracted={}".format(
                    downloaded_evictions,
                    extracted_evictions
                )
            )

        # Log stream queue stats
        for queue_name, queue_stats in stats.stream_queues_stats.items():
            if queue_stats.get('dropped', 0) > 0:
                self.logger.warning(
                    "StreamQueue '{}': size={}/{}, dropped={}".format(
                        queue_name,
                        queue_stats.get('size', 0),
                        queue_stats.get('maxsize', 0),
                        queue_stats.get('dropped', 0)
                    )
                )

        return True

    def force_log_stats(self):
        """
        Force logging of current statistics regardless of interval.
        """
        self.__last_log_time = None
        self.log_stats_if_due()

    def get_stats_history(self) -> list:
        """
        Get the history of collected stats.

        :return: List of MemoryStats objects
        """
        return list(self.__stats_history)

    def get_latest_stats(self) -> Optional[MemoryStats]:
        """
        Get the most recent stats snapshot.

        :return: Latest MemoryStats or None if no stats collected yet
        """
        if self.__stats_history:
            return self.__stats_history[-1]
        return None

    def detect_growth_trend(self, data_source_name: str, window_size: int = 10) -> Optional[float]:
        """
        Detect if a data source is showing consistent growth.

        :param data_source_name: Name of the data source to check
        :param window_size: Number of recent samples to analyze
        :return: Average growth per sample, or None if insufficient data
        """
        if len(self.__stats_history) < window_size:
            return None

        recent = self.__stats_history[-window_size:]
        values = []

        for stats in recent:
            if data_source_name == 'downloaded_files':
                values.append(stats.downloaded_files_count)
            elif data_source_name == 'extracted_files':
                values.append(stats.extracted_files_count)
            elif data_source_name == 'model_files':
                values.append(stats.model_files_count)
            elif data_source_name == 'process_memory':
                values.append(stats.process_memory_mb)
            else:
                return None

        if len(values) < 2:
            return None

        # Calculate average growth
        growths = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_growth = sum(growths) / len(growths)
        return avg_growth
