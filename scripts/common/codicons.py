"""Reading codicons (@vscode/codicons, installed with pnpm)."""

import re

from common.errors import ScriptError
from common.paths import rel

# Codicon badges (e.g. the plus on new-file) sit in this circle, and the rest of
# the icon keeps clear of BADGE_GAP_R around it.
BADGE_CX = 11.5
BADGE_CY = 11.5
BADGE_R = 4.5
BADGE_GAP_R = 5.5

SVG_RE = re.compile(r"<svg\b([^>]*)>(.*)</svg>", re.S)
VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')
SIZE = 16


def _parse(path):
    """(viewBox numbers, markup inside <svg>) of an icon file."""
    text = path.read_text(encoding="utf-8")
    m = SVG_RE.search(text)
    vb = VIEWBOX_RE.search(m.group(1)) if m else None
    if not m or not vb:
        raise ScriptError("%s: expected an <svg> element with a viewBox" % rel(path))
    return [float(v) for v in vb.group(1).replace(",", " ").split()], m.group(2).strip()


def svg_body(path):
    """The markup inside the <svg> element of a 16x16 icon."""
    view_box, body = _parse(path)
    if view_box != [0, 0, SIZE, SIZE]:
        raise ScriptError("%s: expected a 16x16 viewBox" % rel(path))
    return body


def icon_body(path):
    """The markup of an icon, scaled to fit and centred in a 16x16 box (a few
    codicons are drawn on a 24-unit grid)."""
    (x, y, w, h), body = _parse(path)
    if [x, y, w, h] == [0, 0, SIZE, SIZE]:
        return body
    scale = SIZE / max(w, h)
    dx, dy = (SIZE - w * scale) / 2, (SIZE - h * scale) / 2
    return '<g transform="translate(%g %g) scale(%g) translate(%g %g)">%s</g>' % (
        dx, dy, scale, -x, -y, body)
