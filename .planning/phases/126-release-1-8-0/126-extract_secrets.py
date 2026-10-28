"""Read-only, value-free secret extractor for count-only log checks.

Usage (stdin script inside the app image, config dir mounted read-only at /c):
    python3 - < 119.1-extract_secrets.py > <0600 values file> 2> <fields file>

Reads /c/settings.cfg and, for every field returned by Config.secret_fields(),
writes to STDOUT:
  - the DECODED value (Config.from_str, the application's own reader, which
    also decrypts when [Encryption] enabled = True), and
  - the SERIALIZED on-disk form (RawConfigParser, no interpolation) when it
    differs from the decoded value (e.g. '%' stored as '%%').
Empty values are skipped.

STDERR carries only field NAMES and counts:
    FIELDS <names> N=<set fields> LINES=<value lines written>
On any exception it prints only `ERROR <ExceptionClassName>` to stderr and
exits 3; exception messages are never printed (ConfigError messages can
embed values). Never writes a file and never creates a key file.
"""
import configparser
import os
import sys

sys.path.insert(0, "/app/python")

CONFIG_DIR = "/c"


def main() -> int:
    from common import Config
    from seedsyncarr import Seedsyncarr

    settings_name = getattr(Seedsyncarr, "_Seedsyncarr__FILE_CONFIG")
    key_name = getattr(Seedsyncarr, "_Seedsyncarr__FILE_SECRETS_KEY")

    with open(os.path.join(CONFIG_DIR, settings_name), "rb") as f:
        text = f.read().decode("utf-8")

    Config.set_keyfile_path(os.path.join(CONFIG_DIR, key_name))
    config = Config.from_str(text)

    raw = configparser.RawConfigParser()
    raw.read_string(text)

    names = []
    lines = []
    for (attr, field, section) in Config.secret_fields():
        decoded = getattr(getattr(config, attr), field)
        if decoded is None or str(decoded) == "":
            continue
        decoded = str(decoded)
        names.append("{}.{}".format(section, field))
        lines.append(decoded)
        serialized = raw.get(section, field) if raw.has_option(section, field) else ""
        if serialized and serialized != decoded:
            lines.append(serialized)

    for line in lines:
        if "\n" in line or line == "":
            raise ValueError("unexpected value shape")
    out = "".join(line + "\n" for line in lines)
    sys.stdout.write(out)
    sys.stdout.flush()
    sys.stderr.write("FIELDS {} N={} LINES={}\n".format(" ".join(names), len(names), len(lines)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - class name only, never the message
        sys.stderr.write("ERROR {}\n".format(type(exc).__name__))
        sys.exit(3)
