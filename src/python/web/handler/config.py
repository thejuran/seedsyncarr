# Copyright 2017, Inderpreet Singh, All rights reserved.

import json
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse, unquote

import requests
import bottle
from bottle import HTTPResponse

from common import overrides, Config, ConfigError
from ..web_app import IHandler, WebApp
from ..serialize import SerializeConfig


class ConfigHandler(IHandler):
    def __init__(self, config: Config):
        self.__config = config

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler("/server/config/get", self.__handle_get_config)
        # The regex allows slashes in values
        web_app.add_handler("/server/config/set/<section>/<key>/<value:re:.+>", self.__handle_set_config)
        web_app.add_handler("/server/config/sonarr/test-connection", self.__handle_test_sonarr_connection)
        web_app.add_handler("/server/config/radarr/test-connection", self.__handle_test_radarr_connection)

    @staticmethod
    def _validate_url(url: str) -> Optional[str]:
        """Validate URL for SSRF protection. Returns error string or None if valid."""
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

    def __handle_test_sonarr_connection(self):
        sonarr_url = self.__config.sonarr.sonarr_url
        sonarr_api_key = self.__config.sonarr.sonarr_api_key

        if not sonarr_url or not sonarr_url.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Sonarr URL is required"}),
                content_type="application/json"
            )
        if not sonarr_api_key or not sonarr_api_key.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Sonarr API key is required"}),
                content_type="application/json"
            )

        # SSRF protection: validate URL before making any outbound request
        error_msg = ConfigHandler._validate_url(sonarr_url.strip())
        if error_msg is not None:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": error_msg}),
                content_type="application/json"
            )

        # Strip trailing slash from URL
        url = sonarr_url.rstrip("/")

        try:
            response = requests.get(
                "{}/api/v3/system/status".format(url),
                headers={"X-Api-Key": sonarr_api_key},
                timeout=10
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
            else:
                return HTTPResponse(
                    body=json.dumps({"success": False, "error": "Sonarr returned status {}".format(response.status_code)}),
                    content_type="application/json"
                )
        except requests.ConnectionError:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection refused - check Sonarr URL"}),
                content_type="application/json"
            )
        except requests.Timeout:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection timed out"}),
                content_type="application/json"
            )
        except Exception:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "An unexpected error occurred"}),
                content_type="application/json"
            )

    def __handle_test_radarr_connection(self):
        radarr_url = self.__config.radarr.radarr_url
        radarr_api_key = self.__config.radarr.radarr_api_key

        if not radarr_url or not radarr_url.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Radarr URL is required"}),
                content_type="application/json"
            )
        if not radarr_api_key or not radarr_api_key.strip():
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Radarr API key is required"}),
                content_type="application/json"
            )

        # SSRF protection: validate URL before making any outbound request
        error_msg = ConfigHandler._validate_url(radarr_url.strip())
        if error_msg is not None:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": error_msg}),
                content_type="application/json"
            )

        # Strip trailing slash from URL
        url = radarr_url.rstrip("/")

        try:
            response = requests.get(
                "{}/api/v3/system/status".format(url),
                headers={"X-Api-Key": radarr_api_key},
                timeout=10
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
            else:
                return HTTPResponse(
                    body=json.dumps({"success": False, "error": "Radarr returned status {}".format(response.status_code)}),
                    content_type="application/json"
                )
        except requests.ConnectionError:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection refused - check Radarr URL"}),
                content_type="application/json"
            )
        except requests.Timeout:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "Connection timed out"}),
                content_type="application/json"
            )
        except Exception:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "An unexpected error occurred"}),
                content_type="application/json"
            )
