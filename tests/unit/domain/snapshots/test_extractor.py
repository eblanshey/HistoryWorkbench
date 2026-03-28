# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for SnapshotExtractor using FakeFreeCadPort, including
# tree extraction from documents, nested children (via Group/OriginFeatures/InList),
# property extraction, and expression handling.
"""Unit tests for SnapshotExtractor."""

from unittest.mock import MagicMock

from freecad.diff_wb.domain.snapshots.extractor import SnapshotExtractor
from freecad.diff_wb.domain.snapshots.models import Snapshot


class MockFreeCADObject:
    """Mock FreeCAD object for testing.

    Uses Group + OriginFeatures + InList for hierarchy (matching the simplified
    extractor logic), not OutList which represents dependencies not containment.
    """

    def __init__(
        self,
        name,
        type_id,
        label,
        properties=None,
        group=None,
        origin_features=None,
        in_list=None,
        expression_engine=None,
        property_editor_modes=None,
        property_groups=None,
    ):
        """Initialize a mock FreeCAD object.

        Args:
            name: Object name
            type_id: FreeCAD type ID
            label: Display label
            properties: List of property names
            group: Child objects in this container's Group
            origin_features: Origin geometry objects
            in_list: Objects that reference this one (for parent detection)
            expression_engine: List of [prop_name, expression] pairs
            property_editor_modes: Dict mapping property name to editor mode list
                e.g., {"HiddenProp": ["Hidden"], "VisibleProp": []}
            property_groups: Dict mapping property name to group name
                e.g., {"Shape": "", "Length": "Side1"}
        """
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_type_id", type_id)
        object.__setattr__(self, "_label", label)
        object.__setattr__(self, "_properties", properties or [])
        object.__setattr__(self, "_group", group or [])
        object.__setattr__(self, "_origin_features", origin_features or [])
        object.__setattr__(self, "_in_list", in_list or [])
        object.__setattr__(self, "_expression_engine", expression_engine or [])
        object.__setattr__(self, "_properties_values", {})
        object.__setattr__(self, "_property_editor_modes", property_editor_modes or {})
        object.__setattr__(self, "_property_groups", property_groups or {})

    @property
    def Name(self):
        return object.__getattribute__(self, "_name")

    @property
    def TypeId(self):
        return object.__getattribute__(self, "_type_id")

    @property
    def Label(self):
        return object.__getattribute__(self, "_label")

    @property
    def PropertiesList(self):
        return object.__getattribute__(self, "_properties")

    @property
    def Group(self):
        return object.__getattribute__(self, "_group")

    @property
    def OriginFeatures(self):
        return object.__getattribute__(self, "_origin_features")

    @property
    def InList(self):
        return object.__getattribute__(self, "_in_list")

    @property
    def ExpressionEngine(self):
        return object.__getattribute__(self, "_expression_engine")

    def getEditorMode(self, prop_name):
        modes = object.__getattribute__(self, "_property_editor_modes")
        return modes.get(prop_name, [])

    def getGroupOfProperty(self, prop_name):
        groups = object.__getattribute__(self, "_property_groups")
        return groups.get(prop_name, "")

    def __getattr__(self, name):
        props = object.__getattribute__(self, "_properties_values")
        if name in props:
            return props[name]
        if name == "Label":
            return object.__getattribute__(self, "_label")
        return None

    def __setattr__(self, name, value):
        props = object.__getattribute__(self, "_properties_values")
        props[name] = value


class FakePortAndLogger:
    """Fake implementation combining FreeCadPort and Logger for unit testing."""

    def __init__(self):
        """Initialize the fake port with empty document state."""
        self._documents = {}
        self._messages = []

    def get_active_document(self):
        """Get the active document, or None if no document is open."""
        return self._documents.get("active")

    def get_object(self, doc, name):
        """Get a document object by name."""
        if hasattr(doc, "getObject"):
            return doc.getObject(name)
        return None

    def try_recompute_active_document(self):
        """No-op for recompute."""
        pass

    def try_update_gui(self):
        """No-op for GUI update."""
        pass

    def log(self, text):
        """Log a message."""
        self._messages.append(("log", text))

    def warn(self, text):
        """Show a warning message."""
        self._messages.append(("warn", text))

    def message(self, text):
        """Show an informational message."""
        self._messages.append(("message", text))

    def set_active_document(self, doc):
        """Set the active document for testing."""
        self._documents["active"] = doc

    def info(self, message):
        """Log an info message."""
        self._messages.append(("info", message))

    def warning(self, message):
        """Log a warning message."""
        self._messages.append(("warning", message))

    def error(self, message):
        """Log an error message."""
        self._messages.append(("error", message))


class TestSnapshotExtractor:
    """Tests for SnapshotExtractor class."""

    def test_extract_tree_with_empty_document(self):
        """Test extraction from an empty document."""
        mock_doc = MagicMock()
        mock_doc.Objects = []
        mock_doc.Name = "EmptyDocument"

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert isinstance(result, Snapshot)
        assert result.document_name == "EmptyDocument"
        assert result.root_nodes == []

    def test_extract_tree_with_root_object(self):
        """Test extraction with a single root object."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        root_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label", "Placement"],
        )
        root_obj.Label = "My Body"
        root_obj.Placement = "mock_placement"

        mock_doc.Objects = [root_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert isinstance(result, Snapshot)
        assert result.document_name == "TestDoc"
        assert len(result.root_nodes) == 1
        assert result.root_nodes[0].name == "Body"
        assert result.root_nodes[0].type_id == "PartDesign::Body"

    def test_extract_tree_with_nested_children_via_group(self):
        """Test extraction with nested child objects via Group property."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create child object
        child_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        child_obj.Label = "My Sketch"

        # Create parent with child in Group (visual containment)
        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
            group=[child_obj],
        )
        parent_obj.Label = "My Body"

        # Both objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [parent_obj, child_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Body":
                return parent_obj
            elif name == "Sketch":
                return child_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        parent = result.root_nodes[0]
        assert parent.name == "Body"
        assert len(parent.children) == 1
        assert parent.children[0].name == "Sketch"
        assert parent.children[0].path == "Body/Sketch"

    def test_extract_tree_handles_no_document(self):
        """Test that extract_tree handles no document gracefully."""
        fake_port = FakePortAndLogger()
        # No document set

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        # Should return a Snapshot with empty root_nodes when no document
        assert isinstance(result, Snapshot)
        assert result.document_name == "NoDocument"
        assert result.root_nodes == []

    def test_extract_tree_property_extraction(self):
        """Test that properties are correctly extracted."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length"],
            property_groups={"Label": "Base", "Length": "Side1"},
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]
        # Properties should be extracted (with non-empty groups)
        assert "Label" in node.properties
        assert "Length" in node.properties

    def test_extract_tree_captures_expressions(self):
        """Test that expressions are correctly captured from ExpressionEngine."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create object with expression engine
        obj = MockFreeCADObject(
            name="Pocket",
            type_id="PartDesign::Pocket",
            label="Test Pocket",
            properties=["Label", "Length"],
            expression_engine=[["Length", "Sketch.Length * 0.5"]],
            property_groups={"Label": "Base", "Length": "Side1"},
        )
        obj.Label = "Test Pocket"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]
        # Length property should have expression (with non-empty group)
        assert "Length" in node.properties
        length_prop = node.properties["Length"]
        assert length_prop.expression == "Sketch.Length * 0.5"
        assert length_prop.value == 10.0

    def test_extract_tree_discovers_children_via_group(self):
        """Test that Group property discovers children correctly.

        This tests the scenario where a Part container has Body and VarSet in its Group.
        The hierarchy is built from Group/OriginFeatures, not OutList.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create VarSet object
        varset_obj = MockFreeCADObject(
            name="VarSet",
            type_id="App::VarSet",
            label="Variable Set",
            properties=["Label"],
        )
        varset_obj.Label = "Variable Set"

        # Create Body object
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        body_obj.Label = "My Body"

        # Create Part container with Group=[Body, VarSet]
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
            group=[body_obj, varset_obj],
        )
        part_obj.Label = "My Part"

        # All objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [part_obj, body_obj, varset_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Part":
                return part_obj
            elif name == "Body":
                return body_obj
            elif name == "VarSet":
                return varset_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        part_node = result.root_nodes[0]
        assert part_node.name == "Part"

        # Should have both Body and VarSet from Group
        assert len(part_node.children) == 2

        child_names = {child.name for child in part_node.children}
        assert "Body" in child_names
        assert "VarSet" in child_names

        # Verify children paths
        varset_node = next(c for c in part_node.children if c.name == "VarSet")
        assert varset_node.type_id == "App::VarSet"
        assert varset_node.path == "Part/VarSet"

    def test_extract_tree_handles_nested_hierarchy(self):
        """Test nested hierarchy: Part -> Body -> Sketch.

        This verifies that the three-pass parent detection correctly builds
        multi-level hierarchies using Group and InList.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create leaf Sketch object
        sketch_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        sketch_obj.Label = "My Sketch"

        # Create Body with Sketch in Group
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
            group=[sketch_obj],
        )
        body_obj.Label = "My Body"

        # Create Part with Body in Group
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
            group=[body_obj],
        )
        part_obj.Label = "My Part"

        # All objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [part_obj, body_obj, sketch_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Part":
                return part_obj
            elif name == "Body":
                return body_obj
            elif name == "Sketch":
                return sketch_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        part_node = result.root_nodes[0]
        assert part_node.name == "Part"

        # Part should have Body as child
        assert len(part_node.children) == 1
        body_node = part_node.children[0]
        assert body_node.name == "Body"
        assert body_node.path == "Part/Body"

        # Body should have Sketch as child
        assert len(body_node.children) == 1
        sketch_node = body_node.children[0]
        assert sketch_node.name == "Sketch"
        assert sketch_node.path == "Part/Body/Sketch"

    def test_extract_tree_handles_origin_features(self):
        """Test that OriginFeatures property correctly identifies origin children.

        App::Origin containers store their geometry (axes, planes, points) in
        OriginFeatures instead of Group.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create origin geometry objects
        x_axis_obj = MockFreeCADObject(
            name="X_Axis",
            type_id="App::Line",
            label="X_Axis",
            properties=["Label"],
        )
        x_axis_obj.Label = "X_Axis"

        xy_plane_obj = MockFreeCADObject(
            name="XY_Plane",
            type_id="App::Plane",
            label="XY_Plane",
            properties=["Label"],
        )
        xy_plane_obj.Label = "XY_Plane"

        # Create Origin container with geometry in OriginFeatures
        origin_obj = MockFreeCADObject(
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            properties=["Label"],
            origin_features=[x_axis_obj, xy_plane_obj],
        )
        origin_obj.Label = "Origin"

        # All objects must be in doc.Objects
        mock_doc.Objects = [origin_obj, x_axis_obj, xy_plane_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Origin":
                return origin_obj
            elif name == "X_Axis":
                return x_axis_obj
            elif name == "XY_Plane":
                return xy_plane_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        origin_node = result.root_nodes[0]
        assert origin_node.name == "Origin"

        # Origin should have X_Axis and XY_Plane as children
        assert len(origin_node.children) == 2
        child_names = {child.name for child in origin_node.children}
        assert "X_Axis" in child_names
        assert "XY_Plane" in child_names

    def test_extract_tree_filters_hidden_properties_by_editor_mode(self):
        """Test that properties with ['Hidden'] editor mode are filtered out."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create object with some hidden and visible properties
        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "BaseFeature", "ExpressionEngine", "Visibility"],
            # Editor modes: some hidden, some visible
            property_editor_modes={
                "BaseFeature": ["Hidden"],
                "ExpressionEngine": ["Hidden"],
                "Visibility": ["Hidden"],
                "Label": [],
                "Length": [],
            },
            # All properties have non-empty groups
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "BaseFeature": "Base",
                "ExpressionEngine": "Base",
                "Visibility": "Base",
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # Visible properties should be present
        assert "Label" in node.properties
        assert "Length" in node.properties

        # Hidden properties should be filtered out
        assert "BaseFeature" not in node.properties
        assert "ExpressionEngine" not in node.properties
        assert "Visibility" not in node.properties

    def test_extract_tree_filters_hidden_properties_by_empty_group(self):
        """Test that properties with empty group are filtered out.

        Properties with getGroupOfProperty() returning empty string are hidden
        in FreeCAD's property editor (shown only with "show hidden" enabled).
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Shape", "SuppressedShape", "AddSubShape", "ShapeMaterial"],
            # Property groups: empty for hidden properties, non-empty for visible
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Shape": "",  # Empty group = hidden
                "SuppressedShape": "",  # Empty group = hidden
                "AddSubShape": "",  # Empty group = hidden
                "ShapeMaterial": "",  # Empty group = hidden
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0
        obj.Shape = "shape_data"
        obj.SuppressedShape = "suppressed"
        obj.AddSubShape = "subshape"
        obj.ShapeMaterial = "material"

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # Visible properties (with non-empty groups) should be present
        assert "Label" in node.properties
        assert "Length" in node.properties

        # Properties with empty groups should be filtered out
        assert "Shape" not in node.properties
        assert "SuppressedShape" not in node.properties
        assert "AddSubShape" not in node.properties
        assert "ShapeMaterial" not in node.properties

    def test_extract_tree_filters_combined_hidden_conditions(self):
        """Test filtering with both editor mode and empty group conditions."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Shape", "Visibility", "Placement", "_ElementMapVersion"],
            property_editor_modes={
                "Visibility": ["Hidden"],
                "Placement": ["ReadOnly", "Hidden"],
                "_ElementMapVersion": ["Hidden"],
            },
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Shape": "",  # Empty group
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # Only Label and Length should be present (both visible by editor mode AND group)
        assert "Label" in node.properties
        assert "Length" in node.properties
        assert len(node.properties) == 2

    def test_extract_tree_includes_properties_with_non_empty_group(self):
        """Test that properties with non-empty groups are included."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Type", "TaperAngle", "Refine"],
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Type": "Side1",
                "TaperAngle": "Side1",
                "Refine": "Part Design",
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0
        obj.Type = "Length"
        obj.TaperAngle = 0.0
        obj.Refine = False

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # All properties with non-empty groups should be present
        assert "Label" in node.properties
        assert "Length" in node.properties
        assert "Type" in node.properties
        assert "TaperAngle" in node.properties
        assert "Refine" in node.properties
