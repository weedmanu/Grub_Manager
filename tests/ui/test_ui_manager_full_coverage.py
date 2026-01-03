import dataclasses
import os
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest
from gi.repository import Gtk

from core.system.core_grub_system_commands import GrubDefaultChoice, GrubUiModel, GrubUiState
from core.system.core_sync_checker import SyncStatus
from ui.ui_manager import ERROR, INFO, WARNING, GrubConfigManager
from ui.ui_state import AppState


@pytest.fixture
def manager():
    with patch("ui.ui_manager.UIBuilder.create_main_ui"), \
         patch("ui.ui_manager.load_grub_ui_state") as mock_load, \
         patch("ui.ui_manager.check_grub_sync") as mock_sync, \
         patch("ui.ui_manager.render_entries_view"), \
         patch("ui.ui_manager.os.geteuid", return_value=0), \
         patch("ui.ui_manager.GrubConfigManager.create_ui"), \
         patch("ui.ui_manager.GrubConfigManager.load_config"): # Mock load_config to avoid apply_state with None buttons

        mock_load.return_value = GrubUiState(
            model=GrubUiModel(timeout=5, default="0"),
            entries=[],
            raw_config={}
        )
        mock_sync.return_value = SyncStatus(
            in_sync=True,
            message="OK",
            grub_default_exists=True,
            grub_cfg_exists=True,
            grub_default_mtime=0.0,
            grub_cfg_mtime=0.0
        )

        mgr = GrubConfigManager(None)
        # Mock widgets that would be created by UIBuilder
        mgr.save_btn = Gtk.Button()
        mgr.reload_btn = Gtk.Button()
        mgr.info_revealer = Gtk.Revealer()
        mgr.info_box = Gtk.Box()
        mgr.info_label = Gtk.Label()

        mgr.timeout_dropdown = Gtk.DropDown.new_from_strings(["0", "5", "10"])
        mgr.default_dropdown = Gtk.DropDown.new_from_strings(["saved", "Entry 1"])
        mgr.hidden_timeout_check = Gtk.Switch()
        mgr.cmdline_dropdown = Gtk.DropDown.new_from_strings(["quiet splash", "quiet", "splash", "verbose"])
        mgr.gfxmode_dropdown = Gtk.DropDown.new_from_strings(["auto", "1024x768"])
        mgr.gfxpayload_dropdown = Gtk.DropDown.new_from_strings(["keep", "text"])
        mgr.disable_submenu_check = Gtk.Switch()
        mgr.disable_recovery_check = Gtk.Switch()
        mgr.disable_os_prober_check = Gtk.Switch()

        return mgr

def test_get_cmdline_value_full(manager):
    # quiet splash
    manager.cmdline_dropdown.set_selected(0)
    assert manager._get_cmdline_value() == "quiet splash"

    # quiet
    manager.cmdline_dropdown.set_selected(1)
    assert manager._get_cmdline_value() == "quiet"

    # splash
    manager.cmdline_dropdown.set_selected(2)
    assert manager._get_cmdline_value() == "splash"

    # verbose
    manager.cmdline_dropdown.set_selected(3)
    assert manager._get_cmdline_value() == ""

    # None case
    manager.cmdline_dropdown = None
    assert manager._get_cmdline_value() == "quiet splash"

def test_apply_model_to_ui_full(manager):
    model = GrubUiModel(
        timeout=10,
        default="id1",
        hidden_timeout=True,
        quiet=True,
        splash=True,
        gfxmode="1024x768",
        gfxpayload_linux="keep",
        disable_submenu=True,
        disable_recovery=False,
        disable_os_prober=True
    )
    entries = [GrubDefaultChoice(id="id1", title="Title 1")]

    manager._apply_model_to_ui(model, entries)

    # Check cmdline_dropdown (quiet splash -> index 0)
    assert manager.cmdline_dropdown.get_selected() == 0

    # quiet only
    model = dataclasses.replace(model, splash=False)
    manager._apply_model_to_ui(model, entries)
    assert manager.cmdline_dropdown.get_selected() == 1

    # splash only
    model = dataclasses.replace(model, quiet=False, splash=True)
    manager._apply_model_to_ui(model, entries)
    assert manager.cmdline_dropdown.get_selected() == 2

    # verbose
    model = dataclasses.replace(model, quiet=False, splash=False)
    manager._apply_model_to_ui(model, entries)
    assert manager.cmdline_dropdown.get_selected() == 3

def test_read_model_from_ui_full(manager):
    manager.timeout_dropdown.set_selected(1) # 5
    manager.hidden_timeout_check.set_active(True)
    manager.cmdline_dropdown.set_selected(0) # quiet splash
    manager.disable_submenu_check.set_active(True)
    manager.gfxmode_dropdown.set_selected(1) # 1024x768
    manager.gfxpayload_dropdown.set_selected(1) # text

    with patch("core.theme.core_active_theme_manager.ActiveThemeManager") as mock_theme_mgr:
        mock_theme_mgr.return_value.get_active_theme.return_value = MagicMock(name="test-theme")
        with patch("core.config.core_paths.get_grub_themes_dir", return_value=os.path.abspath("/boot/grub/themes")):
            model = manager._read_model_from_ui()

    assert model.timeout == 5
    assert model.hidden_timeout is True
    assert model.quiet is True
    assert model.splash is True
    assert model.disable_submenu is True
    assert model.gfxmode == "1024x768"
    assert model.gfxpayload_linux == "text"

def test_load_config_warnings_full(manager):
    # Sync warning
    with patch("ui.ui_manager.check_grub_sync") as mock_sync:
        mock_sync.return_value = SyncStatus(
            in_sync=False,
            message="Out of sync",
            grub_default_exists=True,
            grub_cfg_exists=True,
            grub_default_mtime=0.0,
            grub_cfg_mtime=0.0
        )
        with patch.object(manager, "show_info") as mock_show:
            manager.load_config()
            assert any("Out of sync" in call[0][0] for call in mock_show.call_args_list)

    # Hidden timeout warning
    with patch("ui.ui_manager.load_grub_ui_state") as mock_load:
        mock_load.return_value = GrubUiState(
            model=GrubUiModel(timeout=5, default="0", hidden_timeout=True),
            entries=[],
            raw_config={}
        )
        with patch.object(manager, "show_info") as mock_show:
            manager.load_config()
            assert any("mode caché" in call[0][0] for call in mock_show.call_args_list)

    # Hidden entries warning
    manager.state_manager.hidden_entry_ids = ["id1"]
    with patch.object(manager, "show_info") as mock_show:
        manager.load_config()
        assert any("entrée(s) GRUB sont masquées" in call[0][0] for call in mock_show.call_args_list)

    # No entries root warning
    with patch("ui.ui_manager.os.geteuid", return_value=0):
        with patch("ui.ui_manager.load_grub_ui_state") as mock_load:
            mock_load.return_value = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})
            with patch.object(manager, "show_info") as mock_show:
                manager.load_config()
                assert any("Aucune entrée GRUB détectée" in call[0][0] for call in mock_show.call_args_list)

def test_load_config_errors_full(manager):
    # FileNotFoundError
    with patch("ui.ui_manager.load_grub_ui_state", side_effect=FileNotFoundError):
        with patch.object(manager, "show_info") as mock_show:
            manager.load_config()
            mock_show.assert_called_with("Fichier /etc/default/grub introuvable", ERROR)

    # Generic Exception
    with patch("ui.ui_manager.load_grub_ui_state", side_effect=RuntimeError("Boom")):
        with patch.object(manager, "show_info") as mock_show:
            manager.load_config()
            assert "Erreur lors du chargement: Boom" in mock_show.call_args[0][0]

def test_on_hidden_timeout_toggled_full(manager):
    manager.state_manager.set_loading(False)
    switch = Gtk.Switch()
    switch.set_active(True)
    manager.on_hidden_timeout_toggled(switch)
    assert manager.timeout_dropdown.get_selected() == 0 # "0"

    switch.set_active(False)
    manager.on_hidden_timeout_toggled(switch)
    # Should just mark dirty
    assert manager.state_manager.modified is True

def test_on_menu_options_toggled_full(manager):
    manager.state_manager.set_loading(False)
    with patch("ui.ui_manager.render_entries_view") as mock_render:
        manager.on_menu_options_toggled(Gtk.Switch())
        assert manager.state_manager.modified is True
        mock_render.assert_called_once()

def test_on_reload_confirm_full(manager):
    manager.state_manager.modified = True
    with patch("gi.repository.Gtk.AlertDialog") as mock_dialog:
        mock_dlg_inst = mock_dialog.return_value
        def fake_choose(parent, cancellable, callback):
            mock_result = MagicMock()
            mock_dlg_inst.choose_finish.return_value = 1 # Recharger
            callback(mock_dlg_inst, mock_result)
        mock_dlg_inst.choose.side_effect = fake_choose

        with patch.object(manager, "load_config") as mock_load:
            manager.on_reload(None)
            mock_load.assert_called_once()

def test_on_save_confirm_full(manager):
    with patch("ui.ui_manager.os.geteuid", return_value=0):
        with patch("gi.repository.Gtk.AlertDialog") as mock_dialog:
            mock_dlg_inst = mock_dialog.return_value
            def fake_choose(parent, cancellable, callback):
                mock_result = MagicMock()
                mock_dlg_inst.choose_finish.return_value = 1 # Appliquer
                callback(mock_dlg_inst, mock_result)
            mock_dlg_inst.choose.side_effect = fake_choose

            with patch.object(manager, "_perform_save") as mock_save:
                manager.on_save(None)
                mock_save.assert_called_with(apply_now=True)

def test_perform_save_full_flow(manager):
    with patch.object(manager, "_read_model_from_ui") as mock_read:
        mock_read.return_value = GrubUiModel(timeout=10, default="id1")
        with patch("ui.ui_manager.merged_config_from_model") as mock_merge:
            mock_merge.return_value = {"GRUB_TIMEOUT": "10"}
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=True, message="Saved", details="Details")

                with patch("ui.ui_manager.read_grub_default") as mock_verify:
                    mock_verify.return_value = {"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "id1"}

                    manager.state_manager.hidden_entry_ids = ["hid1"]
                    manager.state_manager.entries_visibility_dirty = True

                    with patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg") as mock_hide:
                        mock_hide.return_value = ("/boot/grub/grub.cfg", 1)

                        manager._perform_save(apply_now=True)

                        assert manager.state_manager.state == AppState.CLEAN
                        assert manager.state_manager.entries_visibility_dirty is False

def test_perform_save_exception_full(manager):
    with patch.object(manager, "_read_model_from_ui", side_effect=RuntimeError("Save failed")):
        with patch.object(manager, "show_info") as mock_show:
            manager._perform_save(apply_now=True)
            assert manager.state_manager.state == AppState.DIRTY
            assert "Erreur inattendue: Save failed" in mock_show.call_args[0][0]

def test_show_info_full(manager):
    with patch("gi.repository.GLib.timeout_add_seconds") as mock_timeout:
        manager.show_info("Test message", INFO)
        assert manager.info_label.get_text() == "Test message"
        assert manager.info_revealer.get_reveal_child() is True
        mock_timeout.assert_called_once()

        # Test callback
        callback = mock_timeout.call_args[0][1]
        assert callback() is False
        assert manager.info_revealer.get_reveal_child() is False

def test_sync_timeout_choices_not_found(manager):
    # Line 145
    # To hit line 145, we need GtkHelper.stringlist_find to return None.
    with patch("ui.ui_manager.GtkHelper.stringlist_find", return_value=None):
        with patch.object(manager.timeout_dropdown, "set_selected") as mock_set:
            manager._sync_timeout_choices(99)
            mock_set.assert_not_called()

def test_set_default_choice_not_in_ids(manager):
    # Lines 226-236
    manager.state_manager.update_default_choice_ids(["saved", "id1"])
    manager._set_default_choice("new_id")
    assert manager.default_dropdown.get_selected() == 2 # Appended at the end
    assert "new_id" in manager.state_manager.get_default_choice_ids()

def test_read_model_from_ui_theme_success(manager):
    # Lines 367-375
    with patch("ui.ui_manager.ActiveThemeManager") as mock_theme_mgr:
        mock_active = MagicMock()
        mock_active.name = "my-theme"
        mock_theme_mgr.return_value.get_active_theme.return_value = mock_active
        with patch("ui.ui_manager.get_grub_themes_dir", return_value=Path("/boot/grub/themes")):
            model = manager._read_model_from_ui()
            assert "my-theme/theme.txt" in model.grub_theme

def test_read_model_from_ui_theme_exception(manager):
    # Test theme exception in _read_model_from_ui
    with patch("ui.ui_manager.ActiveThemeManager", side_effect=RuntimeError("Theme error")):
        model = manager._read_model_from_ui()
        assert model.grub_theme == ""

def test_show_info_invalid_type_full(manager):
    # Lines 664-667
    manager.show_info("Test", "unknown")
    # Should not crash and should not add class
    assert not manager.info_box.has_css_class("unknown")

def test_check_permissions_not_root(manager):
    # Lines 405-406
    with patch("ui.ui_manager.os.geteuid", return_value=1000):
        with patch.object(manager, "show_info") as mock_show:
            manager.check_permissions()
            mock_show.assert_called_with(ANY, WARNING)

def test_load_config_no_entries_root(manager):
    # Lines 460-466
    with patch("ui.ui_manager.os.geteuid", return_value=0):
        with patch("ui.ui_manager.load_grub_ui_state") as mock_load:
            mock_load.return_value = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})
            with patch.object(manager, "show_info") as mock_show:
                manager.load_config()
                assert any("Aucune entrée GRUB détectée" in call[0][0] for call in mock_show.call_args_list)

def test_on_reload_no_modifications(manager):
    # Lines 538-540
    manager.state_manager.modified = False
    with patch.object(manager, "load_config") as mock_load:
        manager.on_reload(None)
        mock_load.assert_called_once()

def test_perform_save_verification_exception(manager):
    # Lines 637-638
    with patch.object(manager, "_read_model_from_ui") as mock_read:
        mock_read.return_value = GrubUiModel(timeout=10, default="id1")
        with patch("ui.ui_manager.merged_config_from_model"):
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=True, message="Saved", details="")
                with patch("ui.ui_manager.read_grub_default", side_effect=RuntimeError("Verify failed")):
                    manager._perform_save(apply_now=True)
                    # Should log warning and continue
                    assert manager.state_manager.state == AppState.CLEAN

def test_perform_save_visibility_dirty_no_apply(manager):
    # Line 647
    with patch.object(manager, "_read_model_from_ui") as mock_read:
        mock_read.return_value = GrubUiModel(timeout=10, default="id1")
        with patch("ui.ui_manager.merged_config_from_model"):
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=True, message="Saved", details="")
                with patch("ui.ui_manager.read_grub_default"):
                    manager.state_manager.entries_visibility_dirty = True
                    with patch.object(manager, "show_info") as mock_show:
                        manager._perform_save(apply_now=False)
                        assert any("Masquage non appliqué" in call[0][0] for call in mock_show.call_args_list)

def test_set_default_choice_found_in_loop(manager):
    # Line 226-229
    manager.state_manager.update_default_choice_ids(["saved", "id1", "id2"])
    with patch.object(manager.default_dropdown, "set_selected") as mock_set:
        manager._set_default_choice("id1")
        mock_set.assert_called_with(1)

def test_set_default_choice_exception(manager):
    # Line 240 (except Exception)
    manager.state_manager.update_default_choice_ids(["saved"])
    with patch.object(manager.default_dropdown, "get_model") as mock_get_model:
        mock_model = MagicMock()
        mock_model.append.side_effect = RuntimeError("Append failed")
        mock_get_model.return_value = mock_model
        with patch.object(manager.default_dropdown, "set_selected") as mock_set:
            manager._set_default_choice("new_id")
            mock_set.assert_called_with(0) # Fallback to 0

def test_read_model_from_ui_theme_no_name(manager):
    # Line 369 (if active_theme and active_theme.name) - False case
    with patch("ui.ui_manager.ActiveThemeManager") as mock_theme_mgr:
        mock_active = MagicMock()
        mock_active.name = ""
        mock_theme_mgr.return_value.get_active_theme.return_value = mock_active
        model = manager._read_model_from_ui()
        assert model.grub_theme == ""

def test_load_config_no_entries_non_root_full(manager):
    # Lines 460-465
    with patch("ui.ui_manager.os.geteuid", return_value=1000):
        with patch("ui.ui_manager.load_grub_ui_state") as mock_load:
            mock_load.return_value = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})
            with patch.object(manager, "show_info") as mock_show:
                manager.load_config()
                assert any("lecture de /boot/grub/grub.cfg refusée" in call[0][0] for call in mock_show.call_args_list)

def test_perform_save_verification_no_match(manager):
    # Line 635 (if not matches)
    with patch.object(manager, "_read_model_from_ui") as mock_read:
        mock_read.return_value = GrubUiModel(timeout=10, default="id1")
        with patch("ui.ui_manager.merged_config_from_model"):
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=True, message="Saved", details="")
                with patch("ui.ui_manager.read_grub_default") as mock_verify:
                    mock_verify.return_value = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "id2"} # No match
                    manager._perform_save(apply_now=True)
                    assert manager.state_manager.state == AppState.CLEAN

def test_perform_save_hidden_entries_exception_full(manager):
    # Line 658 (except Exception as e in hidden entries)
    with patch.object(manager, "_read_model_from_ui") as mock_read:
        mock_read.return_value = GrubUiModel(timeout=10, default="id1")
        with patch("ui.ui_manager.merged_config_from_model"):
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=True, message="Saved", details="")
                with patch("ui.ui_manager.read_grub_default"):
                    manager.state_manager.hidden_entry_ids = ["hid1"]
                    with patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg", side_effect=RuntimeError("Hide failed")):
                        with patch.object(manager, "show_info") as mock_show:
                            manager._perform_save(apply_now=True)
                            assert any("Masquage échoué" in call[0][0] for call in mock_show.call_args_list)


def test_read_model_from_ui_theme_none(manager):
    # Line 369 (if active_theme) - False case
    with patch("ui.ui_manager.ActiveThemeManager") as mock_theme_mgr:
        mock_theme_mgr.return_value.get_active_theme.return_value = None
        model = manager._read_model_from_ui()
        assert model.grub_theme == ""

def test_set_default_choice_no_model(manager):
    # Line 227 (if model is not None) - False case
    with patch.object(manager.default_dropdown, "get_model", return_value=None):
        with patch.object(manager.default_dropdown, "set_selected") as mock_set:
            manager._set_default_choice("unknown")
            mock_set.assert_called_with(0)

def test_load_config_with_entries(manager):
    # Line 456 (elif not state.entries) - False case
    with patch("ui.ui_manager.load_grub_ui_state") as mock_load:
        mock_load.return_value = GrubUiState(
            model=GrubUiModel(),
            entries=[GrubDefaultChoice(id="1", title="T1")],
            raw_config={}
        )
        manager.load_config()
        assert manager.state_manager.state == AppState.CLEAN

def test_perform_save_failed_result(manager):
    # Lines 633-634 (else block for result.success)
    with patch.object(manager, "_read_model_from_ui"):
        with patch("ui.ui_manager.merged_config_from_model"):
            with patch("ui.ui_manager.GrubApplyManager") as mock_apply_mgr:
                mock_inst = mock_apply_mgr.return_value
                mock_inst.apply_configuration.return_value = MagicMock(success=False, message="Failed")
                manager._perform_save(apply_now=True)
                assert manager.state_manager.state == AppState.DIRTY

def test_hide_info_callback_full(manager):
    # Line 643
    manager.info_revealer = MagicMock()
    assert manager._hide_info_callback() is False
    manager.info_revealer.set_reveal_child.assert_called_with(False)

def test_hide_info_callback_none(manager):
    # Line 642 (if self.info_revealer is None)
    manager.info_revealer = None
    assert manager._hide_info_callback() is False
