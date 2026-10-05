"""
Render every SVG under a folder into one HTML page, for checking icons.

    uv run scripts/render-icons.py <folder>    -> dist/test_icons.html

SVGs are found recursively and shown at 16px (toolbar size) and 64px, on the
palette's base colour from the config file, labelled with their path relative
to <folder>.
"""

import os
import sys

from common.errors import ScriptError, run
from common.paths import DIST, file_url
from common.render import find_svgs, write_page

OUT = os.path.join(DIST, "test_icons.html")


def main():
    if len(sys.argv) != 2:
        raise ScriptError("usage: ./x render-icons <folder>")
    folder = os.path.abspath(sys.argv[1])
    if not os.path.isdir(folder):
        raise ScriptError("%s is not a folder" % folder)
    svgs = find_svgs(folder)
    if not svgs:
        raise ScriptError("no SVGs under %s" % folder)
    write_page(svgs, os.path.basename(folder) or folder, OUT)
    print("rendered %d SVGs to %s" % (len(svgs), file_url(OUT)))


if __name__ == "__main__":
    run(main, "render-icons")
