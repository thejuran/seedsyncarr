from bottle import HTTPResponse

from common import Context, Status, overrides
from ..web_app import IHandler, WebApp
from ..serialize import SerializeStatusJson
from ..rate_limit import rate_limit

class StatusHandler(IHandler):
    def __init__(self, status: Status, context: Context):
        self.__status = status
        self.logger = context.logger.getChild("StatusHandler")

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler(
            "/server/status",
            rate_limit(max_requests=60, window_seconds=60.0, logger=self.logger)(self.__handle_get_status)
        )

    def __handle_get_status(self):
        out_json = SerializeStatusJson.status(self.__status)
        return HTTPResponse(body=out_json)
