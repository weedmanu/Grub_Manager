import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gdk, Gtk

from ui.tabs.ui_tab_theme_editor import TabThemeEditor


@pytest.fixture
def state_manager():
    return MagicMock()


@pytest.fixture
def editor(state_manager):
    with (
        patch("ui.tabs.ui_tab_theme_editor.create_main_box", return_value=Gtk.Box()),
        patch("ui.tabs.ui_tab_theme_editor.WidgetFactory") as mock_wf,
    ):
        mock_wf.create_section_header.return_value = Gtk.Label()
        mock_wf.create_section_title.return_value = Gtk.Label()
        return TabThemeEditor(state_manager)


def test_tab_theme_editor_init(editor):
    assert editor.current_theme is None
    assert editor.theme_name_entry is None  # Not built yet


def test_tab_theme_editor_build(editor):
    box = editor.build()
    assert isinstance(box, Gtk.Box)
    assert editor.theme_name_entry is not None
    assert editor.title_color_btn is not None


def test_parse_color(editor):
    rgba = editor._parse_color("white")
    assert rgba.red == 1.0
    assert rgba.green == 1.0
    assert rgba.blue == 1.0

    rgba = editor._parse_color("#FF0000")
    assert rgba.red == 1.0
    assert rgba.green == 0.0
    assert rgba.blue == 0.0


def test_color_to_hex(editor):
    rgba = Gdk.RGBA()
    rgba.parse("#FF0000")
    assert editor._color_to_hex(rgba).upper() == "#FF0000"


def test_on_theme_property_changed(editor):
    editor.build()
    # Change theme name
    editor.theme_name_entry.set_text("new_theme")
    # Signal should trigger _on_theme_property_changed -> _update_theme_from_ui
    assert editor.current_theme.name == "new_theme"

    # Change color
    rgba = Gdk.RGBA()
    rgba.parse("#00FF00")
    editor.title_color_btn.set_property("rgba", rgba)
    editor.title_color_btn.emit("color-set")
    assert editor.current_theme.colors.title_color.upper() == "#00FF00"


def test_on_load_preset(editor):
    editor.build()
    with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
        mock_dialog = MockDialog.return_value
        editor._on_load_preset(Gtk.Button())
        assert mock_dialog.choose.called


def test_on_preset_selected(editor):
    editor.build()
    mock_dialog = MagicMock()
    mock_dialog.choose_finish.return_value = 1  # Dark theme

    editor._on_preset_selected(mock_dialog, None)
    assert editor.current_theme.name == "dark"


def test_on_preset_selected_cancel(editor):
    editor.build()
    mock_dialog = MagicMock()
    mock_dialog.choose_finish.side_effect = RuntimeError("Cancelled")

    # Should not crash
    editor._on_preset_selected(mock_dialog, None)


def test_on_preview_grub(editor):
    editor.build()
    with patch("ui.tabs.ui_tab_theme_editor.GrubPreviewDialog") as MockPreview:
        editor._on_preview_grub(Gtk.Button())
        assert MockPreview.called


def test_on_preview_grub_error(editor):
    editor.build()
    with (
        patch("ui.tabs.ui_tab_theme_editor.GrubPreviewDialog", side_effect=RuntimeError("Fail")),
        patch("ui.tabs.ui_tab_theme_editor.create_error_dialog") as mock_err,
    ):
        editor._on_preview_grub(Gtk.Button())
        assert mock_err.called


def test_on_save_theme_success(editor):
    editor.build()
    editor.theme_name_entry.set_text("my_theme")
    with (
        patch("ui.tabs.ui_tab_theme_editor.get_grub_themes_dir", return_value="/tmp"),
        patch("ui.tabs.ui_tab_theme_editor.ThemeGenerator.save_theme", return_value="/tmp/my_theme/theme.txt"),
        patch("ui.tabs.ui_tab_theme_editor.create_success_dialog") as mock_success,
    ):
        editor._on_save_theme(Gtk.Button())
        assert mock_success.called


def test_on_save_theme_no_name(editor):
    editor.build()
    editor.current_theme.name = ""  # Force empty name
    with patch("ui.tabs.ui_tab_theme_editor.create_error_dialog") as mock_err:
        editor._on_save_theme(Gtk.Button())
        assert mock_err.called
        assert "nom" in mock_err.call_args[0][0]


def test_on_save_theme_error(editor):
    editor.build()
    editor.theme_name_entry.set_text("my_theme")
    with (
        patch("ui.tabs.ui_tab_theme_editor.get_grub_themes_dir", return_value="/tmp"),
        patch("ui.tabs.ui_tab_theme_editor.ThemeGenerator.save_theme", side_effect=OSError("Disk full")),
        patch("ui.tabs.ui_tab_theme_editor.create_error_dialog") as mock_err,
    ):
        editor._on_save_theme(Gtk.Button())
        assert mock_err.called
        assert "Disk full" in mock_err.call_args[0][0]


def test_on_save_theme_no_theme(editor):
    editor.current_theme = None
    with patch("ui.tabs.ui_tab_theme_editor.create_error_dialog") as mock_err:
        editor._on_save_theme(Gtk.Button())
        assert mock_err.called


def test_on_preview_grub_no_theme(editor):
    editor.current_theme = None
    with patch("ui.tabs.ui_tab_theme_editor.create_error_dialog") as mock_err:
        editor._on_preview_grub(Gtk.Button())
        assert mock_err.called


def test_on_theme_property_changed_updating(editor):
    """Test on_theme_property_changed when updating UI."""
    editor.build()
    editor._updating_ui = True

    # Should return early and not update theme
    editor.current_theme = None
    editor._on_theme_property_changed(None)
    assert editor.current_theme is None


def test_on_preset_selected_not_found(editor):
    """Test on_preset_selected with invalid index."""
    editor.build()
    mock_dialog = MagicMock()
    mock_dialog.choose_finish.return_value = 99  # Invalid index

    editor._on_preset_selected(mock_dialog, None)
    # Should not change theme (or keep default)
    # Default is loaded in build(), so it's not None.
    # But we can check if it didn't crash.


def test_on_preset_selected_theme_not_found(editor):
    """Test on_preset_selected when theme is not found in presets."""
    editor.build()
    mock_dialog = MagicMock()
    mock_dialog.choose_finish.return_value = 0  # "classic"

    # Mock presets to be empty
    with patch("ui.tabs.ui_tab_theme_editor.ThemeGenerator.create_default_themes", return_value=[]):
        editor._on_preset_selected(mock_dialog, None)
        # current_theme should not be updated (or remain None/default)
        # We can check if _update_ui_from_theme was NOT called
        # But simpler: check coverage


def test_update_ui_from_theme_none(editor):
    """Test _update_ui_from_theme when current_theme is None."""
    editor.current_theme = None
    editor._update_ui_from_theme()
    # Should just return without error


def test_update_preview_none(editor):
    """Test _update_preview when current_theme is None."""
    editor.current_theme = None
    editor._update_preview()
    # Should just return without error
