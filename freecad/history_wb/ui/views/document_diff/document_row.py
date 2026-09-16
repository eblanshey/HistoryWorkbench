"""File responsibility: Document root-row widget with status indicators and per-document actions."""

from __future__ import annotations

from functools import partial

from ....qt import QtCore, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import DiffTreePresentation
from ..history.models import HistorySelection
from ..widgets.buttons import make_row_action_button
from .diff_row import DiffTreeRowWidget
from .status_indicators import DocumentStatusIndicatorsWidget


STAGE_BUTTON_WIDTH = 90
REMOVE_BUTTON_WIDTH = 90
RESTORE_BUTTON_WIDTH = 90
REMOVE_REVIEWED_TOOLTIP = translate(
    "History",
    "Remove document(s) from Reviewed.\n"
    "The current file(s) stay unchanged.\n"
    "They will not be saved in the next iteration until reviewed again.",
)


class DocumentDiffRowWidget(DiffTreeRowWidget):
    """Render one document row and emit per-document action requests."""

    stage_requested = QtCore.Signal(str)  # git_path
    remove_from_reviewed_requested = QtCore.Signal(str)  # git_path
    restore_requested = QtCore.Signal(str)  # git_path
    open_document_requested = QtCore.Signal(str)  # git_path

    def __init__(
        self,
        diff: DiffTreePresentation,
        top_level_text: str,
        current_selection: HistorySelection | None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        self._diff = diff
        self._top_level_text = top_level_text
        self._current_selection = current_selection
        self._stage_button: QtWidgets.QToolButton | None = None
        self._remove_from_reviewed_button: QtWidgets.QToolButton | None = None
        super().__init__(top_level_text, parent=parent)
        self._setup_actions()

    @property
    def stage_button(self) -> QtWidgets.QToolButton | None:
        """Return + Reviewed button when rendered for current selection."""
        return self._stage_button

    @property
    def remove_from_reviewed_button(self) -> QtWidgets.QToolButton | None:
        """Return Remove button when rendered for current selection."""
        return self._remove_from_reviewed_button

    def _setup_actions(self) -> None:
        """Add document-specific statuses and actions to shared row shell."""
        status_widget = DocumentStatusIndicatorsWidget(self._diff.indicators, self._diff.git_path, self)
        status_widget.open_document_requested.connect(self.open_document_requested.emit)
        self.add_trailing_widget(status_widget)

        # Reviewed and commit selections expose restore button
        if self._is_staging_selected() or self._is_commit_selected():
            self._add_restore_button()

        # Only working tree rows can be marked reviewed.
        if self._is_working_tree_selected():
            self._add_stage_button()

        # Only reviewed rows can be removed from reviewed staging set.
        if self._is_staging_selected():
            self._add_remove_from_reviewed_button()

    def _is_working_tree_selected(self) -> bool:
        """Return True when Current Files Area history row selected."""
        return self._current_selection is not None and self._current_selection.item_kind == "WORKING_TREE"

    def _is_staging_selected(self) -> bool:
        """Return True when Reviewed Area history row selected."""
        return self._current_selection is not None and self._current_selection.item_kind == "STAGING"

    def _is_commit_selected(self) -> bool:
        """Return True when commit history row selected."""
        return self._current_selection is not None and self._current_selection.item_kind == "COMMIT"

    def _add_stage_button(self) -> None:
        """Add + Reviewed button for one working-tree document row."""
        self._stage_button = make_row_action_button(
            text=translate("History", "+ Reviewed"),
            width=STAGE_BUTTON_WIDTH,
            on_clicked=partial(self.stage_requested.emit, self._diff.git_path),
        )
        self._stage_button.setEnabled(self._diff.stage_button_enabled)
        self.add_trailing_widget(self._stage_button)

    def _add_remove_from_reviewed_button(self) -> None:
        """Add Remove button for one reviewed document row."""
        self._remove_from_reviewed_button = make_row_action_button(
            text=translate("History", "Remove"),
            tooltip=REMOVE_REVIEWED_TOOLTIP,
            width=REMOVE_BUTTON_WIDTH,
            on_clicked=partial(self.remove_from_reviewed_requested.emit, self._diff.git_path),
        )
        self.add_trailing_widget(self._remove_from_reviewed_button)

    def _add_restore_button(self) -> None:
        """Add Restore button for reviewed or commit-backed document rows."""
        tooltip = translate(
            "History",
            "Restore the selected file.\n"
            "This overwrites %1 on disk with a copy of the file as it was saved in the selected iteration.\n"
            "THE CURRENT FILE WILL BE OVERWRITTEN BY THIS OPERATION.\n"
            "Saved history will not be affected.",
        ).replace("%1", self._top_level_text)
        restore_button = make_row_action_button(
            text=translate("History", "Restore"),
            tooltip=tooltip,
            width=RESTORE_BUTTON_WIDTH,
            on_clicked=partial(self.restore_requested.emit, self._diff.git_path),
        )
        self.add_trailing_widget(restore_button)
