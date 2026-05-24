# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Core package initialization for Project History Workbench,
# providing version information and serving as the main entry point
# for FreeCAD workbench registration via init_gui.py.
"""Project History Workbench - A FreeCAD workbench for tracking project iterations."""

from .version import __version__


__all__ = ["__version__"]
