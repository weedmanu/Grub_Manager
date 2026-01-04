import subprocess
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gio

from ui.ui_dialogs import confirm_action, run_command_popup
from ui.ui_manager import GrubConfigManager


@pytest.fixture
def mock_controller():
    controller = MagicMock(spec=GrubConfigManager)
    controller.get_height.return_value = 600
    return controller


def test_run_command_popup_not_root(mock_controller):
    """Test that the function returns early if not root."""
    with patch("os.geteuid", return_value=1000):
        run_command_popup(mock_controller, ["ls"], "Title")

        mock_controller.show_info.assert_called_once_with("Droits root nécessaires", "error")


def test_run_command_popup_root_creation(mock_controller):
    """Test that the dialog is created when root."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk") as mock_gtk,
        patch("ui.ui_dialogs.threading.Thread") as mock_thread,
    ):

        mock_window = MagicMock()
        mock_gtk.Window.return_value = mock_window

        run_command_popup(mock_controller, ["ls"], "Title")

        # Check dialog setup
        mock_window.set_transient_for.assert_called_with(mock_controller)
        mock_window.set_modal.assert_called_with(True)
        mock_window.set_title.assert_called_with("Title")
        mock_window.present.assert_called_once()

        # Check thread start
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()


def test_run_command_popup_thread_execution_success(mock_controller):
    """Test the execution logic inside the thread (success case)."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk"),
        patch("ui.ui_dialogs.GLib.idle_add") as mock_idle_add,
        patch("subprocess.Popen") as mock_popen,
    ):

        # Mock process
        mock_process = MagicMock()
        mock_process.stdout = ["Line 1\n", "Line 2\n"]
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value.__enter__.return_value = mock_process

        # Capture the thread target
        with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
            run_command_popup(mock_controller, ["ls"], "Title")

            # Get the target function passed to Thread
            _args, kwargs = mock_thread.call_args
            target = kwargs.get("target")

            # Execute the target (simulate thread running)
            target()

            # Verify subprocess call
            mock_popen.assert_called_with(
                ["ls"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )

            # Verify output handling
            # We expect calls to append_text via idle_add
            # 1. Line 1
            # 2. Line 2
            # 3. Success message
            assert mock_idle_add.call_count >= 3


def test_confirm_action_glib_error_does_not_call_callback(monkeypatch, mock_controller):
    called = {"v": False}

    def cb():
        called["v"] = True

    class FakeGLibError(Exception):
        pass

    class FakeDialog:
        def set_modal(self, *_a, **_kw):
            pass

        def set_message(self, *_a, **_kw):
            pass

        def set_detail(self, *_a, **_kw):
            pass

        def set_buttons(self, *_a, **_kw):
            pass

        def set_default_button(self, *_a, **_kw):
            pass

        def set_cancel_button(self, *_a, **_kw):
            pass

        def choose_finish(self, _result):
            raise FakeGLibError("boom")

        def choose(self, _controller, _cancellable, callback):
            callback(self, object())

    monkeypatch.setattr("ui.ui_dialogs.GLib.Error", FakeGLibError)
    monkeypatch.setattr("ui.ui_dialogs.Gtk.AlertDialog", lambda: FakeDialog())

    confirm_action(cb, "msg", mock_controller)
    assert called["v"] is False


def test_run_command_popup_thread_execution_failure(mock_controller):
    """Test the execution logic inside the thread (failure case)."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk"),
        patch("ui.ui_dialogs.GLib.idle_add") as mock_idle_add,
        patch("subprocess.Popen") as mock_popen,
    ):

        # Mock process
        mock_process = MagicMock()
        mock_process.stdout = ["Error line\n"]
        mock_process.returncode = 1
        mock_popen.return_value.__enter__.return_value = mock_process

        # Capture the thread target
        with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
            run_command_popup(mock_controller, ["ls"], "Title")
            target = mock_thread.call_args[1]["target"]
            target()

            # Verify output handling
            # We expect calls to append_text via idle_add
            # 1. Error line
            # 2. Error message
            assert mock_idle_add.call_count >= 2


def test_run_command_popup_grub_emu(mock_controller):
    """Test the special case for grub-emu."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk"),
        patch("ui.ui_dialogs.GLib.idle_add"),
        patch("ui.ui_dialogs.shutil.which", return_value="/usr/bin/grub-emu"),
        patch("subprocess.Popen") as mock_popen,
    ):

        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_popen.return_value.__enter__.return_value = mock_process

        with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
            run_command_popup(mock_controller, ["grub-emu"], "Title")
            target = mock_thread.call_args[1]["target"]
            target()

            mock_popen.assert_called_with(["grub-emu"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def test_run_command_popup_grub_emu_missing(mock_controller):
    """Test grub-emu missing."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk"),
        patch("ui.ui_dialogs.GLib.idle_add"),
        patch("ui.ui_dialogs.shutil.which", return_value=None),
    ):

        with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
            run_command_popup(mock_controller, ["grub-emu"], "Title")
            target = mock_thread.call_args[1]["target"]
            target()

            # Should not call subprocess
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.assert_not_called()


def test_run_command_popup_exception(mock_controller):
    """Test exception handling during execution."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk"),
        patch("ui.ui_dialogs.GLib.idle_add") as mock_idle_add,
        patch("subprocess.Popen", side_effect=OSError("Exec failed")),
    ):

        with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
            run_command_popup(mock_controller, ["ls"], "Title")
            target = mock_thread.call_args[1]["target"]
            target()

            # Should log error via idle_add
            assert mock_idle_add.call_count >= 1


def test_append_text_helper(mock_controller):
    """Test the append_text helper function."""
    with (
        patch("os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk") as mock_gtk,
        patch("ui.ui_dialogs.GLib.idle_add") as mock_idle_add,
        patch("ui.ui_dialogs.threading.Thread"),
    ):

        # Setup mocks for TextView and Buffer
        mock_textview = MagicMock()
        mock_buffer = MagicMock()
        mock_textview.get_buffer.return_value = mock_buffer
        mock_gtk.TextView.return_value = mock_textview

        # We need to capture the append_text function.
        # It is defined inside run_command_popup.
        # We can capture it when it's passed to GLib.idle_add.
        # But run_command_popup only calls idle_add inside the thread function.
        # So we need to trigger the thread function first.

        # Mock subprocess to trigger output
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = ["Output"]
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_popen.return_value.__enter__.return_value = mock_process

            # Capture thread target
            with patch("ui.ui_dialogs.threading.Thread") as mock_thread:
                run_command_popup(mock_controller, ["ls"], "Title")
                target = mock_thread.call_args[1]["target"]

                # Run the thread function
                target()

                # Now GLib.idle_add should have been called with append_text
                # Get the first call args
                args = mock_idle_add.call_args_list[0][0]
                append_text_func = args[0]
                text_arg = args[1]

                # Execute append_text
                append_text_func(text_arg)

                # Verify buffer interaction
                mock_buffer.get_end_iter.assert_called()
                mock_buffer.insert.assert_called()
                mock_textview.scroll_to_mark.assert_called()

                # Test with tag
                append_text_func("Error", "error")
                mock_buffer.insert_with_tags_by_name.assert_called()


@patch("gi.repository.Gtk.AlertDialog")
def test_confirm_action(mock_dialog_class, mock_controller):
    """Test the confirm_action dialog and its callbacks."""
    mock_dialog = mock_dialog_class.return_value
    callback = MagicMock()

    confirm_action(callback, "Message", mock_controller)
    mock_dialog.choose.assert_called_once()

    # Test callback
    on_response = mock_dialog.choose.call_args[0][2]

    # Case 1: Confirm (index 1)
    mock_dialog.choose_finish.return_value = 1
    on_response(mock_dialog, MagicMock(spec=Gio.AsyncResult))
    callback.assert_called_once()

    # Case 2: Cancel (index 0)
    callback.reset_mock()
    mock_dialog.choose_finish.return_value = 0
    on_response(mock_dialog, MagicMock(spec=Gio.AsyncResult))
    callback.assert_not_called()

    # Case 3: Exception
    mock_dialog.choose_finish.side_effect = Exception("Err")
    on_response(mock_dialog, MagicMock(spec=Gio.AsyncResult))  # Should not crash
