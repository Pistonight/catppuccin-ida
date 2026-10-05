"""
Remove the theme and plugin from an IDA user directory.

    uv run scripts/uninstall.py            # %APPDATA%\\Hex-Rays\\IDA Pro (or ~/.idapro)
    uv run scripts/uninstall.py <dir>      # another IDA user directory

Removes plugins/catppuccin.py and themes/catppuccin/, plus plugin files left
by older versions of this project. Nothing else is touched.
"""

import os
import shutil
import sys

from common.errors import run
from common.install import ITEMS, LEGACY, target_dir


def main():
    target = target_dir(sys.argv, "uninstall")
    removed = 0
    for item in ITEMS + LEGACY:
        path = os.path.join(target, item)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
        else:
            continue
        removed += 1
        print("removed %s" % path)
    if not removed:
        print("nothing installed in %s" % target)


if __name__ == "__main__":
    run(main, "uninstall")
