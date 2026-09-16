"""File responsibility: Shared widget-backed row shell for document diff trees."""

from __future__ import annotations

from ....domain.diff.models import DiffState
from ....qt import QtGui, QtWidgets
from ..widgets.styles import DIFF_ROW_CONTAINER_OBJECT_NAME, DIFF_ROW_LABEL_OBJECT_NAME, TREE_ITEM_HEIGHT


__all__ = ["DiffTreeRowWidget"]


class DiffTreeRowWidget(QtWidgets.QWidget):
    """Render one document-tree row with shared semantic and interaction styling."""

    def __init__(
        self,
        text: str,
        *,
        tooltip: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = DiffState.UNCHANGED
        self._setup_ui(text, tooltip)

    def _setup_ui(self, text: str, tooltip: str) -> None:
        """Create shared label and trailing-content layout."""
        self.setObjectName(DIFF_ROW_CONTAINER_OBJECT_NAME)
        self.setAccessibleName(text)
        self.setProperty("diffState", DiffState.UNCHANGED.name)
        self.setProperty("rowSelected", False)
        self.setMinimumHeight(TREE_ITEM_HEIGHT)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(4, 0, 4, 0)
        self._layout.setSpacing(4)

        self._label = QtWidgets.QLabel(text, self)
        self._label.setObjectName(DIFF_ROW_LABEL_OBJECT_NAME)
        self._label.setAccessibleName(text)
        self._label.setToolTip(tooltip)
        self._layout.addWidget(self._label)
        self._layout.addStretch()

    def add_trailing_widget(self, widget: QtWidgets.QWidget) -> None:
        """Append status or action content after row label."""
        self._layout.addWidget(widget)

    def set_diff_state(self, state: DiffState) -> None:
        """Expose semantic state for the document tree's shared stylesheet."""
        self._state = state
        self.setProperty("diffState", state.name)

    def set_selected(self, selected: bool) -> None:
        """Expose current-item state and repolish this row only."""
        if self.property("rowSelected") == selected:
            return
        self.setProperty("rowSelected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Paint the stylesheet background for this custom QWidget subclass."""
        del event
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        painter = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_Widget, option, painter, self)
