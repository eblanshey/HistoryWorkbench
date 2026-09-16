"""File responsibility: Unit tests for document diff summary bar behavior."""

from __future__ import annotations

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
    """Stage-all visibility and enabled state stay controllable."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    widget.set_button_states(SummaryButtonState(True, True, False, False, False, False))
    assert not widget._stage_all_button.isHidden()
    assert widget._stage_all_button.isEnabled()

    widget.set_button_states(SummaryButtonState(False, False, False, False, False, False))
    assert not widget._stage_all_button.isEnabled()
    assert widget._stage_all_button.isHidden()


def test_bulk_action_buttons_override_transparent_host_theme(application) -> None:  # type: ignore[no-untyped-def]
    """Bulk actions use paired palette colors instead of host-transparent tool buttons."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)

    for button in (widget._stage_all_button, widget._restore_all_button, widget._remove_all_button):
        assert "background-color: palette(button)" in button.styleSheet()
        assert "color: palette(button-text)" in button.styleSheet()
        assert "background-color: transparent" not in button.styleSheet()


def test_remove_all_button_visibility_and_callback(application) -> None:  # type: ignore[no-untyped-def]
    """Remove All button keeps text, tooltip, visibility, and callback routing."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)
    captured: list[str] = []
    widget.remove_all_requested.connect(lambda: captured.append("remove"))

    widget.set_button_states(SummaryButtonState(False, False, True, True, False, False))
    widget._remove_all_button.click()

    assert widget._remove_all_button.text() == "Remove All"
    assert "will not be saved in the next iteration" in widget._remove_all_button.toolTip()
    assert not widget._remove_all_button.isHidden()
    assert captured == ["remove"]


def test_restore_all_button_visibility_and_callback(application) -> None:  # type: ignore[no-untyped-def]
    """Restore All button stays hidden by default and emits when clicked."""
    widget = DocumentDiffSummaryBar(REMOVE_REVIEWED_TOOLTIP)
    captured: list[str] = []
    widget.restore_all_requested.connect(lambda: captured.append("restore"))

    widget.set_button_states(SummaryButtonState(False, False, False, False, True, True))
    widget._restore_all_button.click()

    assert not widget._restore_all_button.isHidden()
    assert captured == ["restore"]
