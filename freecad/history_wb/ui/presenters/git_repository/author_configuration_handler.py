# File responsibility: Handle author identity configuration dialog flow and action orchestration.
"""Handle author identity configuration dialog flow and action orchestration.

Owns the multi-step flow for checking, prompting, and saving git identity,
including the global-to-local fallback retry loop. Remains orchestration/UI-flow
code, not a new application use case.
"""

from collections.abc import Callable

from ....application.actions.git_config.can_write_global_git_identity import (
    CanWriteGlobalGitIdentityAction,
)
from ....application.actions.git_config.get_git_identity import GetGitIdentityAction
from ....application.actions.git_config.save_git_identity import SaveGitIdentityAction
from ....domain.git.models import GitIdentity, GitRepository
from ....utils import term, translate
from ...views.diff_panel.dialogs import GitConfigDialogResult


class AuthorConfigurationHandler:
    """Own author identity configuration flow for presenter and commands."""

    def __init__(
        self,
        get_git_identity_action: GetGitIdentityAction,
        save_git_identity_action: SaveGitIdentityAction,
        can_write_global_git_identity_action: CanWriteGlobalGitIdentityAction,
        show_configure_author_dialog: Callable[..., GitConfigDialogResult | None],
        show_warning_message: Callable[[str, str], None],
        show_error_message: Callable[[str, str], None],
    ) -> None:
        """Store action and dialog dependencies."""
        self._get_git_identity_action = get_git_identity_action
        self._save_git_identity_action = save_git_identity_action
        self._can_write_global_git_identity_action = can_write_global_git_identity_action
        self._show_configure_author_dialog = show_configure_author_dialog
        self._show_warning_message = show_warning_message
        self._show_error_message = show_error_message

    def execute(self, repo: GitRepository) -> bool:
        """Run full author configuration flow.

        Shows the configure-author dialog, validates input, saves identity,
        and retries with a local-only fallback when global save fails.

        Args:
            repo: The git repository to configure identity for.

        Returns:
            True if identity was saved successfully, False otherwise.
        """
        retry_message: str | None = None
        initial_values = self._configured_identity_dialog_values(repo)
        global_config_writable = self._can_write_global_identity()

        while True:
            dialog_result = self._show_configure_author_dialog(
                message=retry_message,
                initial_values=initial_values,
                global_config_writable=global_config_writable,
            )
            if dialog_result is None:
                return False

            if not dialog_result.author_name or not dialog_result.author_email:
                self._show_warning_message(
                    term(translate("History", "Save Iteration Failed"), translate("History", "Commit Failed")),
                    term(
                        translate("History", "Name and email are required to save iteration"),
                        translate("History", "Name and email are required to commit"),
                    ),
                )
                return False

            save_result = self._save_git_identity_action.execute(
                repo,
                GitIdentity(name=dialog_result.author_name, email=dialog_result.author_email),
                dialog_result.should_save_globally,
            )
            if save_result.is_success:
                return True

            # Local save failed; give up
            if not dialog_result.should_save_globally:
                self._show_error_message(
                    term(translate("History", "Save Iteration Failed"), translate("History", "Commit Failed")),
                    translate("History", "Git identity could not be saved"),
                )
                return False

            # Global save failed; retry with local-only option
            retry_message = term(
                translate(
                    "History",
                    "Could not save git identity for all projects. "
                    "Uncheck the global option to save it only for this project.",
                ),
                translate(
                    "History",
                    "Could not save git identity for all repositories. "
                    "Uncheck the global option to save it only for this repository.",
                ),
            )
            initial_values = dialog_result

    def _can_write_global_identity(self) -> bool:
        """Return whether global git identity config can be written."""
        result = self._can_write_global_git_identity_action.execute()
        if not result.is_success:
            return False
        return bool(result.data)

    def _configured_identity_dialog_values(
        self,
        repo: GitRepository,
    ) -> GitConfigDialogResult | None:
        """Return existing git identity as dialog defaults when configured."""
        identity_result = self._get_git_identity_action.execute(repo)
        identity = identity_result.data
        if identity is None:
            return None
        return GitConfigDialogResult(
            author_name=identity.name,
            author_email=identity.email,
            should_save_globally=False,
        )
