"""File responsibility: Shared Qt view styling and sizing constants."""

TREE_ITEM_HEIGHT = 22
TREE_ITEM_ICON_SIZE = 18

ROW_ACTION_BUTTON_STYLE = """
QToolButton {
    padding: 0px 4px;
    margin: 0px;
    border: 1px solid rgba(128, 128, 128, 120);
    border-radius: 2px;
    background-color: rgba(128, 128, 128, 28);
}
QToolButton:hover {
    border-color: rgba(128, 128, 128, 170);
    background-color: rgba(128, 128, 128, 48);
}
QToolButton:pressed {
    border-color: rgba(128, 128, 128, 190);
    background-color: rgba(128, 128, 128, 70);
}
QToolButton:disabled {
    color: rgba(128, 128, 128, 140);
    border-color: rgba(128, 128, 128, 60);
    background-color: rgba(128, 128, 128, 12);
}
"""
HEADER_ICON_BUTTON_STYLE = "QToolButton { padding: 2px; }"

VISUAL_DIFF_ICON_BUTTON_STYLE = """
QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 3px;
}
QToolButton:hover {
    background-color: rgba(128, 128, 128, 35);
}
QToolButton:pressed {
    background-color: rgba(128, 128, 128, 60);
}
"""

DIFF_ROW_CONTAINER_OBJECT_NAME = "diffRowContainer"
DIFF_ROW_LABEL_OBJECT_NAME = "diffRowLabel"

REPOSITORY_LABEL_EMPTY_STYLE = "font-size: 11px; color: gray; font-style: italic;"
REPOSITORY_LABEL_LINK_STYLE = "font-size: 11px; font-weight: bold; text-decoration: underline;"
