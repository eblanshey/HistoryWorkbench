# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain model for FreeCAD property values.

This module provides a unified representation of FreeCAD property values,
supporting all common property types found in PartDesign and Part workbenches.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class PropertyType(Enum):
    """Types of FreeCAD properties."""

    # Basic types
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # Vector-based types
    VECTOR = auto()  # x, y, z
    PLACEMENT = auto()  # position + rotation

    # Compound types
    LINK = auto()  # Reference to another object
    EXPRESSION = auto()  # Expression string

    # Special types (deferred for later phases)
    SHAPE = auto()  # Geometry data
    MATERIAL = auto()  # Material assignment
    UNKNOWN = auto()


@dataclass(frozen=True)
class PropertyValue:
    """A value of a FreeCAD property.

    This is a union type that can represent any FreeCAD property value.
    It includes type information to enable proper comparison and display.

    Attributes:
        type_: The type of this property value
        value: The actual value (type depends on type_)
        expression: Optional expression if this value is driven by an expression
    """

    type_: PropertyType
    value: Any
    expression: str | None = None

    def __str__(self) -> str:
        """String representation suitable for display."""
        if self.expression:
            return f"{self.value} (via {self.expression})"
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare two property values for equality.

        Two property values are equal if they have the same type, value, and expression.
        Expression differences are considered significant even if values are the same.
        """
        if not isinstance(other, PropertyValue):
            return NotImplemented

        # Different types are never equal
        if self.type_ != other.type_:
            return False

        # Expressions must match (if one has an expression and the other doesn't, they're different)
        if self.expression != other.expression:
            return False

        # For floats, use approximate equality
        if self.type_ == PropertyType.FLOAT:
            tolerance = 1e-9
            return bool(abs(self.value - other.value) < tolerance)

        return bool(self.value == other.value)

    @classmethod
    def from_bool(cls, value: bool, expression: str | None = None) -> "PropertyValue":
        """Create a boolean property value.

        Args:
            value: The boolean value
            expression: Optional expression that drives this value (e.g., "Sketch001.Length")
        """
        return cls(type_=PropertyType.BOOL, value=value, expression=expression)

    @classmethod
    def from_int(cls, value: int, expression: str | None = None) -> "PropertyValue":
        """Create an integer property value.

        Args:
            value: The integer value
            expression: Optional expression that drives this value
        """
        return cls(type_=PropertyType.INT, value=value, expression=expression)

    @classmethod
    def from_float(cls, value: float, expression: str | None = None) -> "PropertyValue":
        """Create a float property value.

        Args:
            value: The float value
            expression: Optional expression that drives this value
        """
        return cls(type_=PropertyType.FLOAT, value=value, expression=expression)

    @classmethod
    def from_string(cls, value: str, expression: str | None = None) -> "PropertyValue":
        """Create a string property value.

        Args:
            value: The string value
            expression: Optional expression that drives this value
        """
        return cls(type_=PropertyType.STRING, value=value, expression=expression)

    @classmethod
    def from_vector(cls, x: float, y: float, z: float, expression: str | None = None) -> "PropertyValue":
        """Create a vector property value."""
        return cls(type_=PropertyType.VECTOR, value=(x, y, z), expression=expression)

    @classmethod
    def from_placement(
        cls,
        position: tuple[float, float, float],
        rotation: tuple[float, float, float, float],  # axis_x, axis_y, axis_z, angle
        expression: str | None = None,
    ) -> "PropertyValue":
        """Create a placement property value."""
        return cls(
            type_=PropertyType.PLACEMENT, value={"position": position, "rotation": rotation}, expression=expression
        )

    @classmethod
    def from_link(cls, object_name: str, expression: str | None = None) -> "PropertyValue":
        """Create a link property value (reference to another object).

        Args:
            object_name: The name of the linked object
            expression: Optional expression that drives this link
        """
        return cls(type_=PropertyType.LINK, value=object_name, expression=expression)


def make_property_value(type_: PropertyType, value: Any, **kwargs: Any) -> PropertyValue:
    """Factory function to create a PropertyValue with proper type handling.

    Args:
        type_: The property type
        value: The value
        **kwargs: Additional arguments (e.g., expression)

    Returns:
        A PropertyValue instance
    """
    return PropertyValue(type_=type_, value=value, **kwargs)
