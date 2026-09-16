"""File responsibility: Selectable widget-backed cells for property diff rows."""

from __future__ import annotations

from ....domain.diff.models import DiffState
from ....qt import QtCore, QtGui, QtWidgets


__all__ = ["PropertyDiffCellWidget"]


class PropertyDiffCellWidget(QtWidgets.QLabel):
    """Render one property cell with copy and row-state behavior."""

    def __init__(
        self,
        tree: QtWidgets.QTreeWidget,
        item: QtWidgets.QTreeWidgetItem,
        text: str,
        state: DiffState,
        *,
        tooltip: str = "",
    ) -> None:
        super().__init__(text, tree)
        self._tree = tree
        self._item = item
        self.setObjectName("propertyDiffCell")
        self.setAccessibleName(text)
        self.setToolTip(tooltip)
        self.setProperty("diffState", state.name)
        self.setProperty("rowSelected", False)

        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        """Select backing tree item before starting text interaction."""
        self._tree.setCurrentItem(self._item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        """Select complete cell text on double-click for copying."""
        super().mouseDoubleClickEvent(event)
        self.setSelection(0, len(self.text()))

    def set_row_selected(self, selected: bool) -> None:
        """Apply synchronized tree selection state to this cell."""
        if self.property("rowSelected") == selected:
            return
        self.setProperty("rowSelected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
