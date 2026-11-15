import json
import os
import time
from pathlib import Path
from threading import Event

from urllib.parse import unquote

from bottle import HTTPResponse, request

from common import Context, overrides
from controller import Controller
from ..web_app import IHandler, WebApp
from ..rate_limit import rate_limit

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

    def wait(self, timeout: float | None = None) -> bool:
        """
        Wait for the command to complete.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if the event was set (command completed), False if timed out.
        """
        return self.__event.wait(timeout=timeout)

class ControllerHandler(IHandler):
    def __init__(self, controller: Controller, context: Context, local_path: str = "", path_pairs=None):
        self.logger = context.logger.getChild("ControllerHandler")
        self.__controller = controller
        self.__local_path_real: Path | None = (
            Path(os.path.realpath(local_path)) if local_path else None
        )
        # Optional PathPairsConfig; gives each pair its own containment root
        self.__path_pairs = path_pairs

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_post_handler("/server/command/queue/<file_name>", self.__handle_action_queue)
        web_app.add_post_handler("/server/command/stop/<file_name>", self.__handle_action_stop)
        web_app.add_post_handler("/server/command/extract/<file_name>", self.__handle_action_extract)
        web_app.add_delete_handler("/server/command/delete_local/<file_name>", self.__handle_action_delete_local)
        web_app.add_delete_handler("/server/command/delete_remote/<file_name>", self.__handle_action_delete_remote)
        web_app.add_post_handler(
            "/server/command/bulk",
            rate_limit(max_requests=10, window_seconds=60.0, logger=self.logger)(self.__handle_bulk_command)
        )

    def _dispatch_command(
        self,
        action: "Controller.Command.Action",
        file_name: str,
        success_msg: str,
        *,
        guard: bool = False,
        release_unverified: bool = False,
    ) -> HTTPResponse:
        """
        Shared dispatch scaffold for single-action handler endpoints.

        Performs unquote → optional path-safety guard → command queue →
        timeout/success/failure response, preserving the exact execution
        ordering and response shapes of the five individual handlers it backs.
        """
        # value is double encoded — MUST run before the path-safety guard
        file_name = unquote(file_name)
        pair_id = self._request_pair_id()
        unknown = self._check_pair_known(pair_id)
        if unknown:
            return unknown
        if guard:
            path_guard = self._check_path_safe(file_name, pair_id)
            if path_guard:
                return path_guard
        command = Controller.Command(action, file_name, release_unverified=release_unverified, pair_id=pair_id)
        callback = WebResponseActionCallback()
        command.add_callback(callback)
        self.__controller.queue_command(command)
        if not callback.wait(timeout=self._ACTION_TIMEOUT):
            return HTTPResponse(body="Operation timed out", status=504)
        if callback.success:
            return HTTPResponse(body=success_msg.format(file_name))
        return HTTPResponse(body=callback.error, status=callback.error_code)

    def __handle_action_queue(self, file_name: str) -> HTTPResponse:
        """
        Request a QUEUE action

        ?release_unverified=true is the user's one-shot confirmation to
        transfer a file whose completion could not be verified (after a 428).
        """
        release_unverified = request.query.get("release_unverified", "").lower() == "true"
        return self._dispatch_command(
            Controller.Command.Action.QUEUE, file_name, "Queued file '{}'",
            release_unverified=release_unverified,
        )

    def __handle_action_stop(self, file_name: str) -> HTTPResponse:
        """
        Request a STOP action
        """
        return self._dispatch_command(Controller.Command.Action.STOP, file_name, "Stopped file '{}'")

    def __handle_action_extract(self, file_name: str) -> HTTPResponse:
        """
        Request a EXTRACT action
        """
        return self._dispatch_command(
            Controller.Command.Action.EXTRACT, file_name,
            "Requested extraction for file '{}'", guard=True,
        )

    def __handle_action_delete_local(self, file_name: str) -> HTTPResponse:
        """
        Request a DELETE LOCAL action
        """
        return self._dispatch_command(
            Controller.Command.Action.DELETE_LOCAL, file_name,
            "Requested local delete for file '{}'", guard=True,
        )

    def __handle_action_delete_remote(self, file_name: str) -> HTTPResponse:
        """
        Request a DELETE REMOTE action
        """
        return self._dispatch_command(
            Controller.Command.Action.DELETE_REMOTE, file_name,
            "Requested remote delete for file '{}'", guard=True,
        )

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

    @staticmethod
    def _request_pair_id() -> str | None:
        """The ?pair_id= of the current request, None when absent."""
        try:
            value = request.query.get("pair_id")
        except Exception:
            return None
        return value if isinstance(value, str) and value else None

    def _check_pair_known(self, pair_id: str | None) -> HTTPResponse | None:
        """
        Returns HTTPResponse(status=404) if a pair id is given that is not a
        configured path pair, else None. A no-op without path pairs.
        """
        if pair_id is None or self.__path_pairs is None:
            return None
        if self.__path_pairs.get_pair(pair_id) is None:
            return HTTPResponse(body="Path pair '{}' not found".format(pair_id), status=404)
        return None

    def _local_root(self, pair_id: str | None) -> Path | None:
        """
        Directory that a file of the given pair must stay inside; the Default
        local path when no pair is given or known.
        """
        if pair_id is not None and self.__path_pairs is not None:
            pair = self.__path_pairs.get_pair(pair_id)
            if pair is not None and pair.local_path:
                return Path(os.path.realpath(pair.local_path))
        return self.__local_path_real

    def _check_path_safe(self, file_name: str, pair_id: str | None = None) -> HTTPResponse | None:
        """
        Returns HTTPResponse(status=400) if file_name resolves outside the local
        path of its pair, else None.

        Uses realpath() to resolve both '..' sequences and symlinks before checking
        containment within the local path. Returns None when no local path was
        configured (guard is a no-op).
        """
        root = self._local_root(pair_id)
        if root is None:
            return None
        candidate = Path(os.path.realpath(
            os.path.join(str(root), file_name)
        ))
        if not candidate.is_relative_to(root):
            # repr() here instead of sanitize_log_value is pre-existing and
            # out of scope for this change; file name only, no credential.
            self.logger.warning("Rejected path traversal attempt for: %s", repr(file_name))
            return HTTPResponse(body="Invalid file path", status=400)
        return None

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
        # A file is a name, or {"name", "pair_id"}; a top-level pair_id is the
        # default for entries that give none.
        default_pair = body.get("pair_id")
        if default_pair is not None and (not isinstance(default_pair, str) or not default_pair.strip()):
            return HTTPResponse(
                body=json.dumps({"error": "pair_id must be a non-empty string"}),
                status=400,
                content_type="application/json"
            )
        entries: list[tuple[str, str | None]] = []
        for f in files:
            if isinstance(f, str) and f.strip():
                entries.append((f, default_pair))
            elif (isinstance(f, dict) and isinstance(f.get("name"), str) and f["name"].strip()
                  and (f.get("pair_id") is None or (isinstance(f["pair_id"], str) and f["pair_id"].strip()))):
                entries.append((f["name"], f.get("pair_id") or default_pair))
            else:
                return HTTPResponse(
                    body=json.dumps({"error": "All files must be non-empty strings"}),
                    status=400,
                    content_type="application/json"
                )
        for pair_id in dict.fromkeys(p for _, p in entries):
            unknown = self._check_pair_known(pair_id)
            if unknown:
                return HTTPResponse(
                    body=json.dumps({"error": unknown.body}),
                    status=404,
                    content_type="application/json"
                )

        files = list(dict.fromkeys(entries))

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

        # One-shot confirmation to transfer files whose completion could not
        # be verified; strict boolean, queue only.
        release_unverified = body.get("release_unverified", False)
        if not isinstance(release_unverified, bool):
            return HTTPResponse(
                body=json.dumps({"error": "release_unverified must be a boolean"}),
                status=400,
                content_type="application/json"
            )
        if release_unverified and action_name != "queue":
            return HTTPResponse(
                body=json.dumps({"error": "release_unverified is only valid for action queue"}),
                status=400,
                content_type="application/json"
            )

        action = self._VALID_ACTIONS[action_name]

        # Process files using parallel queuing for performance
        results, succeeded, failed = self._process_bulk_commands(
            action, files, action_name, release_unverified=release_unverified
        )

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

    @staticmethod
    def _result(file_name: str, pair_id: str | None, fields: dict) -> dict:
        """Bulk result row; carries pair_id only when the request named a pair."""
        result = {"file": file_name}
        if pair_id is not None:
            result["pair_id"] = pair_id
        result.update(fields)
        return result

    def _process_bulk_commands(
        self,
        action: Controller.Command.Action,
        files: list[tuple[str, str | None]],
        action_name: str,
        *,
        release_unverified: bool = False,
    ) -> tuple[list[dict], int, int]:
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
            release_unverified: One-shot confirmation carried by each queue
                command to transfer files whose completion could not be verified.

        Returns:
            tuple of (results list, succeeded count, failed count).
        """
        start_time = time.time()
        file_count = len(files)

        self.logger.info("Bulk {} operation started for {} file(s)".format(action_name, file_count))

        # Calculate timeout: per-file timeout with a maximum cap
        timeout = min(
            file_count * self._BULK_TIMEOUT_PER_FILE,
            self._BULK_MAX_TIMEOUT
        )

        # Queue all commands (parallel queuing)
        commands_with_callbacks: list[tuple[str, str | None, WebResponseActionCallback]] = []
        results = []
        succeeded = 0
        failed = 0
        for file_name, pair_id in files:
            # Path traversal guard for destructive actions
            if action in self._GUARDED_ACTIONS:
                guard = self._check_path_safe(file_name, pair_id)
                if guard:
                    results.append(self._result(file_name, pair_id, {
                        "success": False,
                        "error": "Invalid file path",
                        "error_code": 400
                    }))
                    failed += 1
                    continue

            command = Controller.Command(
                action, file_name, release_unverified=release_unverified, pair_id=pair_id
            )
            callback = WebResponseActionCallback()
            command.add_callback(callback)
            self.__controller.queue_command(command)
            commands_with_callbacks.append((file_name, pair_id, callback))

        queue_time = time.time()
        self.logger.debug("Bulk {}: queued {} commands in {:.3f}s".format(
            action_name, file_count, queue_time - start_time
        ))

        # Wait for all callbacks to complete
        # The controller will process all queued commands in its next cycle,
        # so waiting for all at once is much faster than waiting one-by-one.
        timed_out = 0

        for file_name, pair_id, callback in commands_with_callbacks:
            remaining_timeout = max(0.1, timeout - (time.time() - start_time))
            completed = callback.wait(timeout=remaining_timeout)

            if not completed:
                # Timed out waiting for this command
                results.append(self._result(file_name, pair_id, {
                    "success": False,
                    "error": "Operation timed out",
                    "error_code": 504
                }))
                failed += 1
                timed_out += 1
            elif callback.success:
                results.append(self._result(file_name, pair_id, {"success": True}))
                succeeded += 1
            else:
                results.append(self._result(file_name, pair_id, {
                    "success": False,
                    "error": callback.error,
                    "error_code": callback.error_code
                }))
                failed += 1

        total_time = time.time() - start_time

        # Log performance summary
        if timed_out > 0:
            self.logger.warning(
                "Bulk {} completed: {}/{} succeeded, {} failed, {} timed out in {:.3f}s".format(
                    action_name, succeeded, file_count, failed - timed_out, timed_out, total_time
                )
            )
        else:
            self.logger.info(
                "Bulk {} completed: {}/{} succeeded in {:.3f}s ({:.1f} files/sec)".format(
                    action_name, succeeded, file_count, total_time,
                    file_count / total_time if total_time > 0 else 0
                )
            )

        return results, succeeded, failed
