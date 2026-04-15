# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Unit tests for set_refresh_callback in view mock.

These tests verify that the FakeDiffView correctly stores and invokes the
refresh callback when registered via set_refresh_callback.
"""

from unittest.mock import MagicMock

from tests.fakes.fake_diff_view import FakeDiffView


class TestFakeDiffViewSetRefreshCallback:
    """Tests for FakeDiffView.set_refresh_callback() method."""

    def test_set_refresh_callback_stores_callback(self) -> None:
        """set_refresh_callback() stores the provided callback."""
        # Arrange
        fake_view = FakeDiffView()
        mock_callback = MagicMock()

        # Act
        fake_view.set_refresh_callback(mock_callback)

        # Assert
        # Verify the callback is stored internally
        assert fake_view._refresh_callback is mock_callback

    def test_set_refresh_callback_records_method_call(self) -> None:
        """set_refresh_callback() records the method call for verification."""
        # Arrange
        fake_view = FakeDiffView()
        mock_callback = MagicMock()

        # Act
        fake_view.set_refresh_callback(mock_callback)

        # Assert
        calls = fake_view.get_calls()
        assert len(calls) == 1
        assert calls[0]["method"] == "set_refresh_callback"
        assert calls[0]["callback"] is mock_callback

    def test_trigger_refresh_invokes_callback(self) -> None:
        """trigger_refresh() invokes the registered callback."""
        # Arrange
        fake_view = FakeDiffView()
        mock_callback = MagicMock()
        fake_view.set_refresh_callback(mock_callback)

        # Act
        fake_view.trigger_refresh()

        # Assert
        mock_callback.assert_called_once()

    def test_trigger_refresh_without_callback_does_nothing(self) -> None:
        """trigger_refresh() does nothing when no callback is registered."""
        # Arrange
        fake_view = FakeDiffView()

        # Act & Assert - should not raise any exception
        fake_view.trigger_refresh()

    def test_trigger_refresh_multiple_times_invokes_callback_each_time(self) -> None:
        """trigger_refresh() invokes the callback on each call."""
        # Arrange
        fake_view = FakeDiffView()
        mock_callback = MagicMock()
        fake_view.set_refresh_callback(mock_callback)

        # Act
        fake_view.trigger_refresh()
        fake_view.trigger_refresh()
        fake_view.trigger_refresh()

        # Assert
        assert mock_callback.call_count == 3

    def test_set_refresh_callback_overwrites_previous_callback(self) -> None:
        """set_refresh_callback() overwrites any previously registered callback."""
        # Arrange
        fake_view = FakeDiffView()
        callback1 = MagicMock()
        callback2 = MagicMock()
        fake_view.set_refresh_callback(callback1)

        # Act
        fake_view.set_refresh_callback(callback2)

        # Assert
        assert fake_view._refresh_callback is callback2
        callback1.assert_not_called()
        callback2.assert_not_called()

        # Triggering refresh should only invoke the new callback
        fake_view.trigger_refresh()
        callback1.assert_not_called()
        callback2.assert_called_once()
