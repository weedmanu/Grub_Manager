"""Aides UI pour les Gtk.FileDialog.

Ce module centralise des petites briques pour éviter la duplication entre onglets
et composants tout en gardant l'UX identique.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

from ui.ui_gtk_helpers import GtkHelper


def open_image_file_dialog(
    *,
    gtk_module: Any,
    button: Any,
    title: str,
    on_selected: Callable[[str], None],
    parent_window: Any | None = None,
) -> None:
    """Ouvre un sélecteur de fichier filtré sur les images.

    Args:
        GtkModule: Module Gtk (typiquement `Gtk`) permettant aux tests de patcher
            `Gtk.FileDialog` via le module appelant.
        button: Bouton source (sert à résoudre la fenêtre parente).
        title: Titre du dialogue.
        on_selected: Callback appelé avec le chemin sélectionné.
        parent_window: Fenêtre parente (optionnel).
    """
    dialog = gtk_module.FileDialog()
    dialog.set_title(title)

    filters = gtk_module.FileFilter()
    filters.set_name("Images")
    filters.add_mime_type("image/jpeg")
    filters.add_mime_type("image/png")
    filters.add_mime_type("image/tga")
    dialog.set_default_filter(filters)

    parent = GtkHelper.resolve_parent_window(button, fallback=parent_window)

    def _on_selected(dlg: Any, result: Any) -> None:
        try:
            file = dlg.open_finish(result)
            if file is None:
                return
            path = file.get_path()
            if path:
                on_selected(path)
        except (OSError, RuntimeError) as exc:
            logger.warning(f"[open_image_file_dialog] Sélection d'image annulée/échouée: {exc}")

    dialog.open(parent, None, _on_selected)
