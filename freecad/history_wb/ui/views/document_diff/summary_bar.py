"""File responsibility: Summary bar widget for document diff counts and bulk actions."""

from __future__ import annotations

from ....qt import QtCore, QtGui, QtWidgets
from ....resources import get_icon_path
from ....utils import translate
from ..widgets.buttons import make_row_action_button
from .summary_state import SummaryButtonState, SummaryCounts


SUMMARY_ACTION_BUTTON_WIDTH = 30
_ICON_SIZE = 16


class DocumentDiffSummaryBar(QtWidgets.QWidget):
    """Render document counts and bulk document action buttons."""

    stage_all_requested = QtCore.Signal()
    restore_all_requested = QtCore.Signal()
    remove_all_requested = QtCore.Signal()

    def __init__(self, remove_reviewed_tooltip: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._remove_reviewed_tooltip = remove_reviewed_tooltip
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._summary_layout = QtWidgets.QHBoxLayout()
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(8)

        modified_container, self._modified_count_label = self._create_summary_section(
            "SummaryModified.svg", translate("History", "Modified file count")
        )
        added_container, self._added_count_label = self._create_summary_section(
            "SummaryAdded.svg", translate("History", "Added file count")
        )
        deleted_container, self._deleted_count_label = self._create_summary_section(
            "SummaryDeleted.svg", translate("History", "Deleted file count")
        )

        self._summary_layout.addWidget(modified_container)
        self._summary_layout.addWidget(added_container)
        self._summary_layout.addWidget(deleted_container)
        self._summary_layout.addStretch()

        layout.addLayout(self._summary_layout)
        self._action_layout = QtWidgets.QHBoxLayout()
        self._action_layout.setContentsMargins(0, 0, 0, 0)
        self._action_layout.setSpacing(4)

        mark_all_reviewed_text = translate("History", "Mark All Reviewed")
        self._stage_all_button = make_row_action_button(
            icon_name="Add.svg",
            tooltip=mark_all_reviewed_text,
            accessible_name=mark_all_reviewed_text,
            width=SUMMARY_ACTION_BUTTON_WIDTH,
            parent=self,
        )
        self._stage_all_button.setObjectName("documentDiffStageAllButton")
        self._stage_all_button.hide()
        self._stage_all_button.clicked.connect(self.stage_all_requested.emit)
        self._action_layout.addWidget(self._stage_all_button)

        self._restore_all_button = make_row_action_button(
            icon_name="Restore.svg",
            tooltip=translate(
                "History",
                "Choose which files to restore from the selected iteration.\n"
                "Current files on disk can be overwritten or removed.\n"
                "Saved history will not be affected.",
            ),
            accessible_name=translate("History", "Restore All"),
            width=SUMMARY_ACTION_BUTTON_WIDTH,
            parent=self,
        )
        self._restore_all_button.setObjectName("documentDiffRestoreAllButton")
        self._restore_all_button.hide()
        self._restore_all_button.clicked.connect(self.restore_all_requested.emit)
        self._action_layout.addWidget(self._restore_all_button)

        self._remove_all_button = make_row_action_button(
            icon_name="Remove.svg",
            tooltip=self._remove_reviewed_tooltip,
            accessible_name=translate("History", "Remove All"),
            width=SUMMARY_ACTION_BUTTON_WIDTH,
            parent=self,
        )
        self._remove_all_button.setObjectName("documentDiffRemoveAllButton")
        self._remove_all_button.hide()
        self._remove_all_button.clicked.connect(self.remove_all_requested.emit)
        self._action_layout.addWidget(self._remove_all_button)
        layout.addLayout(self._action_layout)

    def _create_summary_section(self, icon_name: str, tooltip: str) -> tuple[QtWidgets.QWidget, QtWidgets.QLabel]:
        """Create an icon+count section with a shared tooltip.

        Returns the container widget and the count label.
        """
        container = QtWidgets.QWidget()
        container.setToolTip(tooltip)

        section_layout = QtWidgets.QHBoxLayout(container)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(4)

        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(QtGui.QIcon(str(get_icon_path(icon_name))).pixmap(_ICON_SIZE, _ICON_SIZE))
        section_layout.addWidget(icon_label)

        count_label = QtWidgets.QLabel("0")
        count_label.setStyleSheet("font-weight: bold;")
        section_layout.addWidget(count_label)

        return container, count_label

    def set_summary_counts(self, counts: SummaryCounts) -> None:
        """Display per-status document counts."""
        self._modified_count_label.setText(str(counts.modified_docs))
        self._deleted_count_label.setText(str(counts.deleted_docs))
        self._added_count_label.setText(str(counts.added_docs))

    def set_button_states(self, state: SummaryButtonState) -> None:
        """Apply visibility and enabled state for all bulk action buttons."""
        self._stage_all_button.setVisible(state.stage_all_visible)
        self._stage_all_button.setEnabled(state.stage_all_enabled)
        self._remove_all_button.setVisible(state.remove_all_visible)
        self._remove_all_button.setEnabled(state.remove_all_enabled)
        self._restore_all_button.setVisible(state.restore_all_visible)
        self._restore_all_button.setEnabled(state.restore_all_enabled)
