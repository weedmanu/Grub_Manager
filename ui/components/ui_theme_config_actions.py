"""Composants UI pour l'onglet de configuration des thèmes.

Ce module extrait la construction de la colonne de droite (actions) afin de
réduire la taille de l'onglet et faciliter la maintenance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from gi.repository import Gtk

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


@dataclass(frozen=True)
class ThemeConfigRightColumnParts:
    """Widgets de la colonne de droite (actions + outils) de l'onglet thèmes."""

    actions_title: Gtk.Label
    actions_box: Gtk.Box
    global_actions_box: Gtk.Box

    preview_btn: Gtk.Button
    activate_theme_btn: Gtk.Button
    deactivate_theme_btn: Gtk.Button
    edit_btn: Gtk.Button
    delete_btn: Gtk.Button


def build_theme_config_right_column(
    *,
    on_preview: Callable[[], None],
    on_activate_theme: Callable[[Gtk.Button], None],
    on_deactivate_theme: Callable[[Gtk.Button], None],
    on_edit: Callable[[Gtk.Button], None],
    on_delete: Callable[[Gtk.Button], None],
    on_open_editor: Callable[[Gtk.Button], None],
) -> ThemeConfigRightColumnParts:
    """Construit les widgets de la colonne de droite (Actions + Outils).

    Ne modifie pas l'UX: mêmes labels, mêmes styles, même disposition.
    """

    def _on_preview_clicked(_button: Gtk.Button) -> None:
        on_preview()

    actions_title = Gtk.Label(xalign=0)
    actions_title.set_markup("<b>Actions sur le thème</b>")
    actions_title.add_css_class("section-title")

    actions_box = Gtk.Box(orientation=VERTICAL, spacing=8)

    preview_btn = Gtk.Button(label="👁️ Aperçu")
    preview_btn.set_halign(Gtk.Align.FILL)
    preview_btn.set_sensitive(False)
    preview_btn.connect("clicked", _on_preview_clicked)
    actions_box.append(preview_btn)

    activate_theme_btn = Gtk.Button(label="▶️ Activer le thème")
    activate_theme_btn.set_halign(Gtk.Align.FILL)
    activate_theme_btn.set_sensitive(False)
    activate_theme_btn.add_css_class("suggested-action")
    activate_theme_btn.connect("clicked", on_activate_theme)
    actions_box.append(activate_theme_btn)

    deactivate_theme_btn = Gtk.Button(label="⏸️ Désactiver le thème")
    deactivate_theme_btn.set_halign(Gtk.Align.FILL)
    deactivate_theme_btn.set_sensitive(False)
    deactivate_theme_btn.add_css_class("destructive-action")
    deactivate_theme_btn.connect("clicked", on_deactivate_theme)
    actions_box.append(deactivate_theme_btn)

    sep_actions = Gtk.Separator(orientation=HORIZONTAL)
    sep_actions.set_margin_top(8)
    sep_actions.set_margin_bottom(8)
    actions_box.append(sep_actions)

    edit_btn = Gtk.Button(label="✏️ Modifier")
    edit_btn.set_halign(Gtk.Align.FILL)
    edit_btn.set_sensitive(False)
    edit_btn.connect("clicked", on_edit)
    actions_box.append(edit_btn)

    delete_btn = Gtk.Button(label="🗑️ Supprimer")
    delete_btn.set_halign(Gtk.Align.FILL)
    delete_btn.set_sensitive(False)
    delete_btn.add_css_class("destructive-action")
    delete_btn.connect("clicked", on_delete)
    actions_box.append(delete_btn)

    global_actions_box = Gtk.Box(orientation=VERTICAL, spacing=8)
    global_actions_box.set_valign(Gtk.Align.END)
    global_actions_box.set_vexpand(True)

    global_title = Gtk.Label(xalign=0)
    global_title.set_markup("<b>Outils</b>")
    global_title.add_css_class("section-title")
    global_actions_box.append(global_title)

    editor_btn = Gtk.Button(label="➕ Créer un nouveau thème")  # noqa: RUF001
    editor_btn.set_halign(Gtk.Align.FILL)
    editor_btn.connect("clicked", on_open_editor)
    global_actions_box.append(editor_btn)

    return ThemeConfigRightColumnParts(
        actions_title=actions_title,
        actions_box=actions_box,
        global_actions_box=global_actions_box,
        preview_btn=preview_btn,
        activate_theme_btn=activate_theme_btn,
        deactivate_theme_btn=deactivate_theme_btn,
        edit_btn=edit_btn,
        delete_btn=delete_btn,
    )
