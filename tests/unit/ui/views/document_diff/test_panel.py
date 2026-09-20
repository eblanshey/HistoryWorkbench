"""File responsibility: Unit tests for document diff panel facade orchestration and stable public API."""

from __future__ import annotations

import pytest

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation, NodePresentation
from freecad.history_wb.ui.views.history.models import HistorySelection


def _tree_widget(panel) -> QtWidgets.QTreeWidget:  # type: ignore[no-untyped-def]
    """Find rendered document tree through observable object name."""
    tree = panel.findChild(QtWidgets.QTreeWidget, "documentDiffTree")
    assert tree is not None
    return tree


def _first_document_row_button(panel, accessible_name: str) -> QtWidgets.QToolButton:  # type: ignore[no-untyped-def]
    """Find first top-level document-row action button by accessible name."""
    tree = _tree_widget(panel)
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    row_widget = tree.itemWidget(root_item, 0)
    assert row_widget is not None

    for button in row_widget.findChildren(QtWidgets.QToolButton):
        if button.accessibleName() == accessible_name:
            return button
    raise RuntimeError(f"Document row button not found: {accessible_name}")


def _node(
    *,
    path: str = "Body/Pad",
    type_id: str = "PartDesign::Pad",
    label: str = "Pad",
    state: DiffState = DiffState.MODIFIED,
    has_changes: bool = True,
    visual_diff_enabled: bool = False,
    children: list[NodePresentation] | None = None,
) -> NodePresentation:
    """Build node presentation for panel tests."""
    return NodePresentation(
        path=path,
        type_id=type_id,
        label=label,
        state=state,
        has_changes=has_changes,
        visual_diff_enabled=visual_diff_enabled,
        children=[] if children is None else children,
    )


def _diff(*, nodes: list[NodePresentation] | None = None, state: DiffState = DiffState.UNCHANGED) -> DiffTreePresentation:
    """Build document diff presentation for panel tests."""
    return DiffTreePresentation(
        nodes=[] if nodes is None else nodes,
        git_path="parts/A.FCStd",
        indicators=[],
        document_state=state,
    )


def test_show_doc_diffs_creates_top_level_document_rows(panel) -> None:  # type: ignore[no-untyped-def]
    """show_doc_diffs() creates top-level document rows."""
    panel.show_doc_diffs([_diff(nodes=[_node()])])

    tree = _tree_widget(panel)
    assert tree.topLevelItemCount() == 1
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    row_widget = tree.itemWidget(root_item, 0)
    assert row_widget is not None
    label = row_widget.findChild(QtWidgets.QLabel)
    assert label is not None
    assert root_item.text(0) == ""
    assert label.text() == "parts/A.FCStd"
    assert not label.isHidden()


@pytest.mark.parametrize("state", [DiffState.ADDED, DiffState.DELETED])
def test_show_doc_diffs_applies_document_row_diff_state(panel, state: DiffState) -> None:  # type: ignore[no-untyped-def]
    """Document rows keep diff-state styling after tree extraction."""
    panel.show_doc_diffs([_diff(state=state)])

    tree = _tree_widget(panel)
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    row_widget = tree.itemWidget(root_item, 0)
    assert row_widget is not None
    assert "background-color" in tree.styleSheet()
    assert "QWidget#diffRowContainer" in tree.styleSheet()
    assert row_widget.styleSheet() == ""


def test_show_doc_diffs_with_empty_list_clears_tree(panel) -> None:  # type: ignore[no-untyped-def]
    """show_doc_diffs() clears tree when given empty list."""
    panel.show_doc_diffs([_diff(nodes=[_node()])])

    assert _tree_widget(panel).topLevelItemCount() == 1

    panel.show_doc_diffs([])

    assert _tree_widget(panel).topLevelItemCount() == 0


def test_node_selection_requested_signal_routes_tree_selection(panel) -> None:  # type: ignore[no-untyped-def]
    """Panel forwards extracted tree selection through facade signal."""
    captured: list[tuple[str, str]] = []
    panel.node_selection_requested.connect(lambda git_path, node_path: captured.append((git_path, node_path)))
    panel.show_doc_diffs([_diff(nodes=[_node(path="Body", type_id="PartDesign::Body", label="Body")])])

    tree = _tree_widget(panel)
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    child_item = root_item.child(0)
    assert child_item is not None

    tree.itemClicked.emit(child_item, 0)

    assert captured == [("parts/A.FCStd", "Body")]


def test_visual_diff_requested_signal_routes_extracted_tree_signal(panel) -> None:  # type: ignore[no-untyped-def]
    """Panel forwards extracted visual-diff node action through facade signal."""
    captured: list[tuple[str, str]] = []
    panel.visual_diff_requested.connect(lambda git_path, node_path: captured.append((git_path, node_path)))
    panel.show_doc_diffs([_diff(nodes=[_node(visual_diff_enabled=True)])])

    tree = _tree_widget(panel)
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    child_item = root_item.child(0)
    assert child_item is not None
    row_widget = tree.itemWidget(child_item, 0)
    assert row_widget is not None

    button = row_widget.findChild(QtWidgets.QToolButton)
    assert button is not None
    button.click()

    assert captured == [("parts/A.FCStd", "Body/Pad")]


def test_widget_clears_document_diffs_without_property_widget(panel) -> None:  # type: ignore[no-untyped-def]
    """DocumentDiffTreeWidget does not need property widget reference to clear diffs."""
    panel.show_doc_diffs([_diff(nodes=[_node()])])

    assert _tree_widget(panel).topLevelItemCount() == 1

    panel.clear_doc_diffs()

    assert _tree_widget(panel).topLevelItemCount() == 0


def test_widget_renders_document_diffs_without_property_widget(panel) -> None:  # type: ignore[no-untyped-def]
    """DocumentDiffTreeWidget does not need property widget reference to render diffs."""
    panel.show_doc_diffs([_diff(nodes=[_node()])])

    tree = _tree_widget(panel)
    assert tree.topLevelItemCount() == 1
    root_item = tree.topLevelItem(0)
    assert root_item is not None
    assert root_item.childCount() == 1


def test_set_stage_button_enabled_updates_button(panel) -> None:  # type: ignore[no-untyped-def]
    """set_stage_button_enabled() updates rendered stage button for git_path."""
    panel.set_current_history_selection(HistorySelection(item_kind="WORKING_TREE", commit_hash=None))
    panel.show_doc_diffs(
        [
            DiffTreePresentation(
                nodes=[_node()],
                git_path="parts/A.FCStd",
                indicators=[],
                stage_button_enabled=True,
            )
        ]
    )

    stage_button = _first_document_row_button(panel, "Mark this document as reviewed")
    assert stage_button.isEnabled()

    panel.set_stage_button_enabled("parts/A.FCStd", False)

    assert not stage_button.isEnabled()
