# File responsibility: Unit tests for document-diff restore flow handler.

from __future__ import annotations

from typing import Literal
from unittest.mock import MagicMock

import pytest

from freecad.history_wb.application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.application.actions.git_workflow.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreScope,
    RestoreSource,
)
from freecad.history_wb.application.actions.result_models import Result
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.ui.presenters.document_diff.restore_handler import DocumentDiffRestoreHandler
from freecad.history_wb.ui.views.history.models import HistorySelection


def _make_handler() -> tuple[DocumentDiffRestoreHandler, MagicMock, MagicMock, MagicMock, MagicMock]:
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    get_committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    get_staged_paths = MagicMock(spec=GetStagedFilePathsAction)
    show_confirm = MagicMock(return_value=True)
    show_scope = MagicMock(return_value="listed_fcstd")
    show_info = MagicMock()
    show_error = MagicMock()
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        get_committed_paths,
        get_staged_paths,
        show_confirm,
        show_scope,
        show_info,
        show_error,
    )
    return handler, restore_documents, get_committed_paths, get_staged_paths, show_info


@pytest.mark.parametrize("item_kind", ["STAGING", "WORKING_TREE"])
def test_restore_document_builds_index_request(item_kind: Literal["STAGING", "WORKING_TREE"]) -> None:
    """Reviewed and Current Files restore the indexed version."""
    handler, restore_documents, _, _, show_info = _make_handler()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    restore_documents.execute.return_value = Result.success(True)

    succeeded = handler.restore_document(repo, HistorySelection(item_kind=item_kind, commit_hash=None), "doc.FCStd")

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
    restore_documents.execute.return_value = Result.success(True)
    show_confirm = MagicMock(return_value=confirmed)
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        MagicMock(spec=GetCommittedFilePathsAction),
        MagicMock(spec=GetStagedFilePathsAction),
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
    handler, restore_documents, get_committed_paths, _, _ = _make_handler()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    get_committed_paths.execute.return_value = Result.success(["a.FCStd", "b.FCStd"])
    restore_documents.execute.return_value = Result.success(True)

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


def test_restore_all_uses_staged_paths_for_staging_selection() -> None:
    """Bulk staging restore queries staged-file list."""
    handler, restore_documents, _, get_staged_paths, _ = _make_handler()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    get_staged_paths.execute.return_value = Result.success(["doc.FCStd"])
    restore_documents.execute.return_value = Result.success(True)

    handler.restore_all(repo, HistorySelection(item_kind="STAGING", commit_hash=None))

    get_staged_paths.execute.assert_called_once_with(repo)


@pytest.mark.parametrize("confirmed", [False, True])
def test_current_files_restore_all_confirms_and_restores_entire_index(confirmed: bool) -> None:
    """Current Files bulk restore skips scope selection and restores all indexed FCStd files."""
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    restore_documents.execute.return_value = Result.success(True)
    show_confirm = MagicMock(return_value=confirmed)
    show_scope = MagicMock()
    get_committed_paths = MagicMock(spec=GetCommittedFilePathsAction)
    get_staged_paths = MagicMock(spec=GetStagedFilePathsAction)
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        get_committed_paths,
        get_staged_paths,
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
    get_staged_paths.execute.assert_not_called()

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


def test_restore_failure_shows_error_message_and_returns_false() -> None:
    """Restore execution failure reports user-facing error through handler."""
    restore_documents = MagicMock(spec=RestoreDocumentsAction)
    restore_documents.execute.return_value = Result.failure("restore failed")
    show_error = MagicMock()
    handler = DocumentDiffRestoreHandler(
        restore_documents,
        MagicMock(spec=GetCommittedFilePathsAction),
        MagicMock(spec=GetStagedFilePathsAction),
        MagicMock(return_value=True),
        MagicMock(return_value="listed_fcstd"),
        MagicMock(),
        show_error,
    )
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")

    succeeded = handler.restore_document(repo, HistorySelection(item_kind="STAGING", commit_hash=None), "doc.FCStd")

    assert succeeded is False
    show_error.assert_called_once()
