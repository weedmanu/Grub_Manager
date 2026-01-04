import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import patch

from core.services.core_grub_service import GrubConfig, MenuEntry
from core.theme.core_theme_generator import GrubTheme
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog


def test_grub_preview_dialog_fallback():
    theme = GrubTheme(name="test_theme")
    dialog = GrubPreviewDialog(theme)

    with (
        patch("core.services.core_grub_service.GrubService.read_current_config", side_effect=OSError("Error")),
        patch("core.services.core_grub_service.GrubService.get_menu_entries", side_effect=RuntimeError("Error")),
    ):

        # Should not crash and use fallback
        dialog.show()


import os
from unittest.mock import MagicMock

import pytest
from gi.repository import Gtk

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"


@pytest.fixture
def theme():
    t = MagicMock(spec=GrubTheme)
    t.name = "TestTheme"
    t.grub_timeout = 10
    return t


def test_grub_preview_dialog_init(theme):
    dialog = GrubPreviewDialog(theme)
    assert dialog.theme == theme
    assert dialog.theme_name == "TestTheme"


def test_grub_preview_dialog_show(theme):
    dialog = GrubPreviewDialog(theme)

    with (
        patch("ui.tabs.ui_grub_preview_dialog.Gtk.Window") as mock_window_class,
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config"),
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries"),
    ):

        mock_window = mock_window_class.return_value
        dialog.show()

        assert mock_window.present.called
        assert mock_window.set_title.called


def test_create_grub_preview_success(theme):
    dialog = GrubPreviewDialog(theme)
    container = Gtk.Box()

    config = GrubConfig()
    config.default_entry = "1 > 2"
    config.timeout = 5
    config.grub_gfxmode = "auto"
    config.grub_color_normal = "white/black"

    entries = [MenuEntry(title="Ubuntu", id="u"), MenuEntry(title="Windows", id="w")]

    with (
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config", return_value=config),
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries", return_value=entries),
    ):
        dialog._create_grub_preview(container)

    # Check if widgets were added
    assert container.get_first_child() is not None


def test_create_grub_preview_exception(theme):
    dialog = GrubPreviewDialog(theme)
    container = Gtk.Box()

    with (
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config", side_effect=OSError("Boom")),
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries", side_effect=OSError("Boom")),
    ):
        dialog._create_grub_preview(container)

    assert container.get_first_child() is not None


def test_create_grub_preview_no_default_entry(theme):
    dialog = GrubPreviewDialog(theme)
    container = Gtk.Box()

    config = GrubConfig()
    config.default_entry = ""

    with (
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config", return_value=config),
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries", return_value=[]),
    ):
        dialog._create_grub_preview(container)

    assert container.get_first_child() is not None


def test_create_grub_preview_no_timeout_on_theme(theme):
    del theme.grub_timeout
    dialog = GrubPreviewDialog(theme)
    container = Gtk.Box()

    config = GrubConfig()
    config.timeout = 5

    with (
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config", return_value=config),
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries", return_value=[]),
    ):
        dialog._create_grub_preview(container)

    assert container.get_first_child() is not None
