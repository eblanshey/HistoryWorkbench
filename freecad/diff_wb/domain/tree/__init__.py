# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Exports all tree-related domain models including
# TreeNode, the DataPath-based Property wrapper, and the DataPath hierarchy
# (PrimitiveData, QuantityData, VectorData, RotationData, PlacementData,
# ConstraintData, UnknownData, ListData) with their dispatch maps and
# constructor functions for FreeCAD value conversion and YAML serialization.
"""Tree domain models - shared foundation for snapshots and diff."""

from .data_path import (
    FREECAD_TYPE_MAP,
    INTERNAL_TYPE_MAP,
    PYTHON_TYPE_MAP,
    ConstraintData,
    DataPath,
    InternalType,
    ListData,
    PlacementData,
    PrimitiveData,
    PropertyPathType,
    PropertyPathValue,
    QuantityData,
    RotationData,
    UnknownData,
    VectorData,
    data_path_from_freecad_value,
    data_path_from_serialized,
)
from .node import TreeNode
from .property import Property


__all__ = [
    # Tree models
    "TreeNode",
    "Property",
    # DataPath hierarchy
    "InternalType",
    "PropertyPathType",
    "PropertyPathValue",
    "DataPath",
    "PrimitiveData",
    "QuantityData",
    "VectorData",
    "RotationData",
    "PlacementData",
    "ConstraintData",
    "UnknownData",
    "ListData",
    "data_path_from_freecad_value",
    "data_path_from_serialized",
    "FREECAD_TYPE_MAP",
    "PYTHON_TYPE_MAP",
    "INTERNAL_TYPE_MAP",
]
