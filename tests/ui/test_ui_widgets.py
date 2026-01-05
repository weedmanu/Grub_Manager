import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import pytest
from gi.repository import Gtk

from ui.builders.ui_builders_widgets import (
    LabelOptions,
    apply_margins,
    box_append_label,
    box_append_section_title,
    categorize_backup_type,
    clear_listbox,
    create_error_dialog,
    create_list_box_row_with_margins,
    create_main_box,
    create_section_header,
    create_section_title,
    create_success_dialog,
    grid_add_check,
    grid_add_labeled,
    make_scrolled_grid,
)


def test_section_widgets():
    header = create_section_header("Header")
    assert isinstance(header, Gtk.Label)
    assert "Header" in header.get_label()

    title = create_section_title("Title")
    assert isinstance(title, Gtk.Label)
    assert "Title" in title.get_label()


def test_grid_helpers():
    grid = Gtk.Grid()
    widget = Gtk.Entry()

    row = grid_add_labeled(grid, 0, "Label", widget, label=LabelOptions(valign=Gtk.Align.CENTER))
    assert row == 1

    row = grid_add_labeled(grid, 1, "Label 2", Gtk.Entry())
    assert row == 2

    check = Gtk.CheckButton(label="Check")
    row = grid_add_check(grid, row, check)
    assert row == 3


def test_make_scrolled_grid():
    scroll, grid = make_scrolled_grid()
    assert isinstance(scroll, Gtk.ScrolledWindow)
    assert isinstance(grid, Gtk.Grid)
    # In GTK4, ScrolledWindow might wrap non-scrollable children in a Viewport
    child = scroll.get_child()
    if isinstance(child, Gtk.Viewport):
        assert child.get_child() == grid
    else:
        assert child == grid


def test_box_helpers():
    box = Gtk.Box()
    apply_margins(box, 10)
    assert box.get_margin_top() == 10

    box_append_label(box, "Test Label", italic=False)
    box_append_label(box, "Test Label Italic", italic=True)
    box_append_section_title(box, "Section Title")

    switch = Gtk.Switch()
    from ui.builders.ui_builders_widgets import box_append_switch

    box_append_switch(box, "Switch Label", switch)

    main_box = create_main_box(spacing=5, margin=10)
    assert main_box.get_spacing() == 5


def test_grid_add_switch():
    grid = Gtk.Grid()
    switch = Gtk.Switch()
    from ui.builders.ui_builders_widgets import grid_add_switch

    next_row = grid_add_switch(grid, 0, "Switch Label", switch)
    assert next_row == 1


def test_create_two_column_layout():
    parent = Gtk.Box()
    from ui.builders.ui_builders_widgets import create_two_column_layout

    columns, left, right = create_two_column_layout(parent, spacing=20)
    assert columns.get_parent() == parent
    assert left.get_parent() == columns
    assert right.get_parent() == columns
    assert columns.get_spacing() == 20


def test_create_info_box():
    from ui.builders.ui_builders_widgets import create_info_box

    box = create_info_box("Title", "Content")
    assert isinstance(box, Gtk.Box)
    title_label = box.get_first_child()
    assert "Title" in title_label.get_label()
    content_label = title_label.get_next_sibling()
    assert content_label.get_label() == "Content"

    box_no_title = create_info_box("", "Content Only")
    label = box_no_title.get_first_child()
    assert label.get_label() == "Content Only"


def test_listbox_helpers():
    row, hbox = create_list_box_row_with_margins()
    assert isinstance(row, Gtk.ListBoxRow)
    assert isinstance(hbox, Gtk.Box)

    listbox = Gtk.ListBox()
    listbox.append(row)
    assert listbox.get_first_child() is not None

    clear_listbox(listbox)
    assert listbox.get_first_child() is None


def test_categorize_backup_type():
    assert categorize_backup_type("test.backup.initial") == "Initiale"
    assert categorize_backup_type("test.backup.manual.123") == "Manuelle"
    assert categorize_backup_type("test.backup") == "Auto (enregistrement)"
    assert categorize_backup_type("test.other") == "Auto"


def test_dialog_helpers():
    # Best-effort: en CI/headless, Gtk.Window peut échouer.
    try:
        parent = Gtk.Window()
        create_error_dialog("Error", parent=parent)
        create_success_dialog("Success", parent=parent)
    except Exception:
        pytest.skip("Dialog helpers require more complex setup")
