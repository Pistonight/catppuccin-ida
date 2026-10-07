"""
List row icons (Functions, Local Types, ...): rows get their icons straight
from IDA's resources, not through an action, so ActionIcons cannot reach
them. A QIcon does not tell where it was loaded from, so originals are
recognised by their pixels: every icon the theme has a version of
(<theme>/<path>, see chrome_icon_resources.py) is rendered from its resource
(:/<prefix>/<path>) the way IDA renders it, and a row icon drawing the same
pixels is swapped for the theme's.
"""

import hashlib
import time

import ida_kernwin
from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QAbstractItemView, QApplication, QHeaderView, QStyledItemDelegate

from perf import perf

FINGERPRINT_SIZE = QSize(16, 16)
TABLE_SLICE_MS = 8           # longest a slice of a lookup table build may block the UI
# Views are looked for after a new IDA window shows (_IconSwapHooks); this
# catches the rest (e.g. dialogs).
VIEW_SCAN_FALLBACK_S = 10


def _fingerprint(image):
    """Identity of an icon's pixels (size, scale and contents)."""
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = bytes(image.constBits())[:image.sizeInBytes()]
    return image.width(), image.height(), image.devicePixelRatio(), hashlib.sha1(data).digest()


def _scale():
    app = QApplication.instance()
    assert isinstance(app, QApplication)   # IDA's GUI is a QApplication
    return app.devicePixelRatio()


class IconSwap:
    """Swaps IDA's original icons for the theme's in list/tree rows drawn by
    a plain QStyledItemDelegate (it gets an IconSwapDelegate)."""

    def __init__(self, resources):
        # (original QIcon, theme QIcon) for every icon the theme has. A few
        # originals may be pixel-identical; those take the first path's icon.
        self.pairs = []
        for path, resource in sorted(resources.resources.items()):
            file = resources.theme_file(path)
            if file is not None:
                original = QIcon(resource)
                if not original.isNull():
                    self.pairs.append((original, QIcon(file)))
        # Fingerprints depend on the screen scale, which may not be known yet at
        # startup, so a table is built per scale, once refresh() or a row asks
        # for it, in slices between events; rows drawn meanwhile keep IDA's
        # icon and are repainted once it is done.
        self.tables = {}             # scale -> {fingerprint: theme QIcon}
        self.building = {}           # scale -> (partial table, remaining pairs, start)
        self.icon_cache = {}         # (QIcon.cacheKey(), scale) -> theme QIcon or None
        self.stale = True            # views may have been created since the last scan
        self.last_scan = 0.0
        self.hooks = _IconSwapHooks(self)
        self.hooks.hook()

    def mark_stale(self):
        self.stale = True

    def _build(self, scale):
        """Start building the lookup table for `scale`, unless built or underway."""
        if scale not in self.tables and scale not in self.building:
            self.building[scale] = ({}, iter(self.pairs), time.perf_counter())
            QTimer.singleShot(0, lambda: self._build_slice(scale))

    def _build_slice(self, scale):
        table, pairs, start = self.building[scale]
        deadline = time.perf_counter() + TABLE_SLICE_MS / 1000
        with perf.measure("row icons: table slice"):
            for original, theme in pairs:
                table.setdefault(_fingerprint(original.pixmap(FINGERPRINT_SIZE, scale).toImage()), theme)
                if time.perf_counter() >= deadline:
                    QTimer.singleShot(0, lambda: self._build_slice(scale))
                    return
        del self.building[scale]
        self.tables[scale] = table
        perf.note("row icons: table @%g of %d icons built in %.0f ms (wall clock, in slices)"
                  % (scale, len(self.pairs), (time.perf_counter() - start) * 1000))
        for w in QApplication.allWidgets():  # rows drawn meanwhile showed IDA's icons
            if isinstance(w, QAbstractItemView) and isinstance(w.itemDelegate(), IconSwapDelegate):
                w.viewport().update()

    def icon(self, icon):
        """The theme's replacement for an original IDA icon, or None (also
        while the lookup table is being built)."""
        if icon is None or icon.isNull() or not self.pairs:
            return None
        scale = _scale()
        key = (icon.cacheKey(), scale)
        if key not in self.icon_cache:
            table = self.tables.get(scale)
            if table is None:
                self._build(scale)
                return None
            self.icon_cache[key] = table.get(_fingerprint(icon.pixmap(FINGERPRINT_SIZE, scale).toImage()))
        return self.icon_cache[key]

    def refresh(self):
        if not self.pairs:
            return
        self._build(_scale())            # usually ready before any list draws
        now = time.monotonic()
        if not self.stale and now - self.last_scan < VIEW_SCAN_FALLBACK_S:
            return
        self.stale = False
        self.last_scan = now
        for w in QApplication.allWidgets():
            if isinstance(w, QAbstractItemView) and not isinstance(w, QHeaderView):
                delegate = w.itemDelegate()
                if delegate is not None and delegate.metaObject().className() == "QStyledItemDelegate":
                    w.setItemDelegate(IconSwapDelegate(self, w))

    def stop(self):
        self.hooks.unhook()


class IconSwapDelegate(QStyledItemDelegate):
    """A plain item delegate, except original IDA icons are swapped for the theme's."""

    def __init__(self, swap, parent):
        super().__init__(parent)
        self.swap = swap

    def initStyleOption(self, option, index):
        with perf.measure("row icons: row"):
            super().initStyleOption(option, index)
            # `icon` exists at runtime but is missing from PySide's type stubs
            replacement = self.swap.icon(getattr(option, "icon"))
            if replacement is not None:
                setattr(option, "icon", replacement)


class _IconSwapHooks(ida_kernwin.UI_Hooks):
    """Marks the views stale when an IDA window shows (it may hold new
    lists); the scan waits for the next refresh."""

    def __init__(self, swap):
        super().__init__()
        self.swap = swap

    def widget_visible(self, widget):
        self.swap.mark_stale()
