"""File responsibility: Unit tests for theme-aware action button surfaces."""

from __future__ import annotations

import pytest

from freecad.history_wb.qt import QtGui, QtWidgets
from freecad.history_wb.ui.views.theme.buttons import set_action_button_style


def _palette(background: QtGui.QColor, text: QtGui.QColor) -> QtGui.QPalette:
    """Build palette with consistent theme detection roles."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Base, background)
    palette.setColor(QtGui.QPalette.ColorRole.Window, background)
    palette.setColor(QtGui.QPalette.ColorRole.Text, text)
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    return palette


@pytest.mark.parametrize(
    ("background", "text", "expected_dark"),
    [
        (QtGui.QColor(25, 25, 25), QtGui.QColor(240, 240, 240), True),
        (QtGui.QColor(245, 245, 245), QtGui.QColor(20, 20, 20), False),
    ],
)
def test_action_button_selects_surface_for_theme(
    application: QtWidgets.QApplication,
    background: QtGui.QColor,
    text: QtGui.QColor,
    expected_dark: bool,
) -> None:
    """Dark themes select subdued overlay while light themes retain palette button color."""
    host = QtWidgets.QWidget()
    host.setStyleSheet(f"QLabel {{ color: {text.name()}; }}")
    button = QtWidgets.QToolButton(host)
    button.setPalette(_palette(background, text))

    set_action_button_style(button)

    assert button.property("historyDarkTheme") is expected_dark
    if expected_dark:
        assert "background-color: rgba(255, 255, 255, 48)" in button.styleSheet()
        assert "background-color: rgba(255, 255, 255, 24)" in button.styleSheet()
    else:
        assert "background-color: palette(button)" in button.styleSheet()


def test_disabled_button_keeps_dark_surface(application: QtWidgets.QApplication) -> None:
    """Disabled palette changes do not switch dark button back to light styling."""
    host = QtWidgets.QWidget()
    host.setStyleSheet("QLabel { color: #f0f0f0; }")
    button = QtWidgets.QToolButton(host)
    set_action_button_style(button)

    button.setEnabled(False)

    assert button.property("historyDarkTheme") is True
    assert "background-color: rgba(255, 255, 255, 24)" in button.styleSheet()
