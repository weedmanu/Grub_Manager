"""Tests pour TabThemeConfig (nouvelle UX).

La nouvelle UX a scindé l'ancien onglet en 2 onglets:
- "Thèmes" (sélection + actions via theme.txt)
- "Apparence" (configuration simple + scripts)

On évite de créer/afficher des dialogues GTK réels dans ces tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.models.core_models_grub_ui import GrubUiModel, GrubUiState
from core.models.core_models_theme import GrubTheme
from core.services.core_services_grub_script import GrubScriptService
from core.services.core_services_theme import ThemeService
from core.theme.core_theme_active_manager import ActiveThemeManager
from ui.tabs.theme_config import ui_tabs_theme_config_handlers as handlers
from ui.tabs.ui_tabs_theme_config import TabThemeConfig


@pytest.fixture
def mock_state_manager() -> MagicMock:
    sm = MagicMock()
    sm.state_data = GrubUiState(
        model=GrubUiModel(
            timeout=5,
            default="0",
            theme_management_enabled=True,
            grub_background="",
            grub_color_normal="",
            grub_color_highlight="",
            grub_theme="",
        ),
        entries=[],
        raw_config={},
    )
    sm.is_loading.return_value = False
    sm.get_model.return_value = sm.state_data.model
    sm.get_state.return_value = sm.state_data
    sm.update_model = MagicMock()
    return sm


@pytest.fixture
def tab_theme_config(mock_state_manager: MagicMock) -> TabThemeConfig:
    tab = TabThemeConfig(mock_state_manager)
    tab.services.theme_service = MagicMock(spec=ThemeService)
    tab.services.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.services.script_service = MagicMock(spec=GrubScriptService)
    return tab


def test_build_theme_tab_creates_list_and_actions(tab_theme_config: TabThemeConfig) -> None:
    with patch.object(tab_theme_config, "load_themes") as mock_load:
        box = tab_theme_config.build_theme_tab()

    assert isinstance(box, Gtk.Box)
    assert mock_load.called
    assert tab_theme_config.widgets.panels.theme_list_box is not None
    assert tab_theme_config.widgets.actions.preview_btn is not None
    # L'onglet "Thèmes" ne construit pas la section scripts
    assert tab_theme_config.widgets.panels.scripts_list is None


def test_build_appearance_tab_creates_simple_panel_and_scripts(tab_theme_config: TabThemeConfig) -> None:
    with patch.object(tab_theme_config, "load_themes") as mock_load:
        box = tab_theme_config.build_grub_scripts_tab()

    assert isinstance(box, Gtk.Box)
    assert mock_load.called
    assert tab_theme_config.widgets.panels.simple_config_panel is not None
    assert tab_theme_config.widgets.panels.scripts_list is not None


def test_scan_system_themes_adds_none_and_rows(tab_theme_config: TabThemeConfig) -> None:
    tab_theme_config.build_theme_tab()

    with patch.object(tab_theme_config.services.theme_service, "scan_system_themes", return_value={}):
        tab_theme_config.scan_system_themes()

    assert "Aucun (GRUB par défaut)" in tab_theme_config.data.available_themes
    assert tab_theme_config.widgets.panels.theme_list_box.get_first_child() is not None


def test_load_themes_sets_current_theme_and_refreshes(tab_theme_config: TabThemeConfig) -> None:
    tab_theme_config.build_theme_tab()
    tab_theme_config.refresh = MagicMock()

    mock_theme = GrubTheme(name="MyTheme")
    with patch.object(tab_theme_config.services.theme_manager, "load_active_theme", return_value=mock_theme):
        tab_theme_config.load_themes()

    assert tab_theme_config.data.current_theme == mock_theme
    assert tab_theme_config.refresh.called


def test_on_preview_theme_exception_shows_error_dialog(tab_theme_config: TabThemeConfig) -> None:
    tab_theme_config.data.current_theme = GrubTheme(name="MyTheme")
    tab_theme_config.data.theme_paths["MyTheme"] = Path("/tmp")

    with (
        patch.object(handlers, "GrubPreviewDialog") as MockDialog,
        patch.object(handlers, "create_error_dialog") as mock_error,
    ):
        MockDialog.return_value.show.side_effect = RuntimeError("boom")
        handlers.on_preview_theme(tab_theme_config)
        assert mock_error.called
