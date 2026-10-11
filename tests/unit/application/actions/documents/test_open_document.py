# File responsibility: Tests for opening documents with optional GUI view activation.
"""Unit tests for OpenDocumentAction."""

import pytest

from freecad.history_wb.application.actions.documents.open_document import OpenDocumentAction
from tests.fakes.fake_freecad_port import FakeFreeCadPort, MockDocument


def test_execute_opens_document() -> None:
    previous = MockDocument(file_name="/home/user/dir/repo/active.FCStd", name="ActiveDoc")
    port = FakeFreeCadPort(active_document=previous)
    action = OpenDocumentAction(port)

    result = action.execute("/home/user/dir/repo/parts/A.FCStd")

    assert result.is_success is True
    assert port.opened_document_paths == ["/home/user/dir/repo/parts/A.FCStd"]
    assert port.active_document_names == []


def test_execute_opens_document_without_active_document_restore() -> None:
    port = FakeFreeCadPort(active_document=None)
    action = OpenDocumentAction(port)

    result = action.execute("/home/user/dir/repo/parts/A.FCStd")

    assert result.is_success is True
    assert port.opened_document_paths == ["/home/user/dir/repo/parts/A.FCStd"]
    assert port.active_document_names == []


@pytest.mark.parametrize("activate_view", [False, True])
def test_execute_activates_document_view_only_when_requested(activate_view: bool) -> None:
    """Opening for comparison leaves navigation alone; explicit opening activates the document view."""
    port = FakeFreeCadPort()

    result = OpenDocumentAction(port).execute("/home/user/dir/repo/parts/A.FCStd", activate_view=activate_view)

    assert result.is_success
    assert port.activated_view_document_names == (["A"] if activate_view else [])
