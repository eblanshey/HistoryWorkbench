"""File responsibility: Apply action button styling for the active Qt theme."""

from __future__ import annotations

from typing import Any, cast

from ....qt import QtCore, QtWidgets
from ..widgets.styles import ACTION_BUTTON_STYLE, DARK_ACTION_BUTTON_STYLE
from .colors import _is_dark_color


_ACTION_BUTTON_BINDING_ATTR = "_history_wb_action_button_binding"
_DARK_THEME_PROPERTY = "historyDarkTheme"


def set_action_button_style(button: QtWidgets.QAbstractButton) -> None:
    """Apply shared action styling and refresh dark-theme state on changes."""
    button.setStyleSheet(ACTION_BUTTON_STYLE)
    binding = _ActionButtonThemeBinding(button)
    cast(Any, button).__setattr__(_ACTION_BUTTON_BINDING_ATTR, binding)
    binding.apply()


class _ActionButtonThemeBinding(QtCore.QObject):
    """Keep one action button's theme selector property current."""

    def __init__(self, button: QtWidgets.QAbstractButton) -> None:
        super().__init__(button)
        self._button = button
        self._theme_probe = QtWidgets.QLabel(button.parentWidget())
        self._applying_style = False
        self._theme_probe.hide()
        button.destroyed.connect(self._theme_probe.deleteLater)
        button.installEventFilter(self)
        self._theme_probe.installEventFilter(self)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        """Refresh selector property after Qt theme or palette changes."""
        if not self._applying_style and watched in (self._button, self._theme_probe) and event.type() in {
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.StyleChange,
        }:
            self.apply()
        return False

    def apply(self) -> None:
        """Set dark-theme property from stylesheet-resolved visible text."""
        self._applying_style = True
        try:
            self._theme_probe.ensurePolished()
            visible_text = self._theme_probe.palette().color(self._theme_probe.foregroundRole())
        finally:
            self._applying_style = False
        is_dark = not _is_dark_color(visible_text)
        if self._button.property(_DARK_THEME_PROPERTY) == is_dark:
            return
        self._button.setProperty(_DARK_THEME_PROPERTY, is_dark)
        self._applying_style = True
        try:
            self._button.setStyleSheet(DARK_ACTION_BUTTON_STYLE if is_dark else ACTION_BUTTON_STYLE)
        finally:
            self._applying_style = False
