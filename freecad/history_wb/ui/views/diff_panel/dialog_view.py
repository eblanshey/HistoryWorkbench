"""File responsibility: Concrete dialog view that anchors modal UI to diff panel widget."""

from ....domain.git.models import GitRepositoryInitCandidate
from ....qt import QtWidgets
from .dialogs import (
    GitConfigDialogResult,
    show_configure_author_dialog,
    show_gitignore_editor_dialog,
    show_init_repository_dialog,
    show_restore_file_confirmation_dialog,
    show_restore_scope_dialog,
    show_save_iteration_dialog,
)
from .messages import show_error_message, show_info_message, show_warning_message


__all__ = ["DialogView"]


class DialogView:
    """Wrap modal dialog and message helpers with a stable presenter-facing object."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        self._parent = parent

    def show_warning_message(self, title: str, message: str) -> None:
        """Show warning dialog anchored to panel widget."""
        show_warning_message(self._parent, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """Show informational dialog anchored to panel widget."""
        show_info_message(self._parent, title, message)

    def show_error_message(self, title: str, message: str) -> None:
        """Show error dialog anchored to panel widget."""
        show_error_message(self._parent, title, message)

    def show_save_iteration_dialog(self) -> str | None:
        """Show Save Iteration dialog and return notes when accepted."""
        return show_save_iteration_dialog(self._parent)

    def show_configure_author_dialog(
        self,
        *,
        message: str | None = None,
        initial_values: GitConfigDialogResult | None = None,
        global_config_writable: bool = True,
    ) -> GitConfigDialogResult | None:
        """Show configure-author dialog and return entered values."""
        return show_configure_author_dialog(
            self._parent,
            message=message,
            initial_values=initial_values,
            global_config_writable=global_config_writable,
        )

    def show_restore_file_confirmation_dialog(self, git_path: str, last_reviewed_or_saved: bool) -> bool:
        """Show destructive confirmation dialog for file restore."""
        return show_restore_file_confirmation_dialog(self._parent, git_path, last_reviewed_or_saved)

    def show_restore_scope_dialog(self) -> str | None:
        """Show restore-all scope picker dialog."""
        return show_restore_scope_dialog(self._parent)

    def show_init_repository_dialog(
        self,
        candidates: list[GitRepositoryInitCandidate],
    ) -> str | None:
        """Show repository initialization dialog and return selected directory."""
        return show_init_repository_dialog(self._parent, candidates)

    def show_gitignore_editor_dialog(self, content: str) -> str | None:
        """Show gitignore editor dialog and return edited content."""
        return show_gitignore_editor_dialog(self._parent, content)
