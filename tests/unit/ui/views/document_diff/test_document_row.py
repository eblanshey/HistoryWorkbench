"""File responsibility: Unit tests for document root-row action visibility and routing."""

from __future__ import annotations

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


def _button_texts(widget: DocumentDiffRowWidget) -> list[str]:
    """Return visible action-button texts from a document row."""
    return [button.text() for button in widget.findChildren(QtWidgets.QToolButton) if button.text()]


def test_working_tree_selection_shows_only_stage_button(application) -> None:  # type: ignore[no-untyped-def]
    """Current Files Area rows show only + Reviewed action."""
    row = DocumentDiffRowWidget(
        _diff(stage_button_enabled=False),
        "parts/A.FCStd",
        HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
    )

    assert _button_texts(row) == ["+ Reviewed"]
    stage_button = row.stage_button
    assert stage_button is not None
    assert not stage_button.isEnabled()
    assert "background-color: palette(button)" in stage_button.styleSheet()
    assert "color: palette(button-text)" in stage_button.styleSheet()


def test_staging_selection_shows_restore_and_remove(application) -> None:  # type: ignore[no-untyped-def]
    """Reviewed Area rows show Restore and Remove actions."""
    row = DocumentDiffRowWidget(
        _diff(),
        "parts/A.FCStd",
        HistorySelection(item_kind="STAGING", commit_hash=None),
    )

    assert _button_texts(row) == ["Restore", "Remove"]
    remove_button = row.remove_from_reviewed_button
    assert remove_button is not None
    assert "will not be saved in the next iteration" in remove_button.toolTip()


def test_commit_selection_shows_only_restore(application) -> None:  # type: ignore[no-untyped-def]
    """Commit-backed rows show Restore without reviewed-only actions."""
    row = DocumentDiffRowWidget(
        _diff(),
        "parts/A.FCStd",
        HistorySelection(item_kind="COMMIT", commit_hash="abc123"),
    )

    assert _button_texts(row) == ["Restore"]
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
