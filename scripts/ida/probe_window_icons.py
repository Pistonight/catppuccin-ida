"""
Research probe (round 8), run inside IDA (File > Script file... / Alt+F7) with
the catppuccin theme and plugin active and some dock windows tabbed together,
so the red close button shows.

Finds where that red close button lives. Lists:
- every visible widget whose class starts with "Dock": its class chain,
  parent, and every button under it (class, tooltip, text, icon, watched by
  the plugin, red pixels currently drawn)
- for each DockTabBar: tabsClosable and the tabs' own buttons (tabButton)
- every other visible button anywhere drawing red pixels

Writes .cache/window_icons_probe.txt.
"""

import gc
import os
import traceback

from PySide6.QtWidgets import QAbstractButton, QApplication, QTabBar

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".cache", "window_icons_probe.txt")

lines = []


def log(*args):
    lines.append(" ".join(str(a) for a in args))


def text(value):
    """PySide returns str at runtime, but its stubs say bytes for some names."""
    return value if isinstance(value, str) else bytes(value).decode()


def class_name(obj):
    return text(obj.metaObject().className()) if obj is not None else None


def class_chain(obj):
    names = []
    meta = obj.metaObject()
    while meta is not None:
        names.append(text(meta.className()))
        meta = meta.superClass()
    return " < ".join(names)


def red_pixels(widget):
    image = widget.grab().toImage()
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.red() > 170 and c.green() < 90 and c.blue() < 90:
                count += 1
    return count


icons = [o for o in gc.get_objects() if type(o).__name__ == "_WindowIcons"]
close_key = icons[0].close_icon.cacheKey() if icons else None


def describe(b):
    icon = b.icon()
    return ("%s | parent %s | toolTip %r | text %r | objectName %r | icon null %s, ours %s | "
            "watched %r | %dx%d | red pixels %d"
            % (class_chain(b), class_name(b.parentWidget()), b.toolTip(), b.text(), b.objectName(),
               icon.isNull(), close_key is not None and icon.cacheKey() == close_key,
               b.property("catppuccinWindowIcons"), b.width(), b.height(), red_pixels(b)))


try:
    log("== plugin _WindowIcons found: %s" % bool(icons))
    seen = set()
    docks = [w for w in QApplication.allWidgets()
             if w.isVisible() and text(w.metaObject().className()).startswith("Dock")]
    for w in docks:
        buttons = [b for b in w.findChildren(QAbstractButton) if b.isVisible()]
        log("\n- %s | parent %s | %d visible buttons"
            % (class_chain(w), class_name(w.parentWidget()), len(buttons)))
        for b in buttons:
            if id(b) in seen:
                log("    (listed above) %s %r" % (class_name(b), b.toolTip()))
                continue
            seen.add(id(b))
            log("    " + describe(b))
        if isinstance(w, QTabBar):
            log("    tabsClosable %s, count %d" % (w.tabsClosable(), w.count()))
            for i in range(w.count()):
                for side in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
                    tb = w.tabButton(i, side)
                    if tb is not None:
                        log("    tab %d %r %s button: %s, red pixels %d"
                            % (i, w.tabText(i), side.name, class_chain(tb), red_pixels(tb)))

    log("\n== other visible buttons drawing red")
    for b in QApplication.allWidgets():
        if isinstance(b, QAbstractButton) and b.isVisible() and b.width() < 64:
            n = red_pixels(b)
            if n > 10:
                chain = []
                p = b.parentWidget()
                while p is not None and len(chain) < 5:
                    chain.append(class_name(p))
                    p = p.parentWidget()
                log("    %s | ancestors %s" % (describe(b), " > ".join(chain)))
except Exception:
    log(traceback.format_exc())

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("probe written to", OUT)
