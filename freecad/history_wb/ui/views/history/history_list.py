"""File responsibility: History list widget, selection routing, context menus, and scroll-bottom detection."""

from typing import cast

from ....qt import QtCore, QtGui, QtWidgets
from ....utils import term, translate
from .models import HistorySelection


class HistoryList(QtWidgets.QListWidget):
    """Own history-list interactions and row-local behavior."""

    # Emitted only for direct user clicks on selectable history rows.
    user_selection_requested = QtCore.Signal(HistorySelection)

    # Emitted for every effective selection-state change, including
    # user clicks, restored selections, and cleared invalid selections.
    effective_selection_changed = QtCore.Signal(object)  # HistorySelection | None

    near_bottom_requested = QtCore.Signal()
    remove_all_from_reviewed_requested = QtCore.Signal()
    mark_all_reviewed_from_in_progress_requested = QtCore.Signal()
    restore_all_from_history_context_requested = QtCore.Signal(HistorySelection)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._history_scroll_bottom_armed = True
        self._setup_ui()

    def reset_bottom_scroll_arming(self) -> None:
        """Re-arm near-bottom detection after history rebuild."""
        self._history_scroll_bottom_armed = True

    def apply_effective_selection_if_present(self, selection: HistorySelection) -> bool:
        """Apply matching selection from current rows and emit effective state."""
        for row in range(self.count()):
            item = self.item(row)
            if item is None:
                continue

            item_data = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if item_data == selection:
                self.setCurrentItem(item)
                self.effective_selection_changed.emit(selection)
                return True

        return False

    def clear_effective_selection(self) -> None:
        """Clear current selection and emit null effective-selection state."""
        self.clearSelection()
        self.setCurrentRow(-1)
        self.effective_selection_changed.emit(None)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Ignore right-click presses so context menu does not alter selection."""

        # Right-click should act on hovered row, not replace current selection.
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            event.accept()
            return

        super().mousePressEvent(event)

    def _setup_ui(self) -> None:
        """Configure list behavior and connect internal signals."""
        self.setMinimumWidth(150)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setWordWrap(True)
        self.setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu_requested)
        self.itemClicked.connect(self._on_item_clicked)
        self.verticalScrollBar().valueChanged.connect(self._on_scrollbar_value_changed)

    def _on_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        """Route clicked history row through state and user-intent signals."""
        item_data = item.data(QtCore.Qt.ItemDataRole.UserRole)

        # Placeholder rows without HistorySelection are not selectable state.
        if isinstance(item_data, HistorySelection):
            self.effective_selection_changed.emit(item_data)

            # Cross-column views must update effective selection state before
            # presenter-driven reload callbacks render dependent widgets.
            self.user_selection_requested.emit(item_data)

    def _on_context_menu_requested(self, pos: QtCore.QPoint) -> None:
        """Route context menus for pseudo-rows and commits."""
        item = self.itemAt(pos)
        if item is None:
            return

        item_data = item.data(QtCore.Qt.ItemDataRole.UserRole)

        # Placeholder rows without selection model have no context actions.
        if not isinstance(item_data, HistorySelection):
            return

        if self._is_working_tree_selection(item_data):
            self._show_working_tree_context_menu(pos)
            return

        if self._is_staging_selection(item_data):
            self._show_reviewed_context_menu(pos, item_data)
            return

        if item_data.item_kind == "COMMIT" and item_data.commit_hash:
            self._show_commit_context_menu(pos, item_data)

    def _on_scrollbar_value_changed(self, value: int) -> None:
        """Emit near-bottom signal once per bottom-entry until re-armed."""
        scrollbar = self.verticalScrollBar()
        maximum = scrollbar.maximum()

        # Non-scrollable list cannot reach a bottom threshold.
        if maximum <= 0:
            return

        # Moving back above threshold rearms infinite-scroll trigger.
        if value <= int(maximum * 0.7):
            self._history_scroll_bottom_armed = True

        # Fire once in bottom band until user scrolls away again.
        if self._history_scroll_bottom_armed and value >= int(maximum * 0.85):
            self._history_scroll_bottom_armed = False
            self.near_bottom_requested.emit()

    def _is_working_tree_selection(self, selection: HistorySelection) -> bool:
        """Return whether selection points to Current Files Area pseudo-row."""
        return selection.item_kind == "WORKING_TREE" and selection.commit_hash is None

    def _is_staging_selection(self, selection: HistorySelection) -> bool:
        """Return whether selection points to Reviewed Area pseudo-row."""
        return selection.item_kind == "STAGING" and selection.commit_hash is None

    def _show_working_tree_context_menu(self, pos: QtCore.QPoint) -> None:
        """Show Current Files Area bulk-review context action."""
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)
        action = menu.addAction(
            term(translate("History", "Mark All Files Reviewed"), translate("History", "Mark All Files Staged"))
        )
        selected_action = menu.exec(self.mapToGlobal(pos))

        if selected_action == action:
            self.mark_all_reviewed_from_in_progress_requested.emit()

    def _show_reviewed_context_menu(self, pos: QtCore.QPoint, selection: HistorySelection) -> None:
        """Show Reviewed Area context menu actions."""
        tooltip = term(
            translate(
                "History",
                "Remove document(s) from Reviewed. The current file(s) stay unchanged "
                "and will not be saved in the next iteration until reviewed again.",
            ),
            translate(
                "History",
                "Remove document(s) from Staged. The current file(s) stay unchanged "
                "and will not be saved in the next commit until staged again.",
            ),
        )
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)
        action = menu.addAction(
            term(
                translate("History", "Remove All Files From Reviewed"),
                translate("History", "Remove All Files From Staged"),
            )
        )
        restore_action = menu.addAction(
            term(translate("History", "Restore All Reviewed Files"), translate("History", "Restore All Staged Files"))
        )
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        selected_action = menu.exec(self.mapToGlobal(pos))

        if selected_action == restore_action:
            self.restore_all_from_history_context_requested.emit(selection)

        if selected_action == action:
            self.remove_all_from_reviewed_requested.emit()

    def _show_commit_context_menu(self, pos: QtCore.QPoint, selection: HistorySelection) -> None:
        """Show commit-row context actions."""
        menu = QtWidgets.QMenu(self)
        restore_action = menu.addAction(
            term(
                translate("History", "Restore All Files From Iteration"),
                translate("History", "Restore All Files From Commit"),
            )
        )
        copy_id_action = menu.addAction(
            term(
                translate("History", "Copy Iteration ID to Clipboard"),
                translate("History", "Copy Commit ID to Clipboard"),
            )
        )
        selected_action = menu.exec(self.mapToGlobal(pos))

        if selected_action == restore_action:
            self.restore_all_from_history_context_requested.emit(selection)

        if selected_action == copy_id_action and selection.commit_hash:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app = cast(QtWidgets.QApplication, app)
                app.clipboard().setText(selection.commit_hash)
