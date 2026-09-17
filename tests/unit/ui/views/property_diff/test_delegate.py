"""File responsibility: Unit tests for extracted property diff item delegate."""

from __future__ import annotations

import pytest

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtCore, QtGui, QtWidgets
from freecad.history_wb.ui.views.property_diff.delegate import PropertyValueDelegate
from freecad.history_wb.ui.views.property_diff.tree_items import PROPERTY_DIFF_STATE_ROLE
from freecad.history_wb.ui.views.theme.diff import colors_for_diff_state, palette_with_resolved_text


def _delegate(parent: QtWidgets.QWidget) -> PropertyValueDelegate:
    """Create delegate using parent widget's current palette."""
    return PropertyValueDelegate(parent.palette, parent)


def test_create_editor_builds_borderless_line_edit() -> None:
    """Delegate creates borderless line edit aligned for row text."""
    parent = QtWidgets.QWidget()
    delegate = _delegate(parent)
    option = QtWidgets.QStyleOptionViewItem()
    model = QtGui.QStandardItemModel(1, 1)
    index = model.index(0, 0)

    editor = delegate.createEditor(parent, option, index)

    assert isinstance(editor, QtWidgets.QLineEdit)
    assert not editor.hasFrame()
    assert editor.alignment() == (
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft
    )


def test_set_editor_data_populates_text_and_selects_all() -> None:
    """Delegate copies display text into editor and selects all text."""
    parent = QtWidgets.QWidget()
    delegate = _delegate(parent)
    model = QtGui.QStandardItemModel(1, 1)
    model.setData(model.index(0, 0), "Length", QtCore.Qt.ItemDataRole.DisplayRole)
    editor = QtWidgets.QLineEdit(parent)

    delegate.setEditorData(editor, model.index(0, 0))

    assert editor.text() == "Length"
    assert editor.selectedText() == "Length"


def test_set_model_data_keeps_model_read_only() -> None:
    """Delegate ignores editor writes so backing model data stays unchanged."""
    parent = QtWidgets.QWidget()
    delegate = _delegate(parent)
    model = QtGui.QStandardItemModel(1, 1)
    model.setData(model.index(0, 0), "Original", QtCore.Qt.ItemDataRole.DisplayRole)
    editor = QtWidgets.QLineEdit(parent)
    editor.setText("Updated")

    delegate.setModelData(editor, model, model.index(0, 0))

    assert model.data(model.index(0, 0), QtCore.Qt.ItemDataRole.DisplayRole) == "Original"


def test_update_editor_geometry_matches_item_rect() -> None:
    """Delegate positions editor over cell rectangle."""
    parent = QtWidgets.QWidget()
    delegate = _delegate(parent)
    editor = QtWidgets.QLineEdit(parent)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(5, 7, 80, 20)
    model = QtGui.QStandardItemModel(1, 1)

    delegate.updateEditorGeometry(editor, option, model.index(0, 0))

    assert editor.geometry() == option.rect


@pytest.mark.parametrize(
    ("interaction_state", "expected_background_name"),
    [
        (QtWidgets.QStyle.StateFlag.State_MouseOver, "hover_background"),
        (QtWidgets.QStyle.StateFlag.State_Selected, "selected_background"),
    ],
)
def test_paint_uses_native_interaction_state(
    application,
    interaction_state: QtWidgets.QStyle.StateFlag,
    expected_background_name: str,
) -> None:  # type: ignore[no-untyped-def]
    """Delegate renders directly from Qt's current hover and selection flags."""
    parent = QtWidgets.QWidget()
    palette = parent.palette()
    delegate = _delegate(parent)
    model = QtGui.QStandardItemModel(1, 1)
    index = model.index(0, 0)
    model.setData(index, "Length", QtCore.Qt.ItemDataRole.DisplayRole)
    model.setData(index, DiffState.MODIFIED, PROPERTY_DIFF_STATE_ROLE)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 100, 22)
    option.state = QtWidgets.QStyle.StateFlag.State_Enabled | interaction_state
    image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("magenta"))
    painter = QtGui.QPainter(image)

    delegate.paint(painter, option, index)
    painter.end()

    colors = colors_for_diff_state(DiffState.MODIFIED, palette)
    expected_background = getattr(colors, expected_background_name)
    assert image.pixelColor(90, 11) == expected_background


def test_unchanged_hover_overlays_visible_surface_without_using_stale_base(application) -> None:  # type: ignore[no-untyped-def]
    """Unchanged hover remains light when QSS surface and palette Base disagree."""
    stale_palette = QtGui.QPalette()
    stale_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(30, 30, 30))
    stale_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(20, 20, 20))
    stale_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(240, 240, 240))
    effective_palette = palette_with_resolved_text(stale_palette, QtGui.QColor(0, 0, 0))
    delegate = PropertyValueDelegate(lambda: effective_palette)
    model = QtGui.QStandardItemModel(1, 1)
    index = model.index(0, 0)
    model.setData(index, "Length", QtCore.Qt.ItemDataRole.DisplayRole)
    model.setData(index, DiffState.UNCHANGED, PROPERTY_DIFF_STATE_ROLE)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 100, 22)
    option.state = QtWidgets.QStyle.StateFlag.State_Enabled | QtWidgets.QStyle.StateFlag.State_MouseOver
    image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor(245, 245, 245))
    painter = QtGui.QPainter(image)

    delegate.paint(painter, option, index)
    painter.end()

    assert image.pixelColor(90, 11).lightness() > 127
