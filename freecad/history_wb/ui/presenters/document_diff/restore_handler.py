# File responsibility: Handle restore dialog flow and restore action orchestration.
"""Handle restore dialog flow and restore action orchestration."""

from collections.abc import Callable

from ....application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from ....application.actions.git_workflow.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreDocumentsSummary,
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
        show_restore_file_confirmation_dialog: Callable[[str, bool], bool],
        show_restore_scope_dialog: Callable[[], str | None],
        show_info_message: Callable[[str, str], None],
        show_error_message: Callable[[str, str], None],
    ) -> None:
        """Store action and dialog dependencies."""
        self._restore_documents = restore_documents_action
        self._get_committed_file_paths = get_committed_file_paths_action
        self._show_restore_file_confirmation_dialog = show_restore_file_confirmation_dialog
        self._show_restore_scope_dialog = show_restore_scope_dialog
        self._show_info_message = show_info_message
        self._show_error_message = show_error_message

    def restore_document(self, repo: GitRepository, selection: HistorySelection, git_path: str) -> bool:
        """Restore one document from index or selected commit."""

        # Reviewed is unstage-only; destructive operations require current files or a saved iteration.
        source, commit_hash = self._restore_source_from_selection(selection)

        if not self._show_restore_file_confirmation_dialog(git_path, selection.item_kind == "WORKING_TREE"):
            return False

        request = RestoreDocumentsRequest(
            repo=repo,
            source=source,
            scope=RestoreScope.SINGLE_PATH,
            commit_hash=commit_hash,
            paths=[git_path],
        )
        return self._execute_restore(request)

    def restore_all(self, repo: GitRepository, selection: HistorySelection) -> bool:
        """Restore all indexed files or selected scope from history."""

        # Validate the source before opening destructive-operation dialogs.
        source, commit_hash = self._restore_source_from_selection(selection)

        # Working-tree selection restores the complete index without a commit scope picker.
        if selection.item_kind == "WORKING_TREE":
            if not self._show_restore_file_confirmation_dialog("", True):
                return False
            return self._execute_restore(
                RestoreDocumentsRequest(repo=repo, source=RestoreSource.INDEX, scope=RestoreScope.ALL_FCSTD)
            )

        # The restore dialog provides the option to restore just the listed files with diffs, or all files
        # like a normal git checkout
        scope_text = self._show_restore_scope_dialog()
        if scope_text is None:
            return False

        if not self._show_restore_file_confirmation_dialog("", False):
            return False

        # The working-tree branch returned above; historical restore requires a commit.
        if commit_hash is None:
            raise RuntimeError("Missing commit for historical restore")

        listed_paths = self._listed_paths_for_commit(repo, commit_hash)
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

        # Saved iterations must identify a concrete commit.
        if selection.item_kind == "COMMIT" and selection.commit_hash:
            return RestoreSource.COMMIT, selection.commit_hash

        # Current Files discard recovers the index without changing reviewed content.
        if selection.item_kind == "WORKING_TREE":
            return RestoreSource.INDEX, None

        raise RuntimeError(f"Invalid restore selection: {selection}")

    def _listed_paths_for_commit(self, repo: GitRepository, commit_hash: str) -> list[str]:
        """Return visible FCStd paths for a saved iteration."""
        result = self._get_committed_file_paths.execute(repo, commit_hash)
        return result.data if result.is_success else []

    def _execute_restore(self, request: RestoreDocumentsRequest) -> bool:
        """Execute restore request and show user feedback."""
        result = self._restore_documents.execute(request)
        if not result.is_success:
            self._show_error_message(translate("History", "Restore"), result.message or "Restore failed")
            return False

        summary = result.data

        # Every successful restore carries concrete outcome metadata.
        if not isinstance(summary, RestoreDocumentsSummary):
            raise RuntimeError("Missing restore outcome summary")

        # Empty bulk index discard has no changes to refresh or refocus.
        if not summary.restored_paths:
            self._show_info_message(
                translate("History", "Restore"),
                translate("History", "No files to discard changes from."),
            )
            return False

        self._show_info_message(
            translate("History", "Restore"),
            translate("History", "Restoration complete."),
        )
        return True
