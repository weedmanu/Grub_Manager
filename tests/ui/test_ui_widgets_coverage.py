import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.ui_widgets import (
    apply_margins,
    box_append_label,
    box_append_section_title,
    box_append_switch,
    categorize_backup_type,
    clear_listbox,
    create_error_dialog,
    create_info_box,
    create_list_box_row_with_margins,
    create_main_box,
    create_section_header,
    create_section_title,
    create_success_dialog,
    create_two_column_layout,
    grid_add_check,
    grid_add_labeled,
    grid_add_switch,
    make_scrolled_grid,
)


def test_create_section_header():
    label = create_section_header("Test Header")
    assert isinstance(label, Gtk.Label)
    assert "Test Header" in label.get_label()

def test_create_section_title():
    label = create_section_title("Test Title")
    assert isinstance(label, Gtk.Label)
    assert "Test Title" in label.get_label()

def test_grid_add_labeled():
    grid = Gtk.Grid()
    widget = Gtk.Entry()
    next_row = grid_add_labeled(grid, 0, "Label", widget)
    assert next_row == 1
    # Check if label and widget are in grid
    assert grid.get_child_at(0, 0) is not None # Label
    assert grid.get_child_at(1, 0) == widget

def test_grid_add_labeled_with_valign():
    grid = Gtk.Grid()
    widget = Gtk.Entry()
    grid_add_labeled(grid, 0, "Label", widget, label_valign=Gtk.Align.CENTER)
    label = grid.get_child_at(0, 0)
    assert label.get_valign() == Gtk.Align.CENTER

def test_grid_add_check():
    grid = Gtk.Grid()
    check = Gtk.CheckButton(label="Check")
    next_row = grid_add_check(grid, 0, check)
    assert next_row == 1
    assert grid.get_child_at(0, 0) == check

def test_grid_add_switch():
    grid = Gtk.Grid()
    switch = Gtk.Switch()
    next_row = grid_add_switch(grid, 0, "Switch Label", switch)
    assert next_row == 1
    hbox = grid.get_child_at(0, 0)
    assert isinstance(hbox, Gtk.Box)

def test_box_append_label():
    box = Gtk.Box()
    label = box_append_label(box, "Test Label")
    assert label.get_text() == "Test Label"
    assert label.get_parent() == box

def test_box_append_label_italic():
    box = Gtk.Box()
    label = box_append_label(box, "Test Label", italic=True)
    assert "<i>Test Label</i>" in label.get_label()

def test_box_append_section_title():
    box = Gtk.Box()
    label = box_append_section_title(box, "Section Title")
    assert "<b>Section Title</b>" in label.get_label()
    assert label.get_parent() == box

def test_box_append_switch():
    box = Gtk.Box()
    switch = Gtk.Switch()
    hbox = box_append_switch(box, "Switch Label", switch)
    assert isinstance(hbox, Gtk.Box)
    assert hbox.get_parent() == box

def test_apply_margins():
    widget = Gtk.Box()
    apply_margins(widget, 20)
    assert widget.get_margin_top() == 20
    assert widget.get_margin_bottom() == 20
    assert widget.get_margin_start() == 20
    assert widget.get_margin_end() == 20

def test_create_main_box():
    box = create_main_box(spacing=15, margin=5)
    assert box.get_spacing() == 15
    assert box.get_margin_top() == 5

def test_make_scrolled_grid():
    scroll, grid = make_scrolled_grid(margin=10)
    assert isinstance(scroll, Gtk.ScrolledWindow)
    assert isinstance(grid, Gtk.Grid)
    assert grid.get_margin_top() == 10
    # Gtk.Grid doesn't implement Gtk.Scrollable, so it's wrapped in a Viewport
    child = scroll.get_child()
    if isinstance(child, Gtk.Viewport):
        assert child.get_child() == grid
    else:
        assert child == grid

def test_create_list_box_row_with_margins():
    row, hbox = create_list_box_row_with_margins(margin_top=10)
    assert isinstance(row, Gtk.ListBoxRow)
    assert isinstance(hbox, Gtk.Box)
    assert hbox.get_margin_top() == 10
    assert row.get_child() == hbox

def test_create_two_column_layout():
    parent = Gtk.Box()
    columns, left, right = create_two_column_layout(parent, spacing=20)
    assert columns.get_parent() == parent
    assert left.get_parent() == columns
    assert right.get_parent() == columns
    assert columns.get_spacing() == 20

def test_create_info_box():
    box = create_info_box("Title", "Content")
    assert isinstance(box, Gtk.Box)
    # Check if title and content are there
    # First child should be title label
    title_label = box.get_first_child()
    assert "Title" in title_label.get_label()
    # Second child should be content label
    content_label = title_label.get_next_sibling()
    assert content_label.get_label() == "Content"

def test_create_info_box_no_title():
    box = create_info_box("", "Content")
    label = box.get_first_child()
    assert label.get_label() == "Content"

def test_clear_listbox():
    listbox = Gtk.ListBox()
    for i in range(5):
        listbox.append(Gtk.Label(label=f"Item {i}"))

    # Verify it has 5 children
    count = 0
    child = listbox.get_first_child()
    while child:
        count += 1
        child = child.get_next_sibling()
    assert count == 5

    clear_listbox(listbox)

    # Verify it's empty
    assert listbox.get_first_child() is None

def test_create_error_dialog():
    # We can't easily test the dialog display in headless, but we can call it
    # to ensure it doesn't crash.
    create_error_dialog("Error message")

def test_create_success_dialog():
    create_success_dialog("Success message")

def test_categorize_backup_type():
    assert categorize_backup_type("file.backup.initial") == "Initiale"
    assert categorize_backup_type("file.backup.manual.123") == "Manuelle"
    assert categorize_backup_type("file.backup") == "Auto (enregistrement)"
    assert categorize_backup_type("other") == "Auto"
