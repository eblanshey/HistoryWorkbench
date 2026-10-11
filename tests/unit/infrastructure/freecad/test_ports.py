# File responsibility: Unit tests for FreeCadPortAdapter modified-save and GUI view activation behavior.
"""Unit tests for FreeCadPortAdapter runtime operations."""

from unittest.mock import MagicMock, PropertyMock

import pytest

from freecad.history_wb.domain.freecad_ports import FreeCadContext
from freecad.history_wb.infrastructure.freecad.ports import FreeCadPortAdapter


class TestFreeCadPortAdapterSaveIfModified:
    def test_modified_gui_document_saves_and_returns_true(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui_doc = MagicMock()
        type(gui_doc).Modified = PropertyMock(return_value=True)

        gui = MagicMock()
        gui.getDocument.return_value = gui_doc

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is True
        doc.save.assert_called_once_with()

    def test_unmodified_gui_document_does_not_save_and_returns_false(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui_doc = MagicMock()
        type(gui_doc).Modified = PropertyMock(return_value=False)

        gui = MagicMock()
        gui.getDocument.return_value = gui_doc

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is False
        doc.save.assert_not_called()

    def test_missing_gui_document_does_not_save_and_returns_false(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui = MagicMock()
        gui.getDocument.return_value = None

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.save_document_if_modified(doc)

        assert result is False
        doc.save.assert_not_called()

    def test_is_document_modified_checks_gui_flag_without_saving(self) -> None:
        doc = MagicMock()
        doc.Name = "Doc"

        gui_doc = MagicMock()
        type(gui_doc).Modified = PropertyMock(return_value=True)

        gui = MagicMock()
        gui.getDocument.return_value = gui_doc

        ctx = FreeCadContext(app=MagicMock(), gui=gui)  # type: ignore[arg-type]
        adapter = FreeCadPortAdapter(ctx)

        result = adapter.is_document_modified(doc)

        assert result is True
        doc.save.assert_not_called()


def test_activate_document_view_selects_existing_view_in_main_window() -> None:
    """Explicit activation selects the document MDI window even when the document is already active."""
    app = MagicMock()
    app.ActiveDocument.Name = "Doc"
    gui = MagicMock()
    view = object()
    gui.getDocument.return_value.activeView.return_value = view
    adapter = FreeCadPortAdapter(FreeCadContext(app=app, gui=gui))

    adapter.activate_document_view("Doc")

    gui.getDocument.assert_called_once_with("Doc")
    gui.activateView.assert_not_called()
    gui.getMainWindow.return_value.setActiveWindow.assert_called_once_with(view)


def test_activate_document_view_creates_missing_3d_view() -> None:
    """An open document without a GUI view gets a recreated view, matching a model-tree double-click."""
    app = MagicMock()
    created_view = object()
    gui = MagicMock()
    gui.getDocument.return_value.activeView.side_effect = [None, created_view]
    adapter = FreeCadPortAdapter(FreeCadContext(app=app, gui=gui))

    adapter.activate_document_view("Doc")

    app.setActiveDocument.assert_called_once_with("Doc")
    gui.activateView.assert_called_once_with("Gui::View3DInventor", True)
    gui.getMainWindow.return_value.setActiveWindow.assert_called_once_with(created_view)


def test_activate_document_view_reports_missing_view() -> None:
    """A document still without a GUI view after recreation cannot claim successful activation."""
    gui = MagicMock()
    gui.getDocument.return_value.activeView.side_effect = [None, None]
    adapter = FreeCadPortAdapter(FreeCadContext(app=MagicMock(), gui=gui))

    with pytest.raises(RuntimeError, match="has no activatable GUI view"):
        adapter.activate_document_view("Doc")
