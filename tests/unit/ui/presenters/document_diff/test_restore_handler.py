# File responsibility: Unit tests for document-diff restore flow handler.

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from freecad.history_wb.application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.application.actions.git_workflow.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreDocumentsSummary,
    RestoreScope,
    RestoreSource,
)
from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.ui.presenters.document_diff.restore_handler import DocumentDiffRestoreHandler
from freecad.history_wb.ui.views.history.models import HistorySelection


def _make_handler() -> tuple[DocumentDiffRestoreHandler, MagicMock, MagicMock, MagicMock]:
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    get_committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    show_confirm = MagicMock(return_value=True)
    show_scope = MagicMock(return_value="listed_fcstd")
    show_info = MagicMock()
    show_error = MagicMock()
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        get_committed_paths,
        show_confirm,
        show_scope,
        show_info,
        show_error,
    )
    return handler, restore_documents, get_committed_paths, show_info


def test_discard_document_builds_index_request() -> None:
    """Current Files discard restores the indexed version."""
    handler, restore_documents, _, show_info = _make_handler()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    restore_documents.execute.return_value = Result.success(RestoreDocumentsSummary(["doc.FCStd"], 0))

    succeeded = handler.restore_document(repo, HistorySelection("WORKING_TREE", None), "doc.FCStd")

    assert succeeded is True
    restore_documents.execute.assert_called_once_with(
        RestoreDocumentsRequest(
            repo=repo,
            source=RestoreSource.INDEX,
            scope=RestoreScope.SINGLE_PATH,
            commit_hash=None,
            paths=["doc.FCStd"],
        )
    )
    show_info.assert_called_once()


@pytest.mark.parametrize("confirmed", [False, True])
def test_current_files_restore_confirms_index_source_before_execution(confirmed: bool) -> None:
    """Working-tree confirmation identifies index source and cancellation leaves files untouched."""
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    restore_documents.execute.return_value = Result.success(RestoreDocumentsSummary(["doc.FCStd"], 0))
    show_confirm = MagicMock(return_value=confirmed)
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        MagicMock(spec=GetCommittedFilePathsAction),
        show_confirm,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")

    assert handler.restore_document(repo, HistorySelection("WORKING_TREE", None), "doc.FCStd") is confirmed
    show_confirm.assert_called_once_with("doc.FCStd", True)
    assert restore_documents.execute.call_count == int(confirmed)


def test_restore_all_uses_committed_paths_for_commit_selection() -> None:
    """Bulk commit restore queries committed-file list and builds commit request."""
    handler, restore_documents, get_committed_paths, _ = _make_handler()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    get_committed_paths.execute.return_value = Result.success(["a.FCStd", "b.FCStd"])
    restore_documents.execute.return_value = Result.success(RestoreDocumentsSummary(["a.FCStd", "b.FCStd"], 0))

    succeeded = handler.restore_all(repo, HistorySelection(item_kind="COMMIT", commit_hash="abc123"))

    assert succeeded is True
    get_committed_paths.execute.assert_called_once_with(repo, "abc123")
    restore_documents.execute.assert_called_once_with(
        RestoreDocumentsRequest(
            repo=repo,
            source=RestoreSource.COMMIT,
            scope=RestoreScope.LISTED_FCSTD,
            commit_hash="abc123",
            paths=["a.FCStd", "b.FCStd"],
        )
    )


@pytest.mark.parametrize("confirmed", [False, True])
def test_current_files_restore_all_confirms_and_restores_entire_index(confirmed: bool) -> None:
    """Current Files bulk restore skips scope selection and restores all indexed FCStd files."""
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    restore_documents.execute.return_value = Result.success(RestoreDocumentsSummary(["doc.FCStd"], 0))
    show_confirm = MagicMock(return_value=confirmed)
    show_scope = MagicMock()
    get_committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        get_committed_paths,
        show_confirm,
        show_scope,
        MagicMock(),
        MagicMock(),
    )
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")

    assert handler.restore_all(repo, HistorySelection("WORKING_TREE", None)) is confirmed

    show_confirm.assert_called_once_with("", True)
    show_scope.assert_not_called()
    get_committed_paths.execute.assert_not_called()

    # Confirmation is the only gate before issuing the all-files index request.
    if confirmed:
        restore_documents.execute.assert_called_once_with(
            RestoreDocumentsRequest(
                repo=repo,
                source=RestoreSource.INDEX,
                scope=RestoreScope.ALL_FCSTD,
                commit_hash=None,
                paths=None,
            )
        )
    else:
        restore_documents.execute.assert_not_called()


@pytest.mark.parametrize(
    ("bulk", "message"),
    [(False, "restore failed"), (True, "No files available to restore from selected source")],
)
def test_restore_failure_shows_error_message_and_returns_false(bulk: bool, message: str) -> None:
    """Restore execution failure reports user-facing error through handler."""
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    restore_documents.execute.return_value = Result.failure(message)
    show_error = MagicMock()
    show_info = MagicMock()
    get_committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    get_committed_paths.execute.return_value = Result.success(["doc.FCStd"])
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        get_committed_paths,
        MagicMock(return_value=True),
        MagicMock(return_value="listed_fcstd"),
        show_info,
        show_error,
    )
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")

    selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")

    # Both historical entry points retain failure feedback from the action.
    if bulk:
        succeeded = handler.restore_all(repo, selection)
    else:
        succeeded = handler.restore_document(repo, selection, "doc.FCStd")

    assert succeeded is False
    show_error.assert_called_once_with("Restore", message)
    show_info.assert_not_called()


def test_empty_index_discard_shows_info_after_confirmation_without_history_query() -> None:
    """Empty bulk discard reports a normal no-op rather than an error or completed restore."""
    restore = MagicMock(spec=RestoreDocumentsAction)
    restore.execute.return_value = Result.success(RestoreDocumentsSummary([], 0))
    committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    confirm = MagicMock(return_value=True)
    scope = MagicMock()
    info = MagicMock()
    error = MagicMock()
    handler = DocumentDiffRestoreHandler(restore, committed_paths, confirm, scope, info, error)
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")

    assert handler.restore_all(repo, HistorySelection("WORKING_TREE", None)) is False

    confirm.assert_called_once_with("", True)
    info.assert_called_once_with("Restore", "No files to discard changes from.")
    error.assert_not_called()
    committed_paths.execute.assert_not_called()
    scope.assert_not_called()
