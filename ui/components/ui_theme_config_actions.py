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
class ThemeConfigCallbacks:
    """Callbacks utilisés par la colonne de droite."""

    on_preview: Callable[[], None]
    on_activate_theme: Callable[[Gtk.Button], None]
    on_deactivate_theme: Callable[[Gtk.Button], None]
    on_edit: Callable[[Gtk.Button], None]
    on_delete: Callable[[Gtk.Button], None]
    on_open_editor: Callable[[Gtk.Button], None]


@dataclass(frozen=True)
class _ThemeConfigButtons:
    preview_btn: Gtk.Button
    activate_theme_btn: Gtk.Button
    deactivate_theme_btn: Gtk.Button
    edit_btn: Gtk.Button
    delete_btn: Gtk.Button


@dataclass(frozen=True)
class ThemeConfigRightColumnParts:
    """Widgets de la colonne de droite (actions + outils) de l'onglet thèmes."""

    actions_title: Gtk.Label
    actions_box: Gtk.Box
    global_actions_box: Gtk.Box
    buttons: _ThemeConfigButtons


def build_theme_config_right_column(
    *,
    callbacks: ThemeConfigCallbacks,
) -> ThemeConfigRightColumnParts:
    """Construit les widgets de la colonne de droite (Actions + Outils).

    Ne modifie pas l'UX: mêmes labels, mêmes styles, même disposition.
    """

    def _make_button(
        label: str,
        *,
        sensitive: bool = False,
        css_class: str | None = None,
        on_clicked: Callable[[Gtk.Button], None] | None = None,
    ) -> Gtk.Button:
        btn = Gtk.Button(label=label)
        btn.set_halign(Gtk.Align.FILL)
        btn.set_sensitive(sensitive)
        if css_class:
            btn.add_css_class(css_class)
        if on_clicked:
            btn.connect("clicked", on_clicked)
        return btn

    def _on_preview_clicked(_button: Gtk.Button) -> None:
        callbacks.on_preview()

    actions_title = Gtk.Label(xalign=0)
    actions_title.set_markup("<b>Actions sur le thème</b>")
    actions_title.add_css_class("section-title")

    actions_box = Gtk.Box(orientation=VERTICAL, spacing=8)

    preview_btn = _make_button("👁️ Aperçu", on_clicked=_on_preview_clicked)
    actions_box.append(preview_btn)

    activate_theme_btn = _make_button(
        "▶️ Activer le thème",
        css_class="suggested-action",
        on_clicked=callbacks.on_activate_theme,
    )
    actions_box.append(activate_theme_btn)

    deactivate_theme_btn = _make_button(
        "⏸️ Désactiver le thème",
        css_class="destructive-action",
        on_clicked=callbacks.on_deactivate_theme,
    )
    actions_box.append(deactivate_theme_btn)

    sep_actions = Gtk.Separator(orientation=HORIZONTAL)
    sep_actions.set_margin_top(8)
    sep_actions.set_margin_bottom(8)
    actions_box.append(sep_actions)

    edit_btn = _make_button("✏️ Modifier", on_clicked=callbacks.on_edit)
    actions_box.append(edit_btn)

    delete_btn = _make_button(
        "🗑️ Supprimer",
        css_class="destructive-action",
        on_clicked=callbacks.on_delete,
    )
    actions_box.append(delete_btn)

    global_actions_box = Gtk.Box(orientation=VERTICAL, spacing=8)
    global_actions_box.set_valign(Gtk.Align.END)
    global_actions_box.set_vexpand(True)

    global_title = Gtk.Label(xalign=0)
    global_title.set_markup("<b>Outils</b>")
    global_title.add_css_class("section-title")
    global_actions_box.append(global_title)

    editor_btn = _make_button(
        "➕ Créer un nouveau thème",  # noqa: RUF001
        sensitive=True,
        on_clicked=callbacks.on_open_editor,
    )
    global_actions_box.append(editor_btn)

    return ThemeConfigRightColumnParts(
        actions_title=actions_title,
        actions_box=actions_box,
        global_actions_box=global_actions_box,
        buttons=_ThemeConfigButtons(
            preview_btn=preview_btn,
            activate_theme_btn=activate_theme_btn,
            deactivate_theme_btn=deactivate_theme_btn,
            edit_btn=edit_btn,
            delete_btn=delete_btn,
        ),
    )
