class AppError(Exception):
    """
    Exception indicating an error
    """
    pass

class ServiceExit(AppError):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass

class ServiceRestart(AppError):
    """
    Exception indicating a restart is requested.

    Carries keyword-only ``auto``/``reset`` flags so the supervisor can
    distinguish an auto-recovery restart from a UI-requested one (RECOV-01 /
    Phase 114 D-03):

    - ``auto``  — True only for an auto-recovery restart; only these burn the
      bounded consecutive-restart budget. A UI/manual restart leaves it False.
    - ``reset`` — True when the dying run stayed up past the reset threshold;
      signals main() to normalize the consecutive counter to a fresh budget.

    ``*args`` is passed through to ``super().__init__`` FIRST so the inherited
    Exception message contract is preserved (``str(ServiceRestart("restart
    requested")) == "restart requested"``). The flags are keyword-only (placed
    after ``*args``) so a positional message can never be misread as ``auto``.
    """
    def __init__(self, *args, auto: bool = False, reset: bool = False):
        super().__init__(*args)
        self.auto = auto
        self.reset = reset
