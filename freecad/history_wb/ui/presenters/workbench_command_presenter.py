# File responsibility: App-scoped UI presenter that owns single instances of
# command handlers and creates temporary dialogs parented to the FreeCAD main
# window at call time. This avoids stale Qt references from panel widgets.
"""App-scoped presenter for workbench command flows."""

from collections.abc import Callable
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ...qt import QtWidgets

from ...application.actions.git_config.can_write_global_git_identity import (
    CanWriteGlobalGitIdentityAction,
)
from ...application.actions.git_config.get_git_identity import GetGitIdentityAction
from ...application.actions.git_config.get_gitignore_content import GetGitIgnoreContentAction
from ...application.actions.git_config.save_git_identity import SaveGitIdentityAction
from ...application.actions.git_config.update_gitignore import UpdateGitIgnoreAction
from ...application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from ...application.actions.git_repo.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from ...application.actions.git_repo.get_git_repository_init_candidates import (
    GetGitRepositoryInitCandidatesAction,
)
from ...application.actions.git_repo.initialize_git_repository import InitializeGitRepositoryAction
from ...application.actions.git_workflow.commit_staging import CommitStagingAction
from ...domain.git.models import GitRepository
from ...qt import QtCore
from ...utils import Log, term, translate
from ..state import ApplicationState
from ..views.diff_panel.dialog_view import DialogView
from ..views.diff_panel.dialogs import GitConfigDialogResult
from .git_repository.author_configuration_handler import AuthorConfigurationHandler
from .git_repository.commit_iteration_handler import CommitIterationHandler
from .git_repository.gitignore_handler import GitIgnoreHandler
from .git_repository.initialize_repository_handler import InitializeRepositoryHandler


class WorkbenchCommandPresenter(QtCore.QObject):
    """App-scoped presenter that owns single handler instances for workbench commands.

    This presenter lives for the lifetime of the workbench. It creates temporary
    DialogView instances parented to the FreeCAD main window at call time,
    avoiding stale Qt references from panel widgets that get destroyed on close.

    Emits repository_changed when the active git repository is refreshed,
    so panel presenters can react.
    """

    repository_changed = QtCore.Signal(object)  # git_repo

    def __init__(
        self,
        application_state: ApplicationState,
        get_main_window: Callable[[], "QtWidgets.QWidget | None"],
        find_active_git_repository_action: FindActiveGitRepositoryAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        commit_staging_action: CommitStagingAction,
        get_git_identity_action: GetGitIdentityAction,
        save_git_identity_action: SaveGitIdentityAction,
        can_write_global_git_identity_action: CanWriteGlobalGitIdentityAction,
        get_git_repository_init_candidates_action: GetGitRepositoryInitCandidatesAction,
        initialize_git_repository_action: InitializeGitRepositoryAction,
        get_gitignore_content_action: GetGitIgnoreContentAction,
        update_gitignore_action: UpdateGitIgnoreAction,
    ) -> None:
        """Initialize with container actions and main-window callable.

        Args:
            application_state: Application-scoped state holder.
            get_main_window: Callable that returns the FreeCAD main window widget.
            find_active_git_repository_action: Action to find the active git repository.
            get_staged_file_paths_action: Action to get staged file paths.
            commit_staging_action: Action to commit staging area.
            get_git_identity_action: Action to get git identity.
            save_git_identity_action: Action to save git identity.
            can_write_global_git_identity_action: Action to check global identity write access.
            get_git_repository_init_candidates_action: Action to get init candidates.
            initialize_git_repository_action: Action to initialize a git repository.
            get_gitignore_content_action: Action to read gitignore content.
            update_gitignore_action: Action to update gitignore content.
        """
        super().__init__()
        self._application_state = application_state
        self._get_main_window = get_main_window
        self._find_active_git_repository_action = find_active_git_repository_action

        # Create handlers with dialog callbacks that create DialogView at call time
        self._author_handler = AuthorConfigurationHandler(
            get_git_identity_action=get_git_identity_action,
            save_git_identity_action=save_git_identity_action,
            can_write_global_git_identity_action=can_write_global_git_identity_action,
            show_configure_author_dialog=self._show_configure_author_dialog,
            show_warning_message=self._show_warning_message,
            show_error_message=self._show_error_message,
        )
        self._commit_handler = CommitIterationHandler(
            get_staged_file_paths_action=get_staged_file_paths_action,
            commit_staging_action=commit_staging_action,
            get_git_identity_action=get_git_identity_action,
            author_configuration_handler=self._author_handler,
            show_save_iteration_dialog=self._show_save_iteration_dialog,
            show_warning_message=self._show_warning_message,
            show_info_message=self._show_info_message,
            show_error_message=self._show_error_message,
        )
        self._init_repo_handler = InitializeRepositoryHandler(
            get_candidates_action=get_git_repository_init_candidates_action,
            initialize_action=initialize_git_repository_action,
            show_init_dialog=self._show_init_repository_dialog,
            show_info_message=self._show_info_message,
            show_error_message=self._show_error_message,
            application_state=application_state,
        )
        self._gitignore_handler = GitIgnoreHandler(
            get_content_action=get_gitignore_content_action,
            update_action=update_gitignore_action,
            show_editor_dialog=self._show_gitignore_editor_dialog,
            show_info_message=self._show_info_message,
            show_error_message=self._show_error_message,
        )

    def configure_author(self) -> bool:
        """Open author configuration flow.

        Returns:
            True if identity was saved, False otherwise.
        """
        repo = self._application_state.git_repository
        if repo is None:
            self._show_warning_message(
                term(translate("History", "No Project"), translate("History", "No Repository")),
                term(
                    translate("History", "No project detected. Open a FreeCAD document in a project first."),
                    translate("History", "No repository detected. Open a FreeCAD document in a repository first."),
                ),
            )
            return False

        return self._author_handler.execute(repo)

    def save_iteration(self) -> bool:
        """Execute save-iteration (commit) flow.

        Returns:
            True if the commit succeeded, False otherwise.
        """
        repo = self._application_state.git_repository
        if repo is None:
            self._show_warning_message(
                term(translate("History", "No Project"), translate("History", "No Repository")),
                term(
                    translate("History", "No project detected. Open a FreeCAD document in a project first."),
                    translate("History", "No repository detected. Open a FreeCAD document in a repository first."),
                ),
            )
            return False

        return self._commit_handler.execute(repo)

    def initialize_repository(self) -> bool:
        """Execute repository initialization flow.

        Returns:
            True if a repository was initialized, False otherwise.
        """
        return self._init_repo_handler.execute()

    def update_gitignore(self) -> None:
        """Execute gitignore editor flow."""
        repo = self._application_state.git_repository
        if repo is None:
            self._show_warning_message(
                term(translate("History", "No Project"), translate("History", "No Repository")),
                term(
                    translate("History", "No project detected. Open a FreeCAD document in a project first."),
                    translate("History", "No repository detected. Open a FreeCAD document in a repository first."),
                ),
            )
            return

        self._gitignore_handler.execute(repo)

    def refresh_git_repository(self) -> GitRepository | None:
        """Detect and update the active git repository in application state.

        Uses sticky repository logic: the current repository is retained
        as long as at least one open document belongs to it.

        Emits repository_changed with the resulting repository (or None).

        Returns:
            The detected GitRepository, or None if no repository found.
        """
        current_repo = self._application_state.git_repository
        result = self._find_active_git_repository_action.execute(current_repository=current_repo)

        if result.is_success:
            self._application_state.git_repository = result.data
            self.repository_changed.emit(result.data)
            return result.data

        # Detection failed; keep existing repo in state (sticky behavior)
        self.repository_changed.emit(current_repo)
        return current_repo

    # --- Dialog helpers ---

    def _create_dialog_view(self) -> DialogView:
        """Create a DialogView parented to the FreeCAD main window."""
        parent = self._get_main_window()
        if parent is None:
            raise RuntimeError("FreeCAD main window not available")
        return DialogView(parent)

    def _show_configure_author_dialog(
        self,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show configure-author dialog via a temporary DialogView."""
        dialog = self._create_dialog_view()
        return dialog.show_configure_author_dialog(
            message=message,
            initial_values=initial_values,
            global_config_writable=global_config_writable,
        )

    def _show_save_iteration_dialog(self) -> str | None:
        """Show save-iteration dialog via a temporary DialogView."""
        dialog = self._create_dialog_view()
        return dialog.show_save_iteration_dialog()

    def _show_init_repository_dialog(self, candidates: list) -> str | None:
        """Show init-repository dialog via a temporary DialogView."""
        dialog = self._create_dialog_view()
        return dialog.show_init_repository_dialog(candidates)

    def _show_gitignore_editor_dialog(self, content: str) -> str | None:
        """Show gitignore editor dialog via a temporary DialogView."""
        dialog = self._create_dialog_view()
        return dialog.show_gitignore_editor_dialog(content)

    def _show_warning_message(self, title: str, message: str) -> None:
        """Show warning message via a temporary DialogView."""
        try:
            dialog = self._create_dialog_view()
            dialog.show_warning_message(title, message)
        except RuntimeError:
            # Main window not available; log as fallback
            Log.warning(f"{title}: {message}")

    def _show_info_message(self, title: str, message: str) -> None:
        """Show info message via a temporary DialogView."""
        try:
            dialog = self._create_dialog_view()
            dialog.show_info_message(title, message)
        except RuntimeError:
            Log.debug(f"{title}: {message}")

    def _show_error_message(self, title: str, message: str) -> None:
        """Show error message via a temporary DialogView."""
        try:
            dialog = self._create_dialog_view()
            dialog.show_error_message(title, message)
        except RuntimeError:
            Log.error(f"{title}: {message}")
