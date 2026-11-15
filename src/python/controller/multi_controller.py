import copy
import logging
from typing import Callable, List, Optional, Sequence

from common import Context, PathPair, sanitize_log_value
from model import IModelListener, ModelFile
from .auto_queue import AutoQueue, AutoQueuePersist
from .controller import Controller
from .webhook_manager import WebhookManager


class _PairLftpView:
    """
    The lftp config section with the remote and local path of one path pair.
    Every other option, read live, comes from the shared config.
    """

    def __init__(self, lftp, remote_path: str, local_path: str):
        self._lftp = lftp
        self.remote_path = remote_path
        self.local_path = local_path

    def __getattr__(self, name: str):
        return getattr(self._lftp, name)


class _PairConfigView:
    """
    The app config as seen by the components of one path pair
    """

    def __init__(self, config, lftp_view: _PairLftpView):
        self._config = config
        self.lftp = lftp_view

    def __getattr__(self, name: str):
        return getattr(self._config, name)


def pair_scoped_context(context: Context, pair: PathPair) -> Context:
    """
    A context whose lftp remote_path/local_path are those of the given pair.
    Everything else, including later edits to the shared config, passes through.
    """
    pair_context = copy.copy(context)
    pair_context.logger = context.logger.getChild("Pair-{}".format(pair.name))
    lftp_view = _PairLftpView(context.config.lftp, pair.remote_path, pair.local_path)
    pair_context.config = _PairConfigView(context.config, lftp_view)
    return pair_context


class WebhookFanout:
    """
    Hands every webhook import to the webhook manager of each path pair, so that
    each pair matches it against its own files. Presents the enqueue interface
    of WebhookManager to the web layer.
    """

    def __init__(
        self,
        managers: Sequence[WebhookManager],
        matchers: Optional[Sequence[Callable[[str], bool]]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        :param managers: webhook manager of each path pair
        :param matchers: per pair, whether a file name is in that pair's model
            (same order as managers). Without them every pair gets every import.
        """
        self.__managers = list(managers)
        self.__matchers = list(matchers) if matchers is not None else None
        if self.__matchers is not None and len(self.__matchers) != len(self.__managers):
            raise ValueError("WebhookFanout needs one matcher per manager")
        self.__logger = (logger or logging.getLogger(__name__)).getChild(
            "WebhookFanout"
        )

    def enqueue_import(self, source: str, file_name: str, provenance: str = ""):
        """
        A name found in more than one pair is ambiguous: Sonarr and Radarr do
        not say which pair they imported from, so crediting every pair would
        mark and later delete a file that was not the one imported. Such a
        name is dropped. A name found in exactly one pair goes only to that
        pair; an unknown name goes to all pairs, which each report it as not
        found, so a file that is still being scanned is picked up as before.
        """
        targets = self.__managers
        if self.__matchers is not None and len(self.__managers) > 1:
            matching = [
                m
                for m, matches in zip(self.__managers, self.__matchers)
                if matches(file_name)
            ]
            if len(matching) > 1:
                self.__logger.warning(
                    "{} webhook import '{}' is ambiguous: the name exists in {} path pairs; "
                    "no import credit or automatic cleanup authorized ({})".format(
                        source,
                        sanitize_log_value(file_name),
                        len(matching),
                        sanitize_log_value(provenance),
                    )
                )
                return
            if matching:
                targets = matching
        for manager in targets:
            manager.enqueue_import(source, file_name, provenance)


class AutoQueueGroup:
    """
    Runs the auto queue of every path pair
    """

    def __init__(self, auto_queues: Sequence[AutoQueue]):
        self.__auto_queues = list(auto_queues)

    def process(self):
        for auto_queue in self.__auto_queues:
            auto_queue.process()


class MultiController:
    """
    Runs one Controller per path pair, each with its own lftp, scanners and
    persisted state, and presents them as a single controller.

    Exposes the part of the Controller interface used by the app and the web layer.
    With one controller it behaves exactly like that controller.
    """

    def __init__(self, controllers: List[Controller], logger: logging.Logger):
        if not controllers:
            raise ValueError("MultiController needs at least one controller")
        self.logger = logger.getChild("MultiController")
        self.__controllers: List[tuple] = list(controllers)

    @property
    def pair_ids(self) -> List[Optional[str]]:
        return [pair_id for pair_id, _ in self.__controllers]

    @property
    def controllers(self) -> List[Controller]:
        return [c for _, c in self.__controllers]

    def start(self):
        started = []
        for _, controller in self.__controllers:
            try:
                controller.start()
            except Exception:
                self.logger.error(
                    "A controller failed to start; stopping the {} already started".format(
                        len(started)
                    )
                )
                for other in started:
                    try:
                        other.exit()
                    except Exception:
                        self.logger.exception(
                            "Error stopping a controller after a failed start"
                        )
                # Controllers that were never started still own an lftp process
                for _, rest in self.__controllers:
                    if rest not in started and rest is not controller:
                        try:
                            rest.stop_lftp()
                        except Exception:
                            self.logger.exception(
                                "Error stopping a controller after a failed start"
                            )
                raise
            started.append(controller)

    def note_shutdown_requested(self):
        for _, controller in self.__controllers:
            controller.note_shutdown_requested()

    def process(self):
        for _, controller in self.__controllers:
            controller.process()

    def exit(self):
        for _, controller in self.__controllers:
            try:
                controller.exit()
            except Exception:
                self.logger.exception("Error exiting a controller")

    def get_model_files(self) -> List[ModelFile]:
        files = []
        for _, controller in self.__controllers:
            files.extend(controller.get_model_files())
        return files

    def add_model_listener(self, listener: IModelListener):
        for _, controller in self.__controllers:
            controller.add_model_listener(listener)

    def remove_model_listener(self, listener: IModelListener):
        for _, controller in self.__controllers:
            controller.remove_model_listener(listener)

    def get_model_files_and_add_listener(
        self, listener: IModelListener
    ) -> List[ModelFile]:
        files = []
        for _, controller in self.__controllers:
            files.extend(controller.get_model_files_and_add_listener(listener))
        return files

    def resync_model_files(
        self, discard_backlog: Callable[[], None]
    ) -> List[ModelFile]:
        """
        Same contract as Controller.resync_model_files. The model locks of all
        controllers are held, in a fixed order, while the backlog is discarded
        and the snapshots are taken, so no event is lost or repeated.
        """
        snapshots: List[List[ModelFile]] = [[] for _ in self.__controllers]

        def resync_from(index: int):
            if index == len(self.__controllers):
                discard_backlog()
                return
            _, controller = self.__controllers[index]
            snapshots[index] = controller.resync_model_files(
                lambda: resync_from(index + 1)
            )

        resync_from(0)
        return [f for snapshot in snapshots for f in snapshot]

    def queue_command(self, command: Controller.Command):
        """
        Route the command to the controller of its path pair. Without a pair id
        the pair is found by file name; a name present in several pairs is rejected.
        """
        if (
            command.pair_id is not None
            and len(self.__controllers) > 1
            and not any(pair_id == command.pair_id for pair_id, _ in self.__controllers)
        ):
            for callback in command.callbacks:
                callback.on_failure(
                    "Path pair '{}' is not active".format(command.pair_id), 404
                )
            return
        target = self.__find_controller(command)
        if target is None:
            for callback in command.callbacks:
                callback.on_failure(
                    "File '{}' exists in more than one path pair; specify the pair".format(
                        command.filename
                    ),
                    400,
                )
            return
        target.queue_command(command)

    def __find_controller(self, command: Controller.Command) -> Optional[Controller]:
        if len(self.__controllers) == 1:
            return self.__controllers[0][1]
        if command.pair_id is not None:
            for pair_id, controller in self.__controllers:
                if pair_id == command.pair_id:
                    return controller
            return self.__controllers[0][
                1
            ]  # unknown pair: the controller reports the missing file
        matches = [
            c for _, c in self.__controllers if c.has_model_file(command.filename)
        ]
        if len(matches) > 1:
            return None
        return matches[0] if matches else self.__controllers[0][1]


def build_pair_runtime(
    context: Context,
    pairs: Sequence[PathPair],
    persists: dict,
    auto_queue_persist: AutoQueuePersist,
    persist_callbacks: dict,
):
    """
    Build the controller, webhook manager and auto queue for the given enabled pairs.

    :param persists: pair id -> ControllerPersist
    :param persist_callbacks: pair id -> callable saving that pair's persist
    :return: (MultiController, WebhookFanout, AutoQueueGroup)
    """
    controllers = []
    webhook_managers = []
    matchers = []
    auto_queues = []
    for index, pair in enumerate(pairs):
        pair_context = pair_scoped_context(context, pair)
        webhook_manager = WebhookManager(pair_context)
        controller = Controller(
            pair_context,
            persists[pair.id],
            webhook_manager,
            persist_callback=persist_callbacks[pair.id],
            pair_id=pair.id,
            report_status=(index == 0),
        )
        controllers.append((pair.id, controller))
        webhook_managers.append(webhook_manager)
        matchers.append(controller.matches_webhook_name)
        if pair.auto_queue:
            auto_queues.append(
                AutoQueue(pair_context, auto_queue_persist, controller, pair_id=pair.id)
            )
    return (
        MultiController([c for c in controllers], context.logger),
        WebhookFanout(webhook_managers, matchers, context.logger),
        AutoQueueGroup(auto_queues),
    )
