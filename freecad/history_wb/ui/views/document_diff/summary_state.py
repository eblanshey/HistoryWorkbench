# File responsibility: Summary bar state dataclasses for document diff view.
"""Summary bar state dataclasses for document diff view."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryButtonState:
    """Visibility and enabled state for summary-bar bulk actions."""

    stage_all_visible: bool
    stage_all_enabled: bool
    remove_all_visible: bool
    remove_all_enabled: bool
    restore_all_visible: bool
    restore_all_enabled: bool
    restore_all_from_index: bool = False

    @staticmethod
    def hidden() -> "SummaryButtonState":
        """Return a state with all buttons hidden and disabled."""
        return SummaryButtonState(False, False, False, False, False, False)


@dataclass(frozen=True)
class SummaryCounts:
    """Per-document-state counts shown in summary bar."""

    modified_docs: int = 0
    deleted_docs: int = 0
    added_docs: int = 0
