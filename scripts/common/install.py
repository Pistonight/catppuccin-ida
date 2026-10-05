"""What gets installed into an IDA user directory, and where that is."""

import os
import sys

from common.errors import ScriptError
from common.paths import DIST

# Installed items, relative to both dist/ and the IDA user directory
ITEMS = [
    os.path.join("plugins", "catppuccin.py"),
    os.path.join("themes", "catppuccin"),
]

# Files from older versions of this project that should not linger
LEGACY = [
    os.path.join("plugins", "catppuccin_hexrays.py"),
    os.path.join("plugins", "catppuccin_ui.py"),
]


def default_user_dir():
    """IDA's per-user directory: %APPDATA%\\Hex-Rays\\IDA Pro, or ~/.idapro."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise ScriptError("APPDATA is not set; pass the IDA user directory explicitly")
        return os.path.join(appdata, "Hex-Rays", "IDA Pro")
    return os.path.join(os.path.expanduser("~"), ".idapro")


def target_dir(argv, script):
    """The IDA user directory from the command line, or the default one."""
    if len(argv) > 2:
        raise ScriptError("usage: ./x %s [ida user dir]" % script)
    path = os.path.abspath(argv[1]) if len(argv) == 2 else default_user_dir()
    if not os.path.isdir(path):
        raise ScriptError("%s does not exist (is IDA installed? or pass the directory)" % path)
    return path


def dist_item(item):
    return os.path.join(DIST, item)
