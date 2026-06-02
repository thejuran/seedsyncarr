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

    def _handle_queue(self, file: ModelFile, command) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Handle QUEUE command action.
        Returns (success, error_message, error_code) tuple.
        """
        if file.remote_size is None:
            return False, "File '{}' does not exist remotely".format(command.filename), 404
        try:
            self.__lftp_manager.queue(file.name, file.is_dir)
            # Remove from stopped files - user explicitly wants to download this
            self.__persist.stopped_file_names.discard(file.name)
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
            elif file.local_size is None:
                return False, "File '{}' does not exist locally".format(command.filename), 404
            else:
                self.__file_op_manager.delete_local(file)
                # Track as stopped to prevent auto-queuing on restart
                self.__persist.stopped_file_names.add(command.filename)
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
            elif file.remote_size is None:
                return False, "File '{}' does not exist remotely".format(command.filename), 404
            else:
                self.__file_op_manager.delete_remote(file)
                return True, None, None

        return False, "Unknown delete action", 500
