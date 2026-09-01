"""File responsibility: Unit tests for extracted document diff tree widget behavior."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtWidgets
from freecad.history_wb.ui.presenters.presentation_models import DiffTreePresentation, NodePresentation


def _tree_widget(tree) -> QtWidgets.QTreeWidget:  # type: ignore[no-untyped-def]
    """Find rendered document tree through observable object name."""
    widget = tree.findChild(QtWidgets.QTreeWidget, "documentDiffTree")
    assert widget is not None
    return widget


def _collapse_all_button(tree) -> QtWidgets.QToolButton:  # type: ignore[no-untyped-def]
    """Find collapse-all action through accessible name."""
    for button in tree.findChildren(QtWidgets.QToolButton):
        if button.accessibleName() == "Collapse All":
            return button
    raise RuntimeError("Collapse All button not found")


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
    """Build node presentation for extracted tree tests."""
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
    """Build document diff presentation for extracted tree tests."""
    return DiffTreePresentation(
        nodes=[] if nodes is None else nodes,
        git_path="parts/A.FCStd",
        indicators=[],
        document_state=state,
    )


def test_collapse_all_button_is_icon_only(tree) -> None:  # type: ignore[no-untyped-def]
    """Collapse All action uses icon-only button with tooltip."""
    collapse_button = _collapse_all_button(tree)
    assert collapse_button.text() == ""
    assert not collapse_button.icon().isNull()
    assert "Collapse All" in collapse_button.toolTip()


def test_collapse_tree_item_collapses_root(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """collapse_tree_item() collapses root item for given git_path."""
    tree.show_doc_diffs([_diff(nodes=[_node()])], simple_document_row_factory)

    root_item = _tree_widget(tree).topLevelItem(0)
    assert root_item is not None
    root_item.setExpanded(True)
    assert root_item.isExpanded()

    tree.collapse_tree_item("parts/A.FCStd")

    assert not root_item.isExpanded()


def test_collapse_all_tree_items_collapses_every_root(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """collapse_all_tree_items() collapses every expanded root item."""
    tree.show_doc_diffs(
        [
            _diff(nodes=[_node()]),
            DiffTreePresentation(nodes=[_node()], git_path="parts/B.FCStd", indicators=[]),
        ],
        simple_document_row_factory,
    )
    widget = _tree_widget(tree)
    first_root = widget.topLevelItem(0)
    second_root = widget.topLevelItem(1)
    assert first_root is not None
    assert second_root is not None
    first_root.setExpanded(True)
    second_root.setExpanded(True)

    tree.collapse_all_tree_items()

    assert not first_root.isExpanded()
    assert not second_root.isExpanded()


def test_node_selected_emits_git_path_and_node_path(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Child item clicks emit extracted node selection coordinates."""
    captured: list[tuple[str, str]] = []
    tree.node_selected.connect(lambda git_path, node_path: captured.append((git_path, node_path)))
    tree.show_doc_diffs([_diff(nodes=[_node(path="Body", type_id="PartDesign::Body", label="Body")])], simple_document_row_factory)

    widget = _tree_widget(tree)
    root_item = widget.topLevelItem(0)
    assert root_item is not None
    child_item = root_item.child(0)
    assert child_item is not None

    widget.itemClicked.emit(child_item, 0)

    assert captured == [("parts/A.FCStd", "Body")]


def test_root_click_does_not_emit_node_selected(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Root document clicks do not emit node selection because property pane needs node path."""
    captured: list[tuple[str, str]] = []
    tree.node_selected.connect(lambda git_path, node_path: captured.append((git_path, node_path)))
    tree.show_doc_diffs([_diff(nodes=[_node()])], simple_document_row_factory)

    root_item = _tree_widget(tree).topLevelItem(0)
    assert root_item is not None

    _tree_widget(tree).itemClicked.emit(root_item, 0)

    assert captured == []


def test_visual_diff_button_selects_item_and_emits_both_signals(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Visual diff action selects row, emits normal selection, then emits visual diff request."""
    selected: list[tuple[str, str]] = []
    visual_diff: list[tuple[str, str]] = []
    tree.node_selected.connect(lambda git_path, node_path: selected.append((git_path, node_path)))
    tree.visual_diff_requested.connect(lambda git_path, node_path: visual_diff.append((git_path, node_path)))
    tree.show_doc_diffs([_diff(nodes=[_node(visual_diff_enabled=True)])], simple_document_row_factory)

    widget = _tree_widget(tree)
    root_item = widget.topLevelItem(0)
    assert root_item is not None
    child_item = root_item.child(0)
    assert child_item is not None
    row_widget = widget.itemWidget(child_item, 0)
    assert row_widget is not None
    button = row_widget.findChild(QtWidgets.QToolButton)
    assert button is not None

    button.click()

    assert widget.currentItem() is child_item
    assert selected == [("parts/A.FCStd", "Body/Pad")]
    assert visual_diff == [("parts/A.FCStd", "Body/Pad")]


def test_visual_diff_row_widget_owns_visible_text(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Visual-diff rows avoid duplicate delegate and row-widget labels."""
    tree.show_doc_diffs([_diff(nodes=[_node(visual_diff_enabled=True)])], simple_document_row_factory)

    widget = _tree_widget(tree)
    root_item = widget.topLevelItem(0)
    assert root_item is not None
    child_item = root_item.child(0)
    assert child_item is not None
    row_widget = widget.itemWidget(child_item, 0)
    assert row_widget is not None
    label = row_widget.findChild(QtWidgets.QLabel)
    assert label is not None

    assert child_item.text(0) == ""
    assert label.text() == "Pad"


def test_visual_diff_button_only_for_enabled_nodes(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Visual diff widgets appear only for enabled nodes."""
    tree.show_doc_diffs(
        [
            _diff(
                nodes=[
                    _node(visual_diff_enabled=True),
                    _node(path="Body/Sketch", type_id="App::FeaturePython", label="Sketch", visual_diff_enabled=False),
                ]
            )
        ],
        simple_document_row_factory,
    )

    widget = _tree_widget(tree)
    root_item = widget.topLevelItem(0)
    assert root_item is not None
    first_item = root_item.child(0)
    second_item = root_item.child(1)
    assert first_item is not None
    assert second_item is not None
    first_row = widget.itemWidget(first_item, 0)
    second_row = widget.itemWidget(second_item, 0)
    assert first_row is not None
    assert second_row is None
    assert len(first_row.findChildren(QtWidgets.QToolButton)) == 1


def test_nodes_with_changed_descendants_expand_ancestor_branch(tree, simple_document_row_factory) -> None:  # type: ignore[no-untyped-def]
    """Tree expands ancestor branches when descendants have changes."""
    tree.show_doc_diffs(
        [
            _diff(
                nodes=[
                    _node(
                        path="Body",
                        type_id="PartDesign::Body",
                        label="Body",
                        has_changes=True,
                        children=[_node(path="Body/Pad", visual_diff_enabled=False)],
                    )
                ]
            )
        ],
        simple_document_row_factory,
    )

    root_item = _tree_widget(tree).topLevelItem(0)
    assert root_item is not None
    body_item = root_item.child(0)
    assert body_item is not None
    assert root_item.isExpanded()
    assert body_item.isExpanded()
