"""
Research probe, run inside IDA (File > Script file... / Alt+F7) with the
catppuccin theme active.

Finds what IDA's hint popups are (the decompiler hover hint, the Local Types
hint, ...). For 20 seconds after it starts, every new visible top-level
widget is logged with its class chain, window flags, style sheet properties
and its whole child tree, so hover over a few things that show hints
meanwhile: a variable or type in pseudocode, an item in Local Types, a name
in the disassembly.

Writes .cache/hints_probe.txt (also when stopped early by IDA closing).
"""

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFrame, QLabel
from shiboken6 import getCppPointer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".cache", "hints_probe.txt")
DURATION_MS = 20000
POLL_MS = 100
PROPERTIES = ("hints", "os-dark-theme", "debugging")

lines = []


def log(*args):
    lines.append(" ".join(str(a) for a in args))


def text(value):
    """PySide returns str at runtime, but its stubs say bytes for some names."""
    return value if isinstance(value, str) else bytes(value).decode()


def class_chain(obj):
    names = []
    meta = obj.metaObject()
    while meta is not None:
        names.append(text(meta.className()))
        meta = meta.superClass()
    return " < ".join(names)


def describe(w, depth):
    props = {p: w.property(p) for p in PROPERTIES if w.property(p) is not None}
    extra = ""
    if isinstance(w, QFrame):
        extra += " | frameShape %s lineWidth %d" % (w.frameShape().name, w.lineWidth())
    if isinstance(w, QLabel):
        extra += " | label %r" % w.text()[:80]
    palette = w.palette()
    log("%s%s | objectName %r | %dx%d | visible %s | props %s | styleSheet %r | autoFill %s | "
        "window %s base %s%s"
        % ("    " * depth, class_chain(w), w.objectName(), w.width(), w.height(), w.isVisible(),
           props, w.styleSheet()[:200], w.autoFillBackground(),
           palette.window().color().name(), palette.base().color().name(), extra))
    for child in w.children():
        if child.isWidgetType():
            describe(child, depth + 1)


def key(w):
    """Identity of the C++ widget (Python wrappers come and go, so id() is not it)."""
    return getCppPointer(w)[0]


seen = set(key(w) for w in QApplication.topLevelWidgets() if w.isVisible())
elapsed = 0
timer = QTimer()


def write():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def poll():
    global elapsed
    elapsed += POLL_MS
    try:
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and key(w) not in seen:
                seen.add(key(w))
                log("\n== new top-level after %.1fs, windowFlags %s"
                    % (elapsed / 1000, w.windowFlags()))
                describe(w, 0)
    except Exception as e:
        log("error: %r" % e)
    if elapsed >= DURATION_MS:
        timer.stop()
        write()
        print("hints probe written to", OUT)


timer.timeout.connect(poll)
timer.start(POLL_MS)
print("hints probe: hover over things that show hints for the next %ds" % (DURATION_MS // 1000))
