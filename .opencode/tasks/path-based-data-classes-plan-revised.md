# Task: Path-Based Property Data Classes (Revised, Detailed)

## Goal

Implement a deterministic, path-based property representation for FreeCAD values that:

1. Round-trips cleanly through YAML (`serialize -> deserialize -> serialize` stable).
2. Preserves expressions for all valid FreeCAD expression paths.
3. Uses O(1) type dispatch via explicit type maps.
4. Handles unknown values gracefully without pretending full reconstruction is possible.
5. Is implementation-clear enough that an engineer can execute without guesswork.

## Scope & Non-Goals

### In scope

- Domain model for path-based property values.
- Extraction wiring from `gui_extractor.py`.
- YAML persistence wiring in `snapshot_yaml.py`.
- Removal of legacy property handlers/value-objects replaced by the new model.

### Out of scope (separate follow-up plan)

- Diff model/comparator adaptation to new property shape.
- UI presenter/view adaptation to new property shape.

## Context

### Current problems

1. Complex values are not serialized deterministically enough for reliable snapshot equality.
2. Expression extraction is incomplete for nested sub-paths.
3. Constraint list handling loses structure in YAML.
4. Unknown FreeCAD values degrade to weak diff signal.

### Runtime findings (validated)

1. Runtime type keys:
   - `Base.Placement`
   - `Base.Vector`
   - `Base.Rotation`
   - `Sketcher.Constraint`
   - `Base.Quantity`

2. Expression keys can be dotted and undotted for the same target:
   - `.Length` and `Length`
   - `.Constraints[0]` and `Constraints[0]`

3. Constraint expression path behavior:
   - Valid: `Constraints[0]`, `.Constraints[0]`, `Constraints.MyConstr`, `.Constraints.MyConstr`
   - Invalid: `Constraints[0].Value`, `.Constraints.MyConstr.Value`
   - Meaning: constraint expressions are **item-level/root-level**, not per field (`Value`, `First`, etc.).

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|-------------------------|
| O(1) dispatch with runtime type keys (`module.name`) | Fast, explicit, easy to maintain | O(n) handler iteration |
| Add `QuantityData` in this phase | Quantity is common and should not fall into unknown fallback | Keep as unknown |
| Unknown fallback stores both `freecad_type` and `display_value` | Better diff signal than type-only fallback | Type-only fallback, raw object storage |
| Constraint expression handling is item/root only | Matches actual FreeCAD behavior | Modeling invalid `Constraints[0].Value` expressions |
| Standardize on `paths` envelope with `.` root key (`List` uses `items`) | Eliminates value-vs-path ambiguity and removes unknown special nesting | Per-class ad hoc shapes |
| Use shared path-entry helper functions | Reduces duplication and bug surface | Repeated boilerplate loops |
| No compatibility layer in this phase | MVP-forward, requested by user | Transitional compatibility wrappers |
| No YAML version bump in this phase | Keeps scope focused; does not block architecture | Add migration/versioning now |
| Diff/UI changes in follow-up plan | Keeps this task coherent and implementable | Expand scope to entire stack now |

## Architecture Impact

### Affected modules

1. `freecad/diff_wb/domain/tree/data_path.py` (**new**)
2. `freecad/diff_wb/domain/tree/property.py` (**refactor to DataPath-based Property**)
3. `freecad/diff_wb/domain/tree/__init__.py` (**exports update**)
4. `freecad/diff_wb/domain/__init__.py` (**exports update**)
5. `freecad/diff_wb/domain/snapshots/gui_extractor.py` (**expression normalization + extraction wiring**)
6. `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py` (**serialize/deserialize wiring**)

### Follow-up plan required

- `domain/diff/models.py`
- `domain/diff/comparator.py`
- `ui/presenters/diff_presenter.py`
- tests in `tests/unit/domain/diff/` and `tests/unit/ui/`

## Data Model Specification (No Guesswork)

## 1) Enums + base value type

```python
# freecad/diff_wb/domain/tree/data_path.py
# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Path-based domain value classes for deterministic
# property extraction, expression preservation, and YAML round-trip behavior.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Protocol


class InternalType(str, Enum):
    Primitive = "Primitive"
    Quantity = "Quantity"
    Vector = "Vector"
    Rotation = "Rotation"
    Placement = "Placement"
    Constraint = "Constraint"
    List = "List"
    Unknown = "Unknown"


class PropertyPathType(str, Enum):
    FLOAT = "FLOAT"
    INT = "INT"
    STRING = "STRING"
    BOOL = "BOOL"
    NULL = "NULL"


@dataclass(frozen=True)
class PropertyPathValue:
    type_: PropertyPathType
    value: Any
    expression: str | None = None
    freecad_type: str | None = None

    @staticmethod
    def from_python(value: Any, expression: str | None = None) -> "PropertyPathValue":
        if value is None:
            return PropertyPathValue(PropertyPathType.NULL, None, expression)
        if isinstance(value, bool):
            return PropertyPathValue(PropertyPathType.BOOL, value, expression)
        if isinstance(value, int):
            return PropertyPathValue(PropertyPathType.INT, value, expression)
        if isinstance(value, float):
            return PropertyPathValue(PropertyPathType.FLOAT, float(value), expression)
        return PropertyPathValue(PropertyPathType.STRING, str(value), expression)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PropertyPathValue):
            return NotImplemented
        if self.type_ != other.type_:
            return False
        if self.expression != other.expression:
            return False
        if self.type_ == PropertyPathType.FLOAT:
            return math.isclose(float(self.value), float(other.value), rel_tol=1e-9, abs_tol=1e-9)
        return self.value == other.value
```

## 2) DataPath protocol + shared path-entry helpers

```python
class DataPath(Protocol):
    INTERNAL_TYPE: InternalType

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "DataPath":
        ...

    @staticmethod
    def from_serialized_value(data: Any) -> "DataPath":
        ...

    def serialize(self) -> dict[str, Any]:
        ...


def _serialize_path_entries(paths: dict[str, PropertyPathValue]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path, pv in paths.items():
        entry: dict[str, Any] = {"type_": pv.type_.value}
        if pv.value is not None:
            entry["value"] = pv.value
        if pv.expression is not None:
            entry["expression"] = pv.expression
        if pv.freecad_type is not None:
            entry["freecad_type"] = pv.freecad_type
        result[path] = entry
    return result


def _deserialize_path_entries(raw: dict[str, Any]) -> dict[str, PropertyPathValue]:
    paths: dict[str, PropertyPathValue] = {}
    for path, entry in raw.items():
        type_name = entry.get("type_", "NULL")
        try:
            pt = PropertyPathType(type_name)
        except ValueError:
            pt = PropertyPathType.NULL
        paths[path] = PropertyPathValue(
            type_=pt,
            value=entry.get("value"),
            expression=entry.get("expression"),
            freecad_type=entry.get("freecad_type"),
        )
    return paths


def _root_expression(expr_map: dict[str, str]) -> str | None:
    return expr_map.get(".")


def _runtime_type_key(value: Any) -> str:
    t = type(value)
    return f"{t.__module__}.{t.__name__}"


def _safe_display_value(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return f"<{_runtime_type_key(value)}>"
```

## 3) Concrete DataPath classes

### PrimitiveData

```python
@dataclass(frozen=True)
class PrimitiveData:
    INTERNAL_TYPE = InternalType.Primitive
    paths: dict[str, PropertyPathValue]  # root key: "."

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "PrimitiveData":
        return PrimitiveData(paths={".": PropertyPathValue.from_python(value, _root_expression(expr_map))})

    @staticmethod
    def from_serialized_value(data: Any) -> "PrimitiveData":
        raw_paths = data.get("paths", {})
        return PrimitiveData(paths=_deserialize_path_entries(raw_paths))

    def serialize(self) -> dict[str, Any]:
        return {
            "type_": self.INTERNAL_TYPE.value,
            "paths": _serialize_path_entries(self.paths),
        }
```

### QuantityData (`Base.Quantity`)

```python
@dataclass(frozen=True)
class QuantityData:
    INTERNAL_TYPE = InternalType.Quantity
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "QuantityData":
        amount = float(getattr(value, "Value", 0.0))
        unit = str(getattr(value, "Unit", ""))
        paths = {
            "Value": PropertyPathValue(PropertyPathType.FLOAT, amount, None),
            "Unit": PropertyPathValue(PropertyPathType.STRING, unit, None),
        }
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return QuantityData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> "QuantityData":
        return QuantityData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}
```

### VectorData / RotationData / PlacementData

```python
@dataclass(frozen=True)
class VectorData:
    INTERNAL_TYPE = InternalType.Vector
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "VectorData":
        paths = {
            "x": PropertyPathValue(PropertyPathType.FLOAT, float(value.x), expr_map.get("x")),
            "y": PropertyPathValue(PropertyPathType.FLOAT, float(value.y), expr_map.get("y")),
            "z": PropertyPathValue(PropertyPathType.FLOAT, float(value.z), expr_map.get("z")),
        }
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return VectorData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> "VectorData":
        return VectorData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class RotationData:
    INTERNAL_TYPE = InternalType.Rotation
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "RotationData":
        axis = value.Axis
        paths = {
            "Angle": PropertyPathValue(PropertyPathType.FLOAT, float(value.Angle), expr_map.get("Angle")),
            "Axis.x": PropertyPathValue(PropertyPathType.FLOAT, float(axis.x), expr_map.get("Axis.x")),
            "Axis.y": PropertyPathValue(PropertyPathType.FLOAT, float(axis.y), expr_map.get("Axis.y")),
            "Axis.z": PropertyPathValue(PropertyPathType.FLOAT, float(axis.z), expr_map.get("Axis.z")),
        }
        if "Axis" in expr_map:
            paths["Axis"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Axis"])
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return RotationData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> "RotationData":
        return RotationData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}


@dataclass(frozen=True)
class PlacementData:
    INTERNAL_TYPE = InternalType.Placement
    paths: dict[str, PropertyPathValue]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "PlacementData":
        base = value.Base
        rot = value.Rotation
        axis = rot.Axis
        paths = {
            "Base.x": PropertyPathValue(PropertyPathType.FLOAT, float(base.x), expr_map.get("Base.x")),
            "Base.y": PropertyPathValue(PropertyPathType.FLOAT, float(base.y), expr_map.get("Base.y")),
            "Base.z": PropertyPathValue(PropertyPathType.FLOAT, float(base.z), expr_map.get("Base.z")),
            "Rotation.Angle": PropertyPathValue(PropertyPathType.FLOAT, float(rot.Angle), expr_map.get("Rotation.Angle")),
            "Rotation.Axis.x": PropertyPathValue(PropertyPathType.FLOAT, float(axis.x), expr_map.get("Rotation.Axis.x")),
            "Rotation.Axis.y": PropertyPathValue(PropertyPathType.FLOAT, float(axis.y), expr_map.get("Rotation.Axis.y")),
            "Rotation.Axis.z": PropertyPathValue(PropertyPathType.FLOAT, float(axis.z), expr_map.get("Rotation.Axis.z")),
        }
        if "Rotation" in expr_map:
            paths["Rotation"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Rotation"])
        if "Rotation.Axis" in expr_map:
            paths["Rotation.Axis"] = PropertyPathValue(PropertyPathType.NULL, None, expr_map["Rotation.Axis"])
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return PlacementData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> "PlacementData":
        return PlacementData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}
```

### ConstraintData (with correct expression model)

```python
@dataclass(frozen=True)
class ConstraintData:
    INTERNAL_TYPE = InternalType.Constraint
    paths: dict[str, PropertyPathValue]

    # only user-relevant fields; tweak if runtime verification shows more
    VISIBLE_FIELDS = ("Type", "Value", "First", "Second", "Third", "Driving")

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "ConstraintData":
        paths: dict[str, PropertyPathValue] = {}
        for name in ConstraintData.VISIBLE_FIELDS:
            if not hasattr(value, name):
                continue
            v = getattr(value, name)
            if v is None:
                continue
            # field-level expressions are NOT modeled; runtime path support is item-level
            paths[name] = PropertyPathValue.from_python(v, None)

        # root/item expression (e.g., Constraints[0], Constraints.MyConstr)
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)

        return ConstraintData(paths=paths)

    @staticmethod
    def from_serialized_value(data: Any) -> "ConstraintData":
        return ConstraintData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}
```

### UnknownData (addressing “we don’t know what it is”)

```python
@dataclass(frozen=True)
class UnknownData:
    INTERNAL_TYPE = InternalType.Unknown
    paths: dict[str, PropertyPathValue]  # root path stores display_value + freecad_type + optional expression

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "UnknownData":
        type_key = _runtime_type_key(value)
        display = _safe_display_value(value)
        return UnknownData(
            paths={
                ".": PropertyPathValue(
                    PropertyPathType.STRING,
                    display,
                    _root_expression(expr_map),
                    freecad_type=type_key,
                )
            },
        )

    @staticmethod
    def from_serialized_value(data: Any) -> "UnknownData":
        return UnknownData(paths=_deserialize_path_entries(data.get("paths", {})))

    def serialize(self) -> dict[str, Any]:
        return {"type_": self.INTERNAL_TYPE.value, "paths": _serialize_path_entries(self.paths)}
```

### ListData

```python
@dataclass(frozen=True)
class ListData:
    INTERNAL_TYPE = InternalType.List
    paths: dict[str, PropertyPathValue]
    items: list[DataPath]

    @staticmethod
    def from_freecad_value(value: Any, expr_map: dict[str, str]) -> "ListData":
        items: list[DataPath] = []
        for i, item in enumerate(value):
            item_expr = _list_item_expression(expr_map, i, item)
            item_expr_map = {".": item_expr} if item_expr is not None else {}
            items.append(data_path_from_freecad_value(item, item_expr_map))
        list_paths: dict[str, PropertyPathValue] = {}
        root_expr = _root_expression(expr_map)
        if root_expr is not None:
            list_paths["."] = PropertyPathValue(PropertyPathType.NULL, None, root_expr)
        return ListData(paths=list_paths, items=items)

    @staticmethod
    def from_serialized_value(data: Any) -> "ListData":
        raw_items = data.get("items", [])
        return ListData(
            paths=_deserialize_path_entries(data.get("paths", {})),
            items=[data_path_from_serialized(it) for it in raw_items],
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "type_": self.INTERNAL_TYPE.value,
            "paths": _serialize_path_entries(self.paths),
            "items": [item.serialize() for item in self.items],
        }


def _list_item_expression(expr_map: dict[str, str], index: int, item: Any) -> str | None:
    # index form: [0]
    k_index = f"[{index}]"
    if k_index in expr_map:
        return expr_map[k_index]

    # named-constraint form: MyConstr
    name = getattr(item, "Name", None)
    if isinstance(name, str) and name and name in expr_map:
        return expr_map[name]

    return None
```

## 4) O(1) dispatch maps and constructors

```python
FREECAD_TYPE_MAP: dict[str, type[DataPath]] = {
    "Base.Quantity": QuantityData,
    "Base.Vector": VectorData,
    "Base.Rotation": RotationData,
    "Base.Placement": PlacementData,
    "Sketcher.Constraint": ConstraintData,
}

PYTHON_TYPE_MAP: dict[type[Any], type[DataPath]] = {
    bool: PrimitiveData,
    int: PrimitiveData,
    float: PrimitiveData,
    str: PrimitiveData,
    type(None): PrimitiveData,
    list: ListData,
    tuple: ListData,
}

INTERNAL_TYPE_MAP: dict[str, type[DataPath]] = {
    InternalType.Primitive.value: PrimitiveData,
    InternalType.Quantity.value: QuantityData,
    InternalType.Vector.value: VectorData,
    InternalType.Rotation.value: RotationData,
    InternalType.Placement.value: PlacementData,
    InternalType.Constraint.value: ConstraintData,
    InternalType.List.value: ListData,
    InternalType.Unknown.value: UnknownData,
}


def data_path_from_freecad_value(value: Any, expr_map: dict[str, str]) -> DataPath:
    py_cls = PYTHON_TYPE_MAP.get(type(value))
    if py_cls is not None:
        return py_cls.from_freecad_value(value, expr_map)

    fc_cls = FREECAD_TYPE_MAP.get(_runtime_type_key(value))
    if fc_cls is not None:
        return fc_cls.from_freecad_value(value, expr_map)

    return UnknownData.from_freecad_value(value, expr_map)


def data_path_from_serialized(data: dict[str, Any]) -> DataPath:
    cls = INTERNAL_TYPE_MAP.get(data.get("type_", ""), UnknownData)
    return cls.from_serialized_value(data)
```

## 5) Property wrapper (path-based)

```python
# freecad/diff_wb/domain/tree/property.py

@dataclass(frozen=True)
class Property:
    value: DataPath
    group: str = "Base"

    @classmethod
    def from_freecad(cls, fc_value: Any, expr_map: dict[str, str], group: str) -> "Property":
        return cls(value=data_path_from_freecad_value(fc_value, expr_map), group=group)

    def to_serialized(self) -> dict[str, Any]:
        payload = self.value.serialize()
        payload["group"] = self.group
        return payload

    @classmethod
    def from_serialized(cls, data: dict[str, Any]) -> "Property":
        return cls(value=data_path_from_serialized(data), group=data.get("group", "Base"))
```

## 6) Extractor expression normalization (exact algorithm)

```python
# freecad/diff_wb/domain/snapshots/gui_extractor.py

def _normalize_expression_path_for_property(prop_name: str, raw_path: str) -> str | None:
    p = raw_path.lstrip(".")

    if p == prop_name:
        return "."
    if p.startswith(prop_name + "."):
        return p[len(prop_name) + 1 :]
    if p.startswith(prop_name + "["):
        # keep bracket relative key, e.g. Constraints[0] -> [0]
        return p[len(prop_name) :]
    return None


def _build_expression_map_for_property(prop_name: str, expr_engine: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(expr_engine, list):
        return result

    for entry in expr_engine:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        raw_path = str(entry[0])
        expr = str(entry[1])

        rel = _normalize_expression_path_for_property(prop_name, raw_path)
        if rel is None:
            continue

        # deterministic duplicate resolution: dotted form wins when both exist
        if rel not in result:
            result[rel] = expr
        elif raw_path.startswith("."):
            result[rel] = expr

    return result


def _extract_property_value(obj: object, prop_name: str) -> Property | None:
    try:
        value = getattr(obj, prop_name)
        expr_map = _build_expression_map_for_property(prop_name, getattr(obj, "ExpressionEngine", []))
        group = _get_property_group(obj, prop_name)
        return Property.from_freecad(value, expr_map, group)
    except Exception as e:
        Log.exception(f"Failed to extract property {prop_name}: {e}")
        return None
```

## 7) YAML contract (single stable envelope)

Each serialized property payload (non-list) must be:

```yaml
<PropertyName>:
  group: Base
  type_: Placement        # DataPath internal type
  paths:                  # DataPath payload
    Base.x:
      type_: FLOAT
      value: 1.0
      expression: 10 mm
    Rotation.Angle:
      type_: FLOAT
      value: 45.0
```

Unknown payload shape:

```yaml
UnknownProp:
  group: Data
  type_: Unknown
  paths:
    ".":
      type_: STRING
      value: "<display text>"
      freecad_type: SomeModule.SomeType
```

List payload shape:

```yaml
Constraints:
  group: Sketch
  type_: List
  paths:
  items:
    - type_: Constraint
      paths:
        Type:
          type_: STRING
          value: DistanceX
        Value:
          type_: FLOAT
          value: 10.0
        ".":
          type_: NULL
          expression: 5 mm
    - type_: Constraint
      paths:
        Type:
          type_: STRING
          value: Coincident
```

## 8) `snapshot_yaml.py` integration snippets

```python
def _serialize_properties(properties: dict[str, Property]) -> dict[str, Any]:
    return {name: prop.to_serialized() for name, prop in properties.items()}


def _deserialize_properties(data: dict[str, Any]) -> dict[str, Property]:
    if not data:
        return {}
    return {name: Property.from_serialized(payload) for name, payload in data.items()}
```

## Obsolete Code to Remove

### `freecad/diff_wb/domain/tree/property.py`

- `_PROPERTY_HANDLERS` and `register_handler`
- `PropertyHandler`
- `Vector`, `Rotation`, `Placement` legacy value classes
- `Property.create(...)`
- `Property.from_freecad_property(...)`
- `Property._infer_type_from_value(...)`
- `Property.get_children()` and helper recursion methods

### `freecad/diff_wb/domain/snapshots/gui_extractor.py`

- `_get_expression_for_property(...)` top-level-only implementation

### `freecad/diff_wb/infrastructure/persistence/snapshot_yaml.py`

- Type-specific legacy branches for VECTOR/PLACEMENT/LIST that assume old `PropertyType` data shape

## FreeCAD Dependency

- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required for API-behavior validation and integration tests

## Implementation Plan

> **Rule:** Every phase lists test steps first, implementation second.

### Phase 1: DataPath Core (No FreeCAD)

#### Tests first

- [x] `tests/unit/domain/tree/test_data_path_value.py`
  - [x] parameterized `PropertyPathValue.from_python` for `None`, bool, int, float, str
  - [x] float tolerance equality behavior
- [x] `tests/unit/domain/tree/test_data_path_dispatch.py`
  - [x] python type dispatch (`int`, `float`, `list`, etc.)
  - [x] unknown fallback contains both `freecad_type` and root display string
- [x] `tests/unit/domain/tree/test_data_path_roundtrip.py`
  - [x] round-trip `PrimitiveData`
  - [x] round-trip `UnknownData`
  - [x] round-trip `QuantityData`
  - [x] round-trip `VectorData`, `RotationData`, `PlacementData`
  - [x] round-trip `ConstraintData`
  - [x] round-trip `ListData` with mixed items

#### Implement

- [x] Create `domain/tree/data_path.py` with all specs above.
- [x] Add shared helper functions for path-entry serialization/deserialization.
- [x] Add O(1) type maps and constructor functions.

### Phase 2: Property Wrapper Refactor (No FreeCAD)

#### Tests first

- [x] `tests/unit/domain/tree/test_property_data_path_wrapper.py`
  - [x] `Property.from_freecad(...)` wraps expected DataPath type
  - [x] `Property.to_serialized()` includes `group`
  - [x] `Property.from_serialized()` restores `group`

#### Implement

- [x] Refactor `property.py` to DataPath-based `Property` wrapper.
- [x] Remove legacy creation/handler/children APIs.
- [x] Update exports in `domain/tree/__init__.py` and `domain/__init__.py`.

### Phase 3: Expression Normalization + Extractor Wiring

#### Tests first

- [x] `tests/unit/domain/snapshots/test_expression_map_normalization.py`
  - [x] `.Length` + `Length` normalize to `"."`
  - [x] `.Placement.Base.x` normalizes to `Base.x`
  - [x] `.Constraints[0]` and `Constraints[0]` normalize to `[0]`
  - [x] `.Constraints.MyConstr` normalizes to `MyConstr`
  - [x] unrelated properties are ignored

- [x] `tests/unit/domain/snapshots/test_extractor_property_dispatch.py`
  - [x] extracted property uses new `Property.from_freecad(...)`

#### Implement

- [x] Replace `_get_expression_for_property(...)` with normalization builder.
- [x] Update `_extract_property_value(...)` to call new property API.

### Phase 4: YAML Persistence Wiring

#### Tests first

- [x] `tests/unit/infrastructure/persistence/test_snapshot_yaml_data_path.py`
  - [x] property serialization uses `Property.to_serialized()` envelope
  - [x] list payload uses `items` with per-item `paths` envelopes
  - [x] unknown payload preserves path-level `freecad_type` + display root
  - [x] complete snapshot round-trip equality for mixed property types

#### Implement

- [x] Update `_serialize_properties(...)` and `_deserialize_properties(...)` to new property API.
- [x] Remove legacy value-type branches tied to old models.

### Phase 5: Focused FreeCAD Integration Validation

#### Tests first

- [x] `tests/integration/test_property_path_extraction_freecad.py`
  - [x] placement nested expressions are captured with normalized keys
  - [x] constraint item expression is captured at root/item level only
  - [x] quantity extraction maps to `QuantityData`

Example integration test sketch:

```python
def test_constraint_expression_root_only(freecad_doc):
    sketch = freecad_doc.addObject("Sketcher::SketchObject", "Sketch")
    # ... add geometry + constraint index 0
    sketch.setExpression("Constraints[0]", "5 mm")

    expr_map = _build_expression_map_for_property("Constraints", sketch.ExpressionEngine)
    assert expr_map["[0]"] == "5 mm"
    assert "[0].Value" not in expr_map
```

#### Implement

- [x] Adjust any extraction details exposed by integration failures.

### Phase 6: Cleanup & Test Noise Reduction

#### Tests first

- [x] Consolidate repetitive primitive tests into parametric tests.
- [x] Remove legacy tests tied only to removed APIs (`Property.create`, `get_children`, legacy geometry classes).

#### Implement

- [x] Remove obsolete code listed above.
- [x] Keep test suite focused on long-term behavioral contracts.

### Phase 7: Manual Testing Documentation

- [ ] Deferred by explicit user request in this planning session.

## Test Strategy

### Unit tests

- Prefer behavior-rich parameterized tests over repetitive one-case tests.
- Focus on dispatch, normalization, envelope consistency, and round-trip determinism.

### Integration tests

- Keep minimal but high-signal FreeCAD runtime tests:
  - placement expressions
  - constraints path behavior
  - quantity extraction

## Notes Answering Open Questions

1. **UnknownData proposal**: store `freecad_type` on the root path entry (`.`), alongside `display_value` and optional root expression.
2. **Constraint expressions**: item-level only (`Constraints[0]` / `Constraints.MyConstr`), not field-level (`...Value`).
3. **Blast radius strategy**: representation now; diff/UI in explicit follow-up plan.
4. **YAML versioning**: intentionally deferred; architecture here does not depend on introducing it now.
5. **Duplication reduction**: shared `_serialize_path_entries` and `_deserialize_path_entries` helpers are required.
6. **No compatibility layer**: explicitly not used in this phase.
