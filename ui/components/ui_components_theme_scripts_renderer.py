"""Rendu partagé de la liste des scripts de thème GRUB.

Centralise le code de construction des lignes Gtk.ListBox.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger


def _resolve_executable_state(script: Any, pending_changes: dict[str, bool]) -> tuple[bool, bool]:
    is_executable = bool(getattr(script, "is_executable", False))
    script_path = getattr(script, "path", None)

    key_str = str(script_path) if script_path is not None else ""
    if key_str and key_str in pending_changes:
        return bool(pending_changes[key_str]), True

    return is_executable, False


def _format_script_name(script: Any, *, is_pending: bool) -> str:
    script_name = str(getattr(script, "name", ""))
    if script_name in ["05_debian_theme", "05_grub_colors"]:
        script_name += " (Défaut)"
    if is_pending:
        script_name += " *"
    return script_name


def _build_script_row(
    *,
    gtk_module: Any,
    script: Any,
    is_executable: bool,
    script_name: str,
    on_toggle: Callable[[Any, Any, Any | None], None],
) -> Any:
    horizontal = gtk_module.Orientation.HORIZONTAL
    vertical = gtk_module.Orientation.VERTICAL

    row = gtk_module.ListBoxRow()
    row.set_selectable(False)

    script_box = gtk_module.Box(orientation=horizontal, spacing=10)
    script_box.set_margin_top(8)
    script_box.set_margin_bottom(8)
    script_box.set_margin_start(10)
    script_box.set_margin_end(10)

    # Colonne gauche: nom uniquement (les notes sont affichées à droite au niveau de l'onglet)
    left_col = gtk_module.Box(orientation=vertical, spacing=4)
    left_col.set_hexpand(True)

    name_label = gtk_module.Label(label=script_name)
    name_label.set_halign(gtk_module.Align.START)
    name_label.set_hexpand(True)
    # Empêche un nom long d'augmenter la largeur minimale du Notebook.
    try:
        name_label.set_max_width_chars(40)
    except AttributeError:  # pragma: no cover
        pass
    name_label.add_css_class("title-4")
    left_col.append(name_label)

    script_box.append(left_col)

    state_label = gtk_module.Label(label="actif" if is_executable else "inactif")
    state_label.set_margin_end(10)
    if not is_executable:
        state_label.add_css_class("warning")
    script_box.append(state_label)

    switch = gtk_module.Switch()
    switch.set_active(is_executable)
    switch.set_valign(gtk_module.Align.CENTER)

    def _on_notify_active(sw: Any, _pspec: Any, *, _script=script, _lbl=state_label) -> None:
        on_toggle(sw, _script, _lbl)

    switch.connect("notify::active", _on_notify_active)
    script_box.append(switch)

    row.set_child(script_box)
    return row


def clear_list_box(list_box: Any) -> None:
    """Supprime tous les enfants d'une Gtk.ListBox (compatible mocks)."""
    while True:
        child = list_box.get_first_child()
        if child is None:
            break
        list_box.remove(child)


def populate_theme_scripts_list(
    *,
    gtk_module: Any,
    list_box: Any,
    theme_scripts: list[Any],
    pending_changes: dict[str, bool],
    on_toggle: Callable[[Any, Any, Any | None], None],
) -> None:
    """Remplit une Gtk.ListBox avec la liste des scripts.

    Args:
        GtkModule: module Gtk (souvent `Gtk`).
        list_box: Gtk.ListBox.
        theme_scripts: liste d'objets script.
        pending_changes: dict des changements en attente.
        on_toggle: callback appelé avec (switch, script, state_label).
    """
    for script in theme_scripts:
        is_executable, is_pending = _resolve_executable_state(script, pending_changes)
        script_name = _format_script_name(script, is_pending=is_pending)
        row = _build_script_row(
            gtk_module=gtk_module,
            script=script,
            is_executable=is_executable,
            script_name=script_name,
            on_toggle=on_toggle,
        )
        list_box.append(row)

    logger.debug(f"[populate_theme_scripts_list] Rendered {len(theme_scripts)} row(s)")
