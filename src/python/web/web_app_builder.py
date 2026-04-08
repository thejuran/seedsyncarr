from common import Context
from controller import Controller, AutoQueuePersist
from .web_app import WebApp
from .handler.stream_model import ModelStreamHandler
from .handler.stream_status import StatusStreamHandler
from .handler.controller import ControllerHandler
from .handler.server import ServerHandler
from .handler.config import ConfigHandler
from .handler.auto_queue import AutoQueueHandler
from .handler.stream_log import LogStreamHandler
from .handler.stream_heartbeat import HeartbeatStreamHandler
from .handler.status import StatusHandler
from .handler.webhook import WebhookHandler

class WebAppBuilder:
    """
    Helper class to build WebApp with all the extensions
    """
    def __init__(self,
                 context: Context,
                 controller: Controller,
                 auto_queue_persist: AutoQueuePersist,
                 webhook_manager):
        self.__context = context
        self.__controller = controller

        self.controller_handler = ControllerHandler(
            controller,
            local_path=context.config.lftp.local_path
        )
        self.server_handler = ServerHandler(context)
        self.config_handler = ConfigHandler(context.config)
        self.auto_queue_handler = AutoQueueHandler(auto_queue_persist)
        self.status_handler = StatusHandler(context.status)
        self.webhook_handler = WebhookHandler(webhook_manager, context.config)

    def build(self) -> WebApp:
        web_app = WebApp(context=self.__context,
                         controller=self.__controller,
                         config=self.__context.config)

        StatusStreamHandler.register(web_app=web_app,
                                     status=self.__context.status)

        LogStreamHandler.register(web_app=web_app,
                                  logger=self.__context.logger)

        ModelStreamHandler.register(web_app=web_app,
                                    controller=self.__controller)

        HeartbeatStreamHandler.register(web_app=web_app)

        self.controller_handler.add_routes(web_app)
        self.server_handler.add_routes(web_app)
        self.config_handler.add_routes(web_app)
        self.auto_queue_handler.add_routes(web_app)
        self.status_handler.add_routes(web_app)
        self.webhook_handler.add_routes(web_app)

        web_app.add_default_routes()

        return web_app
