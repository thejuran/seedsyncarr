import json
import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin

import requests
import bottle
from bottle import HTTPResponse
from urllib3.util import parse_url

from common import Context, overrides, Config, ConfigError
from ..web_app import IHandler, WebApp
from ..serialize import SerializeConfig
from ..rate_limit import rate_limit

# Printable ASCII without space -- the only characters `requests` accepts in
# a header value without raising InvalidHeader, whose message would embed
# the raw key (122-14, CR-01).
_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")

# Printable ASCII without space -- rejects whitespace, control characters and
# non-ASCII (internationalised) hosts up front, before urlparse or urllib3
# ever see the string (D-11/D-14).
_URL_CHARS = re.compile(r"[\x21-\x7e]+")

# A DNS label is 1-63 characters; underscore is allowed for Docker/Compose
# container and service names (D-11/WR-02).
_HOSTNAME_RE = re.compile(r"[A-Za-z0-9_-]{1,63}(?:\.[A-Za-z0-9_-]{1,63})*\.?")

# Private ranges the Sonarr/Radarr Test Connection path allows, in addition
# to already-public addresses: standard LAN ranges, Tailscale/CGNAT (allowed
# before this change, must not regress), and IPv6 unique-local (LAN-01).
_ALLOWED_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("fc00::/7"),
)

# Cloud-metadata endpoints that fall inside the allowed ranges above and must
# be refused anyway (D-12). 100.100.100.100, Tailscale's MagicDNS address,
# stays allowed.
_METADATA_NETWORKS = (
    ipaddress.ip_network("fd00:ec2::254/128"),   # AWS IMDS (IPv6)
    ipaddress.ip_network("100.100.100.200/32"),  # Alibaba ECS metadata
)

# Deprecated/other reserved ranges that stay refused even though stdlib
# reports is_global=True for them (D-03 "other reserved"; fec0::/10 is
# deprecated IPv6 site-local). The six IPv6-transition entries are explicit
# because the stdlib is_global/is_reserved tables for these prefixes changed
# across CPython patch releases (gh-113171), so relying on them alone would
# make this guard's behaviour depend on which patch release built the image
# (WR-03). ::/96 also contains :: and ::1, which are classified earlier by
# the unspecified and loopback checks, so listing it here only matters for
# other IPv4-compatible addresses.
_REFUSED_NETWORKS = (
    ipaddress.ip_network("fec0::/10"),
    ipaddress.ip_network("2002::/16"),        # 6to4
    ipaddress.ip_network("2001::/32"),        # Teredo
    ipaddress.ip_network("64:ff9b::/96"),     # NAT64 (well-known)
    ipaddress.ip_network("64:ff9b:1::/48"),   # NAT64 (local-use)
    ipaddress.ip_network("::/96"),            # IPv4-compatible
    ipaddress.ip_network("::ffff:0:0:0/96"),  # SIIT
)

# Loopback is allowed only when the URL's explicit port is one of Sonarr's or
# Radarr's own defaults (D-02); any other port, or no port, stays refused.
_ALLOWED_LOOPBACK_PORTS = frozenset({8989, 7878})

_MSG_LOOPBACK_PORT = "Loopback addresses are only allowed on port 8989 (Sonarr) or 7878 (Radarr)"
_MSG_LINK_LOCAL = "URL points to a link-local or cloud-metadata address, which is not allowed"
_MSG_UNSPECIFIED = "URL points to an unspecified address (0.0.0.0 or ::), which is not allowed"
_MSG_MULTICAST = "URL points to a multicast address, which is not allowed"
_MSG_RESERVED = "URL points to a reserved IP address, which is not allowed"
_MSG_UNCHECKABLE = "URL resolves to an address that could not be checked, which is not allowed"
_MSG_BAD_CHARS = "Invalid URL: it contains a space, backslash or other character that is not allowed"
_MSG_CREDENTIALS = "Invalid URL: a user name or password in the URL is not allowed"
_MSG_QUERY = "Invalid URL: a query string or fragment (? or #) is not allowed"
_MSG_BAD_HOSTNAME = "Invalid URL: malformed hostname"


def _classify_resolved_address(
    addr: "ipaddress.IPv4Address | ipaddress.IPv6Address", port: int | None
) -> str | None:
    """Classify a single resolved address as allowed (None) or refused (an
    error string). The check order below is load-bearing:

    IPv6-mapped IPv4 forms (::ffff:a.b.c.d) are unmapped first -- every
    ::ffff: address also reports is_reserved=True in stdlib, so checking
    reserved-ness before unmapping would misclassify an allowed address like
    ::ffff:10.0.0.1. Loopback is checked next, before any reserved check,
    because ::1 and ::ffff:127.0.0.1 both report is_reserved=True too (a
    reserved-first check would block loopback on its own allowed ports).
    Named allow-listed ranges come before the public-address check so a
    quiet LAN IP never has to pass is_global. The public branch requires
    `is_global and not is_reserved` rather than bare is_global, because two
    notations -- ::127.0.0.1 (IPv4-compatible) and 64:ff9b::7f00:1 (NAT64,
    well-known prefix) -- both embed 127.0.0.1 yet report is_global=True;
    both also report is_reserved=True, which is what the "not is_reserved"
    clause closes (it is the only thing standing between those notations and
    a loopback-port-gate bypass). The cloud-metadata check (D-12) sits right
    after link-local and before the named allowed-private-range check, so
    fd00:ec2::254 and 100.100.100.200 are refused even though they would
    otherwise match fc00::/7 or 100.64.0.0/10. The six IPv6-transition
    entries in _REFUSED_NETWORKS (6to4, Teredo, NAT64, IPv4-compatible,
    SIIT) are refused by explicit network membership rather than by
    is_global/is_reserved, because those stdlib properties for these
    specific prefixes changed across CPython patch releases (WR-03,
    gh-113171); this keeps the result independent of the interpreter.
    """
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    if addr.is_unspecified:
        return _MSG_UNSPECIFIED

    if addr.is_loopback:
        return None if port in _ALLOWED_LOOPBACK_PORTS else _MSG_LOOPBACK_PORT

    if addr.is_link_local:
        return _MSG_LINK_LOCAL

    if any(addr in net for net in _METADATA_NETWORKS):
        return _MSG_LINK_LOCAL

    if addr.is_multicast:
        return _MSG_MULTICAST

    if any(addr in net for net in _REFUSED_NETWORKS):
        return _MSG_RESERVED

    if any(addr in net for net in _ALLOWED_PRIVATE_NETWORKS):
        return None

    if addr.is_global and not addr.is_reserved:
        return None

    return _MSG_RESERVED


class ConfigHandler(IHandler):
    def __init__(self, config: Config, context: Context):
        self.logger = context.logger.getChild("ConfigHandler")
        self.__config = config

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        web_app.add_handler("/server/config/get", self.__handle_get_config)
        web_app.add_post_handler(
            "/server/config/set",
            rate_limit(max_requests=60, window_seconds=60.0, logger=self.logger)(self.__handle_set_config)
        )
        web_app.add_handler(
            "/server/config/sonarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0, logger=self.logger)(self.__handle_test_sonarr_connection)
        )
        web_app.add_handler(
            "/server/config/radarr/test-connection",
            rate_limit(max_requests=5, window_seconds=60.0, logger=self.logger)(self.__handle_test_radarr_connection)
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

        Used only by the Sonarr/Radarr Test Connection path (_test_arr_connection):
        LAN ranges, Tailscale/CGNAT, IPv6 unique-local, container/host names
        resolving to any of those, and public addresses are allowed; loopback
        is allowed only on Sonarr's or Radarr's own default port (8989/7878);
        link-local/cloud-metadata, unspecified, multicast, other reserved
        ranges, and loopback on any other port stay refused (LAN-01, LAN-02).

        Validates the exact string it is given -- the caller (_test_arr_connection)
        must normalize once and pass the same string to this function and to
        requests.get, so the host that is checked is the host that is requested
        (D-11, IN-01).

        The order below is load-bearing. A character allow-list (step 1) runs
        before anything else, because urlparse and urllib3 (what `requests`
        actually connects to) can read a backslash differently, and no later
        check can be trusted once the two parsers might disagree about the
        host (CR-01). Credentials, percent-encoding and query/fragment checks
        (steps 4-5) run on the parsed string before the hostname-syntax check
        so they produce a specific message rather than falling through to a
        generic one. The parser-agreement check (step 8) runs after urlparse
        succeeds but before any DNS resolution, so a disagreement is refused
        before getaddrinfo is ever called.

        Known limitation: DNS rebinding (TOCTOU) — getaddrinfo resolves at validation
        time while requests.get resolves again at request time. A DNS rebinding attack
        could bypass this check. Mitigating this requires socket-level interception
        (e.g., ssrfpy or pysafecurl), which is out of scope for a homelab tool.
        """
        # 1. Character allow-list: printable ASCII without space, and no
        # backslash (backslash is itself printable ASCII, so it needs its
        # own check) -- rejects whitespace, control chars and non-ASCII
        # (internationalised) hosts before urlparse/urllib3 ever see the
        # string (D-11, D-14).
        if _URL_CHARS.fullmatch(url) is None or "\\" in url:
            return _MSG_BAD_CHARS

        # 2. Parse once with urlparse.
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
        except ValueError:
            return "Invalid URL"

        # 3. Scheme and hostname presence.
        if parsed.scheme not in {"http", "https"}:
            return "Only http and https URLs are allowed"

        if not hostname:
            return "Invalid URL: no hostname"

        # 4. Credentials and percent-encoding in the authority.
        netloc = parsed.netloc or ""
        if "@" in netloc:
            return _MSG_CREDENTIALS
        if "%" in netloc:
            return "Invalid URL"

        # 5. Query string / fragment -- requests would append the API path
        # inside the query or fragment, so the requested path would differ
        # from the configured one (D-14).
        if "?" in url or "#" in url:
            return _MSG_QUERY

        # 6. Port syntax.
        try:
            port = parsed.port
        except ValueError:
            return "Invalid URL: invalid port"

        # 7. Hostname syntax -- malformed hostnames (consecutive dots, a
        # bare dot, an over-length label) must produce this JSON error
        # rather than letting getaddrinfo raise UnicodeError past this
        # function's boundary (WR-02). IP literals skip this check.
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if len(hostname) > 253 or _HOSTNAME_RE.fullmatch(hostname) is None:
                return _MSG_BAD_HOSTNAME

        # 8. Parser agreement: requests connects via urllib3.util.parse_url,
        # not urlparse. Refuse anything the two parsers would read
        # differently, rather than trusting urlparse's view of the host
        # (CR-01).
        try:
            u3 = parse_url(url)
        except ValueError:
            return "Invalid URL"
        u3_scheme = (u3.scheme or "").lower()
        u3_host = (u3.host or "").strip("[]").lower()
        if u3_scheme != parsed.scheme or u3_host != hostname.lower() or u3.port != port:
            return "Invalid URL"

        # 9. Resolve. UnicodeError/ValueError are defence in depth for
        # hostname forms step 7's regex does not catch (WR-02).
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except (socket.gaierror, UnicodeError, ValueError):
            return "Cannot resolve hostname"

        if not addr_infos:
            return "Cannot resolve hostname"

        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                return _MSG_UNCHECKABLE
            error_msg = _classify_resolved_address(addr, port)
            if error_msg is not None:
                return error_msg

        return None

    def __handle_get_config(self):
        authenticated = getattr(bottle.request, 'auth_valid', False)
        out_json = SerializeConfig.config(self.__config, authenticated=authenticated)
        return HTTPResponse(body=out_json)

    def __handle_set_config(self) -> HTTPResponse:
        # No path params — all fields from JSON body (D-01/D-03).
        # NOTE: no try/except around bottle.request.json — bottle 400s invalid JSON
        # (with Content-Type: application/json) before this handler runs (FINDING 3 /
        # RESEARCH §RQ-1 case 3). wrong/absent content-type → returns None silently.
        body = bottle.request.json

        if not body or not isinstance(body, dict):
            return HTTPResponse(body="Invalid request body", status=400)

        section = body.get("section")
        key = body.get("key")
        value = body.get("value")

        # FINDING 1: reject non-string / empty section|key BEFORE any config lookup.
        # A truthy non-string (list/dict/number) would reach has_section/getattr/
        # has_property and raise TypeError → uncaught 500/DoS. isinstance guard first.
        if not isinstance(section, str) or not section or not isinstance(key, str) or not key:
            return HTTPResponse(body="Invalid request body", status=400)

        # D-06: missing-or-empty value is 400 (was 404 route-miss under GET regex)
        if value is None or str(value) == "":
            return HTTPResponse(body="Invalid request body", status=400)

        value_str = str(value)

        # Preserve existing validation status codes (D-05)
        if not self.__config.has_section(section):
            return HTTPResponse(
                body="There is no section '{}' in config".format(section), status=404
            )
        inner_config = getattr(self.__config, section)
        if not inner_config.has_property(key):
            return HTTPResponse(
                body="Section '{}' in config has no option '{}'".format(section, key), status=404
            )
        try:
            inner_config.set_property(key, value_str)
            return HTTPResponse(body="{}.{} set to {}".format(section, key, value_str))
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

        api_key = api_key.strip()
        if not _API_KEY_CHARS.fullmatch(api_key):
            return HTTPResponse(
                body=json.dumps({"success": False, "error": "{} API key contains invalid characters".format(service_name)}),
                content_type="application/json"
            )

        # Normalize once: the exact same string is validated and requested,
        # so the host the guard checked is the host that is actually
        # requested (D-11/IN-01).
        url = raw_url.strip().rstrip("/")

        # SSRF protection: validate URL before making any outbound request
        error_msg = ConfigHandler._validate_url(url)
        if error_msg is not None:
            return HTTPResponse(
                body=json.dumps({"success": False, "error": error_msg}),
                content_type="application/json"
            )

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
        except Exception as e:
            # requests embeds header values, including the API key, in
            # InvalidHeader and similar messages, so this boundary logs only
            # the exception type, never the message or a traceback
            # (122-14, CR-01; D-14 of 122-CONTEXT).
            self.logger.error(
                "Unexpected error testing %s connection (%s)",
                service_name, type(e).__name__
            )
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
