"""Tests pour l'onglet Configuration du thème."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_grub_script_service import GrubScriptService
from core.theme.core_active_theme_manager import ActiveThemeManager
from core.theme.core_theme_generator import GrubTheme
from ui.tabs.ui_tab_theme_config import (
    TabThemeConfig,
    _on_activate_script,
    _on_activate_theme,
    _on_open_editor,
    _on_preview_theme,
    _on_theme_selected,
    _on_theme_switch_toggled,
    _scan_grub_scripts,
)
from ui.ui_state import AppStateManager


@pytest.fixture
def mock_state_manager():
    return MagicMock()


@pytest.fixture
def tab_theme_config(mock_state_manager):
    return TabThemeConfig(mock_state_manager)


def test_init(tab_theme_config):
    """Test l'initialisation."""
    assert tab_theme_config.current_theme is None
    assert tab_theme_config.available_themes == {}


def test_build(tab_theme_config):
    """Test la construction de l'interface."""
    with patch.object(tab_theme_config, "_load_themes") as mock_load:
        box = tab_theme_config.build()
        assert isinstance(box, Gtk.Box)
        assert mock_load.called
        assert tab_theme_config.theme_list_box is not None
        assert tab_theme_config.activate_btn is not None
        assert tab_theme_config.preview_btn is not None
        assert tab_theme_config.theme_switch is not None


def test_load_themes_active(tab_theme_config):
    """Test le chargement des thèmes avec un thème actif."""
    mock_theme = GrubTheme(name="MyTheme")

    with (
        patch.object(tab_theme_config.theme_manager, "load_active_theme", return_value=mock_theme),
        patch.object(tab_theme_config.theme_service, "is_theme_enabled_in_grub", return_value=True),
        patch.object(tab_theme_config, "_scan_system_themes") as mock_scan,
        patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts") as mock_scan_scripts,
    ):

        tab_theme_config.build()
        tab_theme_config._load_themes()

        assert tab_theme_config.current_theme == mock_theme
        assert tab_theme_config.theme_switch.get_active()
        # _scan_system_themes est appelé explicitement dans _load_themes quand un thème est actif
        assert mock_scan.called
        assert mock_scan_scripts.called


def test_load_themes_no_active(tab_theme_config):
    """Test le chargement des thèmes sans thème actif."""
    with (
        patch.object(tab_theme_config.theme_manager, "load_active_theme", return_value=None),
        patch.object(tab_theme_config, "_scan_system_themes"),
    ):

        tab_theme_config.build()
        tab_theme_config._load_themes()

        assert tab_theme_config.current_theme is None
        assert not tab_theme_config.theme_switch.get_active()


def test_scan_system_themes(tab_theme_config):
    """Test le scan des thèmes système."""
    tab_theme_config.build()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.iterdir.return_value = []

    with patch("ui.tabs.ui_tab_theme_config.get_all_grub_themes_dirs", return_value=[mock_path]):
        tab_theme_config._scan_system_themes()
        # Si aucun thème trouvé, on ajoute un placeholder
        assert tab_theme_config.theme_list_box.get_first_child() is not None


def test_scan_system_themes_found(tab_theme_config):
    """Test le scan avec des thèmes trouvés."""
    tab_theme_config.build()

    mock_theme = GrubTheme(name="MyTheme")
    mock_path = Path("/path/to/MyTheme")

    with patch.object(
        tab_theme_config.theme_service, "scan_system_themes", return_value={"MyTheme": (mock_theme, mock_path)}
    ):
        tab_theme_config._scan_system_themes()

        assert "MyTheme" in tab_theme_config.available_themes
        # Vérifier qu'une ligne a été ajoutée (pas le placeholder)
        row = tab_theme_config.theme_list_box.get_first_child()
        assert row is not None
        # On pourrait vérifier le contenu du label mais c'est complexe avec l'UI


def test_on_theme_selected(tab_theme_config):
    """Test la sélection d'un thème."""
    tab_theme_config.build()

    mock_theme = GrubTheme(name="MyTheme")
    tab_theme_config.available_themes = {"MyTheme": mock_theme}

    # Simuler une ligne
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0

    _on_theme_selected(tab_theme_config.theme_list_box, row, tab_theme_config)

    assert tab_theme_config.current_theme == mock_theme
    assert tab_theme_config.activate_btn.get_sensitive()
    assert tab_theme_config.preview_btn.get_sensitive()


def test_on_theme_selected_none(tab_theme_config):
    """Test la désélection d'un thème."""
    tab_theme_config.build()
    _on_theme_selected(tab_theme_config.theme_list_box, None, tab_theme_config)

    assert tab_theme_config.current_theme is None
    assert not tab_theme_config.activate_btn.get_sensitive()
    assert not tab_theme_config.preview_btn.get_sensitive()


def test_on_theme_switch_toggled(tab_theme_config):
    """Test le basculement du switch."""
    tab_theme_config.build()

    with (
        patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts") as mock_scan_scripts,
        patch.object(tab_theme_config, "_scan_system_themes") as mock_scan_themes,
    ):

        tab_theme_config.theme_switch.set_active(True)
        # Le signal notify::active est émis
        # Mais comme on n'est pas dans une boucle GTK, on appelle directement
        _on_theme_switch_toggled(tab_theme_config.theme_switch, None, tab_theme_config)

        assert mock_scan_scripts.called
        assert mock_scan_themes.called
        assert tab_theme_config.theme_sections_container.get_visible()


def test_scan_grub_scripts(tab_theme_config):
    """Test le scan des scripts."""
    tab_theme_config.build()

    mock_script = MagicMock()
    mock_script.name = "Script 1"
    mock_script.is_executable = True
    mock_script.path = "/etc/grub.d/01_script"

    with patch.object(tab_theme_config.script_service, "scan_theme_scripts", return_value=[mock_script]):
        _scan_grub_scripts(tab_theme_config)

        assert tab_theme_config.scripts_info_box.get_first_child() is not None


def test_on_activate_script_success(tab_theme_config):
    """Test l'activation réussie d'un script."""
    with (
        patch.object(tab_theme_config.script_service, "make_executable", return_value=True),
        patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts") as mock_scan,
        patch("ui.tabs.ui_tab_theme_config.create_success_dialog") as mock_dialog,
    ):

        _on_activate_script(MagicMock(), "/path/to/script", tab_theme_config)

        assert mock_dialog.called
        assert mock_scan.called


def test_on_activate_script_failure(tab_theme_config):
    """Test l'échec de l'activation d'un script."""
    with (
        patch.object(tab_theme_config.script_service, "make_executable", return_value=False),
        patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
    ):

        _on_activate_script(MagicMock(), "/path/to/script", tab_theme_config)

        assert mock_dialog.called


def test_on_activate_script_exceptions(tab_theme_config):
    """Test les exceptions lors de l'activation d'un script."""
    exceptions = [
        GrubCommandError("Cmd error"),
        GrubScriptNotFoundError("Not found"),
        PermissionError("Denied"),
        OSError("OS Error"),
    ]

    for exc in exceptions:
        with (
            patch.object(tab_theme_config.script_service, "make_executable", side_effect=exc),
            patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
        ):

            _on_activate_script(MagicMock(), "/path/to/script", tab_theme_config)
            assert mock_dialog.called


def test_on_open_editor(tab_theme_config):
    """Test l'ouverture de l'éditeur."""
    tab_theme_config.build()

    mock_window = MagicMock(spec=Gtk.Window)
    tab_theme_config.parent_window = mock_window

    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value

        _on_open_editor(tab_theme_config)

        assert mock_dialog.present.called


def test_on_open_editor_no_parent(tab_theme_config):
    """Test l'ouverture de l'éditeur sans fenêtre parente."""
    tab_theme_config.build()
    tab_theme_config.parent_window = None
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = None

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog:
        _on_open_editor(tab_theme_config, button)
        assert mock_dialog.called


def test_on_preview_theme(tab_theme_config):
    """Test l'aperçu du thème."""
    tab_theme_config.current_theme = GrubTheme(name="MyTheme")

    with patch("ui.tabs.ui_tab_theme_config.GrubPreviewDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value

        _on_preview_theme(tab_theme_config)

        assert mock_dialog.show.called


def test_on_preview_theme_no_selection(tab_theme_config):
    """Test l'aperçu sans sélection."""
    tab_theme_config.current_theme = None

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog:
        _on_preview_theme(tab_theme_config)
        assert mock_dialog.called


def test_on_activate_theme(tab_theme_config):
    """Test l'activation du thème."""
    tab_theme_config.current_theme = GrubTheme(name="MyTheme")

    with (
        patch.object(tab_theme_config.theme_manager, "save_active_theme") as mock_save,
        patch("ui.tabs.ui_tab_theme_config.create_success_dialog") as mock_dialog,
    ):

        _on_activate_theme(tab_theme_config)

        assert tab_theme_config.theme_manager.active_theme == tab_theme_config.current_theme
        assert mock_save.called
        assert mock_dialog.called


def test_on_activate_theme_no_selection(tab_theme_config):
    """Test l'activation sans sélection."""
    tab_theme_config.current_theme = None

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog:
        _on_activate_theme(tab_theme_config)
        assert mock_dialog.called


def test_on_activate_theme_error(tab_theme_config):
    """Test l'erreur lors de l'activation."""
    tab_theme_config.current_theme = GrubTheme(name="MyTheme")

    with (
        patch.object(tab_theme_config.theme_manager, "save_active_theme", side_effect=OSError("Save error")),
        patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
    ):

        _on_activate_theme(tab_theme_config)
        assert mock_dialog.called


def test_load_themes_exception(tab_theme_config):
    """Test load_themes with exception."""
    with patch.object(tab_theme_config.theme_manager, "load_active_theme", side_effect=OSError("Load error")):
        tab_theme_config.build()
        tab_theme_config._load_themes()
        assert not tab_theme_config.theme_switch.get_active()


def test_scan_system_themes_dir_not_exists(tab_theme_config):
    """Test scan_system_themes with non-existent directory."""
    tab_theme_config.build()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False

    with patch("ui.tabs.ui_tab_theme_config.get_all_grub_themes_dirs", return_value=[mock_path]):
        tab_theme_config._scan_system_themes()
        # Should continue without error


def test_scan_system_themes_create_error(tab_theme_config):
    """Test scan_system_themes with error creating theme."""
    tab_theme_config.build()

    mock_theme_dir = MagicMock(spec=Path)
    mock_theme_dir.name = "MyTheme"
    mock_theme_dir.is_dir.return_value = True
    (mock_theme_dir / "theme.txt").exists.return_value = True

    mock_root = MagicMock(spec=Path)
    mock_root.exists.return_value = True
    mock_root.iterdir.return_value = [mock_theme_dir]

    with (
        patch("ui.tabs.ui_tab_theme_config.get_all_grub_themes_dirs", return_value=[mock_root]),
        patch("ui.tabs.ui_tab_theme_config.create_custom_theme", side_effect=ValueError("Invalid theme")),
    ):

        tab_theme_config._scan_system_themes()
        # Should catch exception and continue


def test_on_theme_switch_toggled_widgets_none(tab_theme_config):
    """Test on_theme_switch_toggled when widgets are None."""
    tab_theme_config.theme_list_box = None
    tab_theme_config.activate_btn = None
    tab_theme_config.preview_btn = None

    switch = MagicMock()
    switch.get_active.return_value = True

    with patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts"), patch.object(tab_theme_config, "_scan_system_themes"):
        _on_theme_switch_toggled(switch, None, tab_theme_config)
        # Should run without error


def test_scan_grub_scripts_no_box(tab_theme_config):
    """Test scan_grub_scripts when scripts_info_box is None."""
    tab_theme_config.scripts_info_box = None
    _scan_grub_scripts(tab_theme_config)
    # Should run without error


def test_scan_grub_scripts_empty(tab_theme_config):
    """Test scan_grub_scripts with no scripts found."""
    tab_theme_config.build()
    with patch.object(tab_theme_config.script_service, "scan_theme_scripts", return_value=[]):
        _scan_grub_scripts(tab_theme_config)
        # Should not add children


def test_scan_grub_scripts_not_executable(tab_theme_config):
    """Test scan_grub_scripts with non-executable script."""
    tab_theme_config.build()

    mock_script = MagicMock()
    mock_script.name = "Script 1"
    mock_script.is_executable = False
    mock_script.path = "/etc/grub.d/01_script"

    with patch.object(tab_theme_config.script_service, "scan_theme_scripts", return_value=[mock_script]):
        _scan_grub_scripts(tab_theme_config)
        # Should add activate button


def test_on_open_editor_exception(tab_theme_config):
    """Test on_open_editor with exception."""
    tab_theme_config.build()
    tab_theme_config.parent_window = MagicMock()

    with (
        patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog", side_effect=RuntimeError("Dialog error")),
        patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_dialog,
    ):

        _on_open_editor(tab_theme_config)
        assert mock_dialog.called


def test_on_preview_theme_exception(tab_theme_config):
    """Test _on_preview_theme with exception."""
    tab_theme_config.current_theme = MagicMock()
    tab_theme_config.current_theme.name = "test"

    with (
        patch("ui.tabs.ui_tab_theme_config.GrubPreviewDialog", side_effect=OSError("Preview fail")),
        patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_err,
    ):
        _on_preview_theme(tab_theme_config)
        assert mock_err.called


def test_on_theme_switch_toggled_inactive(tab_theme_config):
    """Test le basculement du switch inactif."""
    tab_theme_config.build()

    with (
        patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts") as mock_scan_scripts,
        patch.object(tab_theme_config, "_scan_system_themes") as mock_scan_themes,
    ):

        switch = MagicMock()
        switch.get_active.return_value = False

        _on_theme_switch_toggled(switch, None, tab_theme_config)

        assert not mock_scan_scripts.called
        assert not mock_scan_themes.called
        assert not tab_theme_config.theme_sections_container.get_visible()


def test_load_themes_scan_exception(tab_theme_config):
    """Test _load_themes with exception during scan."""
    mock_theme = GrubTheme(name="MyTheme")
    tab_theme_config.theme_switch = MagicMock()

    with (
        patch.object(tab_theme_config.theme_manager, "load_active_theme", return_value=mock_theme),
        patch.object(tab_theme_config, "_scan_system_themes", side_effect=OSError("Scan fail")),
    ):

        # Should catch exception and log error
        tab_theme_config._load_themes()
        # No assertion needed, just ensure it doesn't crash


def test_on_theme_selected_invalid_index(tab_theme_config):
    """Test _on_theme_selected with invalid index."""
    tab_theme_config.build()
    tab_theme_config.available_themes = {"MyTheme": GrubTheme(name="MyTheme")}
    tab_theme_config.current_theme = None

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 10  # Out of bounds

    _on_theme_selected(tab_theme_config.theme_list_box, row, tab_theme_config)

    # Should not change current theme (or keep it None)
    assert tab_theme_config.current_theme is None


def test_load_themes_inner_exception():
    """Test catching exception inside the inner try block of _load_themes."""
    mock_state_manager = MagicMock(spec=AppStateManager)

    tab = TabThemeConfig(mock_state_manager)

    # Setup mocks
    tab.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.script_service = MagicMock(spec=GrubScriptService)
    tab.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.available_themes = {}

    # Mock load_active_theme to raise OSError
    tab.theme_manager.load_active_theme.side_effect = OSError("Inner fail")

    tab._load_themes()

    # Verification
    tab.theme_switch.set_active.assert_called_with(False)


def test_load_themes_outer_exception():
    """Test catching exception in the outer try block of _load_themes."""
    mock_state_manager = MagicMock(spec=AppStateManager)

    tab = TabThemeConfig(mock_state_manager)

    # Setup mocks
    tab.theme_manager = MagicMock(spec=ActiveThemeManager)
    tab.script_service = MagicMock(spec=GrubScriptService)
    tab.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.available_themes = {}

    # We need to trigger an exception outside the inner try block.
    # The code after inner block is: logger.debug(...)
    # We can patch the logger used in the module.

    with patch("ui.tabs.ui_tab_theme_config.logger") as mock_logger:
        # Make the debug call raise an exception
        mock_logger.debug.side_effect = OSError("Outer fail")

        tab._load_themes()

        # Verify that the outer exception handler caught it
        mock_logger.error.assert_called_with("[TabThemeConfig._load_themes] Erreur: Outer fail")


def test_on_open_editor_exception_coverage():
    """Test exception handling in _on_open_editor."""
    mock_state_manager = MagicMock(spec=AppStateManager)

    tab = TabThemeConfig(mock_state_manager)
    tab.parent_window = MagicMock()  # Set parent window to avoid the search loop for this test

    # Mock ThemeEditorDialog to raise RuntimeError
    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog", side_effect=RuntimeError("Dialog fail")):
        # Also mock create_error_dialog to avoid UI calls
        with patch("ui.tabs.ui_tab_theme_config.create_error_dialog"):
            _on_open_editor(tab)


def test_on_open_editor_find_parent_window():
    """Test finding the parent window in _on_open_editor."""
    mock_state_manager = MagicMock(spec=AppStateManager)
    from ui.tabs.ui_tab_theme_config import _on_open_editor

    tab = TabThemeConfig(mock_state_manager)
    mock_window = MagicMock()
    mock_window.present = MagicMock()
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = mock_window

    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog"):
        _on_open_editor(tab, button)
        assert tab.parent_window == mock_window
