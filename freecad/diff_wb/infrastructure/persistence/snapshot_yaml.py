# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: YAML serialization and deserialization for Snapshot objects
# using the DataPath-based Property model.
"""YAML persistence for snapshot storage and retrieval."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from freecad.diff_wb.domain import Property, Snapshot, TreeNode


class SnapshotYamlSerializer:
    """Serializer for snapshot YAML format.

    Provides methods to serialize and deserialize Snapshot objects to/from
    YAML files following the ProjectState.md format specification.

    YAML format:
        v: snapshot_version
        timestamp: [UTC timestamp]
        uid: [document UUID]
        objects:
        - id: 43
          type_id: Sketcher::SketchObject
          name: Sketch
          after: [sibling name or null]
          path: [full path for text diff readability]
          properties: {...}
    """

    SNAPSHOT_VERSION = 1

    @staticmethod
    def to_yaml(snapshot: Snapshot, path: Path) -> None:
        """Serialize a Snapshot to YAML format.

        Args:
            snapshot: The snapshot to serialize
            path: The path to write the YAML file to
        """
        # Sort nodes by ID (as per spec: "objects are stored in order of the integer id")
        sorted_nodes = sorted(snapshot.nodes, key=lambda n: n.id)

        objects = []
        for node in sorted_nodes:
            obj_dict = {
                "id": node.id,
                "type_id": node.type_id,
                "name": node.name,
                "after": node.after,
                "path": node.path,
                "properties": SnapshotYamlSerializer._serialize_properties(node.properties),
            }
            objects.append(obj_dict)

        data = {
            "v": SnapshotYamlSerializer.SNAPSHOT_VERSION,
            "timestamp": snapshot.timestamp.isoformat(),
            "uid": snapshot.snapshot_id,
            "objects": objects,
        }

        # Write YAML with explicit styling for better text diff readability
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    @staticmethod
    def from_yaml_file(path: Path) -> Snapshot:
        """Deserialize a Snapshot from a YAML file.

        Args:
            path: The path to read the YAML file from.

        Returns:
            The deserialized Snapshot object.
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return SnapshotYamlSerializer._from_data(data)

    @staticmethod
    def from_yaml(yaml_string: str) -> Snapshot:
        """Deserialize a Snapshot from a YAML string.

        Args:
            yaml_string: The YAML content as a string.

        Returns:
            The deserialized Snapshot object.
        """
        data = yaml.safe_load(yaml_string)
        return SnapshotYamlSerializer._from_data(data)

    @staticmethod
    def _from_data(data: dict[str, Any]) -> Snapshot:
        """Deserialize a Snapshot from parsed YAML data.

        Args:
            data: The parsed YAML dictionary.

        Returns:
            The deserialized Snapshot object.
        """
        # Parse timestamp (yaml.safe_load may parse ISO strings as datetime objects)
        timestamp_raw = data.get("timestamp")
        if isinstance(timestamp_raw, datetime):
            timestamp = timestamp_raw
        elif isinstance(timestamp_raw, str) and timestamp_raw:
            timestamp = datetime.fromisoformat(timestamp_raw)
        else:
            timestamp = datetime.now(UTC)

        # Parse objects
        nodes = []
        for obj in data.get("objects", []):
            properties = SnapshotYamlSerializer._deserialize_properties(obj.get("properties", {}))

            node = TreeNode(
                id=obj["id"],
                name=obj["name"],
                type_id=obj["type_id"],
                label=obj.get("label", obj["name"]),
                path=obj["path"],
                after=obj.get("after"),
                properties=properties,
            )
            nodes.append(node)

        return Snapshot(
            snapshot_id=data.get("uid", ""),
            document_name="",  # Not stored in YAML format
            timestamp=timestamp,
            nodes=nodes,
        )

    @staticmethod
    def _serialize_properties(properties: dict[str, Property]) -> dict[str, Any]:
        """Serialize property dict to YAML-compatible format.

        Delegates to Property.to_serialized() which returns the DataPath-based
        envelope with kind, paths/items, and group keys.

        Args:
            properties: Dictionary of property name to Property

        Returns:
            Dictionary suitable for YAML serialization
        """
        return {name: prop.to_serialized() for name, prop in properties.items()}

    @staticmethod
    def _deserialize_properties(data: dict[str, Any]) -> dict[str, Property]:
        """Deserialize property dict from YAML format.

        Delegates to Property.from_serialized() which reconstructs the DataPath
        value from the envelope.

        Args:
            data: Dictionary from YAML

        Returns:
            Dictionary of property name to Property
        """
        if not data:
            return {}
        return {name: Property.from_serialized(payload) for name, payload in data.items()}


__all__ = ["SnapshotYamlSerializer"]
