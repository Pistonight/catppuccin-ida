"""
Research probe, run inside IDA (File > Script file... / Alt+F7) with the
catppuccin theme and plugin active, a database open, after using the
features whose icons change (search direction toggled, a string type picked,
...). Finds icons IDA changes at runtime, which the plugin (it looks at each
action once) misses.

Every icon is identified by pixels against IDA's resources (rendered the
same way), so it also works for icons not set through an action:

1. Actions whose current icon is one of IDA's built-in ones: with the plugin
   active, these were not replaced (no theme file, or IDA changed the icon
   after the plugin looked).
2. Every menu entry and submenu (menu bar, opened as if clicked) whose icon
   draws one of IDA's resources: which resource, and the action behind it if
   any (by label).
3. Every visible label/button outside menus showing one of IDA's resources
   (e.g. the analysis indicator in the toolbar): class, tooltip, resource.
4. How long get_action_icon() over every action takes (for deciding how
   often the plugin can re-check them).

Writes .cache/dynamic_icons_probe.txt.
"""

import hashlib
import os
import time
import traceback
from pathlib import Path

import ida_diskio
import ida_kernwin
from PySide6.QtCore import QDirIterator, QSize
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QMainWindow, QMenu

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".cache" / "dynamic_icons_probe.txt"
THEME_DIR = Path(ida_diskio.get_user_idadir()) / "themes" / "catppuccin"
SIZES = (16, 20, 24, 32)

lines = []


def log(*args):
    lines.append(" ".join(str(a) for a in args))


def text(value):
    return value if isinstance(value, str) else bytes(value).decode()


def class_name(obj):
    return text(obj.metaObject().className())


def fingerprint_image(image):
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = bytes(image.constBits())[:image.sizeInBytes()]
    return image.width(), image.height(), hashlib.sha1(data).digest()


def fingerprint_icon(icon, size, scale):
    return fingerprint_image(icon.pixmap(QSize(size, size), scale).toImage())


def menu_text(value):
    return value.split("\t")[0].replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


def resources():
    """{path without :/<prefix>/: full resource path} for every image."""
    found = {}
    it = QDirIterator(":/", QDirIterator.IteratorFlag.Subdirectories)
    while it.hasNext():
        resource = it.next()
        parts = resource[len(":/"):].split("/", 1)
        if len(parts) == 2 and resource.endswith((".svg", ".png")) and not resource.startswith(":/qt-project.org/"):
            found.setdefault(parts[1], resource)
    return found


def theme_status(path):
    return "theme file exists" if (THEME_DIR / path).is_file() else "NO theme file"


try:
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    scale = app.devicePixelRatio()
    images = resources()
    table = {}                                  # id -> path
    for path in images:
        icon_id = ida_kernwin.get_icon_id_by_name(path)
        if icon_id >= 0:
            table.setdefault(icon_id, path)
    by_print = {}                               # fingerprint -> path
    for path, resource in sorted(images.items()):
        icon = QIcon(resource)
        for size in SIZES:
            by_print.setdefault(fingerprint_icon(icon, size, scale), path)
    log("theme dir: %s; scale %g; %d resource images, %d in the icon table"
        % (THEME_DIR, scale, len(images), len(table)))

    def identify(icon):
        if icon is None or icon.isNull():
            return None
        for size in SIZES:
            path = by_print.get(fingerprint_icon(icon, size, scale))
            if path is not None:
                return path
        return None

    # 1. actions still showing a built-in icon
    labels = {}                                 # menu text -> [action]
    log("")
    log("== 1. actions showing one of IDA's built-in icons (not replaced)")
    start = time.perf_counter()
    actions = ida_kernwin.get_registered_actions()
    icons = {a: ida_kernwin.get_action_icon(a) for a in actions}
    elapsed = (time.perf_counter() - start) * 1000
    for action in sorted(actions):
        ok, icon_id = icons[action]
        labels.setdefault(menu_text(ida_kernwin.get_action_label(action) or ""), []).append(action)
        if ok and icon_id in table:
            log("  %s: #%d %s (%s)" % (action, icon_id, table[icon_id], theme_status(table[icon_id])))

    # 2. menu entries and submenus drawing one of IDA's resources
    log("")
    log("== 2. menu entries / submenus drawing one of IDA's resources")
    opened = set()

    def walk(menu, where):
        if menu is None or id(menu) in opened:
            return
        opened.add(id(menu))
        menu.aboutToShow.emit()
        QApplication.processEvents()
        for entry in menu.actions():
            label = menu_text(entry.text())
            path = identify(entry.icon())
            if path is not None:
                kind = "submenu" if entry.menu() is not None else "entry"
                log("  %s > %s [%s]: %s (%s); actions with this label: %s"
                    % (where, label, kind, path, theme_status(path), ", ".join(labels.get(label, [])) or "-"))
            walk(entry.menu(), where + " > " + label)
        menu.aboutToHide.emit()

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QMainWindow):
            for entry in w.menuBar().actions():
                walk(entry.menu(), menu_text(entry.text()))

    # 3. labels and buttons outside menus drawing one of IDA's resources
    log("")
    log("== 3. visible labels / buttons drawing one of IDA's resources")
    for w in QApplication.allWidgets():
        if not w.isVisible() or isinstance(w, QMenu):
            continue
        icon = None
        if isinstance(w, QAbstractButton):
            icon = w.icon()
        elif isinstance(w, QLabel) and not w.pixmap().isNull():
            icon = QIcon(w.pixmap())
        path = identify(icon)
        if path is not None:
            parent = w.parentWidget()
            log("  %s (parent %s) tooltip=%r text=%r: %s (%s)"
                % (class_name(w), class_name(parent) if parent else "-", w.toolTip(),
                   w.text() if isinstance(w, (QAbstractButton, QLabel)) else "", path, theme_status(path)))

    log("")
    log("== 4. get_action_icon() over all %d actions: %.1f ms" % (len(actions), elapsed))
except Exception:
    log(traceback.format_exc())

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("dynamic icons probe: wrote %s (%d lines)" % (OUT, len(lines)))
