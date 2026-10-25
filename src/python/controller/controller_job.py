from common import overrides, Job, Context, AppError
from .controller import Controller, ControllerError
from .auto_queue import AutoQueue

class ControllerJob(Job):
    """
    The controller service
    Handles querying and downloading of files
    """
    def __init__(self,
                 context: Context,
                 controller: Controller,
                 auto_queue: AutoQueue):
        super().__init__(name=self.__class__.__name__, context=context)
        self.__controller = controller
        self.__auto_queue = auto_queue

    @overrides(Job)
    def setup(self):
        # AppError failures surface unchanged. Other failures are wrapped so the
        # main loop's existing RECOV-01 `except AppError` path handles them (D-04)
        # instead of the process exiting (D-05). The original is the __cause__ and
        # is logged in full with its traceback by Job.run's setup except-block.
        # The UI only sees the generic message.
        try:
            self.__controller.start()
        except AppError:
            raise
        except Exception as exc:
            raise ControllerError(
                "Controller failed to start. Please check server logs for details."
            ) from exc

    @overrides(Job)
    def execute(self):
        self.__controller.process()
        self.__auto_queue.process()

    @overrides(Job)
    def cleanup(self):
        self.__controller.exit()
