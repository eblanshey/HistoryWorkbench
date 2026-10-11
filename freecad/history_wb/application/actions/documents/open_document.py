# File responsibility: Open one FreeCAD document in the runtime session.
"""Application action for opening one document in FreeCAD."""

from __future__ import annotations

from ....domain.freecad_ports import FreeCadPort
from ....utils import Log
from ..result_models import Result


class OpenDocumentAction:
    """Open one document from filesystem path."""

    def __init__(self, freecad_port: FreeCadPort) -> None:
        self._freecad_port = freecad_port

    def execute(self, path: str, *, activate_view: bool = False) -> Result:
        """Open document at path, optionally activate its GUI view, and return action result."""
        try:
            document = self._freecad_port.open_document(path)

            # Comparison loading keeps History visible; explicit opening selects the document view.
            if activate_view:
                self._freecad_port.activate_document_view(document.Name)
            Log.debug(f"Opened document: {path}")
            return Result.success(path)
        except (RuntimeError, ValueError, OSError) as err:
            Log.warning(f"Failed to open document {path}: {err}")
            return Result.failure(str(err))


__all__ = ["OpenDocumentAction"]
