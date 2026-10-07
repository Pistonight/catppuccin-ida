"""
Window chrome a theme cannot reach, because it is not drawn by Qt style
sheets:

- the Windows title bar: drawn by the OS (DWM). On Windows 11 the caption,
  caption text and border colours can be set per window; on Windows 10 we
  can only ask for the dark title bar.
- the nav band scroll buttons: IDA sets their (black) icon in code after the
  theme is applied, so we replace it at runtime.
- disabled icons: Qt generates them by remapping the icon to greys around the
  window colour, which leaves light icons light on a dark theme. A proxy style
  draws them as the normal icon, faded, instead.
"""

import ctypes
import os
import re
import sys

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QPixmap, QPixmapCache
from PySide6.QtWidgets import QAbstractButton, QApplication, QProxyStyle, QStyle

from color_gen import TITLEBAR__BORDER, TITLEBAR__CAPTION, TITLEBAR__TEXT
from perf import perf

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

THEME_DIR_RE = re.compile(r'url\("([^"]*/themes/catppuccin)/icons/')
POLL_MS = 1000
DISABLED_ICON_OPACITY = 0.35


def _colorref(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return b << 16 | g << 8 | r


def _app():
    app = QApplication.instance()
    assert isinstance(app, QApplication)   # IDA's GUI is a QApplication
    return app


def theme_dir():
    """The active catppuccin theme folder, or None if another theme is active."""
    m = THEME_DIR_RE.search(_app().styleSheet())
    return m.group(1) if m else None


class _FadedDisabledIcons(QProxyStyle):
    """The application's style, except disabled icons are the normal icon at
    DISABLED_ICON_OPACITY."""

    def generatedIconPixmap(self, iconMode, pixmap, opt):
        if iconMode != QIcon.Mode.Disabled:
            return super().generatedIconPixmap(iconMode, pixmap, opt)
        faded = QPixmap(pixmap.size())
        faded.setDevicePixelRatio(pixmap.devicePixelRatio())
        faded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(faded)
        painter.setOpacity(DISABLED_ICON_OPACITY)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return faded


def _install_faded_disabled_icons():
    """Put _FadedDisabledIcons on top of the application's existing style,
    whatever it is (IDA's own proxy style, a user's choice, ...); returns the
    new style, or None if the style chain looks unexpected."""
    current = _app().style()
    base = current
    if current.metaObject().className() == "QStyleSheetStyle":
        # With a style sheet (the theme), Qt wraps the real style in an
        # internal QStyleSheetStyle; the real style is its only QStyle child.
        inner = [c for c in current.children() if isinstance(c, QStyle)]
        if len(inner) != 1:
            print("catppuccin: disabled icons left unchanged; QStyleSheetStyle wraps %d styles"
                  % len(inner))
            return None
        base = inner[0]
    # QProxyStyle takes ownership of `base`, so it survives Qt deleting the old
    # QStyleSheetStyle; setStyle() then wraps us in a new one for the style sheet.
    faded = _FadedDisabledIcons(base)
    _app().setStyle(faded)
    QPixmapCache.clear()      # drop disabled icons already drawn the old way
    return faded


class Chrome(QObject):
    def __init__(self, theme_dir):
        super().__init__()
        self.styled = set()       # native window handles already coloured
        self.nav_icons = {
            "Scroll up": QIcon(os.path.join(theme_dir, "icons", "arrow-left.svg")),
            "Scroll down": QIcon(os.path.join(theme_dir, "icons", "arrow-right.svg")),
        }
        self.nav_buttons: list[QAbstractButton] = []
        self.dwm = ctypes.windll.dwmapi if sys.platform == "win32" else None
        with perf.measure("init: faded disabled icons (setStyle)", report=True):
            self.style = _install_faded_disabled_icons()   # kept alive with the plugin

        _app().focusChanged.connect(self.refresh)   # new dialogs take focus
        self.timer = QTimer(self)                # catches everything else
        self.timer.timeout.connect(self.refresh)
        self.timer.start(POLL_MS)
        with perf.measure("init: first refresh", report=True):
            self.refresh()

    def stop(self):
        self.timer.stop()
        try:
            _app().focusChanged.disconnect(self.refresh)
        except (RuntimeError, TypeError):
            pass

    def refresh(self, *_):
        with perf.measure("refresh"):
            with perf.measure("refresh: title bars"):
                for w in QApplication.topLevelWidgets():
                    if w.isVisible():
                        self._style_title_bar(w)
            with perf.measure("refresh: nav buttons"):
                self._fix_nav_buttons()

    def _set_dwm(self, hwnd, attr, value):
        v = ctypes.c_int(value)
        return self.dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)) == 0

    def _style_title_bar(self, w):
        if self.dwm is None:
            return
        hwnd = int(w.winId())
        if hwnd in self.styled:
            return
        self.styled.add(hwnd)
        self._set_dwm(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1)  # light caption buttons
        self._set_dwm(hwnd, DWMWA_CAPTION_COLOR, _colorref(TITLEBAR__CAPTION))  # Windows 11 only;
        self._set_dwm(hwnd, DWMWA_TEXT_COLOR, _colorref(TITLEBAR__TEXT))     # ignored on 10
        self._set_dwm(hwnd, DWMWA_BORDER_COLOR, _colorref(TITLEBAR__BORDER))

    def _fix_nav_buttons(self):
        if not self.nav_buttons:
            self.nav_buttons = [
                w for w in QApplication.allWidgets()
                if isinstance(w, QAbstractButton)
                and w.metaObject().className() == "nav_scroll_button_t"
            ]
        alive = []
        for b in self.nav_buttons:
            try:
                icon = self.nav_icons.get(b.toolTip())
            except RuntimeError:          # widget was deleted
                continue
            alive.append(b)
            if icon is not None and b.icon().cacheKey() != icon.cacheKey():
                b.setIcon(icon)
        self.nav_buttons = alive
