"""HTML preview pages for SVG icons."""

import base64
import html
import mimetypes

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
    found = [(path.relative_to(folder).as_posix(), path) for path in folder.rglob("*")
             if path.suffix.lower() == ".svg" and path.is_file()]
    return sorted(found, key=lambda item: item[0].lower())


def write_page(svgs, title, out):
    """Write an HTML page showing `svgs` ([(label, path)]) at 16px and 64px,
    on the palette's base colour. Each SVG is embedded as a data: URI image,
    so styles inside one SVG cannot leak into another. Other images (.png)
    work too."""
    palette = colors(load_config())
    tiles = []
    for label, path in svgs:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        mime = mimetypes.guess_type(path.name)[0] or "image/svg+xml"
        tiles.append(TILE.format(uri="data:%s;base64,%s" % (mime, data), name=html.escape(label)))
    page = PAGE.format(title=html.escape(title), bg=palette["base"], fg=palette["text"],
                       count=len(svgs), tiles="\n".join(tiles))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
