"""File responsibility: Unit tests for document root-row action visibility and routing."""

from __future__ import annotations

from typing import cast

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import (
    DiffTreePresentation,
    WorkingTreeDocumentClosedIndicator,
)
from freecad.history_wb.ui.views.document_diff.document_row import DocumentDiffRowWidget
from freecad.history_wb.ui.views.history.models import HistorySelection


def _diff(*, indicators: list | None = None, stage_button_enabled: bool = False) -> DiffTreePresentation:
    """Build minimal document diff presentation for row tests."""
    return DiffTreePresentation(
        nodes=[],
        git_path="parts/A.FCStd",
        indicators=[] if indicators is None else indicators,
        document_state=DiffState.MODIFIED,
        stage_button_enabled=stage_button_enabled,
    )


def _action_buttons(widget: DocumentDiffRowWidget) -> list[QtWidgets.QToolButton]:
    """Return document-row action buttons in layout order."""
    return cast(list[QtWidgets.QToolButton], widget.findChildren(QtWidgets.QToolButton))


def test_working_tree_selection_shows_only_stage_button(application) -> None:  # type: ignore[no-untyped-def]
    """Current Files Area rows show only icon-based mark-reviewed action."""
    row = DocumentDiffRowWidget(
        _diff(stage_button_enabled=False),
        "parts/A.FCStd",
        HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
    )

    assert [button.accessibleName() for button in _action_buttons(row)] == ["Mark this document as reviewed"]
    stage_button = row.stage_button
    assert stage_button is not None
    assert stage_button.text() == ""
    assert not stage_button.icon().isNull()
    assert stage_button.toolTip() == "Mark this document as reviewed"
    assert stage_button.width() - stage_button.iconSize().width() >= 12
    assert stage_button.height() - stage_button.iconSize().height() >= 6
    assert not stage_button.isEnabled()
    assert stage_button.property("historyDarkTheme") is not None


def test_staging_selection_shows_restore_and_remove(application) -> None:  # type: ignore[no-untyped-def]
    """Reviewed Area rows show icon-based restore and remove actions."""
    row = DocumentDiffRowWidget(
        _diff(),
        "parts/A.FCStd",
        HistorySelection(item_kind="STAGING", commit_hash=None),
    )

    action_buttons = _action_buttons(row)
    assert [button.accessibleName() for button in action_buttons] == ["Restore", "Remove"]
    assert all(button.text() == "" and not button.icon().isNull() for button in action_buttons)
    remove_button = row.remove_from_reviewed_button
    assert remove_button is not None
    assert "will not be saved in the next iteration" in remove_button.toolTip()


def test_commit_selection_shows_only_restore(application) -> None:  # type: ignore[no-untyped-def]
    """Commit-backed rows show restore icon without reviewed-only actions."""
    row = DocumentDiffRowWidget(
        _diff(),
        "parts/A.FCStd",
        HistorySelection(item_kind="COMMIT", commit_hash="abc123"),
    )

    action_buttons = _action_buttons(row)
    assert [button.accessibleName() for button in action_buttons] == ["Restore"]
    assert action_buttons[0].text() == ""
    assert not action_buttons[0].icon().isNull()
    assert "Restore the selected file" in action_buttons[0].toolTip()
    assert row.stage_button is None
    assert row.remove_from_reviewed_button is None


def test_row_routes_stage_remove_restore_and_open_document(application) -> None:  # type: ignore[no-untyped-def]
    """Row signals route per-document actions through extracted child widgets."""
    captured: list[tuple[str, str]] = []
    row = DocumentDiffRowWidget(
        _diff(indicators=[WorkingTreeDocumentClosedIndicator()], stage_button_enabled=True),
        "parts/A.FCStd",
        HistorySelection(item_kind="STAGING", commit_hash=None),
    )
    row.restore_requested.connect(lambda git_path: captured.append(("restore", git_path)))
    row.remove_from_reviewed_requested.connect(lambda git_path: captured.append(("remove", git_path)))
    row.open_document_requested.connect(lambda git_path: captured.append(("open", git_path)))

    for button in row.findChildren(QtWidgets.QAbstractButton):
        button.click()

    assert captured == [
        ("open", "parts/A.FCStd"),
        ("restore", "parts/A.FCStd"),
        ("remove", "parts/A.FCStd"),
    ]


def test_document_row_renders_leading_document_icon(application) -> None:  # type: ignore[no-untyped-def]
    """Top-level document rows show FreeCAD's document icon before the label."""
    row = DocumentDiffRowWidget(
        _diff(),
        "parts/A.FCStd",
        HistorySelection(item_kind="COMMIT", commit_hash="abc123"),
    )

    icon_labels = [label for label in row.findChildren(QtWidgets.QLabel) if not label.pixmap().isNull()]

    assert len(icon_labels) == 1
    assert row.layout().itemAt(0).widget() is icon_labels[0]
