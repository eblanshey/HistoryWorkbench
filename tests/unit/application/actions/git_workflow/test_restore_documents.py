# File responsibility: Unit tests for restore_documents action orchestration and restore scopes.
"""Unit tests for RestoreDocumentsAction."""

from unittest.mock import patch

import pytest

from freecad.history_wb.application.actions.git_workflow.restore_documents import (
    RestoreDocumentsAction,
    RestoreDocumentsRequest,
    RestoreDocumentsSummary,
    RestoreScope,
    RestoreSource,
)
from freecad.history_wb.domain.git import GitRepository, GitService
from tests.fakes import FakeFreeCadPort, FakeGitPort, MockDocument


def test_all_fcstd_scope_uses_union_of_source_and_current_saved_paths() -> None:
    fake_git_port = FakeGitPort()
    fake_git_port.set_all_fcstd_paths("/repo", "abc123", ["a.FCStd"])
    fake_git_port.set_current_saved_fcstd_paths("/repo", ["b.FCStd"])
    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=FakeFreeCadPort())
    repo = GitRepository(name="repo", absolute_path="/repo")

    result = action.execute(
        RestoreDocumentsRequest(
            repo=repo,
            source=RestoreSource.COMMIT,
            scope=RestoreScope.ALL_FCSTD,
            commit_hash="abc123",
        )
    )

    assert result.is_success is True
    assert fake_git_port.get_last_restore_call() == ("/repo", "abc123", ["a.FCStd", "b.FCStd"])


def test_single_restore_closes_project_docs_reopens_and_restores_active_doc() -> None:
    active_doc = MockDocument("/repo/a.FCStd", name="DocA")
    other_project_doc = MockDocument("/repo/b.FCStd", name="DocB")
    outside_doc = MockDocument("/outside/x.FCStd", name="Outside")
    freecad_port = FakeFreeCadPort(
        active_document=active_doc, open_documents=[active_doc, other_project_doc, outside_doc]
    )

    fake_git_port = FakeGitPort()
    fake_git_port.set_file_contents("abc123", "a.FCStd", "exists")
    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=freecad_port)
    repo = GitRepository(name="repo", absolute_path="/repo")

    with patch("os.path.exists", return_value=True):
        result = action.execute(
            RestoreDocumentsRequest(
                repo=repo,
                source=RestoreSource.COMMIT,
                scope=RestoreScope.SINGLE_PATH,
                commit_hash="abc123",
                paths=["a.FCStd"],
            )
        )

    assert result.is_success is True
    assert freecad_port.closed_document_names == ["DocA", "DocB"]
    assert freecad_port.opened_document_paths == ["/repo/a.FCStd", "/repo/b.FCStd"]
    assert freecad_port.active_document_names == ["DocA"]


def test_reopens_documents_even_when_restore_fails() -> None:
    doc = MockDocument("/repo/a.FCStd", name="DocA")
    freecad_port = FakeFreeCadPort(active_document=doc, open_documents=[doc])

    fake_git_port = FakeGitPort()
    fake_git_port.set_file_contents(None, "a.FCStd", "exists")
    fake_git_port.restore_paths_from_ref = lambda git_root, commit, paths: False  # type: ignore[method-assign]

    service = GitService(git_port=fake_git_port)
    action = RestoreDocumentsAction(git_service=service, freecad_port=freecad_port)
    repo = GitRepository(name="repo", absolute_path="/repo")

    with patch("os.path.exists", return_value=True):
        result = action.execute(
            RestoreDocumentsRequest(
                repo=repo,
                source=RestoreSource.INDEX,
                scope=RestoreScope.SINGLE_PATH,
                paths=["a.FCStd"],
            )
        )

    assert result.is_success is False
    assert freecad_port.closed_document_names == ["DocA"]
    assert freecad_port.opened_document_paths == ["/repo/a.FCStd"]


def test_empty_index_bulk_discard_keeps_documents_and_unindexed_files_untouched() -> None:
    """An empty index is a typed no-op even when saved or open files exist."""
    doc = MockDocument("/home/user/dir/repo/new.FCStd", name="New")
    freecad = FakeFreeCadPort(active_document=doc, open_documents=[doc])
    git = FakeGitPort()
    root = "/home/user/dir/repo"
    git.set_all_fcstd_paths(root, None, [])
    git.set_current_saved_fcstd_paths(root, ["new.FCStd"])
    action = RestoreDocumentsAction(GitService(git_port=git), freecad)

    result = action.execute(RestoreDocumentsRequest(GitRepository("repo", root), RestoreSource.INDEX, RestoreScope.ALL_FCSTD))

    assert result.is_success
    assert result.data == RestoreDocumentsSummary([], 0)
    assert git.get_last_restore_call() is None
    assert freecad.closed_document_names == []
    assert freecad.opened_document_paths == []
    assert freecad.active_document_names == []


def test_clean_indexed_files_still_restore_and_reopen_documents() -> None:
    """Bulk discard restores indexed files without querying whether they are dirty."""
    root = "/home/user/dir/repo"
    doc = MockDocument(f"{root}/a.FCStd", name="DocA")
    freecad = FakeFreeCadPort(active_document=doc, open_documents=[doc])
    git = FakeGitPort()
    git.set_all_fcstd_paths(root, None, ["a.FCStd"])
    git.set_current_saved_fcstd_paths(root, ["a.FCStd", "new.FCStd"])
    action = RestoreDocumentsAction(GitService(git_port=git), freecad)

    with patch("os.path.exists", return_value=True):
        result = action.execute(RestoreDocumentsRequest(GitRepository("repo", root), RestoreSource.INDEX, RestoreScope.ALL_FCSTD))

    assert result.is_success
    assert git.get_last_restore_call() == (root, None, ["a.FCStd"])
    assert freecad.closed_document_names == ["DocA"]
    assert freecad.opened_document_paths == [f"{root}/a.FCStd"]


@pytest.mark.parametrize(
    ("scope", "paths", "message"),
    [
        (RestoreScope.ALL_FCSTD, None, "No files available to restore from selected source"),
        (RestoreScope.LISTED_FCSTD, [], "No files selected for restore"),
        (RestoreScope.SINGLE_PATH, ["missing.FCStd"], "Selected file is not available in source"),
    ],
)
def test_historical_restore_empty_or_missing_source_remains_failure(
    scope: RestoreScope, paths: list[str] | None, message: str
) -> None:
    """Historical empty and missing-source cases retain their errors without destructive effects."""
    git = FakeGitPort()
    freecad = FakeFreeCadPort()
    action = RestoreDocumentsAction(GitService(git_port=git), freecad)
    request = RestoreDocumentsRequest(
        GitRepository("repo", "/home/user/dir/repo"), RestoreSource.COMMIT, scope, "abc123", paths
    )

    result = action.execute(request)

    assert not result.is_success
    assert result.message == message
    assert git.get_last_restore_call() is None
    assert freecad.closed_document_names == []
    assert freecad.opened_document_paths == []
