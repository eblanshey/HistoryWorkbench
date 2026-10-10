"""File responsibility: Shared fixtures and helpers for history view unit tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from freecad.history_wb.domain.git.models import GitCommit
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.views.history.panel import HistoryPanelWidget


@pytest.fixture
def history_panel_widget() -> HistoryPanelWidget:
    """Create HistoryPanelWidget with QApplication available."""
    return HistoryPanelWidget()


@pytest.fixture
def history_list_widget(history_panel_widget: HistoryPanelWidget):
    """Expose HistoryList child through panel fixture."""
    return history_panel_widget._history_list


def make_commit(
    *,
    commit_id: str = "a1b2c3d4e5f67890",
    message: str = "Test commit",
    author: str = "Test Author",
    timestamp: str = "2024-01-15T10:30:00+00:00",
) -> GitCommit:
    """Build GitCommit test value with common defaults."""
    return GitCommit(
        id=commit_id,
        message=message,
        author=author,
        timestamp=datetime.fromisoformat(timestamp),
    )


def history_row_text(list_widget, row: int) -> str:  # type: ignore[no-untyped-def]
    """Return visible text for history row, including custom widgets."""
    item = list_widget.item(row)
    widget = list_widget.itemWidget(item)
    if widget is None:
        return item.text()

    labels = widget.findChildren(QtWidgets.QLabel)
    if len(labels) == 1:
        return labels[0].text()
    if len(labels) >= 4:
        top_line = f"{labels[0].text()} {labels[1].text()} {labels[2].text()}"
        return f"{top_line}\n{labels[3].text()}"
    return item.text()


class FakeMenuAction:
    """Reusable fake QMenu action for context-menu tests."""

    def __init__(self) -> None:
        self.enabled = True

    def setEnabled(self, enabled: bool) -> None:
        """Track whether the action can be selected."""
        self.enabled = enabled

    def setToolTip(self, _value: str) -> None:
        """Ignore tooltip assignment in fake action."""
        return

    def setStatusTip(self, _value: str) -> None:
        """Ignore status-tip assignment in fake action."""
        return


def build_fake_menu_class(select_action_index: int = 0) -> type:
    """Return fake QMenu class tracking creation and exec calls.

    select_action_index controls which addAction return value is returned by exec.
    """

    class _FakeMenu:
        created = False
        exec_called = False
        action_texts: list[str] = []
        actions: list[FakeMenuAction] = []

        def __init__(self, *_args, **_kwargs) -> None:
            _FakeMenu.created = True
            self._actions: list[FakeMenuAction] = []

        def setToolTipsVisible(self, _visible: bool) -> None:
            """Ignore tooltip visibility in fake menu."""
            return

        def addAction(self, _text: str) -> FakeMenuAction:
            """Return tracked fake action."""
            _FakeMenu.action_texts.append(_text)
            action = FakeMenuAction()
            self._actions.append(action)
            _FakeMenu.actions.append(action)
            return action

        def exec(self, *_args, **_kwargs) -> FakeMenuAction | None:
            """Record menu execution and return the selected action."""
            _FakeMenu.exec_called = True
            # Dismissal and disabled actions cannot emit an intent.
            if select_action_index < 0 or not self._actions[select_action_index].enabled:
                return None
            return self._actions[select_action_index]

    return _FakeMenu
