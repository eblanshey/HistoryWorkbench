# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the tree-comparison algorithm with path-based indexing.
"""Unit tests for tree_diff module.

These tests verify the core diff computation logic without any FreeCAD dependencies.
"""

from datetime import datetime

from freecad.diff_wb.config import EXCLUDED_PROPERTIES
from freecad.diff_wb.domain.diff.comparator import PropertyComparator, TreeComparator
from freecad.diff_wb.domain.diff.models import DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree.node import TreeNode
from freecad.diff_wb.domain.tree.property import Property


# Test fixtures - create comparator instances
_tree_comparator = TreeComparator()
_property_comparator = PropertyComparator()


def compare_properties(
    old_props: dict[str, Property],
    new_props: dict[str, Property],
) -> list[PropertyDiff]:
    """Wrapper with default excluded_properties."""
    return _property_comparator.compare_properties(old_props, new_props, EXCLUDED_PROPERTIES)


should_exclude_property = _property_comparator._should_exclude_property
values_are_equal = _property_comparator._values_are_equal


class TestGetParentPath:
    """Tests for _get_parent_path method."""

    def test_parent_with_leading_slash(self) -> None:
        """Test extracting parent from path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad")
        assert result == "/Body"

    def test_parent_without_leading_slash(self) -> None:
        """Test extracting parent from path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad")
        assert result == "Body"

    def test_root_with_leading_slash_returns_empty(self) -> None:
        """Test that root node with leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("/Part")
        assert result == ""

    def test_root_without_leading_slash_returns_empty(self) -> None:
        """Test that root node without leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("Part")
        assert result == ""

    def test_deep_nesting_with_leading_slash(self) -> None:
        """Test extracting parent from deeply nested path with leading slash."""
        result = _tree_comparator._get_parent_path("/A/B/C/D")
        assert result == "/A/B/C"

    def test_deep_nesting_without_leading_slash(self) -> None:
        """Test extracting parent from deeply nested path without leading slash."""
        result = _tree_comparator._get_parent_path("A/B/C/D")
        assert result == "A/B/C"

    def test_two_level_path_with_leading_slash(self) -> None:
        """Test extracting parent from two-level path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad/Sketch")
        assert result == "/Body/Pad"

    def test_two_level_path_without_leading_slash(self) -> None:
        """Test extracting parent from two-level path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad/Sketch")
        assert result == "Body/Pad"


class TestValuesAreEqual:
    """Tests for values_are_equal function."""

    def test_both_none(self) -> None:
        """Test that None vs None returns True."""
        assert values_are_equal(None, None) is True

    def test_old_none_new_value(self) -> None:
        """Test that None vs value returns False."""
        new_val = Property.from_freecad("test", {}, "Base")
        assert values_are_equal(None, new_val) is False

    def test_old_value_new_none(self) -> None:
        """Test that value vs None returns False."""
        old_val = Property.from_freecad("test", {}, "Base")
        assert values_are_equal(old_val, None) is False

    def test_identical_bool_values(self) -> None:
        """Test BOOL type with same values."""
        old_val = Property.from_freecad(True, {}, "Base")
        new_val = Property.from_freecad(True, {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_bool_values(self) -> None:
        """Test BOOL type with different values."""
        old_val = Property.from_freecad(True, {}, "Base")
        new_val = Property.from_freecad(False, {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_int_values(self) -> None:
        """Test INT type with same values."""
        old_val = Property.from_freecad(42, {}, "Base")
        new_val = Property.from_freecad(42, {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_int_values(self) -> None:
        """Test INT type with different values."""
        old_val = Property.from_freecad(42, {}, "Base")
        new_val = Property.from_freecad(43, {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_float_values(self) -> None:
        """Test FLOAT type with same values."""
        old_val = Property.from_freecad(3.14, {}, "Base")
        new_val = Property.from_freecad(3.14, {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_float_values(self) -> None:
        """Test FLOAT type with different values."""
        old_val = Property.from_freecad(3.14, {}, "Base")
        new_val = Property.from_freecad(2.71, {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_float_within_tolerance(self) -> None:
        """Test FLOAT type with values within tolerance (1e-9)."""
        old_val = Property.from_freecad(1.0, {}, "Base")
        new_val = Property.from_freecad(1.0 + 1e-10, {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_float_exceeds_tolerance(self) -> None:
        """Test FLOAT type with values exceeding tolerance (1e-9)."""
        old_val = Property.from_freecad(1.0, {}, "Base")
        new_val = Property.from_freecad(1.0 + 1e-8, {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_string_values(self) -> None:
        """Test STRING type with same values."""
        old_val = Property.from_freecad("hello", {}, "Base")
        new_val = Property.from_freecad("hello", {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_string_values(self) -> None:
        """Test STRING type with different values."""
        old_val = Property.from_freecad("hello", {}, "Base")
        new_val = Property.from_freecad("world", {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_vector_values(self) -> None:
        """Test VECTOR type with same values."""
        old_val = Property.from_freecad((1.0, 2.0, 3.0), {}, "Base")
        new_val = Property.from_freecad((1.0, 2.0, 3.0), {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_vector_values(self) -> None:
        """Test VECTOR type with different values."""
        old_val = Property.from_freecad((1.0, 2.0, 3.0), {}, "Base")
        new_val = Property.from_freecad((4.0, 5.0, 6.0), {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_vector_within_tolerance(self) -> None:
        """Test VECTOR type with components within tolerance."""
        old_val = Property.from_freecad((1.0, 2.0, 3.0), {}, "Base")
        new_val = Property.from_freecad((1.0 + 1e-10, 2.0, 3.0), {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_identical_placement_values(self) -> None:
        """Test PLACEMENT type with same values."""
        old_val = Property.from_freecad({"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base")
        new_val = Property.from_freecad({"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_placement_values(self) -> None:
        """Test PLACEMENT type with different values."""
        old_val = Property.from_freecad({"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base")
        new_val = Property.from_freecad({"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_expression_values(self) -> None:
        """Test STRING type with same values and identical expressions."""
        old_val = Property.from_freecad("Body.Length", {".": "Body.Length"}, "Base")
        new_val = Property.from_freecad("Body.Length", {".": "Body.Length"}, "Base")
        assert values_are_equal(old_val, new_val) is True

    def test_different_expression_values(self) -> None:
        """Test STRING type with different values and different expressions."""
        old_val = Property.from_freecad("Body.Length", {".": "Body.Length"}, "Base")
        new_val = Property.from_freecad("Cube.Size", {".": "Cube.Size"}, "Base")
        assert values_are_equal(old_val, new_val) is False

    def test_same_value_different_expression(self) -> None:
        """Test that same value with different expression returns False."""
        old_val = Property.from_freecad(10.0, {".": "Body.Length"}, "Base")
        new_val = Property.from_freecad(10.0, {".": "Cube.Size"}, "Base")
        assert values_are_equal(old_val, new_val) is False


class TestPropertyDiffState:
    """Tests for PropertyDiff state calculation."""

    def test_state_added(self) -> None:
        """Test ADDED state when old_value is None."""
        prop_diff = PropertyDiff(
            property_name="NewProperty",
            old_value=None,
            new_value=Property.from_freecad("value", {}, "Base"),
        )
        assert prop_diff.state == DiffState.ADDED

    def test_state_deleted(self) -> None:
        """Test DELETED state when new_value is None."""
        prop_diff = PropertyDiff(
            property_name="OldProperty",
            old_value=Property.from_freecad("value", {}, "Base"),
            new_value=None,
        )
        assert prop_diff.state == DiffState.DELETED

    def test_state_modified(self) -> None:
        """Test MODIFIED state when values differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(20.0, {}, "Base"),
        )
        assert prop_diff.state == DiffState.MODIFIED

    def test_state_unchanged(self) -> None:
        """Test UNCHANGED state when values are equal."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(10.0, {}, "Base"),
        )
        assert prop_diff.state == DiffState.UNCHANGED

    def test_state_unchanged_same_value_different_expression(self) -> None:
        """Test UNCHANGED state when values are same (expression tracked separately)."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {".": "Body.Length"}, "Base"),
            new_value=Property.from_freecad(10.0, {".": "Cube.Size"}, "Base"),
        )
        assert prop_diff.state == DiffState.UNCHANGED


class TestCompareProperties:
    """Tests for compare_properties function."""

    def test_empty_dictionaries(self) -> None:
        """Test comparing empty property dictionaries."""
        result = compare_properties({}, {})
        assert result == []

    def test_only_additions(self) -> None:
        """Test when all properties are new (added)."""
        old_props = {}
        new_props = {
            "NewProp1": Property.from_freecad("value1", {}, "Base"),
            "NewProp2": Property.from_freecad(42, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.ADDED

    def test_only_deletions(self) -> None:
        """Test when all properties are removed (deleted)."""
        old_props = {
            "OldProp1": Property.from_freecad("value1", {}, "Base"),
            "OldProp2": Property.from_freecad(42, {}, "Base"),
        }
        new_props = {}
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.DELETED

    def test_only_modifications(self) -> None:
        """Test when all properties are modified."""
        old_props = {
            "Prop1": Property.from_freecad(10.0, {}, "Base"),
            "Prop2": Property.from_freecad("old", {}, "Base"),
        }
        new_props = {
            "Prop1": Property.from_freecad(20.0, {}, "Base"),
            "Prop2": Property.from_freecad("new", {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_only_unchanged_included(self) -> None:
        """Test that unchanged properties are included in result."""
        old_props = {
            "Prop1": Property.from_freecad(10.0, {}, "Base"),
            "Prop2": Property.from_freecad("same", {}, "Base"),
        }
        new_props = {
            "Prop1": Property.from_freecad(10.0, {}, "Base"),
            "Prop2": Property.from_freecad("same", {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.UNCHANGED

    def test_mixed_changes(self) -> None:
        """Test combination of added, deleted, modified and unchanged properties."""
        old_props = {
            "DeletedProp": Property.from_freecad("gone", {}, "Base"),
            "ModifiedProp": Property.from_freecad(10.0, {}, "Base"),
            "UnchangedProp": Property.from_freecad(5, {}, "Base"),
        }
        new_props = {
            "AddedProp": Property.from_freecad("new", {}, "Base"),
            "ModifiedProp": Property.from_freecad(20.0, {}, "Base"),
            "UnchangedProp": Property.from_freecad(5, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 4

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED
        assert states["UnchangedProp"] == DiffState.UNCHANGED

    def test_excludes_time_stamp(self) -> None:
        """Test that TimeStamp property is filtered out."""
        old_props = {
            "TimeStamp": Property.from_freecad("2024-01-01T00:00:00", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "TimeStamp": Property.from_freecad("2024-01-01T00:00:01", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        # TimeStamp is excluded, Length is unchanged but included
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert result[0].state == DiffState.UNCHANGED

    def test_excludes_label2(self) -> None:
        """Test that Label2 property is filtered out."""
        old_props = {
            "Label2": Property.from_freecad("AutoLabel", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "Label2": Property.from_freecad("NewLabel", {}, "Base"),
            "Length": Property.from_freecad(20.0, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Label2" for p in result)

    def test_all_property_types(self) -> None:
        """Test comparison of all property types in a single call."""
        old_props = {
            "BoolProp": Property.from_freecad(True, {}, "Base"),
            "IntProp": Property.from_freecad(42, {}, "Base"),
            "FloatProp": Property.from_freecad(3.14, {}, "Base"),
            "StringProp": Property.from_freecad("hello", {}, "Base"),
            "VectorProp": Property.from_freecad((1.0, 2.0, 3.0), {}, "Base"),
            "PlacementProp": Property.from_freecad(
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }
        new_props = {
            "BoolProp": Property.from_freecad(False, {}, "Base"),  # Changed
            "IntProp": Property.from_freecad(42, {}, "Base"),  # Same
            "FloatProp": Property.from_freecad(2.71, {}, "Base"),  # Changed
            "StringProp": Property.from_freecad("world", {}, "Base"),  # Changed
            "VectorProp": Property.from_freecad((4.0, 5.0, 6.0), {}, "Base"),  # Changed
            "PlacementProp": Property.from_freecad(
                {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),  # Changed
        }
        result = compare_properties(old_props, new_props)

        assert len(result) == 6  # All properties including unchanged IntProp

        prop_names = {p.property_name for p in result}
        assert prop_names == {"BoolProp", "IntProp", "FloatProp", "StringProp", "VectorProp", "PlacementProp"}

        # Verify modified are MODIFIED
        modified_props = [p for p in result if p.property_name != "IntProp"]
        for prop_diff in modified_props:
            assert prop_diff.state == DiffState.MODIFIED
        # Verify IntProp is unchanged
        assert next(p for p in result if p.property_name == "IntProp").state == DiffState.UNCHANGED

    def test_float_tolerance_edge_cases(self) -> None:
        """Test float tolerance with various edge cases."""
        # Very small difference within tolerance
        old_props = {
            "FloatProp": Property.from_freecad(1.0, {}, "Base"),
        }
        new_props = {
            "FloatProp": Property.from_freecad(1.0 + 1e-10, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1  # Within tolerance, so unchanged but included
        assert result[0].state == DiffState.UNCHANGED

        # Difference exceeding tolerance
        new_props_exceed = {
            "FloatProp": Property.from_freecad(1.0 + 1e-8, {}, "Base"),
        }
        result_exceed = compare_properties(old_props, new_props_exceed)
        assert len(result_exceed) == 1
        assert result_exceed[0].state == DiffState.MODIFIED

    def test_property_diff_string_representation(self) -> None:
        """Test string representation of PropertyDiff objects."""
        # ADDED
        added = PropertyDiff(
            property_name="NewProp",
            old_value=None,
            new_value=Property.from_freecad("value", {}, "Base"),
        )
        assert "+value" in str(added)

        # DELETED
        deleted = PropertyDiff(
            property_name="OldProp",
            old_value=Property.from_freecad("value", {}, "Base"),
            new_value=None,
        )
        assert "-value" in str(deleted)

        # MODIFIED
        modified = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(20.0, {}, "Base"),
        )
        assert "10.0" in str(modified)
        assert "20.0" in str(modified)
        assert "->" in str(modified)

    def test_same_value_different_expression_is_unchanged(self) -> None:
        """Test that same value with different expression returns UNCHANGED."""
        old_props = {
            "Length": Property.from_freecad(10.0, {".": "Body.Length"}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(10.0, {".": "Cube.Size"}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.UNCHANGED


class TestPropertyDiffChildrenAutoComputed:
    """Tests verifying PropertyDiff auto-computes children for expandable properties.

    These tests verify that when the comparator creates PropertyDiff objects,
    the children are automatically populated by PropertyDiff's __post_init__ method.
    This is Phase 3 of the refactor-diff-architecture task.
    """

    def test_list_property_diff_has_indexed_children(self) -> None:
        """Test that PropertyDiff for list has indexed children."""
        # Create two list properties that differ
        old_props = {
            "Vector": Property.from_freecad([1.0, 2.0, 3.0], {}, "Base"),
        }
        new_props = {
            "Vector": Property.from_freecad([10.0, 2.0, 3.0], {}, "Base"),
        }

        result = compare_properties(old_props, new_props)

        assert len(result) == 1
        prop_diff = result[0]
        assert prop_diff.property_name == "Vector"
        assert prop_diff.state == DiffState.MODIFIED

        # Verify children are auto-computed (indexed list items)
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"0", "1", "2"}

    def test_list_property_diff_first_child_has_correct_state(self) -> None:
        """Test that first child of list diff has MODIFIED state when value changes."""
        # Create two list properties with different first element
        old_props = {
            "Vector": Property.from_freecad([1.0, 2.0, 3.0], {}, "Base"),
        }
        new_props = {
            "Vector": Property.from_freecad([10.0, 2.0, 3.0], {}, "Base"),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find first child (index 0)
        first_child = next(child for child in prop_diff.children if child.property_name == "0")
        assert first_child.state == DiffState.MODIFIED

    def test_list_property_diff_second_child_has_unchanged_state(self) -> None:
        """Test that second child of list diff has UNCHANGED state when value is same."""
        # Create two list properties with same second element
        old_props = {
            "Vector": Property.from_freecad([1.0, 2.0, 3.0], {}, "Base"),
        }
        new_props = {
            "Vector": Property.from_freecad([1.0, 2.0, 30.0], {}, "Base"),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find second child (index 1) - should be UNCHANGED
        second_child = next(child for child in prop_diff.children if child.property_name == "1")
        assert second_child.state == DiffState.UNCHANGED

    def test_unchanged_placement_has_unchanged_children(self) -> None:
        """Test that unchanged Placement has UNCHANGED children."""
        # Create identical Placement properties
        old_props = {
            "Placement": Property.from_freecad(
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }
        new_props = {
            "Placement": Property.from_freecad(
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.UNCHANGED

        # Both children should be UNCHANGED
        for child in prop_diff.children:
            assert child.state == DiffState.UNCHANGED

    def test_primitive_property_has_empty_children(self) -> None:
        """Test that primitive property (e.g., FLOAT) has empty children list."""
        old_props = {
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(20.0, {}, "Base"),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # Primitive types have no children
        assert len(prop_diff.children) == 0

    def test_list_property_has_indexed_children(self) -> None:
        """Test that LIST property has indexed children."""
        old_props = {
            "Position": Property.from_freecad([1.0, 2.0, 3.0], {}, "Base"),
        }
        new_props = {
            "Position": Property.from_freecad([4.0, 5.0, 6.0], {}, "Base"),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # List has indexed children
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"0", "1", "2"}

    def test_added_placement_has_children(self) -> None:
        """Test that added Placement has Position and Rotation children with ADDED state."""
        old_props: dict[str, Property] = {}
        new_props = {
            "Placement": Property.from_freecad(
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.ADDED

        # Children should also have ADDED state
        for child in prop_diff.children:
            assert child.state == DiffState.ADDED

    def test_deleted_placement_has_children(self) -> None:
        """Test that deleted Placement has Position and Rotation children with DELETED state."""
        old_props = {
            "Placement": Property.from_freecad(
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }
        new_props: dict[str, Property] = {}

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.DELETED

        # Children should also have DELETED state
        for child in prop_diff.children:
            assert child.state == DiffState.DELETED


class TestCompareNodesById:
    """Tests for ID-based node comparison."""

    def test_identical_nodes_returns_unchanged(self) -> None:
        """Test comparing identical nodes returns UNCHANGED."""
        props = {
            "Label": Property.from_freecad("Body", {}, "Base"),
        }
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.UNCHANGED

    def test_modified_property_returns_modified(self) -> None:
        """Test detecting a modified property returns MODIFIED."""
        old_props = {
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(20.0, {}, "Base"),
        }
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=new_props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_includes_old_and_new_path_in_result(self) -> None:
        """Test that NodeDiff includes old_path and new_path."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_path and new_path for move detection
        assert result.old_path == "Body/Pad"
        assert result.new_path == "Body/Pad"

    def test_includes_old_and_new_after_in_result(self) -> None:
        """Test that NodeDiff includes old_after and new_after."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_after and new_after for reorder detection
        assert result.old_after == "Body"
        assert result.new_after == "Body"


class TestIdBasedCompareSnapshots:
    """Tests for ID-based snapshot comparison (end-to-end)."""

    def test_compare_two_flat_node_lists_by_id(self) -> None:
        """Test comparing two flat node lists by ID."""
        # Old snapshot has ID 1 only
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot has both ID 1 and ID 2
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # ID 2 should be added, ID 1 unchanged
        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_added_nodes(self) -> None:
        """Test detecting ADDED nodes (in new, not in old)."""
        # Old snapshot: only ID 1
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 and ID 2 (added)
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_deleted_nodes(self) -> None:
        """Test detecting DELETED nodes (in old, not in new)."""
        # Old snapshot: ID 1 and ID 2
        old_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node1, old_node2],
        )

        # New snapshot: only ID 1
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0

    def test_detect_modified_nodes(self) -> None:
        """Test detecting MODIFIED nodes (in both, properties differ)."""
        # Old snapshot: ID 1 with Length=10
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.from_freecad(10.0, {}, "Base")},
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 with Length=20 (modified)
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.from_freecad(20.0, {}, "Base")},
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 1

        # Find the node diff for ID 1 - it may be nested under parent placeholder
        # Look through the hierarchy for Body/Pad
        def find_node_diff(node_diffs: list[NodeDiff], path: str) -> NodeDiff | None:
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        pad_diff = find_node_diff(result.hierarchy.roots, "Body/Pad")
        assert pad_diff is not None
        assert pad_diff.state == DiffState.MODIFIED

    def test_id_based_comparison_produces_correct_sets(self) -> None:
        """Test ID-based comparison produces correct added/deleted/common sets."""
        # Old: IDs 1, 2, 3
        old_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after="Body"),
            TreeNode(
                id=3, name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Sketch", after="Pad"
            ),
        ]
        # New: IDs 1, 2, 4 (2 unchanged, 1 modified, 3 deleted, 4 added)
        new_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(  # ID 2 modified (different properties)
                id=2,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
                properties={"Length": Property.from_freecad(20.0, {}, "Base")},
            ),
            TreeNode(id=4, name="Box", type_id="Part::Box", label="Box", path="Box", after=None),  # Added
        ]

        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=old_nodes)
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=new_nodes)

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Correct counts: 1 added (ID 4), 1 deleted (ID 3), 1 modified (ID 2)
        assert result.added_count == 1
        assert result.deleted_count == 1
        assert result.modified_count == 1

    def test_node_diff_includes_path_and_after_for_move_detection(self) -> None:
        """Test NodeDiff includes old_path, new_path, old_after, new_after for future move/reorder detection."""
        # Old: ID 1 at path "Body/Original"
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Original",
            after="Body",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New: Same ID but moved to different path "Body/Moved"
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Moved",
            after="Body",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # The NodeDiff should include old_path and new_path for move detection
        # Since the node is unchanged in properties but path changed
        # The node may be nested under a parent placeholder
        def find_node_diff(node_diffs: list[NodeDiff], path: str) -> NodeDiff | None:
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        feature_diff = find_node_diff(result.hierarchy.roots, "Body/Moved")
        assert feature_diff is not None
        assert feature_diff.old_path == "Body/Original"
        assert feature_diff.new_path == "Body/Moved"

    def test_node_diff_for_added_node_has_null_old_path(self) -> None:
        """Test that added node has None for old_path."""
        # New only: ID 2
        new_node = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Old is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Added node should have old_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path is None
        assert box_diff.new_path == "Box"

    def test_node_diff_for_deleted_node_has_null_new_path(self) -> None:
        """Test that deleted node has None for new_path."""
        # Old only: ID 1
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Deleted node should have new_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path == "Box"
        assert box_diff.new_path is None

    def test_hierarchical_output_preserved(self) -> None:
        """Test that hierarchical NodeDiff.children is preserved for UI."""
        # Create a parent-child relationship in flat nodes
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Should have hierarchical structure: Body -> Pad
        assert len(result.hierarchy.roots) == 1  # Root: Body
        body_diff = result.hierarchy.roots[0]
        assert len(body_diff.children) == 1  # Child: Pad
        assert body_diff.children[0].path == "Body/Pad"


class TestExcludedTypesFiltering:
    """Tests for excluded_types filtering in compare_snapshots."""

    def test_excludes_nodes_with_excluded_type(self) -> None:
        """Test that nodes with excluded type_id are filtered out."""
        # Old snapshot with App::Origin (excluded type)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Pass App::Origin in excluded_types
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Origin node should be excluded
        assert len(result.hierarchy.roots) == 0
        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_excludes_children_of_excluded_type_parent(self) -> None:
        """Test that children of excluded type nodes are also filtered."""
        # Old snapshot with App::Origin and its child
        origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[origin, xy_plane],
        )

        # New snapshot with same nodes
        new_origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_origin, new_xy_plane],
        )

        # Pass App::Origin in excluded_types - should exclude both origin and its child
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Both nodes should be excluded
        assert len(result.hierarchy.roots) == 0

    def test_includes_nodes_not_in_excluded_types(self) -> None:
        """Test that nodes not in excluded_types are included."""
        # Old snapshot with Part::Feature
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Pass App::Origin in excluded_types (but our node is Part::Feature)
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Box node should be included
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Box"

    def test_excludes_added_nodes_with_excluded_type(self) -> None:
        """Test that added nodes with excluded type are filtered."""
        # Old snapshot is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        # New snapshot with App::Origin (newly added)
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0

    def test_excludes_deleted_nodes_with_excluded_type(self) -> None:
        """Test that deleted nodes with excluded type are filtered."""
        # Old snapshot with App::Origin (deleted)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0


class TestExcludedParentPathFiltering:
    """Tests for excluded parent path filtering in compare_snapshots."""

    def test_excludes_child_when_parent_excluded_by_type(self) -> None:
        """Test that child nodes are excluded when parent type is excluded."""
        # Old: Body -> Pad -> Sketch (Sketch will be excluded because parent Pad type is excluded)
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body, pad, sketch],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_body, new_pad, new_sketch],
        )

        # Exclude PartDesign::Pad (parent of Sketch)
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["PartDesign::Pad"])

        # Body should be included (not excluded type), but Pad and Sketch should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Body/Pad/Sketch" not in paths_in_result

    def test_mixed_excluded_and_included_nodes(self) -> None:
        """Test that some nodes are excluded while others are included."""
        # Create nodes: Body with two children - one excluded, one included
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        # This Pad will be excluded
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        # This box will NOT be excluded (different parent)
        box = TreeNode(
            id=3,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body, pad, box],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_box = TreeNode(
            id=3,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_body, new_pad, new_box],
        )

        # Exclude PartDesign::Pad only
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["PartDesign::Pad"])

        # Body and Box should be included, Pad should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Box" in paths_in_result


class TestEmptySnapshots:
    """Tests for handling empty snapshots in compare_snapshots."""

    def test_both_snapshots_empty_returns_empty(self) -> None:
        """Test that comparing two empty snapshots returns empty result."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert result.hierarchy.roots == []

    def test_old_empty_new_with_nodes_returns_added(self) -> None:
        """Test that when old is empty, new nodes are marked as added."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        new_box = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_box],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.ADDED

    def test_new_empty_old_with_nodes_returns_deleted(self) -> None:
        """Test that when new is empty, old nodes are marked as deleted."""
        old_box = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_box],
        )

        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.DELETED

    def test_hierarchy_preserved_with_empty_parent(self) -> None:
        """Test that hierarchy is preserved when parent becomes empty."""
        # Old: Body with child Pad
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body],
        )

        # New: empty (Body deleted)
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.deleted_count == 1
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Body"
        assert result.hierarchy.roots[0].state == DiffState.DELETED


def _flatten_diffs(node_diffs: list[NodeDiff]) -> list[NodeDiff]:
    """Flatten a hierarchical list of NodeDiffs into a flat list."""
    result: list[NodeDiff] = []
    for diff in node_diffs:
        result.append(diff)
        if diff.children:
            result.extend(_flatten_diffs(diff.children))
    return result
