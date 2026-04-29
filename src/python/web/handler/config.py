import json
import ipaddress
import logging
import socket
from urllib.parse import urlparse, urljoin, unquote

import requests
import bottle
from bottle import HTTPResponse

from common import overrides, Config, ConfigError
from ..web_app import IHandler, WebApp
from ..serialize import SerializeConfig
from ..rate_limit import rate_limit

logger = logging.getLogger(__name__)

class ConfigHandler(IHandler):
    def __init__(self, config: Config):
        self.__config = config

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler("/server/config/get", self.__handle_get_config)
        # The regex allows slashes in values
        web_app.add_handler(
            "/server/config/set/<section>/<key>/<value:re:.+>",
            rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_set_config)
        )
        web_app.add_handler(
            "/server/config/sonarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_sonarr_connection)
        )
        web_app.add_handler(
            "/server/config/radarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0)(self.__handle_test_radarr_connection)
        )

    @staticmethod
    def _sanitize_redirect_location(raw_location: str, base_url: str) -> str:
        """Sanitize and resolve a redirect Location header for display.

        Truncates to 200 chars, resolves relative paths against the base URL
        using urljoin for correct RFC 3986 handling.
        """
        if not raw_location:
            return "unknown"
        location = raw_location[:200]
        # Resolve relative Location against the base URL
        if not location.startswith(("http://", "https://")):
            if base_url and base_url.startswith(("http://", "https://")):
                location = urljoin(base_url + "/", location)
        return location

    @staticmethod
    def _validate_url(url: str) -> str | None:
        """Validate URL for SSRF protection. Returns error string or None if valid.

        Known limitation: DNS rebinding (TOCTOU) — getaddrinfo resolves at validation
        time while requests.get resolves again at request time. A DNS rebinding attack
        could bypass this check. Mitigating this requires socket-level interception
        (e.g., ssrfpy or pysafecurl), which is out of scope for a homelab tool.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return "Only http and https URLs are allowed"

        hostname = parsed.hostname
        if not hostname:
            return "Invalid URL: no hostname"

        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                try:
                    addr = ipaddress.ip_address(ip_str)
                    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
                        return "URL resolves to a private/reserved IP address"
                except ValueError:
                    pass
        except socket.gaierror:
            return "Cannot resolve hostname"

        return None

    def __handle_get_config(self):
        authenticated = getattr(bottle.request, 'auth_valid', False)
        out_json = SerializeConfig.config(self.__config, authenticated=authenticated)
        return HTTPResponse(body=out_json)

    def __handle_set_config(self, section: str, key: str, value: str):
        # value is double encoded
        value = unquote(value)

        if not self.__config.has_section(section):
            return HTTPResponse(body="There is no section '{}' in config".format(section), status=404)
        inner_config = getattr(self.__config, section)
        if not inner_config.has_property(key):
            return HTTPResponse(body="Section '{}' in config has no option '{}'".format(section, key), status=404)
        try:
            inner_config.set_property(key, value)
            return HTTPResponse(body="{}.{} set to {}".format(section, key, value))
        except ConfigError as e:
            return HTTPResponse(body=str(e), status=400)

    def _test_arr_connection(self, service_name: str, raw_url: str | None, api_key: str | None) -> HTTPResponse:
        """Shared logic for testing Sonarr/Radarr API connections."""
        if not raw_url or not raw_url.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} URL is required".format(service_name)}),
                content_type="application/json"
            )
        if not api_key or not api_key.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} API key is required".format(service_name)}),
                content_type="application/json"
            )

        # SSRF protection: validate URL before making any outbound request
        error_msg = ConfigHandler._validate_url(raw_url.strip())
        if error_msg is not None:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": error_msg}),
                content_type="application/json"
            )

        # Strip trailing slash from URL
        url = raw_url.rstrip("/")

        try:
            response = requests.get(
                "{}/api/v3/system/status".format(url),
                headers={"X-Api-Key": api_key},
                timeout=10,
                allow_redirects=False
            )
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")
                return HTTPResponse(
                    body=json.dumps({"success": True, "version": version}),
                    content_type="application/json"
                )
            elif response.status_code == 401:
                return HTTPResponse(
                    body=json.dumps({"success": False, "error": "Invalid API key"}),
                    content_type="application/json"
                )
            elif response.status_code in (301, 302, 307, 308):
                location = self._sanitize_redirect_location(response.headers.get("Location", ""), url)
                return HTTPResponse(
                    body=json.dumps({"success": False, "error": "URL redirects to {}. Update the URL to the final destination.".format(location)}),
                    content_type="application/json"
                )
            else:
                return HTTPResponse(
                    body=json.dumps({"success": False, "error": "{} returned status {}".format(service_name, response.status_code)}),
                    content_type="application/json"
                )
        except requests.ConnectionError:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection refused - check {} URL".format(service_name)}),
                content_type="application/json"
            )
        except requests.Timeout:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection timed out"}),
                content_type="application/json"
            )
        except Exception:
            logger.exception("Unexpected error testing %s connection", service_name)
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "An unexpected error occurred"}),
                content_type="application/json"
            )

    def __handle_test_sonarr_connection(self):
        return self._test_arr_connection(
            "Sonarr",
            self.__config.sonarr.sonarr_url,
            self.__config.sonarr.sonarr_api_key
        )

    def __handle_test_radarr_connection(self):
        return self._test_arr_connection(
            "Radarr",
            self.__config.radarr.radarr_url,
            self.__config.radarr.radarr_api_key
        )
