"""File responsibility: Build grouped property diff tree items and expansion state."""

from __future__ import annotations

from ....domain.diff.models import DiffState
from ....qt import QtCore, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import PropertyPresentation
from .formatters import build_property_tooltip, camelcase_to_spaces, get_property_display_values


__all__ = ["PROPERTY_DIFF_STATE_ROLE", "apply_stored_expansion_state", "build_grouped_property_items"]


_EXPAND_STATE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
PROPERTY_DIFF_STATE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2


def build_grouped_property_items(
    properties: list[PropertyPresentation],
    precision: int,
) -> list[QtWidgets.QTreeWidgetItem]:
    """Build grouped top-level tree items for property diff rendering."""
    groups: dict[str, list[PropertyPresentation]] = {}
    for prop in properties:
        group_name = getattr(prop, "group", None) or translate("History", "Properties")
        groups.setdefault(group_name, []).append(prop)

    items: list[QtWidgets.QTreeWidgetItem] = []
    for group_name in sorted(groups.keys()):
        group_item = _create_group_header_item(group_name)
        for prop in groups[group_name]:
            group_item.addChild(_build_property_tree_item(prop, precision))
        group_item.setExpanded(True)
        items.append(group_item)

    return items


def _create_group_header_item(group_name: str) -> QtWidgets.QTreeWidgetItem:
    """Create one non-selectable group header row."""
    item = QtWidgets.QTreeWidgetItem([group_name, "", ""])
    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
    font = item.font(0)
    font.setBold(True)
    for column in range(3):
        item.setFont(column, font)
    return item


def _build_property_tree_item(
    prop: PropertyPresentation,
    precision: int,
) -> QtWidgets.QTreeWidgetItem:
    """Build one property tree row and all descendants."""
    left_value, right_value = get_property_display_values(
        prop.state,
        old_value=prop.old_value,
        new_value=prop.new_value,
        precision=precision,
    )
    item = QtWidgets.QTreeWidgetItem([camelcase_to_spaces(prop.name), left_value, right_value])
    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

    tooltip = build_property_tooltip(left_value, right_value)
    for column in range(3):
        item.setToolTip(column, tooltip)

    item.setData(0, _EXPAND_STATE_ROLE, _presentation_has_changes(prop))
    item.setData(0, PROPERTY_DIFF_STATE_ROLE, prop.state)
    for child in prop.children:
        item.addChild(_build_property_tree_item(child, precision))

    return item


def _presentation_has_changes(prop: PropertyPresentation) -> bool:
    """Return whether property or any descendant carries a changed diff state."""
    if prop.state != DiffState.UNCHANGED:
        return True
    return any(_presentation_has_changes(child) for child in prop.children)


def apply_stored_expansion_state(items: list[QtWidgets.QTreeWidgetItem]) -> None:
    """Apply stored expansion flags after whole tree structure exists."""
    for item in items:
        item.setExpanded(True)
        _apply_expansion_recursive(item)


def _apply_expansion_recursive(item: QtWidgets.QTreeWidgetItem) -> None:
    """Apply expansion flag to one item and all descendants."""
    if item.data(0, _EXPAND_STATE_ROLE):
        item.setExpanded(True)
    for index in range(item.childCount()):
        _apply_expansion_recursive(item.child(index))
