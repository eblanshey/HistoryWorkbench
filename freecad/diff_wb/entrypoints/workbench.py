# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Defines the DiffWorkbench class that integrates
# the workbench into FreeCAD's GUI with menus and toolbars.
"""FreeCAD workbench registration for Diff Workbench.

Defines the Gui.Workbench subclass used by FreeCAD to create menus/toolbars
and activate the workbench.
"""

import os

from .._container import _container
from ..resources import ICONPATH


try:
    import FreeCADGui as Gui  # pylint: disable=import-error
    from FreeCADGui import getMainWindow  # noqa: N813
except Exception:  # pylint: disable=broad-exception-caught
    Gui = None
    getMainWindow = None  # noqa: N816


if Gui is not None:

    class DiffWorkbench(Gui.Workbench):
        """Workbench class for the Diff Workbench addon."""

        MenuText = _container.translate("Workbench", "Diff Workbench")
        ToolTip = _container.translate("Workbench", "Compare document snapshots")
        Icon = os.path.join(ICONPATH, "Logo.svg")
        toolbox = [
            "DiffTakeSnapshot",
            "DiffCompare",
            "DiffSwapColumns",
        ]

        def __init__(self):
            super().__init__()
            self._subwindow = None  # Store reference to MDI subwindow

        def GetClassName(self) -> str:
            """Return the class name of the workbench."""
            return "Gui::PythonWorkbench"

        def Initialize(self) -> None:
            """Called at first activation; import all commands."""
            import FreeCAD as App  # pylint: disable=import-error

            _container.log(_container.translate("Log", "Switching to diff_wb") + "\n")

            qt_translate_noop = App.Qt.QT_TRANSLATE_NOOP

            # NOTE: Context for these commands must be "Workbench"
            self.appendToolbar(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)
            self.appendMenu(qt_translate_noop("Workbench", "Diff Workbench"), self.toolbox)

        def Activated(self) -> None:
            """Called when user switches to this workbench."""
            _container.log(_container.translate("Log", "Workbench diff_wb activated.") + "\n")

            # Create and show MDI subwindow if not already created
            if self._subwindow is None:
                self._create_diff_panel()
            else:
                # Show existing subwindow if it was hidden
                self._subwindow.show()

        def Deactivated(self) -> None:
            """Called when this workbench is deactivated."""
            _container.log(_container.translate("Log", "Workbench diff_wb de-activated.") + "\n")

            # Hide subwindow (don't destroy - keep state)
            if self._subwindow:
                self._subwindow.hide()

        def _create_diff_panel(self) -> None:
            """Create the 3-column diff panel as an MDI subwindow."""
            if getMainWindow is None:
                _container.log("Warning: FreeCADGui not available\n")
                return

            from PySide6.QtWidgets import QMdiArea

            from ..ui import DiffPanelView

            # Get MDI area from FreeCAD's main window
            main_window = getMainWindow()
            mdi_area = main_window.findChild(QMdiArea)

            if mdi_area is None:
                _container.log("Warning: Could not get MDI area\n")
                return

            # Create panel
            panel = DiffPanelView()

            # Add as subwindow (QMdiSubWindow created automatically)
            self._subwindow = mdi_area.addSubWindow(panel)
            panel.setParent(mdi_area)  # Important: set parent to MDI area

            # Configure subwindow
            self._subwindow.setWindowTitle("Diff View")
            self._subwindow.show()
