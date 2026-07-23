import functools
import hmac
import hashlib
import json
import os
import logging
from typing import Optional, Tuple

from bottle import HTTPResponse, request

from common import overrides, sanitize_log_value
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

        # Only process Download (import) events. INFO (not debug) so production
        # logs record exactly which events were received and ignored -- an
        # unexplained import mark must be traceable to a specific webhook.
        if event_type != "Download":
            logger.info("{} webhook ignored event type: '{}'".format(
                source, sanitize_log_value(str(event_type))))
            return HTTPResponse(status=200, body="OK")

        # Extract title from the imported file's sourcePath ONLY. A Download
        # event without a file path is NOT treated as an import: falling back to
        # release.releaseTitle would false-positively mark a file imported (for a
        # single-file release the releaseTitle equals the file name exactly),
        # which arms auto-delete for a file *arr never actually imported.
        title, provenance = extract_title_fn(body)
        if not title:
            release_title = body.get("release", {}).get("releaseTitle", "")
            logger.warning(
                "{} webhook Download event has no source file path; NOT marking an "
                "import (release.releaseTitle: '{}')".format(
                    source, sanitize_log_value(release_title)
                )
            )
            return HTTPResponse(status=200, body="OK")

        # Enqueue import; provenance records which event/field produced the title
        # so every imported-mark in the logs is traceable to its webhook.
        self.__webhook_manager.enqueue_import(
            source, title, provenance="eventType={}, {}".format(event_type, provenance)
        )
        return HTTPResponse(status=200, body="OK")

    @staticmethod
    def _extract_sonarr_title(body: dict) -> Tuple[str, str]:
        """
        Extract the imported file name from a Sonarr webhook body.
        Only episodeFile.sourcePath is trusted: it is the actual imported file.
        releaseTitle/series.title fallbacks were removed -- they can mark files
        imported without a real import (see _handle_webhook).

        Args:
            body: Parsed JSON body from Sonarr webhook

        Returns:
            (title, provenance) tuple; ("", "") if no source path found
        """
        episode_file = body.get("episodeFile", {})
        source_path = episode_file.get("sourcePath", "")
        if source_path:
            return os.path.basename(source_path), "episodeFile.sourcePath"
        return "", ""

    @staticmethod
    def _extract_radarr_title(body: dict) -> Tuple[str, str]:
        """
        Extract the imported file name from a Radarr webhook body.
        Only movieFile.sourcePath is trusted: it is the actual imported file.
        releaseTitle/movie.title fallbacks were removed -- they can mark files
        imported without a real import (see _handle_webhook).

        Args:
            body: Parsed JSON body from Radarr webhook

        Returns:
            (title, provenance) tuple; ("", "") if no source path found
        """
        movie_file = body.get("movieFile", {})
        source_path = movie_file.get("sourcePath", "")
        if source_path:
            return os.path.basename(source_path), "movieFile.sourcePath"
        return "", ""
