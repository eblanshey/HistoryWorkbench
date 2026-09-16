"""Module responsibility: Shared Qt view widget primitives and styling constants."""

from .buttons import make_dialog_button_box, make_icon_tool_button, make_row_action_button, make_tool_button
from .styles import (
    ACTION_BUTTON_STYLE,
    DIFF_ROW_CONTAINER_OBJECT_NAME,
    DIFF_ROW_LABEL_OBJECT_NAME,
    HEADER_ICON_BUTTON_STYLE,
    REPOSITORY_LABEL_EMPTY_STYLE,
    REPOSITORY_LABEL_LINK_STYLE,
    TREE_ITEM_HEIGHT,
    TREE_ITEM_ICON_SIZE,
    VISUAL_DIFF_ICON_BUTTON_STYLE,
)


__all__ = [
    "ACTION_BUTTON_STYLE",
    "DIFF_ROW_CONTAINER_OBJECT_NAME",
    "DIFF_ROW_LABEL_OBJECT_NAME",
    "HEADER_ICON_BUTTON_STYLE",
    "REPOSITORY_LABEL_EMPTY_STYLE",
    "REPOSITORY_LABEL_LINK_STYLE",
    "TREE_ITEM_HEIGHT",
    "TREE_ITEM_ICON_SIZE",
    "VISUAL_DIFF_ICON_BUTTON_STYLE",
    "make_dialog_button_box",
    "make_icon_tool_button",
    "make_row_action_button",
    "make_tool_button",
]
