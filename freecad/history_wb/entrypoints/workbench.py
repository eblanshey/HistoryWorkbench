# File responsibility: Defines the HistoryWorkbench class that integrates
# the workbench into FreeCAD's GUI with menus, toolbars, and a native History view.
# Container initialization is deferred to Activated() for faster startup.
"""FreeCAD workbench registration and native History view lifecycle.

Defines the Gui.Workbench subclass used by FreeCAD to create menus/toolbars
and activate the workbench. Commands are registered during Initialize();
container creation is deferred to Activated() for faster FreeCAD startup.
"""

import os
import traceback
from typing import cast

from ..qt import QtCore, QtGui, QtWidgets
from ..resources import ICONPATH
from ..utils import Log, set_logger, translate


_PREFERENCES_REGISTRY_ATTR = "_history_wb_preference_pages"
_PREFERENCES_PAGE_ID = "freecad.history_wb.ui.views.settings_preferences_page.DiffSettingsPreferencesPage"


try:
    import FreeCADGui as Gui  # pylint: disable=import-error
    from FreeCADGui import getMainWindow  # noqa: N813
except ImportError as e:
    Log.exception(f"Failed to import FreeCADGui: {e}")
    Gui = None  # type: ignore[assignment]
    getMainWindow = None  # type: ignore[assignment]  # noqa: N816


if Gui is not None:

    class HistoryWorkbench(Gui.Workbench):
        """Workbench class for the History Workbench addon."""

        _preferences_page_registered = False

        Icon = os.path.join(ICONPATH, "Logo.svg")
        toolbar_commands = [
            "HistoryOpenDiffWindow",
            "HistoryRefreshRepository",
            "HistoryRecomputeActiveDocument",
            "HistoryRecomputeAllOpenDocuments",
            "HistoryOpenAllDocumentsInRepository",
            "HistoryInitializeGitRepository",
            "HistoryCloseDiffWindows",
            "HistoryCommit",
        ]
        menu_commands = [
            *toolbar_commands,
            "HistoryConfigureAuthorCommand",
            "HistoryUpdateGitIgnore",
        ]

        def __init__(self) -> None:
            super().__init__()
            self.MenuText = cast(str, QtCore.QT_TRANSLATE_NOOP("Workbench", "History"))
            self.ToolTip = cast(str, QtCore.QT_TRANSLATE_NOOP("Workbench", "Track project iterations and history"))

            # Native Qt host and FreeCAD view handle share one lifetime.
            self._history_window: tuple[QtWidgets.QWidget, object] | None = None

        def GetClassName(self) -> str:
            """Return the class name of the workbench."""
            return "Gui::PythonWorkbench"

        def Initialize(self) -> None:
            """Called at first activation; register commands and setup UI structure."""

            from ..entrypoints.commands import register_commands

            # Register commands (lightweight - just registers command names with FreeCAD)
            register_commands()

            # Setup toolbar and menu
            self.appendToolbar(
                cast(str, QtCore.QT_TRANSLATE_NOOP("Workbench", "History")),
                self.toolbar_commands,
            )
            self.appendMenu(
                cast(str, QtCore.QT_TRANSLATE_NOOP("Workbench", "History")),
                self.menu_commands,
            )

        @classmethod
        def _register_preferences_page(cls) -> None:
            if cls._preferences_page_registered:
                return
            if Gui is None:
                return

            registry = getattr(Gui, _PREFERENCES_REGISTRY_ATTR, None)
            if not isinstance(registry, set):
                registry = set()
                setattr(Gui, _PREFERENCES_REGISTRY_ATTR, registry)
            if _PREFERENCES_PAGE_ID in registry:
                cls._preferences_page_registered = True
                return

            from ..ui.views.settings_preferences_page import DiffSettingsPreferencesPage

            Gui.addPreferencePage(DiffSettingsPreferencesPage, translate("Workbench", "History"))
            registry.add(_PREFERENCES_PAGE_ID)
            cls._preferences_page_registered = True

        def Activated(self) -> None:
            """Called when user switches to this workbench."""
            try:
                Log.debug("Workbench history_wb activated.")

                # Create container on first activation (deferred from Initialize for faster startup)
                if not getattr(self, "_container_initialized", False):
                    self._initialize_container()
                    self._container_initialized = True

                self.create_or_show_diff_panel()
            except (RuntimeError, AttributeError, TypeError) as e:
                Log.exception(f"Error in Activated(): {e}")

        def _initialize_container(self) -> None:
            """Create application container and set up global state."""
            from .._container import set_container
            from ..application.container import create_application_container
            from ..entrypoints.commands import register_commands
            from ..infrastructure.freecad.logger import FreeCADLogger
            from ..infrastructure.freecad.ports import get_freecad_runtime_context
            from ..ui.composer import compose_and_register_workbench_commands
            from ..ui.registry import ui_registry
            from ..ui.state import ApplicationState
            from ..ui.views.settings_preferences_page import DiffSettingsPreferencesPage

            # Create runtime context
            ctx = get_freecad_runtime_context()

            # Create container (wires all actions/presenters)
            container = create_application_container(ctx)

            # Initialize global logger with FreeCAD logger
            set_logger(FreeCADLogger(container._freecad_port))

            # Make container globally available
            set_container(container)

            # Create and register application state (survives panel open/close)
            application_state = ApplicationState(git_repository=None)
            ui_registry.register_application_state(application_state)

            # Create and register workbench command presenter (app-scoped, survives panel close)
            compose_and_register_workbench_commands(container, application_state)

            # Re-register commands now that container exists
            register_commands()

            # Configure preferences page with actual container
            DiffSettingsPreferencesPage.configure_actions(
                container.get_diff_settings_action,
                container.save_diff_settings_action,
            )

            # Register preferences page (now that actions are configured)
            self._register_preferences_page()

            Log.debug("Application container initialized")

        def create_or_show_diff_panel(self) -> None:
            """Create the diff panel if it doesn't exist, or show/focus it if it does."""
            try:
                # Create the native view if it was closed or never created.
                if self._history_window is None:
                    self._create_diff_panel()
                else:
                    self._show_diff_panel(*self._history_window)
            except (RuntimeError, AttributeError, TypeError) as e:
                Log.exception(f"Error creating/showing diff panel: {e}")

        def Deactivated(self) -> None:
            """Called when this workbench is deactivated."""
            Log.debug("Workbench history_wb de-activated.")

            # Don't hide the native view - let it stay visible like other FreeCAD panels
            # This prevents interference with FreeCAD's default view management
            # Presenter reference is kept alive; cleaned up when the native view is destroyed

        def _create_diff_panel(self) -> None:
            """Create UI components and register them."""
            if getMainWindow is None:
                Log.warning("FreeCADGui not available")
                return

            try:
                from .._container import get_container
                from ..ui.composer import compose_and_register_panel
                from ..ui.registry import ui_registry

                # Use FreeCAD's native host so activation updates its overlay policy.
                main_window = getMainWindow()

                # Compose UI and register presenters globally
                # Application state is pre-created during container init; passed in here
                view = compose_and_register_panel(
                    get_container(),
                    ui_registry.application_state,
                    self._focus_diff_panel_deferred,
                )

                view.setWindowTitle(translate("History", "History"))
                native_view = main_window.addWindow(view)
                native_window = view.parentWidget()
                if native_view is None or native_window is None:
                    raise RuntimeError("FreeCAD did not create a native History view")
                subwindow = native_window.parentWidget()
                if not isinstance(subwindow, QtWidgets.QMdiSubWindow):
                    raise RuntimeError("FreeCAD did not attach the History view to an MDI subwindow")

                icon = QtGui.QIcon(os.path.join(ICONPATH, "Logo.svg"))
                native_window.setWindowIcon(icon)
                subwindow.setWindowIcon(icon)
                self._history_window = (native_window, native_view)

                # MDI shells can be replaced when detaching or redocking the same native view.
                native_window.destroyed.connect(self._on_history_window_closed)
                self._show_diff_panel(native_window, native_view)

            except (ImportError, AttributeError, TypeError, RuntimeError) as e:
                Log.exception(f"ERROR creating diff panel: {e} traceback: {traceback.format_exc()}")

        def _on_history_window_closed(self) -> None:
            """Clear panel-scoped state when the native History view is destroyed."""
            Log.debug("Diff panel closed.")
            self._history_window = None  # Recreate the view on the next activation.

            # Clear panel-scoped presenters; application state survives for command access
            from ..ui.registry import ui_registry

            ui_registry.clear_presenters()

        def _show_diff_panel(self, window: QtWidgets.QWidget, native_view: object) -> None:
            """Show History and synchronize Qt focus with FreeCAD's active view."""
            window.show()
            window.raise_()
            window.activateWindow()
            getMainWindow().setActiveWindow(native_view)

        def _focus_diff_panel_deferred(self) -> None:
            """Queue focus on the same History instance after FreeCAD activation events settle."""
            history_window = self._history_window
            if history_window is None:
                return

            def _focus() -> None:

                # A queued request must not focus a replacement panel after close and reopen.
                if self._history_window is history_window:
                    self._show_diff_panel(*history_window)

            QtCore.QTimer.singleShot(75, _focus)
