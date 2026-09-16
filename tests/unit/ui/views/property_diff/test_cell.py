"""File responsibility: Unit tests for highlighted property diff cell interaction."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtCore, QtGui, QtWidgets
from freecad.history_wb.ui.views.property_diff.cell import PropertyDiffCellWidget


def test_property_cell_is_mouse_selectable_and_selects_backing_item(application) -> None:  # type: ignore[no-untyped-def]
    """Highlighted cell keeps copy behavior and routes selection to its tree item."""
    tree = QtWidgets.QTreeWidget()
    item = QtWidgets.QTreeWidgetItem([""])
    tree.addTopLevelItem(item)
    cell = PropertyDiffCellWidget(
        tree,
        item,
        "20 mm",
        DiffState.MODIFIED,
    )
    local_position = QtCore.QPointF(1, 1)
    global_position = QtCore.QPointF(cell.mapToGlobal(QtCore.QPoint(1, 1)))
    event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress,
        local_position,
        local_position,
        global_position,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )

    cell.mousePressEvent(event)
    cell.setSelection(0, len(cell.text()))

    assert tree.currentItem() is item
    assert cell.selectedText() == "20 mm"
    assert cell.accessibleName() == "20 mm"


def test_property_cell_exposes_diff_state_for_shared_tree_style(application) -> None:  # type: ignore[no-untyped-def]
    """Highlighted cells expose semantic state without installing local stylesheets."""
    tree = QtWidgets.QTreeWidget()
    item = QtWidgets.QTreeWidgetItem([""])
    tree.addTopLevelItem(item)
    cell = PropertyDiffCellWidget(tree, item, "20 mm", DiffState.MODIFIED)

    assert cell.property("diffState") == "MODIFIED"
    assert cell.styleSheet() == ""
