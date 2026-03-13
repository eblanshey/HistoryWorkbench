# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain models for FreeCAD placements (position and orientation).

This module provides pure Python representations of FreeCAD's Placement
concept, which combines position (Vector) and orientation (Rotation).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vector:
    """A 3D vector representing position or direction.

    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
    """

    x: float
    y: float
    z: float

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.x - other.x) < tolerance
            and abs(self.y - other.y) < tolerance
            and abs(self.z - other.z) < tolerance
        )


@dataclass(frozen=True)
class Rotation:
    """A rotation represented by axis-angle notation.

    FreeCAD uses axis-angle representation internally. A rotation consists of
    an axis (unit vector) and an angle (in degrees).

    Attributes:
        axis_x: X component of rotation axis
        axis_y: Y component of rotation axis
        axis_z: Z component of rotation axis
        angle_degrees: Rotation angle in degrees
    """

    axis_x: float
    axis_y: float
    axis_z: float
    angle_degrees: float

    def __str__(self) -> str:
        return f"Axis=({self.axis_x}, {self.axis_y}, {self.axis_z}), Angle={self.angle_degrees}°"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rotation):
            return NotImplemented
        # Use approximate equality for floats
        tolerance = 1e-9
        return (
            abs(self.axis_x - other.axis_x) < tolerance
            and abs(self.axis_y - other.axis_y) < tolerance
            and abs(self.axis_z - other.axis_z) < tolerance
            and abs(self.angle_degrees - other.angle_degrees) < tolerance
        )

    @classmethod
    def identity(cls) -> "Rotation":
        """Create an identity rotation (no rotation)."""
        return cls(axis_x=0.0, axis_y=0.0, axis_z=1.0, angle_degrees=0.0)


@dataclass(frozen=True)
class Placement:
    """A placement combining position and orientation.

    Represents a transformation in 3D space, combining a position vector
    and a rotation. This is the fundamental way FreeCAD positions objects.

    Attributes:
        position: The position vector
        rotation: The rotation (axis-angle)
    """

    position: Vector
    rotation: Rotation

    def __str__(self) -> str:
        return f"Pos={self.position}, Rot={self.rotation}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Placement):
            return NotImplemented
        return self.position == other.position and self.rotation == other.rotation

    @classmethod
    def identity(cls) -> "Placement":
        """Create an identity placement (origin, no rotation)."""
        return cls(position=Vector(0.0, 0.0, 0.0), rotation=Rotation.identity())
