"""File responsibility: History panel facade composing repository header and history list."""

from datetime import datetime

from ....application.actions.result_models import SnapshotSummary
from ....domain.git.models import GitCommit, GitRepository
from ....qt import QtCore, QtWidgets
from ....utils import term, translate
from .formatters import format_snapshot_timestamp
from .history_list import HistoryList
from .history_row import create_commit_history_item, create_no_iterations_history_item, create_special_history_item
from .models import HistorySelection
from .repository_header import RepositoryHeader


__all__ = ["HistoryPanelWidget"]


class HistoryPanelWidget(QtWidgets.QWidget):
    """Left-column widget for repository header and history list."""

    refresh_requested = QtCore.Signal()
    save_iteration_requested = QtCore.Signal()
    history_selection_requested = QtCore.Signal(HistorySelection)
    history_selection_changed = QtCore.Signal(object)  # HistorySelection | None
    history_scroll_bottom_requested = QtCore.Signal()
    remove_all_from_reviewed_requested = QtCore.Signal()
    mark_all_reviewed_from_in_progress_requested = QtCore.Signal()
    restore_all_from_history_context_requested = QtCore.Signal(HistorySelection)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_selection: HistorySelection | None = None
        self._setup_ui()
        self._connect_internal_signals()

    def show_snapshots(self, snapshots: list[SnapshotSummary]) -> None:
        """Display list of available snapshots."""
        self._history_list.clear()

        sorted_snapshots = sorted(
            snapshots,
            key=lambda snapshot: datetime.fromisoformat(snapshot.created_at),
            reverse=True,
        )

        for snapshot in sorted_snapshots:
            display_text = f"{snapshot.name} - {format_snapshot_timestamp(snapshot.created_at)}"
            item = QtWidgets.QListWidgetItem(display_text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, snapshot.id)
            self._history_list.addItem(item)

    def show_commits(self, commits: list[GitCommit], show_special_items: bool = True) -> None:
        """Display git commits in history list and preserve valid prior selection."""
        previous_selection = self._current_selection
        self._history_list.clear()
        self._history_list.reset_bottom_scroll_arming()

        if show_special_items:
            self._add_special_items()

        if not show_special_items and not commits:
            no_iterations_text = term(
                translate("History", "No iterations to display."),
                translate("History", "No commits to display."),
            )
            item, widget = create_no_iterations_history_item(no_iterations_text)
            self._add_list_item(item, widget)
            self._restore_history_selection(previous_selection)
            return

        # Empty commit result with special items still needs selection reconciliation.
        if not commits:
            self._restore_history_selection(previous_selection)
            return

        self.append_commits(commits)
        self._restore_history_selection(previous_selection)

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Append commit entries after existing history rows."""
        for commit in commits:
            item, widget = create_commit_history_item(commit)
            self._add_list_item(item, widget)

    def show_repository(self, repo: GitRepository | None) -> None:
        """Display git repository info above history list."""
        self._repository_header.show_repository(repo)

    def _setup_ui(self) -> None:
        """Build repository header, placeholder label, and history list."""
        self._repository_header = RepositoryHeader(self)
        self._history_list = HistoryList(self)

        history_placeholder = QtWidgets.QLabel(
            term(translate("History", "Iterations"), translate("History", "Commits"))
        )
        history_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._repository_header)
        layout.addWidget(history_placeholder)
        layout.addWidget(self._history_list)

    def _connect_internal_signals(self) -> None:
        """Track effective history selection state from child list."""
        self._history_list.user_selection_requested.connect(self._on_user_history_selection_requested)
        self._history_list.effective_selection_changed.connect(self._on_effective_history_selection_changed)
        self._history_list.near_bottom_requested.connect(self._on_history_scroll_bottom_requested)
        self._history_list.remove_all_from_reviewed_requested.connect(self.remove_all_from_reviewed_requested.emit)
        self._history_list.mark_all_reviewed_from_in_progress_requested.connect(
            self.mark_all_reviewed_from_in_progress_requested.emit
        )
        self._history_list.restore_all_from_history_context_requested.connect(
            self.restore_all_from_history_context_requested.emit
        )
        self._repository_header.refresh_requested.connect(self._on_refresh_requested)
        self._repository_header.save_iteration_requested.connect(self._on_save_iteration_requested)

    def _on_user_history_selection_requested(self, selection: HistorySelection) -> None:
        """Forward user-driven history selection requests to facade callback."""
        self.history_selection_requested.emit(selection)

    def _on_effective_history_selection_changed(self, selection: HistorySelection | None) -> None:
        """Store and forward effective selection-state changes."""
        self._current_selection = selection
        self.history_selection_changed.emit(selection)

    def _on_history_scroll_bottom_requested(self) -> None:
        """Forward near-bottom history scrolling to facade callback."""
        self.history_scroll_bottom_requested.emit()

    def _on_refresh_requested(self) -> None:
        """Forward refresh button clicks to facade callback."""
        self.refresh_requested.emit()

    def _on_save_iteration_requested(self) -> None:
        """Forward save-iteration button clicks to facade callback."""
        self.save_iteration_requested.emit()

    def _add_special_items(self) -> None:
        """Insert Current Files Area and Reviewed Area pseudo-rows."""
        working_tree_item, working_tree_widget = create_special_history_item(
            term(translate("History", "Current Files Area"), translate("History", "Working Tree")),
            HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
        )
        self._add_list_item(working_tree_item, working_tree_widget)

        staging_item, staging_widget = create_special_history_item(
            term(translate("History", "Reviewed Area"), translate("History", "Staging Area")),
            HistorySelection(item_kind="STAGING", commit_hash=None),
        )
        self._add_list_item(staging_item, staging_widget)

    def _add_list_item(self, item: QtWidgets.QListWidgetItem, widget: QtWidgets.QWidget) -> None:
        """Add QListWidgetItem plus companion widget to rendered list."""
        self._history_list.addItem(item)
        self._history_list.setItemWidget(item, widget)
        item.setText("")
        item.setSizeHint(widget.sizeHint())

    def _restore_history_selection(self, previous_selection: HistorySelection | None) -> None:
        """Restore prior selection when item still exists after rebuild."""

        # Null prior selection means facade must propagate cleared state.
        if previous_selection is None:
            self._history_list.clear_effective_selection()
            return

        # Missing previous row means dependents must clear stale state.
        if not self._history_list.apply_effective_selection_if_present(previous_selection):
            self._history_list.clear_effective_selection()
            return

        # Restored selection must still notify presenter-facing selection path.
        self.history_selection_requested.emit(previous_selection)
