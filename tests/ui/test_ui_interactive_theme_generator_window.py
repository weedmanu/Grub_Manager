import pytest
from unittest.mock import MagicMock, patch
from gi.repository import Gtk
from ui.dialogs.ui_interactive_theme_generator_window import (
    InteractiveThemeGeneratorWindow
)

@pytest.fixture
def mock_generator():
    with patch("ui.dialogs.ui_interactive_theme_generator_window.ThemeGenerator") as mock:
        instance = mock.return_value
        instance.create_theme_package.return_value = {"theme.txt": "content"}
        yield instance

def test_interactive_theme_generator_window_init():
    parent = MagicMock(spec=Gtk.Window)
    win = InteractiveThemeGeneratorWindow(parent_window=parent)
    assert win.get_title() == "Générateur de Thème GRUB Interactif"
    assert win.get_modal() is True

def test_interactive_theme_generator_window_on_theme_updated():
    win = InteractiveThemeGeneratorWindow()
    # Just call it to cover the line
    win._on_theme_updated()

def test_interactive_theme_generator_window_create_success(mock_generator):
    on_created = MagicMock()
    win = InteractiveThemeGeneratorWindow(on_theme_created=on_created)
    
    # Mock the Gtk module used in the window
    with patch("ui.dialogs.ui_interactive_theme_generator_window.Gtk") as mock_gtk:
        mock_gtk.ResponseType.OK = Gtk.ResponseType.OK
        mock_gtk.ResponseType.CANCEL = Gtk.ResponseType.CANCEL
        
        mock_dialog = mock_gtk.Dialog.return_value
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        
        mock_entry = mock_gtk.Entry.return_value
        mock_entry.get_text.return_value = "My Custom Theme"
        
        win._on_create_theme(None)
        
        assert mock_generator.create_theme_package.called
        on_created.assert_called_with("My Custom Theme", {"theme.txt": "content"})
        assert mock_gtk.MessageDialog.called

def test_interactive_theme_generator_window_create_cancel(mock_generator):
    win = InteractiveThemeGeneratorWindow()
    with patch("ui.dialogs.ui_interactive_theme_generator_window.Gtk") as mock_gtk:
        mock_gtk.ResponseType.CANCEL = Gtk.ResponseType.CANCEL
        mock_dialog = mock_gtk.Dialog.return_value
        mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
        
        win._on_create_theme(None)
        assert not mock_generator.create_theme_package.called

def test_interactive_theme_generator_window_create_error(mock_generator):
    win = InteractiveThemeGeneratorWindow()
    mock_generator.create_theme_package.side_effect = RuntimeError("Create failed")
    
    with patch("ui.dialogs.ui_interactive_theme_generator_window.Gtk") as mock_gtk:
        mock_gtk.ResponseType.OK = Gtk.ResponseType.OK
        mock_dialog = mock_gtk.Dialog.return_value
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        
        win._on_create_theme(None)
        # Should show error dialog
        assert mock_gtk.MessageDialog.called

def test_interactive_theme_generator_window_close():
    win = InteractiveThemeGeneratorWindow()
    assert win._on_close(None) is False

def test_interactive_theme_generator_window_create_success_no_callback(mock_generator):
    win = InteractiveThemeGeneratorWindow(on_theme_created=None)
    with patch("ui.dialogs.ui_interactive_theme_generator_window.Gtk") as mock_gtk:
        mock_gtk.ResponseType.OK = Gtk.ResponseType.OK
        mock_dialog = mock_gtk.Dialog.return_value
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_entry = mock_gtk.Entry.return_value
        mock_entry.get_text.return_value = "Theme"
        
        win._on_create_theme(None)
        assert mock_generator.create_theme_package.called
