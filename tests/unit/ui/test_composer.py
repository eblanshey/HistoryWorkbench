# File responsibility: Verify UI composer wiring, registration, and constructed dependencies.

from unittest.mock import MagicMock, patch

import pytest

from freecad.history_wb.application.container import ApplicationContainer
from freecad.history_wb.ui.composer import compose_and_register_panel, compose_and_register_workbench_commands
from freecad.history_wb.ui.registry import ui_registry
from freecad.history_wb.ui.state import ApplicationState


class _SignalMock:
    """Minimal Qt-like signal mock for composer connection assertions."""

    def __init__(self) -> None:
        self.connect = MagicMock()


class _HistoryPanelMock:
    """Expose history-panel signals used by ui wiring."""

    def __init__(self) -> None:
        self.refresh_requested = _SignalMock()
        self.save_iteration_requested = _SignalMock()
        self.history_scroll_bottom_requested = _SignalMock()
        self.history_selection_requested = _SignalMock()
        self.remove_all_from_reviewed_requested = _SignalMock()
        self.mark_all_reviewed_from_in_progress_requested = _SignalMock()
        self.restore_all_from_history_context_requested = _SignalMock()


class _DocumentDiffPanelMock:
    """Expose document-diff signals used by ui wiring."""

    def __init__(self) -> None:
        self.add_requested = _SignalMock()
        self.stage_all_requested = _SignalMock()
        self.remove_all_requested = _SignalMock()
        self.remove_from_reviewed_requested = _SignalMock()
        self.restore_requested = _SignalMock()
        self.restore_all_requested = _SignalMock()
        self.node_selection_requested = _SignalMock()
        self.visual_diff_requested = _SignalMock()
        self.open_document_for_comparison_requested = _SignalMock()


def _mock_view() -> MagicMock:
    """Create a view mock with signal attributes used by composer."""
    view = MagicMock()
    view.history_panel = _HistoryPanelMock()
    view.history_selection_changed = _SignalMock()
    view.document_diff_panel = _DocumentDiffPanelMock()
    view.property_diff_panel = MagicMock()
    return view


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset UI registry before each test to ensure clean state."""
    ui_registry.clear()
    yield
    ui_registry.clear()


def _mock_container() -> MagicMock:
    """Create a mock container with all required action attributes."""
    mock = MagicMock(spec=ApplicationContainer)
    mock.get_open_eligible_docs_action = MagicMock()
    mock.create_working_snapshot_action = MagicMock()
    mock.create_commit_snapshot_action = MagicMock()
    mock.create_diff_action = MagicMock()
    mock.create_document_diffs_action = MagicMock()
    mock.stage_documents_action = MagicMock()
    mock.unstage_documents_action = MagicMock()
    mock.open_visual_feature_diff_action = MagicMock()
    mock.open_document_action = MagicMock()
    mock.get_staged_file_paths_action = MagicMock()
    mock.get_committed_file_paths_action = MagicMock()
    mock.commit_staging_action = MagicMock()
    mock.get_git_identity_action = MagicMock()
    mock.save_git_identity_action = MagicMock()
    mock.can_write_global_git_identity_action = MagicMock()
    mock.restore_documents_action = MagicMock()
    mock.find_active_git_repository_action = MagicMock()
    mock.check_git_availability_action = MagicMock()
    mock.get_commits_action = MagicMock()
    mock.get_git_repository_init_candidates_action = MagicMock()
    mock.initialize_git_repository_action = MagicMock()
    mock.get_gitignore_content_action = MagicMock()
    mock.update_gitignore_action = MagicMock()
    mock.settings_repo = MagicMock()
    return mock


def test_compose_creates_and_registers_ui_components() -> None:
    """compose_and_register_panel returns view, uses externally provided ApplicationState, registers both presenters, calls on_workbench_activated."""  # noqa: E501
    mock_container = _mock_container()
    mock_application_state = ApplicationState(git_repository=None)
    mock_command_presenter = MagicMock()

    with (
        patch("freecad.history_wb.ui.composer.HistoryPanelView") as MockView,
        patch("freecad.history_wb.ui.composer.DialogView") as MockDialogView,
        patch("freecad.history_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
        patch("freecad.history_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
    ):
        mock_view = _mock_view()
        MockView.return_value = mock_view
        mock_dialog_view = MagicMock()
        MockDialogView.return_value = mock_dialog_view

        mock_diff_presenter = MagicMock()
        MockDiffPresenter.return_value = mock_diff_presenter

        mock_git_presenter = MagicMock()
        MockGitPresenter.return_value = mock_git_presenter

        # Register command presenter before compose
        ui_registry.register_workbench_command_presenter(mock_command_presenter)

        result = compose_and_register_panel(mock_container, mock_application_state, MagicMock())

        # Returns the view
        assert result is mock_view

        # Both presenters created and registered
        assert MockDiffPresenter.call_count == 1
        assert MockGitPresenter.call_count == 1

        # GitRepositoryPresenter.on_workbench_activated called
        mock_git_presenter.on_workbench_activated.assert_called_once()


def test_compose_uses_externally_provided_application_state() -> None:
    """Composer passes the externally provided ApplicationState into both presenters."""
    mock_container = _mock_container()
    mock_application_state = ApplicationState(git_repository=None)
    mock_command_presenter = MagicMock()

    with (
        patch("freecad.history_wb.ui.composer.HistoryPanelView") as MockView,
        patch("freecad.history_wb.ui.composer.DialogView") as MockDialogView,
        patch("freecad.history_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
        patch("freecad.history_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
    ):
        mock_view = _mock_view()
        MockView.return_value = mock_view
        mock_dialog_view = MagicMock()
        MockDialogView.return_value = mock_dialog_view

        mock_diff_presenter = MagicMock()
        MockDiffPresenter.return_value = mock_diff_presenter

        mock_git_presenter = MagicMock()
        MockGitPresenter.return_value = mock_git_presenter

        # Register command presenter before compose
        ui_registry.register_workbench_command_presenter(mock_command_presenter)

        compose_and_register_panel(mock_container, mock_application_state, MagicMock())

        # Both presenters receive the same ApplicationState instance
        diff_kwargs = MockDiffPresenter.call_args.kwargs
        assert diff_kwargs["application_state"] is mock_application_state

        git_kwargs = MockGitPresenter.call_args.kwargs
        assert git_kwargs["application_state"] is mock_application_state


def test_compose_wires_action_dependencies_and_callbacks() -> None:
    """Action dependencies and event wiring are delegated correctly."""
    mock_container = _mock_container()
    mock_application_state = ApplicationState(git_repository=None)
    mock_command_presenter = MagicMock()

    with (
        patch("freecad.history_wb.ui.composer.HistoryPanelView") as MockView,
        patch("freecad.history_wb.ui.composer.DialogView") as MockDialogView,
        patch("freecad.history_wb.ui.composer.DiffPresenter") as MockDiffPresenter,
        patch("freecad.history_wb.ui.composer.GitRepositoryPresenter") as MockGitPresenter,
    ):
        mock_view = _mock_view()
        MockView.return_value = mock_view
        mock_dialog_view = MagicMock()
        MockDialogView.return_value = mock_dialog_view

        mock_diff_presenter = MagicMock()
        MockDiffPresenter.return_value = mock_diff_presenter

        mock_git_presenter = MagicMock()
        MockGitPresenter.return_value = mock_git_presenter

        # Register command presenter before compose
        ui_registry.register_workbench_command_presenter(mock_command_presenter)

        focus_history_window_callback = MagicMock()

        compose_and_register_panel(mock_container, mock_application_state, focus_history_window_callback)

        # DiffPresenter receives correct concrete collaborators and actions from container
        diff_kwargs = MockDiffPresenter.call_args.kwargs
        assert diff_kwargs["document_view"] is mock_view.document_diff_panel
        assert diff_kwargs["property_view"] is mock_view.property_diff_panel
        assert diff_kwargs["dialog_view"] is mock_dialog_view
        assert diff_kwargs["get_eligible_docs_action"] is mock_container.get_open_eligible_docs_action
        assert diff_kwargs["create_document_diffs_action"] is mock_container.create_document_diffs_action
        assert diff_kwargs["stage_documents_action"] is mock_container.stage_documents_action
        assert diff_kwargs["unstage_documents_action"] is mock_container.unstage_documents_action
        assert diff_kwargs["get_staged_file_paths_action"] is mock_container.get_staged_file_paths_action
        assert diff_kwargs["get_committed_file_paths_action"] is mock_container.get_committed_file_paths_action
        assert diff_kwargs["open_visual_feature_diff_action"] is mock_container.open_visual_feature_diff_action
        assert diff_kwargs["open_document_action"] is mock_container.open_document_action
        assert diff_kwargs["restore_documents_action"] is mock_container.restore_documents_action
        assert diff_kwargs["focus_history_window_callback"] is focus_history_window_callback

        # GitRepositoryPresenter receives correct collaborators and command presenter
        git_kwargs = MockGitPresenter.call_args.kwargs
        assert git_kwargs["history_view"] is mock_view.history_panel
        assert git_kwargs["dialog_view"] is mock_dialog_view
        assert git_kwargs["get_commits_action"] is mock_container.get_commits_action
        assert git_kwargs["application_state"] is mock_application_state
        assert git_kwargs["workbench_command_presenter"] is mock_command_presenter

        # Composer delegates public signal binding to ui.wiring.
        mock_view.history_panel.refresh_requested.connect.assert_called_once_with(
            mock_git_presenter.refresh_repository_and_commits
        )
        mock_view.history_panel.save_iteration_requested.connect.assert_called_once_with(
            mock_git_presenter.save_iteration
        )
        mock_view.history_panel.history_scroll_bottom_requested.connect.assert_called_once_with(
            mock_git_presenter.load_more_commits
        )
        mock_view.history_panel.history_selection_requested.connect.assert_called_once_with(
            mock_diff_presenter.select_history_item
        )
        mock_view.history_selection_changed.connect.assert_called_once_with(mock_diff_presenter.track_history_selection)
        mock_view.document_diff_panel.node_selection_requested.connect.assert_called_once_with(
            mock_diff_presenter.select_node
        )
        mock_view.document_diff_panel.visual_diff_requested.connect.assert_called_once_with(
            mock_diff_presenter.open_visual_diff
        )
        mock_view.document_diff_panel.add_requested.connect.assert_called_once_with(mock_diff_presenter.stage_document)
        mock_view.document_diff_panel.stage_all_requested.connect.assert_called_once_with(
            mock_diff_presenter.stage_all_documents
        )
        mock_view.document_diff_panel.remove_from_reviewed_requested.connect.assert_called_once_with(
            mock_diff_presenter.remove_document_from_reviewed
        )
        mock_view.history_panel.remove_all_from_reviewed_requested.connect.assert_called_once_with(
            mock_diff_presenter.remove_all_from_reviewed
        )
        mock_view.history_panel.mark_all_reviewed_from_in_progress_requested.connect.assert_called_once_with(
            mock_diff_presenter.stage_all_documents
        )
        mock_view.document_diff_panel.remove_all_requested.connect.assert_called_once_with(
            mock_diff_presenter.remove_all_from_reviewed
        )
        mock_view.document_diff_panel.restore_requested.connect.assert_called_once_with(
            mock_diff_presenter.restore_document
        )
        mock_view.document_diff_panel.restore_all_requested.connect.assert_called_once_with(
            mock_diff_presenter.restore_all_documents
        )
        mock_view.history_panel.restore_all_from_history_context_requested.connect.assert_called_once_with(
            mock_diff_presenter.restore_all_from_history
        )
        mock_view.document_diff_panel.open_document_for_comparison_requested.connect.assert_called_once_with(
            mock_diff_presenter.open_document_for_comparison
        )


def test_compose_and_register_workbench_commands() -> None:
    """compose_and_register_workbench_commands creates and registers WorkbenchCommandPresenter."""
    mock_container = _mock_container()
    mock_application_state = ApplicationState(git_repository=None)

    with (
        patch("freecad.history_wb.ui.presenters.workbench_command_presenter.WorkbenchCommandPresenter") as MockWCP,
        patch("freecad.history_wb.entrypoints.workbench.getMainWindow", return_value=MagicMock()),
    ):
        mock_wcp_instance = MagicMock()
        MockWCP.return_value = mock_wcp_instance

        compose_and_register_workbench_commands(mock_container, mock_application_state)

        # WorkbenchCommandPresenter created with correct arguments
        assert MockWCP.call_count == 1
        wcp_kwargs = MockWCP.call_args.kwargs
        assert wcp_kwargs["application_state"] is mock_application_state
        assert wcp_kwargs["find_active_git_repository_action"] is mock_container.find_active_git_repository_action
        assert wcp_kwargs["check_git_availability_action"] is mock_container.check_git_availability_action
        assert wcp_kwargs["get_staged_file_paths_action"] is mock_container.get_staged_file_paths_action
        assert wcp_kwargs["commit_staging_action"] is mock_container.commit_staging_action
        assert wcp_kwargs["get_git_identity_action"] is mock_container.get_git_identity_action
        assert wcp_kwargs["save_git_identity_action"] is mock_container.save_git_identity_action
        assert wcp_kwargs["can_write_global_git_identity_action"] is mock_container.can_write_global_git_identity_action
        assert (
            wcp_kwargs["get_git_repository_init_candidates_action"]
            is mock_container.get_git_repository_init_candidates_action
        )
        assert wcp_kwargs["initialize_git_repository_action"] is mock_container.initialize_git_repository_action
        assert wcp_kwargs["get_gitignore_content_action"] is mock_container.get_gitignore_content_action
        assert wcp_kwargs["update_gitignore_action"] is mock_container.update_gitignore_action

        # Registered in ui_registry
        assert ui_registry.workbench_command_presenter is mock_wcp_instance
