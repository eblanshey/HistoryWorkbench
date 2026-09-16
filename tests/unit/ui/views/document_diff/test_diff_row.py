"""File responsibility: Unit tests for shared document-tree row rendering."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.views.document_diff.diff_row import DiffTreeRowWidget
from freecad.history_wb.ui.views.widgets.styles import TREE_ITEM_HEIGHT


def test_diff_row_renders_label_and_trailing_widget(application) -> None:  # type: ignore[no-untyped-def]
    """Shared row renders text, tooltip, and caller-provided trailing content."""
    row = DiffTreeRowWidget("Pad", tooltip="PartDesign::Pad")
    action = QtWidgets.QToolButton()
    row.add_trailing_widget(action)

    label = row.findChild(QtWidgets.QLabel)

    assert label is not None
    assert label.text() == "Pad"
    assert label.toolTip() == "PartDesign::Pad"
    assert row.accessibleName() == "Pad"
    assert action in row.findChildren(QtWidgets.QToolButton)


def test_diff_row_expands_to_theme_item_geometry(application) -> None:  # type: ignore[no-untyped-def]
    """Row background can fill item geometry made taller by application QSS."""
    row = DiffTreeRowWidget("Pad")

    row.resize(200, TREE_ITEM_HEIGHT + 8)

    assert row.minimumHeight() == TREE_ITEM_HEIGHT
    assert row.height() == TREE_ITEM_HEIGHT + 8


def test_diff_row_exposes_diff_and_selection_state_for_shared_tree_style(application) -> None:  # type: ignore[no-untyped-def]
    """Shared row exposes semantic properties without installing a local stylesheet."""
    row = DiffTreeRowWidget("Pad")
    row.set_diff_state(DiffState.MODIFIED)

    row.set_selected(True)

    assert row.property("diffState") == "MODIFIED"
    assert row.property("rowSelected") is True
    assert row.styleSheet() == ""


def test_unchanged_row_keeps_theme_native_label_without_local_style(application) -> None:  # type: ignore[no-untyped-def]
    """Unchanged row leaves foreground selection to application QLabel theme rules."""
    row = DiffTreeRowWidget("Body")
    row.set_selected(True)

    label = row.findChild(QtWidgets.QLabel)
    assert label is not None
    assert label.text() == "Body"
    assert not label.isHidden()
    assert row.styleSheet() == ""
