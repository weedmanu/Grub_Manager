
import os
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gtk

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from core.io.core_grub_menu_parser import GrubDefaultChoice
from ui.tabs.ui_entries_renderer import _entry_display_title, _entry_is_os_prober, _entry_is_recovery, render_entries


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
    render_entries(ctrl) # Should not crash

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

    with patch("ui.tabs.ui_entries_renderer.get_simulated_os_prober_entries", return_value=[simulated]), \
         patch("ui.tabs.ui_entries_renderer.clear_listbox"):
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
    with patch("ui.tabs.ui_entries_renderer.save_hidden_entry_ids"), \
         patch("ui.tabs.ui_entries_renderer.clear_listbox"):

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
