import json
import logging
import os
import time
from pathlib import Path
from threading import Event, Lock
from typing import List, Optional, Tuple
from urllib.parse import unquote

from bottle import HTTPResponse, request

from common import overrides
from controller import Controller
from ..web_app import IHandler, WebApp

logger = logging.getLogger(__name__)

class WebResponseActionCallback(Controller.Command.ICallback):
    """
    Controller action callback used by model streams to wait for action
    status.
    Clients should call wait() method to wait for the status,
    then query the status from 'success', 'error', and 'error_code'
    """

    def __init__(self):
        self.__event = Event()
        self.success = None
        self.error = None
        self.error_code = 400

    @overrides(Controller.Command.ICallback)
    def on_failure(self, error: str, error_code: int = 400):
        self.success = False
        self.error = error
        self.error_code = error_code
        self.__event.set()

    @overrides(Controller.Command.ICallback)
    def on_success(self):
        self.success = True
        self.__event.set()

    def wait(self, timeout: float = None) -> bool:
        """
        Wait for the command to complete.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if the event was set (command completed), False if timed out.
        """
        return self.__event.wait(timeout=timeout)

class ControllerHandler(IHandler):
    def __init__(self, controller: Controller, local_path: str = ""):
        self.__controller = controller
        self.__local_path_real: Optional[Path] = (
            Path(os.path.realpath(local_path)) if local_path else None
        )
        self._bulk_request_times: List[float] = []
        self._bulk_rate_lock = Lock()

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_post_handler("/server/command/queue/<file_name>", self.__handle_action_queue)
        web_app.add_post_handler("/server/command/stop/<file_name>", self.__handle_action_stop)
        web_app.add_post_handler("/server/command/extract/<file_name>", self.__handle_action_extract)
        web_app.add_delete_handler("/server/command/delete_local/<file_name>", self.__handle_action_delete_local)
        web_app.add_delete_handler("/server/command/delete_remote/<file_name>", self.__handle_action_delete_remote)
        web_app.add_post_handler("/server/command/bulk", self.__handle_bulk_command)

    def __handle_action_queue(self, file_name: str) -> HTTPResponse:
        """
        Request a QUEUE action
        """
        # value is double encoded
        file_name = unquote(file_name)

        command = Controller.Command(Controller.Command.Action.QUEUE, file_name)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        completed = callback.wait(timeout=self._ACTION_TIMEOUT)
        if not completed:
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body="Queued file '{}'".format(file_name))
        else:
            return HTTPResponse(body=callback.error, status=callback.error_code)

    def __handle_action_stop(self, file_name: str) -> HTTPResponse:
        """
        Request a STOP action
        """
        # value is double encoded
        file_name = unquote(file_name)

        command = Controller.Command(Controller.Command.Action.STOP, file_name)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        completed = callback.wait(timeout=self._ACTION_TIMEOUT)
        if not completed:
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body="Stopped file '{}'".format(file_name))
        else:
            return HTTPResponse(body=callback.error, status=callback.error_code)

    def __handle_action_extract(self, file_name: str) -> HTTPResponse:
        """
        Request a EXTRACT action
        """
        # value is double encoded
        file_name = unquote(file_name)

        guard = self._check_path_safe(file_name)
        if guard:
            return guard

        command = Controller.Command(Controller.Command.Action.EXTRACT, file_name)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        completed = callback.wait(timeout=self._ACTION_TIMEOUT)
        if not completed:
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body="Requested extraction for file '{}'".format(file_name))
        else:
            return HTTPResponse(body=callback.error, status=callback.error_code)

    def __handle_action_delete_local(self, file_name: str) -> HTTPResponse:
        """
        Request a DELETE LOCAL action
        """
        # value is double encoded
        file_name = unquote(file_name)

        guard = self._check_path_safe(file_name)
        if guard:
            return guard

        command = Controller.Command(Controller.Command.Action.DELETE_LOCAL, file_name)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        completed = callback.wait(timeout=self._ACTION_TIMEOUT)
        if not completed:
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body="Requested local delete for file '{}'".format(file_name))
        else:
            return HTTPResponse(body=callback.error, status=callback.error_code)

    def __handle_action_delete_remote(self, file_name: str) -> HTTPResponse:
        """
        Request a DELETE REMOTE action
        """
        # value is double encoded
        file_name = unquote(file_name)

        guard = self._check_path_safe(file_name)
        if guard:
            return guard

        command = Controller.Command(Controller.Command.Action.DELETE_REMOTE, file_name)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        completed = callback.wait(timeout=self._ACTION_TIMEOUT)
        if not completed:
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body="Requested remote delete for file '{}'".format(file_name))
        else:
            return HTTPResponse(body=callback.error, status=callback.error_code)

    # Timeout for individual action endpoints in seconds
    _ACTION_TIMEOUT = 30.0

    # Valid action names for the bulk endpoint
    _VALID_ACTIONS = {
        "queue": Controller.Command.Action.QUEUE,
        "stop": Controller.Command.Action.STOP,
        "extract": Controller.Command.Action.EXTRACT,
        "delete_local": Controller.Command.Action.DELETE_LOCAL,
        "delete_remote": Controller.Command.Action.DELETE_REMOTE,
    }

    # Path-destructive actions that require traversal guarding
    _GUARDED_ACTIONS = {
        Controller.Command.Action.DELETE_LOCAL,
        Controller.Command.Action.DELETE_REMOTE,
        Controller.Command.Action.EXTRACT,
    }

    # Timeout per file in seconds for bulk operations
    _BULK_TIMEOUT_PER_FILE = 5.0
    # Maximum total timeout for bulk operations in seconds
    _BULK_MAX_TIMEOUT = 300.0
    # Maximum number of files allowed in a single bulk request
    _MAX_BULK_FILES = 1000

    # Rate limiting for bulk endpoint (DoS prevention)
    _BULK_RATE_LIMIT = 10  # Max requests per window
    _BULK_RATE_WINDOW = 60.0  # Window size in seconds

    def _check_path_safe(self, file_name: str) -> Optional[HTTPResponse]:
        """
        Returns HTTPResponse(status=400) if file_name resolves outside local_path, else None.

        Uses realpath() to resolve both '..' sequences and symlinks before checking
        containment within local_path. Returns None when local_path was not configured
        (guard is a no-op).
        """
        if self.__local_path_real is None:
            return None
        candidate = Path(os.path.realpath(
            os.path.join(str(self.__local_path_real), file_name)
        ))
        if not candidate.is_relative_to(self.__local_path_real):
            logger.warning("Rejected path traversal attempt for: %s", repr(file_name))
            return HTTPResponse(body="Invalid file path", status=400)
        return None

    def _check_bulk_rate_limit(self) -> bool:
        """
        Check if the bulk request rate limit has been exceeded.

        Uses a sliding window algorithm to track recent requests.
        Thread-safe via instance-level lock.

        Returns:
            True if request is allowed, False if rate limited.
        """
        now = time.time()
        with self._bulk_rate_lock:
            # Remove timestamps outside the window
            self._bulk_request_times = [
                t for t in self._bulk_request_times
                if now - t < self._BULK_RATE_WINDOW
            ]
            # Check if limit exceeded
            if len(self._bulk_request_times) >= self._BULK_RATE_LIMIT:
                return False
            # Record this request
            self._bulk_request_times.append(now)
            return True

    def __handle_bulk_command(self) -> HTTPResponse:
        """
        Handle bulk command requests for multiple files.

        Expected JSON body:
        {
            "action": "queue|stop|extract|delete_local|delete_remote",
            "files": ["file1", "file2", ...]
        }

        Returns JSON:
        {
            "results": [
                {"file": "file1", "success": true},
                {"file": "file2", "success": false, "error": "error message", "error_code": 404}
            ],
            "summary": {
                "total": 2,
                "succeeded": 1,
                "failed": 1
            }
        }
        """
        # Rate limiting check
        if not self._check_bulk_rate_limit():
            logger.warning("Bulk endpoint rate limit exceeded")
            return HTTPResponse(
                body=json.dumps({"error": "Rate limit exceeded. Please try again later."}),
                status=429,
                content_type="application/json"
            )

        # Parse JSON body
        try:
            body = request.json
        except Exception:
            return HTTPResponse(
                body=json.dumps({"error": "Invalid JSON body"}),
                status=400,
                content_type="application/json"
            )

        if not body:
            return HTTPResponse(
                body=json.dumps({"error": "Request body is required"}),
                status=400,
                content_type="application/json"
            )

        # Validate action
        action_name = body.get("action")
        if not action_name or action_name not in self._VALID_ACTIONS:
            valid_actions = ", ".join(self._VALID_ACTIONS.keys())
            return HTTPResponse(
                body=json.dumps({
                    "error": "Invalid action '{}'. Valid actions: {}".format(action_name, valid_actions)
                }),
                status=400,
                content_type="application/json"
            )

        # Validate files array
        files = body.get("files")
        if not files:
            return HTTPResponse(
                body=json.dumps({"error": "files array is required and must not be empty"}),
                status=400,
                content_type="application/json"
            )
        if not isinstance(files, list):
            return HTTPResponse(
                body=json.dumps({"error": "files must be an array"}),
                status=400,
                content_type="application/json"
            )
        if not all(isinstance(f, str) and f.strip() for f in files):
            return HTTPResponse(
                body=json.dumps({"error": "All files must be non-empty strings"}),
                status=400,
                content_type="application/json"
            )

        files = list(dict.fromkeys(files))

        # Prevent DoS — enforce file limit
        if len(files) > self._MAX_BULK_FILES:
            return HTTPResponse(
                body=json.dumps({
                    "error": "Too many files. Maximum {} files allowed per request".format(
                        self._MAX_BULK_FILES
                    )
                }),
                status=400,
                content_type="application/json"
            )

        action = self._VALID_ACTIONS[action_name]

        # Process files using parallel queuing for performance
        results, succeeded, failed = self._process_bulk_commands(action, files, action_name)

        response = {
            "results": results,
            "summary": {
                "total": len(files),
                "succeeded": succeeded,
                "failed": failed
            }
        }

        return HTTPResponse(
            body=json.dumps(response),
            status=200,
            content_type="application/json"
        )

    def _process_bulk_commands(
        self,
        action: Controller.Command.Action,
        files: List[str],
        action_name: str
    ) -> Tuple[List[dict], int, int]:
        """
        Process bulk commands with parallel queuing for improved performance.

        Instead of queuing one command and waiting for it to complete before
        queuing the next, this method queues ALL commands first, allowing the
        controller to process them in a single batch. This significantly reduces
        latency for large file counts.

        Args:
            action: The action to perform on all files.
            files: List of file names to process.
            action_name: Human-readable action name for logging.

        Returns:
            Tuple of (results list, succeeded count, failed count).
        """
        start_time = time.time()
        file_count = len(files)

        logger.info("Bulk {} operation started for {} file(s)".format(action_name, file_count))

        # Calculate timeout: per-file timeout with a maximum cap
        timeout = min(
            file_count * self._BULK_TIMEOUT_PER_FILE,
            self._BULK_MAX_TIMEOUT
        )

        # Queue all commands (parallel queuing)
        commands_with_callbacks: List[Tuple[str, WebResponseActionCallback]] = []
        results = []
        succeeded = 0
        failed = 0
        for file_name in files:
            # Path traversal guard for destructive actions
            if action in self._GUARDED_ACTIONS:
                guard = self._check_path_safe(file_name)
                if guard:
                    results.append({
                        "file": file_name,
                        "success": False,
                        "error": "Invalid file path",
                        "error_code": 400
                    })
                    failed += 1
                    continue

            command = Controller.Command(action, file_name)
            callback = WebResponseActionCallback()
            command.add_callback(callback)
            self.__controller.queue_command(command)
            commands_with_callbacks.append((file_name, callback))

        queue_time = time.time()
        logger.debug("Bulk {}: queued {} commands in {:.3f}s".format(
            action_name, file_count, queue_time - start_time
        ))

        # Wait for all callbacks to complete
        # The controller will process all queued commands in its next cycle,
        # so waiting for all at once is much faster than waiting one-by-one.
        timed_out = 0

        for file_name, callback in commands_with_callbacks:
            remaining_timeout = max(0.1, timeout - (time.time() - start_time))
            completed = callback.wait(timeout=remaining_timeout)

            if not completed:
                # Timed out waiting for this command
                results.append({
                    "file": file_name,
                    "success": False,
                    "error": "Operation timed out",
                    "error_code": 504
                })
                failed += 1
                timed_out += 1
            elif callback.success:
                results.append({
                    "file": file_name,
                    "success": True
                })
                succeeded += 1
            else:
                results.append({
                    "file": file_name,
                    "success": False,
                    "error": callback.error,
                    "error_code": callback.error_code
                })
                failed += 1

        total_time = time.time() - start_time

        # Log performance summary
        if timed_out > 0:
            logger.warning(
                "Bulk {} completed: {}/{} succeeded, {} failed, {} timed out in {:.3f}s".format(
                    action_name, succeeded, file_count, failed - timed_out, timed_out, total_time
                )
            )
        else:
            logger.info(
                "Bulk {} completed: {}/{} succeeded in {:.3f}s ({:.1f} files/sec)".format(
                    action_name, succeeded, file_count, total_time,
                    file_count / total_time if total_time > 0 else 0
                )
            )

        return results, succeeded, failed
