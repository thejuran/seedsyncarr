import json
import collections

from common import Config

# Sensitive fields that must never be returned in API responses.
# Keyed by section name (lowercase), values are field names to redact.
_SENSITIVE_FIELDS = {
    "lftp": ["remote_password", "remote_address", "remote_username", "remote_path"],
    "sonarr": ["sonarr_api_key"],
    "radarr": ["radarr_api_key"],
    "general": ["webhook_secret", "api_token"],
}

_REDACTED = "**REDACTED**"

# Fields whose value ALWAYS serializes as "" regardless of auth status or whether set.
# SEC-02 (D-10/D-11): prevents distinguishing set vs unset via value or length.
_ALWAYS_BLANK_FIELDS = {
    "general": ["webhook_secret", "api_token"],
}

class SerializeConfig:
    @staticmethod
    def config(config: Config, authenticated: bool = False) -> str:
        config_dict = config.as_dict()

        # Make the section names lower case
        keys = list(config_dict.keys())
        config_dict_lowercase = collections.OrderedDict()
        for key in keys:
            config_dict_lowercase[key.lower()] = config_dict[key]

        # Redact sensitive fields before serializing.
        # Skip redaction for authenticated requests (CONF-04 fix).
        if not authenticated:
            for section, fields in _SENSITIVE_FIELDS.items():
                if section in config_dict_lowercase:
                    section_dict = config_dict_lowercase[section]
                    for field in fields:
                        if field in section_dict:
                            section_dict[field] = _REDACTED

        # SEC-02: secret value fields always serialize as "" (D-10/D-11).
        # Applies on both authenticated and unauthenticated paths, overwriting
        # **REDACTED** with "" for these two fields on the unauthenticated path
        # and zeroing the real value on the authenticated path.
        for section, fields in _ALWAYS_BLANK_FIELDS.items():
            if section in config_dict_lowercase:
                for field in fields:
                    if field in config_dict_lowercase[section]:
                        config_dict_lowercase[section][field] = ""

        return json.dumps(config_dict_lowercase)
