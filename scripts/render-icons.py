"""
Render every SVG under a folder into one HTML page, for checking icons.

    uv run scripts/render-icons.py <folder>    -> dist/test_icons.html

SVGs are found recursively and shown at 16px (toolbar size) and 64px, on the
palette's base colour from the config file, labelled with their path relative
to <folder>.
"""

import sys
from pathlib import Path

from common.errors import ScriptError, run
from common.paths import RENDER_ICONS_PAGE, file_url
from common.render import find_svgs, write_page


def main():
    if len(sys.argv) != 2:
        raise ScriptError("usage: ./x render-icons <folder>")
    folder = Path(sys.argv[1]).resolve()
    if not folder.is_dir():
        raise ScriptError("%s is not a folder" % folder)
    svgs = find_svgs(folder)
    if not svgs:
        raise ScriptError("no SVGs under %s" % folder)
    write_page(svgs, folder.name or str(folder), RENDER_ICONS_PAGE)
    print("rendered %d SVGs to %s" % (len(svgs), file_url(RENDER_ICONS_PAGE)))


if __name__ == "__main__":
    run(main)
