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


def test_entry_display_title_disable_submenu_empty_parts_falls_back():
    # Cas limite: titre réduit à ">" après strip(), split() donne uniquement des éléments vides.
    assert _entry_display_title(">", True) == ">"


def test_render_entries_filters_memtest_and_advanced_are_executed():
    controller = MagicMock()
    controller.entries_listbox = Gtk.ListBox()

    state_data = controller.state_manager.state_data
    state_data.entries = [
        GrubDefaultChoice(id="0", title="Ubuntu", menu_id="ubuntu-id", source="10_linux"),
        GrubDefaultChoice(id="1", title="Memory test (memtest86+)", menu_id="memtest-id", source="20_memtest86+"),
        GrubDefaultChoice(
            id="2",
            title="Advanced options for Ubuntu > Ubuntu, with Linux",
            menu_id="adv-id",
            source="10_linux",
        ),
    ]
    state_data.model.default = "0"

    controller.disable_recovery_check.get_active.return_value = False
    controller.disable_os_prober_check.get_active.return_value = False
    controller.disable_submenu_check.get_active.return_value = False

    controller.hide_advanced_options_check.get_active.return_value = True
    controller.hide_memtest_check.get_active.return_value = True

    controller.state_manager.hidden_entry_ids = set()

    render_entries(controller)

    # Seul Ubuntu doit rester
    child = controller.entries_listbox.get_first_child()
    assert child is not None
    assert child.get_next_sibling() is None


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


import os

import pytest

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"



def test_entry_is_recovery():
    assert _entry_is_recovery("Linux recovery mode") is True
    assert _entry_is_recovery("Linux recup") is True
    assert _entry_is_recovery("Linux normal") is False
    assert _entry_is_recovery(None) is False


def test_entry_is_os_prober():
    c1 = MagicMock(spec=GrubDefaultChoice)
    c1.source = "30_os-prober"
    assert _entry_is_os_prober(c1) is True

    c2 = MagicMock(spec=GrubDefaultChoice)
    c2.source = "10_linux"
    c2.menu_id = "osprober-123"
    assert _entry_is_os_prober(c2) is True

    c3 = MagicMock(spec=GrubDefaultChoice)
    c3.source = "10_linux"
    c3.menu_id = "gnulinux-123"
    assert _entry_is_os_prober(c3) is False


def test_entry_display_title():
    assert _entry_display_title("", False) == "(Untitled)"
    assert _entry_display_title("Title >> Sub", True) == "Sub"
    assert _entry_display_title("Title >> Sub", False) == "Title >> Sub"
    assert _entry_display_title("Submenu > Entry", True) == "Entry"
    assert _entry_display_title("A" * 200, False) == "A" * 100


class MockController:
    def __init__(self):
        self.entries_listbox = MagicMock(spec=Gtk.ListBox)
        self.state_manager = MagicMock()
        self.state_manager.state_data = MagicMock()
        self.state_manager.state_data.model.default = "id1"
        self.state_manager.state_data.entries = []
        self.state_manager.hidden_entry_ids = set()
        self.state_manager.state = "clean"

        self.disable_recovery_check = MagicMock(spec=Gtk.CheckButton)
        self.disable_recovery_check.get_active.return_value = False

        self.disable_os_prober_check = MagicMock(spec=Gtk.CheckButton)
        self.disable_os_prober_check.get_active.return_value = False

        self.hide_advanced_options_check = MagicMock(spec=Gtk.Switch)
        self.hide_advanced_options_check.get_active.return_value = False

        self.hide_memtest_check = MagicMock(spec=Gtk.Switch)
        self.hide_memtest_check.get_active.return_value = False

        self.disable_submenu_check = MagicMock(spec=Gtk.CheckButton)
        self.disable_submenu_check.get_active.return_value = False

        self._apply_state = MagicMock()
        self.show_info = MagicMock()


@pytest.fixture
def controller():
    return MockController()


def test_render_entries_no_listbox():
    ctrl = MockController()
    ctrl.entries_listbox = None
    render_entries(ctrl)  # Should not crash


def test_render_entries_basic(controller):
    e1 = MagicMock(spec=GrubDefaultChoice)
    e1.title = "Entry 1"
    e1.menu_id = "id1"
    e1.id = "id1"
    e1.source = "10_linux"

    controller.state_manager.state_data.entries = [e1]

    with patch("ui.tabs.ui_entries_renderer.clear_listbox"):
        render_entries(controller)

    assert controller.entries_listbox.append.called


def test_render_entries_filters(controller):
    e_rec = MagicMock(spec=GrubDefaultChoice)
    e_rec.title = "Recovery"
    e_rec.menu_id = "rec"
    e_rec.source = "10_linux"

    e_os = MagicMock(spec=GrubDefaultChoice)
    e_os.title = "Windows"
    e_os.menu_id = "osprober-win"
    e_os.source = "30_os-prober"

    controller.state_manager.state_data.entries = [e_rec, e_os]
    controller.disable_recovery_check.get_active.return_value = True
    controller.disable_os_prober_check.get_active.return_value = True

    with patch("ui.tabs.ui_entries_renderer.clear_listbox"):
        render_entries(controller)

    # Both should be filtered out
    assert controller.entries_listbox.append.call_count == 0


def test_render_entries_simulated_os_prober(controller):
    controller.state_manager.state_data.entries = []
    controller.disable_os_prober_check.get_active.return_value = False

    simulated = MagicMock(spec=GrubDefaultChoice)
    simulated.title = "Simulated"
    simulated.menu_id = "osprober-simulated-1"
    simulated.source = "30_os-prober"
    simulated.id = "sim1"

    with (
        patch("ui.tabs.ui_entries_renderer.get_simulated_os_prober_entries", return_value=[simulated]),
        patch("ui.tabs.ui_entries_renderer.clear_listbox"),
    ):
        render_entries(controller)

    assert controller.entries_listbox.append.called


def test_render_entries_no_id_and_simulated_masking(controller):
    e_no_id = MagicMock(spec=GrubDefaultChoice)
    e_no_id.title = "No ID"
    e_no_id.menu_id = ""
    e_no_id.source = "10_linux"
    e_no_id.id = "no-id"

    e_sim = MagicMock(spec=GrubDefaultChoice)
    e_sim.title = "Simulated"
    e_sim.menu_id = "osprober-simulated-1"
    e_sim.source = "30_os-prober"
    e_sim.id = "sim1"

    controller.state_manager.state_data.entries = [e_no_id, e_sim]

    with patch("ui.tabs.ui_entries_renderer.clear_listbox"):
        render_entries(controller)

    assert controller.entries_listbox.append.called


def test_render_entries_switch_toggle(controller):
    e1 = MagicMock(spec=GrubDefaultChoice)
    e1.title = "Entry 1"
    e1.menu_id = "id1"
    e1.id = "id1"
    e1.source = "10_linux"

    controller.state_manager.state_data.entries = [e1]
    controller.state_manager.hidden_entry_ids = set()

    # We'll use a real switch but mock the controller methods it calls
    with patch("ui.tabs.ui_entries_renderer.save_hidden_entry_ids"), patch("ui.tabs.ui_entries_renderer.clear_listbox"):

        render_entries(controller)

        # Find the switch in the listbox
        # controller.entries_listbox.append(row)
        row = controller.entries_listbox.append.call_args[0][0]
        hbox = row.get_child()
        # hbox has num_label, title_label, switch
        # In GTK4 we can't easily get children by index without a loop or knowing the structure
        # But we can find the switch by type
        switch = None
        child = hbox.get_first_child()
        while child:
            if isinstance(child, Gtk.Switch):
                switch = child
                break
            child = child.get_next_sibling()

        assert switch is not None

        # Toggle ON
        switch.set_active(True)
        # notify::active should have been triggered
        assert "id1" in controller.state_manager.hidden_entry_ids

        # Toggle OFF
        switch.set_active(False)
        assert "id1" not in controller.state_manager.hidden_entry_ids
