"""File responsibility: Unit tests for document diff summary bar behavior."""

from __future__ import annotations

from freecad.history_wb.qt import QtCore, QtGui, QtWidgets
from freecad.history_wb.ui.views.document_diff.document_row import REMOVE_REVIEWED_TOOLTIP
from freecad.history_wb.ui.views.document_diff.summary_bar import DocumentDiffSummaryBar
from freecad.history_wb.ui.views.document_diff.summary_state import SummaryButtonState, SummaryCounts


def test_set_summary_counts_with_zero_changes(application) -> None:  # type: ignore[no-untyped-def]
    """set_summary_counts with zero values displays 0 for all counts."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    widget.set_summary_counts(SummaryCounts())

    assert widget._modified_count_label.text() == "0"
    assert widget._deleted_count_label.text() == "0"
    assert widget._added_count_label.text() == "0"


def test_set_summary_counts_with_per_status_counts(application) -> None:  # type: ignore[no-untyped-def]
    """set_summary_counts displays correct counts for each status."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    widget.set_summary_counts(SummaryCounts(modified_docs=2, deleted_docs=1, added_docs=3))

    assert widget._modified_count_label.text() == "2"
    assert widget._deleted_count_label.text() == "1"
    assert widget._added_count_label.text() == "3"


def test_stage_all_button_visibility_and_enabled(application) -> None:  # type: ignore[no-untyped-def]
    """Stage-all icon remains accessible while visibility and enabled state change."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    assert widget._stage_all_button.text() == ""
    assert not widget._stage_all_button.icon().isNull()
    assert widget._stage_all_button.toolTip() == "Mark All Reviewed"
    assert widget._stage_all_button.accessibleName() == "Mark All Reviewed"
    widget.set_button_states(SummaryButtonState(True, True, False, False, False, False))
    assert not widget._stage_all_button.isHidden()
    assert widget._stage_all_button.isEnabled()

    widget.set_button_states(SummaryButtonState(False, False, False, False, False, False))
    assert not widget._stage_all_button.isEnabled()
    assert widget._stage_all_button.isHidden()


def test_bulk_action_buttons_use_theme_aware_style(application) -> None:  # type: ignore[no-untyped-def]
    """Bulk actions bind styling to current application theme."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    assert widget._action_layout.spacing() == 4
    for button in (widget._stage_all_button, widget._restore_all_button, widget._remove_all_button):
        assert button.property("historyDarkTheme") is not None


def test_bulk_action_icons_use_button_text_color(application) -> None:  # type: ignore[no-untyped-def]
    """Bulk icons match action text color in normal and disabled icon modes."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)
    palette = widget.palette()
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(130, 130, 130))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(0, 0, 0))
    widget.setPalette(palette)
    widget.set_button_states(SummaryButtonState(True, True, False, False, False, False))
    QtWidgets.QApplication.sendEvent(
        widget._stage_all_button,
        QtCore.QEvent(QtCore.QEvent.Type.PaletteChange),
    )

    center_color = widget._stage_all_button.icon().pixmap(64, 64).toImage().pixelColor(32, 32)
    disabled_center_color = (
        widget._stage_all_button.icon()
        .pixmap(QtCore.QSize(64, 64), QtGui.QIcon.Mode.Disabled)
        .toImage()
        .pixelColor(32, 32)
    )
    assert center_color == QtGui.QColor(0, 0, 0)
    assert disabled_center_color == QtGui.QColor(0, 0, 0)


def test_remove_all_button_visibility_and_callback(application) -> None:  # type: ignore[no-untyped-def]
    """Remove-all icon keeps tooltip, accessibility, visibility, and callback routing."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)
    captured: list[str] = []
    widget.remove_all_requested.connect(lambda: captured.append("remove"))

    widget.set_button_states(SummaryButtonState(False, False, True, True, False, False))
    widget._remove_all_button.click()

    assert widget._remove_all_button.text() == ""
    assert not widget._remove_all_button.icon().isNull()
    assert widget._remove_all_button.accessibleName() == "Remove All"
    assert "will not be saved in the next iteration" in widget._remove_all_button.toolTip()
    assert not widget._remove_all_button.isHidden()
    assert captured == ["remove"]


def test_restore_all_button_visibility_and_callback(application) -> None:  # type: ignore[no-untyped-def]
    """Restore-all icon stays accessible and emits when clicked."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)
    captured: list[str] = []
    widget.restore_all_requested.connect(lambda: captured.append("restore"))

    widget.set_button_states(SummaryButtonState(False, False, False, False, True, True))
    widget._restore_all_button.click()

    assert widget._restore_all_button.text() == ""
    assert not widget._restore_all_button.icon().isNull()
    assert widget._restore_all_button.accessibleName() == "Restore All"
    assert "Choose which files to restore" in widget._restore_all_button.toolTip()
    assert not widget._restore_all_button.isHidden()
    assert captured == ["restore"]
