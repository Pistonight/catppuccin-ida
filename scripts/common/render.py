"""HTML preview pages for SVG icons."""

import base64
import html
import os

from common.config import colors, load_config

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Icons: {title}</title>
<style>
  body {{ background: {bg}; color: {fg}; font: 12px sans-serif; margin: 16px; }}
  h1 {{ font-size: 14px; font-weight: normal; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }}
  .icon {{ display: flex; flex-direction: column; align-items: center; gap: 6px; }}
  .sizes {{ display: flex; align-items: center; gap: 12px; height: 64px; }}
  .name {{ word-break: break-all; text-align: center; opacity: 0.8; }}
</style>
</head>
<body>
<h1>{count} SVGs: {title}</h1>
<div class="grid">
{tiles}
</div>
</body>
</html>
"""

TILE = """<div class="icon">
  <div class="sizes"><img src="{uri}" width="16" height="16"><img src="{uri}" width="64" height="64"></div>
  <div class="name">{name}</div>
</div>"""


def find_svgs(folder):
    """[(path relative to folder with forward slashes, absolute path)], sorted."""
    found = []
    for dirpath, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".svg"):
                path = os.path.join(dirpath, name)
                found.append((os.path.relpath(path, folder).replace(os.sep, "/"), path))
    return sorted(found, key=lambda item: item[0].lower())


def write_page(svgs, title, out):
    """Write an HTML page showing `svgs` ([(label, path)]) at 16px and 64px,
    on the palette's base colour. Each SVG is embedded as a data: URI image,
    so styles inside one SVG cannot leak into another."""
    palette = colors(load_config())
    tiles = []
    for label, path in svgs:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        tiles.append(TILE.format(uri="data:image/svg+xml;base64," + data, name=html.escape(label)))
    page = PAGE.format(title=html.escape(title), bg=palette["base"], fg=palette["text"],
                       count=len(svgs), tiles="\n".join(tiles))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
