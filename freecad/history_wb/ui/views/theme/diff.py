"""File responsibility: Theme-aware semantic diff colors for widget-backed views."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ....domain.diff.models import DiffState
from ....qt import QtGui, QtWidgets
from .colors import (
    _blend_colors,
    _color_from_key,
    _color_key,
    _ColorKey,
    _contrast_ratio,
    _palette_from_key,
    _palette_key,
    _palette_theme_colors,
    _PaletteKey,
    _theme_is_dark,
)


__all__ = [
    "DiffInteractionColors",
    "apply_diff_state_to_widget",
    "background_for_state",
    "colors_for_diff_state",
    "foreground_for_background",
    "hover_background_for",
    "selected_background_for",
]

# Minimum contrast target for normal-sized UI text. This follows the WCAG AA
# 4.5:1 guidance and keeps diff labels readable across light and dark themes.
_MIN_CONTRAST = 4.5

# First-pass accent blend for dark themes. Light themes use direct pastel
# colors so they match the original bright diff highlights with black text.
_DARK_ACCENT_BLEND = 0.38

# Fallback blend ratios move gradually toward pure accent color until the chosen
# text color reaches the contrast target.
_CONTRAST_FALLBACK_BLEND_RATIOS = (0.45, 0.52, 0.60, 0.70, 0.82, 1.0)
_LAST_FALLBACK_BLEND = 0.52
_HOVER_BLEND = 0.22
_SELECTED_BLEND = 0.42

# Diff accents are paired as (light-theme accent, dark-theme accent). Light
# variants preserve the original bright pastel highlights. Dark variants are
# brighter saturated targets so they remain visible when blended into dark
# palettes.
_ADDED_LIGHT_ACCENT = QtGui.QColor(200, 255, 200)  # #C8FFC8
_ADDED_DARK_ACCENT = QtGui.QColor(48, 219, 91)  # #30DB5B
_DELETED_LIGHT_ACCENT = QtGui.QColor(255, 200, 200)  # #FFC8C8
_DELETED_DARK_ACCENT = QtGui.QColor(255, 105, 97)  # #FF6961
_MODIFIED_LIGHT_ACCENT = QtGui.QColor(200, 200, 255)  # #C8C8FF
_MODIFIED_DARK_ACCENT = QtGui.QColor(116, 192, 252)  # #74C0FC


@dataclass(frozen=True)
class DiffInteractionColors:
    """Colors for normal, hovered, and selected rendering of one diff state."""

    normal_background: QtGui.QColor | None
    normal_foreground: QtGui.QColor
    hover_background: QtGui.QColor
    hover_foreground: QtGui.QColor
    selected_background: QtGui.QColor
    selected_foreground: QtGui.QColor


def background_for_state(state: DiffState, palette: QtGui.QPalette) -> QtGui.QColor | None:
    """Return theme-aware background color for diff state.

    Unchanged rows return None so they inherit the normal theme background.
    """
    palette_cache_key = _palette_key(palette)
    return _cached_background_for_state(state, palette_cache_key)


@lru_cache(maxsize=96)
def _cached_background_for_state(state: DiffState, palette_cache_key: _PaletteKey) -> QtGui.QColor | None:
    """Return cached background for state and palette colors.

    Painting can call this once per visible cell, while many cells share the
    same application palette and diff state. Cache prevents repeating WCAG math.
    """
    palette = _palette_from_key(palette_cache_key)
    if state == DiffState.ADDED:
        return _state_background(palette, _ADDED_LIGHT_ACCENT, _ADDED_DARK_ACCENT)
    if state == DiffState.DELETED:
        return _state_background(palette, _DELETED_LIGHT_ACCENT, _DELETED_DARK_ACCENT)
    if state == DiffState.MODIFIED:
        return _state_background(palette, _MODIFIED_LIGHT_ACCENT, _MODIFIED_DARK_ACCENT)
    return None


def foreground_for_background(background: QtGui.QColor, palette: QtGui.QPalette) -> QtGui.QColor:
    """Return readable text color for a background and current palette.

    Prefer the theme text color when possible, then fall back to black or white.
    """
    return _cached_foreground_for_background(_color_key(background), _palette_key(palette))


def hover_background_for(background: QtGui.QColor, palette: QtGui.QPalette) -> QtGui.QColor:
    """Blend one semantic background toward theme highlight for hover feedback."""
    return _blend_colors(background, palette.color(QtGui.QPalette.ColorRole.Highlight), _HOVER_BLEND)


def selected_background_for(background: QtGui.QColor, palette: QtGui.QPalette) -> QtGui.QColor:
    """Blend one semantic background toward theme highlight for selection feedback."""
    return _blend_colors(background, palette.color(QtGui.QPalette.ColorRole.Highlight), _SELECTED_BLEND)


def colors_for_diff_state(state: DiffState, palette: QtGui.QPalette) -> DiffInteractionColors:
    """Return complete interaction colors for one semantic diff state."""
    background = background_for_state(state, palette)
    if background is None:
        hover_background = hover_background_for(palette.color(QtGui.QPalette.ColorRole.Base), palette)
        selected_background = palette.color(QtGui.QPalette.ColorRole.Highlight)
        return DiffInteractionColors(
            normal_background=None,
            normal_foreground=palette.color(QtGui.QPalette.ColorRole.Text),
            hover_background=hover_background,
            hover_foreground=foreground_for_background(hover_background, palette),
            selected_background=selected_background,
            selected_foreground=palette.color(QtGui.QPalette.ColorRole.HighlightedText),
        )

    hover_background = hover_background_for(background, palette)
    selected_background = selected_background_for(background, palette)
    return DiffInteractionColors(
        normal_background=background,
        normal_foreground=foreground_for_background(background, palette),
        hover_background=hover_background,
        hover_foreground=foreground_for_background(hover_background, palette),
        selected_background=selected_background,
        selected_foreground=foreground_for_background(selected_background, palette),
    )


def apply_diff_state_to_widget(
    widget: QtWidgets.QWidget,
    state: DiffState,
    palette: QtGui.QPalette,
    *,
    container_object_name: str,
    label_object_name: str,
    selected: bool = False,
) -> None:
    """Apply diff colors plus local hover and selection styles to a row widget."""
    colors = colors_for_diff_state(state, palette)
    normal_background = colors.normal_background.name() if colors.normal_background is not None else "transparent"
    display_background = colors.selected_background.name() if selected else normal_background
    display_foreground = colors.selected_foreground if selected else colors.normal_foreground
    active_hover_background = colors.selected_background if selected else colors.hover_background
    hover_foreground = colors.selected_foreground if selected else colors.hover_foreground

    # FreeCAD themes such as OpenTheme apply global QSS that overrides item
    # palette roles. Object-scoped widget QSS wins locally without affecting
    # unrelated FreeCAD views.
    widget.setStyleSheet(
        f"QWidget#{container_object_name} {{ "
        f"background-color: {display_background}; color: {display_foreground.name()}; }} "
        f"QWidget#{container_object_name}:hover {{ "
        f"background-color: {active_hover_background.name()}; color: {hover_foreground.name()}; }} "
        f"QWidget#{container_object_name} QLabel#{label_object_name} {{ "
        f"background-color: transparent; color: {display_foreground.name()}; }} "
        f"QWidget#{container_object_name}:hover QLabel#{label_object_name} {{ color: {hover_foreground.name()}; }}"
    )


@lru_cache(maxsize=256)
def _cached_foreground_for_background(background_key: _ColorKey, palette_cache_key: _PaletteKey) -> QtGui.QColor:
    """Return cached foreground for background and palette colors."""
    background = _color_from_key(background_key)
    palette = _palette_from_key(palette_cache_key)
    if not _theme_is_dark(palette):
        return QtGui.QColor(0, 0, 0)  # #000000

    palette_text = _color_from_key(palette_cache_key[1])
    black = QtGui.QColor(0, 0, 0)  # #000000
    white = QtGui.QColor(255, 255, 255)  # #FFFFFF
    candidates = [palette_text, black, white]
    best = max(candidates, key=lambda color: _contrast_ratio(color, background))
    if _contrast_ratio(best, background) >= _MIN_CONTRAST:
        return best
    return black if _contrast_ratio(black, background) > _contrast_ratio(white, background) else white


def _state_background(palette: QtGui.QPalette, light_accent: QtGui.QColor, dark_accent: QtGui.QColor) -> QtGui.QColor:
    """Blend state accent with theme base and adjust until text is readable."""
    colors = _palette_theme_colors(palette)
    if _theme_is_dark(palette):
        accent = dark_accent
        initial = _blend_colors(colors.base, accent, _DARK_ACCENT_BLEND)
    else:
        accent = light_accent
        initial = light_accent
    foreground = foreground_for_background(initial, palette)
    if _contrast_ratio(foreground, initial) >= _MIN_CONTRAST:
        return initial
    return _find_contrast_background(colors.base, accent, foreground)


def _find_contrast_background(base: QtGui.QColor, accent: QtGui.QColor, foreground: QtGui.QColor) -> QtGui.QColor:
    """Try stronger accent blends until foreground contrast is sufficient."""
    for ratio in _CONTRAST_FALLBACK_BLEND_RATIOS:
        candidate = _blend_colors(base, accent, ratio)
        if _contrast_ratio(foreground, candidate) >= _MIN_CONTRAST:
            return candidate
    return _blend_colors(base, accent, _LAST_FALLBACK_BLEND)
