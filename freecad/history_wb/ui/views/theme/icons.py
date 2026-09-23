"""File responsibility: Build theme-aware Qt icons from SVG resources."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from ....qt import QtCore, QtGui, QtWidgets
from ....resources import get_icon_path
from .colors import _color_from_key, _color_key, _ColorKey


__all__ = ["set_themed_icon"]

_THEMED_ICON_BINDING_ATTR = "_history_wb_themed_icon_binding"
_DARK_THEME_PROPERTY = "historyDarkTheme"
_DARK_ACTION_ICON_COLOR = QtGui.QColor("#e6e6e6")


def _themed_icon(icon_name: str, color: QtGui.QColor, preserve_disabled_color: bool = False) -> QtGui.QIcon:
    """Create QIcon from currentColor SVG using explicit resolved color."""
    return _cached_themed_icon(icon_name, _color_key(color), preserve_disabled_color)


def set_themed_icon(
    button: QtWidgets.QAbstractButton,
    icon_name: str,
    *,
    preserve_disabled_color: bool = False,
) -> None:
    """Set a themed SVG icon on a button and refresh it when palette changes."""
    binding = _ThemedButtonIconBinding(button, icon_name, preserve_disabled_color)
    cast(Any, button).__setattr__(_THEMED_ICON_BINDING_ATTR, binding)
    button.installEventFilter(binding)
    binding.apply()


class _ThemedButtonIconBinding(QtCore.QObject):
    """Event filter that keeps one button icon synced with its palette."""

    def __init__(
        self,
        button: QtWidgets.QAbstractButton,
        icon_name: str,
        preserve_disabled_color: bool,
    ) -> None:
        super().__init__(button)
        self._button = button
        self._icon_name = icon_name
        self._preserve_disabled_color = preserve_disabled_color
        self._theme_probe = QtWidgets.QLabel(button)
        self._theme_probe.hide()
        self._theme_probe.installEventFilter(self)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Refresh icon after Qt style or palette changes."""
        if watched in (self._button, self._theme_probe) and event.type() in {
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.Polish,
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.StyleChange,
        }:
            self.apply()
        return False

    def apply(self) -> None:
        """Apply current themed icon to the target button."""
        dark_theme = self._button.property(_DARK_THEME_PROPERTY)
        if dark_theme is True:
            color = _DARK_ACTION_ICON_COLOR
        elif dark_theme is False:
            color = self._button.palette().color(
                QtGui.QPalette.ColorGroup.Active,
                QtGui.QPalette.ColorRole.ButtonText,
            )
        else:
            self._theme_probe.ensurePolished()
            color = self._theme_probe.palette().color(QtGui.QPalette.ColorRole.WindowText)
        self._button.setIcon(_themed_icon(self._icon_name, color, self._preserve_disabled_color))


@lru_cache(maxsize=256)
def _cached_themed_icon(
    icon_name: str,
    icon_color_key: _ColorKey,
    preserve_disabled_color: bool,
) -> QtGui.QIcon:
    """Return cached icon rendered with one foreground color."""
    icon_path = get_icon_path(icon_name)
    if not icon_path.exists():
        raise RuntimeError(f"Icon resource not found: {icon_name}")

    svg_text = icon_path.read_text(encoding="utf-8")
    if "currentColor" not in svg_text:
        raise RuntimeError(f"Themed SVG icon must use currentColor: {icon_name}")

    icon_color = _color_from_key(icon_color_key)
    themed_svg_text = svg_text.replace("currentColor", icon_color.name())
    pixmap = QtGui.QPixmap()
    if not pixmap.loadFromData(themed_svg_text.encode("utf-8")):
        raise RuntimeError(f"Themed SVG icon could not be rendered: {icon_name}")
    icon = QtGui.QIcon(pixmap)
    if preserve_disabled_color:
        icon.addPixmap(pixmap, QtGui.QIcon.Mode.Disabled)
    return icon
