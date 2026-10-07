"""
Install the built theme and plugin into an IDA user directory.

    uv run scripts/install.py              # %APPDATA%\\Hex-Rays\\IDA Pro (or ~/.idapro)
    uv run scripts/install.py <dir>        # another IDA user directory

Copies dist/catppuccin-ida/plugins/catppuccin.py and themes/catppuccin/ (replacing
any previous install). Build first with ./x build.
"""

import shutil
import sys

from common.errors import ScriptError, run
from common.paths import DIST_IDA, INSTALL_ITEMS, ida_user_dir


def main():
    missing = [str(DIST_IDA / i) for i in INSTALL_ITEMS if not (DIST_IDA / i).exists()]
    if missing:
        raise ScriptError("not built yet: %s (run ./x build)" % ", ".join(missing))
    target = ida_user_dir(sys.argv, "install")

    for item in INSTALL_ITEMS:
        src, dst = DIST_IDA / item, target / item
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print("installed %s" % dst)


if __name__ == "__main__":
    run(main)
