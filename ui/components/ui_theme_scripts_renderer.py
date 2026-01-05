"""Rendu partagé de la liste des scripts de thème GRUB.

Centralise le code de construction des lignes Gtk.ListBox, utilisé par:
- le composant `ThemeScriptsList`
- la fonction de compat tests `_scan_grub_scripts` dans l'onglet
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger


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
    pending_changes: dict[Any, bool],
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
    horizontal = gtk_module.Orientation.HORIZONTAL

    for script in theme_scripts:
        row = gtk_module.ListBoxRow()
        row.set_selectable(False)

        script_box = gtk_module.Box(orientation=horizontal, spacing=10)
        script_box.set_margin_top(8)
        script_box.set_margin_bottom(8)
        script_box.set_margin_start(10)
        script_box.set_margin_end(10)

        is_executable = bool(getattr(script, "is_executable", False))
        is_pending = False

        script_path = getattr(script, "path", None)
        key_str = str(script_path) if script_path is not None else ""
        if key_str and key_str in pending_changes:
            is_executable = pending_changes[key_str]
            is_pending = True
        elif script_path is not None and script_path in pending_changes:  # compat: anciennes clés Path
            is_executable = pending_changes[script_path]
            is_pending = True

        script_name = str(getattr(script, "name", ""))
        if script_name in ["05_debian_theme", "05_grub_colors"]:
            script_name += " (Défaut)"
        if is_pending:
            script_name += " *"

        name_label = gtk_module.Label(label=script_name)
        name_label.set_halign(gtk_module.Align.START)
        name_label.set_hexpand(True)
        name_label.add_css_class("title-4")
        script_box.append(name_label)

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
        list_box.append(row)

    logger.debug(f"[populate_theme_scripts_list] Rendered {len(theme_scripts)} row(s)")
