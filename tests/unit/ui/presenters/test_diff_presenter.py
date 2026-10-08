# File responsibility: Facade-focused unit tests for DiffPresenter coordinator behavior.

from __future__ import annotations

from datetime import datetime
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest

from freecad.history_wb.application.actions.diffs.create_document_diffs import CreateDocumentDiffsAction
from freecad.history_wb.application.actions.diffs.open_visual_diff import OpenVisualDiffAction
from freecad.history_wb.application.actions.documents.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from freecad.history_wb.application.actions.documents.open_document import OpenDocumentAction
from freecad.history_wb.application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from freecad.history_wb.application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from freecad.history_wb.application.actions.git_workflow.restore_documents import RestoreDocumentsAction
from freecad.history_wb.application.actions.git_workflow.stage_documents import StageDocumentsAction
from freecad.history_wb.application.actions.git_workflow.unstage_documents import UnstageDocumentsAction
from freecad.history_wb.application.actions.result_models import DiffIssues, DocumentDiffResult, Result
from freecad.history_wb.domain.diff.models import DiffResult, DiffState
from freecad.history_wb.domain.git.models import GitRepository
from freecad.history_wb.domain.snapshots.models import Snapshot
from freecad.history_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.history_wb.ui.presenters.document_diff.staging_handler import StagingDisplayState
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation, PropertyPresentation
from freecad.history_wb.ui.state import ApplicationState
from freecad.history_wb.ui.views.document_diff.summary_state import SummaryButtonState, SummaryCounts
from freecad.history_wb.ui.views.history.models import HistorySelection
from tests.fakes.fake_views import FakeDialogView, FakeDocumentDiffView, FakePropertyDiffView


def _make_presenter() -> tuple[FakeDocumentDiffView, FakePropertyDiffView, FakeDialogView, DiffPresenter]:
    document_view = FakeDocumentDiffView()
    property_view = FakePropertyDiffView()
    dialog_view = FakeDialogView()
    presenter = DiffPresenter(
        document_view=document_view,
        property_view=property_view,
        dialog_view=dialog_view,
        application_state=ApplicationState(git_repository=None),
        get_eligible_docs_action=MagicMock(spec=GetOpenEligibleDocumentsAction),
        create_document_diffs_action=MagicMock(spec=CreateDocumentDiffsAction),
        stage_documents_action=MagicMock(spec=StageDocumentsAction),
        unstage_documents_action=MagicMock(spec=UnstageDocumentsAction),
        get_staged_file_paths_action=MagicMock(spec=GetStagedFilePathsAction),
        get_committed_file_paths_action=MagicMock(spec=GetCommittedFilePathsAction),
        open_visual_feature_diff_action=MagicMock(spec=OpenVisualDiffAction),
        open_document_action=MagicMock(spec=OpenDocumentAction),
        restore_documents_action=MagicMock(spec=RestoreDocumentsAction),
        focus_history_window_callback=lambda: None,
    )
    return document_view, property_view, dialog_view, presenter


def _make_snapshot(git_path: str) -> Snapshot:
    return Snapshot(
        snapshot_id=git_path,
        document_name=git_path,
        timestamp=datetime.now(),
        git_path=git_path,
    )


@pytest.mark.parametrize(
    ("selection", "method_name", "expected_arg"),
    [
        (HistorySelection(item_kind="WORKING_TREE", commit_hash=None), "_on_working_tree_selected", None),
        (HistorySelection(item_kind="STAGING", commit_hash=None), "_on_staging_selected", None),
    ],
)
def test_history_item_selected_routes_non_commit_selections(
    selection: HistorySelection,
    method_name: str,
    expected_arg: str | None,
) -> None:
    """History selection routes working-tree and staging rows to matching flow."""
    _, _, _, presenter = _make_presenter()

    with patch.object(presenter, method_name) as target_method:
        presenter.select_history_item(selection)

    assert presenter._current_history_selection == selection
    if expected_arg is None:
        target_method.assert_called_once_with()
    else:
        target_method.assert_called_once_with(expected_arg)


def test_history_item_selected_routes_commit_selection_and_tracks_current_selection() -> None:
    """Commit selection updates presenter state and delegates to commit flow."""
    _, _, _, presenter = _make_presenter()
    selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")

    with patch.object(presenter, "_on_commit_selected") as on_commit_selected:
        presenter.select_history_item(selection)

    assert presenter._current_history_selection == selection
    on_commit_selected.assert_called_once_with("abc123")


def test_open_document_click_focuses_history_window_after_refresh() -> None:
    """Successful open-document flow refreshes and refocuses history host window."""
    _, _, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    presenter._open_document.execute.return_value = Result.success("/home/user/dir/repo/doc.FCStd")
    focused: list[bool] = []
    presenter._focus_history_window_callback = lambda: focused.append(True)

    with patch.object(presenter, "_on_working_tree_selected") as on_working_tree_selected:
        presenter.open_document_for_comparison("doc.FCStd")

    on_working_tree_selected.assert_called_once_with()
    assert focused == [True]


def test_add_button_click_applies_staging_handler_remaining_results() -> None:
    """Presenter applies cached remainder returned by staging handler."""
    _, _, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    remaining_result = DocumentDiffResult(git_path="b.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues())
    presenter._staging_handler = MagicMock()
    presenter._staging_handler.stage_document.return_value = StagingDisplayState(
        clear_property_diff=True,
        remaining_document_results=[remaining_result],
    )

    with patch.object(presenter, "present_diffs") as present_diffs:
        presenter.stage_document("a.FCStd")

    presenter._staging_handler.stage_document.assert_called_once()
    present_diffs.assert_called_once_with([remaining_result])


def test_restore_document_click_clears_property_diff_after_handler_call() -> None:
    """Presenter clears property pane after single-file restore flow."""
    _, property_view, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    presenter._current_history_selection = HistorySelection(item_kind="STAGING", commit_hash=None)
    presenter._restore_handler = MagicMock()
    presenter._restore_handler.restore_document.return_value = False

    presenter.restore_document("doc.FCStd")

    presenter._restore_handler.restore_document.assert_called_once()
    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())


def test_current_files_restore_focuses_history_and_refreshes_diff() -> None:
    """Successful Current Files restore refocuses history and reloads working-tree changes."""
    _, _, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    presenter._current_history_selection = selection
    presenter._restore_handler = MagicMock()
    presenter._restore_handler.restore_document.return_value = True
    focused: list[bool] = []
    presenter._focus_history_window_callback = lambda: focused.append(True)

    with patch.object(presenter, "_on_working_tree_selected") as refresh:
        presenter.restore_document("doc.FCStd")

    presenter._restore_handler.restore_document.assert_called_once_with(
        presenter._application_state.git_repository, selection, "doc.FCStd"
    )
    refresh.assert_called_once_with()
    assert focused == [True]


def test_clear_doc_diff_clears_document_and_property_panels() -> None:
    """Clearing document diffs also clears dependent property panel."""
    document_view, property_view, _, presenter = _make_presenter()
    snapshot = _make_snapshot("doc.FCStd")
    presenter._result_store.store_results(
        [
            DocumentDiffResult(
                git_path="doc.FCStd",
                document_state=DiffState.MODIFIED,
                issues=DiffIssues(),
                snapshot_diff=DiffResult(old_snapshot=snapshot, new_snapshot=snapshot),
            )
        ]
    )

    presenter.clear_doc_diff()

    assert any(call["method"] == "clear_doc_diffs" for call in document_view.get_calls())
    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())
    assert presenter._result_store.get_document_result("doc.FCStd") is None
    assert presenter._result_store.has_diff_results() is False


def test_staging_display_state_doc_clear_also_clears_property_panel() -> None:
    """Doc-clear staging state clears both panels through presenter helper."""
    document_view, property_view, _, presenter = _make_presenter()

    presenter._apply_staging_display_state(StagingDisplayState(clear_doc_diff=True))

    assert any(call["method"] == "clear_doc_diffs" for call in document_view.get_calls())
    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())


@pytest.mark.parametrize(
    ("refresh_mode", "expected_method"),
    [("working_tree", "_on_working_tree_selected"), ("staging", "_on_staging_selected")],
)
def test_staging_display_state_refreshes_requested_history_mode(refresh_mode: str, expected_method: str) -> None:
    """Staging display state triggers requested follow-up history refresh."""
    _, _, _, presenter = _make_presenter()

    with (
        patch.object(presenter, "_on_working_tree_selected") as on_working_tree_selected,
        patch.object(presenter, "_on_staging_selected") as on_staging_selected,
    ):
        presenter._apply_staging_display_state(StagingDisplayState(refresh_mode=refresh_mode))

    expected_call_count = 1 if expected_method == "_on_working_tree_selected" else 0
    assert on_working_tree_selected.call_count == expected_call_count
    expected_call_count = 1 if expected_method == "_on_staging_selected" else 0
    assert on_staging_selected.call_count == expected_call_count


def test_present_diffs_sorts_presentations_and_updates_summary_controls() -> None:
    """Presenter sorts mapped document rows and forwards summary-bar state to view."""
    document_view, property_view, _, presenter = _make_presenter()
    presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    document_results = [DocumentDiffResult(git_path="b.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues())]
    mapped_presentations = [
        DiffTreePresentation(nodes=[], git_path="z.FCStd", indicators=[]),
        DiffTreePresentation(nodes=[], git_path="a.FCStd", indicators=[], stage_button_enabled=True),
    ]
    button_state = SummaryButtonState(True, True, False, False, False, False)
    counts = SummaryCounts(modified_docs=2, deleted_docs=1, added_docs=3)

    with (
        patch(
            "freecad.history_wb.ui.presenters.diff_presenter.build_document_presentations",
            return_value=mapped_presentations,
        ),
        patch("freecad.history_wb.ui.presenters.diff_presenter.build_summary_button_state", return_value=button_state),
        patch("freecad.history_wb.ui.presenters.diff_presenter.count_summary_counts", return_value=counts),
    ):
        presenter.present_diffs(document_results)

    show_doc_diffs_call = next(call for call in document_view.get_calls() if call["method"] == "show_doc_diffs")
    assert [tree.git_path for tree in show_doc_diffs_call["diff_trees"]] == ["a.FCStd", "z.FCStd"]
    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())
    button_states_call = next(call for call in document_view.get_calls() if call["method"] == "set_button_states")
    assert button_states_call["state"] == button_state
    summary_counts_call = next(call for call in document_view.get_calls() if call["method"] == "set_summary_counts")
    assert summary_counts_call["counts"] == counts


@pytest.mark.parametrize("item_kind", ["STAGING", "WORKING_TREE"])
def test_restore_all_documents_delegates_current_selection_to_history_context_restore(
    item_kind: Literal["STAGING", "WORKING_TREE"],
) -> None:
    """Restore-all button reuses context-restore path with current history selection."""
    _, _, _, presenter = _make_presenter()
    selection = HistorySelection(item_kind=item_kind, commit_hash=None)
    presenter._current_history_selection = selection

    with patch.object(presenter, "restore_all_from_history") as restore_all_from_history:
        presenter.restore_all_documents()

    restore_all_from_history.assert_called_once_with(selection)


@pytest.mark.parametrize("succeeded", [False, True])
def test_current_files_restore_all_refreshes_and_focuses_only_after_success(succeeded: bool) -> None:
    """Bulk Current Files restore forwards selection and reloads working diffs after success."""
    _, _, _, presenter = _make_presenter()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    presenter._application_state.git_repository = repo
    presenter._current_history_selection = selection
    presenter._restore_handler = MagicMock()
    presenter._restore_handler.restore_all.return_value = succeeded
    focused: list[bool] = []
    presenter._focus_history_window_callback = lambda: focused.append(True)

    with patch.object(presenter, "_on_working_tree_selected") as refresh:
        presenter.restore_all_documents()

    presenter._restore_handler.restore_all.assert_called_once_with(repo, selection)
    assert refresh.call_count == int(succeeded)
    assert focused == ([True] if succeeded else [])


def test_present_empty_current_files_keeps_restore_all_visible_disabled() -> None:
    """Empty Current Files uses real summary mapping without hiding Restore All."""
    document_view, _, _, presenter = _make_presenter()
    presenter._current_history_selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)

    presenter.present_diffs([])

    button_states_call = next(call for call in document_view.get_calls() if call["method"] == "set_button_states")
    assert button_states_call["state"] == SummaryButtonState(True, False, False, False, True, False, True)


def test_restore_all_from_history_clears_property_diff_after_handler_call() -> None:
    """Context restore-all clears property pane after delegated restore flow."""
    _, property_view, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    presenter._restore_handler = MagicMock()
    presenter._restore_handler.restore_all.return_value = False
    selection = HistorySelection(item_kind="COMMIT", commit_hash="abc123")

    presenter.restore_all_from_history(selection)

    presenter._restore_handler.restore_all.assert_called_once_with(
        presenter._application_state.git_repository, selection
    )
    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())


@pytest.mark.parametrize(
    "selection",
    [
        HistorySelection(item_kind="STAGING", commit_hash=None),
        HistorySelection(item_kind="COMMIT", commit_hash="abc123"),
    ],
)
def test_restore_all_from_history_focuses_history_window_after_success(
    selection: HistorySelection,
) -> None:
    """Successful bulk restore refocuses history window for both UI entry points."""
    _, _, _, presenter = _make_presenter()
    presenter._application_state.git_repository = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    presenter._restore_handler = MagicMock()
    presenter._restore_handler.restore_all.return_value = True
    focused: list[bool] = []
    presenter._focus_history_window_callback = lambda: focused.append(True)

    presenter.restore_all_from_history(selection)

    assert focused == [True]


def test_visual_diff_click_delegates_to_visual_diff_handler() -> None:
    """Visual diff slot delegates request building and execution to handler."""
    _, _, _, presenter = _make_presenter()
    repo = GitRepository(name="repo", absolute_path="/home/user/dir/repo")
    selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    presenter._application_state.git_repository = repo
    presenter._current_history_selection = selection
    presenter._visual_diff_handler = MagicMock()

    presenter.open_visual_diff("doc.FCStd", "Body/Pad")

    presenter._visual_diff_handler.open_visual_diff.assert_called_once_with(
        selection,
        repo,
        "doc.FCStd",
        "Body/Pad",
    )


def test_visual_diff_click_skips_handler_when_no_history_selection_exists() -> None:
    """Visual diff requires active history selection before delegating to handler."""
    _, _, _, presenter = _make_presenter()
    presenter._visual_diff_handler = MagicMock()

    presenter.open_visual_diff("doc.FCStd", "Body/Pad")

    presenter._visual_diff_handler.open_visual_diff.assert_not_called()


def test_node_selected_shows_transformed_property_diff_for_valid_node() -> None:
    """Valid tree-node selection transforms and shows mapped property diff rows."""
    _, property_view, _, presenter = _make_presenter()
    node_diff = MagicMock()
    diff_result = MagicMock()
    diff_result.hierarchy.find_by_path.return_value = node_diff
    presenter._result_store.store_results(
        [
            DocumentDiffResult(
                git_path="doc.FCStd",
                document_state=DiffState.MODIFIED,
                issues=DiffIssues(),
                snapshot_diff=diff_result,
            )
        ]
    )
    expected_properties = [PropertyPresentation(name="Length", state=DiffState.MODIFIED)]

    with patch(
        "freecad.history_wb.ui.presenters.diff_presenter.transform_property_diffs", return_value=expected_properties
    ):
        presenter.select_node("doc.FCStd", "Body/Pad")

    show_property_call = next(call for call in property_view.get_calls() if call["method"] == "show_property_diff")
    assert show_property_call["properties"] == expected_properties


def test_node_selected_clears_property_diff_for_stale_tree_row() -> None:
    """Stale tree selection clears property pane instead of raising."""
    _, property_view, _, presenter = _make_presenter()
    snapshot = _make_snapshot("doc.FCStd")
    presenter._result_store.store_results(
        [
            DocumentDiffResult(
                git_path="doc.FCStd",
                document_state=DiffState.MODIFIED,
                issues=DiffIssues(),
                snapshot_diff=DiffResult(old_snapshot=snapshot, new_snapshot=snapshot),
            )
        ]
    )

    presenter.select_node("missing.FCStd", "Body/Pad")

    assert any(call["method"] == "clear_property_diff" for call in property_view.get_calls())
