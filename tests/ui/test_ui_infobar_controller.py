"""Tests pour InfoBarController."""

from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.ui_controllers_infobar import ERROR, INFO, WARNING, InfoBarController


@pytest.fixture
def mock_widgets():
    revealer = MagicMock()
    box = MagicMock()
    label = MagicMock()
    return revealer, box, label


def test_infobar_show_basic(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)

    with patch("gi.repository.GLib.timeout_add_seconds") as mock_timeout:
        controller.show("Test message", INFO)

        label.set_text.assert_called_once_with("Test message")
        box.add_css_class.assert_called_with(INFO)
        revealer.set_reveal_child.assert_called_once_with(True)
        mock_timeout.assert_called_once()


def test_infobar_show_error(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)

    with patch("gi.repository.GLib.timeout_add_seconds"):
        controller.show("Error message", ERROR)
        box.add_css_class.assert_called_with(ERROR)


def test_infobar_css_cleanup(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)

    box.has_css_class.side_effect = lambda c: c == INFO

    with patch("gi.repository.GLib.timeout_add_seconds"):
        controller.show("Warning message", WARNING)
        box.remove_css_class.assert_called_with(INFO)
        box.add_css_class.assert_called_with(WARNING)


def test_infobar_timeout_cancellation(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)

    with (
        patch("gi.repository.GLib.timeout_add_seconds") as mock_timeout,
        patch("gi.repository.GLib.source_remove") as mock_remove,
    ):

        mock_timeout.return_value = 123
        controller.show("First")
        assert controller._timeout_id == 123

        controller.show("Second")
        mock_remove.assert_called_once_with(123)


def test_infobar_hide_callback(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)
    controller._timeout_id = 123

    result = controller.hide_info_callback()

    revealer.set_reveal_child.assert_called_once_with(False)
    assert controller._timeout_id == 0
    assert result is False


def test_infobar_missing_label(mock_widgets):
    revealer, box, _ = mock_widgets
    controller = InfoBarController(revealer, box, None)

    controller.show("Message")
    revealer.set_reveal_child.assert_not_called()


def test_infobar_show_without_box(mock_widgets):
    revealer, _box, label = mock_widgets
    controller = InfoBarController(revealer, None, label)

    with patch("gi.repository.GLib.timeout_add_seconds") as mock_timeout:
        controller.show("Hello", INFO)

        label.set_text.assert_called_once_with("Hello")
        revealer.set_reveal_child.assert_called_once_with(True)
        mock_timeout.assert_called_once()


def test_infobar_show_invalid_type_does_not_add_css_class(mock_widgets):
    revealer, box, label = mock_widgets
    controller = InfoBarController(revealer, box, label)

    with patch("gi.repository.GLib.timeout_add_seconds"):
        controller.show("Hello", "not-a-type")

        box.add_css_class.assert_not_called()


def test_infobar_show_without_revealer_does_not_schedule_timeout(mock_widgets):
    _revealer, box, label = mock_widgets
    controller = InfoBarController(None, box, label)

    with patch("gi.repository.GLib.timeout_add_seconds") as mock_timeout:
        controller.show("Hello", INFO)

        mock_timeout.assert_not_called()


def test_infobar_hide_callback_without_revealer(mock_widgets):
    _revealer, box, label = mock_widgets
    controller = InfoBarController(None, box, label)
    controller._timeout_id = 123

    result = controller.hide_info_callback()

    assert controller._timeout_id == 0
    assert result is False
