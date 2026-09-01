# File responsibility: Handle save-iteration (commit) dialog flow and action orchestration.
"""Handle save-iteration (commit) dialog flow and action orchestration.

Owns the staged-file check, identity delegation, message dialog, and
commit-action invocation. Returns a success flag so the caller can decide
whether to refresh. Scope stays orchestration only: collect dialog input,
validate UI-level flow, call actions.
"""

from collections.abc import Callable

from ....application.actions.git_config.get_git_identity import GetGitIdentityAction
from ....application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from ....application.actions.git_workflow.commit_staging import CommitStagingAction
from ....domain.git.models import GitRepository
from ....utils import term, translate
from .author_configuration_handler import AuthorConfigurationHandler


class CommitIterationHandler:
    """Own save-iteration (commit) flow for presenter and commands."""

    def __init__(
        self,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        commit_staging_action: CommitStagingAction,
        get_git_identity_action: GetGitIdentityAction,
        author_configuration_handler: AuthorConfigurationHandler,
        show_save_iteration_dialog: Callable[[], str | None],
        show_warning_message: Callable[[str, str], None],
        show_info_message: Callable[[str, str], None],
        show_error_message: Callable[[str, str], None],
    ) -> None:
        """Store action and dialog dependencies."""
        self._get_staged_file_paths_action = get_staged_file_paths_action
        self._commit_staging_action = commit_staging_action
        self._get_git_identity_action = get_git_identity_action
        self._author_handler = author_configuration_handler
        self._show_save_iteration_dialog = show_save_iteration_dialog
        self._show_warning_message = show_warning_message
        self._show_info_message = show_info_message
        self._show_error_message = show_error_message

    def execute(self, repo: GitRepository) -> bool:
        """Run full save-iteration flow.

        Checks for staged files, ensures git identity is configured,
        collects the commit message, and executes the commit.

        Args:
            repo: The git repository to commit in.

        Returns:
            True if the commit succeeded, False otherwise.
        """
        staged_result = self._get_staged_file_paths_action.execute(repo)
        if not staged_result.is_success or not staged_result.data:
            self._show_info_message(
                term(translate("History", "No Reviewed Files"), translate("History", "No Staged Files")),
                term(
                    translate("History", "There are no reviewed files to save."),
                    translate("History", "There are no staged files to commit."),
                ),
            )
            return False

        # Skip author dialog if identity is already configured
        identity_result = self._get_git_identity_action.execute(repo)

        # Identity missing; show configuration dialog
        if identity_result.data is None and not self._author_handler.execute(repo):
            return False

        commit_message = self._show_save_iteration_dialog()
        if commit_message is None:
            return False

        trimmed_message = commit_message.strip()
        if not trimmed_message:
            self._show_warning_message(
                translate("History", "Empty Notes"),
                term(
                    translate("History", "Iteration notes cannot be empty"),
                    translate("History", "Commit notes cannot be empty"),
                ),
            )
            return False

        result = self._commit_staging_action.execute(repo, trimmed_message)
        if result.is_success:
            return True

        self._show_error_message(
            term(translate("History", "Save Iteration Failed"), translate("History", "Commit Failed")),
            result.message or translate("History", "Git commit failed"),
        )
        return False
