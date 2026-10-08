# File responsibility: Unit tests for pure summary-state helpers used by diff presenter.

import pytest

from freecad.history_wb.application.actions.result_models import DiffIssues, DocumentDiffResult
from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.ui.presenters.document_diff.summary_state import (
    SummaryButtonState,
    SummaryCounts,
    build_summary_button_state,
    count_summary_counts,
)
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation
from freecad.history_wb.ui.views.history.models import HistorySelection


def test_count_summary_counts_counts_document_states() -> None:
    """Summary counts derive only from document state buckets."""
    counts = count_summary_counts(
        [
            DocumentDiffResult(git_path="a.FCStd", document_state=DiffState.MODIFIED, issues=DiffIssues()),
            DocumentDiffResult(git_path="b.FCStd", document_state=DiffState.DELETED, issues=DiffIssues()),
            DocumentDiffResult(git_path="c.FCStd", document_state=DiffState.ADDED, issues=DiffIssues()),
            DocumentDiffResult(git_path="d.FCStd", document_state=DiffState.UNCHANGED, issues=DiffIssues()),
        ]
    )

    assert counts == SummaryCounts(modified_docs=1, deleted_docs=1, added_docs=1)


@pytest.mark.parametrize(
    ("document_state", "stage_enabled", "restore_enabled"),
    [
        (None, False, False),
        (DiffState.ADDED, True, False),
        (DiffState.MODIFIED, False, True),
        (DiffState.MODIFIED, True, True),
        (DiffState.DELETED, True, True),
    ],
)
def test_build_summary_button_state_for_working_tree(
    document_state: DiffState | None, stage_enabled: bool, restore_enabled: bool
) -> None:
    """Current Files enables restore for indexed rows, independently of review eligibility."""
    presentations = (
        [
            DiffTreePresentation(
                nodes=[],
                git_path="a.FCStd",
                indicators=[],
                document_state=document_state,
                stage_button_enabled=stage_enabled,
            )
        ]
        if document_state is not None
        else []
    )
    state = build_summary_button_state(
        HistorySelection(item_kind="WORKING_TREE", commit_hash=None),
        presentations,
    )

    assert state == SummaryButtonState(True, stage_enabled, False, False, True, restore_enabled, True)


def test_build_summary_button_state_for_staging() -> None:
    """Staging shows remove-all and restore-all when rows exist."""
    state = build_summary_button_state(
        HistorySelection(item_kind="STAGING", commit_hash=None),
        [DiffTreePresentation(nodes=[], git_path="a.FCStd", indicators=[])],
    )

    assert state == SummaryButtonState(False, False, True, True, True, True)


def test_build_summary_button_state_for_commit() -> None:
    """Commit view shows restore-all only when rows exist."""
    state = build_summary_button_state(
        HistorySelection(item_kind="COMMIT", commit_hash="abc123"),
        [DiffTreePresentation(nodes=[], git_path="a.FCStd", indicators=[])],
    )

    assert state == SummaryButtonState(False, False, False, False, True, True)


def test_build_summary_button_state_for_none_selection() -> None:
    """Missing selection hides and disables every summary action."""
    state = build_summary_button_state(None, [DiffTreePresentation(nodes=[], git_path="a.FCStd", indicators=[])])

    assert state == SummaryButtonState(False, False, False, False, False, False)
