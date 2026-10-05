"""
Research probe, run inside IDA (File > Script file... / Alt+F7).

Finds which IDA colour tags the Local Types view uses for each part of a type
declaration (struct keyword, type name, base class, member types, member
names, offsets, comments). For 30 seconds after it starts, the line under the
cursor in the focused view is logged with its tags spelled out, once per
distinct line: click into Local Types and move the cursor over a struct
header (one with a base class), its members, an enum and a typedef.

Writes .cache/type_listing_probe.txt.
"""

import os

import ida_kernwin
import ida_lines
from PySide6.QtCore import QTimer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".cache", "type_listing_probe.txt")
DURATION_MS = 30000
POLL_MS = 200

# COLOR_* value -> name, to spell the tags out
TAG_NAMES = {getattr(ida_lines, n): n[len("COLOR_"):] for n in dir(ida_lines)
             if n.startswith("COLOR_") and isinstance(getattr(ida_lines, n), int)
             and len(n) > len("COLOR_") and getattr(ida_lines, n) < 0x40}


def spell(line):
    """The line with each tag as <NAME>...</NAME>; addresses as <ADDR>."""
    out = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == ida_lines.SCOLOR_ON and i + 1 < n:
            if line[i + 1] == ida_lines.SCOLOR_ADDR:
                out.append("<ADDR>")
                i += 2 + ida_lines.COLOR_ADDR_SIZE
                continue
            out.append("<%s>" % TAG_NAMES.get(ord(line[i + 1]), hex(ord(line[i + 1]))))
            i += 2
        elif c == ida_lines.SCOLOR_OFF and i + 1 < n:
            out.append("</%s>" % TAG_NAMES.get(ord(line[i + 1]), hex(ord(line[i + 1]))))
            i += 2
        elif c in (ida_lines.SCOLOR_ESC, ida_lines.SCOLOR_INV):
            i += 2 if c == ida_lines.SCOLOR_ESC else 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


lines = []
seen = set()
elapsed = 0
timer = QTimer()


def poll():
    global elapsed
    elapsed += POLL_MS
    try:
        viewer = ida_kernwin.get_current_viewer()
        if viewer is not None:
            line = ida_kernwin.get_custom_viewer_curline(viewer, False)
            if line and line not in seen:
                seen.add(line)
                lines.append("[%s] %s" % (ida_kernwin.get_widget_title(viewer), spell(line)))
    except Exception as e:
        lines.append("error: %r" % e)
    if elapsed >= DURATION_MS:
        timer.stop()
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("type listing probe written to", OUT)


timer.timeout.connect(poll)
timer.start(POLL_MS)
print("type listing probe: move the cursor through Local Types for %ds" % (DURATION_MS // 1000))
