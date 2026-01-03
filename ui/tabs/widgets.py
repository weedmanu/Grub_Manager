"""Widgets/helpers réutilisables pour composer les onglets (GTK4).

But: réduire la duplication lors de la création de lignes label + contrôle.
"""

from __future__ import annotations

from gi.repository import Gtk
from loguru import logger


def grid_add_labeled(
    grid: Gtk.Grid,
    row: int,
    label_text: str,
    widget: Gtk.Widget,
    *,
    label_xalign: float = 0,
    label_valign: Gtk.Align | None = None,
) -> int:
    """Ajoute une ligne `Label + Widget` à un `Gtk.Grid`.

    DEV: Helper pour layout uniforme label + contrôle.

    Returns:
        Le prochain index de ligne.
    """
    logger.debug(f"[grid_add_labeled] Ligne {row}: {label_text[:30]} + {widget.__class__.__name__}")
    label = Gtk.Label(label=label_text, xalign=label_xalign)
    if label_valign is not None:
        label.set_valign(label_valign)
    grid.attach(label, 0, row, 1, 1)
    grid.attach(widget, 1, row, 1, 1)
    return row + 1


def grid_add_check(grid: Gtk.Grid, row: int, check: Gtk.CheckButton, *, colspan: int = 2) -> int:
    """Ajoute un `Gtk.CheckButton` sur une ligne du `Gtk.Grid`.

    DEV: Helper pour checkbox sur ligne complète.

    Returns:
        Le prochain index de ligne.
    """
    logger.debug(f"[grid_add_check] Ligne {row}: {check.get_label()[:30]}")
    grid.attach(check, 0, row, colspan, 1)
    return row + 1


def box_append_label(
    box: Gtk.Box,
    text: str,
    *,
    halign: Gtk.Align = Gtk.Align.START,
    italic: bool = False,
) -> Gtk.Label:
    """Ajoute un label à une `Gtk.Box` et renvoie le widget créé."""
    logger.debug(f"[box_append_label] Label: {text[:30]} (italic={italic})")
    label = Gtk.Label()
    if italic:
        label.set_markup(f"<i>{text}</i>")
    else:
        label.set_text(text)
    label.set_halign(halign)
    box.append(label)
    return label


def box_append_section_title(box: Gtk.Box, text: str) -> Gtk.Label:
    """Ajoute un titre de section (sobre) dans une `Gtk.Box`."""
    logger.debug(f"[box_append_section_title] Titre: {text}")
    label = Gtk.Label()
    label.set_markup(f"<b>{text}</b>")
    label.set_halign(Gtk.Align.START)
    box.append(label)
    return label


def clear_listbox(listbox: Gtk.ListBox) -> None:
    """Remove all rows from GTK4 ListBox widget.

    Efficiently clears all children from listbox. Used before refreshing
    dynamic lists (backups, entries).
    """
    logger.debug("[clear_listbox] Nettoyage de la ListBox")
    child = listbox.get_first_child()
    count = 0
    while child is not None:
        nxt = child.get_next_sibling()
        listbox.remove(child)
        count += 1
        child = nxt
    logger.debug(f"[clear_listbox] {count} ligne(s) supprimée(s)")
