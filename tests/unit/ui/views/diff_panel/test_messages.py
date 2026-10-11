"""File responsibility: Unit tests for diff panel message helpers and document-open error display."""

from __future__ import annotations

from typing import cast
from unittest.mock import patch

import pytest

from freecad.history_wb.qt import QtWidgets


def _ensure_app() -> QtWidgets.QApplication:
    """Return QApplication instance for widget tests."""
    app = QtWidgets.QApplication.instance()

    # Tests may run outside pytest-qt, so create QApplication lazily.
    if app is None:
        app = QtWidgets.QApplication([])

    return cast(QtWidgets.QApplication, app)


def test_show_warning_message_calls_qmessagebox_warning() -> None:
    """Warning helper calls QMessageBox.warning with parent and text."""
    from freecad.history_wb.ui.views.diff_panel.messages import show_warning_message

    _ensure_app()
    parent = QtWidgets.QWidget()

    with patch.object(QtWidgets.QMessageBox, "warning") as warning_mock:
        show_warning_message(parent, "warn", "message")

    warning_mock.assert_called_once_with(parent, "warn", "message")


def test_show_info_message_calls_qmessagebox_information() -> None:
    """Info helper calls QMessageBox.information with parent and text."""
    from freecad.history_wb.ui.views.diff_panel.messages import show_info_message

    _ensure_app()
    parent = QtWidgets.QWidget()

    with patch.object(QtWidgets.QMessageBox, "information") as info_mock:
        show_info_message(parent, "info", "message")

    info_mock.assert_called_once_with(parent, "info", "message")


def test_show_error_message_calls_qmessagebox_critical() -> None:
    """Error helper calls QMessageBox.critical with parent and text."""
    from freecad.history_wb.ui.views.diff_panel.messages import show_error_message

    _ensure_app()
    parent = QtWidgets.QWidget()

    with patch.object(QtWidgets.QMessageBox, "critical") as error_mock:
        show_error_message(parent, "error", "message")

    error_mock.assert_called_once_with(parent, "error", "message")


@pytest.mark.parametrize(
    "reason",
    [
        "File '/home/user/parts/A.FCStd' does not exist!",
        "Invalid document",
    ],
)
def test_document_open_error_preserves_runtime_reason(reason: str) -> None:
    """Failed document opening preserves the runtime reason without adding a second path."""
    from freecad.history_wb.ui.views.diff_panel.dialog_view import DialogView

    _ensure_app()
    parent = QtWidgets.QWidget()

    with patch.object(QtWidgets.QMessageBox, "critical") as error_mock:
        DialogView(parent).show_document_open_error(reason)

    error_mock.assert_called_once_with(
        parent,
        "Open Document Failed",
        f"Could not open the current document.\n\n{reason}",
    )
