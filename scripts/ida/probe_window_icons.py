"""
Research probe (round 6), run inside IDA (File > Script file... / Alt+F7) with
the catppuccin theme and plugin active and several dock windows tabbed
together (a DockTabBar visible).

The plugin swaps the icons of tabbed dock windows with QTabBar.setTabIcon, but
the tabs still look original. This checks whether DockTabBar draws the icons
QTabBar stores at all:

- for every visible DockTabBar: each tab's stored icon (IDA ORIGINAL / OURS)
- experiment on the first tab: set a solid red icon, grab the tab bar's
  pixels, count red pixels inside that tab; then restore the original icon
- run the plugin's swap and report the stored icons again

Writes .cache/window_icons_probe.txt.
"""

import gc
import hashlib
import os
import traceback

from PySide6.QtCore import QDirIterator, QSize
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QTabBar

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".cache", "window_icons_probe.txt")
PREFIX = ":/IDAG/resources/menu/"
SIZE = QSize(16, 16)
RED = QColor(255, 0, 0)

lines = []


def log(*args):
    lines.append(" ".join(str(a) for a in args))


def text(value):
    """PySide returns str at runtime, but its stubs say bytes for some names."""
    return value if isinstance(value, str) else bytes(value).decode()


def class_name(obj):
    return text(obj.metaObject().className()) if obj is not None else None


def fingerprint(image):
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = bytes(image.constBits())[:image.sizeInBytes()]
    return image.width(), image.height(), image.devicePixelRatio(), hashlib.sha1(data).digest()


originals = {}
it = QDirIterator(PREFIX, QDirIterator.IteratorFlag.Subdirectories)
while it.hasNext():
    path = it.next()
    if path.endswith(".svg"):
        originals.setdefault(fingerprint(QIcon(path).pixmap(SIZE).toImage()), path[len(PREFIX):-4])

swaps = [o for o in gc.get_objects() if type(o).__name__ == "_IconSwap"]
swap = swaps[0] if swaps else None
ours = set()
if swap is not None:
    ours = {fingerprint(theme.pixmap(SIZE).toImage()) for _, theme in swap.pairs}


def classify(icon):
    if icon is None or icon.isNull():
        return "(none)"
    fp = fingerprint(icon.pixmap(SIZE).toImage())
    if fp in originals:
        return "IDA ORIGINAL %s" % originals[fp]
    if fp in ours:
        return "OURS"
    return "other"


def red_pixels(bar, index):
    image = bar.grab().toImage()
    scale = image.devicePixelRatio()
    rect = bar.tabRect(index)
    count = 0
    for y in range(int(rect.top() * scale), int((rect.bottom() + 1) * scale)):
        for x in range(int(rect.left() * scale), int((rect.right() + 1) * scale)):
            if 0 <= x < image.width() and 0 <= y < image.height():
                c = image.pixelColor(x, y)
                if c.red() > 230 and c.green() < 40 and c.blue() < 40:
                    count += 1
    return count


try:
    log("== plugin swap object found: %s" % (swap is not None))
    bars = [w for w in QApplication.allWidgets()
            if isinstance(w, QTabBar) and w.isVisible() and class_name(w) == "DockTabBar"]
    log("== %d visible DockTabBars" % len(bars))
    for bar in bars:
        log("\n- %d tabs, icon size %dx%d, metaObject %s < %s"
            % (bar.count(), bar.iconSize().width(), bar.iconSize().height(),
               class_name(bar), text(bar.metaObject().superClass().className())))
        for i in range(bar.count()):
            log("    tab %d %r stored icon: %s" % (i, bar.tabText(i), classify(bar.tabIcon(i))))

        if bar.count():
            original = bar.tabIcon(0)
            log("  experiment on tab 0, red pixels before: %d" % red_pixels(bar, 0))
            red = QPixmap(64, 64)
            red.fill(RED)
            bar.setTabIcon(0, QIcon(red))
            QApplication.processEvents()
            log("  after setTabIcon(red): stored icon is red: %s, red pixels drawn in tab 0: %d"
                % (classify(bar.tabIcon(0)) == "other", red_pixels(bar, 0)))
            bar.setTabIcon(0, original)
            QApplication.processEvents()
            log("  restored: %s" % classify(bar.tabIcon(0)))

    if swap is not None:
        swap.refresh()
        QApplication.processEvents()
        log("\n== after swap.refresh()")
        for bar in bars:
            log("- " + ", ".join("%r %s" % (bar.tabText(i), classify(bar.tabIcon(i)))
                                 for i in range(bar.count())))
except Exception:
    log(traceback.format_exc())

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("probe written to", OUT)
