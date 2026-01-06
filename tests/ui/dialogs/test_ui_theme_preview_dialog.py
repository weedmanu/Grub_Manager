"""Tests pour GrubPreviewDialog - architecture SOLID modulaire."""

import os
from unittest.mock import MagicMock

import gi
import pytest

gi.require_version("Gtk", "4.0")

from core.models.core_models_theme import GrubTheme
from ui.dialogs.preview.ui_dialogs_preview_grub_parsers import GrubConfigParser
from ui.dialogs.ui_dialogs_theme_preview import GrubThemePreviewDialog as GrubPreviewDialog
from ui.dialogs.ui_dialogs_theme_preview import compute_text_mode_metrics

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"


def test_parse_grub_cfg_menu_colors_parses_fg_bg_pairs() -> None:
    """Test parsing des couleurs menu GRUB depuis grub.cfg."""
    parser = GrubConfigParser()
    colors = parser.parse_grub_cfg_menu_colors(
        [
            "set menu_color_normal=white/black",
            "set menu_color_highlight=black/light-gray",
        ]
    )
    assert colors is not None
    assert colors.normal_fg == "white"
    assert colors.normal_bg == "black"
    assert colors.highlight_fg == "black"
    # light-gray est mappé vers un gris clair CSS
    assert colors.highlight_bg in ("#D3D3D3", "light-gray")


@pytest.fixture
def theme():
    """Fixture: thème de test."""
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
    """Test initialisation GrubPreviewDialog."""
    dialog = GrubPreviewDialog(theme)
    assert dialog.theme == theme
    assert dialog.theme_name == "TestTheme"


def test_compute_text_mode_metrics_scales_with_size() -> None:
    small = compute_text_mode_metrics(width=800, height=600)
    large = compute_text_mode_metrics(width=1600, height=1200)

    assert large["outer_margin"] > small["outer_margin"]
    assert large["inner_pad_x"] > small["inner_pad_x"]
    assert large["inner_pad_y"] > small["inner_pad_y"]
