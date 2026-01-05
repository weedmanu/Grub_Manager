import os
from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.services.core_grub_service import GrubConfig, MenuEntry
from core.models.core_theme_models import GrubTheme
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"


def test_grub_preview_dialog_fallback():
    theme_obj = GrubTheme(name="test_theme")
    dialog = GrubPreviewDialog(theme_obj, model=None)

    with (
        patch("core.services.core_grub_service.GrubService.read_current_config", side_effect=OSError("Error")),
        patch("core.services.core_grub_service.GrubService.get_menu_entries", side_effect=RuntimeError("Error")),
    ):

        # Should not crash and use fallback
        dialog.show()


@pytest.fixture
def theme():
    t = MagicMock(spec=GrubTheme)
    t.name = "TestTheme"
    t.colors = MagicMock()
    t.colors.menu_normal_fg = "white"
    t.colors.menu_highlight_fg = "black"
    t.colors.menu_highlight_bg = "white"
    t.layout = MagicMock()
    t.layout.menu_top = "20%"
    t.layout.menu_left = "10%"
    t.layout.menu_width = "80%"
    t.image = MagicMock()
    t.image.desktop_image = ""
    return t


def test_grub_preview_dialog_init(theme):
    dialog = GrubPreviewDialog(theme)
    assert dialog.theme == theme
    assert dialog.theme_name == "TestTheme"


def test_grub_preview_dialog_show(theme):
    dialog = GrubPreviewDialog(theme)

    with (
        patch("ui.tabs.ui_grub_preview_dialog.Gtk.Window") as mock_window_class,
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.read_current_config") as mock_read,
        patch("ui.tabs.ui_grub_preview_dialog.GrubService.get_menu_entries"),
    ):
        mock_read.return_value.timeout = 10
        mock_read.return_value.default_entry = "0"
        mock_read.return_value.grub_gfxmode = "auto"

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
