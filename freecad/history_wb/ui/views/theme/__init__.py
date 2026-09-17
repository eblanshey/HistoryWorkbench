"""Module responsibility: Shared theme helpers for Qt view widgets."""

from .diff import (
    DiffInteractionColors,
    background_for_state,
    colors_for_diff_state,
    foreground_for_background,
    hover_background_for,
    palette_with_resolved_text,
    selected_background_for,
)
from .icons import set_themed_icon


__all__ = [
    "DiffInteractionColors",
    "background_for_state",
    "colors_for_diff_state",
    "foreground_for_background",
    "hover_background_for",
    "palette_with_resolved_text",
    "selected_background_for",
    "set_themed_icon",
]
