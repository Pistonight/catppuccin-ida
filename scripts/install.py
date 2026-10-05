"""
Install the built theme and plugin into an IDA user directory.

    uv run scripts/install.py              # %APPDATA%\\Hex-Rays\\IDA Pro (or ~/.idapro)
    uv run scripts/install.py <dir>        # another IDA user directory

Copies dist/plugins/catppuccin.py and dist/themes/catppuccin/ (replacing
any previous install). Build first with scripts/build.py and
scripts/build-css.py.
"""

import os
import shutil
import sys

from common.errors import ScriptError, run
from common.install import ITEMS, LEGACY, dist_item, target_dir


def main():
    missing = [dist_item(i) for i in ITEMS if not os.path.exists(dist_item(i))]
    if missing:
        raise ScriptError("not built yet: %s (run ./x build and ./x build-css)" % ", ".join(missing))
    target = target_dir(sys.argv, "install")

    for item in ITEMS:
        src, dst = dist_item(item), os.path.join(target, item)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print("installed %s" % dst)

    for item in LEGACY:
        path = os.path.join(target, item)
        if os.path.exists(path):
            print("warning: %s is from an older version and will also load; "
                  "remove it (./x uninstall removes it too)" % path)


if __name__ == "__main__":
    run(main, "install")
