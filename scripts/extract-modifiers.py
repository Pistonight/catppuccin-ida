"""
Extract icon modifiers (badges) from codicons into src/icons/.

    uv run scripts/extract-modifiers.py    -> src/icons/modifier-<name>.svg

Some codicons carry a badge in the bottom-right corner, e.g. the plus on
new-file: a filled circle with the glyph knocked out. This keeps only the
shapes inside that badge circle, so the result can be layered onto any other
codicon. The output is 16x16 like the codicons, filled with currentColor;
scripts/build-icons.py colours it.

Run this only when changing the set of modifiers (MODIFIERS below); the
results are committed sources.
"""

import re

from common.codicons import BADGE_CX, BADGE_CY, BADGE_R, svg_body
from common.errors import ScriptError, run
from common.paths import MODIFIERS_DIR, codicon_file, modifier_file, rel

# modifier name -> codicon whose badge it is taken from
MODIFIERS = {
    "add": "new-file",               # +
    "remove": "exclude",             # -
    "delete": "copilot-error",       # x
    "check": "copilot-success",      # check mark
    "warning": "copilot-warning",    # !
    "sync": "copilot-in-progress",   # circular arrows
    "edit": "save-as",               # pencil
    "down": "cloud-download",        # down arrow
    "up": "cloud-upload",            # up arrow
}

# Slack around the badge circle when deciding what belongs to the badge
BADGE_SLACK = 0.2

PATH_RE = re.compile(r"<path\b([^>]*?)\sd=\"([^\"]+)\"([^>]*)/>")
TOKEN_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
ARG_COUNT = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def split_subpaths(d):
    """[(bbox, text)] for each subpath (from one M to the next) of a path."""
    tokens = [(m.group(0), m.start()) for m in TOKEN_RE.finditer(d)]
    found = []           # (points, start offset)
    points, start = [], 0
    x = y = sx = sy = 0.0
    cmd = None
    i = 0
    while i < len(tokens):
        tok, pos = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            if cmd in "Mm" and points:
                found.append((points, start))
                points = []
            if cmd in "Mm":
                start = pos
            if cmd in "Zz":
                x, y = sx, sy
                continue
        if cmd is None:
            raise ScriptError("path data does not start with a command: %r" % d[:40])
        upper, relative = cmd.upper(), cmd.islower()
        values = [float(t) for t, _ in tokens[i:i + ARG_COUNT[upper]]]
        i += ARG_COUNT[upper]
        if upper == "H":
            x = x + values[0] if relative else values[0]
        elif upper == "V":
            y = y + values[0] if relative else values[0]
        elif upper == "A":
            x, y = (x + values[5], y + values[6]) if relative else (values[5], values[6])
        else:
            pairs = list(zip(values[0::2], values[1::2]))
            for px, py in pairs:
                points.append((x + px, y + py) if relative else (px, py))
            x, y = (x + pairs[-1][0], y + pairs[-1][1]) if relative else pairs[-1]
        points.append((x, y))
        if upper == "M":
            sx, sy = x, y
            cmd = "l" if relative else "L"    # further pairs are line-tos
    if points:
        found.append((points, start))

    out = []
    for k, (pts, begin) in enumerate(found):
        end = found[k + 1][1] if k + 1 < len(found) else len(d)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(((min(xs), min(ys), max(xs), max(ys)), d[begin:end].strip()))
    return out


def in_badge(bbox):
    r = BADGE_R + BADGE_SLACK
    x0, y0, x1, y1 = bbox
    return x0 >= BADGE_CX - r and y0 >= BADGE_CY - r and x1 <= BADGE_CX + r and y1 <= BADGE_CY + r


def extract(donor):
    """The badge of a codicon as <path> elements (attributes like fill-rule kept)."""
    body = svg_body(codicon_file(donor))
    paths = []
    for m in PATH_RE.finditer(body):
        attrs = (m.group(1) + m.group(3)).strip()
        kept = [text for bbox, text in split_subpaths(m.group(2)) if in_badge(bbox)]
        if kept:
            paths.append('<path%s d="%s"/>' % ((" " + attrs) if attrs else "", "".join(kept)))
    if not paths:
        raise ScriptError("codicon %r has no badge in the bottom-right corner" % donor)
    return paths


def main():
    MODIFIERS_DIR.mkdir(parents=True, exist_ok=True)
    for name, donor in MODIFIERS.items():
        svg = ('<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" '
               'fill="currentColor">%s</svg>\n' % "".join(extract(donor)))
        path = modifier_file(name)
        path.write_text(svg, encoding="utf-8", newline="\n")
        print("wrote %s (from %s)" % (rel(path), donor))


if __name__ == "__main__":
    run(main)
