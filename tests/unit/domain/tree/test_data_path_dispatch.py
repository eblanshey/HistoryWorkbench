# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for data_path dispatch functions including
# Python type dispatch and unknown type fallback behavior.
"""Unit tests for data_path dispatch functions."""

import pytest

from freecad.diff_wb.domain.tree.data_path import (
    DataPath,
    ListData,
    PrimitiveData,
    UnknownData,
    data_path_from_freecad_value,
)


class MockUnknownType:
    """A mock class simulating an unknown FreeCAD type."""

    def __str__(self) -> str:
        return "<MockUnknownType display>"


class TestPythonTypeDispatch:
    """Tests for dispatch based on Python built-in types."""

    @pytest.mark.parametrize(
        ("value", "expected_class"),
        [
            (True, PrimitiveData),
            (False, PrimitiveData),
            (42, PrimitiveData),
            (-7, PrimitiveData),
            (3.14, PrimitiveData),
            (0.0, PrimitiveData),
            ("hello", PrimitiveData),
            ("", PrimitiveData),
            (None, PrimitiveData),
            ([1, 2, 3], ListData),
            ((1, 2, 3), ListData),
        ],
    )
    def test_python_type_dispatch(self, value: object, expected_class: type[DataPath]) -> None:
        """Test that Python built-in types dispatch to the correct DataPath class."""
        result = data_path_from_freecad_value(value, {})
        assert isinstance(result, expected_class)

    def test_int_dispatch(self) -> None:
        """Test that int values dispatch to PrimitiveData."""
        result = data_path_from_freecad_value(42, {})
        assert isinstance(result, PrimitiveData)
        assert "." in result.paths
        assert result.paths["."].value == 42

    def test_float_dispatch(self) -> None:
        """Test that float values dispatch to PrimitiveData."""
        result = data_path_from_freecad_value(3.14, {})
        assert isinstance(result, PrimitiveData)
        assert "." in result.paths
        assert result.paths["."].value == 3.14

    def test_string_dispatch(self) -> None:
        """Test that string values dispatch to PrimitiveData."""
        result = data_path_from_freecad_value("hello", {})
        assert isinstance(result, PrimitiveData)
        assert "." in result.paths
        assert result.paths["."].value == "hello"

    def test_bool_dispatch(self) -> None:
        """Test that bool values dispatch to PrimitiveData (not int)."""
        result = data_path_from_freecad_value(True, {})
        assert isinstance(result, PrimitiveData)
        assert result.paths["."].value is True

    def test_none_dispatch(self) -> None:
        """Test that None values dispatch to PrimitiveData."""
        result = data_path_from_freecad_value(None, {})
        assert isinstance(result, PrimitiveData)

    def test_list_dispatch(self) -> None:
        """Test that list values dispatch to ListData."""
        result = data_path_from_freecad_value([1, 2, 3], {})
        assert isinstance(result, ListData)
        assert len(result.items) == 3

    def test_tuple_dispatch(self) -> None:
        """Test that tuple values dispatch to ListData."""
        result = data_path_from_freecad_value((1, 2, 3), {})
        assert isinstance(result, ListData)
        assert len(result.items) == 3


class TestUnknownFallback:
    """Tests for unknown type fallback to UnknownData."""

    def test_unknown_type_fallback(self) -> None:
        """Test that unrecognized types fall back to UnknownData."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)

    def test_unknown_contains_freecad_type(self) -> None:
        """Test that UnknownData contains freecad_type info."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)
        assert "." in result.paths
        assert result.paths["."].freecad_type is not None
        assert "MockUnknownType" in result.paths["."].freecad_type

    def test_unknown_contains_root_display_string(self) -> None:
        """Test that UnknownData root path contains display string."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        assert isinstance(result, UnknownData)
        assert result.paths["."].value == "<MockUnknownType display>"

    def test_unknown_with_expression(self) -> None:
        """Test that UnknownData preserves expression."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {".": "Some.Expression"})
        assert isinstance(result, UnknownData)
        assert result.paths["."].expression == "Some.Expression"

    def test_unknown_type_key_format(self) -> None:
        """Test that the freecad_type key has module.name format."""
        mock = MockUnknownType()
        result = data_path_from_freecad_value(mock, {})
        type_key = result.paths["."].freecad_type
        assert type_key is not None
        assert "." in type_key  # Should have module.name format
