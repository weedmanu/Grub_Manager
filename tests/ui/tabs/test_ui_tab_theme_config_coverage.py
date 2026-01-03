from pathlib import Path
from unittest.mock import MagicMock, patch

import gi
import pytest

from core.theme.core_theme_generator import GrubTheme
from ui.tabs.ui_tab_theme_config import (
    TabThemeConfig,
    _on_activate_script,
    _on_delete_confirmed,
    _on_delete_theme,
    _on_edit_theme,
    _on_open_editor,
    _on_theme_selected,
)
from ui.ui_state import AppStateManager

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


@pytest.fixture
def mock_state_manager():
    manager = MagicMock(spec=AppStateManager)
    return manager

@pytest.fixture
def tab(mock_state_manager):
    with patch("ui.tabs.ui_tab_theme_config.ActiveThemeManager"), \
         patch("ui.tabs.ui_tab_theme_config.GrubScriptService"), \
         patch("ui.tabs.ui_tab_theme_config.ThemeService"):
        tab = TabThemeConfig(mock_state_manager)
        tab.theme_list_box = MagicMock(spec=Gtk.ListBox)
        # Prevent infinite loops in clearing loops
        tab.theme_list_box.get_first_child.return_value = None

        tab.activate_btn = MagicMock(spec=Gtk.Button)
        tab.preview_btn = MagicMock(spec=Gtk.Button)
        tab.edit_btn = MagicMock(spec=Gtk.Button)
        tab.delete_btn = MagicMock(spec=Gtk.Button)
        tab.parent_window = MagicMock(spec=Gtk.Window)

        tab.scripts_info_box = MagicMock(spec=Gtk.Box)
        tab.scripts_info_box.get_first_child.return_value = None

        return tab

def test_on_edit_theme_not_found(tab):
    """Teste _on_edit_theme quand le thème n'est pas trouvé."""
    tab.available_themes = {}
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_edit_theme(None, "Unknown", tab)
        mock_error.assert_called_once_with("Thème 'Unknown' introuvable")

def test_on_edit_theme_system(tab):
    """Teste _on_edit_theme quand le thème est un thème système."""
    tab.available_themes = {"System": GrubTheme(name="System")}
    tab.theme_paths = {"System": Path("/usr/share/grub/themes/System")}
    tab.theme_service.is_theme_custom.return_value = False

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_edit_theme(None, "System", tab)
        mock_error.assert_called_once_with("Ce thème système ne peut pas être modifié")

def test_on_edit_theme_success(tab):
    """Teste _on_edit_theme avec succès."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.theme_service.is_theme_custom.return_value = True

    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog") as mock_dialog:
        _on_edit_theme(None, "Custom", tab)
        mock_dialog.assert_called_once()

def test_on_edit_theme_no_parent(tab):
    """Teste _on_edit_theme sans fenêtre parente."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.theme_service.is_theme_custom.return_value = True
    tab.parent_window = None

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_edit_theme(None, "Custom", tab)
        mock_error.assert_called_once_with("Impossible d'ouvrir l'éditeur")

def test_on_edit_theme_exception(tab):
    """Teste _on_edit_theme avec une exception."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.theme_service.is_theme_custom.side_effect = RuntimeError("Test Error")

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_edit_theme(None, "Custom", tab)
        assert mock_error.called

def test_on_delete_theme_not_found(tab):
    """Teste _on_delete_theme quand le thème n'est pas trouvé."""
    tab.available_themes = {}
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_delete_theme(None, "Unknown", tab)
        mock_error.assert_called_once_with("Thème 'Unknown' introuvable")

def test_on_delete_theme_system(tab):
    """Teste _on_delete_theme quand le thème est un thème système."""
    tab.available_themes = {"System": GrubTheme(name="System")}
    tab.theme_paths = {"System": Path("/usr/share/grub/themes/System")}
    tab.theme_service.is_theme_custom.return_value = False

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_delete_theme(None, "System", tab)
        mock_error.assert_called_once_with("Les thèmes système ne peuvent pas être supprimés")

def test_on_delete_theme_success(tab):
    """Teste _on_delete_theme avec succès (ouverture du dialogue)."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.theme_service.is_theme_custom.return_value = True

    with patch("ui.tabs.ui_tab_theme_config.Gtk.AlertDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        _on_delete_theme(None, "Custom", tab)
        mock_dialog.choose.assert_called_once()

def test_on_delete_theme_exception(tab):
    """Teste _on_delete_theme avec une exception."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/home/user/.local/share/grub/themes/Custom")}
    tab.theme_service.is_theme_custom.side_effect = RuntimeError("Test Error")

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_delete_theme(None, "Custom", tab)
        assert mock_error.called

def test_on_delete_confirmed_yes(tab):
    """Teste _on_delete_confirmed quand l'utilisateur confirme."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 1 # Supprimer

    theme_name = "Custom"
    theme_path = Path("/home/user/.local/share/grub/themes/Custom")
    user_data = (theme_name, theme_path, tab)

    tab.theme_service.delete_theme.return_value = True
    tab._scan_system_themes = MagicMock()

    with patch("ui.tabs.ui_tab_theme_config.create_success_dialog") as mock_success:
        _on_delete_confirmed(mock_dialog, None, user_data)
        tab.theme_service.delete_theme.assert_called_once_with(theme_path)
        mock_success.assert_called_once()
        tab._scan_system_themes.assert_called_once()

def test_on_delete_confirmed_no(tab):
    """Teste _on_delete_confirmed quand l'utilisateur annule."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 0 # Annuler

    user_data = ("Custom", Path("/path"), tab)

    _on_delete_confirmed(mock_dialog, None, user_data)
    assert not tab.theme_service.delete_theme.called

def test_on_delete_confirmed_failure(tab):
    """Teste _on_delete_confirmed quand la suppression échoue."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.return_value = 1

    user_data = ("Custom", Path("/path"), tab)
    tab.theme_service.delete_theme.return_value = False
    tab._scan_system_themes = MagicMock()

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_delete_confirmed(mock_dialog, None, user_data)
        mock_error.assert_called_once()
        tab._scan_system_themes.assert_called_once()

def test_on_delete_confirmed_exception(tab):
    """Teste _on_delete_confirmed avec une exception."""
    mock_dialog = MagicMock(spec=Gtk.AlertDialog)
    mock_dialog.choose_finish.side_effect = RuntimeError("Test Error")
    tab._scan_system_themes = MagicMock()

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_delete_confirmed(mock_dialog, None, None)
        assert mock_error.called

def test_on_theme_selected_custom(tab):
    """Teste _on_theme_selected avec un thème custom."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/path")}
    tab.theme_service.is_theme_custom.return_value = True

    _on_theme_selected(tab.theme_list_box, row, tab)

    assert tab.edit_btn.set_sensitive.called
    assert tab.delete_btn.set_sensitive.called
    # Vérifier que set_sensitive(True) a été appelé pour edit/delete
    tab.edit_btn.set_sensitive.assert_called_with(True)
    tab.delete_btn.set_sensitive.assert_called_with(True)

def test_on_theme_selected_system(tab):
    """Teste _on_theme_selected avec un thème système."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.available_themes = {"System": GrubTheme(name="System")}
    tab.theme_paths = {"System": Path("/path")}
    tab.theme_service.is_theme_custom.return_value = False

    _on_theme_selected(tab.theme_list_box, row, tab)

    tab.edit_btn.set_sensitive.assert_called_with(False)
    tab.delete_btn.set_sensitive.assert_called_with(False)

def test_tab_build(tab):
    """Teste la construction de l'interface."""
    with patch("ui.tabs.ui_tab_theme_config.create_main_box") as mock_main_box, \
         patch("ui.tabs.ui_tab_theme_config.create_two_column_layout") as mock_layout:

        mock_main_box.return_value = MagicMock(spec=Gtk.Box)
        mock_layout.return_value = (MagicMock(spec=Gtk.Box), MagicMock(spec=Gtk.Box), MagicMock(spec=Gtk.Box))

        res = tab.build()
        assert res == mock_main_box.return_value
        assert tab.theme_sections_container is not None

def test_tab_refresh(tab):
    """Teste le rafraîchissement de l'onglet."""
    tab._scan_system_themes = MagicMock()
    with patch("ui.tabs.ui_tab_theme_config._scan_grub_scripts") as mock_scan:
        tab.refresh()
        mock_scan.assert_called_once_with(tab)
        tab._scan_system_themes.assert_called_once()

def test_load_themes_enabled(tab):
    """Teste le chargement des thèmes quand ils sont activés dans GRUB."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = GrubTheme(name="Active")
    tab.refresh = MagicMock()
    tab.theme_list_box.get_row_at_index.return_value = MagicMock(spec=Gtk.ListBoxRow)
    tab.available_themes = {"Active": tab.theme_manager.load_active_theme.return_value}

    tab._load_themes()

    assert tab.current_theme.name == "Active"
    tab.refresh.assert_called_once()
    tab.theme_list_box.select_row.assert_called_once()

def test_load_themes_disabled(tab):
    """Teste le chargement des thèmes quand ils sont désactivés dans GRUB."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = False
    tab.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()

    tab._load_themes()

    assert not tab.refresh.called

def test_scan_system_themes_empty(tab):
    """Teste le scan des thèmes quand aucun n'est trouvé."""
    tab.theme_service.scan_system_themes.return_value = {}
    tab.theme_list_box.get_first_child.side_effect = [MagicMock(), None]

    tab._scan_system_themes()

    tab.theme_list_box.append.assert_called_once() # Placeholder

def test_scan_system_themes_with_data(tab):
    """Teste le scan des thèmes avec des résultats."""
    theme = GrubTheme(name="Test")
    path = Path("/path/to/theme")
    tab.theme_service.scan_system_themes.return_value = {"Test": (theme, path)}
    tab.theme_list_box.get_first_child.return_value = None

    tab._scan_system_themes()

    assert "Test" in tab.available_themes
    assert tab.theme_list_box.append.called

def test_on_theme_switch_toggled_on(tab):
    """Teste le basculement du switch sur ON."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.theme_sections_container = MagicMock(spec=Gtk.Box)
    tab.refresh = MagicMock()
    tab.available_themes = {"T": MagicMock()}
    tab.theme_list_box.get_row_at_index.return_value = MagicMock()

    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)

    tab.theme_sections_container.set_visible.assert_called_with(True)
    tab.refresh.assert_called_once()

def test_on_theme_switch_toggled_off(tab):
    """Teste le basculement du switch sur OFF."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = False
    tab.theme_sections_container = MagicMock(spec=Gtk.Box)

    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)

    tab.theme_sections_container.set_visible.assert_called_with(False)

def test_on_activate_theme(tab):
    """Teste l'activation d'un thème."""
    tab.current_theme = GrubTheme(name="Test")
    from ui.tabs.ui_tab_theme_config import _on_activate_theme
    with patch("ui.tabs.ui_tab_theme_config.create_success_dialog"):
        _on_activate_theme(tab)
        assert tab.theme_manager.active_theme == tab.current_theme
        tab.theme_manager.save_active_theme.assert_called_once()
        tab.state_manager.mark_dirty.assert_called_once()

def test_on_preview_theme(tab):
    """Teste la prévisualisation d'un thème."""
    tab.current_theme = GrubTheme(name="Test")
    from ui.tabs.ui_tab_theme_config import _on_preview_theme
    with patch("ui.tabs.ui_tab_theme_config.GrubPreviewDialog") as mock_dialog:
        _on_preview_theme(tab)
        mock_dialog.assert_called_once_with(tab.current_theme)

def test_on_open_editor(tab):
    """Teste l'ouverture de l'éditeur."""
    from ui.tabs.ui_tab_theme_config import _on_open_editor
    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog") as mock_dialog:
        _on_open_editor(tab)
        mock_dialog.assert_called_once()

def test_scan_grub_scripts(tab):
    """Teste le scan des scripts GRUB."""
    tab.scripts_info_box = MagicMock(spec=Gtk.Box)
    tab.scripts_info_box.get_first_child.side_effect = [MagicMock(), None]

    script = MagicMock()
    script.name = "00_header"
    script.path = Path("/etc/grub.d/00_header")
    script.is_executable = False

    tab.script_service.scan_theme_scripts.return_value = [script]

    from ui.tabs.ui_tab_theme_config import _scan_grub_scripts
    _scan_grub_scripts(tab)

    assert tab.scripts_info_box.append.called

def test_on_activate_script_success(tab):
    """Teste l'activation d'un script avec succès."""
    tab.script_service.make_executable.return_value = True
    tab.refresh = MagicMock()

    from ui.tabs.ui_tab_theme_config import _on_activate_script
    with patch("ui.tabs.ui_tab_theme_config.create_success_dialog"):
        _on_activate_script(None, "/path/to/script", tab)
        tab.script_service.make_executable.assert_called_once()
        tab.refresh.assert_called_once()

def test_load_themes_no_active_theme_exception(tab):
    """Teste _load_themes quand le chargement du thème actif lève une exception."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.side_effect = RuntimeError("No active theme")
    tab.refresh = MagicMock()

    tab._load_themes()

    assert tab.refresh.called

def test_load_themes_global_exception(tab):
    """Teste _load_themes quand une exception globale survient."""
    tab.theme_service.is_theme_enabled_in_grub.side_effect = RuntimeError("Global error")

    tab._load_themes() # Ne doit pas lever d'exception

def test_on_theme_selected_no_index(tab):
    """Teste _on_theme_selected avec un index invalide."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = -1
    tab.available_themes = {"T": MagicMock()}

    from ui.tabs.ui_tab_theme_config import _on_theme_selected
    _on_theme_selected(tab.theme_list_box, row, tab)

    assert not tab.activate_btn.set_sensitive.called

def test_on_activate_script_errors(tab):
    """Teste les erreurs dans _on_activate_script."""
    from ui.tabs.ui_tab_theme_config import GrubCommandError, GrubScriptNotFoundError, _on_activate_script

    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        # GrubCommandError
        tab.script_service.make_executable.side_effect = GrubCommandError("Cmd error")
        _on_activate_script(None, "/path", tab)
        assert mock_error.called

        # GrubScriptNotFoundError
        tab.script_service.make_executable.side_effect = GrubScriptNotFoundError("Not found")
        _on_activate_script(None, "/path", tab)
        assert mock_error.called

        # PermissionError
        tab.script_service.make_executable.side_effect = PermissionError("Perm error")
        _on_activate_script(None, "/path", tab)
        assert mock_error.called

        # OSError
        tab.script_service.make_executable.side_effect = OSError("OS error")
        _on_activate_script(None, "/path", tab)
        assert mock_error.called

def test_on_open_editor_no_parent(tab):
    """Teste _on_open_editor sans fenêtre parente."""
    tab.parent_window = None
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = None
    from ui.tabs.ui_tab_theme_config import _on_open_editor
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_open_editor(tab, button)
        mock_error.assert_called_once_with("Impossible d'ouvrir l'éditeur")

def test_on_preview_theme_no_selection(tab):
    """Teste _on_preview_theme sans sélection."""
    tab.current_theme = None
    from ui.tabs.ui_tab_theme_config import _on_preview_theme
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_preview_theme(tab)
        mock_error.assert_called_once_with("Veuillez sélectionner un thème")

def test_on_activate_theme_no_selection(tab):
    """Teste _on_activate_theme sans sélection."""
    tab.current_theme = None
    from ui.tabs.ui_tab_theme_config import _on_activate_theme
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_activate_theme(tab)
        mock_error.assert_called_once_with("Veuillez sélectionner un thème")

def test_on_theme_selected_no_preview(tab):
    """Teste _on_theme_selected avec un thème sans aperçu."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.available_themes = {"None": GrubTheme(name="Aucun (GRUB par défaut)")}
    tab.theme_paths = {"None": Path("/path")}
    tab.theme_service.is_theme_custom.return_value = False

    from ui.tabs.ui_tab_theme_config import _on_theme_selected
    _on_theme_selected(tab.theme_list_box, row, tab)

    tab.preview_btn.set_sensitive.assert_called_with(False)

def test_scan_grub_scripts_executable(tab):
    """Teste le scan des scripts GRUB avec un script déjà exécutable."""
    tab.scripts_info_box = MagicMock(spec=Gtk.Box)
    tab.scripts_info_box.get_first_child.side_effect = [None]

    script = MagicMock()
    script.name = "00_header"
    script.path = Path("/etc/grub.d/00_header")
    script.is_executable = True

    tab.script_service.scan_theme_scripts.return_value = [script]

    from ui.tabs.ui_tab_theme_config import _scan_grub_scripts
    _scan_grub_scripts(tab)

    assert tab.scripts_info_box.append.called

def test_on_activate_script_failure(tab):
    """Teste l'échec de l'activation d'un script."""
    tab.script_service.make_executable.return_value = False

    from ui.tabs.ui_tab_theme_config import _on_activate_script
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_activate_script(None, "/path/to/script", tab)
        mock_error.assert_called_once()

def test_on_open_editor_with_root(tab):
    """Teste _on_open_editor en trouvant le root."""
    tab.parent_window = None
    mock_root = MagicMock(spec=Gtk.Window)
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = mock_root

    from ui.tabs.ui_tab_theme_config import _on_open_editor
    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog") as mock_dialog:
        _on_open_editor(tab, button)
        mock_dialog.assert_called_once()

def test_on_preview_theme_exception(tab):
    """Teste _on_preview_theme avec une exception."""
    tab.current_theme = GrubTheme(name="Test")
    from ui.tabs.ui_tab_theme_config import _on_preview_theme
    with patch("ui.tabs.ui_tab_theme_config.GrubPreviewDialog", side_effect=RuntimeError("Preview error")):
        with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
            _on_preview_theme(tab)
            assert mock_error.called

def test_on_activate_theme_exception(tab):
    """Teste _on_activate_theme avec une exception."""
    tab.current_theme = GrubTheme(name="Test")
    tab.theme_manager.save_active_theme.side_effect = RuntimeError("Save error")
    from ui.tabs.ui_tab_theme_config import _on_activate_theme
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_activate_theme(tab)
        assert mock_error.called

def test_load_themes_no_active_theme(tab):
    """Teste _load_themes quand aucun thème n'est actif."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()

    tab._load_themes()

    assert tab.current_theme is None
    assert tab.refresh.called

def test_load_themes_no_available_themes(tab):
    """Teste _load_themes quand aucun thème n'est disponible."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    tab.available_themes = {}

    tab._load_themes()

    assert not tab.theme_list_box.select_row.called

def test_scan_system_themes_no_list_box(tab):
    """Teste _scan_system_themes sans list_box."""
    tab.theme_list_box = None
    tab._scan_system_themes()
    assert tab.theme_service.scan_system_themes.called == False

def test_on_theme_selected_row_none(tab):
    """Teste _on_theme_selected avec row=None."""
    _on_theme_selected(tab.theme_list_box, None, tab)
    assert tab.current_theme is None
    tab.activate_btn.set_sensitive.assert_called_with(False)

def test_on_theme_selected_no_buttons(tab):
    """Teste _on_theme_selected sans boutons définis."""
    tab.activate_btn = None
    tab.preview_btn = None
    tab.edit_btn = None
    tab.delete_btn = None

    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.available_themes = {"T": GrubTheme(name="T")}

    # Ne doit pas lever d'exception
    _on_theme_selected(tab.theme_list_box, row, tab)

    # Cas row is None
    _on_theme_selected(tab.theme_list_box, None, tab)

def test_on_theme_selected_theme_not_in_paths(tab):
    """Teste _on_theme_selected quand le thème n'est pas dans theme_paths."""
    row = MagicMock(spec=Gtk.ListBoxRow)
    row.get_index.return_value = 0
    tab.available_themes = {"T": GrubTheme(name="T")}
    tab.theme_paths = {} # Vide

    _on_theme_selected(tab.theme_list_box, row, tab)

    tab.edit_btn.set_sensitive.assert_called_with(False)

def test_on_theme_switch_toggled_no_container(tab):
    """Teste _on_theme_switch_toggled sans container."""
    tab.theme_sections_container = None
    tab.refresh = MagicMock()
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True

    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)
    # Ne doit pas lever d'exception

def test_on_theme_switch_toggled_no_list_box(tab):
    """Teste _on_theme_switch_toggled sans list_box."""
    tab.theme_list_box = None
    tab.refresh = MagicMock()
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.available_themes = {"T": MagicMock()}

    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)
    # Ne doit pas lever d'exception

def test_scan_grub_scripts_no_box(tab):
    """Teste _scan_grub_scripts sans scripts_info_box."""
    tab.scripts_info_box = None
    from ui.tabs.ui_tab_theme_config import _scan_grub_scripts
    _scan_grub_scripts(tab)
    assert not tab.script_service.scan_theme_scripts.called

def test_scan_grub_scripts_empty(tab):
    """Teste _scan_grub_scripts quand aucun script n'est trouvé."""
    tab.scripts_info_box = MagicMock(spec=Gtk.Box)
    tab.scripts_info_box.get_first_child.return_value = None
    tab.script_service.scan_theme_scripts.return_value = []

    from ui.tabs.ui_tab_theme_config import _scan_grub_scripts
    _scan_grub_scripts(tab)

    assert not tab.scripts_info_box.append.called

def test_on_open_editor_root_no_present(tab):
    """Teste _on_open_editor quand le root n'a pas de méthode present."""
    tab.parent_window = None
    mock_root = MagicMock() # Pas de spec Gtk.Window, donc pas de present() par défaut
    del mock_root.present
    button = MagicMock(spec=Gtk.Button)
    button.get_root.return_value = mock_root

    from ui.tabs.ui_tab_theme_config import _on_open_editor
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_error:
        _on_open_editor(tab, button)
        mock_error.assert_called_once()

def test_on_activate_theme_no_mark_dirty(tab):
    """Teste _on_activate_theme quand state_manager n'a pas mark_dirty."""
    tab.current_theme = GrubTheme(name="Test")
    del tab.state_manager.mark_dirty

    from ui.tabs.ui_tab_theme_config import _on_activate_theme
    with patch("ui.tabs.ui_tab_theme_config.create_success_dialog"):
        _on_activate_theme(tab)
        # Ne doit pas lever d'exception

def test_on_delete_theme_no_parent_no_button(tab):
    """Teste _on_delete_theme sans parent et sans bouton."""
    tab.available_themes = {"Custom": GrubTheme(name="Custom")}
    tab.theme_paths = {"Custom": Path("/path")}
    tab.theme_service.is_theme_custom.return_value = True
    tab.parent_window = None

    with patch("ui.tabs.ui_tab_theme_config.Gtk.AlertDialog") as mock_dialog_class:
        _on_delete_theme(None, "Custom", tab)
        # Vérifier que choose a été appelé
        assert mock_dialog_class.return_value.choose.called

def test_on_activate_script_oserror(tab):
    """Teste _on_activate_script avec OSError."""
    tab.script_service.make_executable.side_effect = OSError("OS Error")
    with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_err:
        _on_activate_script(MagicMock(), "/path/to/script", tab)
        mock_err.assert_called()

def test_on_delete_theme_no_parent_with_button(tab):
    """Teste _on_delete_theme sans parent_window mais avec un bouton."""
    tab.parent_window = None
    tab.available_themes = {"custom": MagicMock()}
    tab.theme_paths = {"custom": "/home/user/.local/share/grub/themes/custom"}
    tab.theme_service.is_theme_custom.return_value = True

    button = MagicMock()
    mock_root = MagicMock()
    button.get_root.return_value = mock_root

    with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
        mock_dialog = MockDialog.return_value
        _on_delete_theme(button, "custom", tab)
        mock_dialog.choose.assert_called()
        # Vérifier que le parent passé à choose est mock_root
        args, kwargs = mock_dialog.choose.call_args
        assert kwargs['parent'] == mock_root

def test_on_open_editor_exception(tab):
    """Teste _on_open_editor avec une exception."""
    tab.parent_window = MagicMock()
    with patch("ui.tabs.ui_tab_theme_config.ThemeEditorDialog", side_effect=RuntimeError("Editor Error")):
        with patch("ui.tabs.ui_tab_theme_config.create_error_dialog") as mock_err:
            _on_open_editor(tab)
            mock_err.assert_called()

def test_scan_system_themes_custom_badge(tab):
    """Teste _scan_system_themes avec un badge 'Custom'."""
    mock_theme = GrubTheme(name="custom_theme")
    tab.theme_service.scan_system_themes.return_value = {"custom_theme": (mock_theme, Path("/path/to/custom"))}
    tab.theme_service.is_theme_custom.return_value = True
    tab._scan_system_themes()
    assert tab.theme_list_box.append.called

def test_load_themes_with_container(tab):
    """Teste _load_themes avec un container de sections."""
    tab.theme_sections_container = MagicMock(spec=Gtk.Box)
    tab.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    # Mock available_themes to trigger selection branch
    tab.available_themes = {"T": MagicMock()}
    mock_row = MagicMock(spec=Gtk.ListBoxRow)
    tab.theme_list_box.get_row_at_index.return_value = mock_row

    tab._load_themes()
    tab.theme_sections_container.set_visible.assert_called_with(True)
    tab.theme_list_box.select_row.assert_called_with(mock_row)

def test_on_theme_switch_toggled_select_first(tab):
    """Teste _on_theme_switch_toggled sélectionne le premier thème."""
    tab.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.theme_list_box.get_first_child.return_value = None
    # Mock scan_system_themes to populate available_themes
    tab.theme_service.scan_system_themes.return_value = {"T": (MagicMock(), Path("/path"))}

    mock_row = MagicMock(spec=Gtk.ListBoxRow)
    tab.theme_list_box.get_row_at_index.return_value = mock_row

    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True

    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)

    tab.theme_list_box.select_row.assert_called_with(mock_row)

def test_on_theme_switch_toggled_no_themes(tab):
    """Teste _on_theme_switch_toggled quand aucun thème n'est disponible."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.available_themes = {}
    tab.refresh = MagicMock()
    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)
    tab.theme_list_box.select_row.assert_not_called()

def test_load_themes_active_theme_exception(tab):
    """Teste _load_themes avec une exception lors du chargement du thème actif."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.side_effect = RuntimeError("Test error")
    tab.refresh = MagicMock()

    # Ne devrait pas planter
    tab._load_themes()
    # Vérifier que la suite s'est exécutée
    tab.refresh.assert_called()

def test_load_themes_global_exception_real(tab):
    """Teste _load_themes avec une exception globale."""
    tab.theme_service.is_theme_enabled_in_grub.side_effect = RuntimeError("Global error")

    # Ne devrait pas planter
    tab._load_themes()

def test_load_themes_no_sections_container(tab):
    """Teste _load_themes sans container de sections."""
    tab.theme_switch = MagicMock(spec=Gtk.Switch)
    tab.theme_sections_container = None
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = None
    tab.refresh = MagicMock()
    tab._load_themes()
    # Devrait passer sans erreur

def test_load_themes_no_first_row(tab):
    """Teste _load_themes quand get_row_at_index(0) retourne None."""
    tab.theme_service.is_theme_enabled_in_grub.return_value = True
    tab.theme_manager.load_active_theme.return_value = None
    tab.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.theme_list_box.get_row_at_index.return_value = None
    tab.available_themes = {"T": MagicMock()}
    tab.refresh = MagicMock()
    tab._load_themes()
    tab.theme_list_box.select_row.assert_not_called()

def test_on_theme_switch_toggled_no_first_row(tab):
    """Teste _on_theme_switch_toggled quand get_row_at_index(0) retourne None."""
    switch = MagicMock(spec=Gtk.Switch)
    switch.get_active.return_value = True
    tab.theme_list_box = MagicMock(spec=Gtk.ListBox)
    tab.theme_list_box.get_row_at_index.return_value = None
    tab.available_themes = {"T": MagicMock()}
    tab.refresh = MagicMock()
    from ui.tabs.ui_tab_theme_config import _on_theme_switch_toggled
    _on_theme_switch_toggled(switch, None, tab)
    tab.theme_list_box.select_row.assert_not_called()

def test_scan_system_themes_system_badge(tab):
    """Teste _scan_system_themes avec un badge 'Système'."""
    mock_theme = GrubTheme(name="system_theme")
    tab.theme_service.scan_system_themes.return_value = {"system_theme": (mock_theme, Path("/usr/share/grub/themes/system_theme"))}
    tab.theme_service.is_theme_custom.return_value = False
    tab._scan_system_themes()
    assert tab.theme_list_box.append.called
