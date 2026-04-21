# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the domain diff models module.
"""Unit tests for domain diff models."""

from freecad.diff_wb.domain.diff.models import WARNING_OLD_SNAPSHOT_MISSING, DiffState, PropertyDiff
from freecad.diff_wb.domain.tree import Property


class TestPropertyDiffChildren:
    """Tests for PropertyDiff children computation."""

    def test_property_diff_computes_children(self) -> None:
        """PropertyDiff has children after creation for expandable properties."""
        # Create a Vector property which has x, y, z children
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_vector = Property.from_freecad([4.0, 5.0, 6.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Should have 3 children (indexed list items)
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"0", "1", "2"}

    def test_property_diff_no_children_for_primitives(self) -> None:
        """Primitive properties have empty children."""
        old_value = Property.from_freecad(10.0, {}, "Base")
        new_value = Property.from_freecad(20.0, {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []

    def test_property_diff_no_children_for_string(self) -> None:
        """String properties have empty children."""
        old_value = Property.from_freecad("hello", {}, "Base")
        new_value = Property.from_freecad("world", {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Label",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []

    def test_property_diff_children_states_unchanged(self) -> None:
        """Children have correct UNCHANGED state when values are equal."""
        old_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )
        new_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        # Parent should be UNCHANGED
        assert prop_diff.state == DiffState.UNCHANGED

        # All children should also be UNCHANGED
        for child in prop_diff.children:
            assert child.state == DiffState.UNCHANGED

    def test_property_diff_children_states_modified(self) -> None:
        """Children have correct MODIFIED state when values differ."""
        # Use a list property which has indexed children
        old_list = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_list = Property.from_freecad([10.0, 2.0, 3.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_list,
            new_value=new_list,
        )

        # Parent should be MODIFIED
        assert prop_diff.state == DiffState.MODIFIED

        # First item (index 0) should be MODIFIED (1.0 -> 10.0)
        first_child = next(c for c in prop_diff.children if c.property_name == "0")
        assert first_child.state == DiffState.MODIFIED

        # Second item (index 1) should be UNCHANGED (2.0 -> 2.0)
        second_child = next(c for c in prop_diff.children if c.property_name == "1")
        assert second_child.state == DiffState.UNCHANGED

    def test_property_diff_children_added(self) -> None:
        """Children have ADDED state when property is new."""
        new_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=None,
            new_value=new_placement,
        )

        # Parent should be ADDED
        assert prop_diff.state == DiffState.ADDED

        # Children should also be ADDED
        for child in prop_diff.children:
            assert child.state == DiffState.ADDED

    def test_property_diff_children_deleted(self) -> None:
        """Children have DELETED state when property is removed."""
        old_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=None,
        )

        # Parent should be DELETED
        assert prop_diff.state == DiffState.DELETED

        # Children should also be DELETED
        for child in prop_diff.children:
            assert child.state == DiffState.DELETED

    def test_property_diff_vector_children(self) -> None:
        """List/tuple properties have indexed children."""
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_vector = Property.from_freecad([4.0, 5.0, 6.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Position",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Should have 3 children (indexed list items)
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"0", "1", "2"}

        # All should be MODIFIED since values differ
        for child in prop_diff.children:
            assert child.state == DiffState.MODIFIED

    def test_property_diff_both_none(self) -> None:
        """PropertyDiff handles None for both old and new values."""
        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=None,
            new_value=None,
        )

        # Both None - since old is None, it defaults to ADDED state
        # (this is consistent with the current behavior)
        assert prop_diff.state == DiffState.ADDED
        assert prop_diff.children == []

    def test_property_diff_children_empty_both_sides(self) -> None:
        """PropertyDiff handles both sides having no children."""
        old_value = Property.from_freecad("hello", {}, "Base")
        new_value = Property.from_freecad("world", {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Label",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.children == []
        assert prop_diff.state == DiffState.MODIFIED


class TestWarningConstants:
    """Tests for warning constants in diff models."""

    def test_warning_old_snapshot_missing_exists(self) -> None:
        """Warning constant for missing old snapshot is defined."""
        # The constant should be importable and accessible
        assert WARNING_OLD_SNAPSHOT_MISSING is not None

    def test_warning_old_snapshot_missing_exact_value(self) -> None:
        """Warning constant equals expected string exactly."""
        assert WARNING_OLD_SNAPSHOT_MISSING == "Old snapshot missing"

    def test_warning_old_snapshot_missing_is_non_empty_descriptive(self) -> None:
        """Warning string is non-empty and descriptive."""
        # Check that the warning string is non-empty
        assert isinstance(WARNING_OLD_SNAPSHOT_MISSING, str)
        assert len(WARNING_OLD_SNAPSHOT_MISSING) > 0

        # Check that it contains descriptive text
        assert "old" in WARNING_OLD_SNAPSHOT_MISSING.lower() or "snapshot" in WARNING_OLD_SNAPSHOT_MISSING.lower()
