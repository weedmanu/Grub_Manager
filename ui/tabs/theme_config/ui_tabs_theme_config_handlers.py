"""Handlers (callbacks) pour l'onglet de configuration de thème.

Objectif: réduire la taille de l'implémentation en déplaçant les callbacks
dans un sous-module. Les tests importent/patchent désormais ce module.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.config.core_config_paths import get_grub_themes_dir
from core.models.core_models_theme import GrubTheme
from ui.builders.ui_builders_widgets import create_error_dialog, create_success_dialog
from ui.dialogs.ui_dialogs_grub_preview import GrubPreviewDialog
from ui.dialogs.ui_dialogs_interactive_theme_generator_window import InteractiveThemeGeneratorWindow
from ui.helpers.ui_helpers_gtk import GtkHelper


def _set_sensitive(widget: Any, is_sensitive: bool) -> None:
    if widget is not None:
        widget.set_sensitive(is_sensitive)


def on_activate_theme(_button: Any, tab: Any) -> None:
    """Active le thème sélectionné dans le modèle."""
    if not getattr(getattr(tab, "data", None), "current_theme", None):
        return

    theme_name = tab.data.current_theme.name
    theme_path = tab.data.theme_paths.get(theme_name)
    theme_txt = ""
    if theme_path:
        theme_txt = str(theme_path / "theme.txt")

    current_model = tab.state_manager.get_model()
    new_model = replace(current_model, grub_theme=theme_txt)

    tab.state_manager.update_model(new_model)
    tab.mark_dirty()

    tab.refresh()


def on_deactivate_theme(_button: Any, tab: Any) -> None:
    """Désactive le thème (revient à 'Aucun')."""
    current_model = tab.state_manager.get_model()
    new_model = replace(current_model, grub_theme="")

    tab.state_manager.update_model(new_model)
    tab.mark_dirty()

    tab.refresh()


def on_theme_selected(_list_box: Any, row: Any, tab: Any) -> None:
    """Callback: sélection d'un thème."""
    if row is None:
        tab.data.current_theme = None
        actions = tab.widgets.actions
        _set_sensitive(actions.preview_btn, False)
        _set_sensitive(actions.edit_btn, False)
        _set_sensitive(actions.delete_btn, False)
        return

    index = row.get_index()
    themes_list = list(tab.data.available_themes.values())

    if not 0 <= index < len(themes_list):
        return

    tab.data.current_theme = themes_list[index]

    actions = tab.widgets.actions
    _set_sensitive(actions.preview_btn, tab.data.current_theme.name != "Aucun (GRUB par défaut)")

    theme_path = tab.data.theme_paths.get(tab.data.current_theme.name)
    is_custom = bool(theme_path) and tab.services.theme_service.is_theme_custom(theme_path)

    _set_sensitive(actions.edit_btn, is_custom)
    _set_sensitive(actions.delete_btn, is_custom)

    model = tab.state_manager.get_model()
    is_none = tab.data.current_theme.name == "Aucun (GRUB par défaut)"
    theme_txt_path = (theme_path / "theme.txt") if theme_path else None
    is_active = (str(theme_txt_path) == model.grub_theme) if theme_txt_path else (is_none and not model.grub_theme)

    _set_sensitive(actions.activate_theme_btn, not is_active)
    _set_sensitive(actions.deactivate_theme_btn, is_active and not is_none)


def on_theme_switch_toggled(switch: Any, _param: Any, tab: Any) -> None:
    """Callback historique (switch supprimé).

    DEV: Conservé pour compatibilité des imports/tests anciens.
    La nouvelle UX sépare en 2 onglets (Thèmes et Apparence) et n'utilise plus ce switch.
    """
    if tab.state_manager.is_loading() or getattr(tab, "_updating_switch", False):
        return

    # Best-effort: si un ancien widget de switch existe encore dans un test isolé,
    # on met à jour le modèle, sans gérer de visibilité de conteneurs.
    try:
        is_active = bool(switch.get_active())
    except (AttributeError, TypeError):  # pragma: no cover
        return

    current_model = tab.state_manager.get_model()
    if getattr(current_model, "theme_management_enabled", None) != is_active:
        new_model = replace(current_model, theme_management_enabled=is_active)
        tab.state_manager.update_model(new_model)
        tab.mark_dirty()

    tab.load_themes()


def on_open_editor(
    tab: Any,
    button: Gtk.Button | None = None,
) -> None:
    """Ouvre le générateur interactif de thème."""
    try:
        if not tab.parent_window:
            tab.parent_window = GtkHelper.resolve_parent_window(button, fallback=tab.parent_window)

        if not tab.parent_window:
            logger.error("[on_open_editor] Fenêtre parente introuvable")
            create_error_dialog("Impossible d'ouvrir l'éditeur")
            return

        def _on_theme_created(name: str, package: dict[str, Any]) -> None:
            try:
                themes_dir = get_grub_themes_dir()
                theme_path = themes_dir / name

                theme_path.mkdir(parents=True, exist_ok=True)
                (theme_path / "theme.txt").write_text(package["theme.txt"], encoding="utf-8")

                assets = package.get("assets", {})
                for target_name, source_path in assets.items():
                    try:
                        src = Path(source_path)
                        if not src.exists():
                            logger.warning(f"Asset non trouvé: {source_path}")
                            continue

                        dst = theme_path / target_name
                        if src.is_dir():
                            if dst.exists():
                                shutil.rmtree(dst)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy(src, dst)
                    except (OSError, shutil.Error, ValueError) as exc:
                        logger.error(f"Erreur lors de la copie de l'asset {target_name}: {exc}")

                tab.scan_system_themes()

            except (OSError, PermissionError) as exc:
                logger.error(f"Erreur lors de la création du thème: {exc}")
                create_error_dialog(f"Erreur lors de la création du thème:\n{exc}")

        win = InteractiveThemeGeneratorWindow(parent_window=tab.parent_window, on_theme_created=_on_theme_created)

        tab.set_interactive_theme_generator_window(win)

        def _on_close(_widget: Any) -> bool:
            tab.clear_interactive_theme_generator_window()
            return False

        win.connect("close-request", _on_close)
        win.present()

    except (OSError, RuntimeError) as exc:
        logger.error(f"[on_open_editor] Erreur: {exc}")
        create_error_dialog(f"Erreur lors de l'ouverture de l'éditeur:\n{exc}")


def on_preview_theme(
    tab: Any,
) -> None:
    """Ouvre le dialog de prévisualisation du thème."""
    model = tab.state_manager.get_model()
    theme = tab.data.current_theme

    # Sans sélection explicite: on affiche un aperçu basé sur la configuration simple.
    if theme is None:
        theme = GrubTheme(name="Configuration Simple")

    try:
        theme_txt_path = None

        # Si un thème est sélectionné et correspond à un répertoire, on utilise son theme.txt.
        if theme is not None and getattr(theme, "name", "") and theme.name != "Configuration Simple":
            theme_path = tab.data.theme_paths.get(theme.name)
            if theme_path:
                theme_txt_path = theme_path / "theme.txt"

        dialog = GrubPreviewDialog(theme, model=model, theme_txt_path=theme_txt_path)
        dialog.show()
    except (OSError, RuntimeError) as exc:
        logger.error(f"[on_preview_theme] Erreur: {exc}")
        create_error_dialog(f"Erreur lors de l'aperçu:\n{exc}")


def on_edit_theme(
    _button: Any | None,
    theme_name: str,
    tab: Any,
) -> None:
    """Ouvre l'éditeur pour modifier un thème custom."""
    try:
        tab.parent_window = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        if theme_name not in tab.data.available_themes:
            create_error_dialog(f"Thème '{theme_name}' introuvable")
            return

        theme_path = tab.data.theme_paths.get(theme_name)
        if not theme_path or not tab.services.theme_service.is_theme_custom(theme_path):
            create_error_dialog("Ce thème système ne peut pas être modifié")
            return

        if not tab.parent_window:
            logger.error("[on_edit_theme] Fenêtre parente introuvable")
            create_error_dialog("Impossible d'ouvrir l'éditeur")
            return

        win = InteractiveThemeGeneratorWindow(
            parent_window=tab.parent_window,
            on_theme_created=lambda _n, _p: tab.scan_system_themes(),
        )
        tab.set_interactive_theme_generator_window(win)
        win.present()

    except (OSError, RuntimeError) as exc:
        logger.error(f"[on_edit_theme] Erreur: {exc}")
        create_error_dialog(f"Erreur lors de l'ouverture de l'éditeur:\n{exc}")


def on_delete_theme(
    _button: Any | None,
    theme_name: str,
    tab: Any,
) -> None:
    """Supprime un thème custom après confirmation."""
    try:
        tab.parent_window = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        if theme_name not in tab.data.available_themes:
            create_error_dialog(f"Thème '{theme_name}' introuvable")
            return

        theme_path = tab.data.theme_paths.get(theme_name)
        if not theme_path or not tab.services.theme_service.is_theme_custom(theme_path):
            create_error_dialog("Les thèmes système ne peuvent pas être supprimés")
            return

        dialog = Gtk.AlertDialog()
        dialog.set_message(f"Supprimer le thème '{theme_name}' ?")
        dialog.set_detail(
            f"Cette action supprimera définitivement le répertoire:\n{theme_path}\n\n" "Cette action est irréversible."
        )
        dialog.set_buttons(["Annuler", "Supprimer"])
        dialog.set_default_button(0)
        dialog.set_cancel_button(0)

        parent = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        dialog.choose(
            parent=parent,
            cancellable=None,
            callback=on_delete_confirmed,
            user_data=(theme_name, theme_path, tab),
        )

    except (OSError, RuntimeError) as exc:
        logger.error(f"[on_delete_theme] Erreur: {exc}")
        create_error_dialog(f"Erreur lors de la suppression:\n{exc}")


def on_delete_confirmed(
    dialog: Any,
    result: Any,
    user_data: tuple,
) -> None:
    """Callback après confirmation de suppression."""
    try:
        choice = dialog.choose_finish(result)

        if choice != 1:
            return

        theme_name, theme_path, tab = user_data
        parent = getattr(tab, "parent_window", None)

        if tab.services.theme_service.delete_theme(theme_path):
            logger.info(f"[on_delete_confirmed] Thème supprimé: {theme_name}")
            create_success_dialog(f"Thème '{theme_name}' supprimé avec succès", parent=parent)
        else:
            logger.error(f"[on_delete_confirmed] Échec suppression: {theme_name}")
            create_error_dialog(f"Impossible de supprimer le thème '{theme_name}'", parent=parent)

        tab.scan_system_themes()

    except (OSError, RuntimeError) as exc:
        logger.error(f"[on_delete_confirmed] Erreur: {exc}")
        parent = None
        if user_data:
            try:
                parent = getattr(user_data[2], "parent_window", None)
            except (TypeError, IndexError):
                parent = None
        create_error_dialog(f"Erreur lors de la suppression:\n{exc}", parent=parent)
