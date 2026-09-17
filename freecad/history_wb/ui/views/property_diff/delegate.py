"""File responsibility: Native property-cell painting and read-only text selection."""

from collections.abc import Callable
from typing import Any, cast

from ....domain.diff.models import DiffState
from ....qt import QtCore, QtGui, QtWidgets
from ..theme.diff import colors_for_diff_state
from .tree_items import PROPERTY_DIFF_STATE_ROLE


__all__ = ["PropertyValueDelegate"]


class PropertyValueDelegate(QtWidgets.QStyledItemDelegate):
    """Paint native hover/selection states and provide selectable inline text."""

    def __init__(
        self,
        palette_provider: Callable[[], QtGui.QPalette],
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette_provider = palette_provider

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:  # type: ignore[override]
        """Paint one property cell from Qt's immediate hover and selection flags."""
        state = index.data(PROPERTY_DIFF_STATE_ROLE)
        if not isinstance(state, DiffState):
            super().paint(painter, option, index)
            return

        themed_option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(themed_option, index)
        option_data = cast(Any, themed_option)
        colors = colors_for_diff_state(state, self._palette_provider())
        background: QtGui.QColor | None
        if option_data.state & QtWidgets.QStyle.StateFlag.State_Selected:
            background = colors.selected_background
            foreground = colors.selected_foreground
        elif option_data.state & QtWidgets.QStyle.StateFlag.State_MouseOver:
            background = colors.hover_background
            foreground = colors.hover_foreground
        else:
            background = colors.normal_background
            foreground = colors.normal_foreground

        painter.save()
        if background is not None:
            painter.fillRect(option_data.rect, background)
        painter.setFont(option_data.font)
        painter.setPen(foreground)
        text_rect = option_data.rect.adjusted(3, 0, -3, 0)
        text = option_data.fontMetrics.elidedText(
            option_data.text,
            option_data.textElideMode,
            text_rect.width(),
        )
        painter.drawText(text_rect, int(option_data.displayAlignment), text)
        painter.restore()

    def createEditor(
        self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem, index
    ) -> QtWidgets.QWidget:  # type: ignore[override]
        """Create inline editor used only for text selection and copying."""
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index) -> None:  # type: ignore[override]
        """Populate editor and select all text for copying."""
        text = index.model().data(index, QtCore.Qt.ItemDataRole.DisplayRole)
        if text is not None:
            editor.setText(str(text))
            editor.selectAll()

    def setModelData(self, editor: QtWidgets.QLineEdit, model, index) -> None:  # type: ignore[override]
        """Ignore edits because property diff rows are read-only."""
        pass

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index,
    ) -> None:  # type: ignore[override]
        """Position editor directly over target cell."""
        editor.setGeometry(option.rect)  # type: ignore[attr-defined]
