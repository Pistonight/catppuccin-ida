"""
IDA 9.3 icon workarounds, formerly in chrome.py. Not imported by the plugin
(main_ida.py), so not bundled; kept for reference while icons are redone for 9.4.

- list row icons: the theme's themeicon properties only reached actions; list
  rows (Functions, Local Types, ...) get their icons from IDA's icon table or
  straight from its resources. They are recognised by their pixels and
  swapped for the theme's own icons.
- dock window icons and header buttons: also from IDA's icon table. Windows are
  recognised by their title instead (see the `windows` section of the icon
  config), in their tab, header, title bar and Windows menu entry.

Both were created in Chrome.__init__ and refreshed from Chrome.refresh:

    self.icon_swap = _IconSwap(theme_dir)
    self.window_icons = _WindowIcons(theme_dir)
    ...
    widgets = QApplication.allWidgets()
    self.icon_swap.refresh(widgets)
    self.window_icons.refresh(widgets)
"""

import hashlib
import os
import time

from PySide6.QtCore import QEvent, QObject, QSize, QTimer
from PySide6.QtGui import QIcon, QImage, QPainter
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QHeaderView,
                               QLabel, QMenu, QStyle, QStyledItemDelegate, QTabBar)

from ida.chrome import _app
from icons_gen import WINDOW_CLOSE_ICON, WINDOW_FLOAT_ICON, WINDOW_FULLSCREEN_ICON, WINDOW_ICONS
from perf import perf

ORIGINAL_ICONS = ":/IDAG/resources/menu/"
FINGERPRINT_SIZE = QSize(16, 16)
TABLE_SLICE_MS = 8           # longest a slice of a lookup table build may block the UI
DOCK_WINDOW_CLASS = "IDADockWidget"
DOCK_TITLE_CLASS = "DockWidgetTitle"      # header of a dock window alone in its area
DOCK_AREA_TITLE_CLASS = "DockAreaDragTitle"  # header of an area of tabbed dock windows
DOCK_TAB_BAR_CLASS = "DockTabBar"         # tabs of dock windows sharing an area
# Header buttons, by tooltip -> theme icon (relative to icons/)
DOCK_BUTTON_ICONS = {
    "Close": WINDOW_CLOSE_ICON,
    "Fullscreen": WINDOW_FULLSCREEN_ICON,
    "Float": WINDOW_FLOAT_ICON,
}
WINDOWS_MENU = "Windows"                  # lists the open windows, with their icons
WATCHED_PROPERTY = "catppuccinWindowIcons"
TITLE_PROPERTY = "catppuccinWindowTitle"     # on header icon labels


def _fingerprint(image):
    """Identity of an icon's pixels (size, scale and contents)."""
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = bytes(image.constBits())[:image.sizeInBytes()]
    return image.width(), image.height(), image.devicePixelRatio(), hashlib.sha1(data).digest()


class _IconSwap:
    """Swaps IDA's original icons for the theme's in list rows, which bypass
    the themeicon properties. IDA renders its icons from Qt resources, so
    rendering a resource the same way gives the exact pixels to look for:
    - icons/menu/<Name>.svg replaces :/IDAG/resources/menu/<Name>.svg
    - icons/swapped/<path>.svg replaces :/<path>.svg (e.g. Local Types rows)"""

    def __init__(self, theme_dir):
        # (original QIcon, theme QIcon) in priority order. A few originals are
        # pixel-identical (e.g. WatchList / WatchView); those take the
        # alphabetically first name's icon.
        self.pairs = []
        icons_dir = os.path.join(theme_dir, "icons")
        menu_dir = os.path.join(icons_dir, "menu")
        for name in sorted(os.listdir(menu_dir)) if os.path.isdir(menu_dir) else []:
            if name.endswith(".svg"):
                self._add(ORIGINAL_ICONS + name, os.path.join(menu_dir, name))
        swapped_dir = os.path.join(icons_dir, "swapped")
        for dirpath, _, files in sorted(os.walk(swapped_dir)):
            for name in sorted(files):
                if name.endswith(".svg"):
                    path = os.path.join(dirpath, name)
                    resource = os.path.relpath(path, swapped_dir).replace(os.sep, "/")
                    self._add(":/" + resource, path)
        # Fingerprints depend on the screen scale, which may not be known yet at
        # startup, so a table is built per scale, once refresh() or a row asks
        # for it. Rendering every original takes a few hundred ms, so it is
        # built in slices between events; rows drawn meanwhile keep IDA's icon
        # and are repainted once it is done.
        self.tables = {}             # scale -> {fingerprint: theme QIcon}
        self.building = {}           # scale -> (partial table, remaining pairs, start)
        self.icon_cache = {}         # (QIcon.cacheKey(), scale) -> theme QIcon or None

    def _add(self, original_path, theme_path):
        original = QIcon(original_path)
        if not original.isNull():
            self.pairs.append((original, QIcon(theme_path)))

    def _build(self, scale):
        """Start building the lookup table for `scale`, unless built or underway."""
        if scale not in self.tables and scale not in self.building:
            self.building[scale] = ({}, iter(self.pairs), time.perf_counter())
            QTimer.singleShot(0, lambda: self._build_slice(scale))

    def _build_slice(self, scale):
        table, pairs, start = self.building[scale]
        deadline = time.perf_counter() + TABLE_SLICE_MS / 1000
        with perf.measure("list icons: table slice"):
            for original, theme in pairs:
                key = _fingerprint(original.pixmap(FINGERPRINT_SIZE, scale).toImage())
                table.setdefault(key, theme)
                if time.perf_counter() >= deadline:
                    QTimer.singleShot(0, lambda: self._build_slice(scale))
                    return
        del self.building[scale]
        self.tables[scale] = table
        perf.note("list icons: table @%g built in %.0f ms (wall clock, in slices)"
                  % (scale, (time.perf_counter() - start) * 1000))
        for w in QApplication.allWidgets():  # rows drawn meanwhile showed IDA's icons
            if isinstance(w, QAbstractItemView) and isinstance(w.itemDelegate(), _IconSwapDelegate):
                w.viewport().update()

    def icon(self, icon):
        """The theme's replacement for an original IDA icon, or None (also
        while the lookup table is being built)."""
        if icon is None or icon.isNull():
            return None
        scale = _app().devicePixelRatio()
        key = (icon.cacheKey(), scale)
        if key not in self.icon_cache:
            table = self.tables.get(scale)
            if table is None:
                self._build(scale)
                return None
            image = icon.pixmap(FINGERPRINT_SIZE, scale).toImage()
            self.icon_cache[key] = table.get(_fingerprint(image))
        return self.icon_cache[key]

    def refresh(self, widgets):
        self._build(_app().devicePixelRatio())   # usually ready before any list draws
        for w in widgets:
            if isinstance(w, QAbstractItemView) and not isinstance(w, QHeaderView):
                self._swap_delegate(w)

    def _swap_delegate(self, view):
        """List/tree rows drawn by a plain QStyledItemDelegate (e.g. Functions,
        Local Types) get one that swaps the row icons."""
        delegate = view.itemDelegate()
        if delegate is not None and delegate.metaObject().className() == "QStyledItemDelegate":
            view.setItemDelegate(_IconSwapDelegate(self, view))


class _IconSwapDelegate(QStyledItemDelegate):
    """A plain item delegate, except original IDA icons are swapped for the theme's."""

    def __init__(self, swap, parent):
        super().__init__(parent)
        self.swap = swap

    def initStyleOption(self, option, index):
        with perf.measure("list icons: row"):
            super().initStyleOption(option, index)
            # `icon` exists at runtime but is missing from PySide's type stubs
            replacement = self.swap.icon(getattr(option, "icon"))
            if replacement is not None:
                setattr(option, "icon", replacement)


class _WindowIcons(QObject):
    """Dock window icons, by window title, wherever IDA shows them: the
    window's own icon (title bar when floating), its header, its tab and its
    Windows menu entry, plus the header's buttons. IDA re-applies its
    icons at will, so the headers and tab bars are watched and fixed up right
    before they paint, and the Windows menu right before it shows."""

    def __init__(self, theme_dir):
        super().__init__()
        icons_dir = os.path.join(theme_dir, "icons")
        self.icons = [(title, is_prefix, QIcon(os.path.join(icons_dir, path)))
                      for title, is_prefix, path in WINDOW_ICONS]
        self.button_icons = {tip: QIcon(os.path.join(icons_dir, path))
                             for tip, path in DOCK_BUTTON_ICONS.items()}

    def icon(self, title):
        """The theme's icon for a dock window title, or None."""
        title = title.strip()
        for name, is_prefix, icon in self.icons:
            if title == name or (is_prefix and title.startswith(name)):
                return icon
        return None

    def refresh(self, widgets):
        for w in widgets:
            kind = w.metaObject().className()
            if kind == DOCK_WINDOW_CLASS:
                _set_icon(self.icon(w.windowTitle()), w.windowIcon, w.setWindowIcon)
            elif kind == DOCK_TAB_BAR_CLASS and isinstance(w, QTabBar):
                self._watch(w)
                self._fix_tabs(w)
            elif kind == DOCK_TITLE_CLASS:
                self._watch_title(w)
                self._watch_buttons(w)
            elif kind == DOCK_AREA_TITLE_CLASS:
                self._watch_buttons(w)
            elif isinstance(w, QMenu) and _menu_text(w.title()) == WINDOWS_MENU:
                self._watch(w)

    def _watch(self, widget):
        if not widget.property(WATCHED_PROPERTY):
            widget.setProperty(WATCHED_PROPERTY, True)
            widget.installEventFilter(self)
            widget.update()

    def _watch_title(self, title):
        labels = title.findChildren(QLabel)
        text = next((label.text() for label in labels if label.text()), "")
        for label in labels:
            if not label.text():                 # the icon, next to the title label
                # for _paint_label
                if label.property(TITLE_PROPERTY) != text:
                    label.setProperty(TITLE_PROPERTY, text)
                    label.update()
                self._watch(label)

    def _watch_buttons(self, header):
        """The header's Close / Fullscreen / Float buttons."""
        for button in header.findChildren(QAbstractButton):
            icon = self.button_icons.get(button.toolTip())
            if icon is not None:
                self._watch(button)
                _set_icon(icon, button.icon, button.setIcon)

    def _fix_tabs(self, bar):
        for i in range(bar.count()):
            _set_icon(self.icon(bar.tabText(i)), lambda: bar.tabIcon(i),
                      lambda icon: bar.setTabIcon(i, icon))

    def _fix_menu(self, menu):
        """The Windows menu's entries are named after the windows' titles."""
        for action in menu.actions():
            _set_icon(self.icon(_menu_text(action.text())), action.icon, action.setIcon)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QMenu):
            try:
                with perf.measure("window icons: menu"):
                    self._fix_menu(watched)      # IDA refills it on aboutToShow
            except RuntimeError:
                pass
            return False
        if event.type() != QEvent.Type.Paint:
            return False
        with perf.measure("window icons: paint " + type(watched).__name__):
            return self._paint_event(watched)

    def _paint_event(self, watched):
        try:
            if isinstance(watched, QTabBar):
                self._fix_tabs(watched)
            elif isinstance(watched, QAbstractButton):
                _set_icon(self.button_icons.get(watched.toolTip()), watched.icon, watched.setIcon)
            elif isinstance(watched, QLabel):
                return self._paint_label(watched)
        except RuntimeError:                     # widget deleted under us: paint normally
            pass
        return False

    def _paint_label(self, label):
        """Paint the theme's icon in place of a header's icon label (IDA keeps
        re-applying its own pixmap, so it is painted over rather than replaced)."""
        pixmap = label.pixmap()
        if pixmap.isNull():
            return False
        rect_args = (label.layoutDirection(), label.alignment(), label.contentsRect())
        # Set by _watch_title. (Looking up the title label here, while the
        # label paints, re-wraps it and PySide took it for deleted.)
        icon = self.icon(str(label.property(TITLE_PROPERTY) or ""))
        if icon is None:
            return False                         # unknown window: paint normally
        size = pixmap.deviceIndependentSize().toSize()
        rect = QStyle.alignedRect(rect_args[0], rect_args[1], size, rect_args[2])
        painter = QPainter(label)
        painter.drawPixmap(rect.topLeft(), icon.pixmap(size, pixmap.devicePixelRatio()))
        painter.end()
        return True


def _menu_text(text):
    """A menu or action text without its & mnemonics and tab-separated shortcut."""
    return text.split("\t")[0].replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


def _set_icon(icon, get, set_):
    """set_(icon) unless it is already set (setting icons repaints)."""
    if icon is not None and get().cacheKey() != icon.cacheKey():
        set_(icon)
