"""File responsibility: Property diff tree container that wires headers, delegate, and item builders."""

from __future__ import annotations

from typing import cast

from ....domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION
from ....domain.settings import SettingsRepository
from ....qt import QtCore, QtGui, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import PropertyPresentation
from ..theme.diff import palette_with_resolved_text
from .delegate import PropertyValueDelegate
from .tree_items import apply_stored_expansion_state, build_grouped_property_items


__all__ = ["PropertyDiffTreeWidget"]


class PropertyDiffTreeWidget(QtWidgets.QTreeWidget):
    """Widget that renders grouped property diffs in three columns."""

    _SEPARATOR_HIT_MARGIN = 4

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._default_precision = DEFAULT_FLOAT_PRECISION
        self._theme_probe = QtWidgets.QLabel(self)
        self._theme_probe.hide()
        self._property_value_delegate = PropertyValueDelegate(self._effective_diff_palette, self)
        self._resizing_column: int | None = None
        self._resize_start_x = 0
        self._resize_start_width = 0
        self._setup_tree()

    def _setup_tree(self) -> None:
        """Configure headers, resize behavior, delegate, and edit triggers."""
        self.setObjectName("propertyDiffTree")
        self.setColumnCount(3)
        self.setHeaderLabels(
            [
                translate("History", "Property"),
                translate("History", "Old Value"),
                translate("History", "New Value"),
            ]
        )
        header = self.header()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.setItemDelegate(self._property_value_delegate)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self.setMouseTracking(True)

    def viewportEvent(self, event: QtCore.QEvent) -> bool:  # noqa: N802
        """Resize columns when a separator is dragged anywhere in the viewport."""
        event_type = event.type()
        if event_type == QtCore.QEvent.Type.MouseButtonPress and self._handle_resize_press(event):
            return True
        if event_type == QtCore.QEvent.Type.MouseMove and self._handle_resize_move(event):
            return True
        if event_type == QtCore.QEvent.Type.MouseButtonRelease and self._handle_resize_release(event):
            return True
        if event_type == QtCore.QEvent.Type.Leave and self._resizing_column is None:
            self._set_separator_cursor(False)

        return super().viewportEvent(event)

    def _handle_resize_press(self, event: QtCore.QEvent) -> bool:
        """Start resizing when left button presses a body separator."""
        mouse_event = cast(QtGui.QMouseEvent, event)
        if mouse_event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        x_position = mouse_event.pos().x()
        column = self._separator_at(x_position)
        if column is None:
            return False
        self._start_column_resize(column, x_position)
        return True

    def _handle_resize_move(self, event: QtCore.QEvent) -> bool:
        """Update active resize or separator hover cursor."""
        mouse_event = cast(QtGui.QMouseEvent, event)
        x_position = mouse_event.pos().x()
        if self._resizing_column is None:
            self._set_separator_cursor(self._separator_at(x_position) is not None)
            return False
        self._resize_column(x_position)
        return True

    def _handle_resize_release(self, event: QtCore.QEvent) -> bool:
        """Finish active resizing on left-button release."""
        mouse_event = cast(QtGui.QMouseEvent, event)
        if self._resizing_column is None or mouse_event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        x_position = mouse_event.pos().x()
        self._resize_column(x_position)
        self._resizing_column = None
        self._set_separator_cursor(self._separator_at(x_position) is not None)
        return True

    def _separator_at(self, x_position: int) -> int | None:
        """Return resizable column left of a separator near viewport x position."""
        header = self.header()
        for column in range(self.columnCount() - 1):
            boundary = header.sectionViewportPosition(column) + header.sectionSize(column)
            if abs(x_position - boundary) <= self._SEPARATOR_HIT_MARGIN:
                return column
        return None

    def _start_column_resize(self, column: int, x_position: int) -> None:
        """Capture initial pointer and section geometry for one drag."""
        self._resizing_column = column
        self._resize_start_x = x_position
        self._resize_start_width = self.header().sectionSize(column)
        self._set_separator_cursor(True)

    def _resize_column(self, x_position: int) -> None:
        """Apply current drag delta to active header section."""
        if self._resizing_column is None:
            raise RuntimeError("Column resize requested without an active separator drag")
        width = self._resize_start_width + x_position - self._resize_start_x
        self.header().resizeSection(
            self._resizing_column,
            max(self.header().minimumSectionSize(), width),
        )

    def _set_separator_cursor(self, over_separator: bool) -> None:
        """Show horizontal split cursor only while separator interaction is available."""
        if over_separator:
            self.viewport().setCursor(QtCore.Qt.CursorShape.SplitHCursor)
        else:
            self.viewport().unsetCursor()

    def _effective_diff_palette(self) -> QtGui.QPalette:
        """Resolve visible text color from application QSS into tree palette.

        Stylesheet themes can paint label text without updating the tree's Text
        palette role. A polished QLabel exposes effective WindowText while
        preserving theme-owned surface roles.
        """
        self._theme_probe.ensurePolished()
        return palette_with_resolved_text(
            self.palette(),
            self._theme_probe.palette().color(QtGui.QPalette.ColorRole.WindowText),
        )

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Refresh shared semantic colors when FreeCAD changes theme or style."""
        super().changeEvent(event)
        if event.type() in {
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.StyleChange,
        }:
            self.viewport().update()

    def clear_property_diff(self) -> None:
        """Clear all property diff entries from the tree widget."""
        self.clear()

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Render property diffs grouped by their group name."""
        updates_enabled = self.updatesEnabled()

        # Defer repaints while installing many items and cell widgets to avoid repeated layout and style work.
        self.setUpdatesEnabled(False)
        try:
            self.clear_property_diff()
            if not properties:
                return

            items = build_grouped_property_items(properties, self._get_precision())
            self.addTopLevelItems(items)
            apply_stored_expansion_state(items)
        finally:
            self.setUpdatesEnabled(updates_enabled)

    def _get_precision(self) -> int:
        """Read configured float precision or fall back to default precision."""
        if self._settings_repo is not None:
            try:
                return self._settings_repo.get_settings().float_precision
            except (AttributeError, RuntimeError):
                pass
        return self._default_precision
