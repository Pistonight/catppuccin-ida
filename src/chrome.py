"""
Window chrome a theme cannot reach, because it is not drawn by Qt style
sheets:

- the Windows title bar: drawn by the OS (DWM). On Windows 11 the caption,
  caption text and border colours can be set per window; on Windows 10 we
  can only ask for the dark title bar.
- the nav band scroll buttons: IDA sets their (black) icon in code after the
  theme is applied, so we replace it at runtime.
"""

import ctypes
import os
import re
import sys

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractButton, QApplication

# Catppuccin Mocha
CAPTION = "#181825"   # mantle
CAPTION_TEXT = "#cdd6f4"  # text
BORDER = "#313244"    # surface0

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

THEME_DIR_RE = re.compile(r'url\("([^"]*/themes/catppuccin)/icons/')
POLL_MS = 1000


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

        _app().focusChanged.connect(self.refresh)   # new dialogs take focus
        self.timer = QTimer(self)                # catches everything else
        self.timer.timeout.connect(self.refresh)
        self.timer.start(POLL_MS)
        self.refresh()

    def stop(self):
        self.timer.stop()
        try:
            _app().focusChanged.disconnect(self.refresh)
        except (RuntimeError, TypeError):
            pass

    def refresh(self, *_):
        for w in QApplication.topLevelWidgets():
            if w.isVisible():
                self._style_title_bar(w)
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
        self._set_dwm(hwnd, DWMWA_CAPTION_COLOR, _colorref(CAPTION))   # Windows 11 only;
        self._set_dwm(hwnd, DWMWA_TEXT_COLOR, _colorref(CAPTION_TEXT))  # ignored on 10
        self._set_dwm(hwnd, DWMWA_BORDER_COLOR, _colorref(BORDER))

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
