"""File responsibility: Shared Qt button factory helpers for view widgets."""

from __future__ import annotations

from collections.abc import Callable

from ....qt import QtCore, QtGui, QtWidgets
from ..theme.buttons import set_action_button_style
from ..theme.icons import set_themed_icon
from .styles import (
    ACTION_BUTTON_STYLE,
    HEADER_ICON_BUTTON_STYLE,
    ROW_ACTION_ICON_SIZE,
    TREE_ITEM_HEIGHT,
    TREE_ITEM_ICON_SIZE,
)


def make_tool_button(
    *,
    text: str = "",
    tooltip: str = "",
    icon: QtGui.QIcon | None = None,
    icon_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    style: str = "",
    auto_raise: bool = False,
    accessible_name: str = "",
    icon_size: QtCore.QSize | None = None,
    tool_button_style: QtCore.Qt.ToolButtonStyle = QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly,
    parent: QtWidgets.QWidget | None = None,
) -> QtWidgets.QToolButton:
    """Create configured QToolButton for History Workbench views."""
    button = QtWidgets.QToolButton(parent)
    button.setText(text)
    button.setToolTip(tooltip)
    button.setToolButtonStyle(tool_button_style)
    button.setAutoRaise(auto_raise)

    if accessible_name:
        button.setAccessibleName(accessible_name)

    if icon is not None:
        button.setIcon(icon)

    if icon_name is not None:
        set_themed_icon(button, icon_name)

    if icon_size is not None:
        button.setIconSize(icon_size)

    if style:
        _apply_button_style(button, style)

    if width is not None and height is not None:
        button.setFixedSize(width, height)
    elif width is not None:
        button.setFixedWidth(width)
    elif height is not None:
        button.setFixedHeight(height)

    return button


def _apply_button_style(button: QtWidgets.QAbstractButton, style: str) -> None:
    """Apply static styling or bind theme-aware action styling."""
    if style == ACTION_BUTTON_STYLE:
        set_action_button_style(button)
        return
    button.setStyleSheet(style)


def make_row_action_button(
    *,
    icon_name: str,
    tooltip: str = "",
    accessible_name: str,
    width: int | None = None,
    on_clicked: Callable[[], None] | None = None,
    parent: QtWidgets.QWidget | None = None,
) -> QtWidgets.QToolButton:
    """Create icon-only row action button matching diff tree rows."""
    button = make_tool_button(
        tooltip=tooltip,
        icon_name=icon_name,
        width=width,
        height=TREE_ITEM_HEIGHT,
        style=ACTION_BUTTON_STYLE,
        accessible_name=accessible_name,
        icon_size=QtCore.QSize(ROW_ACTION_ICON_SIZE, ROW_ACTION_ICON_SIZE),
        tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
        parent=parent,
    )

    if on_clicked is not None:
        button.clicked.connect(lambda checked=False: on_clicked())

    return button


def make_icon_tool_button(
    *,
    icon_name: str,
    tooltip: str,
    accessible_name: str,
    size: int,
    on_clicked: Callable[[], None] | None = None,
    style: str = HEADER_ICON_BUTTON_STYLE,
    auto_raise: bool = False,
) -> QtWidgets.QToolButton:
    """Create square icon-only tool button with themed icon."""
    button = make_tool_button(
        tooltip=tooltip,
        icon_name=icon_name,
        width=size,
        height=size,
        style=style,
        auto_raise=auto_raise,
        accessible_name=accessible_name,
        icon_size=QtCore.QSize(TREE_ITEM_ICON_SIZE, TREE_ITEM_ICON_SIZE),
        tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
    )

    if on_clicked is not None:
        button.clicked.connect(lambda checked=False: on_clicked())

    return button


def make_dialog_button_box(*, accept_text: str, reject_text: str) -> QtWidgets.QDialogButtonBox:
    """Create dialog button box with explicit translated button labels."""
    button_box = QtWidgets.QDialogButtonBox()
    accept_button = button_box.addButton(accept_text, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
    reject_button = button_box.addButton(reject_text, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
    accept_button.setAutoDefault(True)
    reject_button.setAutoDefault(False)
    return button_box
