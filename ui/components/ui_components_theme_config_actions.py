"""Composants UI pour l'onglet de configuration des thèmes.

Ce module extrait la construction de la colonne de droite (actions) afin de
réduire la taille de l'onglet et faciliter la maintenance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from gi.repository import Gtk

from ui.builders.ui_builders_widgets import box_append_section_grid

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
    """Construit les widgets de la colonne de droite (Actions + Outils)."""

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

    # --- Section Actions ---
    actions_container = Gtk.Box(orientation=VERTICAL, spacing=12)
    grid_actions = box_append_section_grid(
        actions_container,
        "Actions sur le thème",
        row_spacing=12,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )

    preview_btn = _make_button("Aperçu", on_clicked=_on_preview_clicked)
    grid_actions.attach(preview_btn, 0, 0, 2, 1)

    activate_theme_btn = _make_button(
        "Activer le thème",
        css_class="suggested-action",
        on_clicked=callbacks.on_activate_theme,
    )
    grid_actions.attach(activate_theme_btn, 0, 1, 2, 1)

    deactivate_theme_btn = _make_button(
        "Désactiver le thème",
        css_class="destructive-action",
        on_clicked=callbacks.on_deactivate_theme,
    )
    grid_actions.attach(deactivate_theme_btn, 0, 2, 2, 1)

    edit_btn = _make_button("Modifier", on_clicked=callbacks.on_edit)
    grid_actions.attach(edit_btn, 0, 3, 2, 1)

    delete_btn = _make_button(
        "Supprimer",
        css_class="destructive-action",
        on_clicked=callbacks.on_delete,
    )
    grid_actions.attach(delete_btn, 0, 4, 2, 1)

    # --- Section Outils ---
    global_actions_container = Gtk.Box(orientation=VERTICAL, spacing=12)
    grid_tools = box_append_section_grid(
        global_actions_container,
        "Outils de création",
        row_spacing=12,
        column_spacing=12,
        title_class="green",
        frame_class="green-frame",
    )

    editor_btn = _make_button(
        "Créer un nouveau thème",
        sensitive=True,
        on_clicked=callbacks.on_open_editor,
    )
    grid_tools.attach(editor_btn, 0, 0, 2, 1)

    return ThemeConfigRightColumnParts(
        actions_title=Gtk.Label(),  # Plus utilisé
        actions_box=actions_container,
        global_actions_box=global_actions_container,
        buttons=_ThemeConfigButtons(
            preview_btn=preview_btn,
            activate_theme_btn=activate_theme_btn,
            deactivate_theme_btn=deactivate_theme_btn,
            edit_btn=edit_btn,
            delete_btn=delete_btn,
        ),
    )
