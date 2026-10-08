"""File responsibility: Narrow fake UI views for presenter tests."""

from __future__ import annotations

from typing import Any

from freecad.history_wb.domain.git.models import GitCommit, GitRepository
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation, PropertyPresentation
from freecad.history_wb.ui.views.diff_panel.dialogs import GitConfigDialogResult
from freecad.history_wb.ui.views.document_diff.summary_state import SummaryButtonState, SummaryCounts


class _CallRecorder:
    """Collect view method calls for observable presenter assertions."""

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs: Any) -> None:
        self._calls.append({"method": method, **kwargs})

    def get_calls(self) -> list[dict[str, Any]]:
        """Return all recorded calls."""
        return self._calls.copy()


class FakeHistoryView(_CallRecorder):
    """Fake history-column view for repository presenter tests."""

    def show_repository(self, repo: GitRepository | None) -> None:
        """Capture repository display call."""
        self._record_call("show_repository", repo=repo)

    def show_commits(self, commits: list[GitCommit], show_special_items: bool = True) -> None:
        """Capture history list replacement call."""
        self._record_call("show_commits", commits=commits, show_special_items=show_special_items)

    def append_commits(self, commits: list[GitCommit]) -> None:
        """Capture appended commit rows."""
        self._record_call("append_commits", commits=commits)


class FakeDocumentDiffView(_CallRecorder):
    """Fake document-diff view for diff presenter tests."""

    def show_doc_diffs(self, diff_trees: list[DiffTreePresentation]) -> None:
        """Capture document diff presentation call."""
        self._record_call("show_doc_diffs", diff_trees=diff_trees)

    def clear_doc_diffs(self) -> None:
        """Capture document-diff clear call."""
        self._record_call("clear_doc_diffs")

    def set_summary_counts(self, counts: SummaryCounts) -> None:
        """Capture summary counts display call."""
        self._record_call(
            "set_summary_counts",
            counts=counts,
        )

    def set_button_states(self, state: SummaryButtonState) -> None:
        """Capture button states update."""
        self._record_call("set_button_states", state=state)

    def collapse_tree_item(self, git_path: str) -> None:
        """Capture tree collapse request."""
        self._record_call("collapse_tree_item", git_path=git_path)

    def set_stage_button_enabled(self, git_path: str, enabled: bool) -> None:
        """Capture per-document stage-button state update."""
        self._record_call("set_stage_button_enabled", git_path=git_path, enabled=enabled)


class FakePropertyDiffView(_CallRecorder):
    """Fake property-diff view for diff presenter tests."""

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Capture property presentation call."""
        self._record_call("show_property_diff", properties=properties)

    def clear_property_diff(self) -> None:
        """Capture property clear call."""
        self._record_call("clear_property_diff")


class FakeDialogView(_CallRecorder):
    """Fake dialog view for presenter tests that need modal feedback."""

    def __init__(self) -> None:
        super().__init__()
        self.save_iteration_dialog_result: str | None = None
        self.configure_author_dialog_result: GitConfigDialogResult | None = None
        self.restore_file_confirmation_result = True
        self.restore_scope_result: str | None = "listed_fcstd"

    def show_warning_message(self, title: str, message: str) -> None:
        """Capture warning dialog call."""
        self._record_call("show_warning_message", title=title, message=message)

    def show_info_message(self, title: str, message: str) -> None:
        """Capture info dialog call."""
        self._record_call("show_info_message", title=title, message=message)

    def show_error_message(self, title: str, message: str) -> None:
        """Capture error dialog call."""
        self._record_call("show_error_message", title=title, message=message)

    def show_save_iteration_dialog(self) -> str | None:
        """Capture save-iteration dialog request."""
        self._record_call("show_save_iteration_dialog")
        return self.save_iteration_dialog_result

    def show_configure_author_dialog(
        self,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Capture configure-author dialog request."""
        self._record_call(
            "show_configure_author_dialog",
            message=message,
            initial_values=initial_values,
            global_config_writable=global_config_writable,
        )
        return self.configure_author_dialog_result

    def show_restore_file_confirmation_dialog(self, git_path: str, use_index_wording: bool) -> bool:
        """Capture restore confirmation dialog request."""
        self._record_call(
            "show_restore_file_confirmation_dialog", git_path=git_path, use_index_wording=use_index_wording
        )
        return self.restore_file_confirmation_result

    def show_restore_scope_dialog(self) -> str | None:
        """Capture restore scope dialog request."""
        self._record_call("show_restore_scope_dialog")
        return self.restore_scope_result
