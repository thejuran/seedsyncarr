"""Value-free fixture sanitizer for raw Sonarr API / webhook captures.

Usage (NAS host python3, or inside the app image via --entrypoint python3):
    python3 120-sanitize_fixtures.py <raw_file> <mapping_json> <out_file>

<mapping_json> is a local, UNCOMMITTED, 0600 JSON object mapping each
sensitive substring to its placeholder, e.g.
    {"/home/<seedbox-user>/": "/home/user/", "<Tracker> (Prowlarr)": "Indexer (Prowlarr)"}
Every key must be a non-empty single-line string and every value a
single-line string; anything else is rejected.

Processing, in order:
  1. Decode the raw bytes as UTF-8 and apply str.replace for each mapping key,
     LONGEST KEY FIRST, so a more specific prefix (".../v5test-incomplete")
     is replaced before a shorter one it contains (".../v5test").
  2. json.loads the substituted text (fails closed if it is no longer JSON).
  3. Neutralise identity fields by KEY anywhere in the document, regardless of
     their value: instanceName, applicationUrl, startupPath, appData, osName,
     osVersion, packageAuthor, urlBase. startTime / buildTime are kept (ISO
     timestamps, not personal). Every images[].url / images[].remoteUrl that
     carries a host is rewritten to https://images.example.invalid, keeping
     the path and query.
  4. Render JSON (2-space indent, non-ASCII kept literal, trailing newline) and count
     mapping keys still present in that text (RESIDUAL).
  5. Only when RESIDUAL is 0, write the rendered text to <out_file>, created
     with O_EXCL and mode 0600 (an existing file is never overwritten).

Path basenames are preserved: nothing after the final "/" of outputPath,
sourcePath, path or any other value is altered except through an explicit
mapping key. Gate and webhook matching depend on exact release and file
basenames, so there is no pattern-based path rewriting and no hand editing.

STDERR carries only counts:
    REPLACED n=<keys that matched at least once> RESIDUAL=<keys still present>
Exit 0 when RESIDUAL is 0, exit 2 (and no output file) otherwise. On any
exception it prints only `ERROR <ExceptionClassName>` and exits 3; exception
messages are never printed. Mapping keys, placeholders and body content are
never printed.
"""
import json
import os
import sys
from urllib.parse import urlsplit, urlunsplit

PLACEHOLDER_IMAGE_SCHEME = "https"
PLACEHOLDER_IMAGE_HOST = "images.example.invalid"

# Fields whose value is replaced outright, whatever it contains.
NEUTRALISED_FIELDS = {
    "instanceName": "Sonarr",
    "applicationUrl": "",
    "startupPath": "/app/sonarr/bin",
    "appData": "/config",
    "osName": "Linux",
    "osVersion": "0.0",
    "packageAuthor": "example",
    "urlBase": "",
}

IMAGE_URL_FIELDS = ("url", "remoteUrl")


def load_mapping(path):
    with open(path, "rb") as f:
        mapping = json.loads(f.read().decode("utf-8"))
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("unexpected mapping shape")
    for key, value in mapping.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("unexpected mapping shape")
        if key == "" or "\n" in key or "\r" in key:
            raise ValueError("unexpected mapping shape")
        if "\n" in value or "\r" in value:
            raise ValueError("unexpected mapping shape")
    return mapping


def rewrite_image_url(value):
    if not isinstance(value, str):
        return value
    parts = urlsplit(value)
    if not parts.netloc:
        # Relative (e.g. /MediaCover/...) - no host to neutralise.
        return value
    return urlunsplit((PLACEHOLDER_IMAGE_SCHEME, PLACEHOLDER_IMAGE_HOST, parts.path, parts.query, ""))


def neutralise(node):
    if isinstance(node, dict):
        for key in list(node.keys()):
            if key in NEUTRALISED_FIELDS:
                node[key] = NEUTRALISED_FIELDS[key]
            elif key == "images" and isinstance(node[key], list):
                for image in node[key]:
                    if isinstance(image, dict):
                        for field in IMAGE_URL_FIELDS:
                            if field in image:
                                image[field] = rewrite_image_url(image[field])
                        neutralise(image)
            else:
                neutralise(node[key])
    elif isinstance(node, list):
        for item in node:
            neutralise(item)


def write_exclusive_0600(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> int:
    if len(sys.argv) != 4:
        raise ValueError("usage")
    raw_path, mapping_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    mapping = load_mapping(mapping_path)
    with open(raw_path, "rb") as f:
        text = f.read().decode("utf-8")

    replaced = 0
    for key in sorted(mapping.keys(), key=len, reverse=True):
        if key in text:
            replaced += 1
            text = text.replace(key, mapping[key])

    obj = json.loads(text)
    neutralise(obj)
    out_text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"

    residual = sum(1 for key in mapping if key in out_text)
    sys.stderr.write("REPLACED n={} RESIDUAL={}\n".format(replaced, residual))
    if residual != 0:
        return 2

    write_exclusive_0600(out_path, out_text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - class name only, never the message
        sys.stderr.write("ERROR {}\n".format(type(exc).__name__))
        sys.exit(3)
