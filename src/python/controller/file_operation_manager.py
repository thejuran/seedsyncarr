# Copyright 2017, Inderpreet Singh, All rights reserved.

from typing import List, Optional, Callable

from common import Context, MultiprocessingLogger, AppOneShotProcess
from model import ModelFile
from .extract import ExtractProcess, ExtractStatus
from .delete import DeleteLocalProcess, DeleteRemoteProcess


class CommandProcessWrapper:
    """
    Wraps any one-shot command processes launched by the file operation manager.
    """
    def __init__(self, process: AppOneShotProcess, post_callback: Callable):
        self.process = process
        self.post_callback = post_callback


class FileOperationManager:
    """
    Manages file operations (extract, delete) and their processes.

    Responsible for:
    - Extract process lifecycle and operations
    - Delete process creation and tracking (local and remote)
    - Command process cleanup
    - Active extracting file tracking

    Thread-safety: The ExtractProcess uses multiprocessing queues which are
    inherently thread-safe. Delete processes are one-shot and tracked
    in a list that is only modified from the controller thread.
    """

    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger,
                 force_local_scan_callback: Callable,
                 force_remote_scan_callback: Callable):
        """
        Create the file operation manager.

        Args:
            context: Application context with config and logger
            mp_logger: Multiprocessing logger for child processes
            force_local_scan_callback: Callback to trigger a local scan after delete
            force_remote_scan_callback: Callback to trigger a remote scan after delete
        """
        self.__context = context
        self.__mp_logger = mp_logger
        self.logger = context.logger.getChild("FileOperationManager")
        self.__force_local_scan = force_local_scan_callback
        self.__force_remote_scan = force_remote_scan_callback

        # Decide the password for remote operations
        self.__password = (
            context.config.lftp.remote_password
            if not context.config.lftp.use_ssh_key
            else None
        )

        # Setup extract process
        if context.config.controller.use_local_path_as_extract_path:
            out_dir_path = context.config.lftp.local_path
        else:
            out_dir_path = context.config.controller.extract_path
        self.__extract_process = ExtractProcess(
            out_dir_path=out_dir_path,
            local_path=context.config.lftp.local_path
        )
        self.__extract_process.set_multiprocessing_logger(mp_logger)

        # Track active extracting files
        self.__active_extracting_file_names: List[str] = []

        # Track active command processes (delete operations)
        self.__active_command_processes: List[CommandProcessWrapper] = []

        self.__started = False

    def start(self) -> None:
        """
        Start the extract process.

        Must be called after construction and before using extract operations.
        """
        self.logger.debug("Starting file operation manager")
        self.__extract_process.start()
        self.__started = True

    def stop(self) -> None:
        """
        Stop the extract process and wait for it to terminate.

        Safe to call multiple times or if not started.
        """
        if not self.__started:
            return

        self.logger.debug("Stopping file operation manager")
        self.__extract_process.terminate()
        self.__extract_process.join()
        self.__started = False
        self.logger.debug("File operation manager stopped")

    def extract(self, file: ModelFile) -> None:
        """
        Queue a file for extraction.

        Args:
            file: The model file to extract
        """
        self.__extract_process.extract(file)

    def pop_extract_statuses(self) -> Optional[object]:
        """
        Get the latest extract statuses.

        Returns:
            Extract statuses object, or None if no new statuses available.
        """
        return self.__extract_process.pop_latest_statuses()

    def pop_completed_extractions(self) -> List:
        """
        Get completed extraction results.

        Returns:
            List of completed extraction results.
        """
        return self.__extract_process.pop_completed()

    def get_active_extracting_file_names(self) -> List[str]:
        """
        Get the list of files currently being extracted.

        Returns:
            List of file names being extracted.
        """
        return self.__active_extracting_file_names

    def update_active_extracting_files(self, extract_statuses: Optional[object]) -> None:
        """
        Update the list of actively extracting files based on extract statuses.

        Args:
            extract_statuses: Current extract statuses, or None.
        """
        if extract_statuses is not None:
            self.__active_extracting_file_names = [
                s.name for s in extract_statuses.statuses
                if s.state == ExtractStatus.State.EXTRACTING
            ]

    def delete_local(self, file: ModelFile) -> bool:
        """
        Start a local file deletion process.

        Args:
            file: The model file to delete locally

        Returns:
            True if delete process was started successfully
        """
        process = DeleteLocalProcess(
            local_path=self.__context.config.lftp.local_path,
            file_name=file.name
        )
        process.set_multiprocessing_logger(self.__mp_logger)
        wrapper = CommandProcessWrapper(
            process=process,
            post_callback=self.__force_local_scan
        )
        self.__active_command_processes.append(wrapper)
        wrapper.process.start()
        return True

    def delete_remote(self, file: ModelFile) -> bool:
        """
        Start a remote file deletion process.

        Args:
            file: The model file to delete remotely

        Returns:
            True if delete process was started successfully
        """
        process = DeleteRemoteProcess(
            remote_address=self.__context.config.lftp.remote_address,
            remote_username=self.__context.config.lftp.remote_username,
            remote_password=self.__password,
            remote_port=self.__context.config.lftp.remote_port,
            remote_path=self.__context.config.lftp.remote_path,
            file_name=file.name
        )
        process.set_multiprocessing_logger(self.__mp_logger)
        wrapper = CommandProcessWrapper(
            process=process,
            post_callback=self.__force_remote_scan
        )
        self.__active_command_processes.append(wrapper)
        wrapper.process.start()
        return True

    def cleanup_completed_processes(self) -> None:
        """
        Cleanup completed command processes and execute their callbacks.

        Should be called periodically to clean up finished delete operations
        and trigger any post-operation callbacks (like forcing a scan).
        """
        still_active_processes = []
        for wrapper in self.__active_command_processes:
            if wrapper.process.is_alive():
                still_active_processes.append(wrapper)
            else:
                # Do the post callback
                wrapper.post_callback()
                # Propagate any exception
                wrapper.process.propagate_exception()
        self.__active_command_processes = still_active_processes

    def propagate_exception(self) -> None:
        """
        Propagate any exceptions from the extract process.

        Should be called periodically to detect and re-raise any errors.

        Raises:
            Any exception that occurred in the extract process.
        """
        self.__extract_process.propagate_exception()
