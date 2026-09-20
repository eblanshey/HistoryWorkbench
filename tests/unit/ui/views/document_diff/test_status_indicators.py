"""File responsibility: Unit tests for document diff status indicator rendering and actions."""

from __future__ import annotations

from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import (
    OldSnapshotMissingIndicator,
    WorkingTreeDocumentClosedIndicator,
)
from freecad.history_wb.ui.views.document_diff.status_indicators import DocumentStatusIndicatorsWidget


def test_non_interactive_indicator_renders_icon_label(application) -> None:  # type: ignore[no-untyped-def]
    """Passive indicators render as QLabel icons with translated tooltips."""
    widget = DocumentStatusIndicatorsWidget([OldSnapshotMissingIndicator()], "parts/A.FCStd")

    labels = widget.findChildren(QtWidgets.QLabel)

    assert len(labels) == 1
    assert "previous snapshot" in labels[0].toolTip()


def test_open_document_indicator_emits_git_path(application) -> None:  # type: ignore[no-untyped-def]
    """Closed working-tree indicator renders button and emits open request."""
    widget = DocumentStatusIndicatorsWidget([WorkingTreeDocumentClosedIndicator()], "parts/A.FCStd")
    captured: list[str] = []
    widget.open_document_requested.connect(captured.append)

    buttons = widget.findChildren(QtWidgets.QPushButton)
    assert len(buttons) == 1

    buttons[0].click()

    assert buttons[0].text() == "Open"
    assert "generate a comparison" in buttons[0].toolTip()
    assert buttons[0].property("historyDarkTheme") is not None
    assert captured == ["parts/A.FCStd"]
