import functools
import hmac
import hashlib
import json
import os
import logging
from typing import Optional

from bottle import HTTPResponse, request

from common import overrides
from common.config import Config
from controller.webhook_manager import WebhookManager
from ..rate_limit import rate_limit
from ..web_app import IHandler, WebApp

logger = logging.getLogger(__name__)

_WEBHOOK_MAX_BODY_BYTES = 1_048_576  # 1 MB

class WebhookHandler(IHandler):
    """
    Handles webhook POST requests from Sonarr and Radarr.
    Extracts file names from import events and enqueues them via WebhookManager.
    """

    def __init__(self, webhook_manager: WebhookManager, config: Config):
        self.__webhook_manager = webhook_manager
        self.__config = config

    @overrides(IHandler)
    def add_routes(self, web_app: WebApp):
        """Register webhook endpoints.

        Execution order per request:
          1. fail-closed guard (503 if require_secret ON and no secret — reads no body, no counter)
          2. rate_limit (429 if over 60/60s budget — independent closures per route, D-09)
          3. _handle_webhook (413 / HMAC / JSON parse / enqueue)
        """
        web_app.add_post_handler("/server/webhook/sonarr", self._make_require_secret_guard(rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_sonarr_webhook)))
        web_app.add_post_handler("/server/webhook/radarr", self._make_require_secret_guard(rate_limit(max_requests=60, window_seconds=60.0)(self.__handle_radarr_webhook)))

    def _make_require_secret_guard(self, handler):
        """Return a wrapper that fails closed with 503 when webhook_require_secret is on but no secret is set.

        The wrapper is outermost (applied OUTSIDE rate_limit) so 503 fires before:
        - the rate-limit counter is consulted (BLOCKER 2 — 429 cannot mask 503), and
        - any request body is read.

        When webhook_require_secret is False (default) OR a secret is configured, the
        wrapper delegates to handler() unchanged, preserving backward compatibility.
        """
        @functools.wraps(handler)
        def wrapper():
            if self.__config.general.webhook_require_secret and not self.__config.general.webhook_secret:
                logger.warning(
                    "Webhook request rejected: webhook_require_secret is enabled but no "
                    "webhook_secret is configured."
                )
                return HTTPResponse(status=503, body="Service unavailable")
            return handler()
        return wrapper

    def __handle_sonarr_webhook(self) -> HTTPResponse:
        """Handle Sonarr webhook POST."""
        return self._handle_webhook("Sonarr", WebhookHandler._extract_sonarr_title)

    def __handle_radarr_webhook(self) -> HTTPResponse:
        """Handle Radarr webhook POST."""
        return self._handle_webhook("Radarr", WebhookHandler._extract_radarr_title)

    def _verify_hmac(self) -> Optional[HTTPResponse]:
        """
        Verify HMAC signature on the webhook request.

        If webhook_secret is empty or None, verification is skipped (backward compat).
        Reads the raw body, computes expected HMAC-SHA256, and compares with
        the X-Webhook-Signature header using a constant-time compare.

        Returns:
            HTTPResponse(401) if signature is missing or invalid, None on success.
        """
        secret = self.__config.general.webhook_secret
        if not secret:
            # No secret configured — skip verification for backward compatibility
            return None

        # Read raw body bytes, then reset the stream for downstream JSON parsing
        body_bytes = request.body.read()
        request.body.seek(0)

        # Compute expected HMAC-SHA256 signature
        expected = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        # Read signature from header
        provided_signature = request.headers.get("X-Webhook-Signature", "")
        if not provided_signature:
            logger.warning("Webhook request missing X-Webhook-Signature header")
            return HTTPResponse(status=401, body="Missing webhook signature")

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected, provided_signature):
            logger.warning("Webhook request has invalid HMAC signature")
            return HTTPResponse(status=401, body="Invalid webhook signature")

        return None

    def _handle_webhook(self, source: str, extract_title_fn) -> HTTPResponse:
        """
        Generic webhook handler for both Sonarr and Radarr.

        Args:
            source: Source service name ("Sonarr" or "Radarr")
            extract_title_fn: Function to extract title from request body

        Returns:
            HTTPResponse with appropriate status code
        """
        # Reject oversized payloads before reading body (WHOOK-01)
        if request.content_length is not None and request.content_length > _WEBHOOK_MAX_BODY_BYTES:
            return HTTPResponse(status=413, body="Payload too large")

        # Verify HMAC signature when webhook_secret is configured
        auth_error = self._verify_hmac()
        if auth_error is not None:
            return auth_error

        # Parse JSON body
        try:
            body = request.json
        except (ValueError, json.JSONDecodeError):
            return HTTPResponse(status=400, body="Invalid JSON")

        if not body:
            return HTTPResponse(status=400, body="Empty body")

        # Extract event type
        event_type = body.get("eventType", "")

        # Handle Test events (sent when webhook is first configured)
        if event_type == "Test":
            logger.info("{} webhook test event received".format(source))
            return HTTPResponse(status=200, body="Test OK")

        # Only process Download (import) events
        if event_type != "Download":
            logger.debug("{} webhook ignored event type: {}".format(source, event_type))
            return HTTPResponse(status=200, body="OK")

        # Extract title
        title = extract_title_fn(body)
        if not title:
            logger.debug("{} webhook Download event has no extractable title".format(source))
            return HTTPResponse(status=200, body="OK")

        # Enqueue import
        self.__webhook_manager.enqueue_import(source, title)
        return HTTPResponse(status=200, body="OK")

    @staticmethod
    def _extract_sonarr_title(body: dict) -> str:
        """
        Extract title from Sonarr webhook body.
        Fallback chain: episodeFile.sourcePath (basename) -> release.releaseTitle -> series.title

        Args:
            body: Parsed JSON body from Sonarr webhook

        Returns:
            Extracted title or empty string if none found
        """
        # Try episodeFile.sourcePath (most accurate - actual file name)
        episode_file = body.get("episodeFile", {})
        source_path = episode_file.get("sourcePath", "")
        if source_path:
            return os.path.basename(source_path)

        # Fallback to release.releaseTitle
        release = body.get("release", {})
        release_title = release.get("releaseTitle", "")
        if release_title:
            return release_title

        # Fallback to series.title (least accurate)
        series = body.get("series", {})
        series_title = series.get("title", "")
        if series_title:
            return series_title

        return ""

    @staticmethod
    def _extract_radarr_title(body: dict) -> str:
        """
        Extract title from Radarr webhook body.
        Fallback chain: movieFile.sourcePath (basename) -> release.releaseTitle -> movie.title

        Args:
            body: Parsed JSON body from Radarr webhook

        Returns:
            Extracted title or empty string if none found
        """
        # Try movieFile.sourcePath (most accurate - actual file name)
        movie_file = body.get("movieFile", {})
        source_path = movie_file.get("sourcePath", "")
        if source_path:
            return os.path.basename(source_path)

        # Fallback to release.releaseTitle
        release = body.get("release", {})
        release_title = release.get("releaseTitle", "")
        if release_title:
            return release_title

        # Fallback to movie.title (least accurate)
        movie = body.get("movie", {})
        movie_title = movie.get("title", "")
        if movie_title:
            return movie_title

        return ""
