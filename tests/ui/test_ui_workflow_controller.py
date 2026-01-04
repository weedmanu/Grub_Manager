"""Tests unitaires pour WorkflowController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ui.ui_infobar_controller import ERROR, INFO, WARNING
from ui.ui_state import AppState
from ui.ui_workflow_controller import WorkflowController


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
    read_model_cb = MagicMock(return_value=SimpleNamespace(timeout=10, default="0"))
    show_info_cb = MagicMock()

    controller = WorkflowController(
        window=MagicMock(),
        state_manager=sm,
        save_btn=save_btn,
        reload_btn=reload_btn,
        load_config_cb=load_config_cb,
        read_model_cb=read_model_cb,
        show_info_cb=show_info_cb,
    )
    return controller, load_config_cb, read_model_cb, show_info_cb, sm


def test_on_reload_when_not_modified_calls_load_directly():
    controller, load_config_cb, _read_model_cb, show_info_cb, sm = _make_controller()
    sm.modified = False

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

    with patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog):
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

    with patch("ui.ui_workflow_controller.Gtk.AlertDialog", return_value=dialog):
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
    ):
        controller.perform_save(apply_now=True)

    sm.apply_state.assert_any_call(AppState.DIRTY, controller.save_btn, controller.reload_btn)
    msg, msg_type = show_info_cb.call_args[0]
    assert msg.startswith("Erreur: ")
    assert msg_type == ERROR


def test_perform_save_exception_sets_dirty_and_shows_unexpected_error():
    controller, _load_config_cb, read_model_cb, show_info_cb, sm = _make_controller()

    read_model_cb.side_effect = RuntimeError("boom")

    controller.perform_save(apply_now=True)

    sm.apply_state.assert_any_call(AppState.DIRTY, controller.save_btn, controller.reload_btn)
    msg, msg_type = show_info_cb.call_args[0]
    assert "Erreur inattendue" in msg
    assert msg_type == ERROR
