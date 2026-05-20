# File responsibility: FreeCAD visual BREP diff document creation service.

"""FreeCAD visual BREP diff document creation service."""

from __future__ import annotations

from typing import Any, cast

from ...domain.freecad_ports import FreeCadContext


Color = tuple[float, float, float, float]

DIFF_FEATURE_TRANSPARENCY: int = 50
UNCHANGED_COLOR: Color = (0.6, 0.6, 0.6, 1.0)
ADDED_COLOR: Color = (0.0, 0.8, 0.0, 1.0)
REMOVED_COLOR: Color = (0.9, 0.0, 0.0, 1.0)


class FreeCADVisualDiffCreator:
    """Open a new FreeCAD document importing old/new BREP as features."""

    def __init__(self, ctx: FreeCadContext) -> None:
        self._ctx = ctx

    def open_brep_visual_diff(
        self,
        old_brep_path: str | None,
        new_brep_path: str | None,
        document_name: str,
    ) -> object:
        """Open a new document showing unchanged, added, and removed BREP regions."""
        if old_brep_path is None and new_brep_path is None:
            raise ValueError("At least one BREP path is required")

        document = self._ctx.app.newDocument(document_name)

        old_shape = self._load_shape(old_brep_path) if old_brep_path is not None else None
        new_shape = self._load_shape(new_brep_path) if new_brep_path is not None else None
        if old_shape is not None:
            self._reset_placement(old_shape)
        if new_shape is not None:
            self._reset_placement(new_shape)

        if old_shape is None or new_shape is None:
            self._add_single_visual(document, old_shape, new_shape)
            document.recompute()
            self._set_corner_view_and_fit_all()
            return document

        self._add_diff_visuals(document, old_shape, new_shape)
        document.recompute()
        self._set_corner_view_and_fit_all()
        return document

    def _add_single_visual(self, document: Any, old_shape: object | None, new_shape: object | None) -> None:
        visual_shape = old_shape if old_shape is not None else new_shape
        visual_name = "Old_Visual" if old_shape is not None else "New_Visual"
        visual_feature = cast(Any, document.addObject("Part::Feature", visual_name))
        visual_feature.Label = visual_name
        visual_feature.Shape = visual_shape

    def _add_diff_visuals(self, document: Any, old_shape: object, new_shape: object) -> None:
        old_feature = cast(Any, document.addObject("Part::Feature", "Old_Visual"))
        old_feature.Label = "Old_Visual"
        old_feature.Shape = old_shape
        old_feature.ViewObject.Visibility = False

        new_feature = cast(Any, document.addObject("Part::Feature", "New_Visual"))
        new_feature.Label = "New_Visual"
        new_feature.Shape = new_shape
        new_feature.ViewObject.Visibility = False

        diff_folder = cast(Any, document.addObject("App::DocumentObjectGroup", "Diff"))
        diff_folder.Label = "Diff"

        unchanged_feature = cast(Any, document.addObject("Part::Feature", "Unchanged_Visual"))
        unchanged_feature.Label = "Unchanged_Visual"
        unchanged_feature.Shape = cast(Any, old_shape).common(new_shape)
        self._set_color(unchanged_feature, UNCHANGED_COLOR)
        unchanged_feature.ViewObject.Transparency = DIFF_FEATURE_TRANSPARENCY
        diff_folder.addObject(unchanged_feature)

        added_feature = cast(Any, document.addObject("Part::Feature", "Added_Visual"))
        added_feature.Label = "Added_Visual"
        added_feature.Shape = cast(Any, new_shape).cut(old_shape)
        added_feature.ViewObject.Transparency = DIFF_FEATURE_TRANSPARENCY
        self._set_color(added_feature, ADDED_COLOR)
        diff_folder.addObject(added_feature)

        removed_feature = cast(Any, document.addObject("Part::Feature", "Removed_Visual"))
        removed_feature.Label = "Removed_Visual"
        removed_feature.Shape = cast(Any, old_shape).cut(new_shape)
        removed_feature.ViewObject.Transparency = DIFF_FEATURE_TRANSPARENCY
        self._set_color(removed_feature, REMOVED_COLOR)
        diff_folder.addObject(removed_feature)

    def _load_shape(self, path: str) -> object:
        import Part

        shape = Part.Shape()
        shape.read(path)
        return shape

    def _reset_placement(self, feature: Any) -> None:
        import FreeCAD

        feature.Placement = FreeCAD.Placement(
            FreeCAD.Vector(0, 0, 0),
            FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0),
        )

    def _set_color(self, feature: Any, color: Color) -> None:
        feature.ViewObject.ShapeColor = color
        feature.ViewObject.LineColor = color
        feature.ViewObject.PointColor = color

    def _set_corner_view_and_fit_all(self) -> None:
        try:
            import FreeCADGui
        except ImportError:
            return

        FreeCADGui.runCommand("Std_ViewIsometric", 0)
        FreeCADGui.runCommand("Std_ViewFitAll", 0)
