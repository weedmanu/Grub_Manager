"""Helpers communs pour les onglets UI (GTK4)."""

from __future__ import annotations

from gi.repository import Gtk
from loguru import logger


def apply_margins(widget: Gtk.Widget, margin: int = 12) -> None:
    """Apply uniform margins to all sides of a GTK4 widget.

    Sets top, bottom, start (left), and end (right) margins in pixels.
    Simplifies layout spacing for consistent UI appearance.
    """
    logger.debug(f"[apply_margins] margin={margin} pour {widget.__class__.__name__}")
    widget.set_margin_top(margin)
    widget.set_margin_bottom(margin)
    widget.set_margin_start(margin)
    widget.set_margin_end(margin)


def make_scrolled_grid(
    *,
    h_policy: Gtk.PolicyType = Gtk.PolicyType.NEVER,
    v_policy: Gtk.PolicyType = Gtk.PolicyType.AUTOMATIC,
    margin: int = 12,
    col_spacing: int = 12,
    row_spacing: int = 12,
) -> tuple[Gtk.ScrolledWindow, Gtk.Grid]:
    """Create scrollable grid container with uniform column layout.

    Returns scrolled window containing a Grid with configurable column/row
    spacing. Used for responsive tab layouts.
    """
    logger.debug(
        f"[make_scrolled_grid] Création scrolled grid - margin={margin}, spacing=({col_spacing},{row_spacing})"
    )
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(h_policy, v_policy)

    grid = Gtk.Grid()
    grid.set_column_spacing(col_spacing)
    grid.set_row_spacing(row_spacing)
    apply_margins(grid, margin)

    scroll.set_child(grid)
    return scroll, grid
