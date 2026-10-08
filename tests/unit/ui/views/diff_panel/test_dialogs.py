"""File responsibility: Unit tests for diff panel dialog helper functions."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.views.diff_panel.dialogs import GitConfigDialogResult


def _ensure_app() -> QtWidgets.QApplication:
    """Return QApplication instance for widget tests."""
    app = QtWidgets.QApplication.instance()

    # Tests may run outside pytest-qt, so create QApplication lazily.
    if app is None:
        app = QtWidgets.QApplication([])

    return cast(QtWidgets.QApplication, app)


def test_show_save_iteration_dialog_returns_none_when_cancelled() -> None:
    """Save iteration helper returns None when dialog is rejected."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_save_iteration_dialog

    _ensure_app()

    with patch.object(QtWidgets.QDialog, "exec", return_value=QtWidgets.QDialog.DialogCode.Rejected):
        assert show_save_iteration_dialog(QtWidgets.QWidget()) is None


def test_show_save_iteration_dialog_returns_entered_text_when_accepted() -> None:
    """Save iteration helper returns text field contents after accept."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_save_iteration_dialog

    _ensure_app()

    def _accept_after_seeding_text(dialog: QtWidgets.QDialog) -> int:
        text_edit = dialog.findChild(QtWidgets.QPlainTextEdit)
        assert text_edit is not None
        text_edit.setPlainText("subject\n\nbody")
        return QtWidgets.QDialog.DialogCode.Accepted

    with patch.object(QtWidgets.QDialog, "exec", new=_accept_after_seeding_text):
        assert show_save_iteration_dialog(QtWidgets.QWidget()) == "subject\n\nbody"


def test_show_configure_author_dialog_returns_none_when_cancelled() -> None:
    """Configure author helper returns None when dialog is rejected."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_configure_author_dialog

    _ensure_app()

    with patch.object(QtWidgets.QDialog, "exec", return_value=QtWidgets.QDialog.DialogCode.Rejected):
        assert show_configure_author_dialog(QtWidgets.QWidget(), None, None, True) is None


def test_show_configure_author_dialog_returns_trimmed_values_when_accepted() -> None:
    """Configure author helper trims values and preserves checkbox state."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_configure_author_dialog

    _ensure_app()

    def _accept_after_seeding_values(dialog: QtWidgets.QDialog) -> int:
        line_edits = dialog.findChildren(QtWidgets.QLineEdit)
        assert len(line_edits) == 2
        line_edits[0].setText("  Alice  ")
        line_edits[1].setText("  alice@example.com  ")
        checkbox = dialog.findChild(QtWidgets.QCheckBox)
        assert checkbox is not None
        checkbox.setChecked(True)
        return QtWidgets.QDialog.DialogCode.Accepted

    with patch.object(QtWidgets.QDialog, "exec", new=_accept_after_seeding_values):
        result = show_configure_author_dialog(QtWidgets.QWidget(), None, None, True)

    assert result == GitConfigDialogResult(
        author_name="Alice",
        author_email="alice@example.com",
        should_save_globally=True,
    )


def test_show_configure_author_dialog_disables_global_option_when_not_writable() -> None:
    """Configure author helper forces local save when global config is not writable."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_configure_author_dialog

    _ensure_app()

    initial_values = GitConfigDialogResult(
        author_name="Alice",
        author_email="alice@example.com",
        should_save_globally=True,
    )

    def _assert_disabled_checkbox(dialog: QtWidgets.QDialog) -> int:
        checkbox = dialog.findChild(QtWidgets.QCheckBox)
        assert checkbox is not None
        assert checkbox.isEnabled() is False
        assert checkbox.isChecked() is False
        return QtWidgets.QDialog.DialogCode.Accepted

    with patch.object(QtWidgets.QDialog, "exec", new=_assert_disabled_checkbox):
        result = show_configure_author_dialog(QtWidgets.QWidget(), "warning", initial_values, False)

    assert result == GitConfigDialogResult(
        author_name="Alice",
        author_email="alice@example.com",
        should_save_globally=False,
    )


@pytest.mark.parametrize("use_index_wording", [False, True])
def test_show_restore_file_confirmation_dialog_returns_true_for_restore_button(use_index_wording: bool) -> None:
    """Restore confirmation helper returns True only for destructive button."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_restore_file_confirmation_dialog

    _ensure_app()

    clicked_button = MagicMock()
    captured_text: list[str] = []

    def _fake_add_button(_self: QtWidgets.QMessageBox, text: str, _role: QtWidgets.QMessageBox.ButtonRole) -> object:
        if text == "Restore":
            return clicked_button
        return MagicMock()

    def _capture_text(_self: QtWidgets.QMessageBox, text: str) -> None:
        captured_text.append(text)

    with (
        patch.object(QtWidgets.QMessageBox, "addButton", new=_fake_add_button),
        patch.object(QtWidgets.QMessageBox, "setText", new=_capture_text),
        patch.object(QtWidgets.QMessageBox, "exec", return_value=0),
        patch.object(QtWidgets.QMessageBox, "clickedButton", return_value=clicked_button),
    ):
        assert show_restore_file_confirmation_dialog(QtWidgets.QWidget(), "file.FCStd", use_index_wording) is True

    assert len(captured_text) == 1
    assert captured_text[0].startswith("file.FCStd\n\n")
    expected_source = "last reviewed or saved version" if use_index_wording else "selected saved copies"
    assert expected_source in captured_text[0]
    assert "Unsaved changes in open files will be lost" in captured_text[0]
    assert "Saved history will not be affected" in captured_text[0]


@pytest.mark.parametrize("use_index_wording", [False, True])
def test_show_restore_file_confirmation_dialog_uses_bulk_source_warning(use_index_wording: bool) -> None:
    """Bulk restore confirmation identifies its source without a file-path prefix."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_restore_file_confirmation_dialog

    _ensure_app()

    captured_text: list[str] = []

    def _capture_text(_self: QtWidgets.QMessageBox, text: str) -> None:
        captured_text.append(text)

    with (
        patch.object(QtWidgets.QMessageBox, "addButton", return_value=MagicMock()),
        patch.object(QtWidgets.QMessageBox, "setText", new=_capture_text),
        patch.object(QtWidgets.QMessageBox, "exec", return_value=0),
        patch.object(QtWidgets.QMessageBox, "clickedButton", return_value=MagicMock()),
    ):
        show_restore_file_confirmation_dialog(QtWidgets.QWidget(), "", use_index_wording)

    assert len(captured_text) == 1
    if use_index_wording:
        assert captured_text[0].startswith("This operation will restore all FreeCAD files")
        assert "last reviewed or saved versions.\n\nCurrent files on disk" in captured_text[0]
        assert "overwritten or removed" in captured_text[0]
        assert "Files that have not been saved or reviewed will be kept" in captured_text[0]
    else:
        assert captured_text[0].startswith("This operation will overwrite")
    assert "Saved history will not be affected" in captured_text[0]


def test_show_restore_scope_dialog_defaults_to_listed_scope() -> None:
    """Restore scope helper returns listed scope by default after accept."""
    from freecad.history_wb.ui.views.diff_panel.dialogs import show_restore_scope_dialog

    _ensure_app()

    with patch.object(QtWidgets.QDialog, "exec", return_value=QtWidgets.QDialog.DialogCode.Accepted):
        assert show_restore_scope_dialog(QtWidgets.QWidget()) == "listed_fcstd"
