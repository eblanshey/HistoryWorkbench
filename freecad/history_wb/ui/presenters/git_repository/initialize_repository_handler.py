# File responsibility: Handle repository initialization dialog flow and action orchestration.
"""Handle repository initialization dialog flow and action orchestration."""

from collections.abc import Callable

from ....application.actions.git_repo.get_git_repository_init_candidates import (
    GetGitRepositoryInitCandidatesAction,
)
from ....application.actions.git_repo.initialize_git_repository import InitializeGitRepositoryAction
from ....utils import Log, term, translate
from ...state import ApplicationState


class InitializeRepositoryHandler:
    """Own repository initialization flow for presenter and commands."""

    def __init__(
        self,
        get_candidates_action: GetGitRepositoryInitCandidatesAction,
        initialize_action: InitializeGitRepositoryAction,
        show_init_dialog: Callable[[list], str | None],
        show_info_message: Callable[[str, str], None],
        show_error_message: Callable[[str, str], None],
        application_state: ApplicationState,
    ) -> None:
        """Store action and dialog dependencies."""
        self._get_candidates_action = get_candidates_action
        self._initialize_action = initialize_action
        self._show_init_dialog = show_init_dialog
        self._show_info_message = show_info_message
        self._show_error_message = show_error_message
        self._application_state = application_state

    def execute(self) -> bool:
        """Run full initialization flow. Returns True on success."""
        candidates_result = self._get_candidates_action.execute()
        if not candidates_result.is_success:
            self._show_info_message(
                translate("History", "No Directories Available"),
                term(
                    translate(
                        "History",
                        "No open documents are available for project initialization. "
                        "Please open at least one saved document in the root location "
                        "you'd like to initialize a new project.",
                    ),
                    translate(
                        "History",
                        "No open documents are available for repository initialization. "
                        "Please open at least one saved document in the root location "
                        "you'd like to initialize a new repository.",
                    ),
                ),
            )
            return False

        selected_directory = self._show_init_dialog(candidates_result.data)
        if selected_directory is None:
            return False

        init_result = self._initialize_action.execute(selected_directory)
        if not init_result.is_success:
            self._show_error_message(
                translate("History", "Initialization Failed"),
                init_result.message or translate("History", "Unknown error occurred"),
            )
            return False

        repository = init_result.data
        self._application_state.git_repository = repository

        success_template = term(
            translate("History", "Initialized project: %1"), translate("History", "Initialized repository: %1")
        )
        success_message = success_template.replace("%1", repository.absolute_path)
        self._show_info_message(
            term(translate("History", "Project Initialized"), translate("History", "Repository Initialized")),
            success_message,
        )
        Log.info(f"Initialized git repository at {repository.absolute_path}")
        return True
