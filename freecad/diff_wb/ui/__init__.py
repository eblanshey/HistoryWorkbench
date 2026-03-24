"""Module responsibility: User interface."""

# Lazy imports for Qt widgets - only load when FreeCAD GUI is available
try:
    from .views.diff_panel_view import DiffPanelView
except ImportError:
    # PySide6 not available (running outside FreeCAD)
    DiffPanelView = None  # type: ignore

__all__ = ["DiffPanelView"]
