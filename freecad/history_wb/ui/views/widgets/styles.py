"""File responsibility: Shared Qt view styling and sizing constants."""

TREE_ITEM_HEIGHT = 22
TREE_ITEM_ICON_SIZE = 18
ROW_ACTION_ICON_SIZE = 14

ACTION_BUTTON_STYLE = """
QToolButton, QPushButton {
    padding: 0px 6px;
    margin: 0px;
    color: palette(button-text);
    background-color: palette(button);
    border: 1px solid palette(mid);
    border-radius: 3px;
}
QToolButton:hover, QPushButton:hover,
QToolButton:focus, QPushButton:focus {
    color: palette(highlighted-text);
    background-color: palette(highlight);
    border-color: palette(highlight);
}
QToolButton:pressed, QPushButton:pressed {
    color: palette(highlighted-text);
    background-color: palette(highlight);
    border: 2px inset palette(dark);
}
QToolButton:disabled, QPushButton:disabled {
    color: palette(mid);
    background-color: palette(window);
    border-color: palette(mid);
}
"""

DARK_ACTION_BUTTON_STYLE = """
QToolButton, QPushButton {
    padding: 0px 6px;
    margin: 0px;
    color: #e6e6e6;
    background-color: rgba(255, 255, 255, 48);
    border: 1px solid rgba(255, 255, 255, 110);
    border-radius: 3px;
}
QToolButton:hover, QPushButton:hover,
QToolButton:focus, QPushButton:focus {
    color: palette(highlighted-text);
    background-color: palette(highlight);
    border-color: palette(highlight);
}
QToolButton:pressed, QPushButton:pressed {
    color: palette(highlighted-text);
    background-color: palette(highlight);
    border: 2px inset palette(dark);
}
QToolButton:disabled, QPushButton:disabled {
    color: #8f969b;
    background-color: rgba(255, 255, 255, 24);
    border-color: rgba(255, 255, 255, 55);
}
"""
HEADER_ICON_BUTTON_STYLE = "QToolButton { padding: 2px; }"

VISUAL_DIFF_ICON_BUTTON_STYLE = """
QToolButton,
QToolButton:disabled {
    padding: 0px;
    margin: 0px;
    background-color: transparent;
    border: none;
}
QToolButton:hover,
QToolButton:focus {
    background-color: palette(highlight);
    border: 1px solid palette(highlighted-text);
    border-radius: 3px;
}
QToolButton:pressed {
    background-color: palette(highlight);
    border: 2px inset palette(highlighted-text);
    border-radius: 3px;
}
"""

DIFF_ROW_CONTAINER_OBJECT_NAME = "diffRowContainer"
DIFF_ROW_LABEL_OBJECT_NAME = "diffRowLabel"

REPOSITORY_LABEL_EMPTY_STYLE = "font-size: 11px; color: gray; font-style: italic;"
REPOSITORY_LABEL_LINK_STYLE = "font-size: 11px; font-weight: bold; text-decoration: underline;"
