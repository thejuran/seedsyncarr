"""Generate good/bad/mixed scratch fixtures for parse_check.py using the image's own code."""
import os
import sys

sys.path.insert(0, "/app/python")

from seedsyncarr import Seedsyncarr  # noqa: E402
from controller.controller_persist import ControllerPersist  # noqa: E402
from controller.auto_queue import AutoQueuePersist  # noqa: E402

good_settings = Seedsyncarr._create_default_config().to_str()
good_controller = ControllerPersist().to_str()
good_autoqueue = AutoQueuePersist().to_str()

bad_settings = good_settings[:good_settings.index("\n[", 1) + 1]
bad_controller = "{}"
bad_autoqueue = '{"not_patterns": []}'

sets = {
    "good": (good_settings, good_controller, good_autoqueue),
    "bad": (bad_settings, bad_controller, bad_autoqueue),
    "mixed": (good_settings, good_controller, bad_autoqueue),
}
for d, (s, c, a) in sets.items():
    os.makedirs(os.path.join("/c", d), exist_ok=True)
    for name, text in (("settings.cfg", s), ("controller.persist", c), ("autoqueue.persist", a)):
        p = os.path.join("/c", d, name)
        with open(p, "w") as f:
            f.write(text)
        print("{} {}".format(p, os.path.getsize(p)))
