# File responsibility: Pure property-diff to property-presentation mapping.
"""Pure property-diff to property-presentation mapping helpers."""

import re
from dataclasses import replace
from typing import Any

from ....domain.diff.models import DiffState, NodeDiff, PropertyDiff, PropertyPathDiff
from ....domain.tree import Property
from ....domain.tree.data_path import PropertyPathType, PropertyPathValue
from ....utils import format_float
from ..presentation_models import PropertyPresentation
from .path_tree import (
    _collect_leaf_values,
    _derive_container_summary,
    _format_path_value,
    _insert_path_diff,
    _path_tree_to_presentations,
    _PathTreeNode,
    _set_subtree_state,
)


def transform_property_diffs(node_diff: NodeDiff, precision: int) -> list[PropertyPresentation]:
    """Transform one node's property diffs into UI presentation rows."""
    presentations: list[PropertyPresentation] = []
    for prop_diff in node_diff.property_diffs:
        group = _extract_property_group(prop_diff.new_value if prop_diff.new_value is not None else prop_diff.old_value)
        presentation = _build_property_presentation(prop_diff, precision, group)

        if node_diff.type_id == "Spreadsheet::Sheet":
            presentation = modify_spreadsheet_presentation(presentation, prop_diff, precision)

        presentations.append(presentation)
    return presentations


def modify_spreadsheet_presentation(
    presentation: PropertyPresentation, prop_diff: PropertyDiff, precision: int
) -> PropertyPresentation:
    """Remove redundant cell expression rows without changing stored source input."""

    # If spreadsheet cell values and contents (stored as expressions) are the same, don't show redundant contents
    if _is_redundant_cell_input(prop_diff, precision):
        return replace(presentation, children=[child for child in presentation.children if child.name != "Expression"])

    return presentation


def _is_redundant_cell_input(prop_diff: PropertyDiff, precision: int) -> bool:
    """Hide matching literal input unless an existing cell's source input changed."""

    # Match cell addresses (A1, AA10), not ordinary sheet properties such as Label.
    if re.fullmatch(r"[A-Z]+[1-9][0-9]*", prop_diff.property_name) is None:
        return False

    root = next((path for path in prop_diff.path_diffs if path.path == "."), None)

    if root is None:
        return False

    old, new = root.old_value, root.new_value

    # Keep syntax-only changes visible even when both inputs match their evaluated values.
    if old is not None and new is not None and old.expression != new.expression:
        return False

    return all(_cell_input_matches_value(value, precision) for value in (old, new) if value is not None)


def _cell_input_matches_value(value: PropertyPathValue, precision: int) -> bool:
    """Compare literal cell input with its displayed value without hiding formulas."""
    expression = value.expression

    if expression is None:
        return True

    if expression.startswith("="):
        return False

    literal = expression.removeprefix("'")

    if literal == str(_format_path_value(value, precision)):
        return True

    # Numeric input may omit decimal places added by display formatting.
    if value.type_ in (PropertyPathType.INT, PropertyPathType.FLOAT):
        try:
            return format_float(float(literal), precision) == format_float(float(value.value), precision)
        except ValueError:
            return False

    return False


def _build_property_presentation(
    prop_diff: PropertyDiff,
    precision: int,
    group: str | None,
) -> PropertyPresentation:
    """Build UI presentation for one property diff."""
    root_path = next((path_diff for path_diff in prop_diff.path_diffs if path_diff.path == "."), None)
    root_state = _property_root_state(prop_diff, root_path)
    root = _PathTreeNode(name=prop_diff.property_name, state=root_state)
    for path_diff in prop_diff.path_diffs:
        _insert_path_diff(root, path_diff)

    # Whole-property add/delete must override nested child states for consistent row coloring.
    if prop_diff.state in (DiffState.ADDED, DiffState.DELETED):
        _set_subtree_state(root, prop_diff.state)

    prop_old_value, prop_new_value = _property_root_values(root, precision)
    return PropertyPresentation(
        name=prop_diff.property_name,
        state=root.state,
        old_value=prop_old_value,
        new_value=prop_new_value,
        children=_path_tree_to_presentations(root, precision),
        group=group,
    )


def _property_root_state(prop_diff: PropertyDiff, root_path: PropertyPathDiff | None) -> DiffState:
    """Return property root state without inheriting child-only changes."""
    if prop_diff.state in (DiffState.ADDED, DiffState.DELETED):
        return prop_diff.state
    return root_path.value_state if root_path is not None else DiffState.UNCHANGED


def _property_root_values(root: _PathTreeNode, precision: int) -> tuple[Any, Any]:
    """Return formatted old and new values for property root row."""
    old_value = root.old_value
    new_value = root.new_value
    if old_value is None and new_value is None and root.children:
        old_leaf_values, new_leaf_values = _collect_leaf_values(root, include_expr=False)
        old_value = _derive_container_summary(old_leaf_values, precision)
        new_value = _derive_container_summary(new_leaf_values, precision)
    return _format_path_value(old_value, precision), _format_path_value(new_value, precision)


def _extract_property_group(prop: Property | None) -> str | None:
    """Extract group name from a property value object."""
    return getattr(prop, "group", None) if prop is not None else None
