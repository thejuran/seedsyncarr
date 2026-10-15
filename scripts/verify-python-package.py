#!/usr/bin/env python3
"""Verify member paths of the built SeedSyncarr wheel and sdist.

Usage: verify-python-package.py <dist-dir>

Fails (exit 1) when any archive member starts with "./", contains a ".."
path component or is absolute, or when the wheel ships top-level members
that belong to the source tree rather than the application (tests, docs,
lockfile, project metadata files).
"""

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

FORBIDDEN_WHEEL_TOP_LEVEL = {"tests", "docs", "poetry.lock", "pyproject.toml", "PKG-INFO"}


def path_problem(name):
    """Return a reason string if a member name is unsafe, else None."""
    if name.startswith("./"):
        return "dot-slash-prefix"
    if name.startswith("/") or name.startswith("\\") or (len(name) > 1 and name[1] == ":"):
        return "absolute-path"
    if ".." in PurePosixPath(name.replace("\\", "/")).parts:
        return "parent-traversal"
    return None


def find_single(dist_dir, pattern, failures):
    matches = sorted(dist_dir.glob(pattern))
    if len(matches) != 1:
        failures.append(f"FAIL {dist_dir} expected-exactly-one {pattern} found={len(matches)}")
        return None
    return matches[0]


def check_members(archive, names, failures, forbidden_top_level=None):
    archive_failures = 0
    for name in names:
        reason = path_problem(name)
        if reason is not None:
            failures.append(f"FAIL {archive.name} {reason} {name}")
            archive_failures += 1
            continue
        if forbidden_top_level is not None:
            top = name.split("/", 1)[0]
            if top in forbidden_top_level:
                failures.append(f"FAIL {archive.name} forbidden-member {name}")
                archive_failures += 1
    if archive_failures == 0:
        print(f"PASS {archive.name} members={len(names)}")
    return len(names)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist_dir", help="directory containing exactly one .whl and one .tar.gz")
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir)
    failures = []
    total = 0

    if not dist_dir.is_dir():
        print(f"FAIL {dist_dir} not-a-directory")
        return 1

    wheel = find_single(dist_dir, "*.whl", failures)
    sdist = find_single(dist_dir, "*.tar.gz", failures)

    if wheel is not None:
        with zipfile.ZipFile(wheel) as zf:
            names = [info.filename for info in zf.infolist()]
        total += check_members(wheel, names, failures, FORBIDDEN_WHEEL_TOP_LEVEL)
        files = [n for n in names if not n.endswith("/")]
        print(f"INFO {wheel.name} files={len(files)}")

    if sdist is not None:
        with tarfile.open(sdist, "r:gz") as tf:
            names = tf.getnames()
        total += check_members(sdist, names, failures)

    print(f"TOTAL members={total}")

    if failures:
        for line in failures:
            print(line)
        return 1

    print("PACKAGE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
