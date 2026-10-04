"""File responsibility: Unit tests for theme-aware action button surfaces."""

from __future__ import annotations

import pytest

from freecad.history_wb.qt import QtGui, QtWidgets
from freecad.history_wb.ui.views.theme.buttons import set_action_button_style
from freecad.history_wb.ui.views.widgets.buttons import make_row_action_button


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
    host.ensurePolished()
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


@pytest.mark.parametrize("text", ["#141414", "#f0f0f0"])
def test_review_action_icon_is_muted_when_disabled(application: QtWidgets.QApplication, text: str) -> None:
    """Shared row and summary review actions visibly mute icons when disabled."""
    host = QtWidgets.QWidget()
    host.setStyleSheet(f"QLabel {{ color: {text}; }}")
    host.ensurePolished()
    button = make_row_action_button(icon_name="Add.svg", accessible_name="Review", parent=host)
    enabled_image = button.icon().pixmap(button.iconSize(), QtGui.QIcon.Mode.Normal).toImage()

    button.setEnabled(False)
    disabled_image = button.icon().pixmap(button.iconSize(), QtGui.QIcon.Mode.Disabled).toImage()

    assert not disabled_image.isNull()
    assert disabled_image != enabled_image

    button.setEnabled(True)

    assert button.icon().pixmap(button.iconSize(), QtGui.QIcon.Mode.Normal).toImage() == enabled_image
