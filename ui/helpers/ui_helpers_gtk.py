"""Helpers génériques pour la manipulation de widgets GTK4."""

from __future__ import annotations

from gi.repository import GLib, Gtk
from loguru import logger


class GtkHelper:
    """Utilitaires statiques pour manipuler les modèles et widgets GTK."""

    @staticmethod
    def get_dialog_response(dialog: Gtk.AlertDialog, result) -> int | None:
        """Récupère la réponse d'un dialogue asynchrone de manière sécurisée.

        Encapsule le pattern try/except GLib.Error autour de choose_finish.
        """
        try:
            return dialog.choose_finish(result)
        except GLib.Error:
            return None

    @staticmethod
    def present_dialog(dialog: Gtk.Widget) -> None:
        """Affiche un dialogue en gérant la compatibilité (present() vs show())."""
        if hasattr(dialog, "present"):
            dialog.present()
        elif hasattr(dialog, "show"):
            dialog.show()

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
    def dropdown_selected_text(dropdown: Gtk.DropDown | None) -> str:
        """Retourne le texte de l'item sélectionné (supporte None).

        Utilise `get_selected_item()` car certains tests/mocks ne fournissent pas un
        modèle compatible `get_model().get_string()`.
        """
        if dropdown is None:
            return ""
        item = dropdown.get_selected_item()
        if item is None:
            return ""
        try:
            return str(item.get_string())
        except (AttributeError, TypeError):  # pragma: no cover
            return str(item)

    @staticmethod
    def info_box_text_label(box: Gtk.Box) -> Gtk.Label | None:
        """Retourne le label de texte d'une `create_info_box()`.

        La factory `create_info_box()` retourne un Gtk.Box contenant au moins un
        Gtk.Label pour le texte. On récupère le dernier label rencontré afin de
        pouvoir mettre à jour le texte dynamiquement sans reconstruire le widget.
        """
        last_label: Gtk.Label | None = None
        child = box.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Label):
                last_label = child
            child = child.get_next_sibling()
        return last_label

    @staticmethod
    def format_size_bytes(size: int) -> str:
        """Formate une taille en octets pour l'affichage UI."""
        if size < 1024:
            return f"{size} o"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} Ko"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} Mo"
        return f"{size / (1024 * 1024 * 1024):.1f} Go"

    @staticmethod
    def build_option_frame(*, frame_css_class: str, label_markup: str, widget: Gtk.Widget) -> Gtk.Frame:
        """Construit une ligne d'option (label + widget) encapsulée dans un Gtk.Frame.

        Ce helper centralise le layout commun utilisé dans plusieurs onglets.
        """
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_box.set_hexpand(True)
        row_box.set_vexpand(False)
        row_box.set_valign(Gtk.Align.START)
        row_box.set_margin_top(10)
        row_box.set_margin_bottom(10)
        row_box.set_margin_start(12)
        row_box.set_margin_end(12)

        label = Gtk.Label(xalign=0)
        label.set_markup(label_markup)
        label.set_hexpand(True)
        label.set_valign(Gtk.Align.START)
        row_box.append(label)

        widget.set_valign(Gtk.Align.START)
        row_box.append(widget)

        frame = Gtk.Frame()
        frame.add_css_class(frame_css_class)
        frame.set_hexpand(True)
        frame.set_vexpand(False)
        frame.set_valign(Gtk.Align.START)
        frame.set_child(row_box)
        return frame

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
