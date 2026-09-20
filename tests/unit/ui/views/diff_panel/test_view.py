"""File responsibility: Unit tests for HistoryPanelView cross-column coordination behavior."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation
from freecad.history_wb.ui.views.diff_panel.view import HistoryPanelView
from freecad.history_wb.ui.views.document_diff.panel import DocumentDiffTreeWidget
from freecad.history_wb.ui.views.history.panel import HistoryPanelWidget


def test_history_click_updates_document_row_buttons_on_first_click() -> None:
    """History selection updates document-row action buttons before diff render callback runs."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    panel = HistoryPanelView()
    history_panel = panel.findChild(HistoryPanelWidget)
    document_tree = panel.findChild(DocumentDiffTreeWidget)
    assert history_panel is not None
    assert document_tree is not None

    history_panel.show_commits([])
    history_panel.history_selection_requested.connect(
        lambda _selection: document_tree.show_doc_diffs([_sample_diff_tree()])
    )

    history_panel._history_list.itemClicked.emit(history_panel._history_list.item(1))
    assert _document_row_button_accessible_names(document_tree) == ["Restore", "Remove"]

    history_panel._history_list.itemClicked.emit(history_panel._history_list.item(0))
    assert _document_row_button_accessible_names(document_tree) == ["Mark this document as reviewed"]


def _sample_diff_tree() -> DiffTreePresentation:
    """Build minimal document diff presentation for button-state tests."""
    return DiffTreePresentation(nodes=[], git_path="parts/A.FCStd", indicators=[], document_state=DiffState.MODIFIED)


def _document_row_button_accessible_names(widget: DocumentDiffTreeWidget) -> list[str]:
    """Return action-button accessible names from first document row."""
    tree_widget = widget.findChild(QtWidgets.QTreeWidget, "documentDiffTree")
    assert tree_widget is not None
    root_item = tree_widget.topLevelItem(0)
    assert root_item is not None
    row_widget = tree_widget.itemWidget(root_item, 0)
    assert row_widget is not None
    return [button.accessibleName() for button in row_widget.findChildren(QtWidgets.QToolButton)]
