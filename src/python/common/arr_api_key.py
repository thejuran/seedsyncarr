import re
from typing import Any

# Printable ASCII without space: the application's policy for a Sonarr/Radarr
# API key. It is deliberately narrower than what `requests` accepts in a
# header value, and it excludes every value `requests` rejects with
# InvalidHeader, whose message would embed the raw key (122-14, CR-01).
# Shared by Save, Test Connection and the queue client so the three can never
# disagree (Phase 128, D-01).
ARR_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")


def normalize_arr_api_key(raw: Any) -> str:
    """Return the key with surrounding whitespace removed, or "" when it is not a str."""
    if not isinstance(raw, str):
        return ""
    return raw.strip()


def is_valid_arr_api_key(key: Any) -> bool:
    """Return True only for a non-empty str made solely of printable ASCII without space."""
    if not isinstance(key, str):
        return False
    return ARR_API_KEY_CHARS.fullmatch(key) is not None
