"""Dialog pour afficher un aperçu réaliste du menu GRUB.

Utilisé par tab_theme_config et tab_theme_editor pour prévisualiser
les thèmes avec la configuration réelle du système.
"""

from __future__ import annotations

from gi.repository import Gtk
from loguru import logger

from core.services.core_grub_service import GrubConfig, GrubService, MenuEntry
from core.theme.core_theme_generator import GrubTheme


class GrubPreviewDialog:
    """Dialog pour prévisualiser un thème GRUB."""

    def __init__(self, theme: GrubTheme, theme_name: str = "") -> None:
        """Initialise le dialog de preview.

        Args:
            theme: Thème à prévisualiser
            theme_name: Nom du thème pour le titre
        """
        self.theme = theme
        self.theme_name = theme_name or theme.name

    def show(self) -> None:
        """Affiche le dialog de preview."""
        # Créer le dialog
        dialog = Gtk.Window()
        dialog.set_title(f"Aperçu GRUB: {self.theme_name}")
        dialog.set_default_size(1000, 700)
        dialog.set_modal(True)

        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(15)
        main_box.set_margin_end(15)
        main_box.set_margin_top(15)
        main_box.set_margin_bottom(15)

        # Titre
        title = Gtk.Label()
        title.set_markup(f"<b>Aperçu du menu GRUB avec {self.theme_name}</b>")
        title.set_xalign(0)
        main_box.append(title)

        # Zone de prévisualisation GRUB
        frame = Gtk.Frame()
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        preview_box.set_margin_start(20)
        preview_box.set_margin_end(20)
        preview_box.set_margin_top(20)
        preview_box.set_margin_bottom(20)

        # Remplir avec le contenu du preview
        self._create_grub_preview(preview_box)

        frame.set_child(preview_box)
        main_box.append(frame)

        # Bouton fermer
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        close_btn = Gtk.Button(label="Fermer")
        close_btn.connect("clicked", lambda b: dialog.close())
        button_box.append(close_btn)
        main_box.append(button_box)

        dialog.set_child(main_box)
        dialog.present()

    def _create_grub_preview(self, container: Gtk.Box) -> None:
        """Crée un aperçu réaliste du menu GRUB.

        Args:
            container: Container où placer le preview
        """
        try:
            # Utiliser le service pour accéder aux données
            config = GrubService.read_current_config()
            menu_entries = GrubService.get_menu_entries()
        except (OSError, RuntimeError) as e:
            logger.warning(f"[GrubPreviewDialog] Erreur lecture config: {e}")
            # Fallback avec valeurs par défaut
            config = GrubConfig()
            menu_entries = [MenuEntry(title="Ubuntu", id="gnulinux")]

        # Titre du système
        title_label = Gtk.Label(label="GNU GRUB version 2.12")
        title_label.add_css_class("title-3")
        container.append(title_label)

        # Espace vide
        space1 = Gtk.Label(label="")
        container.append(space1)

        # Menu entries - afficher les vraies entrées
        default_index = int(config.default_entry.split(">", maxsplit=1)[0].strip()) if config.default_entry else 0

        for i, entry in enumerate(menu_entries):
            is_selected = i == default_index
            if is_selected:
                # Élément sélectionné avec fond
                entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                entry_box.set_margin_start(40)
                entry_box.set_margin_end(40)

                # Icône de sélection
                arrow = Gtk.Label(label="➤")
                arrow.add_css_class("title-2")
                entry_box.append(arrow)

                entry_text = Gtk.Label(label=entry.title)
                entry_text.set_xalign(0)
                entry_box.append(entry_text)

                # Styling pour sélection
                entry_box.add_css_class("card")
                container.append(entry_box)
            else:
                entry_text = Gtk.Label(label=entry.title)
                entry_text.set_xalign(0)
                entry_text.set_margin_start(60)
                entry_text.set_margin_end(40)
                entry_text.add_css_class("dim-label")
                container.append(entry_text)

        # Espace vide
        space2 = Gtk.Label(label="")
        container.append(space2)

        # Informations de timeout
        timeout_label = Gtk.Label()
        timeout_label.set_markup(
            f"<small>Timeout: <b>{config.timeout}s</b> | " f"Sélection: <b>{config.default_entry}</b></small>"
        )
        timeout_label.set_xalign(0)
        container.append(timeout_label)

        # Informations de configuration
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info_box.set_margin_top(20)

        info_label1 = Gtk.Label()
        info_label1.set_markup(f"<small><b>Résolution:</b> {config.grub_gfxmode}</small>")
        info_label1.set_xalign(0)
        info_box.append(info_label1)

        info_label2 = Gtk.Label()
        info_label2.set_markup(f"<small><b>Couleurs:</b> {config.grub_color_normal}</small>")
        info_label2.set_xalign(0)
        info_box.append(info_label2)

        info_label3 = Gtk.Label()
        theme_timeout = self.theme.grub_timeout if hasattr(self.theme, "grub_timeout") else config.timeout
        info_label3.set_markup(f"<small><b>Timeout thème:</b> {theme_timeout}s</small>")
        info_label3.set_xalign(0)
        info_box.append(info_label3)

        container.append(info_box)

        logger.debug("[GrubPreviewDialog] Preview créé")
