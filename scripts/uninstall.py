"""
Remove the theme and plugin from an IDA user directory.

    uv run scripts/uninstall.py            # %APPDATA%\\Hex-Rays\\IDA Pro (or ~/.idapro)
    uv run scripts/uninstall.py <dir>      # another IDA user directory

Removes plugins/catppuccin.py and themes/catppuccin/. Nothing else is
touched.
"""

import shutil
import sys

from common.errors import run
from common.paths import INSTALL_ITEMS, ida_user_dir


def main():
    target = ida_user_dir(sys.argv, "uninstall")
    removed = 0
    for item in INSTALL_ITEMS:
        path = target / item
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            continue
        removed += 1
        print("removed %s" % path)
    if not removed:
        print("nothing installed in %s" % target)


if __name__ == "__main__":
    run(main)
