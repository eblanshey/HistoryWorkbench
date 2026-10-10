"""File responsibility: Document diff panel facade wiring summary, tree, document rows, and signals."""

from __future__ import annotations

from ....qt import QtCore, QtWidgets
from ...presenters.presentation_models import DiffTreePresentation
from ..history.models import HistorySelection
from .document_row import REMOVE_REVIEWED_TOOLTIP, DocumentDiffRowWidget
from .summary_bar import DocumentDiffSummaryBar
from .summary_state import SummaryButtonState, SummaryCounts
from .tree import DocumentDiffTree


__all__ = ["DocumentDiffTreeWidget"]


class DocumentDiffTreeWidget(QtWidgets.QWidget):
    """Middle-column widget that renders document/node diffs and staging actions."""

    add_requested = QtCore.Signal(str)  # git_path
    stage_all_requested = QtCore.Signal()
    remove_all_requested = QtCore.Signal()
    restore_requested = QtCore.Signal(str)  # git_path
    restore_all_requested = QtCore.Signal()
    discard_requested = QtCore.Signal(str)  # git_path
    discard_all_requested = QtCore.Signal()
    remove_from_reviewed_requested = QtCore.Signal(str)  # git_path
    node_selection_requested = QtCore.Signal(str, str)  # git_path, node_path
    visual_diff_requested = QtCore.Signal(str, str)  # git_path, node_path
    open_document_for_comparison_requested = QtCore.Signal(str)  # git_path

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_selection: HistorySelection | None = None
        self._stage_buttons: dict[str, QtWidgets.QToolButton] = {}
        self._remove_from_reviewed_buttons: dict[str, QtWidgets.QToolButton] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._summary_bar = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP, self)
        self._summary_bar.stage_all_requested.connect(self._on_stage_all_clicked)
        self._summary_bar.restore_all_requested.connect(self._on_restore_all_clicked)
        self._summary_bar.discard_all_requested.connect(self.discard_all_requested.emit)
        self._summary_bar.remove_all_requested.connect(self._on_remove_all_clicked)
        self._tree = DocumentDiffTree(self)
        self._tree.node_selected.connect(self._on_tree_node_selected)
        self._tree.visual_diff_requested.connect(self._on_tree_visual_diff_requested)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._summary_bar)
        layout.addWidget(self._tree)

    def set_current_history_selection(self, selection: HistorySelection | None) -> None:
        """Set current history selection for conditional Current Files Area controls."""
        self._current_selection = selection

    def collapse_all_tree_items(self) -> None:
        """Collapse every document and node row in the tree."""
        self._tree.collapse_all_tree_items()

    def set_button_states(self, state: SummaryButtonState) -> None:
        """Apply visibility and enabled state for all bulk action buttons."""
        self._summary_bar.set_button_states(state)

    def set_summary_counts(self, counts: SummaryCounts) -> None:
        """Display per-status document counts."""
        self._summary_bar.set_summary_counts(counts)

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget."""
        self._tree.clear()
        self._stage_buttons.clear()
        self._remove_from_reviewed_buttons.clear()

        # Empty document lists mean presenter wants a cleared middle column.
        if not diffs:
            return

        self._tree.show_doc_diffs(diffs, self._create_doc_row_widget)

    def _create_doc_row_widget(self, diff: DiffTreePresentation, top_level_text: str) -> DocumentDiffRowWidget:
        """Create top-level row widget for one document diff."""
        container = DocumentDiffRowWidget(diff, top_level_text, self._current_selection, self)
        container.stage_requested.connect(self.add_requested.emit)
        container.remove_from_reviewed_requested.connect(self.remove_from_reviewed_requested.emit)
        container.restore_requested.connect(self.restore_requested.emit)
        container.discard_requested.connect(self.discard_requested.emit)
        container.open_document_requested.connect(self.open_document_for_comparison_requested.emit)

        if diff.git_path and container.stage_button is not None:
            self._stage_buttons[diff.git_path] = container.stage_button

        if diff.git_path and container.remove_from_reviewed_button is not None:
            self._remove_from_reviewed_buttons[diff.git_path] = container.remove_from_reviewed_button

        return container

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls."""
        self._tree.clear()
        self.set_summary_counts(SummaryCounts())
        self.set_button_states(SummaryButtonState.hidden())
        self._stage_buttons.clear()
        self._remove_from_reviewed_buttons.clear()

    def _on_stage_all_clicked(self) -> None:
        """Forward Stage All button click through facade signal."""
        self.stage_all_requested.emit()

    def _on_remove_all_clicked(self) -> None:
        """Forward Remove All button click through facade signal."""
        self.remove_all_requested.emit()

    def _on_restore_all_clicked(self) -> None:
        """Forward Restore All button click through facade signal."""
        self.restore_all_requested.emit()

    def _on_tree_node_selected(self, git_path: str, node_path: str) -> None:
        """Forward child-tree node selection through facade signal."""
        self.node_selection_requested.emit(git_path, node_path)

    def _on_tree_visual_diff_requested(self, git_path: str, node_path: str) -> None:
        """Forward child-tree visual diff request through facade signal."""
        self.visual_diff_requested.emit(git_path, node_path)

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse the root tree item for the given git_path."""
        self._tree.collapse_tree_item(git_path)

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Enable or disable the + Reviewed button for a given git_path."""
        if git_path in self._stage_buttons:
            self._stage_buttons[git_path].setEnabled(enabled)
