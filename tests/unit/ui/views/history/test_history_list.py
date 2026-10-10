"""File responsibility: Unit tests for HistoryList local interactions and signals."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from freecad.history_wb.qt import QtCore, QtGui, QtWidgets
from freecad.history_wb.ui.presenters.diff_presenter import DiffPresenter
from freecad.history_wb.ui.wiring import bind_history_events
from freecad.history_wb.ui.views.history.history_row import create_commit_history_item, create_special_history_item
from freecad.history_wb.ui.views.history.models import HistorySelection

from .conftest import build_fake_menu_class, make_commit


def test_item_click_emits_user_requested_and_effective_selection_signals(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Clicking selection row emits both user-intent and effective-state signals."""
    selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    item, widget = create_special_history_item("Current Files Area", selection)
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    requested: list[HistorySelection] = []
    changed: list[HistorySelection | None] = []
    history_list_widget.user_selection_requested.connect(requested.append)
    history_list_widget.effective_selection_changed.connect(changed.append)

    history_list_widget.itemClicked.emit(item)

    assert requested == [selection]
    assert changed == [selection]


def test_apply_effective_selection_if_present_sets_current_item_and_emits_signal(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Applying existing selection updates current item and effective-state signal."""
    selection = HistorySelection(item_kind="STAGING", commit_hash=None)
    item, widget = create_special_history_item("Reviewed Area", selection)
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    changed: list[HistorySelection | None] = []
    history_list_widget.effective_selection_changed.connect(changed.append)

    assert history_list_widget.apply_effective_selection_if_present(selection) is True
    assert history_list_widget.currentItem() is item
    assert changed == [selection]


def test_clear_effective_selection_clears_current_item_and_emits_none(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Clearing list selection emits null effective-selection state."""
    selection = HistorySelection(item_kind="STAGING", commit_hash=None)
    item, widget = create_special_history_item("Reviewed Area", selection)
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    history_list_widget.setCurrentItem(item)
    changed: list[HistorySelection | None] = []
    history_list_widget.effective_selection_changed.connect(changed.append)

    history_list_widget.clear_effective_selection()

    assert history_list_widget.currentRow() == -1
    assert changed == [None]


def test_reviewed_context_menu_emits_remove_all_signal(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Reviewed Area context menu emits remove-all signal."""
    selection = HistorySelection(item_kind="STAGING", commit_hash=None)
    item, widget = create_special_history_item("Reviewed Area", selection)
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    called = {"count": 0}
    history_list_widget.remove_all_from_reviewed_requested.connect(
        lambda: called.__setitem__("count", called["count"] + 1)
    )
    fake_menu = build_fake_menu_class(select_action_index=0)
    pos = history_list_widget.visualItemRect(item).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        history_list_widget._on_context_menu_requested(pos)

    assert fake_menu.created is True
    assert fake_menu.exec_called is True
    assert called["count"] == 1
    assert fake_menu.action_texts == ["Remove All Files From Reviewed"]


def test_commit_context_menu_emits_restore_signal(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Commit context menu emits restore signal with commit selection."""
    commit_selection = HistorySelection(item_kind="COMMIT", commit_hash="abc1234")
    item, widget = create_commit_history_item(make_commit(commit_id="abc1234", author="a", message="m"))
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    received: list[HistorySelection] = []
    history_list_widget.restore_all_from_history_context_requested.connect(received.append)
    fake_menu = build_fake_menu_class()
    pos = history_list_widget.visualItemRect(item).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        history_list_widget._on_context_menu_requested(pos)

    assert fake_menu.created is True
    assert fake_menu.exec_called is True
    assert received == [commit_selection]
    assert fake_menu.action_texts == ["Restore All Files From Iteration", "Copy Iteration ID to Clipboard"]


def test_commit_context_menu_copies_iteration_id_to_clipboard(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Commit context menu copy action writes commit hash to clipboard."""
    commit_hash = "deadbeef12345678"
    item, widget = create_commit_history_item(make_commit(commit_id=commit_hash, author="a", message="m"))
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)

    clipboard = MagicMock()
    fake_app = MagicMock()
    fake_app.clipboard.return_value = clipboard

    # select_action_index=1 selects the second menu action (Copy Iteration ID).
    fake_menu = build_fake_menu_class(select_action_index=1)
    pos = history_list_widget.visualItemRect(item).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        with patch(
            "freecad.history_wb.ui.views.history.history_list.QtWidgets.QApplication.instance", return_value=fake_app
        ):
            history_list_widget._on_context_menu_requested(pos)

    clipboard.setText.assert_called_once_with(commit_hash)


def test_working_tree_context_menu_emits_mark_all_reviewed_signal(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Current Files Area context menu emits mark-all-reviewed signal."""
    selection = HistorySelection(item_kind="WORKING_TREE", commit_hash=None)
    item, widget = create_special_history_item("Current Files Area", selection)
    history_list_widget.addItem(item)
    history_list_widget.setItemWidget(item, widget)
    called = {"count": 0}
    history_list_widget.mark_all_reviewed_from_in_progress_requested.connect(
        lambda: called.__setitem__("count", called["count"] + 1)
    )
    fake_menu = build_fake_menu_class()
    pos = history_list_widget.visualItemRect(item).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        history_list_widget._on_context_menu_requested(pos)

    assert fake_menu.created is True
    assert fake_menu.exec_called is True
    assert called["count"] == 1


@pytest.mark.parametrize("action_index", [1, -1])
def test_current_files_context_discard_preserves_commit_selection(
    history_panel_widget, history_list_widget, action_index: int
) -> None:  # type: ignore[no-untyped-def]
    """Discard is always enabled and preserves the selected commit, including menu dismissal."""
    history_panel_widget.show_commits([make_commit()])
    history_list_widget.setCurrentRow(2)
    selected_item = history_list_widget.currentItem()
    requested: list[bool] = []
    selection_changes: list[object] = []
    history_panel_widget.discard_all_from_current_files_requested.connect(lambda: requested.append(True))
    history_panel_widget.history_selection_changed.connect(selection_changes.append)
    fake_menu = build_fake_menu_class(select_action_index=action_index)
    pos = history_list_widget.visualItemRect(history_list_widget.item(0)).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        history_list_widget._on_context_menu_requested(pos)

    assert fake_menu.action_texts == ["Mark All Files Reviewed", "Discard All Changes"]
    assert fake_menu.actions[1].enabled is True
    assert requested == ([True] if action_index == 1 else [])
    assert history_list_widget.currentItem() is selected_item
    assert selection_changes == []


def test_opening_current_files_menu_does_not_request_presenter_work(history_panel_widget, history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Wired menu opening does not load diffs or query availability before an action is chosen."""
    presenter = MagicMock(spec=DiffPresenter)
    view = MagicMock()
    view.history_panel = history_panel_widget
    bind_history_events(view, presenter, MagicMock())
    history_panel_widget.show_commits([])
    presenter.reset_mock()
    fake_menu = build_fake_menu_class(select_action_index=-1)
    pos = history_list_widget.visualItemRect(history_list_widget.item(0)).center()

    with patch("freecad.history_wb.ui.views.history.history_list.QtWidgets.QMenu", fake_menu):
        history_list_widget._on_context_menu_requested(pos)

    assert fake_menu.actions[1].enabled is True
    assert presenter.mock_calls == []


def test_scroll_bottom_callback_fires_near_bottom_once_until_rearmed(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Near-bottom signal fires once per bottom entry until user scrolls away."""
    fired: list[str] = []
    history_list_widget.near_bottom_requested.connect(lambda: fired.append("bottom"))
    mock_scrollbar = MagicMock()
    mock_scrollbar.maximum.return_value = 100

    with patch.object(history_list_widget, "verticalScrollBar", return_value=mock_scrollbar):
        history_list_widget._on_scrollbar_value_changed(90)
        history_list_widget._on_scrollbar_value_changed(95)
        history_list_widget._on_scrollbar_value_changed(60)
        history_list_widget._on_scrollbar_value_changed(90)

    assert fired == ["bottom", "bottom"]


def test_right_click_does_not_change_current_selection(history_list_widget) -> None:  # type: ignore[no-untyped-def]
    """Right-click press does not alter list current row."""
    item_one, widget_one = create_commit_history_item(make_commit(commit_id="a1b2c3d4e5f67890", message="First commit"))
    item_two, widget_two = create_commit_history_item(
        make_commit(commit_id="b2c3d4e5f6789012", message="Second commit")
    )
    history_list_widget.addItem(item_one)
    history_list_widget.setItemWidget(item_one, widget_one)
    history_list_widget.addItem(item_two)
    history_list_widget.setItemWidget(item_two, widget_two)
    history_list_widget.setCurrentRow(0)

    target_rect = history_list_widget.visualItemRect(item_two)
    click_pos = target_rect.center()
    local_pos = QtCore.QPointF(click_pos)
    global_pos = QtCore.QPointF(history_list_widget.viewport().mapToGlobal(click_pos))
    press_event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress,
        local_pos,
        global_pos,
        QtCore.Qt.MouseButton.RightButton,
        QtCore.Qt.MouseButton.RightButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    release_event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        local_pos,
        global_pos,
        QtCore.Qt.MouseButton.RightButton,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )

    QtWidgets.QApplication.sendEvent(history_list_widget.viewport(), press_event)
    QtWidgets.QApplication.sendEvent(history_list_widget.viewport(), release_event)

    assert history_list_widget.currentRow() == 0
