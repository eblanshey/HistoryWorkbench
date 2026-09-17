# File responsibility: Composes and registers UI components.
# Provides two composition roots: one for the app-scoped workbench command
# presenter, and one for the panel-scoped diff panel (views + presenters +
# signal wiring). It consumes a pre-created ApplicationState and does not
# own state lifecycle.
"""UI Composer - Composes and registers UI components."""

from collections.abc import Callable

from ..application.container import ApplicationContainer
from ..ui.registry import ui_registry
from ..ui.state import ApplicationState
from ..ui.views.diff_panel import DialogView, HistoryPanelView
from ..ui.wiring import bind_ui_events
from .presenters.diff_presenter import DiffPresenter
from .presenters.git_repository_presenter import GitRepositoryPresenter


__all__ = ["compose_and_register_workbench_commands", "compose_and_register_panel"]


def compose_and_register_workbench_commands(
    container: ApplicationContainer,
    application_state: ApplicationState,
) -> None:
    """Create and register the app-scoped workbench command presenter."""
    from ..entrypoints.workbench import getMainWindow
    from .presenters.workbench_command_presenter import WorkbenchCommandPresenter

    command_presenter = WorkbenchCommandPresenter(
        application_state=application_state,
        get_main_window=lambda: getMainWindow(),  # noqa: B026
        find_active_git_repository_action=container.find_active_git_repository_action,
        check_git_availability_action=container.check_git_availability_action,
        get_staged_file_paths_action=container.get_staged_file_paths_action,
        commit_staging_action=container.commit_staging_action,
        get_git_identity_action=container.get_git_identity_action,
        save_git_identity_action=container.save_git_identity_action,
        can_write_global_git_identity_action=container.can_write_global_git_identity_action,
        get_git_repository_init_candidates_action=container.get_git_repository_init_candidates_action,
        initialize_git_repository_action=container.initialize_git_repository_action,
        get_gitignore_content_action=container.get_gitignore_content_action,
        update_gitignore_action=container.update_gitignore_action,
    )
    ui_registry.register_workbench_command_presenter(command_presenter)


def compose_and_register_panel(
    container: ApplicationContainer,
    application_state: ApplicationState,
    focus_history_window_callback: Callable[[], None],
) -> HistoryPanelView:
    """Create and register the diff panel UI components.

    This function is the composition root for the panel-scoped UI layer.
    It creates all UI components (views, presenters) and wires them together,
    then registers the presenters in the global UI registry for access
    by entry points (commands).

    ApplicationState is created externally (workbench lifecycle) and passed
    in. This keeps state alive across panel open/close cycles.

    Args:
        container: Application container with actions wired (backend only)
        application_state: Pre-created application state (survives panel close)
        focus_history_window_callback: Callback that refocuses the history host window
    Returns:
        The configured HistoryPanelView

    Side Effects:
        - Registers presenters in UIRegistry
        - Connects all callbacks
        - Initializes git repository detection
    """
    # Create view with settings repo for runtime precision
    view = HistoryPanelView(settings_repo=container.settings_repo)
    dialog_view = DialogView(view)

    # Create and register diff_presenter (needs application_state for git_repository)
    diff_presenter = DiffPresenter(
        document_view=view.document_diff_panel,
        property_view=view.property_diff_panel,
        dialog_view=dialog_view,
        application_state=application_state,
        get_eligible_docs_action=container.get_open_eligible_docs_action,
        create_document_diffs_action=container.create_document_diffs_action,
        stage_documents_action=container.stage_documents_action,
        unstage_documents_action=container.unstage_documents_action,
        get_staged_file_paths_action=container.get_staged_file_paths_action,
        get_committed_file_paths_action=container.get_committed_file_paths_action,
        open_visual_feature_diff_action=container.open_visual_feature_diff_action,
        open_document_action=container.open_document_action,
        restore_documents_action=container.restore_documents_action,
        focus_history_window_callback=focus_history_window_callback,
        settings_repo=container.settings_repo,
    )
    ui_registry.register_diff_presenter(diff_presenter)

    # Get app-scoped command presenter (created during workbench init)
    command_presenter = ui_registry.workbench_command_presenter

    # Lifecycle presenter - creates git detection + refresh behavior
    git_repo_presenter = GitRepositoryPresenter(
        history_view=view.history_panel,
        dialog_view=dialog_view,
        get_commits_action=container.get_commits_action,
        application_state=application_state,
        clear_doc_diffs=diff_presenter.clear_doc_diff,
        workbench_command_presenter=command_presenter,
    )
    ui_registry.register_git_repository_presenter(git_repo_presenter)

    bind_ui_events(view, diff_presenter, git_repo_presenter)

    # Trigger git repository detection on workbench activation
    git_repo_presenter.on_workbench_activated()

    return view
