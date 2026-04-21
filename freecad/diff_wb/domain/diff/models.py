# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides models for representing the differences between two
# document snapshots, including property-level and node-level comparisons.
#
# This module contains pure data models with embedded state calculation logic.
# It depends on domain/tree/property.py but has no circular dependencies.
"""Domain models for diff results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, cast

from ..snapshots import Snapshot
from ..tree import Property
from ..tree.data_path import (
    DataPath,
    ListData,
    PlacementData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    RotationData,
    VectorData,
)


class DiffState(Enum):
    """The state of a node or property in a diff comparison.

    This is used for UI highlighting to show changes:
    - ADDED: Node/property exists only in the new snapshot
    - DELETED: Node/property exists only in the old snapshot
    - MODIFIED: Node/property exists in both but has different values
    - UNCHANGED: Node/property is identical in both snapshots
    """

    ADDED = auto()
    DELETED = auto()
    MODIFIED = auto()
    UNCHANGED = auto()


# Warning constants for edge cases
WARNING_OLD_SNAPSHOT_MISSING = "Old snapshot missing"


def _data_path_values_equal_ignoring_expression(old_pv: PropertyPathValue, new_pv: PropertyPathValue) -> bool:
    """Compare two PropertyPathValue instances ignoring expression differences.

    Args:
        old_pv: Value in the old snapshot
        new_pv: Value in the new snapshot

    Returns:
        True if values are equal ignoring expression differences
    """
    if old_pv.type_ != new_pv.type_:
        return False
    # PropertyPathValue.__eq__ already handles float tolerance and expression
    # comparison. For expression-ignoring comparison, compare values only.
    if old_pv.type_ == PropertyPathType.FLOAT:
        tolerance = 1e-9
        return bool(abs(float(old_pv.value) - float(new_pv.value)) < tolerance)
    return old_pv.value == new_pv.value


def _data_paths_equal_ignoring_expression(old_dp: Any, new_dp: Any) -> bool:
    """Compare two DataPath objects ignoring expression differences.

    Uses float-tolerant comparison for PropertyPathValue instances
    via _data_path_values_equal_ignoring_expression.

    Args:
        old_dp: Old DataPath
        new_dp: New DataPath

    Returns:
        True if DataPaths are equal ignoring expressions
    """
    if type(old_dp) is not type(new_dp):
        return False

    # For types with paths, compare paths ignoring expressions
    if isinstance(old_dp, PrimitiveData):
        return all(
            _data_path_values_equal_ignoring_expression(
                old_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
                new_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
            )
            for k in set(old_dp.paths) | set(new_dp.paths)
        )

    if isinstance(old_dp, ListData):
        if len(old_dp.items) != len(new_dp.items):
            return False
        # Compare paths ignoring expressions
        if not all(
            _data_path_values_equal_ignoring_expression(
                old_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
                new_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
            )
            for k in set(old_dp.paths) | set(new_dp.paths)
        ):
            return False
        # Compare items recursively
        return all(
            _data_paths_equal_ignoring_expression(old_item, new_item)
            for old_item, new_item in zip(old_dp.items, new_dp.items, strict=True)
        )

    # For VectorData, RotationData, PlacementData, QuantityData, ConstraintData, UnknownData
    # Compare paths ignoring expressions
    if hasattr(old_dp, "paths") and hasattr(new_dp, "paths"):
        return all(
            _data_path_values_equal_ignoring_expression(
                old_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
                new_dp.paths.get(k, PropertyPathValue(PropertyPathType.NULL, None)),
            )
            for k in set(old_dp.paths) | set(new_dp.paths)
        )

    return False


def _get_data_path_value(dp: Any) -> PropertyPathValue | None:
    """Extract the root PropertyPathValue from a DataPath.

    Args:
        dp: A DataPath instance (PrimitiveData, ListData, etc.)

    Returns:
        The root PropertyPathValue, or None if not a PrimitiveData
    """
    if isinstance(dp, PrimitiveData):
        return dp.paths.get(".")
    return None


def _values_are_equal_ignoring_expression(old_value: Property, new_value: Property, prop_name: str = "") -> bool:
    """Compare two property values ignoring expressions.

    Args:
        old_value: Value in the old snapshot
        new_value: Value in the new snapshot
        prop_name: The property name for logging purposes

    Returns:
        True if values are equal ignoring expression differences
    """
    old_dp = old_value.value
    new_dp = new_value.value

    # Compare internal types first
    if type(old_dp).INTERNAL_TYPE != type(new_dp).INTERNAL_TYPE:
        return False

    # For PrimitiveData, compare the root path value
    old_pv = _get_data_path_value(old_dp)
    new_pv = _get_data_path_value(new_dp)

    if old_pv is not None and new_pv is not None:
        return _data_path_values_equal_ignoring_expression(old_pv, new_pv)

    # For other DataPath types, compare by stripping expressions
    return _data_paths_equal_ignoring_expression(old_dp, new_dp)


def _calculate_property_diff_state(
    old_value: Property | None, new_value: Property | None, prop_name: str = ""
) -> DiffState:
    """Calculate the diff state for a property based on old and new values.

    Note: Expression changes are tracked separately. This function compares
    only the actual values (ignoring expressions) to determine if the value changed.

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        prop_name: The property name for logging purposes

    Returns:
        The appropriate DiffState based on the values
    """
    # If old_value is None, property was added
    if old_value is None:
        return DiffState.ADDED
    # If new_value is None, property was deleted
    if new_value is None:
        return DiffState.DELETED
    # If values are equal (ignoring expressions), unchanged
    values_equal = _values_are_equal_ignoring_expression(old_value, new_value, prop_name)
    if values_equal:
        return DiffState.UNCHANGED
    # Otherwise, modified
    return DiffState.MODIFIED


def _is_vector_like(value: Any) -> bool:
    """Check if value is Vector-like (has x, y, z attributes)."""
    return hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z") and not isinstance(value, (int, float))


def _is_rotation_like(value: Any) -> bool:
    """Check if value is Rotation-like (has angle and axis)."""
    has_angle = hasattr(value, "angle") or hasattr(value, "Angle")
    has_axis = hasattr(value, "axis") or hasattr(value, "Axis")
    return has_angle and has_axis


def _is_placement_like(value: Any) -> bool:
    """Check if value is Placement-like (has position and rotation)."""
    return hasattr(value, "position") and hasattr(value, "rotation")


def _create_property_from_child_value(value: Any, group: str = "Base") -> Property | None:
    """Create a Property from a raw child value or DataPath.

    This wraps raw values from DataPath children into Property objects.
    If the value is already a DataPath, it wraps it directly.

    Args:
        value: The raw value (DataPath, Vector, float, dict, etc.)
        group: The property group

    Returns:
        A Property object, or None if value is None
    """
    if value is None:
        return None

    # If it's already a DataPath, wrap it directly
    if isinstance(value, DataPath):
        return Property(value=value, group=group)

    # Check if it's a Vector object
    if _is_vector_like(value):
        return Property(value=PrimitiveData(paths={".": PropertyPathValue.from_python(value)}), group=group)

    # Check if it's a Rotation-like object (has angle and axis)
    if _is_rotation_like(value):
        return Property(value=PrimitiveData(paths={".": PropertyPathValue.from_python(value)}), group=group)

    # Check if it's a Placement object
    if _is_placement_like(value):
        return Property(value=PrimitiveData(paths={".": PropertyPathValue.from_python(value)}), group=group)

    # Check if it's a list or tuple
    if isinstance(value, (list, tuple)):
        items = [PrimitiveData(paths={".": PropertyPathValue.from_python(v)}) for v in value]
        return Property(value=ListData(paths={}, items=cast(list, items)), group=group)

    # Check if it's a dict
    if isinstance(value, dict):
        return Property(value=PrimitiveData(paths={".": PropertyPathValue.from_python(value)}), group=group)

    # For primitives, wrap in PrimitiveData
    return Property(value=PrimitiveData(paths={".": PropertyPathValue.from_python(value)}), group=group)


def _compute_property_children(
    old_value: Property | None, new_value: Property | None, parent_prop_name: str = ""
) -> list[PropertyDiff]:
    """Compute child property diffs for expandable properties.

    Handles:
    - ListData: each item becomes a child (indexed by position)
    - VectorData: x, y, z become children
    - RotationData: Angle, Axis.x, Axis.y, Axis.z become children
    - PlacementData: Base.x/y/z and Rotation.* become children, grouped as Position/Rotation

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        parent_prop_name: The parent property name for logging purposes

    Returns:
        List of PropertyDiff for child properties
    """
    children: list[PropertyDiff] = []

    old_children: dict[str, Any] = _extract_data_path_children(old_value)
    new_children: dict[str, Any] = _extract_data_path_children(new_value)

    all_child_names = set(old_children.keys()) | set(new_children.keys())

    for child_name in sorted(all_child_names):
        raw_old_child = old_children.get(child_name)
        raw_new_child = new_children.get(child_name)

        # Wrap raw values in Property objects
        old_child_prop = _create_property_from_child_value(raw_old_child) if raw_old_child is not None else None
        new_child_prop = _create_property_from_child_value(raw_new_child) if raw_new_child is not None else None

        # For child properties, prepend parent name to create a full path for logging
        full_prop_name = f"{parent_prop_name}[{child_name}]" if parent_prop_name else child_name

        child_diff = PropertyDiff(
            property_name=child_name,
            old_value=old_child_prop,
            new_value=new_child_prop,
            _parent_prop_name=full_prop_name,
        )

        children.append(child_diff)

    return children


def _extract_data_path_children(prop: Property | None) -> dict[str, Any]:
    """Extract child values from a DataPath for child diff computation.

    Args:
        prop: A Property object or None

    Returns:
        Dict mapping child name to child value
    """
    if prop is None:
        return {}

    dp = prop.value

    # Dispatch to type-specific handler
    if isinstance(dp, ListData):
        return _children_list(dp)
    if isinstance(dp, VectorData):
        return _children_vector(dp)
    if isinstance(dp, RotationData):
        return _children_rotation(dp)
    if isinstance(dp, PlacementData):
        return _children_placement(dp)

    return {}


def _children_list(dp: ListData) -> dict[str, Any]:
    """Extract children from ListData as indexed items."""
    return {str(i): item for i, item in enumerate(dp.items)}


def _children_vector(dp: VectorData) -> dict[str, Any]:
    """Extract children from VectorData (x, y, z)."""
    return {k: v.value for k, v in dp.paths.items() if k != "."}


def _children_rotation(dp: RotationData) -> dict[str, Any]:
    """Extract children from RotationData (Angle, Axis.x/y/z)."""
    result: dict[str, Any] = {}
    for k, v in dp.paths.items():
        if k == "." or k == "Axis":
            continue
        result[k] = v.value
    return result


def _children_placement(dp: PlacementData) -> dict[str, Any]:
    """Extract children from PlacementData grouped as Position/Rotation."""
    position: dict[str, Any] = {}
    rotation: dict[str, Any] = {}
    for k, v in dp.paths.items():
        if k in (".", "Rotation", "Rotation.Axis"):
            continue
        if k.startswith("Base."):
            position[k.replace("Base.", "")] = v.value
        elif k.startswith("Rotation."):
            rotation[k.replace("Rotation.", "")] = v.value
        else:
            position[k] = v.value

    result: dict[str, Any] = {}
    if position:
        result["Position"] = position
    if rotation:
        result["Rotation"] = rotation
    return result


def _property_value_str(prop: Property | None) -> str:
    """Extract a string representation of a property's value.

    Args:
        prop: A Property object or None

    Returns:
        A string representation of the property value
    """
    if prop is None:
        return "None"
    dp = prop.value
    if isinstance(dp, PrimitiveData):
        pv = dp.paths.get(".")
        if pv is not None:
            return str(pv.value) if pv.value is not None else "None"
    # For complex types, use the internal type as identifier
    return dp.INTERNAL_TYPE.value


def _has_expression_change(old_value: Property | None, new_value: Property | None) -> bool:
    """Check if there's an expression change between two property values.

    With the DataPath-based model, expression tracking is embedded in the
    PropertyPathValue objects within the DataPath structure.
    """
    if old_value is None or new_value is None:
        return True

    old_pv = _get_data_path_value(old_value.value)
    new_pv = _get_data_path_value(new_value.value)

    if old_pv is None or new_pv is None:
        return False

    return old_pv.expression != new_pv.expression


def _are_properties_modified(property_diffs: list[PropertyDiff], children: list[NodeDiff]) -> bool:
    """Check if any properties or children have modifications.

    A node's properties are considered modified if:
    - Any child node has state != DiffState.UNCHANGED
    - Any property has state != DiffState.UNCHANGED (includes ADDED, DELETED, MODIFIED)
    - Any property has children with state != DiffState.UNCHANGED (e.g., constraint items)
    - Any property has an expression change (even if value is unchanged)

    Args:
        property_diffs: List of property diffs for this node
        children: List of child node diffs

    Returns:
        True if any properties or children are modified, False otherwise
    """
    # Check child node states - if any child node has changes, properties are modified
    if any(child.state != DiffState.UNCHANGED for child in children):
        return True

    # Check if any property has changed (ADDED, DELETED, or MODIFIED)
    if any(prop_diff.state != DiffState.UNCHANGED for prop_diff in property_diffs):
        return True

    # Check if any property has children with changes (e.g., individual constraint items)
    for prop_diff in property_diffs:
        if prop_diff.children and any(child.state != DiffState.UNCHANGED for child in prop_diff.children):
            return True

    # Check if any property has expression changes (value may be unchanged but expression changed)
    return any(_has_expression_change(prop_diff.old_value, prop_diff.new_value) for prop_diff in property_diffs)


@dataclass(frozen=True)
class PropertyDiff:
    """The difference between two property values.

    The state is automatically calculated based on the old and new values
    (including their expressions). This ensures consistency and prevents
    invalid states where the state doesn't match the actual values.

    Attributes:
        property_name: Name of the property
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        state: The diff state (ADDED, DELETED, MODIFIED, UNCHANGED) - auto-calculated
        children: List of child property diffs for expandable properties
        _parent_prop_name: Internal field for full property path (e.g., "Constraints[0]")
    """

    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    children: list[PropertyDiff] = field(default_factory=list)
    _parent_prop_name: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state and children based on old and new values."""
        # Use object.__setattr__ since the dataclass is frozen
        # Use _parent_prop_name if set (for child properties), otherwise use property_name
        full_prop_name = self._parent_prop_name or self.property_name
        object.__setattr__(
            self, "state", _calculate_property_diff_state(self.old_value, self.new_value, full_prop_name)
        )
        # Compute children for expandable properties (pass property_name as parent)
        object.__setattr__(
            self, "children", _compute_property_children(self.old_value, self.new_value, self.property_name)
        )

    def __str__(self) -> str:
        old_str = _property_value_str(self.old_value)
        new_str = _property_value_str(self.new_value)
        if self.state == DiffState.ADDED:
            return f"{self.property_name}: +{new_str}"
        elif self.state == DiffState.DELETED:
            return f"{self.property_name}: -{old_str}"
        elif self.state == DiffState.MODIFIED:
            return f"{self.property_name}: {old_str} -> {new_str}"
        return f"{self.property_name}: {old_str}"


@dataclass(frozen=True)
class NodeDiff:
    """The difference between two tree nodes.

    Represents the diff result for a single node in the document tree,
    including its properties and children.

    The state is automatically calculated based on property diffs and children:
    - If `_force_state` is set (by factory functions), that state is used
    - Otherwise, state is MODIFIED if any property/child has changes, UNCHANGED otherwise

    This separates node-level changes (entire node added/deleted) from
    property-level changes (properties modified/added/deleted).

    Attributes:
        path: The path to this node (for backward compatibility, same as new_path)
        type_id: The TypeID of the node
        state: The overall state of this node - auto-calculated or forced
        property_diffs: List of property-level differences
        children: List of child node diffs
        old_path: Path in old snapshot (None for added nodes). Used for move detection.
        new_path: Path in new snapshot (None for deleted nodes). Used for move detection.
        old_after: The 'after' field in old snapshot (None for added/root nodes).
            Used for reorder detection.
        new_after: The 'after' field in new snapshot (None for deleted/root nodes).
            Used for reorder detection.
        _force_state: Internal override for state calculation. Only used by
            factory functions (`create_added_node_diff`, `create_deleted_node_diff`)
            to indicate node-level changes (ADDED/DELETED). When None, state is
            calculated from property_diffs (MODIFIED/UNCHANGED). Not included in
            repr or comparison.
    """

    path: str
    type_id: str
    state: DiffState = field(init=False)
    property_diffs: list[PropertyDiff] = field(default_factory=list)
    children: list[NodeDiff] = field(default_factory=list)
    old_path: str | None = field(default=None)
    new_path: str | None = field(default=None)
    old_after: str | None = field(default=None)
    new_after: str | None = field(default=None)
    _force_state: DiffState | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state based on _force_state or property diffs.

        State calculation logic:
        1. If _force_state is set (node-level change), use that state
        2. Otherwise, check if any properties/children are modified
        3. Return MODIFIED if changes exist, UNCHANGED otherwise
        """
        # Use object.__setattr__ since the dataclass is frozen
        if self._force_state is not None:
            object.__setattr__(self, "state", self._force_state)
        elif _are_properties_modified(self.property_diffs, self.children):
            object.__setattr__(self, "state", DiffState.MODIFIED)
        else:
            object.__setattr__(self, "state", DiffState.UNCHANGED)

    def __str__(self) -> str:
        state_str = self.state.name
        prop_count = len(self.property_diffs)
        child_count = len(self.children)
        return f"NodeDiff({self.path}, {state_str}, {prop_count} props, {child_count} children)"

    @property
    def has_changes(self) -> bool:
        """Check if this node or any children have changes."""
        if self.state != DiffState.UNCHANGED:
            return True
        # Check if any property diff has changes (not just if property_diffs exists)
        if any(p.state != DiffState.UNCHANGED for p in self.property_diffs):
            return True
        return any(child.has_changes for child in self.children)

    @property
    def changed_properties(self) -> list[PropertyDiff]:
        """Get only the properties that actually changed."""
        return [p for p in self.property_diffs if p.state != DiffState.UNCHANGED]


@dataclass(frozen=True)
class DiffResult:
    """The complete result of comparing two snapshots.

    Represents all differences between an old and new snapshot, organized
    as a tree structure that mirrors the original document hierarchy.

    Attributes:
        old_snapshot: The old snapshot being compared
        new_snapshot: The new snapshot being compared
        warnings: List of warning messages for edge cases
        added_count: Number of added nodes
        deleted_count: Number of deleted nodes
        modified_count: Number of modified nodes
        hierarchy: The DiffHierarchy containing the node diffs in tree form
    """

    old_snapshot: Snapshot
    new_snapshot: Snapshot
    warnings: list[str] = field(default_factory=list)
    added_count: int = 0
    deleted_count: int = 0
    modified_count: int = 0
    hierarchy: DiffHierarchy = field(default_factory=lambda: DiffHierarchy())

    def __str__(self) -> str:
        return (
            f"DiffResult({self.old_snapshot.document_name} vs {self.new_snapshot.document_name}): "
            f"{self.added_count} added, {self.deleted_count} deleted, {self.modified_count} modified"
        )

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes in this diff."""
        return (self.added_count > 0 or self.deleted_count > 0 or self.modified_count > 0) or any(
            node.has_changes for node in self.hierarchy.roots
        )

    def get_all_changed_paths(self) -> list[str]:
        """Get all paths that have changes (for UI highlighting)."""
        changed_paths: list[str] = []
        for node_diff in self.hierarchy.roots:
            self._collect_changed_paths(node_diff, changed_paths)
        return changed_paths

    def _collect_changed_paths(self, node: NodeDiff, result: list[str]) -> None:
        """Recursively collect paths with changes."""
        if node.has_changes:
            result.append(node.path)
        for child in node.children:
            self._collect_changed_paths(child, result)


class DiffHierarchy:
    """Holds hierarchical node diffs as a tree structure.

    This class manages the hierarchical organization of NodeDiff objects,
    providing efficient path-based lookups and parent-child relationships.

    Attributes:
        _hierarchy: Nested dict mapping path segments to NodeDiff objects
        _roots: List of top-level NodeDiff objects
    """

    def __init__(self) -> None:
        """Initialize an empty hierarchy."""
        self._hierarchy: dict[str, Any] = {}
        self._roots: list[NodeDiff] = []

    @property
    def roots(self) -> list[NodeDiff]:
        """Get list of top-level NodeDiff objects."""
        return self._roots

    def find_by_path(self, path: str) -> NodeDiff | None:
        """Find a NodeDiff by its path.

        Args:
            path: The path to search for (e.g., "Body/Pad")

        Returns:
            The NodeDiff at the given path, or None if not found
        """
        if not path:
            return None

        # Split path into segments
        segments = path.split("/")

        # Traverse the hierarchy
        current: dict[str, Any] | None = self._hierarchy
        for i, segment in enumerate(segments):
            if not segment:
                continue
            if isinstance(current, dict) and segment in current:
                value = current[segment]

                if i == len(segments) - 1:
                    # This is the final segment, return the NodeDiff
                    if isinstance(value, NodeDiff):
                        return value
                    elif isinstance(value, dict):
                        # Might have __node__ key
                        return value.get("__node__")
                    return None

                # Move to children
                if isinstance(value, dict):
                    current = value.get("__children__")
                else:
                    # It's a NodeDiff, its children are in NodeDiff.children
                    return None
            else:
                return None
        return None

    def add_node(self, node_diff: NodeDiff) -> None:
        """Add a NodeDiff to the hierarchy.

        Handles parent linking automatically - if the parent exists in the
        hierarchy, the node is added as a child. If no parent exists,
        the node is added to roots.

        Args:
            node_diff: The NodeDiff to add
        """
        path = node_diff.path
        if not path:
            return

        segments = path.split("/")

        if len(segments) == 1:
            # Root level node
            self._roots.append(node_diff)
            self._hierarchy[segments[0]] = node_diff
            return

        # Find or create parent path
        parent_segments = segments[:-1]
        parent_path = "/".join(parent_segments)

        # Try to find parent in hierarchy
        parent_node = self.find_by_path(parent_path)

        if parent_node is not None:
            # Add as child to existing parent, but only if not already present
            # (to avoid infinite loops when node_diffs already has children set)
            if node_diff not in parent_node.children:
                parent_node.children.append(node_diff)
        else:
            # No parent found, add to roots
            self._roots.append(node_diff)

        # Store in hierarchy dict
        self._ensure_parent_segments(path, segments, parent_node)
        self._store_node_in_hierarchy(segments, node_diff)

    def _ensure_parent_segments(self, path: str, segments: list[str], parent_node: NodeDiff | None) -> None:
        """Ensure parent segment dict containers exist in hierarchy.

        Args:
            path: Full path of the node being added
            segments: Path segments
            parent_node: Parent NodeDiff if found, None otherwise
        """
        current = self._hierarchy
        for segment in segments[:-1]:  # Process all but last segment
            if segment not in current:
                # Only raise error if parent NodeDiff was supposed to exist
                if parent_node is not None:
                    raise ValueError(
                        f"Parent segment '{segment}' not found in hierarchy for path '{path}'. "
                        f"Parent paths must be created before adding child nodes."
                    )
                # Create dict container for orphaned child (no parent NodeDiff)
                current[segment] = {"__children__": {}}
            elif isinstance(current[segment], NodeDiff):
                existing_node = current[segment]
                current[segment] = {"__children__": {}, "__node__": existing_node}

            # Move to children dict
            if isinstance(current[segment], dict):
                current = current[segment].get("__children__", {})
            else:
                break

    def _store_node_in_hierarchy(self, segments: list[str], node_diff: NodeDiff) -> None:
        """Store the final node in the hierarchy dict.

        Args:
            segments: Path segments
            node_diff: The node to store
        """
        current = self._hierarchy
        # Navigate to parent dict
        for segment in segments[:-1]:
            if isinstance(current.get(segment), dict):
                current = current[segment].get("__children__", {})
            else:
                break

        # Store the final node
        final_segment = segments[-1]
        if final_segment not in current:
            current[final_segment] = node_diff


__all__ = [
    "DiffResult",
    "DiffHierarchy",
    "NodeDiff",
    "PropertyDiff",
    "DiffState",
    "WARNING_OLD_SNAPSHOT_MISSING",
]
