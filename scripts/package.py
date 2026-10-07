"""
Zip the IDA build for release.

    uv run scripts/package.py    -> dist/catppuccin-ida.zip

The zip holds the contents of dist/catppuccin-ida/ (plugins/, themes/) at its
root, so it unpacks straight into an IDA user directory. Build first with
./x build.
"""

import sys
import zipfile

from common.errors import ScriptError, run
from common.paths import DIST_IDA, DIST_IDA_ZIP, INSTALL_ITEMS, rel


def main():
    if len(sys.argv) > 1:
        raise ScriptError("usage: ./x package")
    missing = [rel(DIST_IDA / i) for i in INSTALL_ITEMS if not (DIST_IDA / i).exists()]
    if missing:
        raise ScriptError("not built yet: %s (run ./x build)" % ", ".join(missing))

    files = sorted(p for p in DIST_IDA.rglob("*") if p.is_file())
    with zipfile.ZipFile(DIST_IDA_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(DIST_IDA).as_posix())
    print("packaged %d files from %s into %s" % (len(files), rel(DIST_IDA), rel(DIST_IDA_ZIP)))


if __name__ == "__main__":
    run(main)
