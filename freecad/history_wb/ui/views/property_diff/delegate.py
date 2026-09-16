"""File responsibility: Read-only property value delegate with selectable inline text."""

from ....qt import QtCore, QtWidgets


__all__ = ["PropertyValueDelegate"]


class PropertyValueDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate allowing double-click text selection without persisting edits."""

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
