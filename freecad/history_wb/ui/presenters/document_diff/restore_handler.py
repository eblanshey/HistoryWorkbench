# File responsibility: Handle restore dialog flow and restore action orchestration.
"""Handle restore dialog flow and restore action orchestration."""

from collections.abc import Callable

from ....application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from ....application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from ....application.actions.git_workflow.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreScope,
    RestoreSource,
)
from ....domain.git.models import GitRepository
from ....utils import translate
from ...views.history.models import HistorySelection


class DocumentDiffRestoreHandler:
    """Own single-file and bulk restore flows for presenter."""

    def __init__(
        self,
        restore_documents_action: RestoreDocumentsAction,
        get_committed_file_paths_action: GetCommittedFilePathsAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        show_restore_file_confirmation_dialog: Callable[[str, bool], bool],
        show_restore_scope_dialog: Callable[[], str | None],
        show_info_message: Callable[[str, str], None],
        show_error_message: Callable[[str, str], None],
    ) -> None:
        """Store action and dialog dependencies."""
        self._restore_documents = restore_documents_action
        self._get_committed_file_paths = get_committed_file_paths_action
        self._get_staged_file_paths = get_staged_file_paths_action
        self._show_restore_file_confirmation_dialog = show_restore_file_confirmation_dialog
        self._show_restore_scope_dialog = show_restore_scope_dialog
        self._show_info_message = show_info_message
        self._show_error_message = show_error_message

    def restore_document(self, repo: GitRepository, selection: HistorySelection, git_path: str) -> bool:
        """Restore one document from index or selected commit."""
        if selection.item_kind not in ("WORKING_TREE", "STAGING", "COMMIT"):
            return False

        if not self._show_restore_file_confirmation_dialog(git_path, selection.item_kind == "WORKING_TREE"):
            return False

        source, commit_hash = self._restore_source_from_selection(selection)
        request = RestoreDocumentsRequest(
            repo=repo,
            source=source,
            scope=RestoreScope.SINGLE_PATH,
            commit_hash=commit_hash,
            paths=[git_path],
        )
        return self._execute_restore(request)

    def restore_all(self, repo: GitRepository, selection: HistorySelection) -> bool:
        """Restore listed or all files for staging or commit selection."""
        if selection.item_kind not in ("STAGING", "COMMIT"):
            return False

        # The restore dialog provides the option to restore just the listed files with diffs, or all files
        # like a normal git checkout
        scope_text = self._show_restore_scope_dialog()
        if scope_text is None:
            return False

        if not self._show_restore_file_confirmation_dialog("", False):
            return False

        source, commit_hash = self._restore_source_from_selection(selection)
        listed_paths = self._listed_paths_for_selection(repo, selection)
        scope = RestoreScope.LISTED_FCSTD if scope_text == "listed_fcstd" else RestoreScope.ALL_FCSTD
        request = RestoreDocumentsRequest(
            repo=repo,
            source=source,
            scope=scope,
            commit_hash=commit_hash,
            paths=listed_paths,
        )
        return self._execute_restore(request)

    def _restore_source_from_selection(self, selection: HistorySelection) -> tuple[RestoreSource, str | None]:
        """Map history selection to restore source."""
        if selection.item_kind == "COMMIT":
            return RestoreSource.COMMIT, selection.commit_hash

        # Item kind STAGING and WORKING_TREE both restore from the index
        return RestoreSource.INDEX, None

    def _listed_paths_for_selection(self, repo: GitRepository, selection: HistorySelection) -> list[str]:
        """Return visible FCStd paths for selected restore source."""
        if selection.item_kind == "COMMIT" and selection.commit_hash:
            result = self._get_committed_file_paths.execute(repo, selection.commit_hash)
            return result.data if result.is_success else []

        result = self._get_staged_file_paths.execute(repo)
        return result.data if result.is_success else []

    def _execute_restore(self, request: RestoreDocumentsRequest) -> bool:
        """Execute restore request and show user feedback."""
        result = self._restore_documents.execute(request)
        if not result.is_success:
            self._show_error_message(translate("History", "Restore"), result.message or "Restore failed")
            return False

        self._show_info_message(
            translate("History", "Restore"),
            translate("History", "Restoration complete."),
        )
        return True
