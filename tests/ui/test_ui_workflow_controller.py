"""Tests unitaires pour WorkflowController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.ui_infobar_controller import ERROR, INFO, WARNING
from ui.ui_state import AppState
from ui.ui_workflow_controller import WorkflowController, WorkflowDeps


def _make_state_manager() -> MagicMock:
    state_manager = MagicMock()
    state_manager.modified = False
    state_manager.hidden_entry_ids = set()
    state_manager.entries_visibility_dirty = False
    state_manager.state_data = SimpleNamespace(raw_config={"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}, entries=["e"])
    state_manager.apply_state = MagicMock()
    state_manager.update_state_data = MagicMock()
    return state_manager


def _make_controller(
    state_manager: MagicMock | None = None,
) -> tuple[WorkflowController, MagicMock, MagicMock, MagicMock, MagicMock]:
    sm = state_manager or _make_state_manager()
    save_btn = MagicMock()
    reload_btn = MagicMock()
    load_config_cb = MagicMock()
    read_model_cb = MagicMock(return_value=SimpleNamespace(timeout=10, default="0", theme_management_enabled=True))
    show_info_cb = MagicMock()

    controller = WorkflowController(
        window=MagicMock(),
        state_manager=sm,
        deps=WorkflowDeps(
            save_btn=save_btn,
            reload_btn=reload_btn,
            load_config_cb=load_config_cb,
            read_model_cb=read_model_cb,
            show_info_cb=show_info_cb,
        ),
    )
    return controller, load_config_cb, read_model_cb, show_info_cb, sm


def test_on_reload_when_not_modified_calls_load_directly():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = False

    with patch("ui.ui_workflow_controller.os.path.exists", return_value=False):
        controller.on_reload()

    load_config_cb.assert_called_once_with()
    show_info_cb.assert_called_once_with("Configuration rechargée", INFO)


def test_on_reload_when_modified_confirm_triggers_load():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = True

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 1

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.os.path.exists", return_value=False),
    ):
        controller.on_reload()

    assert "callback" in captured
    callback = captured["callback"]
    callback(dialog, MagicMock())

    load_config_cb.assert_called_once_with()
    show_info_cb.assert_called_once_with("Configuration rechargée", INFO)


def test_on_reload_when_modified_cancel_does_nothing():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = True

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 0

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.os.path.exists", return_value=False),
    ):
        controller.on_reload()

    callback = captured["callback"]
    callback(dialog, MagicMock())

    load_config_cb.assert_not_called()
    show_info_cb.assert_not_called()


def test_on_reload_dialog_exception_is_swallowed():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = True

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.GLib.Error", new=Exception),
        patch("ui.ui_workflow_controller.os.path.exists", return_value=False),
    ):
        controller.on_reload()
        dialog.choose_finish.side_effect = Exception("cancel")
        callback = captured["callback"]
        callback(dialog, MagicMock())

    load_config_cb.assert_not_called()
    show_info_cb.assert_not_called()


def test_on_save_non_root_shows_error():
    controller, _load_config_cb, _read_model_cb, show_info_cb, _sm = _make_controller()

    with patch("ui.ui_workflow_controller.os.geteuid", return_value=1000):
        controller.on_save()

    show_info_cb.assert_called_once_with("Droits administrateur requis pour enregistrer", ERROR)


def test_on_save_root_confirm_triggers_perform_save():
    controller, _load_config_cb, _read_model_cb, _show_info_cb, _sm = _make_controller()

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 1

    with (
        patch("ui.ui_workflow_controller.os.geteuid", return_value=0),
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch.object(controller, "perform_save") as mock_perform,
    ):
        controller.on_save()
        callback = captured["callback"]
        callback(dialog, MagicMock())

    mock_perform.assert_called_once_with(apply_now=True)


def test_on_save_root_dialog_exception_is_swallowed():
    controller, _load_config_cb, _read_model_cb, _show_info_cb, _sm = _make_controller()

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose

    with (
        patch("ui.ui_workflow_controller.os.geteuid", return_value=0),
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.GLib.Error", new=Exception),
        patch.object(controller, "perform_save") as mock_perform,
    ):
        controller.on_save()
        dialog.choose_finish.side_effect = Exception("cancel")
        callback = captured["callback"]
        callback(dialog, MagicMock())

    mock_perform.assert_not_called()


def test_perform_save_success_apply_now_with_hidden_entries_adds_mask_info():
    controller, _load_config_cb, read_model_cb, show_info_cb, sm = _make_controller()
    sm.hidden_entry_ids = {"id-1"}

    result = SimpleNamespace(success=True, message="OK", details="Details")

    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.apply_hidden_entries_to_grub_cfg", return_value=("/boot/grub/grub.cfg", 2)),
        patch("ui.ui_workflow_controller.read_grub_default", return_value={"GRUB_TIMEOUT": "999", "GRUB_DEFAULT": "x"}),
        patch("ui.ui_workflow_controller.create_last_modif_backup"),
    ):
        controller.perform_save(apply_now=True)

    read_model_cb.assert_called_once()
    sm.apply_state.assert_any_call(AppState.APPLYING, controller.save_btn, controller.reload_btn)
    sm.apply_state.assert_any_call(AppState.CLEAN, controller.save_btn, controller.reload_btn)
    assert sm.entries_visibility_dirty is False

    # Message final
    args = show_info_cb.call_args[0]
    assert "OK" in args[0]
    assert "Details" in args[0]
    assert "Entrées masquées" in args[0]
    assert args[1] == INFO


def test_perform_save_success_apply_now_without_hidden_entries_stays_info():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.hidden_entry_ids = set()

    result = SimpleNamespace(success=True, message="OK", details="")
    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.read_grub_default", return_value={"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}),
        patch("ui.ui_workflow_controller.create_last_modif_backup"),
    ):
        controller.perform_save(apply_now=True)

    msg, msg_type = show_info_cb.call_args[0]
    assert msg.startswith("OK")
    assert "Entrées masquées" not in msg
    assert msg_type == INFO


def test_perform_save_apply_now_true_entries_visibility_dirty_does_not_add_skip_note():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.hidden_entry_ids = set()
    sm.entries_visibility_dirty = True

    result = SimpleNamespace(success=True, message="OK", details="")
    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.read_grub_default", return_value={"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}),
        patch("ui.ui_workflow_controller.create_last_modif_backup"),
    ):
        controller.perform_save(apply_now=True)

    msg, msg_type = show_info_cb.call_args[0]
    assert msg.startswith("OK")
    assert "Masquage non appliqué" not in msg
    assert msg_type == INFO


def test_perform_save_success_apply_now_masking_failure_becomes_warning():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.hidden_entry_ids = {"id-1"}

    result = SimpleNamespace(success=True, message="OK", details="")

    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.apply_hidden_entries_to_grub_cfg", side_effect=RuntimeError("boom")),
        patch("ui.ui_workflow_controller.read_grub_default", side_effect=OSError("nope")),
        patch("ui.ui_workflow_controller.create_last_modif_backup"),
    ):
        controller.perform_save(apply_now=True)

    msg, msg_type = show_info_cb.call_args[0]
    assert "Masquage échoué" in msg
    assert msg_type == WARNING


def test_perform_save_success_no_apply_adds_visibility_note():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.entries_visibility_dirty = True

    result = SimpleNamespace(success=True, message="OK", details="")

    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.read_grub_default", return_value={"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}),
    ):
        controller.perform_save(apply_now=False)

    msg, msg_type = show_info_cb.call_args[0]
    assert "Masquage non appliqué" in msg
    assert msg_type == INFO


def test_perform_save_success_no_apply_and_not_dirty_does_not_add_visibility_note():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.entries_visibility_dirty = False

    result = SimpleNamespace(success=True, message="OK", details="")

    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.read_grub_default", return_value={"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}),
    ):
        controller.perform_save(apply_now=False)

    msg, msg_type = show_info_cb.call_args[0]
    assert msg.startswith("OK")
    assert "Masquage non appliqué" not in msg
    assert msg_type == INFO


def test_perform_save_failure_sets_dirty_and_shows_error():
    controller, _load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()

    result = SimpleNamespace(success=False, message="Nope", details="")

    apply_manager = MagicMock()
    apply_manager.apply_configuration.return_value = result

    with (
        patch("ui.ui_workflow_controller.merged_config_from_model", return_value={"A": "B"}),
        patch("ui.ui_workflow_controller.GrubApplyManager", return_value=apply_manager),
        patch("ui.ui_workflow_controller.create_last_modif_backup"),
    ):
        controller.perform_save(apply_now=True)

    sm.apply_state.assert_any_call(AppState.DIRTY, controller.save_btn, controller.reload_btn)
    msg, msg_type = show_info_cb.call_args[0]
    assert msg.startswith("Erreur: ")
    assert msg_type == ERROR


def test_on_reload_with_backup_restore_success():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = False  # Not modified, but backup exists

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 2  # Restore previous

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.os.path.exists", return_value=True),
        patch("ui.ui_workflow_controller.os.geteuid", return_value=0),
        patch("ui.ui_workflow_controller.restore_grub_default_backup") as mock_restore,
    ):
        controller.on_reload()
        callback = captured["callback"]
        callback(dialog, MagicMock())

    mock_restore.assert_called_once()
    load_config_cb.assert_called_once()
    show_info_cb.assert_called_with("Version précédente restaurée avec succès", INFO)


def test_on_reload_with_backup_reload_current():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = False

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 1  # Reload current

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.os.path.exists", return_value=True),
    ):
        controller.on_reload()
        callback = captured["callback"]
        callback(dialog, MagicMock())

    load_config_cb.assert_called_once()
    show_info_cb.assert_called_with("Configuration rechargée", INFO)


def test_perform_save_exception_sets_dirty_and_shows_unexpected_error():
    controller, _load_config_cb, read_model_cb, show_info_cb, sm = _make_controller()

    read_model_cb.side_effect = RuntimeError("boom")

    with patch("ui.ui_workflow_controller.create_last_modif_backup"):
        controller.perform_save(apply_now=True)

    sm.apply_state.assert_any_call(AppState.DIRTY, controller.save_btn, controller.reload_btn)
    msg, msg_type = show_info_cb.call_args[0]
    assert "Erreur inattendue" in msg
    assert msg_type == ERROR

def test_check_restore_last_modif_non_root_blocks_restore():
    """Test que la restauration est bloquée si l'utilisateur n'est pas root."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    backup_path = "/tmp/fake_backup"

    dialog = MagicMock()
    captured: dict[str, object] = {}

    def _choose(_parent, _cancellable, callback):
        captured["callback"] = callback

    dialog.choose.side_effect = _choose
    dialog.choose_finish.return_value = 2  # Restaurer

    with (
        patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog),
        patch("ui.ui_workflow_controller.os.geteuid", return_value=1000),  # Non-root
        patch("ui.ui_workflow_controller.restore_grub_default_backup") as mock_restore,
    ):
        controller._check_restore_last_modif(has_last_modif=True, backup_path=backup_path)
        callback = captured["callback"]
        callback(dialog, MagicMock())

    mock_restore.assert_not_called()
    load_config_cb.assert_not_called()
    show_info_cb.assert_called()
    calls = show_info_cb.call_args_list
    assert any("Droits root" in str(call) for call in calls)


def test_check_restore_last_modif_restore_failure():
    """Test la gestion d'erreur lors de la restauration."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    backup_path = "/tmp/fake_backup"
    
    with patch("ui.ui_workflow_controller.os.geteuid", return_value=0), \
         patch("ui.ui_workflow_controller.restore_grub_default_backup", side_effect=OSError("Backup not found")):
        
        def fake_choose(window, parent, callback):
            dlg = MagicMock()
            dlg.choose_finish.return_value = 2  # Restaurer
            callback(dlg, None)
        
        with patch("ui.ui_workflow_controller.Gtk.AlertDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.choose = fake_choose
            MockDialog.return_value = mock_dialog
            
            controller._check_restore_last_modif(has_last_modif=True, backup_path=backup_path)
            
            # Doit avoir montré le message d'erreur
            show_info_cb.assert_called()
            calls = show_info_cb.call_args_list
            assert any("Erreur" in str(call) for call in calls)


def test_check_restore_success_restore_path():
    """Test successful restoration of last_modif backup (idx==2)."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    backup_path = "/tmp/fake_backup"
    
    with patch("ui.ui_workflow_controller.os.geteuid", return_value=0), \
         patch("ui.ui_workflow_controller.restore_grub_default_backup") as mock_restore:
        
        def fake_choose(window, parent, callback):
            dlg = MagicMock()
            dlg.choose_finish.return_value = 2  # Restaurer
            callback(dlg, None)
        
        with patch("ui.ui_workflow_controller.Gtk.AlertDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.choose = fake_choose
            MockDialog.return_value = mock_dialog
            
            controller._check_restore_last_modif(has_last_modif=True, backup_path=backup_path)
            
            # Verify restore was called
            mock_restore.assert_called_once_with(backup_path)
            # Verify load_config was called
            load_config_cb.assert_called()
            # Verify success message was shown
            show_info_cb.assert_called()
            calls = show_info_cb.call_args_list
            assert any("restaurée" in str(call) for call in calls)


def test_check_restore_reload_current():
    """Test restoration reload current option (idx==1)."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    backup_path = "/tmp/fake_backup"
    
    def fake_choose(window, parent, callback):
        dlg = MagicMock()
        dlg.choose_finish.return_value = 1  # Recharger actuel
        callback(dlg, None)
    
    with patch("ui.ui_workflow_controller.Gtk.AlertDialog") as MockDialog:
        mock_dialog = MagicMock()
        mock_dialog.choose = fake_choose
        MockDialog.return_value = mock_dialog
        
        controller._check_restore_last_modif(has_last_modif=True, backup_path=backup_path)
        
        # Verify load_config was called
        load_config_cb.assert_called()
        # Verify reload message was shown
        show_info_cb.assert_called()
        calls = show_info_cb.call_args_list
        assert any("rechargée" in str(call) for call in calls)


def test_check_restore_restore_requires_root():
    """Test restore previous option (idx==2) without root rights."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    backup_path = "/tmp/fake_backup"

    def fake_choose(window, parent, callback):
        dlg = MagicMock()
        dlg.choose_finish.return_value = 2  # Restaurer précédent
        callback(dlg, None)

    with patch("ui.ui_workflow_controller.os.geteuid", return_value=1000), \
         patch("ui.ui_workflow_controller.restore_grub_default_backup") as mock_restore, \
         patch("ui.ui_workflow_controller.Gtk.AlertDialog") as MockDialog:
        mock_dialog = MagicMock()
        mock_dialog.choose = fake_choose
        MockDialog.return_value = mock_dialog

        controller._check_restore_last_modif(has_last_modif=True, backup_path=backup_path)

        mock_restore.assert_not_called()
        load_config_cb.assert_not_called()
        show_info_cb.assert_called()
        calls = show_info_cb.call_args_list
        assert any("Droits root" in str(call) for call in calls)


def test_perform_save_create_last_modif_backup_fails():
    """Test that perform_save continues even if create_last_modif_backup fails."""
    controller, _, _, _, _ = _make_controller()
    
    with patch("ui.ui_workflow_controller.create_last_modif_backup", side_effect=OSError("Backup failed")), \
         patch.object(controller, "read_model_cb", return_value=MagicMock()), \
         patch("ui.ui_workflow_controller.GrubApplyManager") as mock_apply:
        
        # Should not raise, just continue
        controller.perform_save(apply_now=True)
        
        # GrubApplyManager should still be called
        assert mock_apply.called


def test_handle_restore_choice_reload_current():
    """Test _handle_restore_choice with idx=1 (reload current) - lines 127-128."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    
    mock_dlg = MagicMock()
    mock_dlg.choose_finish.return_value = 1  # Recharger actuel
    
    controller._handle_restore_choice(mock_dlg, MagicMock(), "/backup/path")
    
    load_config_cb.assert_called_once()
    show_info_cb.assert_called()
    # Verify the message contains "rechargée"
    call_args = show_info_cb.call_args_list
    assert any("rechargée" in str(call) for call in call_args)


def test_handle_restore_choice_glib_error():
    """Test _handle_restore_choice when GLib.Error is raised (line 133->exit)."""
    controller, load_config_cb, _, show_info_cb, _ = _make_controller()
    
    with patch("ui.ui_workflow_controller.GLib.Error", new=Exception):
        mock_dlg = MagicMock()
        mock_dlg.choose_finish.side_effect = Exception("Cancelled")
        
        controller._handle_restore_choice(mock_dlg, MagicMock(), "/backup/path")
    
    # Neither should be called since idx remains None
    load_config_cb.assert_not_called()
    show_info_cb.assert_not_called()