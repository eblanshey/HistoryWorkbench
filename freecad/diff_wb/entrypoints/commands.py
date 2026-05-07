# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: FreeCAD command entry points for the Diff Workbench.

This module defines the FreeCAD commands that bridge user interactions
(toolbar/menu clicks) with application layer actions and UI presenters.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..resources import ICONPATH


if TYPE_CHECKING:
    from ..domain.git.models import GitRepositoryInitCandidate


class _SwapColumnsCommand:
    """Command to swap left/right columns in the diff view."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Swap Columns",
            "ToolTip": "Swap the left and right columns",
            "Pixmap": os.path.join(ICONPATH, "SwapColumns.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """Execute the swap columns action.

        TODO: Phase 8 - Implement when UI view exists.
        """
        # Phase 8: Will call view method to swap columns when UI is implemented
        pass


class _CommitCommand:
    """Command to commit staged changes."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Commit",
            "ToolTip": "Commit staged changes to git",
            "Pixmap": os.path.join(ICONPATH, "Commit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True  # Always enabled; validation happens in Activated()

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            COMMIT_EMPTY_MESSAGE,
            COMMIT_EMPTY_MESSAGE_TITLE,
            COMMIT_FAILED_TITLE,
            COMMIT_NO_REPOSITORY_MESSAGE,
            COMMIT_NO_REPOSITORY_TITLE,
            COMMIT_NO_STAGED_FILES_MESSAGE,
            COMMIT_NO_STAGED_FILES_TITLE,
        )

        container = get_container()

        # Check if we have a git repository via UIState in registry
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_NO_REPOSITORY_TITLE),
                container.translate("Commit", COMMIT_NO_REPOSITORY_MESSAGE),
            )
            return

        # Check for staged files
        staged_result = container.get_staged_file_paths_action.execute(repo)
        if not staged_result.is_success or not staged_result.data:
            QMessageBox.information(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_NO_STAGED_FILES_TITLE),
                container.translate("Commit", COMMIT_NO_STAGED_FILES_MESSAGE),
            )
            return

        # Show commit dialog with multi-line text area
        message = self._show_commit_dialog(container)

        if message is None:
            return

        if not message.strip():
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_EMPTY_MESSAGE_TITLE),
                container.translate("Commit", COMMIT_EMPTY_MESSAGE),
            )
            return

        # Execute commit action
        result = container.commit_staging_action.execute(repo, message.strip())

        if result.is_success:
            container.log("Commit successful")
            # Reload commits by triggering refresh
            ui_registry.git_repository_presenter.refresh_repository_and_commits()
        else:
            QMessageBox.critical(
                None,  # type: ignore[arg-type]
                container.translate("Commit", COMMIT_FAILED_TITLE),
                result.message or "Git commit failed",
            )

    def _show_commit_dialog(self, container) -> str | None:
        """Show the commit dialog and return the message or None if cancelled.

        Args:
            container: The application container.

        Returns:
            The commit message string if user confirmed, None if cancelled.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QPlainTextEdit,
            QPushButton,
            QVBoxLayout,
        )

        from ..ui.translation_strings import (
            COMMIT_DIALOG_PLACEHOLDER,
            COMMIT_DIALOG_PROMPT,
            COMMIT_DIALOG_TITLE,
            DIALOG_CANCEL,
            DIALOG_OK,
        )

        dialog = QDialog(None)  # type: ignore[arg-type]
        dialog.setWindowTitle(container.translate("Commit", COMMIT_DIALOG_TITLE))

        # Enable resize grip in bottom-right corner
        dialog.setSizeGripEnabled(True)

        # Create layout with text area and buttons
        layout = QVBoxLayout(dialog)

        # Add label
        from PySide6.QtWidgets import QLabel

        label = QLabel(container.translate("Commit", COMMIT_DIALOG_PROMPT))
        layout.addWidget(label)

        # Create a multi-line text editor that can resize vertically
        from PySide6.QtWidgets import QSizePolicy

        text_edit = QPlainTextEdit(dialog)
        text_edit.setPlaceholderText(container.translate("Commit", COMMIT_DIALOG_PLACEHOLDER))
        text_edit.setTabStopDistance(40)  # Tab spacing in pixels
        text_edit.setMinimumHeight(100)  # Minimum height for initial usability
        # Allow the text edit to expand vertically when dialog is resized
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(text_edit)

        # Add OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton(container.translate("Common", DIALOG_OK))
        cancel_button = QPushButton(container.translate("Common", DIALOG_CANCEL))

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Make the dialog resizable with a reasonable size
        dialog.resize(500, 300)

        ok = dialog.exec() == 1  # QDialog.Accepted = 1
        return text_edit.toPlainText() if ok else None


class _RefreshRepositoryCommand:
    """Command to refresh repository detection and reload commits."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Refresh Git Repository and Commits",
            "ToolTip": "Refresh the detected git repository and reload commits.\nOpen at least one FreeCAD document "
            "located within a git repository before running this command.\nHow it works: open FreeCAD "
            "documents are checked one by one until one is found to be located within a git repository.",
            "Pixmap": os.path.join(ICONPATH, "RefreshRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        ui_registry.git_repository_presenter.refresh_repository_and_commits()


class _InitializeGitRepositoryCommand:
    """Command to initialize a git repository from open document directories."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        from .._container import get_container
        from ..ui.translation_strings import INITIALIZE_REPOSITORY_MENU_TEXT, INITIALIZE_REPOSITORY_TOOLTIP

        container = get_container()
        return {
            "MenuText": container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_MENU_TEXT),
            "ToolTip": container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_TOOLTIP),
            "Pixmap": os.path.join(ICONPATH, "CreateGitRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            ERROR_UNKNOWN,
            INITIALIZE_REPOSITORY_FAILED_TITLE,
            INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE,
            INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE,
            INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE,
            INITIALIZE_REPOSITORY_SUCCESS_TITLE,
        )

        container = get_container()
        candidates_result = container.get_git_repository_init_candidates_action.execute()
        if not candidates_result.is_success:
            QMessageBox.information(
                None,  # type: ignore[arg-type]
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE),
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE),
            )
            return

        selected_directory = self._show_init_dialog(container, candidates_result.data)
        if selected_directory is None:
            return

        init_result = container.initialize_git_repository_action.execute(selected_directory)
        if not init_result.is_success:
            QMessageBox.critical(
                None,  # type: ignore[arg-type]
                container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_FAILED_TITLE),
                init_result.message or container.translate("Common", ERROR_UNKNOWN),
            )
            return

        repository = init_result.data
        self._store_initialized_repository(repository)

        success_template = container.translate(
            "InitializeGitRepository",
            INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE,
        )
        success_message = success_template.replace("%1", repository.absolute_path)
        QMessageBox.information(
            None,  # type: ignore[arg-type]
            container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_SUCCESS_TITLE),
            success_message,
        )
        ui_registry.git_repository_presenter.refresh_repository_and_commits()

    def _show_init_dialog(self, container, candidates: list[GitRepositoryInitCandidate]) -> str | None:
        """Show initialization selection dialog and return selected directory."""
        from PySide6.QtWidgets import (
            QButtonGroup,
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QRadioButton,
            QVBoxLayout,
        )

        from ..ui.translation_strings import (
            DIALOG_CANCEL,
            INITIALIZE_REPOSITORY_BUTTON,
            INITIALIZE_REPOSITORY_DIALOG_PROMPT,
            INITIALIZE_REPOSITORY_DIALOG_TITLE,
            INITIALIZE_REPOSITORY_DISABLED_REASON,
            INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE,
        )

        dialog = QDialog(None)  # type: ignore[arg-type]
        dialog.setWindowTitle(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DIALOG_TITLE))
        dialog.setSizeGripEnabled(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DIALOG_PROMPT)))

        button_group = QButtonGroup(dialog)
        first_available_button = None

        for index, candidate in enumerate(candidates):
            row_layout = QHBoxLayout()
            radio = QRadioButton(candidate.path, dialog)
            radio.setEnabled(candidate.is_available)
            button_group.addButton(radio, index)
            row_layout.addWidget(radio)
            if candidate.is_available and first_available_button is None:
                first_available_button = radio

            if not candidate.is_available:
                reason_label = QLabel(
                    container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_DISABLED_REASON),
                    dialog,
                )
                reason_label.setEnabled(False)
                row_layout.addWidget(reason_label)

            row_layout.addStretch()
            layout.addLayout(row_layout)

        if first_available_button is not None:
            first_available_button.setChecked(True)
        else:
            no_available_text = container.translate(
                "InitializeGitRepository",
                INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE,
            )
            layout.addWidget(QLabel(no_available_text))

        button_layout = QHBoxLayout()
        initialize_button = QPushButton(container.translate("InitializeGitRepository", INITIALIZE_REPOSITORY_BUTTON))
        initialize_button.setEnabled(first_available_button is not None)
        cancel_button = QPushButton(container.translate("Common", DIALOG_CANCEL))
        initialize_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(initialize_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setMinimumWidth(680)
        dialog.adjustSize()
        target_height = min(360, dialog.sizeHint().height() + 8)
        dialog.resize(dialog.width(), target_height)
        if dialog.exec() != 1:
            return None

        selected_id = button_group.checkedId()
        if selected_id < 0:
            return None
        return candidates[selected_id].path

    def _store_initialized_repository(self, repository) -> None:
        """Store initialized repository in UI state before refresh."""
        from ..ui.registry import ui_registry

        ui_registry.ui_state.git_repository = repository


class _OpenAllDocumentsInRepositoryCommand:
    """Command to open all .FCStd documents under detected repository."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Open All Documents in Repository",
            "ToolTip": "Open every .FCStd file found in repository. Useful for generating snapshots for all project "
            "documents.",
            "Pixmap": os.path.join(ICONPATH, "OpenAllDocuments.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from PySide6.QtWidgets import QMessageBox

        from .._container import get_container
        from ..ui.registry import ui_registry
        from ..ui.translation_strings import (
            OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE,
            OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE,
        )

        container = get_container()
        repo = ui_registry.ui_state.git_repository

        if repo is None:
            QMessageBox.warning(
                None,  # type: ignore[arg-type]
                container.translate("OpenAllDocuments", OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE),
                container.translate("OpenAllDocuments", OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE),
            )
            return

        container.open_all_documents_in_repository_action.execute(repo)


class _RecomputeAllOpenDocumentsCommand:
    """Command to recompute all open documents in FreeCAD."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Recompute All",
            "ToolTip": "Recompute every open document",
            "Pixmap": os.path.join(ICONPATH, "RecomputeAll.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()
        container.recompute_all_open_documents_action.execute()


class _RecomputeActiveDocumentCommand:
    """Command to recompute the active document in FreeCAD."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Recompute Active Document",
            "ToolTip": "Recompute the active document",
            "Pixmap": "view-refresh",  # FreeCAD's standard recompute icon (from Std_Recompute)
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container

        container = get_container()

        # Use FreeCAD port to recompute the active document
        container._freecad_port.try_recompute_active_document()


class _OpenDiffWindowCommand:
    """Command to open or focus the diff window."""

    def GetResources(self) -> dict[str, str]:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": "Open Diff Window",
            "ToolTip": "Open diff view",
            "Pixmap": os.path.join(ICONPATH, "Logo.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCADGui as Gui  # pylint: disable=import-error

        # Get the Diff workbench instance and show/create the diff panel
        workbench = Gui.getWorkbench("DiffWorkbench")
        if workbench is not None:
            workbench.create_or_show_diff_panel()


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD."""
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("DiffCommit", _CommitCommand())
    Gui.addCommand("DiffRefreshRepository", _RefreshRepositoryCommand())
    Gui.addCommand("DiffInitializeGitRepository", _InitializeGitRepositoryCommand())
    Gui.addCommand("DiffOpenAllDocumentsInRepository", _OpenAllDocumentsInRepositoryCommand())
    Gui.addCommand("DiffRecomputeAllOpenDocuments", _RecomputeAllOpenDocumentsCommand())
    Gui.addCommand("DiffRecomputeActiveDocument", _RecomputeActiveDocumentCommand())
    Gui.addCommand("DiffOpenDiffWindow", _OpenDiffWindowCommand())
