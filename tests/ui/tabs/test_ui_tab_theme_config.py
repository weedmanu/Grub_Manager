"""Tests pour l'onglet Configuration du thème."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_grub_script_service import GrubScriptService
from core.services.core_theme_service import ThemeService
from core.theme.core_active_theme_manager import ActiveThemeManager
from core.models.core_theme_models import GrubTheme
from ui.components.ui_theme_scripts_list import ThemeScriptsList
from ui.tabs.theme_config.ui_theme_config_handlers import (
    on_delete_confirmed,
    on_delete_theme,
    on_edit_theme,
    on_open_editor,
    on_preview_theme,
    on_theme_selected,
    on_theme_switch_toggled,
)
from ui.tabs.ui_tab_theme_config import TabThemeConfig
from ui.ui_state import AppStateManager


@pytest.fixture
def mock_state_manager():
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    sm = MagicMock()
    sm.state_data = GrubUiState(
        model=GrubUiModel(
            timeout=5,
            default="0",
            theme_management_enabled=True,
            grub_background="",
            grub_color_normal="",
            grub_color_highlight="",
            grub_theme=""
        ),
        entries=[],
        raw_config={}
    )
    sm.is_loading.return_value = False  # Important for _on_theme_switch_toggled
    sm.get_model.return_value = sm.state_data.model
    sm.get_state.return_value = sm.state_data
    return sm


@pytest.fixture
def mock_state_manager_disabled():
    """Fixture avec theme_management_enabled=False pour les tests désactivés."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    sm = MagicMock()
    sm.state_data = GrubUiState(
        model=GrubUiModel(
            timeout=5,
            default="0",
            theme_management_enabled=False,
            grub_background="",
            grub_color_normal="",
            grub_color_highlight="",
            grub_theme=""
        ),
        entries=[],
        raw_config={}
    )
    sm.is_loading.return_value = False
    sm.get_model.return_value = sm.state_data.model
    sm.get_state.return_value = sm.state_data
    return sm


@pytest.fixture
def tab_theme_config(mock_state_manager):
    tab = TabThemeConfig(mock_state_manager)
    tab.services.theme_service = MagicMock(spec=ThemeService)
    tab.services.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.services.script_service = MagicMock(spec=GrubScriptService)
    return tab


def test_init(tab_theme_config):
    """Test l'initialisation."""
    assert tab_theme_config.data.current_theme is None
    assert tab_theme_config.data.available_themes == {}


def test_build(tab_theme_config):
    """Test la construction de l'interface."""
    with patch.object(tab_theme_config, "load_themes") as mock_load:
        box = tab_theme_config.build()
        assert isinstance(box, Gtk.Box)
        assert mock_load.called
        assert tab_theme_config.widgets.panels.theme_list_box is not None
        assert tab_theme_config.widgets.actions.preview_btn is not None
        assert tab_theme_config.widgets.panels.theme_switch is not None


def test_load_themes_active(tab_theme_config):
    """Test le chargement des thèmes avec un thème actif."""
    mock_theme = GrubTheme(name="MyTheme")

    with (
        patch.object(tab_theme_config.services.theme_manager, "load_active_theme", return_value=mock_theme),
        patch.object(tab_theme_config, "scan_system_themes") as mock_scan,
        patch.object(ThemeScriptsList, "refresh") as mock_scan_scripts,
    ):

        tab_theme_config.build()
        tab_theme_config.load_themes()

        assert tab_theme_config.data.current_theme == mock_theme
        assert tab_theme_config.widgets.panels.theme_switch.get_active()
        # _scan_system_themes est appelé explicitement dans _load_themes quand un thème est actif
        assert mock_scan.called
        assert mock_scan_scripts.called


def test_load_themes_no_active(tab_theme_config):
    """Test le chargement des thèmes sans thème actif."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    # Configurer le modèle pour avoir theme_management_enabled=False
    tab_theme_config.state_manager.state_data = GrubUiState(
        model=GrubUiModel(theme_management_enabled=False),
        entries=[],
        raw_config={}
    )
    
    with (
        patch.object(tab_theme_config.services.theme_manager, "load_active_theme", return_value=None),
        patch.object(tab_theme_config, "scan_system_themes"),
    ):

        tab_theme_config.build()
        tab_theme_config.load_themes()

        assert tab_theme_config.data.current_theme is None
        assert not tab_theme_config.widgets.panels.theme_switch.get_active()


def test_scan_system_themes(tab_theme_config):
    """Test le scan des thèmes système."""
    tab_theme_config.build()

    with patch.object(tab_theme_config.services.theme_service, "scan_system_themes", return_value={}):
        tab_theme_config.scan_system_themes()
        assert "Aucun (GRUB par défaut)" in tab_theme_config.data.available_themes
        assert tab_theme_config.widgets.panels.theme_list_box.get_first_child() is not None


def test_scan_system_themes_found(tab_theme_config):
    """Test le scan avec des thèmes trouvés."""
    tab_theme_config.build()

    mock_theme = GrubTheme(name="MyTheme")
    mock_path = Path("/path/to/MyTheme")

    with patch.object(
        tab_theme_config.services.theme_service,
        "scan_system_themes",
        return_value={"MyTheme": (mock_theme, mock_path)},
    ):
        tab_theme_config.scan_system_themes()

        assert "MyTheme" in tab_theme_config.data.available_themes
        # Vérifier qu'une ligne a été ajoutée (pas le placeholder)
        row = tab_theme_config.widgets.panels.theme_list_box.get_first_child()
        assert row is not None
        # On pourrait vérifier le contenu du label mais c'est complexe avec l'UI


def test_on_theme_selected(tab_theme_config):
    """Test la sélection d'un thème."""
    tab_theme_config.build()

    mock_theme = GrubTheme(name="MyTheme")
    tab_theme_config.data.available_themes = {"MyTheme": mock_theme}

    # Simuler une ligne
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0

    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, row, tab_theme_config)

    assert tab_theme_config.data.current_theme == mock_theme
    assert tab_theme_config.widgets.actions.preview_btn.get_sensitive()


def test_on_theme_selected_none(tab_theme_config):
    """Test la désélection d'un thème."""
    tab_theme_config.build()
    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, None, tab_theme_config)

    assert tab_theme_config.data.current_theme is None
    assert not tab_theme_config.widgets.actions.preview_btn.get_sensitive()


def test_on_theme_switch_toggled(tab_theme_config):
    """Test le basculement du switch."""
    tab_theme_config.build()

    with patch.object(tab_theme_config, "refresh") as mock_refresh:
        tab_theme_config.widgets.panels.theme_switch.set_active(True)
        # Le signal notify::active est émis
        # Mais comme on n'est pas dans une boucle GTK, on appelle directement
        on_theme_switch_toggled(tab_theme_config.widgets.panels.theme_switch, None, tab_theme_config)

        mock_refresh.assert_called()
        assert tab_theme_config.widgets.containers.theme_sections_container.get_visible()


def test_theme_scripts_list_refresh(tab_theme_config):
    """Test refresh() du composant ThemeScriptsList."""
    tab_theme_config.build()

    mock_script = MagicMock()
    mock_script.name = "Script 1"
    mock_script.is_executable = True
    mock_script.path = "/etc/grub.d/01_script"

    with patch.object(
        tab_theme_config.services.script_service,
        "scan_theme_scripts",
        return_value=[mock_script],
    ):
        assert tab_theme_config.widgets.panels.scripts_list is not None
        tab_theme_config.widgets.panels.scripts_list.refresh()
        assert tab_theme_config.widgets.panels.scripts_list.scripts_list_box.get_first_child() is not None


def test_theme_scripts_list_on_script_switch_toggled(mock_state_manager):
    """Test le basculement du switch d'un script via ThemeScriptsList."""
    from types import SimpleNamespace

    script = SimpleNamespace(path="/path/to/script", name="test_script", is_executable=False)
    switch = MagicMock()
    switch.get_active.return_value = True
    label = MagicMock()

    mock_state_manager.is_loading.return_value = False
    mock_state_manager.pending_script_changes = {}

    scripts = ThemeScriptsList(state_manager=mock_state_manager, script_service=MagicMock())
    scripts.on_script_switch_toggled(switch, script, label)

    assert mock_state_manager.pending_script_changes["/path/to/script"] is True
    assert mock_state_manager.update_model.called
    label.set_label.assert_called_with("actif")
    label.remove_css_class.assert_called_with("warning")


# Tests obsolètes (remplacés par _on_script_switch_toggled)
# def test_on_activate_script_success(tab):
#     ...



# def test_on_activate_script_failure(tab_theme_config):
#     """Test l'échec de l'activation d'un script."""
#     with (
#         patch.object(tab_theme_config.script_service, "make_executable", return_value=False),
#         patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
#     ):
#
#         _on_activate_script(MagicMock(), "/path/to/script", tab_theme_config)
#
#         assert mock_dialog.called
#
#
# def test_on_activate_script_exceptions(tab_theme_config):
#     """Test les exceptions lors de l'activation d'un script."""
#     exceptions = [
#         GrubCommandError("Cmd error"),
#         GrubScriptNotFoundError("Not found"),
#         PermissionError("Denied"),
#         OSError("OS Error"),
#     ]
#
#     for exc in exceptions:
#         with (
#             patch.object(tab_theme_config.script_service, "make_executable", side_effect=exc),
#             patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
#         ):
#
#             _on_activate_script(MagicMock(), "/path/to/script", tab_theme_config)
#             assert mock_dialog.called


def test_on_open_editor(tab_theme_config):
    """Test l'ouverture de l'éditeur."""
    tab_theme_config.build()

    mock_window = MagicMock(spec=Gtk.Window)
    tab_theme_config.parent_window = mock_window

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value

        on_open_editor(tab_theme_config)

        assert mock_dialog.present.called

def test_on_open_editor_close_callback(tab_theme_config):
    """Test le callback de fermeture de l'éditeur."""
    tab_theme_config.build()
    mock_window = MagicMock(spec=Gtk.Window)
    tab_theme_config.parent_window = mock_window

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        
        # Capturer le callback connecté à "close-request"
        close_callback = None
        def mock_connect(signal, callback):
            nonlocal close_callback
            if signal == "close-request":
                close_callback = callback
        
        mock_dialog.connect.side_effect = mock_connect

        on_open_editor(tab_theme_config)
        
        assert hasattr(tab_theme_config, "_interactive_theme_generator_window")
        assert close_callback is not None
        
        # Appeler le callback
        result = close_callback(mock_dialog)
        assert result is False
        assert not hasattr(tab_theme_config, "_interactive_theme_generator_window")

        # Tester le cas où l'attribut est déjà supprimé (pour la branche except)
        close_callback(mock_dialog) # Ne devrait pas lever d'exception


def test_on_preview_theme(tab_theme_config):
    """Test l'aperçu du thème."""
    tab_theme_config.data.current_theme = GrubTheme(name="MyTheme")

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.GrubPreviewDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value

        on_preview_theme(tab_theme_config)

        assert mock_dialog.show.called


def test_load_themes_exception(mock_state_manager_disabled):
    """Test load_themes with exception."""
    tab_theme_config = TabThemeConfig(mock_state_manager_disabled)
    
    with patch.object(
        tab_theme_config.services.theme_manager,
        "load_active_theme",
        side_effect=OSError("Load error"),
    ):
        tab_theme_config.build()
        tab_theme_config.load_themes()
        # Should handle exception gracefully
        assert not tab_theme_config.widgets.panels.theme_switch.get_active()


def test_on_theme_switch_toggled_widgets_none(tab_theme_config):
    """Test on_theme_switch_toggled when widgets are None."""
    tab_theme_config.widgets.panels.theme_list_box = None
    tab_theme_config.widgets.actions.preview_btn = None

    # Évite de rentrer dans le flux complet (UI) dans ce test.
    tab_theme_config.load_themes = MagicMock()

    switch = MagicMock()
    switch.get_active.return_value = True

    with patch.object(tab_theme_config, "scan_system_themes"):
        on_theme_switch_toggled(switch, None, tab_theme_config)
        # Should run without error
        # Should add activate button


def test_on_open_editor_exception(tab_theme_config):
    """Test on_open_editor with exception."""
    tab_theme_config.build()
    tab_theme_config.parent_window = MagicMock()

    with (
        patch(
            "ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow",
            side_effect=RuntimeError("Dialog error"),
        ),
        patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_dialog,
    ):

        on_open_editor(tab_theme_config)
        assert mock_dialog.called


def test_on_preview_theme_exception(tab_theme_config):
    """Test _on_preview_theme with exception."""
    tab_theme_config.data.current_theme = MagicMock()
    tab_theme_config.data.current_theme.name = "test"

    with (
        patch("ui.tabs.theme_config.ui_theme_config_handlers.GrubPreviewDialog", side_effect=OSError("Preview fail")),
        patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_err,
    ):
        on_preview_theme(tab_theme_config)
        assert mock_err.called


def test_on_preview_theme_show_raises_is_caught(tab_theme_config):
    tab_theme_config.data.current_theme = GrubTheme(name="MyTheme")

    dialog = MagicMock()
    dialog.show.side_effect = RuntimeError("boom")

    with (
        patch("ui.tabs.theme_config.ui_theme_config_handlers.GrubPreviewDialog", return_value=dialog),
        patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_err,
    ):
        on_preview_theme(tab_theme_config)
        assert mock_err.called


def test_on_theme_selected_row_none_buttons_none(tab_theme_config):
    tab_theme_config.build()
    tab_theme_config.widgets.actions.preview_btn = None
    tab_theme_config.widgets.actions.edit_btn = None
    tab_theme_config.widgets.actions.delete_btn = None

    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, None, tab_theme_config)
    assert tab_theme_config.data.current_theme is None


def test_on_theme_selected_default_theme_disables_preview(tab_theme_config):
    tab_theme_config.build()

    default_theme = GrubTheme(name="Aucun (GRUB par défaut)")
    tab_theme_config.data.available_themes = {default_theme.name: default_theme}

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0

    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, row, tab_theme_config)

    assert tab_theme_config.data.current_theme == default_theme
    assert not tab_theme_config.widgets.actions.preview_btn.get_sensitive()


def test_on_theme_selected_custom_enables_edit_delete(tab_theme_config):
    tab_theme_config.build()

    theme = GrubTheme(name="MyCustom")
    tab_theme_config.data.available_themes = {theme.name: theme}
    tab_theme_config.data.theme_paths = {theme.name: Path("/tmp/theme")}

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0

    with patch.object(tab_theme_config.services.theme_service, "is_theme_custom", return_value=True):
        on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, row, tab_theme_config)

    assert tab_theme_config.widgets.actions.edit_btn.get_sensitive()
    assert tab_theme_config.widgets.actions.delete_btn.get_sensitive()


def test_on_theme_selected_buttons_none_valid_row(tab_theme_config):
    tab_theme_config.build()

    theme = GrubTheme(name="MyTheme")
    tab_theme_config.data.available_themes = {theme.name: theme}
    tab_theme_config.widgets.actions.preview_btn = None
    tab_theme_config.widgets.actions.edit_btn = None
    tab_theme_config.widgets.actions.delete_btn = None

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0

    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, row, tab_theme_config)
    assert tab_theme_config.data.current_theme == theme


def test_on_theme_switch_toggled_selects_first_row_when_available(tab_theme_config):
    tab_theme_config.build()

    tab_theme_config.data.available_themes = {"T": GrubTheme(name="T")}
    tab_theme_config.widgets.panels.theme_list_box = MagicMock()
    tab_theme_config.widgets.panels.theme_list_box.get_row_at_index.return_value = MagicMock()

    switch = MagicMock()
    switch.get_active.return_value = True

    with (
        patch.object(tab_theme_config, "refresh") as mock_refresh,
        patch.object(tab_theme_config, "scan_system_themes"),
    ):
        on_theme_switch_toggled(switch, None, tab_theme_config)

    assert mock_refresh.called
    assert tab_theme_config.widgets.panels.theme_list_box.select_row.called


def test_on_theme_switch_toggled_inactive(mock_state_manager_disabled):
    """Test le basculement du switch inactif."""
    tab_theme_config = TabThemeConfig(mock_state_manager_disabled)
    tab_theme_config.build()

    with patch.object(tab_theme_config, "load_themes") as mock_load_themes:
        switch = MagicMock()
        switch.get_active.return_value = False

        on_theme_switch_toggled(switch, None, tab_theme_config)

        mock_load_themes.assert_called_once()
        assert not tab_theme_config.widgets.containers.theme_sections_container.get_visible()


def test_load_themes_scan_exception(tab_theme_config):
    """Test load_themes with exception during scan."""
    mock_theme = GrubTheme(name="MyTheme")
    tab_theme_config.widgets.panels.theme_switch = MagicMock()

    with (
        patch.object(tab_theme_config.services.theme_manager, "load_active_theme", return_value=mock_theme),
        patch.object(tab_theme_config, "scan_system_themes", side_effect=OSError("Scan fail")),
    ):

        # Should catch exception and log error
        tab_theme_config.load_themes()
        # No assertion needed, just ensure it doesn't crash


def test_on_theme_selected_invalid_index(tab_theme_config):
    """Test _on_theme_selected with invalid index."""
    tab_theme_config.build()
    tab_theme_config.data.available_themes = {"MyTheme": GrubTheme(name="MyTheme")}
    tab_theme_config.data.current_theme = None

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 10  # Out of bounds

    on_theme_selected(tab_theme_config.widgets.panels.theme_list_box, row, tab_theme_config)

    # Should not change current theme (or keep it None)
    assert tab_theme_config.data.current_theme is None


def test_load_themes_inner_exception():
    """Test catching exception inside the inner try block of load_themes."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    mock_state_manager = MagicMock(spec=AppStateManager)
    mock_state_manager.state_data = GrubUiState(
        model=GrubUiModel(theme_management_enabled=False),
        entries=[],
        raw_config={}
    )
    mock_state_manager.is_loading.return_value = False

    tab = TabThemeConfig(mock_state_manager)

    # Setup mocks
    tab.services.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.services.script_service = MagicMock(spec=GrubScriptService)
    tab.services.theme_service = MagicMock(spec=ThemeService)
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.data.available_themes = {}

    # Mock load_active_theme to raise OSError
    tab.services.theme_manager.load_active_theme.side_effect = OSError("Inner fail")

    tab.load_themes()

    # Verification - should handle exception gracefully
    tab.widgets.panels.theme_switch.set_active.assert_called()


def test_load_themes_outer_exception():
    """Test catching exception in the outer try block of load_themes."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    mock_state_manager = MagicMock(spec=AppStateManager)
    mock_state_manager.state_data = GrubUiState(
        model=GrubUiModel(theme_management_enabled=False),
        entries=[],
        raw_config={}
    )
    mock_state_manager.is_loading.return_value = False

    tab = TabThemeConfig(mock_state_manager)

    # Setup mocks
    tab.services.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.services.script_service = MagicMock(spec=GrubScriptService)
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.data.available_themes = {}

    # Make load_active_theme raise an exception to test outer exception handling
    tab.services.theme_manager.load_active_theme.side_effect = RuntimeError("Outer fail")

    tab.load_themes()

    # Verify that the exception handler caught it (exception is logged but not re-raised)
    # The _updating_ui flag should be reset to False


def test_on_open_editor_find_parent_window():
    """Test finding the parent window in _on_open_editor."""
    mock_state_manager = MagicMock(spec=AppStateManager)
    tab = TabThemeConfig(mock_state_manager)
    mock_window = MagicMock()
    mock_window.present = MagicMock()
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = mock_window

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow"):
        on_open_editor(tab, button)
        assert tab.parent_window == mock_window


@pytest.fixture
def tab(mock_state_manager):
    tab = TabThemeConfig(mock_state_manager)

    tab.services.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.services.script_service = MagicMock(spec=GrubScriptService)
    tab.services.theme_service = MagicMock(spec=ThemeService)

    tab.widgets.panels.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.widgets.panels.theme_list_box.get_first_child.return_value = None
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.widgets.panels.scripts_list = MagicMock()
    tab.widgets.panels.scripts_list.refresh = MagicMock()

    tab.widgets.actions.preview_btn = MagicMock(spec=Gtk.Button)
    tab.widgets.actions.activate_theme_btn = MagicMock(spec=Gtk.Button)
    tab.widgets.actions.deactivate_theme_btn = MagicMock(spec=Gtk.Button)
    tab.widgets.actions.edit_btn = MagicMock(spec=Gtk.Button)
    tab.widgets.actions.delete_btn = MagicMock(spec=Gtk.Button)

    tab.widgets.containers.theme_sections_container = MagicMock(spec=Gtk.Box)
    tab.widgets.containers.simple_config_container = MagicMock(spec=Gtk.Box)

    tab.parent_window = MagicMock(spec=Gtk.Window)

    return tab


def test_on_edit_theme_not_found(tab):
    """Teste _on_edit_theme quand le thème n'est pas trouvé."""
    tab.data.available_themes = {}
    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_edit_theme(None, "Unknown", tab)
        mock_error.assert_called_once_with("Thème 'Unknown' introuvable")


def test_on_edit_theme_system(tab):
    """Teste _on_edit_theme quand le thème est un thème système."""
    tab.data.available_themes = {"System": GrubTheme(name="System")}
    tab.data.theme_paths = {"System": Path("/usr/share/grub/themes/System")}
    tab.services.theme_service.is_theme_custom.return_value = False

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_edit_theme(None, "System", tab)
        mock_error.assert_called_once_with("Ce thème système ne peut pas être modifié")


def test_on_edit_theme_success(tab):
    """Teste _on_edit_theme avec succès."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.services.theme_service.is_theme_custom.return_value = True

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow") as mock_win:
        on_edit_theme(None, "Custom", tab)
        mock_win.assert_called_once()


def test_on_edit_theme_no_parent(tab):
    """Teste _on_edit_theme sans fenêtre parente."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.services.theme_service.is_theme_custom.return_value = True
    tab.parent_window = None

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_edit_theme(None, "Custom", tab)
        mock_error.assert_called_once_with("Impossible d'ouvrir l'éditeur")


def test_on_edit_theme_exception(tab):
    """Teste _on_edit_theme avec une exception."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.services.theme_service.is_theme_custom.side_effect = RuntimeError("Test Error")

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_edit_theme(None, "Custom", tab)
        assert mock_error.called


def test_on_delete_theme_not_found(tab):
    """Teste _on_delete_theme quand le thème n'est pas trouvé."""
    tab.data.available_themes = {}
    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_delete_theme(None, "Unknown", tab)
        mock_error.assert_called_once_with("Thème 'Unknown' introuvable")


def test_on_delete_theme_system(tab):
    """Teste _on_delete_theme quand le thème est un thème système."""
    tab.data.available_themes = {"System": GrubTheme(name="System")}
    tab.data.theme_paths = {"System": Path("/usr/share/grub/themes/System")}
    tab.services.theme_service.is_theme_custom.return_value = False

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_delete_theme(None, "System", tab)
        mock_error.assert_called_once_with("Les thèmes système ne peuvent pas être supprimés")


def test_on_delete_theme_success(tab):
    """Teste _on_delete_theme avec succès (ouverture du dialogue)."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.services.theme_service.is_theme_custom.return_value = True

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.Gtk.AlertDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        on_delete_theme(None, "Custom", tab)
        mock_dialog.choose.assert_called_once()


def test_on_delete_theme_exception(tab):
    """Teste _on_delete_theme avec une exception."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.services.theme_service.is_theme_custom.side_effect = RuntimeError("Test Error")

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_delete_theme(None, "Custom", tab)
        assert mock_error.called


def test_on_delete_confirmed_yes(tab):
    """Teste _on_delete_confirmed quand l'utilisateur confirme."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 1  # Supprimer

    theme_name = "Custom"
    theme_path = Path("/home/user/.local/share/grub/themes/Custom")
    user_data = (theme_name, theme_path, tab)

    tab.services.theme_service.delete_theme.return_value = True
    tab.scan_system_themes = MagicMock()

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_success_dialog") as mock_success:
        on_delete_confirmed(mock_dialog, None, user_data)
        tab.services.theme_service.delete_theme.assert_called_once_with(theme_path)
        mock_success.assert_called_once()
        tab.scan_system_themes.assert_called_once()


def test_on_delete_confirmed_no(tab):
    """Teste _on_delete_confirmed quand l'utilisateur annule."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 0  # Annuler

    user_data = ("Custom", Path("/path"), tab)

    on_delete_confirmed(mock_dialog, None, user_data)
    assert not tab.services.theme_service.delete_theme.called


def test_on_delete_confirmed_failure(tab):
    """Teste _on_delete_confirmed quand la suppression échoue."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 1

    user_data = ("Custom", Path("/path"), tab)
    tab.services.theme_service.delete_theme.return_value = False
    tab.scan_system_themes = MagicMock()

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_delete_confirmed(mock_dialog, None, user_data)
        mock_error.assert_called_once()
        tab.scan_system_themes.assert_called_once()


def test_on_delete_confirmed_exception(tab):
    """Teste _on_delete_confirmed avec une exception."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.side_effect = RuntimeError("Test Error")
    tab.scan_system_themes = MagicMock()

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_delete_confirmed(mock_dialog, None, None)
        assert mock_error.called


def test_on_theme_selected_custom(tab):
    """Teste _on_theme_selected avec un thème custom."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/path")}
    tab.services.theme_service.is_theme_custom.return_value = True

    on_theme_selected(tab.widgets.panels.theme_list_box, row, tab)

    assert tab.widgets.actions.edit_btn.set_sensitive.called
    assert tab.widgets.actions.delete_btn.set_sensitive.called
    # Vérifier que set_sensitive(True) a été appelé pour edit/delete
    tab.widgets.actions.edit_btn.set_sensitive.assert_called_with(True)
    tab.widgets.actions.delete_btn.set_sensitive.assert_called_with(True)


def test_on_theme_selected_system(tab):
    """Teste _on_theme_selected avec un thème système."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.data.available_themes = {"System": GrubTheme(name="System")}
    tab.data.theme_paths = {"System": Path("/path")}
    tab.services.theme_service.is_theme_custom.return_value = False

    on_theme_selected(tab.widgets.panels.theme_list_box, row, tab)

    tab.widgets.actions.edit_btn.set_sensitive.assert_called_with(False)
    tab.widgets.actions.delete_btn.set_sensitive.assert_called_with(False)


def test_tab_build(tab):
    """Teste la construction de l'interface."""
    with (
        patch("ui.tabs.ui_tab_theme_config.create_main_box") as mock_main_box,
        patch("ui.tabs.ui_tab_theme_config.create_two_column_layout") as mock_layout,
    ):

        mock_main_box.return_value = MagicMock(spec=Gtk.Box)
        mock_layout.return_value = (MagicMock(spec=Gtk.Box), MagicMock(spec=Gtk.Box), MagicMock(spec=Gtk.Box))

        res = tab.build()
        assert res == mock_main_box.return_value
        assert tab.widgets.containers.theme_sections_container is not None


def test_tab_refresh(tab):
    """Teste le rafraîchissement de l'onglet."""
    tab.scan_system_themes = MagicMock()
    tab.widgets.panels.scripts_list = MagicMock()
    tab.refresh()
    tab.widgets.panels.scripts_list.refresh.assert_called_once()
    tab.scan_system_themes.assert_called_once()


def test_load_themes_enabled(tab):
    """Teste le chargement des thèmes quand ils sont activés dans le modèle."""
    tab.services.theme_manager.load_active_theme.return_value = GrubTheme(name="Active")
    tab.refresh = MagicMock()
    tab.widgets.panels.theme_list_box.get_row_at_index.return_value = MagicMock(spec=Gtk.ListBoxRow)
    tab.data.available_themes = {"Active": tab.services.theme_manager.load_active_theme.return_value}

    tab.load_themes()

    assert tab.data.current_theme.name == "Active"
    tab.refresh.assert_called_once()
    tab.widgets.panels.theme_list_box.select_row.assert_called_once()


def test_load_themes_disabled(tab):
    """Teste le chargement des thèmes quand ils sont désactivés dans GRUB."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    
    # Configurer le modèle pour avoir theme_management_enabled=False
    tab.state_manager.state_data = GrubUiState(
        model=GrubUiModel(theme_management_enabled=False),
        entries=[],
        raw_config={}
    )
    
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()

    tab.load_themes()

    assert not tab.refresh.called


def test_scan_system_themes_empty(tab):
    """Teste le scan des thèmes quand aucun n'est trouvé."""
    tab.services.theme_service.scan_system_themes.return_value = {}
    tab.widgets.panels.theme_list_box.get_first_child.side_effect = [MagicMock(), None]

    tab.scan_system_themes()

    tab.widgets.panels.theme_list_box.append.assert_called_once()  # Placeholder


def test_scan_system_themes_with_data(tab):
    """Teste le scan des thèmes avec des résultats."""
    theme = GrubTheme(name="Test")
    path = Path("/path/to/theme")
    tab.services.theme_service.scan_system_themes.return_value = {"Test": (theme, path)}
    tab.widgets.panels.theme_list_box.get_first_child.return_value = None

    tab.scan_system_themes()

    assert "Test" in tab.data.available_themes
    assert tab.widgets.panels.theme_list_box.append.called


def test_on_theme_switch_toggled_on(tab):
    """Teste le basculement du switch sur ON."""
    from core.models.core_grub_ui_model import GrubUiModel
    
    # Reconfigure state to be disabled initially
    tab.state_manager.get_model.return_value = GrubUiModel(theme_management_enabled=False)
    
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.data.available_themes = {"T": MagicMock()}
    
    on_theme_switch_toggled(switch, None, tab)
    
    # Verify that the model was updated
    tab.state_manager.update_model.assert_called()
    args, _ = tab.state_manager.update_model.call_args
    assert args[0].theme_management_enabled is True


def test_on_theme_switch_toggled_off(tab):
    """Teste le basculement du switch sur OFF."""
    from core.models.core_grub_ui_model import GrubUiModel
    tab.state_manager.get_model.return_value = GrubUiModel(theme_management_enabled=True)
    
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = False

    on_theme_switch_toggled(switch, None, tab)

    # Verify that the model was updated
    tab.state_manager.update_model.assert_called()
    args, _ = tab.state_manager.update_model.call_args
    assert args[0].theme_management_enabled is False


def test_load_themes_no_active_theme_exception(tab):
    """Teste load_themes quand le chargement du thème actif lève une exception."""
    tab.services.theme_manager.load_active_theme.side_effect = RuntimeError("No active theme")
    tab.refresh = MagicMock()

    tab.load_themes()

    assert tab.refresh.called


def test_load_themes_global_exception(tab):
    """Teste load_themes quand une exception globale survient."""
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.widgets.panels.theme_switch.set_active.side_effect = RuntimeError("Global error")

    tab.load_themes()  # Ne doit pas lever d'exception


def test_on_theme_selected_no_index(tab):
    """Teste on_theme_selected avec un index invalide."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = -1
    tab.data.available_themes = {"T": MagicMock()}

    on_theme_selected(tab.widgets.panels.theme_list_box, row, tab)

    # activate_btn is no longer part of the UI



# def test_on_activate_script_errors(tab):
#     """Teste les erreurs dans _on_activate_script."""
#     from ui.tabs.ui_tab_theme_config import GrubCommandError, GrubScriptNotFoundError, _on_activate_script
#
#     with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
#         # GrubCommandError
#         tab.script_service.make_executable.side_effect = GrubCommandError("Cmd error")
#         _on_activate_script(None, "/path", tab)
#         assert mock_error.called
#
#         # GrubScriptNotFoundError
#         tab.script_service.make_executable.side_effect = GrubScriptNotFoundError("Not found")
#         _on_activate_script(None, "/path", tab)
#         assert mock_error.called
#
#         # PermissionError
#         tab.script_service.make_executable.side_effect = PermissionError("Perm error")
#         _on_activate_script(None, "/path", tab)
#         assert mock_error.called
#
#         # OSError
#         tab.script_service.make_executable.side_effect = OSError("OS error")
#         _on_activate_script(None, "/path", tab)
#         assert mock_error.called


def test_on_open_editor_no_parent(tab):
    """Teste _on_open_editor sans fenêtre parente."""
    tab.parent_window = None
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = None

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_open_editor(tab, button)
        mock_error.assert_called_once_with("Impossible d'ouvrir l'éditeur")


def test_on_theme_selected_no_preview(tab):
    """Teste _on_theme_selected avec un thème sans aperçu."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.data.available_themes = {"None": GrubTheme(name="Aucun (GRUB par défaut)")}
    tab.data.theme_paths = {"None": Path("/path")}
    tab.services.theme_service.is_theme_custom.return_value = False

    on_theme_selected(tab.widgets.panels.theme_list_box, row, tab)

    tab.widgets.actions.preview_btn.set_sensitive.assert_called_with(False)


def test_on_open_editor_with_root(tab):
    """Teste _on_open_editor en trouvant le root."""
    tab.parent_window = None
    mock_root = MagicMock(spec=Gtk.Window)
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = mock_root

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow") as mock_dialog:
        on_open_editor(tab, button)
        mock_dialog.assert_called_once()


def test_load_themes_no_active_theme(tab):
    """Teste load_themes quand aucun thème n'est actif."""
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()

    tab.load_themes()

    assert tab.data.current_theme is None
    assert tab.refresh.called


def test_load_themes_no_available_themes(tab):
    """Teste load_themes quand aucun thème n'est disponible."""
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    tab.data.available_themes = {}

    tab.load_themes()

    assert not tab.widgets.panels.theme_list_box.select_row.called


def test_scan_system_themes_no_list_box(tab):
    """Teste _scan_system_themes sans list_box."""
    tab.widgets.panels.theme_list_box = None
    tab.scan_system_themes()
    assert not tab.services.theme_service.scan_system_themes.called


def test_on_theme_selected_row_none(tab):
    """Teste _on_theme_selected avec row=None."""
    on_theme_selected(tab.widgets.panels.theme_list_box, None, tab)
    assert tab.data.current_theme is None


def test_on_theme_selected_no_buttons(tab):
    """Teste _on_theme_selected sans boutons définis."""
    tab.data.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.data.theme_paths = {"Custom": Path("/path")}
    tab.services.theme_service.is_theme_custom.return_value = True
    tab.parent_window = None

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.Gtk.AlertDialog") as mock_dialog_class:
        on_delete_theme(None, "Custom", tab)
        # Vérifier que choose a été appelé
        assert mock_dialog_class.return_value.choose.called


# def test_on_activate_script_oserror(tab):
#     """Teste _on_activate_script avec OSError."""
#     tab.script_service.make_executable.side_effect = OSError("OS Error")
#     with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_err:
#         _on_activate_script(MagicMock(), "/path/to/script", tab)
#         mock_err.assert_called()


def test_on_delete_theme_no_parent_with_button(tab):
    """Teste _on_delete_theme sans parent_window mais avec un bouton."""
    tab.parent_window = None
    tab.data.available_themes = {"custom": MagicMock()}
    tab.data.theme_paths = {"custom": Path("/home/user/.local/share/grub/themes/custom")}
    tab.services.theme_service.is_theme_custom.return_value = True

    button = MagicMock()
    mock_root = MagicMock()
    button.get_root.return_value = mock_root

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.Gtk.AlertDialog") as MockDialog:
        mock_dialog = MockDialog.return_value
        on_delete_theme(button, "custom", tab)
        mock_dialog.choose.assert_called()
        # Vérifier que le parent passé à choose est mock_root
        _, kwargs = mock_dialog.choose.call_args
        assert kwargs["parent"] == mock_root


def test_on_open_editor_with_error(tab):
    """Teste _on_open_editor avec une exception."""
    tab.parent_window = MagicMock()
    with patch(
        "ui.tabs.theme_config.ui_theme_config_handlers.InteractiveThemeGeneratorWindow",
        side_effect=RuntimeError("Editor Error"),
    ):
        with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_err:
            on_open_editor(tab)
            mock_err.assert_called()


def test_scan_system_themes_custom_badge(tab):
    """Teste _scan_system_themes avec un badge 'Custom'."""
    mock_theme = GrubTheme(name="custom_theme")
    tab.services.theme_service.scan_system_themes.return_value = {"custom_theme": (mock_theme, Path("/path/to/custom"))}
    tab.services.theme_service.is_theme_custom.return_value = True
    tab.scan_system_themes()
    assert tab.widgets.panels.theme_list_box.append.called


def test_load_themes_with_container(tab):
    """Teste load_themes avec un container de sections."""
    tab.widgets.containers.theme_sections_container = MagicMock(spec=Gtk.Box)
    tab.widgets.containers.simple_config_container = MagicMock(spec=Gtk.Box)
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    # Mock available_themes to trigger selection branch
    tab.data.available_themes = {"T": MagicMock()}
    mock_row = MagicMock(spec=Gtk.ListBoxRow)
    tab.widgets.panels.theme_list_box.get_row_at_index.return_value = mock_row

    tab.load_themes()
    tab.widgets.containers.theme_sections_container.set_visible.assert_called_with(True)
    tab.widgets.panels.theme_list_box.select_row.assert_called_with(mock_row)


def test_on_theme_switch_toggled_select_first(tab):
    """Teste on_theme_switch_toggled sélectionne le premier thème."""
    tab.widgets.panels.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.widgets.panels.theme_list_box.get_first_child.return_value = None
    # Mock scan_system_themes to populate available_themes
    tab.services.theme_service.scan_system_themes.return_value = {"T": (MagicMock(), Path("/path"))}

    mock_row = MagicMock(spec=Gtk.ListBoxRow)
    tab.widgets.panels.theme_list_box.get_row_at_index.return_value = mock_row

    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True

    on_theme_switch_toggled(switch, None, tab)

    tab.widgets.panels.theme_list_box.select_row.assert_called_with(mock_row)


def test_on_theme_switch_toggled_no_themes(tab):
    """Teste on_theme_switch_toggled quand aucun thème n'est disponible."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.widgets.panels.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.data.available_themes = {}
    tab.refresh = MagicMock()
    on_theme_switch_toggled(switch, None, tab)
    tab.widgets.panels.theme_list_box.select_row.assert_not_called()


def test_load_themes_active_theme_exception(tab):
    """Teste load_themes avec une exception lors du chargement du thème actif."""
    tab.services.theme_manager.load_active_theme.side_effect = RuntimeError("Test error")
    tab.refresh = MagicMock()

    # Ne devrait pas planter
    tab.load_themes()
    # Vérifier que la suite s'est exécutée
    tab.refresh.assert_called()


def test_load_themes_global_exception_real(tab):
    """Teste load_themes avec une exception globale."""
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.widgets.panels.theme_switch.set_active.side_effect = RuntimeError("Global error")

    tab.load_themes()


def test_load_themes_no_sections_container(tab):
    """Teste load_themes sans container de sections."""
    tab.widgets.panels.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.widgets.containers.theme_sections_container = None
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    tab.load_themes()
    # Devrait passer sans erreur


def test_load_themes_no_first_row(tab):
    """Teste load_themes quand get_row_at_index(0) retourne None."""
    tab.services.theme_manager.load_active_theme.return_value = None
    tab.widgets.panels.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.widgets.panels.theme_list_box.get_row_at_index.return_value = None
    tab.data.available_themes = {"T": MagicMock()}
    tab.refresh = MagicMock()
    tab.load_themes()
    tab.widgets.panels.theme_list_box.select_row.assert_not_called()


def test_on_theme_switch_toggled_no_first_row(tab):
    """Teste _on_theme_switch_toggled quand get_row_at_index(0) retourne None."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.widgets.panels.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.widgets.panels.theme_list_box.get_row_at_index.return_value = None
    tab.data.available_themes = {"T": MagicMock()}
    tab.refresh = MagicMock()

    on_theme_switch_toggled(switch, None, tab)
    tab.widgets.panels.theme_list_box.select_row.assert_not_called()


def test_scan_system_themes_system_badge(tab):
    """Teste _scan_system_themes avec un badge 'Système'."""
    mock_theme = GrubTheme(name="system_theme")
    tab.services.theme_service.scan_system_themes.return_value = {
        "system_theme": (mock_theme, Path("/usr/share/grub/themes/system_theme"))
    }
    tab.services.theme_service.is_theme_custom.return_value = False
    tab.scan_system_themes()
    assert tab.widgets.panels.theme_list_box.append.called


def test_on_preview_theme_no_theme_selected(tab):
    """Teste _on_preview_theme quand aucun thème n'est sélectionné."""
    tab.data.current_theme = None

    with patch("ui.tabs.theme_config.ui_theme_config_handlers.create_error_dialog") as mock_error:
        on_preview_theme(tab)
        mock_error.assert_called_once_with("Veuillez sélectionner un thème")

def test_on_bg_image_selected_with_file(tab):
    """Test sélection d'image: le callback met à jour l'Entry du panneau."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    assert panel.widgets.bg_image_entry is not None

    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        assert open_dialog.called

        on_selected = open_dialog.call_args.kwargs["on_selected"]
        on_selected("/path/to/image.png")
        assert panel.widgets.bg_image_entry.get_text() == "/path/to/image.png"


def test_on_bg_image_selected_no_file(tab):
    """Test sélection d'image: callback tolère un chemin vide."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    assert panel.widgets.bg_image_entry is not None
    panel.widgets.bg_image_entry.set_text("already")

    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        on_selected = open_dialog.call_args.kwargs["on_selected"]
        on_selected("")
        assert panel.widgets.bg_image_entry.get_text() == ""


def test_on_bg_image_selected_no_entry_widget(tab):
    """Test sélection d'image: ne plante pas si l'Entry est absente."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    panel.widgets.bg_image_entry = None

    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        on_selected = open_dialog.call_args.kwargs["on_selected"]
        on_selected("/path/to/image.png")


def test_on_simple_config_changed_updating_ui(tab):
    """Test changement config simple ignoré pendant un update UI."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    panel._updating_ui = True
    assert panel._on_config_changed() is None


def test_on_simple_config_changed_missing_widgets(tab):
    """Test changement config simple avec widgets manquants."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    panel.widgets.bg_image_entry = None
    panel.widgets.normal_fg_combo = None
    panel._updating_ui = False
    assert panel._on_config_changed() is None


def test_on_select_bg_image(tab):
    """Test sélection d'image via helper open_image_file_dialog."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        open_dialog.assert_called_once()


def test_on_bg_image_selected_success(tab):
    """Test sélection d'image: le callback met bien le texte."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    assert panel.widgets.bg_image_entry is not None

    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        on_selected = open_dialog.call_args.kwargs["on_selected"]
        on_selected("/path/to/image.png")
        assert panel.widgets.bg_image_entry.get_text() == "/path/to/image.png"


def test_on_bg_image_selected_error(tab):
    """Test sélection d'image: l'appel au helper ne plante pas."""
    tab.build()
    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    with patch("ui.components.ui_theme_simple_config.open_image_file_dialog") as open_dialog:
        panel._on_select_bg_image(Gtk.Button())
        assert open_dialog.called


# === Tests pour couvrir les lignes manquantes ===

def test_on_simple_config_changed_updates_model(tab):
    """Test changement config simple met à jour le modèle et marque dirty."""
    from core.models.core_grub_ui_model import GrubUiModel
    tab.mark_dirty = MagicMock()
    tab.build()

    panel = tab.widgets.panels.simple_config_panel
    assert panel is not None
    panel._updating_ui = False
    
    # Setup real model
    real_model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="", grub_color_highlight="",
        theme_management_enabled=True, quiet=True, splash=True, save_default=True,
    )
    tab.state_manager.get_model.return_value = real_model
    
    # Set values in combos
    widgets = panel.widgets
    assert widgets.normal_fg_combo is not None
    assert widgets.normal_bg_combo is not None
    assert widgets.highlight_fg_combo is not None
    assert widgets.highlight_bg_combo is not None
    widgets.normal_fg_combo.set_selected(0)
    widgets.normal_bg_combo.set_selected(1)
    widgets.highlight_fg_combo.set_selected(1)
    widgets.highlight_bg_combo.set_selected(0)
    
    # Trigger callback
    panel._on_config_changed()
    
    # Verify model was updated
    tab.state_manager.update_model.assert_called()
    tab.mark_dirty.assert_called()


def test_load_themes_no_model(tab):
    """Test load_themes with no model (line 390-391)."""
    tab.state_manager.state_data = None
    tab.load_themes()  # Should return early without error


def test_load_themes_color_not_found(tab):
    """Test load_themes tolère des couleurs invalides (update_from_model)."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    tab.build()
    
    model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="unknown-color/invalid",
        grub_color_highlight="bad/colors", theme_management_enabled=True,
        quiet=True, splash=True, save_default=True,
    )
    state_data = GrubUiState(model=model, entries=[], raw_config={})
    tab.state_manager.state_data = state_data
    
    # Should not raise, just log warning
    tab.load_themes()


def test_add_theme_to_list_system_badge(tab):
    """Test _add_theme_to_list shows system badge (lines 548-551)."""
    from pathlib import Path
    tab.build()
    tab.data.current_theme = None  # Not active
    
    theme = MagicMock()
    theme.name = "test_theme"
    with patch.object(tab.services.theme_service, "is_theme_custom", return_value=False):
        # Should complete without error
        tab._add_theme_to_list(theme, Path("/themes/test_theme"))


def test_add_theme_to_list_custom_badge(tab):
    """Test _add_theme_to_list shows custom badge (lines 548-551 else branch)."""
    from pathlib import Path
    tab.build()
    tab.data.current_theme = None  # Not active
    
    theme = MagicMock()
    theme.name = "custom_theme"
    with patch.object(tab.services.theme_service, "is_theme_custom", return_value=True):
        # Should complete without error
        tab._add_theme_to_list(theme, Path("/themes/custom_theme"))


def test_on_theme_switch_toggled_updates_state(tab):
    """Test on_theme_switch_toggled met à jour l'état."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    tab.build()
    
    model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="", grub_color_highlight="",
        theme_management_enabled=False, quiet=True, splash=True, save_default=True,
    )
    tab.state_manager.get_model.return_value = model
    tab.state_manager.is_loading.return_value = False
    tab._updating_switch = False
    
    mock_switch = MagicMock()
    mock_switch.get_active.return_value = True
    
    on_theme_switch_toggled(mock_switch, None, tab)
    
    # Should have updated state
    tab.state_manager.update_model.assert_called()


def test_load_themes_color_without_slash(tab):
    """Test load_themes when color does not contain / (line 437->443)."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    tab.build()
    
    model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="justcolornobackground",
        grub_color_highlight="anothercolor", theme_management_enabled=True,
        quiet=True, splash=True, save_default=True,
    )
    state_data = GrubUiState(model=model, entries=[], raw_config={})
    tab.state_manager.state_data = state_data
    
    tab.load_themes()


def test_load_themes_color_empty_parts(tab):
    """Test load_themes when color has empty parts after split (line 439->443)."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    tab.build()
    
    # Just "/" would split to ['', ''] which has len==2 but empty strings
    model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="/",
        grub_color_highlight="/", theme_management_enabled=True,
        quiet=True, splash=True, save_default=True,
    )
    state_data = GrubUiState(model=model, entries=[], raw_config={})
    tab.state_manager.state_data = state_data
    
    tab.load_themes()


def test_load_themes_highlight_color_without_slash(tab):
    """Test load_themes when highlight color has no / (line 444->451)."""
    from core.models.core_grub_ui_model import GrubUiModel, GrubUiState
    tab.build()
    
    model = GrubUiModel(
        timeout=10, default="saved", hidden_timeout=False, gfxmode="",
        gfxpayload_linux="", disable_os_prober=False, grub_theme="",
        grub_background="", grub_color_normal="white/black",
        grub_color_highlight="noslash", theme_management_enabled=True,
        quiet=True, splash=True, save_default=True,
    )
    state_data = GrubUiState(model=model, entries=[], raw_config={})
    tab.state_manager.state_data = state_data
    
    tab.load_themes()