"""File responsibility: Visual-diff node row widget with icon button and request signal."""

from __future__ import annotations

from ....qt import QtCore, QtGui, QtWidgets
from ....resources import get_icon_path
from ....utils import term, translate
from ..widgets.buttons import make_tool_button
from ..widgets.styles import (
    DIFF_ROW_CONTAINER_OBJECT_NAME,
    DIFF_ROW_LABEL_OBJECT_NAME,
    TREE_ITEM_HEIGHT,
    TREE_ITEM_ICON_SIZE,
    VISUAL_DIFF_ICON_BUTTON_STYLE,
)


__all__ = ["NodeDiffRowWidget"]


class NodeDiffRowWidget(QtWidgets.QWidget):
    """Render one tree-node row with visual-diff action."""

    visual_diff_requested = QtCore.Signal(str, str)  # git_path, node_path

    def __init__(
        self,
        text: str,
        type_id: str,
        git_path: str,
        node_path: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._type_id = type_id
        self._git_path = git_path
        self._node_path = node_path
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName(DIFF_ROW_CONTAINER_OBJECT_NAME)
        self.setFixedHeight(TREE_ITEM_HEIGHT)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        label = QtWidgets.QLabel(self._text)
        label.setObjectName(DIFF_ROW_LABEL_OBJECT_NAME)
        label.setFixedHeight(TREE_ITEM_HEIGHT)
        label.setToolTip(self._type_id)
        layout.addWidget(label)
        layout.addStretch()

        icon_size = QtCore.QSize(TREE_ITEM_ICON_SIZE, TREE_ITEM_ICON_SIZE)
        button = make_tool_button(
            tooltip=term(translate("History", "Open 3D comparison"), translate("History", "Open 3D diff")),
            icon=QtGui.QIcon(str(get_icon_path("VisualDiff.svg"))),
            width=TREE_ITEM_HEIGHT,
            height=TREE_ITEM_HEIGHT,
            style=VISUAL_DIFF_ICON_BUTTON_STYLE,
            auto_raise=True,
            icon_size=icon_size,
            tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
        )
        button.clicked.connect(lambda checked=False: self.visual_diff_requested.emit(self._git_path, self._node_path))
        layout.addWidget(button)
