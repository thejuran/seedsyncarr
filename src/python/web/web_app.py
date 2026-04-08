from typing import Type, Callable, Optional
from abc import ABC, abstractmethod
import hmac
import html as html_mod
import os
import time

import bottle
from bottle import static_file, HTTPResponse

from common import Context, Config
from controller import Controller

class IHandler(ABC):
    """
    Abstract class that defines a web handler
    """
    @abstractmethod
    def add_routes(self, web_app: "WebApp"):
        """
        Add all the handled routes to the given web app
        """
        pass

class IStreamHandler(ABC):
    """
    Abstract class that defines a streaming data provider
    """
    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def get_value(self) -> Optional[str]:
        pass

    @abstractmethod
    def cleanup(self):
        pass

    @classmethod
    def register(cls, web_app: "WebApp", **kwargs):
        """
        Register this streaming handler with the web app
        :param web_app: web_app instance
        :param kwargs: args for stream handler ctor
        """
        web_app.add_streaming_handler(cls, **kwargs)

class WebApp(bottle.Bottle):
    """
    Web app implementation
    """
    _STREAM_POLL_INTERVAL_IN_MS = 100
    _STREAM_YIELD_INTERVAL_IN_MS = 10  # Small delay between events to avoid flooding
    _HEARTBEAT_INTERVAL_IN_MS = 15000  # Send ping every 15 seconds

    # Paths exempt from Bearer token auth
    _AUTH_EXEMPT_PATHS = {
        "/server/stream",      # SSE — EventSource cannot send custom headers (R003)
        "/server/status",      # Health check — needed by monitoring and E2E tests
    }
    _AUTH_EXEMPT_PREFIXES = (
        "/server/webhook/",    # Webhooks use HMAC auth (R004)
    )

    def __init__(self, context: Context, controller: Controller, config: Config = None):
        super().__init__()
        self.logger = context.logger.getChild("WebApp")
        self._controller = controller
        self._html_path = context.args.html_path
        self._status = context.status
        self._config = config
        self.logger.info("Html path set to: {}".format(self._html_path))
        # Use object.__setattr__ to bypass Bottle's special __setattr__ handling
        # that prevents attribute reassignment (Bottle thinks it's a plugin conflict)
        object.__setattr__(self, '_stop_flag', False)
        self._streaming_handlers = []  # list of (handler, kwargs) pairs

        # Cache index.html template for meta tag injection
        self._index_html_template = self._load_index_html()

        @self.hook('before_request')
        def _check_host_and_auth():
            """Validate Host header and Bearer token on /server/* API endpoints."""
            path = bottle.request.path

            # Only protect /server/* paths
            if not path.startswith("/server/"):
                bottle.request.auth_valid = True
                return

            # --- Host header validation (R009, R010, R011) ---
            # Only enforce when allowed_hostname is configured (opt-in).
            # Default (empty) allows any Host for backward compatibility and
            # Docker/container environments where the hostname is dynamic.
            if self._config and self._config.general.allowed_hostname:
                host = bottle.request.get_header("Host", "")
                # Strip port from Host header
                if ":" in host and not host.startswith("["):
                    host = host.rsplit(":", 1)[0]
                elif host.startswith("[") and "]:" in host:
                    host = host.rsplit(":", 1)[0]

                allowed_hosts = {"localhost", "127.0.0.1", "[::1]",
                                 self._config.general.allowed_hostname}

                if host not in allowed_hosts:
                    bottle.abort(400)
                    return

            # --- Bearer token auth ---

            # Exempt paths
            if path in WebApp._AUTH_EXEMPT_PATHS:
                bottle.request.auth_valid = True
                return
            if path.startswith(WebApp._AUTH_EXEMPT_PREFIXES):
                bottle.request.auth_valid = True
                return

            # No token configured — allow all (backward compat, R005)
            api_token = self._config.general.api_token if self._config else ""
            if not api_token:
                bottle.request.auth_valid = True
                return

            # Validate Bearer token
            auth_header = bottle.request.get_header("Authorization", "")
            if not auth_header.startswith("Bearer "):
                bottle.request.auth_valid = False
                bottle.abort(401, "Unauthorized")
                return

            provided_token = auth_header[7:]  # Strip "Bearer "
            if not hmac.compare_digest(provided_token, api_token):
                bottle.request.auth_valid = False
                bottle.abort(401, "Unauthorized")
                return

            bottle.request.auth_valid = True

        @self.hook('after_request')
        def _add_security_headers():
            # CSP layered with Angular autoCsp (R014).
            # autoCsp emits a <meta> CSP with hash-based script-src/style-src.
            # When both HTTP header and meta tag CSPs exist, the browser enforces
            # BOTH — a resource must pass ALL policies. The HTTP header must be
            # permissive for inline (via 'unsafe-inline') so Angular's inline
            # bootstrap script isn't blocked by default-src fallback. The meta
            # tag's hash-based policy provides the actual inline restriction.
            bottle.response.set_header(
                'Content-Security-Policy',
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "font-src 'self'; "
                "connect-src 'self' https://api.github.com; "
                "img-src 'self' data:; "
                "frame-ancestors 'none'; "
                "object-src 'none'"
            )
            bottle.response.set_header('X-Frame-Options', 'DENY')
            bottle.response.set_header('X-Content-Type-Options', 'nosniff')

    def add_default_routes(self):
        """
        Add the default routes. This must be called after all the handlers have
        been added.
        """
        # Streaming route
        self.get("/server/stream")(self.__web_stream)

        # Front-end routes
        self.route("/")(self.__index)
        self.route("/dashboard")(self.__index)
        self.route("/settings")(self.__index)
        self.route("/autoqueue")(self.__index)
        self.route("/logs")(self.__index)
        self.route("/about")(self.__index)
        # For static files
        self.route("/<file_path:path>")(self.__static)

    def add_handler(self, path: str, handler: Callable):
        self.get(path)(handler)

    def add_post_handler(self, path: str, handler: Callable):
        self.post(path)(handler)

    def add_delete_handler(self, path: str, handler: Callable):
        self.delete(path)(handler)

    def add_streaming_handler(self, handler: Type[IStreamHandler], **kwargs):
        self._streaming_handlers.append((handler, kwargs))

    def process(self):
        """
        Advance the web app state
        """
        pass

    def stop(self):
        """
        Exit gracefully, kill any connections and clean up any state
        """
        # Use object.__setattr__ to bypass Bottle's special __setattr__ handling
        object.__setattr__(self, '_stop_flag', True)

    def _load_index_html(self) -> Optional[str]:
        """Load and cache the index.html template from disk."""
        index_path = os.path.join(self._html_path, "index.html")
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, PermissionError):
            self.logger.warning("index.html not found at {}".format(index_path))
            return None

    def _inject_meta_tag(self, html: str) -> str:
        """Inject api-token meta tag into the HTML before </head>."""
        api_token = self._config.general.api_token if self._config else ""
        safe_token = html_mod.escape(api_token or "", quote=True)
        meta_tag = '<meta name="api-token" content="{}">'.format(safe_token)
        return html.replace("</head>", "    {}\n</head>".format(meta_tag), 1)

    def __index(self):
        """
        Serves index.html with injected api-token meta tag.
        """
        if self._index_html_template is None:
            bottle.abort(404, "index.html not found")
            return

        body = self._inject_meta_tag(self._index_html_template)
        return HTTPResponse(body=body, headers={"Content-Type": "text/html; charset=UTF-8"})

    # noinspection PyMethodMayBeStatic
    def __static(self, file_path: str):
        """
        Serves all the static files
        """
        return static_file(file_path, root=self._html_path)

    @staticmethod
    def _sse_pack(event: str, data: str = "") -> str:
        """Pack data into SSE format"""
        return "event: {}\ndata: {}\n\n".format(event, data)

    def __web_stream(self):
        # Initialize all the handlers
        handlers = [cls(**kwargs) for (cls, kwargs) in self._streaming_handlers]

        try:
            # Setup the response headers for SSE
            bottle.response.content_type = "text/event-stream"
            bottle.response.set_header("Cache-Control", "no-cache")
            bottle.response.set_header("Connection", "keep-alive")
            bottle.response.set_header("X-Accel-Buffering", "no")  # Disable nginx buffering

            # Call setup on all handlers
            for handler in handlers:
                handler.setup()

            # Track time for heartbeat
            last_heartbeat = time.time()

            # Get streaming values until the connection closes
            while not self._stop_flag:
                had_value = False
                for handler in handlers:
                    # Get one value from this handler per iteration
                    # to ensure fair interleaving between handlers
                    value = handler.get_value()
                    if value:
                        yield value
                        had_value = True

                # Send heartbeat ping if interval has elapsed
                now = time.time()
                if (now - last_heartbeat) * 1000 >= WebApp._HEARTBEAT_INTERVAL_IN_MS:
                    yield WebApp._sse_pack("ping")
                    last_heartbeat = now

                # Always sleep between iterations to avoid flooding the connection
                # Use shorter sleep when data is available, longer when idle
                if had_value:
                    time.sleep(WebApp._STREAM_YIELD_INTERVAL_IN_MS / 1000)
                else:
                    time.sleep(WebApp._STREAM_POLL_INTERVAL_IN_MS / 1000)

        finally:
            self.logger.debug("Stream connection stopped by {}".format(
                "server" if self._stop_flag else "client"
            ))

            # Cleanup all handlers
            for handler in handlers:
                handler.cleanup()
