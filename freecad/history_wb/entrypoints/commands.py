# File responsibility: FreeCAD command entry points for the Diff Workbench.
# Commands delegate to the app-scoped WorkbenchCommandPresenter for shared
# command flows, keeping them usable after the diff panel is closed.
"""FreeCAD command entry points for the Diff Workbench."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypedDict

from ..qt import QtCore
from ..resources import ICONPATH
from ..utils import Log, term, translate


if TYPE_CHECKING:
    from ..qt import QtWidgets
    from ..ui.views.diff_panel import DialogView

    QWidget = QtWidgets.QWidget


def _main_window_parent(container) -> QWidget | None:
    """Get the FreeCAD main window as a parent widget for dialogs.

    Args:
        container: The application container with _freecad_port attribute

    Returns:
        QWidget parent or None if not available
    """
    main_window = container._freecad_port.get_main_window()
    return main_window  # type: ignore[return-value]


def _create_dialog_view(container) -> DialogView:
    """Create a DialogView anchored to the FreeCAD main window.

    Used by the command that needs to show a warning when no repo exists
    but are not covered by the command presenter flows.
    """
    from ..ui.views.diff_panel import DialogView

    parent = _main_window_parent(container)
    if parent is None:
        raise RuntimeError("FreeCAD main window not available")
    return DialogView(parent)


def _refresh_git_repository_presenter_if_open() -> None:
    """Refresh the git repository presenter if the panel is currently open."""
    from ..ui.registry import ui_registry

    presenter = ui_registry.git_repository_presenter
    if presenter is not None:
        presenter.refresh_repository_and_commits()


class CommandResources(TypedDict):
    """Shape of FreeCAD command metadata returned by GetResources."""

    MenuText: object
    ToolTip: object
    Pixmap: str


class _ConfigureAuthorCommand:
    """Command to configure author identity."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryConfigureAuthorCommand", "Configure Author"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryConfigureAuthorCommand", "Configure author name and email"),
            "Pixmap": os.path.join(ICONPATH, "ConfigureGit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        ui_registry.workbench_command_presenter.configure_author()


class _CommitCommand:
    """Command to save iteration."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Save Iteration"),
                QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Commit"),
            ),
            "ToolTip": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Save reviewed changes as an iteration"),
                QtCore.QT_TRANSLATE_NOOP("HistoryCommit", "Commit the staged changes"),
            ),
            "Pixmap": os.path.join(ICONPATH, "Commit.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True  # Always enabled; validation happens in Activated()

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        success = ui_registry.workbench_command_presenter.save_iteration()
        if success:
            Log.info("Commit successful")
            _refresh_git_repository_presenter_if_open()


class _RefreshRepositoryCommand:
    """Command to refresh project detection and reload iterations."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryRefreshRepository", "Refresh Project"),
                QtCore.QT_TRANSLATE_NOOP("HistoryRefreshRepository", "Refresh Repository"),
            ),
            "ToolTip": term(
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryRefreshRepository",
                    "Refresh the detected project and reload iterations.\n"
                    "Open at least one FreeCAD document "
                    "located within a project before running this command.\n"
                    "How it works: open FreeCAD "
                    "documents are checked one by one until one is found to be located within a project.",
                ),
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryRefreshRepository",
                    "Refresh the detected repository and reload commits.\n"
                    "Open at least one FreeCAD document "
                    "located within a repository before running this command.\n"
                    "How it works: open FreeCAD "
                    "documents are checked one by one until one is found to be located within a repository.",
                ),
            ),
            "Pixmap": os.path.join(ICONPATH, "RefreshRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        ui_registry.workbench_command_presenter.refresh_git_repository()


class _InitializeGitRepositoryCommand:
    """Command to initialize a git repository from open document directories."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryInitializeGitRepository", "Initialize Project"),
                QtCore.QT_TRANSLATE_NOOP("HistoryInitializeGitRepository", "Initialize Repository"),
            ),
            "ToolTip": term(
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryInitializeGitRepository",
                    "Initialize a new project in the selected directory",
                ),
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryInitializeGitRepository",
                    "Initialize a new repository in the selected directory",
                ),
            ),
            "Pixmap": os.path.join(ICONPATH, "CreateGitRepository.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        initialized = ui_registry.workbench_command_presenter.initialize_repository()
        if initialized:
            _refresh_git_repository_presenter_if_open()


class _OpenAllDocumentsInRepositoryCommand:
    """Command to open all .FCStd documents under detected repository."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryOpenAllDocumentsInRepository",
                    "Open All Documents in Project",
                ),
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryOpenAllDocumentsInRepository",
                    "Open All Documents in Repository",
                ),
            ),
            "ToolTip": term(
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryOpenAllDocumentsInRepository",
                    "Open every .FCStd file found in the project. Useful for generating en masse.",
                ),
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryOpenAllDocumentsInRepository",
                    "Open every .FCStd file found in the repository. Useful for generating en masse.",
                ),
            ),
            "Pixmap": os.path.join(ICONPATH, "OpenAllDocuments.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from .._container import get_container
        from ..ui.registry import ui_registry

        container = get_container()
        try:
            dialog_view = _create_dialog_view(container)
        except RuntimeError:
            return

        repo = ui_registry.application_state.git_repository
        if repo is None:
            dialog_view.show_warning_message(
                term(
                    translate("History", "No Project"),
                    translate("History", "No Repository"),
                ),
                term(
                    translate("History", "No project detected. Open a FreeCAD document in a project first."),
                    translate("History", "No repository detected. Open a FreeCAD document in a repository first."),
                ),
            )
            return

        container.open_all_documents_in_repository_action.execute(repo)


class _UpdateGitIgnoreCommand:
    """Command to edit repository .gitignore content."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryUpdateGitIgnore", "Edit Ignored Files"),
                QtCore.QT_TRANSLATE_NOOP("HistoryUpdateGitIgnore", "Edit .gitignore"),
            ),
            "ToolTip": term(
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryUpdateGitIgnore",
                    "Edit project ignored files list (.gitignore)",
                ),
                QtCore.QT_TRANSLATE_NOOP(
                    "HistoryUpdateGitIgnore",
                    "Edit repository ignored files list (.gitignore)",
                ),
            ),
            "Pixmap": os.path.join(ICONPATH, "GitIgnore.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        from ..ui.registry import ui_registry

        ui_registry.workbench_command_presenter.update_gitignore()


class _RecomputeAllOpenDocumentsCommand:
    """Command to recompute all open documents in FreeCAD."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeAllOpenDocuments", "Recompute All"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeAllOpenDocuments", "Recompute every open document"),
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

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeActiveDocument", "Recompute Active Document"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryRecomputeActiveDocument", "Recompute the active document"),
            "Pixmap": os.path.join(ICONPATH, "RecomputeActiveDocument.svg"),
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
    """Command to open or focus the history panel."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": QtCore.QT_TRANSLATE_NOOP("HistoryOpenDiffWindow", "Open History Panel"),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP("HistoryOpenDiffWindow", "Open history panel view"),
            "Pixmap": os.path.join(ICONPATH, "Logo.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCADGui as Gui  # pylint: disable=import-error

        # Get the History workbench instance and show/create the diff panel
        workbench = Gui.getWorkbench("HistoryWorkbench")
        if workbench is not None:
            workbench.create_or_show_diff_panel()


class _CloseDiffWindowsCommand:
    """Command to close all Diff_* windows without saving."""

    def GetResources(self) -> CommandResources:
        """Return FreeCAD command metadata for UI integration."""
        return {
            "MenuText": term(
                QtCore.QT_TRANSLATE_NOOP("HistoryCloseDiffWindows", "Close Comparison Windows"),
                QtCore.QT_TRANSLATE_NOOP("HistoryCloseDiffWindows", "Close Diff Windows"),
            ),
            "ToolTip": QtCore.QT_TRANSLATE_NOOP(
                "HistoryCloseDiffWindows",
                "Close every document starting with 'Diff_' without saving",
            ),
            "Pixmap": os.path.join(ICONPATH, "DiffCloseDiffWindows.svg"),
        }

    def IsActive(self) -> bool:
        """Return whether the command should be enabled."""
        return True

    def Activated(self) -> None:
        """FreeCAD calls this when user clicks toolbar button."""
        import FreeCAD as App  # pylint: disable=import-error

        # Get list of document names to close (iterate over copy to avoid modification during iteration)
        docs_to_close = [doc_name for doc_name in App.listDocuments() if doc_name.startswith("Diff_")]

        # Close each document without saving
        for doc_name in docs_to_close:
            App.closeDocument(doc_name)


def register_commands() -> None:
    """Register the Diff Workbench commands with FreeCAD.

    Command labels resolve the git-terminology toggle inside GetResources via
    term(), so no wrapper is needed. FreeCAD queries GetResources at Initialize
    (before the container exists); term() reads the toggle directly from
    preferences in that case.
    """
    import FreeCADGui as Gui  # pylint: disable=import-error

    Gui.addCommand("HistoryConfigureAuthorCommand", _ConfigureAuthorCommand())
    Gui.addCommand("HistoryCommit", _CommitCommand())
    Gui.addCommand("HistoryRefreshRepository", _RefreshRepositoryCommand())
    Gui.addCommand("HistoryInitializeGitRepository", _InitializeGitRepositoryCommand())
    Gui.addCommand("HistoryUpdateGitIgnore", _UpdateGitIgnoreCommand())
    Gui.addCommand("HistoryOpenAllDocumentsInRepository", _OpenAllDocumentsInRepositoryCommand())
    Gui.addCommand("HistoryRecomputeAllOpenDocuments", _RecomputeAllOpenDocumentsCommand())
    Gui.addCommand("HistoryRecomputeActiveDocument", _RecomputeActiveDocumentCommand())
    Gui.addCommand("HistoryOpenDiffWindow", _OpenDiffWindowCommand())
    Gui.addCommand("HistoryCloseDiffWindows", _CloseDiffWindowsCommand())
