# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for opening one missing document for working-tree comparison.
"""Unit tests for OpenDocumentAction."""

from freecad.history_wb.application.actions.open_document import OpenDocumentAction
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
