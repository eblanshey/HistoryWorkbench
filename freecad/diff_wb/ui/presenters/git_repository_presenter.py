# SPDX-License-Identifier: LGPL-3.0-or-later
"""Git repository presenter for UI layer."""

from freecad.diff_wb.application.actions.find_active_git_repository import (
    FindActiveGitRepositoryAction,
)
from freecad.diff_wb.ui.presenters.application_state import ApplicationState
from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView
from freecad.diff_wb.utils import Log


class GitRepositoryPresenter:
    """Handles git repository detection and UI display.

    This presenter is responsible for:
    1. Detecting the active git repository when the workbench is activated
    2. Updating the application state with the detected repository
    3. Displaying the repository information in the view

    Attributes:
        _view: The DiffPanelView instance for displaying repository info.
        _find_git_repo_action: The action for finding the active git repository.
        _application_state: The application state holder for storing repository.
    """

    def __init__(
        self,
        view: DiffPanelView,
        find_git_repo_action: FindActiveGitRepositoryAction,
        application_state: ApplicationState,
    ) -> None:
        """Initialize the presenter with required dependencies.

        Args:
            view: The DiffPanelView instance for displaying repository info.
            find_git_repo_action: The action for finding the active git repository.
            application_state: The application state holder for storing repository.
        """
        self._view = view
        self._find_git_repo_action = find_git_repo_action
        self._application_state = application_state
        self._view.set_refresh_callback(self.on_refresh_clicked)

    def on_workbench_activated(self) -> None:
        """Detect and display git repository when workbench activates.

        This method is called when the workbench is activated to detect
        the current git repository and display it in the UI.
        """
        self._detect_git_repository()

    def on_refresh_clicked(self) -> None:
        """Re-detect and display git repository when refresh is clicked."""
        self._detect_git_repository()

    def _detect_git_repository(self) -> None:
        """Detect git repository and update UI and application state.

        This protected method encapsulates the common logic for git repository
        detection used by both workbench activation and refresh button clicks.
        """
        result = self._find_git_repo_action.execute()

        if result.is_success:
            repo = result.data
            self._application_state.git_repository = repo
            self._view.show_repository(repo)
        else:
            self._application_state.git_repository = None
            self._view.show_repository(None)
            Log.warning(f"Git detection failed: {result.message}")
