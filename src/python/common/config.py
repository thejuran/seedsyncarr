import configparser
import os
from typing import Dict, Optional
from io import StringIO
import collections
from abc import ABC
from typing import Type, TypeVar, Callable, Any

from .encryption import load_or_create_key, is_ciphertext, encrypt_field, decrypt_field, DecryptionError
from .error import AppError
from .persist import Persist, PersistError
from .types import overrides

# Module-level tuple listing the 5 secret field paths used for encryption.
# Format: (inner_attr_name_on_Config, field_name, INI_section_name)
# INI sections are TitleCase; Config attrs are lowercase.
# The [Encryption] section itself is intentionally NOT listed here —
# the enabled boolean is not a secret and must never be encrypted (T-81-02-07).
_SECRET_FIELD_PATHS = (
    ("general", "webhook_secret", "General"),
    ("general", "api_token", "General"),
    ("lftp", "remote_password", "Lftp"),
    ("sonarr", "sonarr_api_key", "Sonarr"),
    ("radarr", "radarr_api_key", "Radarr"),
)


def _strtobool(value: str) -> int:
    """Convert a string representation of a boolean to 1 or 0.

    Replacement for the removed distutils.util.strtobool (removed in Python 3.12).
    Returns 1 for: 'y', 'yes', 't', 'true', 'on', '1' (case-insensitive).
    Returns 0 for: 'n', 'no', 'f', 'false', 'off', '0' (case-insensitive).
    Raises ValueError for any other value.
    """
    lower = value.lower()
    if lower in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif lower in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("Invalid truth value: {!r}".format(value))

class ConfigError(AppError):
    """
    Exception indicating a bad config value
    """
    pass

InnerConfigType = Dict[str, str]
OuterConfigType = Dict[str, InnerConfigType]

# Source: https://stackoverflow.com/a/39205612/8571324
T = TypeVar('T', bound='InnerConfig')

class Converters:
    @staticmethod
    def null(_: T, __: str, value: str) -> str:
        return value

    @staticmethod
    def int(cls: T, name: str, value: str) -> int:
        if not value:
            raise ConfigError("Bad config: {}.{} is empty".format(
                cls.__name__, name
            ))
        try:
            val = int(value)
        except ValueError:
            raise ConfigError("Bad config: {}.{} ({}) must be an integer value".format(
                cls.__name__, name, value
            ))
        return val

    @staticmethod
    def bool(cls: T, name: str, value: str) -> bool:
        if not value:
            raise ConfigError("Bad config: {}.{} is empty".format(
                cls.__name__, name
            ))
        try:
            val = bool(_strtobool(value))
        except ValueError:
            raise ConfigError("Bad config: {}.{} ({}) must be a boolean value".format(
                cls.__name__, name, value
            ))
        return val

class Checkers:
    @staticmethod
    def null(_: T, __: str, value: Any) -> Any:
        return value

    @staticmethod
    def string_nonempty(cls: T, name: str, value: str) -> str:
        if not value or not value.strip():
            raise ConfigError("Bad config: {}.{} is empty".format(
                cls.__name__, name
            ))
        return value

    @staticmethod
    def int_non_negative(cls: T, name: str, value: int) -> int:
        if value < 0:
            raise ConfigError("Bad config: {}.{} ({}) must be zero or greater".format(
                cls.__name__, name, value
            ))
        return value

    @staticmethod
    def int_positive(cls: T, name: str, value: int) -> int:
        if value < 1:
            raise ConfigError("Bad config: {}.{} ({}) must be greater than 0".format(
                cls.__name__, name, value
            ))
        return value

class InnerConfig(ABC):
    """
    Abstract base class for a config section
    Config values are exposed as properties. They must be set using their native type.
    Internal utility methods are provided to convert strings to native types. These are
    only used when creating config from a dict.

    Implementation details:
    Each property has associated with is a checker and a converter function.
    The checker function performs boundary check on the native type value.
    The converter function converts the string representation into the native type.
    """
    class PropMetadata:
        """Tracks property metadata"""
        def __init__(self, checker: Callable, converter: Callable):
            self.checker = checker
            self.converter = converter

    # Global map to map a property to its metadata
    # Is there a way for each concrete class to do this separately?
    __prop_addon_map = collections.OrderedDict()

    @classmethod
    def _create_property(cls, name: str, checker: Callable, converter: Callable) -> property:
        prop = property(fget=lambda s: s._get_property(name),
                        fset=lambda s, v: s._set_property(name, v, checker))
        prop_addon = InnerConfig.PropMetadata(checker=checker, converter=converter)
        InnerConfig.__prop_addon_map[prop] = prop_addon
        return prop

    def _get_property(self, name: str) -> Any:
        return getattr(self, "__" + name, None)

    def _set_property(self, name: str, value: Any, checker: Callable):
        # Allow setting to None for the first time
        if value is None and self._get_property(name) is None:
            setattr(self, "__" + name, None)
        else:
            setattr(self, "__" + name, checker(self.__class__, name, value))

    @classmethod
    def from_dict(cls: Type[T], config_dict: InnerConfigType) -> T:
        """
        Construct and return inner config from a dict
        Dict values can be either native types, or str representations
        """
        config_dict = dict(config_dict)  # copy that we can modify

        # Loop over all the property name, and set them to the value given in config_dict
        # Raise error if a matching key is not found in config_dict
        inner_config = cls()
        property_map = {p: getattr(cls, p) for p in dir(cls) if isinstance(getattr(cls, p), property)}
        for name, prop in property_map.items():
            if name not in config_dict:
                raise ConfigError("Missing config: {}.{}".format(cls.__name__, name))
            inner_config.set_property(name, config_dict[name])
            del config_dict[name]

        # Raise error if a key in config_dict did not match a property
        extra_keys = config_dict.keys()
        if extra_keys:
            raise ConfigError("Unknown config: {}.{}".format(cls.__name__, next(iter(extra_keys))))

        return inner_config

    def as_dict(self) -> InnerConfigType:
        """
        Return the dict representation of the inner config
        """
        config_dict = collections.OrderedDict()
        cls = self.__class__
        my_property_to_name_map = {getattr(cls, p): p for p in dir(cls) if isinstance(getattr(cls, p), property)}
        # Arrange prop names in order of creation. Use the prop map to get the order
        # Prop map contains all properties of all config classes, so filtering is required
        all_properties = InnerConfig.__prop_addon_map.keys()
        for prop in all_properties:
            if prop in my_property_to_name_map.keys():
                name = my_property_to_name_map[prop]
                config_dict[name] = getattr(self, name)
        return config_dict

    def has_property(self, name: str) -> bool:
        """
        Returns true if the given property exists, false otherwise
        """
        try:
            return isinstance(getattr(self.__class__, name), property)
        except AttributeError:
            return False

    def set_property(self, name: str, value: Any):
        """
        Set a property dynamically.
        Converts str values to native types using the property's converter.
        """
        cls = self.__class__
        prop_addon = InnerConfig.__prop_addon_map[getattr(cls, name)]
        # Do the conversion if value is of type str
        native_value = prop_addon.converter(cls, name, value) if type(value) is str else value
        # Set the property, which will invoke the checker
        self._set_property(name, native_value, prop_addon.checker)

# Useful aliases
IC = InnerConfig
PROP = InnerConfig._create_property  # intentional protected access: module-level shorthand

class Config(Persist):
    """
    Configuration registry
    """
    class General(IC):
        debug = PROP("debug", Checkers.null, Converters.bool)
        verbose = PROP("verbose", Checkers.null, Converters.bool)
        webhook_secret = PROP("webhook_secret", Checkers.null, Converters.null)
        api_token = PROP("api_token", Checkers.null, Converters.null)
        allowed_hostname = PROP("allowed_hostname", Checkers.null, Converters.null)

        def __init__(self):
            super().__init__()
            self.debug = None
            self.verbose = None
            self.webhook_secret = None
            self.api_token = None
            self.allowed_hostname = None

    class Lftp(IC):
        remote_address = PROP("remote_address", Checkers.string_nonempty, Converters.null)
        remote_username = PROP("remote_username", Checkers.string_nonempty, Converters.null)
        remote_password = PROP("remote_password", Checkers.string_nonempty, Converters.null)
        remote_port = PROP("remote_port", Checkers.int_positive, Converters.int)
        remote_path = PROP("remote_path", Checkers.string_nonempty, Converters.null)
        local_path = PROP("local_path", Checkers.string_nonempty, Converters.null)
        remote_path_to_scan_script = PROP("remote_path_to_scan_script", Checkers.string_nonempty, Converters.null)
        use_ssh_key = PROP("use_ssh_key", Checkers.null, Converters.bool)
        num_max_parallel_downloads = PROP("num_max_parallel_downloads", Checkers.int_positive, Converters.int)
        num_max_parallel_files_per_download = PROP("num_max_parallel_files_per_download",
                                                   Checkers.int_positive,
                                                   Converters.int)
        num_max_connections_per_root_file = PROP("num_max_connections_per_root_file",
                                                 Checkers.int_positive,
                                                 Converters.int)
        num_max_connections_per_dir_file = PROP("num_max_connections_per_dir_file",
                                                Checkers.int_positive,
                                                Converters.int)
        num_max_total_connections = PROP("num_max_total_connections", Checkers.int_non_negative, Converters.int)
        use_temp_file = PROP("use_temp_file", Checkers.null, Converters.bool)

        def __init__(self):
            super().__init__()
            self.remote_address = None
            self.remote_username = None
            self.remote_password = None
            self.remote_port = None
            self.remote_path = None
            self.local_path = None
            self.remote_path_to_scan_script = None
            self.use_ssh_key = None
            self.num_max_parallel_downloads = None
            self.num_max_parallel_files_per_download = None
            self.num_max_connections_per_root_file = None
            self.num_max_connections_per_dir_file = None
            self.num_max_total_connections = None
            self.use_temp_file = None

    class Controller(IC):
        interval_ms_remote_scan = PROP("interval_ms_remote_scan", Checkers.int_positive, Converters.int)
        interval_ms_local_scan = PROP("interval_ms_local_scan", Checkers.int_positive, Converters.int)
        interval_ms_downloading_scan = PROP("interval_ms_downloading_scan", Checkers.int_positive, Converters.int)
        extract_path = PROP("extract_path", Checkers.string_nonempty, Converters.null)
        use_local_path_as_extract_path = PROP("use_local_path_as_extract_path", Checkers.null, Converters.bool)
        max_tracked_files = PROP("max_tracked_files", Checkers.int_positive, Converters.int)

        def __init__(self):
            super().__init__()
            self.interval_ms_remote_scan = None
            self.interval_ms_local_scan = None
            self.interval_ms_downloading_scan = None
            self.extract_path = None
            self.use_local_path_as_extract_path = None
            self.max_tracked_files = None

    class Web(InnerConfig):
        port = PROP("port", Checkers.int_positive, Converters.int)

        def __init__(self):
            super().__init__()
            self.port = None

    class AutoQueue(InnerConfig):
        enabled = PROP("enabled", Checkers.null, Converters.bool)
        patterns_only = PROP("patterns_only", Checkers.null, Converters.bool)
        auto_extract = PROP("auto_extract", Checkers.null, Converters.bool)

        def __init__(self):
            super().__init__()
            self.enabled = None
            self.patterns_only = None
            self.auto_extract = None

    class Sonarr(IC):
        enabled = PROP("enabled", Checkers.null, Converters.bool)
        sonarr_url = PROP("sonarr_url", Checkers.null, Converters.null)
        sonarr_api_key = PROP("sonarr_api_key", Checkers.null, Converters.null)

        def __init__(self):
            super().__init__()
            self.enabled = None
            self.sonarr_url = None
            self.sonarr_api_key = None

    class Radarr(IC):
        enabled = PROP("enabled", Checkers.null, Converters.bool)
        radarr_url = PROP("radarr_url", Checkers.null, Converters.null)
        radarr_api_key = PROP("radarr_api_key", Checkers.null, Converters.null)

        def __init__(self):
            super().__init__()
            self.enabled = None
            self.radarr_url = None
            self.radarr_api_key = None

    class AutoDelete(IC):
        enabled = PROP("enabled", Checkers.null, Converters.bool)
        dry_run = PROP("dry_run", Checkers.null, Converters.bool)
        delay_seconds = PROP("delay_seconds", Checkers.int_positive, Converters.int)

        def __init__(self):
            super().__init__()
            self.enabled = None
            self.dry_run = None
            self.delay_seconds = None

    class Encryption(IC):
        enabled = PROP("enabled", Checkers.null, Converters.bool)

        def __init__(self):
            super().__init__()
            self.enabled = None

    # Class-level keyfile path; injected via set_keyfile_path() before any
    # from_file / to_file call when encryption may be enabled. Pass None to reset
    # (test isolation). See RESEARCH §9.3 and §A2.
    _keyfile_path: Optional[str] = None

    def __init__(self):
        self.general = Config.General()
        self.lftp = Config.Lftp()
        self.controller = Config.Controller()
        self.web = Config.Web()
        self.autoqueue = Config.AutoQueue()
        self.sonarr = Config.Sonarr()
        self.radarr = Config.Radarr()
        self.autodelete = Config.AutoDelete()
        self.encryption = Config.Encryption()
        # List of "Section.field" strings populated during from_str when a value
        # looks like ciphertext but fails to decrypt. Read by plan 03's startup
        # hook to emit per-field warnings (T-81-02-03, T-81-02-04).
        self._decrypt_errors: list[str] = []

    @classmethod
    def set_keyfile_path(cls, path: Optional[str]) -> None:
        """
        Inject the keyfile path before any from_file/to_file call when encryption
        may be enabled. Pass None to reset (test isolation).
        """
        cls._keyfile_path = path

    @staticmethod
    def _check_section(dct: OuterConfigType, name: str) -> InnerConfigType:
        if name not in dct:
            raise ConfigError("Missing config section: {}".format(name))
        val = dct[name]
        del dct[name]
        return val

    @staticmethod
    def _check_empty_outer_dict(dct: OuterConfigType):
        extra_keys = dct.keys()
        if extra_keys:
            raise ConfigError("Unknown section: {}".format(next(iter(extra_keys))))

    @classmethod
    @overrides(Persist)
    def from_str(cls: Type["Config"], content: str) -> "Config":
        config_parser = configparser.ConfigParser()
        try:
            config_parser.read_string(content)
        except (
                configparser.MissingSectionHeaderError,
                configparser.ParsingError
        ) as e:
            raise PersistError("Error parsing Config - {}: {}".format(
                type(e).__name__, str(e))
            )
        config_dict = {}
        for section in config_parser.sections():
            config_dict[section] = {}
            for option in config_parser.options(section):
                config_dict[section][option] = config_parser.get(section, option)

        # ── Decrypt hook (SEC-02 criterion #2) ────────────────────────────────
        # Resolve encryption flag BEFORE from_dict so plaintext values reach the
        # PROP/Checker/Converter layer. The [Encryption] section itself is never
        # in _SECRET_FIELD_PATHS (T-81-02-07).
        _decrypt_errors_local: list[str] = []
        try:
            encryption_enabled = bool(
                _strtobool(
                    config_dict.get("Encryption", {}).get("enabled", "False")
                )
            )
        except ValueError:
            encryption_enabled = False
        if encryption_enabled and cls._keyfile_path is not None:
            # Pitfall 8.4 guard: if the keyfile is missing AND any of the 5
            # fields are already ciphertext-shaped, refuse to create a new key
            # (a new key would orphan the existing ciphertext and cause data
            # loss). Only call load_or_create_key when the keyfile exists OR
            # all 5 fields are plaintext (first-enable case).
            keyfile_exists = os.path.isfile(cls._keyfile_path)
            has_existing_ciphertext = any(
                is_ciphertext(config_dict.get(ini_section, {}).get(field_name, ""))
                for (_, field_name, ini_section) in _SECRET_FIELD_PATHS
            )
            if not keyfile_exists and has_existing_ciphertext:
                # Cannot decrypt — keyfile is gone and values are already
                # ciphertext. Record errors for plan 03's startup warning hook.
                for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:
                    value = config_dict.get(ini_section, {}).get(field_name, "")
                    if is_ciphertext(value):
                        _decrypt_errors_local.append("{}.{}".format(ini_section, field_name))
            else:
                key = load_or_create_key(cls._keyfile_path)
                for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:
                    if ini_section in config_dict and field_name in config_dict[ini_section]:
                        value = config_dict[ini_section][field_name]
                        if is_ciphertext(value):
                            try:
                                config_dict[ini_section][field_name] = decrypt_field(key, value)
                            except DecryptionError:
                                # Leave value as-is; record for startup warning.
                                _decrypt_errors_local.append(
                                    "{}.{}".format(ini_section, field_name)
                                )
                        # Else: plaintext fallback — value stays plaintext in
                        # memory; re-encryption happens on next to_str call if
                        # encryption stays enabled (plan 03's startup hook).
        # ──────────────────────────────────────────────────────────────────────

        config = Config.from_dict(config_dict)
        config._decrypt_errors.extend(_decrypt_errors_local)
        return config

    @overrides(Persist)
    def to_str(self) -> str:
        config_parser = configparser.ConfigParser()
        config_dict = self.as_dict()

        # ── Encrypt hook (SEC-02 criterion #1b, T-81-02-01, T-81-02-05) ──────
        # Walk the 5 secret field paths and encrypt any non-empty, non-ciphertext
        # value when encryption is enabled. Already-ciphertext values are left
        # untouched (idempotent). Empty strings remain empty — never encrypted.
        # The [Encryption] section itself is not in _SECRET_FIELD_PATHS (T-81-02-07).
        if self.encryption.enabled:
            if Config._keyfile_path is None:
                raise ConfigError(
                    "Encryption enabled but no keyfile path set. "
                    "Call Config.set_keyfile_path() before saving."
                )
            fernet_key = load_or_create_key(Config._keyfile_path)
            for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:
                if ini_section in config_dict and field_name in config_dict[ini_section]:
                    value = config_dict[ini_section][field_name]
                    # Encrypt only non-empty plaintext values (research §6.3).
                    if value and not is_ciphertext(value):
                        config_dict[ini_section][field_name] = encrypt_field(fernet_key, str(value))
        # ──────────────────────────────────────────────────────────────────────

        for section in config_dict:
            config_parser.add_section(section)
            section_dict = config_dict[section]
            for key in section_dict:
                config_parser.set(section, key, str(section_dict[key]))
        str_io = StringIO()
        config_parser.write(str_io)
        return str_io.getvalue()

    @staticmethod
    def from_dict(config_dict: OuterConfigType) -> "Config":
        config_dict = dict(config_dict)  # copy that we can modify
        config = Config()

        general_dict = Config._check_section(config_dict, "General")
        # Backward compatibility: webhook_secret added in v3.1 — default to empty string
        if "webhook_secret" not in general_dict:
            general_dict["webhook_secret"] = ""
        # Backward compatibility: api_token added in v3.2 — default to empty string
        if "api_token" not in general_dict:
            general_dict["api_token"] = ""
        if "allowed_hostname" not in general_dict:
            general_dict["allowed_hostname"] = ""
        config.general = Config.General.from_dict(general_dict)
        config.lftp = Config.Lftp.from_dict(Config._check_section(config_dict, "Lftp"))
        config.controller = Config.Controller.from_dict(Config._check_section(config_dict, "Controller"))
        config.web = Config.Web.from_dict(Config._check_section(config_dict, "Web"))
        config.autoqueue = Config.AutoQueue.from_dict(Config._check_section(config_dict, "AutoQueue"))

        # Sonarr section is optional for backward compatibility with older config files
        if "Sonarr" in config_dict:
            config.sonarr = Config.Sonarr.from_dict(Config._check_section(config_dict, "Sonarr"))
        else:
            # Default values for existing installs missing [Sonarr] section
            config.sonarr.enabled = False
            config.sonarr.sonarr_url = ""
            config.sonarr.sonarr_api_key = ""

        # Radarr section is optional for backward compatibility with older config files
        if "Radarr" in config_dict:
            config.radarr = Config.Radarr.from_dict(Config._check_section(config_dict, "Radarr"))
        else:
            # Default values for existing installs missing [Radarr] section
            config.radarr.enabled = False
            config.radarr.radarr_url = ""
            config.radarr.radarr_api_key = ""

        # AutoDelete section is optional for backward compatibility
        if "AutoDelete" in config_dict:
            config.autodelete = Config.AutoDelete.from_dict(
                Config._check_section(config_dict, "AutoDelete")
            )
        else:
            # Default values for existing installs missing [AutoDelete] section
            config.autodelete.enabled = False
            config.autodelete.dry_run = False
            config.autodelete.delay_seconds = 60

        # Encryption section is optional for backward compatibility (SEC-02 criterion #3)
        if "Encryption" in config_dict:
            config.encryption = Config.Encryption.from_dict(
                Config._check_section(config_dict, "Encryption")
            )
        else:
            # Default values for existing installs missing [Encryption] section
            config.encryption.enabled = False

        Config._check_empty_outer_dict(config_dict)
        return config

    def as_dict(self) -> OuterConfigType:
        # We convert all values back to strings
        # Use an ordered dict to main section order
        config_dict = collections.OrderedDict()
        config_dict["General"] = self.general.as_dict()
        config_dict["Lftp"] = self.lftp.as_dict()
        config_dict["Controller"] = self.controller.as_dict()
        config_dict["Web"] = self.web.as_dict()
        config_dict["AutoQueue"] = self.autoqueue.as_dict()
        config_dict["Sonarr"] = self.sonarr.as_dict()
        config_dict["Radarr"] = self.radarr.as_dict()
        config_dict["AutoDelete"] = self.autodelete.as_dict()
        config_dict["Encryption"] = self.encryption.as_dict()
        return config_dict

    def has_section(self, name: str) -> bool:
        """
        Returns true if the given section exists, false otherwise
        """
        try:
            return isinstance(getattr(self, name), InnerConfig)
        except AttributeError:
            return False
