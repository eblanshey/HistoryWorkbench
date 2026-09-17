"""File responsibility: Unit tests for PropertyDiffTreeWidget container behavior."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation
from freecad.history_wb.ui.views.property_diff.delegate import PropertyValueDelegate


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
    assert first_group.text(0) == "Base"
    assert second_group.text(0) == "Data"


def test_tree_keeps_double_click_edit_trigger(widget) -> None:  # type: ignore[no-untyped-def]
    """Container keeps double-click text-selection trigger."""
    triggers = widget.editTriggers()
    assert bool(triggers & QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)


def test_all_property_rows_keep_native_item_text(widget) -> None:  # type: ignore[no-untyped-def]
    """Changed and unchanged rows keep native item text for delegate painting."""
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
    assert group.text(0) == "Data"
    changed = group.child(0)
    unchanged = group.child(1)
    assert changed is not None
    assert unchanged is not None

    assert [changed.text(column) for column in range(3)] == ["Length", "10 mm", "20 mm"]
    assert [unchanged.text(column) for column in range(3)] == ["Label", "Pad", "Pad"]
    assert all(widget.itemWidget(changed, column) is None for column in range(3))
    assert all(widget.itemWidget(unchanged, column) is None for column in range(3))


def test_tree_uses_native_mouse_tracking_without_cell_stylesheet(widget) -> None:  # type: ignore[no-untyped-def]
    """Tree supplies native hover flags directly to delegate without widget QSS."""
    assert widget.hasMouseTracking()
    assert widget.styleSheet() == ""
