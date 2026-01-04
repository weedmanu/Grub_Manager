"""Tests pour le gestionnaire d'interface utilisateur GrubConfigManager."""

import dataclasses
from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")

from core.system.core_grub_system_commands import GrubDefaultChoice, GrubUiModel, GrubUiState
from core.system.core_sync_checker import SyncStatus
from ui.ui_manager import GrubConfigManager
from ui.ui_state import AppState

INFO = "info"
WARNING = "warning"
ERROR = "error"


class MockStringList:
    """Mock pour Gtk.StringList."""

    def __init__(self, items=None):
        """Initialise le mock avec une liste d'éléments."""
        self.items = list(items or [])

    def get_n_items(self):
        """Retourne le nombre d'éléments."""
        return len(self.items)

    def get_string(self, index):
        """Retourne la chaîne à l'index donné."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def splice(self, position, n_removals, additions):
        """Simule l'opération splice."""
        self.items[position : position + n_removals] = list(additions)

    def append(self, item):
        """Ajoute un élément à la fin."""
        self.items.append(item)

    def remove(self, index):
        """Supprime l'élément à l'index donné."""
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def __iter__(self):
        """Retourne un itérateur sur les éléments."""
        return iter(self.items)


class GrubConfigManagerFull(GrubConfigManager):
    """Version étendue de GrubConfigManager pour les tests avec mocks injectés."""

    def __init__(self, application):
        """Initialise le manager avec des mocks pour l'état et l'UI."""
        self.application = application
        self.set_default_size = MagicMock()

        # State manager mock (compatible avec les tests qui utilisent .return_value et .assert_called_with)
        self.state_manager = MagicMock()
        self.state_manager.state = AppState.CLEAN
        self.state_manager.modified = False
        self.state_manager.entries_visibility_dirty = False
        self.state_manager.hidden_entry_ids = set()
        self.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

        # IMPORTANT: les tests modifient souvent `.is_loading.return_value`.
        # On évite un side_effect ici sinon ces overrides ne servent à rien.
        self.state_manager.is_loading = MagicMock(return_value=False)

        def _set_loading(value: bool):
            # pylint: disable=no-member
            self.state_manager.is_loading.return_value = bool(value)  # type: ignore[attr-defined]

        def _mark_dirty(*_args, **_kwargs):
            self.state_manager.modified = True
            self.state_manager.state = AppState.DIRTY

        def _apply_state(state, *_args):
            self.state_manager.state = state
            self.state_manager.modified = state != AppState.CLEAN

        def _update_state_data(state_data):
            self.state_manager.state_data = state_data

        self.state_manager.set_loading.side_effect = _set_loading
        self.state_manager.mark_dirty.side_effect = _mark_dirty
        self.state_manager.apply_state.side_effect = _apply_state
        self.state_manager.update_state_data.side_effect = _update_state_data

        self.state_manager._default_choice_ids = ["saved"]
        self.state_manager.get_default_choice_ids.side_effect = lambda: list(self.state_manager._default_choice_ids)
        self.state_manager.update_default_choice_ids.side_effect = lambda ids: setattr(
            self.state_manager, "_default_choice_ids", list(ids)
        )

        self.state_manager.get_state.side_effect = lambda: AppState(grub_state=self.state_manager.state_data)
        self.state_manager.update_state.side_effect = lambda app_state: setattr(
            self.state_manager, "state_data", app_state.grub_state
        )

        # IMPORTANT: éviter spec=Gtk.* (GI) -> inspect.signature peut provoquer MemoryError/SystemError
        self.timeout_dropdown = MagicMock()
        self.default_dropdown = MagicMock()
        self.hidden_timeout_check = MagicMock()
        self.gfxmode_dropdown = MagicMock()
        self.gfxpayload_dropdown = MagicMock()
        self.cmdline_dropdown = MagicMock()
        self.terminal_color_check = MagicMock()
        self.disable_os_prober_check = MagicMock()
        self.entries_listbox = MagicMock()
        self.maintenance_output = MagicMock()
        self.info_revealer = MagicMock()
        self.info_box = MagicMock()
        self.info_label = MagicMock()
        self.reload_btn = MagicMock()
        self.save_btn = MagicMock()

        self.hide_category_dropdown = MagicMock()
        self.hide_category_switch = MagicMock()
        self.show_advanced_switch = MagicMock()

        self.entries_renderer = MagicMock()
        self.entries_renderer.hide_advanced_mode = True

        self.workflow = MagicMock()
        self.infobar = None

        # Contrôleurs SRP (Single Responsibility)
        from ui.controllers import TimeoutController, DefaultChoiceController, PermissionController
        self.timeout_ctrl = TimeoutController(self)
        self.default_ctrl = DefaultChoiceController(self)
        self.perm_ctrl = PermissionController()

        # show_info est souvent asserté dans les tests, mais on veut aussi exécuter la logique
        # réelle (fallback info_label/info_revealer si infobar absent).
        real_show_info = GrubConfigManager.show_info.__get__(self, GrubConfigManagerFull)
        self.show_info = MagicMock(side_effect=real_show_info)

        # Valeurs par défaut pour éviter des branches involontaires
        self.cmdline_dropdown.get_selected.return_value = 0  # quiet splash
        self.default_dropdown.get_selected.return_value = 0


@pytest.fixture
def mock_app():
    return MagicMock()


@pytest.fixture
def manager(mock_app):
    mgr = GrubConfigManagerFull(mock_app)
    return mgr


def test_create_ui(mock_app):
    with patch("ui.ui_manager.UIBuilder") as mock_builder:
        manager = GrubConfigManagerFull(mock_app)
        manager.create_ui()

        mock_builder.create_main_ui.assert_called_once_with(manager)
        manager.state_manager.apply_state.assert_called_with(AppState.CLEAN, manager.save_btn, manager.reload_btn)


def test_apply_state_wrapper(manager):
    manager._apply_state(AppState.DIRTY)
    manager.state_manager.apply_state.assert_called_with(AppState.DIRTY, manager.save_btn, manager.reload_btn)


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (0, "quiet splash"),
        (1, "quiet"),
        (2, "splash"),
        (3, ""),
    ],
)
def test_get_cmdline_value_variants(manager, selected, expected):
    manager.cmdline_dropdown.get_selected.return_value = selected
    assert manager.get_cmdline_value() == expected


def test_get_cmdline_value_without_dropdown_returns_default(manager):
    manager.cmdline_dropdown = None
    assert manager.get_cmdline_value() == "quiet splash"


def test_check_permissions_root(manager):
    with patch("os.geteuid", return_value=0):
        manager.check_permissions()
        manager.show_info.assert_not_called()


def test_check_permissions_non_root(manager):
    with patch("os.geteuid", return_value=1000):
        manager.check_permissions()
        manager.show_info.assert_called_once()
        args = manager.show_info.call_args[0]
        # Vérifier que le message mentionne l'absence de droits root
        assert "droits root" in args[0] or "administrateur" in args[0]


def test_real_init_calls_create_ui_load_config_and_check_permissions():
    """Couvre le __init__ réel sans exécuter de logique I/O."""
    from gi.repository import Gtk

    app = Gtk.Application(application_id="com.example.grubmanager.tests")

    with (
        patch.object(GrubConfigManager, "create_ui", autospec=True) as mock_create_ui,
        patch.object(GrubConfigManager, "load_config", autospec=True) as mock_load_config,
        patch.object(GrubConfigManager, "check_permissions", autospec=True) as mock_check_permissions,
    ):
        win = GrubConfigManager(app)

    mock_create_ui.assert_called_once_with(win)
    mock_load_config.assert_called_once_with(win)
    mock_check_permissions.assert_called_once_with(win)


# --- Configuration Loading ---


def test_load_config_success(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )

    model = GrubUiModel(timeout=10, default="saved")
    entries = [GrubDefaultChoice(id="id1", title="Title 1")]
    state = GrubUiState(model=model, entries=entries, raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_set_value"),
    ):

        manager.load_config()

        manager.state_manager.update_state_data.assert_called_with(state)
        mock_render.assert_called_once_with(manager)
        manager.state_manager.apply_state.assert_called_with(AppState.CLEAN, manager.save_btn, manager.reload_btn)


def test_load_config_desync(manager):
    sync_status = SyncStatus(
        in_sync=False,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="Desync",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    state = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        manager.show_info.assert_any_call("⚠ Desync", "warning")


def test_load_config_hidden_timeout(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    model = GrubUiModel(hidden_timeout=True)
    state = GrubUiState(model=model, entries=[], raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        found = False
        target = "menu GRUB"
        for call in manager.show_info.call_args_list:
            args, _ = call
            if args and target in args[0]:
                found = True
                break
        assert found


def test_load_config_hidden_entries(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    model = GrubUiModel()
    state = GrubUiState(model=model, entries=[], raw_config={})

    manager.state_manager.hidden_entry_ids = {"entry1"}

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        args_list = manager.show_info.call_args_list
        found = any("entrée(s) GRUB sont masquées" in str(call) for call in args_list)
        assert found


def test_load_config_no_entries(manager):
    """Test load_config with root user and no entries."""
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    with (
        patch("ui.ui_manager.os.geteuid", return_value=0),
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state") as mock_load_state,
        patch("ui.ui_manager.render_entries_view"),
    ):

        # Mock state (utiliser de vrais objets pour éviter des comparaisons MagicMock/int)
        mock_load_state.return_value = GrubUiState(
            model=GrubUiModel(hidden_timeout=False),
            entries=[],
            raw_config={},
        )

        # Mock state manager to return empty entries
        manager.state_manager.state_data = dataclasses.replace(manager.state_manager.state_data, entries=[])

        manager.load_config()

        # Le message passe par show_info -> fallback info_label
        manager.info_label.set_text.assert_called()
        args, _ = manager.info_label.set_text.call_args
        assert "Aucune entrée GRUB détectée" in args[0]


def test_load_config_no_entries_non_root(manager):
    """Test load_config with no entries and non-root user."""
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.check_grub_sync") as mock_sync,
        patch("ui.ui_manager.load_grub_ui_state") as mock_load_state,
        patch("ui.ui_manager.render_entries_view"),
        patch("os.geteuid", return_value=1000),
    ):

        mock_sync.return_value.in_sync = True

        mock_load_state.return_value = GrubUiState(
            model=GrubUiModel(hidden_timeout=False),
            entries=[],
            raw_config={},
        )

        manager.load_config()

        manager.info_label.set_text.assert_any_call(
            "Entrées GRUB indisponibles: lecture de /boot/grub/grub.cfg refusée (droits). "
            "Relancez l'application avec pkexec/sudo."
        )


def test_load_config_file_not_found(manager):
    with patch("ui.ui_manager.check_grub_sync", side_effect=FileNotFoundError("Missing")):
        manager.load_config()


def test_load_config_exceptions(manager):
    """Test load_config exception handling for OSError."""
    manager.info_label = MagicMock()
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", side_effect=OSError("Permission denied")),
    ):
        manager.load_config()
        # Should show error info
        assert manager.show_info.called
        args = manager.show_info.call_args[0]
        assert "Impossible de lire la configuration" in args[0]


# --- Model UI Sync ---


def test_read_model_from_ui(manager):
    manager.timeout_dropdown.get_model.return_value = MagicMock()

    with (
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="10"),
        patch.object(manager, "get_timeout_value", return_value=10),
        patch.object(manager, "get_default_choice", return_value="saved"),
    ):

        manager.hidden_timeout_check.get_active.return_value = True
        manager.disable_os_prober_check.get_active.return_value = False
        manager.terminal_color_check.get_active.return_value = True

        model = manager.read_model_from_ui()

        assert model.timeout == 10
        assert model.default == "saved"
        assert model.save_default is True
        assert model.hidden_timeout is True
        assert model.quiet is True


def test_apply_model_to_ui(manager):
    model = GrubUiModel(
        timeout=5,
        default="id1",
        hidden_timeout=True,
        gfxmode="1024x768",
        gfxpayload_linux="keep",
        disable_os_prober=True,
        quiet=True,
    )
    entries = [GrubDefaultChoice(id="id1", title="Title 1")]

    with (
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_set_value") as mock_set_val,
        patch.object(manager, "sync_timeout_choices") as mock_sync_timeout,
        patch.object(manager, "refresh_default_choices") as mock_refresh_defaults,
        patch.object(manager, "set_default_choice") as mock_set_default,
    ):

        manager.apply_model_to_ui(model, entries)

        mock_sync_timeout.assert_called_with(5)
        manager.hidden_timeout_check.set_active.assert_called_with(True)

        mock_set_val.assert_any_call(manager.gfxmode_dropdown, "1024x768")
        mock_set_val.assert_any_call(manager.gfxpayload_dropdown, "keep")
        manager.disable_os_prober_check.set_active.assert_called_with(True)

        mock_refresh_defaults.assert_called_with(entries)
        mock_set_default.assert_called_with("id1")


def test_apply_model_to_ui_none_widgets(manager):
    """Test _apply_model_to_ui with None widgets."""
    # Set all widgets to None
    manager.hidden_timeout_check = None
    manager.gfxmode_dropdown = None
    manager.gfxpayload_dropdown = None
    manager.disable_os_prober_check = None
    manager.terminal_color_check = None

    model = MagicMock()
    model.timeout = 5

    # Should run without error
    manager.apply_model_to_ui(model, [])


def test_get_timeout_value(manager):
    with patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="5"):
        assert manager.get_timeout_value() == 5

    # Valeur invalide -> fallback 5
    with patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="Hidden"):
        assert manager.get_timeout_value() == 5


def test_get_timeout_value_none(manager):
    """Test _get_timeout_value when dropdown is None."""
    manager.timeout_dropdown = None
    assert manager.get_timeout_value() == 5


def test_get_timeout_value_exception(manager):
    """Test _get_timeout_value handles exceptions."""
    with patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="invalid"):
        assert manager.get_timeout_value() == 5


def test_sync_timeout_choices(manager):
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    manager.sync_timeout_choices(5)

    assert "5" in model.items
    assert "10" in model.items
    manager.timeout_dropdown.set_selected.assert_called()


def test_sync_timeout_choices_none_widgets(manager):
    """Test _sync_timeout_choices with None widgets."""
    manager.timeout_dropdown = None
    manager.sync_timeout_choices(5)  # Should not raise

    manager.timeout_dropdown = MagicMock()
    manager.timeout_dropdown.get_model.return_value = None
    manager.sync_timeout_choices(5)  # Should not raise


def test_ensure_timeout_choice(manager):
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    # Value exists
    manager._ensure_timeout_choice("5")
    assert model.items == ["5", "10"]

    # Value doesn't exist -> should be added
    manager._ensure_timeout_choice("15")
    assert "15" in model.items


def test_ensure_timeout_choice_non_int_hits_except_path(manager):
    model = MockStringList(["0", "5"])
    manager.timeout_dropdown.get_model.return_value = model

    idx = manager._ensure_timeout_choice("abc")
    assert idx is not None
    assert model.items[-1] == "abc"


def test_ensure_timeout_choice_none_widgets(manager):
    """Test _ensure_timeout_choice with None widgets."""
    manager.timeout_dropdown = None
    assert manager._ensure_timeout_choice("5") is None

    manager.timeout_dropdown = MagicMock()
    manager.timeout_dropdown.get_model.return_value = None
    assert manager._ensure_timeout_choice("5") is None


def test_ensure_timeout_choice_new_value(manager):
    """Test _ensure_timeout_choice when adding a new value."""
    model = MagicMock()
    model.get_n_items.return_value = 3
    model.get_string.side_effect = lambda i: ["1", "5", "10"][i]

    manager.timeout_dropdown.get_model.return_value = model

    # Execute with a value not in the list ("3" should be inserted between "1" and "5", so index 1)
    manager._ensure_timeout_choice("3")

    # Verify splice was called: index 1, remove 0, add ["3"]
    model.splice.assert_called_with(1, 0, ["3"])


def test_ensure_timeout_choice_exception(manager):
    """Test _ensure_timeout_choice when splice raises exception."""
    model = MagicMock()
    model.get_n_items.return_value = 3
    model.get_string.side_effect = lambda i: ["1", "5", "10"][i]

    # Make splice raise an exception to trigger the fallback
    model.splice.side_effect = TypeError("Splice failed")

    manager.timeout_dropdown.get_model.return_value = model

    # Call with new value
    manager._ensure_timeout_choice("3")

    # Verify fallback to append was called
    model.append.assert_called_with("3")


def test_ensure_timeout_choice_loop_completion(manager):
    """Test _ensure_timeout_choice loop completion (no break)."""
    manager.timeout_dropdown = MagicMock()
    model = MagicMock()
    manager.timeout_dropdown.get_model.return_value = model

    # Setup model with values smaller than wanted "100"
    model.get_n_items.return_value = 2
    model.get_string.side_effect = ["10", "20"]

    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", side_effect=[None, 2]):
        # Wanted "100" > "10" and "20", so loop finishes without break
        # insert_at should remain 2 (initial value)
        with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_insert") as mock_insert:
            manager._ensure_timeout_choice("100")
            mock_insert.assert_called_with(model, 2, "100")


def test_set_timeout_value(manager):
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    # Set normal value
    manager.set_timeout_value(10)
    manager.timeout_dropdown.set_selected.assert_called_with(1)

    # Set value not in list -> adds it
    manager.set_timeout_value(15)
    assert "15" in model.items
    manager.timeout_dropdown.set_selected.assert_called_with(2)


def test_set_timeout_value_edge_cases(manager):
    """Test _set_timeout_value edge cases."""
    manager.timeout_dropdown = None
    manager.set_timeout_value(5)  # Should return early

    manager.timeout_dropdown = MagicMock()
    with patch.object(manager, "_ensure_timeout_choice", return_value=None):
        manager.set_timeout_value(5)
        manager.timeout_dropdown.set_selected.assert_called_with(0)


def test_refresh_default_choices(manager):
    choices = [
        GrubDefaultChoice(id="id1", title="Choice 1", source="src1"),
        GrubDefaultChoice(id="id2", title="Choice 2", source="src2"),
    ]
    model = MockStringList(["Old Choice"])
    manager.default_dropdown.get_model.return_value = model

    manager.refresh_default_choices(choices)

    assert "Choice 1" in model.items
    assert "Choice 2" in model.items
    assert "saved (dernière sélection)" in model.items
    assert "Old Choice" not in model.items

    manager.state_manager.update_default_choice_ids.assert_called()
    args = manager.state_manager.update_default_choice_ids.call_args[0][0]
    assert args == ["saved", "id1", "id2"]


def test_refresh_default_choices_none_widgets(manager):
    """Test _refresh_default_choices with None widgets."""
    manager.default_dropdown = None
    manager.refresh_default_choices([])

    manager.default_dropdown = MagicMock()
    manager.default_dropdown.get_model.return_value = None
    manager.refresh_default_choices([])


def test_get_default_choice(manager):
    model = MockStringList(["saved (dernière sélection)", "Choice 1"])
    manager.default_dropdown.get_model.return_value = model

    manager.default_dropdown.get_selected.return_value = 1
    manager.state_manager._default_choice_ids = ["saved", "id1"]

    assert manager.get_default_choice() == "id1"


def test_get_default_choice_edge_cases(manager):
    """Test _get_default_choice edge cases."""
    manager.default_dropdown = None
    assert manager.get_default_choice() == "0"

    manager.default_dropdown = MagicMock()
    manager.default_dropdown.get_selected.return_value = None
    assert manager.get_default_choice() == "0"

    manager.default_dropdown.get_selected.return_value = 0
    manager.state_manager.get_default_choice_ids = MagicMock(side_effect=Exception("Mock"))
    assert manager.get_default_choice() == "0"


def test_set_default_choice(manager):
    model = MockStringList(["saved (dernière sélection)", "Choice 1"])
    manager.default_dropdown.get_model.return_value = model

    manager.state_manager.get_default_choice_ids.return_value = ["saved", "id1"]

    manager.set_default_choice("id1")

    manager.default_dropdown.set_selected.assert_called_with(1)


def test_set_default_choice_branches(manager):
    """Test _set_default_choice branches."""
    manager.default_dropdown = MagicMock()
    model = MagicMock()
    manager.default_dropdown.get_model.return_value = model

    # Case 1: "saved"
    manager.set_default_choice("saved")
    manager.default_dropdown.set_selected.assert_called_with(0)

    # Case 2: Existing ID
    manager.state_manager._default_choice_ids = ["saved", "id1", "id2"]
    manager.set_default_choice("id2")
    manager.default_dropdown.set_selected.assert_called_with(2)

    # Case 3: New ID (append)
    manager.set_default_choice("new_id")
    model.append.assert_called_with("new_id")
    # Should update ids and select last
    assert manager.state_manager.update_default_choice_ids.called

    # Case 4: Exception during append
    model.append.side_effect = Exception("Error")
    manager.set_default_choice("error_id")
    manager.default_dropdown.set_selected.assert_called_with(0)


def test_set_default_choice_model_none(manager):
    """Test _set_default_choice when dropdown model is None."""
    manager.default_dropdown.get_model.return_value = None
    manager.set_default_choice("some_value")
    manager.default_dropdown.set_selected.assert_called_with(0)


def test_set_default_choice_dropdown_none_returns(manager):
    manager.default_dropdown = None
    manager.set_default_choice("id1")


def test_set_default_choice_empty_value_defaults_to_zero(manager):
    manager.default_dropdown.get_model.return_value = None
    manager.set_default_choice("   ")
    manager.default_dropdown.set_selected.assert_called_with(0)


# --- Event Handlers ---


def test_on_modified(manager):
    manager.state_manager.is_loading.return_value = False
    manager.on_modified(None)
    manager.state_manager.mark_dirty.assert_called_once()


def test_on_modified_loading(manager):
    manager.state_manager.is_loading.return_value = True
    manager.on_modified(None)
    manager.state_manager.mark_dirty.assert_not_called()


def test_on_hidden_timeout_toggled(manager):
    widget = MagicMock()
    widget.get_active.return_value = True
    with patch.object(manager, "sync_timeout_choices") as mock_sync:
        manager.on_hidden_timeout_toggled(widget)
        mock_sync.assert_called()


def test_on_hidden_timeout_toggled_inactive(manager):
    """Test on_hidden_timeout_toggled when widget is inactive."""
    widget = MagicMock()
    widget.get_active.return_value = False
    manager.on_modified = MagicMock()

    manager.on_hidden_timeout_toggled(widget)

    # Should call on_modified
    manager.on_modified.assert_called_with(widget)


def test_on_hidden_timeout_toggled_loading(manager):
    """Test on_hidden_timeout_toggled when loading."""
    manager.state_manager.is_loading.return_value = True
    widget = MagicMock()
    manager.on_hidden_timeout_toggled(widget)
    widget.get_active.assert_not_called()


def test_on_menu_options_toggled(manager):
    """Cover lines 458-460: on_menu_options_toggled."""
    widget = MagicMock()
    with patch("ui.ui_manager.render_entries_view") as mock_render:
        manager.on_menu_options_toggled(widget)

        manager.state_manager.mark_dirty.assert_called()
        mock_render.assert_called_once_with(manager)


def test_on_menu_options_toggled_loading(manager):
    """Test on_menu_options_toggled when loading."""
    manager.state_manager.is_loading.return_value = True
    manager.on_modified = MagicMock()
    manager.on_menu_options_toggled(MagicMock())
    manager.on_modified.assert_not_called()


def test_on_save_delegates_to_workflow(manager):
    button = MagicMock()
    manager.on_save(button)
    manager.workflow.on_save.assert_called_once_with(button)


def test_on_reload_delegates_to_workflow(manager):
    button = MagicMock()
    manager.on_reload(button)
    manager.workflow.on_reload.assert_called_once_with(button)


def test_perform_save_delegates_to_workflow(manager):
    manager.perform_save(apply_now=True)
    manager.workflow.perform_save.assert_called_once_with(True)


def test_wrappers_when_workflow_missing_do_nothing(manager):
    manager.workflow = None
    manager.on_reload(MagicMock())
    manager.on_save(MagicMock())
    manager.perform_save(True)


def test_on_hide_category_toggled_loading_returns(manager):
    widget = MagicMock()
    widget.category_name = "advanced_options"
    manager.state_manager.is_loading.return_value = True

    with (
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_manager.save_hidden_entry_ids") as mock_save,
    ):
        manager.on_hide_category_toggled(widget)
        assert not mock_render.called
        assert not mock_save.called


def test_on_hide_category_toggled_unknown_category_returns(manager):
    widget = MagicMock()
    widget.category_name = "unknown"
    widget.get_active.return_value = True

    manager.state_manager.is_loading.return_value = False

    with (
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_manager.save_hidden_entry_ids") as mock_save,
    ):
        manager.on_hide_category_toggled(widget)
        assert not mock_render.called
        assert not mock_save.called


def test_on_hide_category_toggled_no_matching_ids_returns(manager):
    widget = MagicMock()
    widget.category_name = "advanced_options"
    widget.get_active.return_value = True

    manager.state_manager.is_loading.return_value = False
    manager.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_manager.save_hidden_entry_ids") as mock_save,
    ):
        manager.on_hide_category_toggled(widget)
        assert not mock_render.called
        assert not mock_save.called


def test_on_hide_category_toggled_advanced_adds_ids_and_marks_dirty(manager):
    widget = MagicMock()
    widget.category_name = "advanced_options"
    widget.get_active.return_value = True

    manager.state_manager.is_loading.return_value = False

    entry_class = dataclasses.make_dataclass("Entry", [("menu_id", str), ("title", str), ("source", str)])
    e1 = entry_class("id-adv", "Advanced options for Ubuntu", "")
    manager.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[e1], raw_config={})
    manager.state_manager.hidden_entry_ids = set()

    with (
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_manager.save_hidden_entry_ids") as mock_save,
        patch.object(manager, "_apply_state") as mock_apply_state,
    ):
        manager.on_hide_category_toggled(widget)

    assert "id-adv" in manager.state_manager.hidden_entry_ids
    assert manager.state_manager.entries_visibility_dirty is True
    assert mock_save.called
    assert mock_apply_state.called
    assert mock_render.called


def test_on_hide_category_toggled_advanced_skips_invalid_and_non_matching_entries(manager):
    widget = MagicMock()
    widget.category_name = "advanced_options"
    widget.get_active.return_value = True

    manager.state_manager.is_loading.return_value = False

    entry_class = dataclasses.make_dataclass("Entry2", [("menu_id", str), ("title", str), ("source", str)])
    e0 = entry_class("", "Advanced options", "")
    e1 = entry_class("id-other", "Ubuntu", "")
    e2 = entry_class("id-adv", "Options avancées", "")

    manager.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[e0, e1, e2], raw_config={})
    manager.state_manager.hidden_entry_ids = set()

    with (
        patch("ui.ui_manager.render_entries_view"),
        patch("ui.ui_manager.save_hidden_entry_ids"),
        patch.object(manager, "_apply_state"),
    ):
        manager.on_hide_category_toggled(widget)

    assert manager.state_manager.hidden_entry_ids == {"id-adv"}


def test_on_hide_category_toggled_memtest_removes_ids(manager):
    widget = MagicMock()
    widget.category_name = "memtest"
    widget.get_active.return_value = False

    manager.state_manager.is_loading.return_value = False

    entry_class = dataclasses.make_dataclass("Entry", [("menu_id", str), ("title", str), ("source", str)])
    e1 = entry_class("id-mem", "Memtest86+", "memtest")
    manager.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[e1], raw_config={})
    manager.state_manager.hidden_entry_ids = {"id-mem"}

    with (
        patch("ui.ui_manager.render_entries_view"),
        patch("ui.ui_manager.save_hidden_entry_ids"),
        patch.object(manager, "_apply_state"),
    ):
        manager.on_hide_category_toggled(widget)

    assert "id-mem" not in manager.state_manager.hidden_entry_ids


def test_on_hide_category_toggled_memtest_adds_ids(manager):
    widget = MagicMock()
    widget.category_name = "memtest"
    widget.get_active.return_value = True

    manager.state_manager.is_loading.return_value = False

    entry_class = dataclasses.make_dataclass("Entry3", [("menu_id", str), ("title", str), ("source", str)])
    e0 = entry_class("", "memtest", "memtest")
    e1 = entry_class("id-other", "Ubuntu", "")
    e2 = entry_class("id-mem", "Memtest86+", "")
    manager.state_manager.state_data = GrubUiState(model=GrubUiModel(), entries=[e0, e1, e2], raw_config={})
    manager.state_manager.hidden_entry_ids = set()

    with (
        patch("ui.ui_manager.render_entries_view"),
        patch("ui.ui_manager.save_hidden_entry_ids"),
        patch.object(manager, "_apply_state"),
    ):
        manager.on_hide_category_toggled(widget)

    assert "id-mem" in manager.state_manager.hidden_entry_ids


# --- Info Display ---


def test_show_info(manager):
    manager.show_info("Test message", "info")

    manager.info_label.set_text.assert_called_with("Test message")
    manager.info_revealer.set_reveal_child.assert_called_with(True)


def test_show_info_already_visible(manager):
    manager.show_info("New message", "error")

    manager.info_label.set_text.assert_called_with("New message")
    manager.info_revealer.set_reveal_child.assert_called_with(True)


def test_show_info_invalid_type(manager):
    """Cover show_info with invalid msg_type."""
    manager.show_info("Test message", "INVALID_TYPE")
    manager.info_revealer.set_reveal_child.assert_called_with(True)


def test_show_info_none_widgets(manager):
    """Test show_info with None widgets."""
    manager.info_label = None
    manager.show_info("msg", "info")

    manager.info_label = MagicMock()
    manager.info_box = None
    manager.show_info("msg", "info")

    manager.info_box = MagicMock()
    manager.info_revealer = None
    manager.show_info("msg", "info")


def test_show_info_delegates_to_infobar_when_present(manager):
    infobar = MagicMock()
    manager.infobar = infobar

    manager.show_info("Hello", "info")
    infobar.show.assert_called_once_with("Hello", "info")


def test_hide_info_callback_none_revealer(manager):
    """Test _hide_info_callback when revealer is None."""
    manager.info_revealer = None
    result = manager.hide_info_callback()
    assert result is False


def test_load_config_parsing_error(manager):
    """Test load_config exception handling for GrubParsingError."""
    manager.info_label = MagicMock()
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    from core.core_exceptions import GrubParsingError
    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", side_effect=GrubParsingError("Invalid config")),
    ):
        manager.load_config()
        # Should show error info
        assert manager.show_info.called
        args = manager.show_info.call_args[0]
        assert "Configuration GRUB invalide" in args[0]


def test_hide_info_callback_delegates_when_infobar_present(manager):
    infobar = MagicMock()
    infobar.hide_info_callback.return_value = True
    manager.infobar = infobar

    assert manager.hide_info_callback() is True
