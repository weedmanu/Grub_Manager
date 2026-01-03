
import pytest
from unittest.mock import MagicMock, patch
from gi.repository import Gtk, GLib, Gio
import os
import subprocess
import threading
import time

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.ui_dialogs import run_command_popup, confirm_action

@pytest.fixture
def controller():
    c = MagicMock(spec=Gtk.Window)
    c.show_info = MagicMock()
    c.get_height = MagicMock(return_value=600)
    return c

def test_run_command_popup_no_root(controller):
    with patch("os.geteuid", return_value=1000), \
         patch("ui.ui_dialogs.Gtk.Window"):
        run_command_popup(controller, ["ls"], "Title")
        controller.show_info.assert_called_with("Droits root nécessaires", "error")

def test_run_command_popup_success(controller):
    with patch("os.geteuid", return_value=0), \
         patch("ui.ui_dialogs.Gtk.Window") as mock_window_class, \
         patch("subprocess.Popen") as mock_popen, \
         patch("threading.Thread") as mock_thread_class:
        
        # Mock dialog
        mock_dialog = mock_window_class.return_value
        
        # Mock process
        mock_process = mock_popen.return_value.__enter__.return_value
        mock_process.stdout = ["line1\n", "line2\n"]
        mock_process.returncode = 0
        
        # Mock thread to run target immediately
        def mock_start_side_effect(*args, **kwargs):
            target = mock_thread_class.call_args[1]['target']
            target()
        mock_thread_class.return_value.start.side_effect = mock_start_side_effect
        
        # Mock GLib.idle_add to run callback immediately
        with patch("gi.repository.GLib.idle_add", side_effect=lambda f, *args: f(*args)):
            run_command_popup(controller, ["ls"], "Title")
            
        assert mock_popen.called

def test_run_command_popup_error_code(controller):
    with patch("os.geteuid", return_value=0), \
         patch("ui.ui_dialogs.Gtk.Window"), \
         patch("subprocess.Popen") as mock_popen, \
         patch("threading.Thread") as mock_thread_class:
        
        mock_process = mock_popen.return_value.__enter__.return_value
        mock_process.stdout = ["error line\n"]
        mock_process.returncode = 1
        
        def mock_start_side_effect(*args, **kwargs):
            target = mock_thread_class.call_args[1]['target']
            target()
        mock_thread_class.return_value.start.side_effect = mock_start_side_effect
        
        with patch("gi.repository.GLib.idle_add", side_effect=lambda f, *args: f(*args)):
            run_command_popup(controller, ["ls"], "Title")
            
        assert mock_popen.called

def test_run_command_popup_grub_emu_success(controller):
    with patch("os.geteuid", return_value=0), \
         patch("ui.ui_dialogs.Gtk.Window"), \
         patch("shutil.which", return_value="/usr/bin/grub-emu"), \
         patch("subprocess.Popen") as mock_popen, \
         patch("threading.Thread") as mock_thread_class:
        
        mock_process = mock_popen.return_value.__enter__.return_value
        mock_process.wait.return_value = 0
        
        def mock_start_side_effect(*args, **kwargs):
            target = mock_thread_class.call_args[1]['target']
            target()
        mock_thread_class.return_value.start.side_effect = mock_start_side_effect
        
        with patch("gi.repository.GLib.idle_add", side_effect=lambda f, *args: f(*args)):
            run_command_popup(controller, ["grub-emu"], "Title")
            
        assert mock_popen.called

def test_run_command_popup_grub_emu_not_installed(controller):
    with patch("os.geteuid", return_value=0), \
         patch("ui.ui_dialogs.Gtk.Window"), \
         patch("shutil.which", return_value=None), \
         patch("threading.Thread") as mock_thread_class:
        
        def mock_start_side_effect(*args, **kwargs):
            target = mock_thread_class.call_args[1]['target']
            target()
        mock_thread_class.return_value.start.side_effect = mock_start_side_effect
        
        with patch("gi.repository.GLib.idle_add", side_effect=lambda f, *args: f(*args)):
            run_command_popup(controller, ["grub-emu"], "Title")
            
        # Should have called idle_add with error message

def test_run_command_popup_exception(controller):
    with patch("os.geteuid", return_value=0), \
         patch("ui.ui_dialogs.Gtk.Window"), \
         patch("subprocess.Popen", side_effect=OSError("Boom")), \
         patch("threading.Thread") as mock_thread_class:
        
        def mock_start_side_effect(*args, **kwargs):
            target = mock_thread_class.call_args[1]['target']
            target()
        mock_thread_class.return_value.start.side_effect = mock_start_side_effect
        
        with patch("gi.repository.GLib.idle_add", side_effect=lambda f, *args: f(*args)):
            run_command_popup(controller, ["ls"], "Title")

@patch("gi.repository.Gtk.AlertDialog")
def test_confirm_action(mock_dialog_class, controller):
    mock_dialog = mock_dialog_class.return_value
    callback = MagicMock()
    
    confirm_action(callback, "Message", controller)
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
    on_response(mock_dialog, MagicMock(spec=Gio.AsyncResult)) # Should not crash
