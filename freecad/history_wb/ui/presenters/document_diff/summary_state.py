# File responsibility: Pure summary counts and summary-button state computation.
"""Pure summary counts and summary-button state computation.

Imports dataclasses from the view layer and provides computation functions
that operate on presenter-level types (HistorySelection, DiffTreePresentation).
"""

from ....application.actions.result_models import DocumentDiffResult
from ....domain.diff.models import DiffState
from ...views.document_diff.summary_state import SummaryButtonState, SummaryCounts
from ..presentation_models import DiffTreePresentation


def build_summary_button_state(
    current_selection,
    presentations: list[DiffTreePresentation],
) -> SummaryButtonState:
    """Return summary-bar button state for current history selection."""
    if current_selection is None:
        return SummaryButtonState.hidden()

    if current_selection.item_kind == "WORKING_TREE":
        any_stagable = any(p.stage_button_enabled for p in presentations)

        # Added working-tree files have no indexed version to restore.
        any_restorable = any(p.document_state != DiffState.ADDED for p in presentations)
        return SummaryButtonState(
            stage_all_visible=True,
            stage_all_enabled=any_stagable,
            remove_all_visible=False,
            remove_all_enabled=False,
            restore_all_visible=False,
            restore_all_enabled=False,
            discard_all_visible=True,
            discard_all_enabled=any_restorable,
        )

    if current_selection.item_kind == "STAGING":
        has_rows = bool(presentations)
        return SummaryButtonState(
            stage_all_visible=False,
            stage_all_enabled=False,
            remove_all_visible=True,
            remove_all_enabled=has_rows,
            restore_all_visible=False,
            restore_all_enabled=False,
        )

    if current_selection.item_kind == "COMMIT":
        has_rows = bool(presentations)
        return SummaryButtonState(
            stage_all_visible=False,
            stage_all_enabled=False,
            remove_all_visible=False,
            remove_all_enabled=False,
            restore_all_visible=True,
            restore_all_enabled=has_rows,
        )

    raise RuntimeError(f"Unsupported history selection kind: {current_selection.item_kind}")


def count_summary_counts(document_results: list[DocumentDiffResult]) -> SummaryCounts:
    """Count added, deleted, and modified documents for summary display."""
    modified_docs = 0
    deleted_docs = 0
    added_docs = 0
    for document_result in document_results:
        if document_result.document_state == DiffState.MODIFIED:
            modified_docs += 1
        elif document_result.document_state == DiffState.DELETED:
            deleted_docs += 1
        elif document_result.document_state == DiffState.ADDED:
            added_docs += 1
    return SummaryCounts(modified_docs=modified_docs, deleted_docs=deleted_docs, added_docs=added_docs)
