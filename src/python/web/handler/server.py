# Copyright 2017, Inderpreet Singh, All rights reserved.

from threading import Lock

from bottle import HTTPResponse

from common import Context, overrides
from ..web_app import IHandler, WebApp


class ServerHandler(IHandler):
    def __init__(self, context: Context):
        self.logger = context.logger.getChild("ServerActionHandler")
        self.__restart_lock = Lock()
        self.__request_restart = False

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_post_handler("/server/command/restart", self.__handle_action_restart)

    def is_restart_requested(self):
        """
        Returns true if a restart is requested.
        Thread-safe: can be called from any thread.
        :return:
        """
        with self.__restart_lock:
            return self.__request_restart

    def __handle_action_restart(self):
        """
        Request a server restart.
        Thread-safe: can be called from web server thread.
        :return:
        """
        self.logger.info("Received a restart action")
        with self.__restart_lock:
            self.__request_restart = True
        return HTTPResponse(body="Requested restart")
