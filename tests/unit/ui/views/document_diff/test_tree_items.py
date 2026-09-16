"""File responsibility: Unit tests for structural document diff tree-item builders."""

from __future__ import annotations

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtCore
from freecad.history_wb.ui.presenters.presentation_models import NodePresentation
from freecad.history_wb.ui.views.document_diff.tree_items import build_document_root_item, build_node_item


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
    """Build node presentation for tree-item tests."""
    return NodePresentation(
        path=path,
        type_id=type_id,
        label=label,
        state=state,
        has_changes=has_changes,
        visual_diff_enabled=visual_diff_enabled,
        children=[] if children is None else children,
    )


def test_build_document_root_item_stores_git_path() -> None:
    """Document root items keep display text and structural git path."""
    item = build_document_root_item("parts/A.FCStd", "parts/A.FCStd")

    assert item.text(0) == "parts/A.FCStd"
    assert item.data(0, QtCore.Qt.ItemDataRole.UserRole) == "parts/A.FCStd"


def test_build_node_item_stores_path_and_tooltip() -> None:
    """Node items store path in user role and type in tooltip."""
    item = build_node_item(_node(path="Body/Pad/Length", type_id="PropertyLength", label="Length"))

    assert item.data(0, QtCore.Qt.ItemDataRole.UserRole) == "Body/Pad/Length"
    assert item.toolTip(0) == "PropertyLength"


def test_build_node_item_recurses_children_and_formats_mismatched_names() -> None:
    """Node tree builder recurses through children and includes basename when label differs."""
    item = build_node_item(
        _node(
            path="Body",
            type_id="PartDesign::Body",
            label="Main Body",
            children=[
                _node(
                    path="Body/Pad001",
                    type_id="PartDesign::Pad",
                    label="Pad",
                )
            ],
        )
    )

    assert item.text(0) == "Main Body (Body)"
    assert item.childCount() == 1
    child_item = item.child(0)
    assert child_item is not None
    assert child_item.text(0) == "Pad (Pad001)"
