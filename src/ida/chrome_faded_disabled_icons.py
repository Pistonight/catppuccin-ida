"""
Disabled icons: Qt generates them by remapping the icon to greys around the
window colour, which leaves light icons light on a dark theme. A proxy style
draws them as the normal icon, faded, instead.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QPixmapCache
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle

DISABLED_ICON_OPACITY = 0.35


class FadedDisabledIcons(QProxyStyle):
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


def install_faded_disabled_icons():
    """Put FadedDisabledIcons on top of the application's existing style,
    whatever it is (IDA's own proxy style, a user's choice, ...); returns the
    new style, or None if the style chain looks unexpected."""
    app = QApplication.instance()
    assert isinstance(app, QApplication)   # IDA's GUI is a QApplication
    current = app.style()
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
    faded = FadedDisabledIcons(base)
    app.setStyle(faded)
    QPixmapCache.clear()      # drop disabled icons already drawn the old way
    return faded
