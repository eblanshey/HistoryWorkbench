"""File responsibility: Unit tests for extracted property diff tree item builders."""

from __future__ import annotations

import pytest

from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtCore
from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation
from freecad.history_wb.ui.views.property_diff.tree_items import (
    PROPERTY_DIFF_STATE_ROLE,
    apply_stored_expansion_state,
    build_grouped_property_items,
)


def test_group_header_is_non_selectable(widget) -> None:  # type: ignore[no-untyped-def]
    """Builder creates non-selectable group header rows."""
    group_item = _build_single_group(widget)
    assert not (group_item.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable)


def test_groups_are_expanded_by_default(widget) -> None:  # type: ignore[no-untyped-def]
    """Top-level groups stay expanded so properties remain visible."""
    group_item = _build_single_group(widget)
    assert group_item.isExpanded()


def test_groups_appear_in_alphabetical_order(widget) -> None:  # type: ignore[no-untyped-def]
    """Builder sorts groups alphabetically while preserving input order inside groups."""
    properties = [
        PropertyPresentation(name="ZebraProp", state=DiffState.MODIFIED, group="Zebra"),
        PropertyPresentation(name="AlphaProp", state=DiffState.MODIFIED, group="Alpha"),
        PropertyPresentation(name="MiddleProp", state=DiffState.MODIFIED, group="Middle"),
        PropertyPresentation(name="BetaProp", state=DiffState.MODIFIED, group="Beta"),
    ]

    items = build_grouped_property_items(properties, 6)

    assert [item.text(0) for item in items] == ["Alpha", "Beta", "Middle", "Zebra"]


def test_properties_within_groups_maintain_input_order(widget) -> None:  # type: ignore[no-untyped-def]
    """Builder preserves source order for properties within same group."""
    properties = [
        PropertyPresentation(name="ZProp", state=DiffState.UNCHANGED, group="TestGroup"),
        PropertyPresentation(name="AProp", state=DiffState.UNCHANGED, group="TestGroup"),
        PropertyPresentation(name="MProp", state=DiffState.UNCHANGED, group="TestGroup"),
    ]

    items = build_grouped_property_items(properties, 6)
    group_item = items[0]

    assert [group_item.child(index).text(0) for index in range(group_item.childCount())] == [
        "Z Prop",
        "A Prop",
        "M Prop",
    ]


@pytest.mark.parametrize(
    ("state", "old_val", "new_val", "col1", "col2"),
    [
        (DiffState.ADDED, None, "25.0", "", "25.0"),
        (DiffState.DELETED, "15.0", None, "15.0", ""),
        (DiffState.MODIFIED, "10.0", "20.0", "10.0", "20.0"),
    ],
)
def test_state_variant_columns(
    widget,
    state,
    old_val,
    new_val,
    col1,
    col2,
) -> None:  # type: ignore[no-untyped-def]
    """Builder keeps changed-state display columns before widget installation."""
    properties = [
        PropertyPresentation(name="TestProp", old_value=old_val, new_value=new_val, state=state),
    ]

    items = build_grouped_property_items(properties, 6)
    prop_item = items[0].child(0)

    assert prop_item.text(1) == col1
    assert prop_item.text(2) == col2
    assert [prop_item.data(column, PROPERTY_DIFF_STATE_ROLE) for column in range(3)] == [state, state, state]


def test_property_with_unchanged_state_uses_normal_background(widget) -> None:  # type: ignore[no-untyped-def]
    """Builder leaves unchanged rows on normal palette background."""
    properties = [
        PropertyPresentation(name="ChangedProp", old_value="10.0", new_value="20.0", state=DiffState.MODIFIED),
        PropertyPresentation(name="UnchangedProp", old_value="50.0", new_value="50.0", state=DiffState.UNCHANGED),
        PropertyPresentation(name="AnotherChanged", old_value=None, new_value="75.0", state=DiffState.ADDED),
    ]

    items = build_grouped_property_items(properties, 6)
    group_item = items[0]
    names = [group_item.child(index).text(0) for index in range(group_item.childCount())]

    unchanged_item = group_item.child(names.index("Unchanged Prop"))
    assert unchanged_item.text(1) == "50.0"
    assert unchanged_item.text(2) == "50.0"


def test_nested_children_recurse_and_expansion_state_applied(widget) -> None:  # type: ignore[no-untyped-def]
    """Changed descendants keep recursive children expanded after insertion."""
    x_child = PropertyPresentation(name="x", state=DiffState.MODIFIED, old_value=1.0, new_value=2.0)
    base_parent = PropertyPresentation(name="Base", state=DiffState.MODIFIED, children=[x_child])
    placement = PropertyPresentation(name="Placement", state=DiffState.MODIFIED, children=[base_parent])

    items = build_grouped_property_items([placement], 6)
    widget.addTopLevelItems(items)
    apply_stored_expansion_state(items)
    prop_item = items[0].child(0)

    assert prop_item.isExpanded()
    assert prop_item.child(0).isExpanded()
    assert prop_item.child(0).child(0).isExpanded()


def test_unchanged_branches_collapsed(widget) -> None:  # type: ignore[no-untyped-def]
    """Unchanged descendants remain collapsed when no changed rows exist."""
    x_child = PropertyPresentation(name="x", state=DiffState.UNCHANGED, old_value=1.0, new_value=1.0)
    base_parent = PropertyPresentation(name="Base", state=DiffState.UNCHANGED, children=[x_child])
    placement = PropertyPresentation(name="Placement", state=DiffState.UNCHANGED, children=[base_parent])

    items = build_grouped_property_items([placement], 6)
    widget.addTopLevelItems(items)
    apply_stored_expansion_state(items)
    prop_item = items[0].child(0)

    assert not prop_item.isExpanded()
    assert not prop_item.child(0).isExpanded()
    assert not prop_item.child(0).child(0).isExpanded()


def _build_single_group(widget):  # type: ignore[no-untyped-def]
    """Create one simple grouped property item for header assertions."""
    items = build_grouped_property_items([PropertyPresentation(name="TestProp", state=DiffState.MODIFIED)], 6)
    widget.addTopLevelItems(items)
    apply_stored_expansion_state(items)
    return items[0]
