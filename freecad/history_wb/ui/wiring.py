# ruff: noqa: E501
# Ignored for signal readability in event-binding tables.
# File responsibility: Wire public UI component signals to presenter slots.
"""UI signal wiring helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .presenters.diff_presenter import DiffPresenter
from .presenters.git_repository_presenter import GitRepositoryPresenter
from .views.diff_panel.view import HistoryPanelView


__all__ = ["bind_ui_events", "bind_history_events", "bind_document_diff_events"]


def bind_ui_events(
    view: HistoryPanelView,
    diff_presenter: DiffPresenter,
    git_repo_presenter: GitRepositoryPresenter,
) -> None:
    """Bind public UI component signals to presenter slots."""
    bind_history_events(view, diff_presenter, git_repo_presenter)
    bind_document_diff_events(view, diff_presenter)

    history_selection_bindings = [
        (view.history_selection_changed, diff_presenter.track_history_selection),
    ]

    _bind_signal_pairs(history_selection_bindings)


def bind_history_events(
    view: HistoryPanelView,
    diff_presenter: DiffPresenter,
    git_repo_presenter: GitRepositoryPresenter,
) -> None:
    """Bind history-column public signals to presenter listeners."""
    history_panel = view.history_panel

    signal_bindings = [
        (history_panel.refresh_requested, git_repo_presenter.refresh_repository_and_commits),
        (history_panel.save_iteration_requested, git_repo_presenter.save_iteration),
        (history_panel.history_scroll_bottom_requested, git_repo_presenter.load_more_commits),
        (history_panel.history_selection_requested, diff_presenter.select_history_item),
        (history_panel.remove_all_from_reviewed_requested, diff_presenter.remove_all_from_reviewed),
        (history_panel.mark_all_reviewed_from_in_progress_requested, diff_presenter.stage_all_documents),
        (history_panel.restore_all_from_history_context_requested, diff_presenter.restore_all_from_history),
        (history_panel.discard_all_from_current_files_requested, diff_presenter.discard_all_from_current_files),
    ]

    _bind_signal_pairs(signal_bindings)


def bind_document_diff_events(view: HistoryPanelView, diff_presenter: DiffPresenter) -> None:
    """Bind document-diff public signals to presenter listeners."""
    document_diff_panel = view.document_diff_panel

    signal_bindings = [
        (document_diff_panel.add_requested, diff_presenter.stage_document),
        (document_diff_panel.stage_all_requested, diff_presenter.stage_all_documents),
        (document_diff_panel.remove_all_requested, diff_presenter.remove_all_from_reviewed),
        (document_diff_panel.remove_from_reviewed_requested, diff_presenter.remove_document_from_reviewed),
        (document_diff_panel.restore_requested, diff_presenter.restore_document),
        (document_diff_panel.restore_all_requested, diff_presenter.restore_all_documents),
        (document_diff_panel.discard_requested, diff_presenter.restore_document),
        (document_diff_panel.discard_all_requested, diff_presenter.restore_all_documents),
        (document_diff_panel.node_selection_requested, diff_presenter.select_node),
        (document_diff_panel.visual_diff_requested, diff_presenter.open_visual_diff),
        (document_diff_panel.open_document_for_comparison_requested, diff_presenter.open_document_for_comparison),
    ]

    _bind_signal_pairs(signal_bindings)


def _bind_signal_pairs(signal_bindings: Sequence[tuple[Any, Any]]) -> None:
    """Connect grouped signal-slot pairs from small event tables."""
    for signal, slot in signal_bindings:
        signal.connect(slot)
