# SPDX-License-Identifier: LGPL-3.0-or-later
"""Configuration for the Diff Workbench.

This module contains hard-coded configuration defaults. In a future phase,
these will be moved to FreeCAD Preferences with runtime reload support.
"""

# Type IDs to exclude from diff computation by default
# Objects of these types and their children are removed from the diff view
# Decision: Start permissive - only exclude truly auto-generated types
EXCLUDED_TYPES = [
    "App::Origin",  # Origin elements (planes, axes) are auto-generated
]

# Property names to exclude from diff comparison
# These properties often change without meaningful semantic differences
# Auto-excluded properties (always excluded, even if user manually sets them)
AUTO_EXCLUDED_PROPERTIES = [
    # Timestamp/change tracking
    "TimeStamp",
    "LastModified",
    # Auto-generated labels
    "Label2",  # Auto-generated secondary label
    # Version tracking
    "_ElementMapVersion",  # Internal version tracking
    # Internal state tracking
    "EditorMode",  # UI-only property
    "EditorObject",  # UI-only property
]

# Additional properties to exclude (can be overridden by user configuration)
EXCLUDED_PROPERTIES = [
    *AUTO_EXCLUDED_PROPERTIES,
]
