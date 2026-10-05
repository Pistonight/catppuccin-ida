"""The list of IDA's toolbar/menu icons, src/icons.txt (from scripts/dump-icons.py)."""

import os

from common.errors import ScriptError
from common.paths import SRC, rel

ICON_LIST = os.path.join(SRC, "icons.txt")


def ida_icon_names():
    """IDA icon names (file names without .svg), in file order."""
    if not os.path.isfile(ICON_LIST):
        raise ScriptError("missing %s (run ./x dump-icons)" % rel(ICON_LIST))
    names = []
    with open(ICON_LIST, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            if not entry.endswith(".svg"):
                raise ScriptError("%s:%d: expected an .svg file name, got %r"
                                  % (rel(ICON_LIST), lineno, entry))
            names.append(entry[:-len(".svg")])
    if not names:
        raise ScriptError("%s lists no icons" % rel(ICON_LIST))
    return names
