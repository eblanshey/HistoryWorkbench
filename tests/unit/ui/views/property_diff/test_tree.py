"""File responsibility: Unit tests for PropertyDiffTreeWidget container behavior."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtGui, QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation
from freecad.history_wb.ui.views.property_diff.cell import PropertyDiffCellWidget
from freecad.history_wb.ui.views.property_diff.delegate import PropertyValueDelegate
from freecad.history_wb.ui.views.property_diff.tree import PropertyDiffTreeWidget


def test_widget_has_three_columns(widget) -> None:  # type: ignore[no-untyped-def]
    """Property diff tree keeps 3-column layout."""
    assert widget.columnCount() == 3


def test_header_labels_are_correct(widget) -> None:  # type: ignore[no-untyped-def]
    """Property diff tree exposes expected translated headers."""
    assert widget.headerItem().text(0) == "Property"
    assert widget.headerItem().text(1) == "Old Value"
    assert widget.headerItem().text(2) == "New Value"


def test_widget_uses_selectable_read_only_delegate(widget) -> None:  # type: ignore[no-untyped-def]
    """Property diff tree wires extracted delegate as item delegate."""
    assert isinstance(widget.itemDelegate(), PropertyValueDelegate)


def test_empty_property_list_clears_tree(widget) -> None:  # type: ignore[no-untyped-def]
    """show_property_diff clears existing rows when given empty input."""
    widget.show_property_diff([PropertyPresentation(name="Length", state=DiffState.MODIFIED)])
    assert widget.topLevelItemCount() == 1

    widget.show_property_diff([])

    assert widget.topLevelItemCount() == 0


def test_clear_property_diff_removes_existing_rows(widget) -> None:  # type: ignore[no-untyped-def]
    """Explicit clear entry point removes rendered property rows."""
    widget.show_property_diff([PropertyPresentation(name="Length", state=DiffState.MODIFIED)])

    widget.clear_property_diff()

    assert widget.topLevelItemCount() == 0


def test_show_property_diff_renders_group_rows(widget) -> None:  # type: ignore[no-untyped-def]
    """Container renders grouped top-level items via extracted builders."""
    widget.show_property_diff(
        [
            PropertyPresentation(name="Length", state=DiffState.MODIFIED, group="Base"),
            PropertyPresentation(name="Width", state=DiffState.MODIFIED, group="Data"),
        ]
    )

    assert widget.topLevelItemCount() == 2
    first_group = widget.topLevelItem(0)
    second_group = widget.topLevelItem(1)
    assert first_group is not None
    assert second_group is not None
    first_label = widget.itemWidget(first_group, 0)
    second_label = widget.itemWidget(second_group, 0)
    assert isinstance(first_label, QtWidgets.QLabel)
    assert isinstance(second_label, QtWidgets.QLabel)
    assert first_label.text() == "Base"
    assert second_label.text() == "Data"


def test_tree_keeps_double_click_edit_trigger(widget) -> None:  # type: ignore[no-untyped-def]
    """Container keeps double-click text-selection trigger."""
    triggers = widget.editTriggers()
    assert bool(triggers & QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)


def test_all_property_rows_use_widget_cells(widget) -> None:  # type: ignore[no-untyped-def]
    """Changed and unchanged rows use selectable widget-backed cells."""
    widget.show_property_diff(
        [
            PropertyPresentation(
                name="Length",
                state=DiffState.MODIFIED,
                old_value="10 mm",
                new_value="20 mm",
                group="Data",
            ),
            PropertyPresentation(
                name="Label",
                state=DiffState.UNCHANGED,
                old_value="Pad",
                new_value="Pad",
                group="Data",
            ),
        ]
    )

    group = widget.topLevelItem(0)
    assert group is not None
    group_label = widget.itemWidget(group, 0)
    assert isinstance(group_label, QtWidgets.QLabel)
    assert group_label.text() == "Data"
    assert group.text(0) == ""
    changed = group.child(0)
    unchanged = group.child(1)
    assert changed is not None
    assert unchanged is not None

    changed_cells = [widget.itemWidget(changed, column) for column in range(3)]
    assert all(isinstance(cell, PropertyDiffCellWidget) for cell in changed_cells)
    assert [cell.text() for cell in changed_cells if isinstance(cell, PropertyDiffCellWidget)] == [
        "Length",
        "10 mm",
        "20 mm",
    ]
    unchanged_cells = [widget.itemWidget(unchanged, column) for column in range(3)]
    assert all(isinstance(cell, PropertyDiffCellWidget) for cell in unchanged_cells)
    assert [cell.text() for cell in unchanged_cells if isinstance(cell, PropertyDiffCellWidget)] == [
        "Label",
        "Pad",
        "Pad",
    ]
    assert [unchanged.text(column) for column in range(3)] == ["", "", ""]


def test_changed_row_supports_hover_and_synchronizes_selection_across_cells(widget) -> None:  # type: ignore[no-untyped-def]
    """Widget-backed property cells expose hover and shared row selection styles."""
    widget.show_property_diff([PropertyPresentation(name="Length", state=DiffState.MODIFIED)])

    group = widget.topLevelItem(0)
    assert group is not None
    item = group.child(0)
    assert item is not None
    cells = [widget.itemWidget(item, column) for column in range(3)]
    assert all(isinstance(cell, PropertyDiffCellWidget) for cell in cells)
    typed_cells = [cell for cell in cells if isinstance(cell, PropertyDiffCellWidget)]

    widget.setCurrentItem(item)

    assert "QLabel#propertyDiffCell" in widget.styleSheet()
    assert "QTreeWidget#propertyDiffTree::item { border: none; border-radius: 0px; }" in widget.styleSheet()
    assert "border: none; border-radius: 0px" in widget.styleSheet()
    assert all(cell.styleSheet() == "" for cell in typed_cells)
    assert all(cell.property("rowSelected") is True for cell in typed_cells)


def test_tree_refreshes_shared_diff_style_when_palette_changes(application) -> None:  # type: ignore[no-untyped-def]
    """One tree-level stylesheet recomputes all semantic colors after theme changes."""
    host = QtWidgets.QWidget()
    host.setStyleSheet("QLabel { color: #f0f0f0; }")
    widget = PropertyDiffTreeWidget(host)
    light_style = widget.styleSheet()
    dark_palette = QtGui.QPalette(widget.palette())
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(30, 30, 30))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(20, 20, 20))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(240, 240, 240))

    widget.setPalette(dark_palette)

    assert widget.styleSheet() != light_style


def test_light_qss_foreground_keeps_pastel_diff_colors(application) -> None:  # type: ignore[no-untyped-def]
    """QSS-resolved dark text prevents stale palette roles from selecting dark accents."""
    host = QtWidgets.QWidget()
    host.setStyleSheet("QLabel { color: #000000; } QTreeWidget { background-color: #eeeeee; }")
    tree = PropertyDiffTreeWidget(host)
    stale_palette = QtGui.QPalette(tree.palette())
    stale_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(30, 30, 30))
    stale_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(20, 20, 20))
    stale_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(240, 240, 240))

    tree.setPalette(stale_palette)

    assert "background-color: #c8ffc8" in tree.styleSheet()
