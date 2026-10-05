"""The CSS file list in src/styles.txt.

One CSS path per line, relative to src/; blank lines and lines starting with
# are ignored.
"""

import os

from common.errors import ScriptError
from common.paths import SRC, rel

STYLES = os.path.join(SRC, "styles.txt")


def style_list():
    """CSS paths from src/styles.txt, relative to src/, in order."""
    if not os.path.isfile(STYLES):
        raise ScriptError("missing %s" % rel(STYLES))
    paths = []
    with open(STYLES, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            path = os.path.normpath(entry).replace(os.sep, "/")
            where = "%s:%d" % (rel(STYLES), lineno)
            if path.startswith("../") or os.path.isabs(path):
                raise ScriptError("%s: %s is outside src/" % (where, entry))
            if path in paths:
                raise ScriptError("%s: %s is listed twice" % (where, entry))
            if not os.path.isfile(os.path.join(SRC, path)):
                raise ScriptError("%s: src/%s does not exist" % (where, path))
            paths.append(path)
    if not paths:
        raise ScriptError("%s lists no CSS files" % rel(STYLES))
    return paths


def style_path(path):
    """Absolute path of a style_list() entry."""
    return os.path.join(SRC, path)
