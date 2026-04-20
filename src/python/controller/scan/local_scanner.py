import logging
import shutil
from typing import List, Optional, Tuple

from .scanner_process import IScanner, ScannerError
from common import overrides, Localization, Constants
from system import SystemScanner, SystemFile, SystemScannerError

class LocalScanner(IScanner):
    """
    Scanner implementation to scan the local filesystem
    """
    def __init__(self, local_path: str, use_temp_file: bool):
        self.__local_path = local_path
        self.__scanner = SystemScanner(local_path)
        if use_temp_file:
            self.__scanner.set_lftp_temp_suffix(Constants.LFTP_TEMP_FILE_SUFFIX)
        self.logger = logging.getLogger("LocalScanner")

    @overrides(IScanner)
    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("LocalScanner")

    @overrides(IScanner)
    def scan(self) -> Tuple[List[SystemFile], Optional[int], Optional[int]]:
        try:
            result = self.__scanner.scan()
        except SystemScannerError:
            self.logger.exception("Caught SystemScannerError")
            raise ScannerError(Localization.Error.LOCAL_SERVER_SCAN, recoverable=False)

        total_bytes: Optional[int] = None
        used_bytes: Optional[int] = None
        try:
            usage = shutil.disk_usage(self.__local_path)
            total_bytes = usage.total
            used_bytes = usage.used
        except (OSError, ValueError) as err:
            self.logger.warning("Local disk_usage failed for path '%s': %s", self.__local_path, err)

        return result, total_bytes, used_bytes
