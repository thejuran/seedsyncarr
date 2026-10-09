from typing import Optional, Tuple

from common import sanitize_log_value
from model import ModelFile
from lftp import LftpError, LftpJobStatusParserError


class CommandProcessor:
    """
    Handles command dispatch for the four command-handler actions:
    QUEUE, STOP, EXTRACT, DELETE_LOCAL, DELETE_REMOTE.

    Responsible for:
    - Routing a command to the correct _handle_* method via handle()
    - Executing queue/stop/extract/delete operations against the injected managers
    - Returning (success, error_msg, error_code) triples to the caller

    Thread-safety: None of the _handle_* methods acquire any lock. They are
    called from Controller.__process_commands AFTER __model_lock is released,
    so subprocess-spawning operations (delete_local) run with no lock held.
    The injected managers are themselves thread-safe; CommandProcessor adds no
    synchronization of its own.

    Ordering: Controller.__process_commands drains every pending command
    against the ModelFile frozen at the last model build, before the model is
    rebuilt. A QUEUE that lftp accepted earlier in the same batch is therefore
    invisible in file.state, so extract, delete and queue also consult the
    LftpManager's submitted-but-unobserved names at execution time and refuse
    to act on a transfer whose state has not yet been observed (XFER-02).

    Construction: All manager instances (lftp_manager, file_op_manager, persist)
    are constructed in Controller.__init__ and injected here already-built.
    CommandProcessor constructs none of them (D-05: mock.patch binding must
    resolve against controller.controller, not this module).
    """

    def __init__(self,
                 lftp_manager,
                 file_op_manager,
                 persist,
                 logger):
        """
        Create the command processor.

        Args:
            lftp_manager: LftpManager instance, already constructed in Controller.__init__
            file_op_manager: FileOperationManager instance, already constructed
            persist: ControllerPersist instance, already constructed
            logger: Parent logger; a child logger named "CommandProcessor" is created
        """
        self.__lftp_manager = lftp_manager
        self.__file_op_manager = file_op_manager
        self.__persist = persist
        self.logger = logger.getChild("CommandProcessor")

    def handle(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Route a command to the appropriate handler.

        This method is called by Controller.__process_commands after __model_lock
        is released. No lock is held when this method executes.

        Args:
            file: The frozen ModelFile looked up under __model_lock by the caller
            command: Duck-typed command object with .action (enum), .filename (str),
                     .callbacks (list). Controller.Command is NOT imported here to
                     avoid a circular import — action is dispatched by .name string.

        Returns:
            (success, error_msg, error_code) triple.
            On success: (True, None, None).
            On failure: (False, human-readable message, HTTP status code).
        """
        action_name = command.action.name
        if action_name == 'QUEUE':
            return self._handle_queue(file, command)
        elif action_name == 'STOP':
            return self._handle_stop(file, command)
        elif action_name == 'EXTRACT':
            return self._handle_extract(file, command)
        elif action_name in ('DELETE_LOCAL', 'DELETE_REMOTE'):
            return self._handle_delete(file, command)
        else:
            self.logger.warning(
                "Unknown action '{}' for file {}".format(
                    action_name, sanitize_log_value(command.filename)
                )
            )
            return False, "Unknown action", 500

    def _is_submitted_unobserved(self, file: ModelFile) -> bool:
        """
        True if lftp accepted a QUEUE for this file but no successful status
        has observed the job yet.

        The model state is not enough here: Controller.__process_commands
        handles every pending command against the ModelFile frozen at the last
        build and runs before the model is rebuilt, so a QUEUE accepted by lftp
        earlier in the same batch does not show in file.state. The LftpManager
        set is the only synchronous evidence of that submission (XFER-02).
        """
        return file.name in self.__lftp_manager.submitted_unobserved_file_names()

    def _handle_queue(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Handle QUEUE command action.
        Returns (success, error_message, error_code) tuple.

        Origin-aware (dispatched by origin.name string, mirroring the
        action.name dispatch — Controller.Command is not imported here):
        - AUTO: re-check the stopped/downloaded guards at execution time and
          skip quietly if either holds. Auto-queue filters at enqueue time
          only; a guard added between enqueue and execution (incident
          2026-08-27: a user Delete Local racing an in-flight auto-queue
          command) must win. Guards are never cleared by AUTO commands.
        - USER: an explicit re-download; clear all tracking that would
          suppress or misrepresent the fresh lifecycle (stopped, downloaded,
          imported, per-child imports).
        """
        if file.remote_size is None:
            return False, "File '{}' does not exist remotely".format(command.filename), 404

        is_auto = getattr(command, "origin", None) is not None and \
            command.origin.name == 'AUTO'
        if is_auto:
            if file.name in self.__persist.stopped_file_names or \
                    file.name in self.__persist.downloaded_file_names:
                self.logger.info(
                    "Skipping auto-queue of '{}': guarded at execution time".format(
                        sanitize_log_value(file.name)
                    )
                )
                return True, None, None

        try:
            # Already submitted and awaiting its first status: do not hand lftp
            # a duplicate job. The next successful status clears the set, after
            # which a re-queue is admissible.
            if not self._is_submitted_unobserved(file):
                self.__lftp_manager.queue(file.name, file.is_dir)
            if not is_auto:
                # User explicitly wants a fresh download lifecycle
                self.__persist.stopped_file_names.discard(file.name)
                self.__persist.downloaded_file_names.discard(file.name)
                self.__persist.imported_file_names.discard(file.name)
                self.__persist.imported_children.pop(file.name, None)
            return True, None, None
        except LftpError as e:
            return False, "Lftp error: {}".format(str(e)), 500

    def _handle_stop(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Handle STOP command action.
        Returns (success, error_message, error_code) tuple.
        """
        if file.state not in (ModelFile.State.DOWNLOADING, ModelFile.State.QUEUED):
            return False, "File '{}' is not Queued or Downloading".format(command.filename), 409
        try:
            self.__lftp_manager.kill(file.name)
            # Track this file as stopped so it won't be auto-queued on restart
            self.__persist.stopped_file_names.add(file.name)
            return True, None, None
        except (LftpError, LftpJobStatusParserError) as e:
            return False, "Lftp error: {}".format(str(e)), 500

    def _handle_extract(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Handle EXTRACT command action.
        Returns (success, error_message, error_code) tuple.
        """
        # Note: We don't check the is_extractable flag because it's just a guess
        if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED
        ):
            return False, "File '{}' in state {} cannot be extracted".format(
                command.filename, str(file.state)
            ), 409
        elif self._is_submitted_unobserved(file):
            return False, "File '{}' is queued (transfer submitted, awaiting lftp status) and cannot be extracted".format(
                command.filename
            ), 409
        elif file.local_size is None:
            return False, "File '{}' does not exist locally".format(command.filename), 404
        else:
            self.__file_op_manager.extract(file)
            return True, None, None

    def _handle_delete(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Handle DELETE_LOCAL and DELETE_REMOTE command actions.
        Returns (success, error_message, error_code) tuple.

        Dispatched by action.name string ('DELETE_LOCAL' or 'DELETE_REMOTE') to
        avoid importing Controller.Command.Action (circular-import risk).
        """
        if command.action.name == 'DELETE_LOCAL':
            if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED
            ):
                return False, "Local file '{}' cannot be deleted in state {}".format(
                    command.filename, str(file.state)
                ), 409
            elif self._is_submitted_unobserved(file):
                return False, ("Local file '{}' cannot be deleted while its transfer is queued "
                               "(submitted, awaiting lftp status)").format(command.filename), 409
            elif file.local_size is None:
                return False, "File '{}' does not exist locally".format(command.filename), 404
            else:
                self.__file_op_manager.delete_local(file)
                # Track as stopped to prevent auto-queuing on restart
                self.__persist.stopped_file_names.add(command.filename)
                # Record the deletion durably: membership in downloaded means
                # "completed and intentionally removed", which the auto-queue
                # filter honors at every restart. Without this the release
                # re-downloads at the next restart burst while its remote
                # copy persists (incident 2026-08-27).
                self.__persist.downloaded_file_names.add(command.filename)
                return True, None, None

        elif command.action.name == 'DELETE_REMOTE':
            if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED,
                ModelFile.State.DELETED
            ):
                return False, "Remote file '{}' cannot be deleted in state {}".format(
                    command.filename, str(file.state)
                ), 409
            elif self._is_submitted_unobserved(file):
                return False, ("Remote file '{}' cannot be deleted while its transfer is queued "
                               "(submitted, awaiting lftp status)").format(command.filename), 409
            elif file.remote_size is None:
                return False, "File '{}' does not exist remotely".format(command.filename), 404
            else:
                self.__file_op_manager.delete_remote(file)
                return True, None, None

        return False, "Unknown delete action", 500
