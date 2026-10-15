"""Read-only loader check for SeedSyncarr state files.

Usage (stdin script inside the app image, /c mounted read-only):
    python3 - <settings> <controller> <autoqueue> < parse_check.py

Loads each file with the application's own from_str loader and prints only
PASS/FAIL, the loader or exception class name, and the AutoDelete boolean.
Never prints file contents or exception messages (ConfigError messages embed
config values). Never writes, chmods, or creates a key file.
"""
import os
import sys

sys.path.insert(0, "/app/python")

ok = True
try:
    from common import Config
    from controller.controller_persist import ControllerPersist
    from controller.auto_queue import AutoQueuePersist
except Exception as e:  # noqa: BLE001 - class name only
    print("FAIL import {}".format(type(e).__name__))
    print("PARSE_FAIL")
    sys.exit(1)

if len(sys.argv) != 4:
    print("FAIL usage ArgCount")
    print("PARSE_FAIL")
    sys.exit(1)

pairs = [
    (sys.argv[1], Config),
    (sys.argv[2], ControllerPersist),
    (sys.argv[3], AutoQueuePersist),
]

for name, loader in pairs:
    base = os.path.basename(name)
    try:
        path = os.path.join("/c", name)
        with open(path, "rb") as f:
            raw = f.read()
        if len(raw) == 0:
            print("FAIL {} EmptyFile".format(base))
            ok = False
            continue
        text = raw.decode("utf-8")
        obj = loader.from_str(text)
        print("PASS {} loader={}".format(base, loader.__name__))
        if loader is Config:
            print("AutoDelete.enabled={}".format(bool(obj.autodelete.enabled)))
    except Exception as e:  # noqa: BLE001 - class name only, never str(e)
        print("FAIL {} {}".format(base, type(e).__name__))
        ok = False

if ok:
    print("PARSE_OK")
    sys.exit(0)
print("PARSE_FAIL")
sys.exit(1)
