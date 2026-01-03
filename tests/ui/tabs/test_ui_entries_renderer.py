import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock, patch

from gi.repository import Gtk

from core.io.core_grub_menu_parser import GrubDefaultChoice
from ui.tabs.ui_entries_renderer import _entry_display_title, _entry_is_os_prober, _entry_is_recovery, render_entries


def test_entry_helpers():
    assert _entry_is_recovery("Ubuntu (recovery mode)") is True
    assert _entry_is_recovery("Ubuntu") is False
    assert _entry_is_recovery(None) is False

    assert (
        _entry_is_os_prober(GrubDefaultChoice(id="0", title="Windows", menu_id="osprober-123", source="30_os-prober"))
        is True
    )
    assert (
        _entry_is_os_prober(GrubDefaultChoice(id="0", title="Linux", menu_id="gnulinux-123", source="10_linux"))
        is False
    )
    assert _entry_is_os_prober(GrubDefaultChoice(id="0", title="Windows", menu_id="osprober-123", source=None)) is True

    assert _entry_display_title("Ubuntu", False) == "Ubuntu"
    assert _entry_display_title("Ubuntu >> Advanced", True) == "Advanced"
    assert _entry_display_title("Advanced options for Ubuntu > Ubuntu, with Linux", True) == "Ubuntu, with Linux"
    assert _entry_display_title("", False) == "(Untitled)"
    assert _entry_display_title("A" * 200, False) == "A" * 100


def test_render_entries_no_listbox():
    controller = MagicMock()
    controller.entries_listbox = None
    render_entries(controller)
    # Should just return without error


def test_render_entries_basic():
    controller = MagicMock()
    controller.entries_listbox = Gtk.ListBox()

    state_data = controller.state_manager.state_data
    state_data.entries = [
        GrubDefaultChoice(id="0", title="Ubuntu", menu_id="ubuntu-id", source="10_linux"),
        GrubDefaultChoice(id="1", title="Windows", menu_id="osprober-id", source="30_os-prober"),
        GrubDefaultChoice(id="2", title="Ubuntu (recovery)", menu_id="recovery-id", source="10_linux"),
    ]
    state_data.model.default = "0"

    controller.disable_recovery_check.get_active.return_value = False
    controller.disable_os_prober_check.get_active.return_value = False
    controller.disable_submenu_check.get_active.return_value = False

    controller.state_manager.hidden_entry_ids = ["osprober-id"]

    render_entries(controller)

    # Check that 3 entries were added
    count = 0
    child = controller.entries_listbox.get_first_child()
    while child:
        count += 1
        child = child.get_next_sibling()
    assert count == 3


def test_render_entries_filters():
    controller = MagicMock()
    controller.entries_listbox = Gtk.ListBox()

    state_data = controller.state_manager.state_data
    state_data.entries = [
        GrubDefaultChoice(id="0", title="Ubuntu", menu_id="ubuntu-id", source="10_linux"),
        GrubDefaultChoice(
            id="0>0",
            title="Advanced options for Ubuntu > Ubuntu, with Linux",
            menu_id="adv-id",
            source="10_linux",
        ),
        GrubDefaultChoice(id="1", title="Windows", menu_id="osprober-id", source="30_os-prober"),
        GrubDefaultChoice(id="2", title="Ubuntu (recovery)", menu_id="recovery-id", source="10_linux"),
        GrubDefaultChoice(id="3", title="Memory test (memtest86+)", menu_id="memtest-id", source="20_memtest86+"),
    ]
    state_data.model.default = "0"

    # Filter recovery and os-prober
    controller.disable_recovery_check.get_active.return_value = True
    controller.disable_os_prober_check.get_active.return_value = True
    controller.disable_submenu_check.get_active.return_value = False

    # New global filters
    controller.hide_advanced_options_check.get_active.return_value = True
    controller.hide_memtest_check.get_active.return_value = True

    render_entries(controller)

    # Only Ubuntu should remain
    count = 0
    child = controller.entries_listbox.get_first_child()
    while child:
        count += 1
        child = child.get_next_sibling()
    assert count == 1


def test_render_entries_toggle_signal():
    controller = MagicMock()
    controller.entries_listbox = Gtk.ListBox()
    choice = GrubDefaultChoice(id="0", title="Ubuntu", menu_id="ubuntu-id", source="10_linux")

    state_data = controller.state_manager.state_data
    state_data.entries = [choice]
    state_data.model.default = "0"

    controller.disable_recovery_check.get_active.return_value = False
    controller.disable_os_prober_check.get_active.return_value = False
    controller.disable_submenu_check.get_active.return_value = False

    controller.state_manager.hidden_entry_ids = set()

    render_entries(controller)

    # Find the switch in the row
    row = controller.entries_listbox.get_first_child()
    hbox = row.get_child()
    # The switch is the last child of hbox (based on typical implementation)
    # Let's find it
    switch = None
    child = hbox.get_first_child()
    while child:
        if isinstance(child, Gtk.Switch):
            switch = child
            break
        child = child.get_next_sibling()

    assert switch is not None

    # Trigger switch ON
    with patch("ui.tabs.ui_entries_renderer.save_hidden_entry_ids") as mock_save:
        switch.set_active(True)
        assert "ubuntu-id" in controller.state_manager.hidden_entry_ids
        mock_save.assert_called_once()

    # Trigger switch OFF
    with patch("ui.tabs.ui_entries_renderer.save_hidden_entry_ids") as mock_save:
        switch.set_active(False)
        assert "ubuntu-id" not in controller.state_manager.hidden_entry_ids
        mock_save.assert_called()


def test_render_entries_edge_cases():
    controller = MagicMock()
    controller.entries_listbox = Gtk.ListBox()

    state_data = controller.state_manager.state_data
    state_data.entries = [
        GrubDefaultChoice(id="0", title="Linux", menu_id="", source="10_linux"),  # No menu_id
        GrubDefaultChoice(id="2", title="Target", menu_id="target-id", source="10_linux"),  # Wanted ID
    ]
    state_data.model.default = "2"

    controller.disable_recovery_check.get_active.return_value = False
    controller.disable_os_prober_check.get_active.return_value = False
    controller.disable_submenu_check.get_active.return_value = False

    controller.state_manager.hidden_entry_ids = set()

    with patch("ui.tabs.ui_entries_renderer.get_simulated_os_prober_entries") as mock_sim:
        mock_sim.return_value = [
            GrubDefaultChoice(id="3", title="Simulated OS", menu_id="osprober-simulated-2", source="30_os-prober")
        ]
        render_entries(controller)
        assert mock_sim.called
