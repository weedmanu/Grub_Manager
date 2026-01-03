import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import patch

from core.services.core_grub_service import GrubConfig, MenuEntry
from core.theme.core_theme_generator import GrubTheme
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog


def test_grub_preview_dialog_init():
    theme = GrubTheme(name="test_theme")
    dialog = GrubPreviewDialog(theme)
    assert dialog.theme == theme
    assert dialog.theme_name == "test_theme"


def test_grub_preview_dialog_show():
    theme = GrubTheme(name="test_theme")
    dialog = GrubPreviewDialog(theme)

    with (
        patch("core.services.core_grub_service.GrubService.read_current_config") as mock_read,
        patch("core.services.core_grub_service.GrubService.get_menu_entries") as mock_entries,
    ):

        mock_read.return_value = GrubConfig()
        mock_entries.return_value = [MenuEntry(title="Test OS 1", id="test1"), MenuEntry(title="Test OS 2", id="test2")]

        # show() calls _create_grub_preview which calls the mocked services
        dialog.show()

        # We can't easily check the window content without a main loop
        # but we can verify the mocks were called
        mock_read.assert_called_once()
        mock_entries.assert_called_once()


def test_grub_preview_dialog_fallback():
    theme = GrubTheme(name="test_theme")
    dialog = GrubPreviewDialog(theme)

    with (
        patch("core.services.core_grub_service.GrubService.read_current_config", side_effect=OSError("Error")),
        patch("core.services.core_grub_service.GrubService.get_menu_entries", side_effect=RuntimeError("Error")),
    ):

        # Should not crash and use fallback
        dialog.show()
