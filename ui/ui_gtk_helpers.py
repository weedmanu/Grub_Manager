"""Helpers génériques pour la manipulation de widgets GTK4."""

from __future__ import annotations

from gi.repository import Gtk
from loguru import logger


class GtkHelper:
    """Utilitaires statiques pour manipuler les modèles et widgets GTK."""

    @staticmethod
    def resolve_parent_window(*widgets: Gtk.Widget | None, fallback: Gtk.Window | None = None) -> Gtk.Window | None:
        """Résout une fenêtre parente à partir d'un ou plusieurs widgets.

        En GTK4, `get_root()` renvoie généralement une `Gtk.Window` (ou un root compatible).

        Args:
            widgets: Widgets candidats (ex: bouton cliqué).
            fallback: Fenêtre de repli si aucune n'est trouvée.

        Returns:
            Une fenêtre GTK si trouvée, sinon `fallback`.
        """

        for widget in widgets:
            if widget is None:
                continue
            try:
                root = widget.get_root()
            except (AttributeError, TypeError):
                continue

            if root is None:
                continue
            # Gtk.Window est un Gtk.Root en pratique; certains mocks exposent seulement present().
            if isinstance(root, Gtk.Window) or hasattr(root, "present"):
                return root

        return fallback

    @staticmethod
    def stringlist_find(model, wanted: str) -> int | None:
        """Trouve l'index d'une chaîne dans un Gtk.StringList."""
        if model is None:
            return None
        for i in range(model.get_n_items()):
            if str(model.get_string(i)) == wanted:
                return i
        return None

    @staticmethod
    def stringlist_insert(model, index: int, value: str) -> None:
        """Insère une valeur dans un Gtk.StringList de manière sécurisée."""
        try:
            logger.debug(f"[stringlist_insert] splice at index {index} with value '{value}'")
            model.splice(index, 0, [value])
            logger.debug("[stringlist_insert] splice succeeded")
        except (TypeError, AttributeError) as e:
            logger.debug(f"[stringlist_insert] splice failed: {e}, using append with value '{value}'")
            model.append(value)
            logger.debug("[stringlist_insert] append succeeded")

    @staticmethod
    def dropdown_get_value(dropdown: Gtk.DropDown, *, auto_prefix: str = "auto") -> str:
        """Récupère la valeur sélectionnée d'un DropDown."""
        idx = dropdown.get_selected()
        model = dropdown.get_model()
        if idx is None or model is None:
            logger.debug(f"[dropdown_get_value] idx={idx}, model={model is not None}, returning ''")
            return ""
        try:
            val = model.get_string(int(idx))
            if val is None:
                return ""
            label = str(val)
            logger.debug(f"[dropdown_get_value] idx={idx}, label='{label}'")
        except (TypeError, AttributeError) as e:
            logger.debug(f"[dropdown_get_value] exception getting string: {e}, returning ''")
            return ""
        if label.startswith(auto_prefix):
            logger.debug(f"[dropdown_get_value] label starts with '{auto_prefix}', returning ''")
            return ""
        return label

    @staticmethod
    def dropdown_set_value(dropdown: Gtk.DropDown, value: str, *, auto_prefix: str = "auto") -> None:
        """Définit la sélection d'un DropDown, en ajoutant la valeur si nécessaire."""
        model = dropdown.get_model()
        if model is None:
            logger.debug(f"[dropdown_set_value] model is None, cannot set value '{value}'")
            return

        wanted = (value or "").strip()
        logger.debug(f"[dropdown_set_value] wanted='{wanted}', model has {model.get_n_items()} items")

        if not wanted:
            logger.debug(f"[dropdown_set_value] wanted is empty, looking for '{auto_prefix}' prefix")
            for i in range(model.get_n_items()):
                item = str(model.get_string(i))
                if item.startswith(auto_prefix):
                    logger.debug(f"[dropdown_set_value] found auto item at index {i}: '{item}'")
                    dropdown.set_selected(i)
                    return
            logger.debug("[dropdown_set_value] no auto item found, selecting index 0")
            dropdown.set_selected(0)
            return

        for i in range(model.get_n_items()):
            item = str(model.get_string(i))
            if item == wanted:
                logger.debug(f"[dropdown_set_value] found exact match at index {i}: '{item}'")
                dropdown.set_selected(i)
                return

        logger.debug(f"[dropdown_set_value] no exact match found, adding '{wanted}' to model")
        has_auto = model.get_n_items() >= 1 and str(model.get_string(0)).startswith(auto_prefix)
        insert_at = 1 if has_auto else model.get_n_items()
        GtkHelper.stringlist_insert(model, insert_at, wanted)
        idx = GtkHelper.stringlist_find(model, wanted)
        if idx is not None:
            dropdown.set_selected(idx)
            return

        for i in range(model.get_n_items()):
            if str(model.get_string(i)).startswith(auto_prefix):
                dropdown.set_selected(i)
                return
        dropdown.set_selected(0)

    @staticmethod
    def stringlist_replace_all(model, items: list[str]) -> None:
        """Remplace tout le contenu d'un Gtk.StringList."""
        if model is None:
            return
        try:
            model.splice(0, model.get_n_items(), items)
            logger.debug(f"[stringlist_replace_all] splice succeeded, items count={model.get_n_items()}")
        except (TypeError, AttributeError) as e:
            logger.debug(f"[stringlist_replace_all] splice failed: {e}, using remove/append loop")
            while model.get_n_items() > 0:
                model.remove(0)
            for it in items:
                model.append(it)
            logger.debug(f"[stringlist_replace_all] loop completed, items count={model.get_n_items()}")
