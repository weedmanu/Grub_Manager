"""Renderer pour le preview GRUB - responsabilité unique de rendu UI."""

from __future__ import annotations

from gi.repository import Gtk

from core.services.core_services_grub import MenuEntry


class GrubPreviewRenderer:
    """Rend le preview GRUB dans un container GTK."""

    @staticmethod
    def default_entry_index(menu_entries: list[MenuEntry], default: str) -> int:
        """Trouve l'index de l'entrée par défaut.

        Args:
            menu_entries: Liste des entrées
            default: ID ou index de l'entrée par défaut

        Returns:
            Index de l'entrée (0 si non trouvé)
        """
        try:
            idx = int(default)
            if 0 <= idx < len(menu_entries):
                return idx
        except (ValueError, TypeError):
            pass

        # Essayer de matcher par ID
        for i, entry in enumerate(menu_entries):
            if entry.id == default:
                return i

        # Essayer de matcher par titre
        for i, entry in enumerate(menu_entries):
            if entry.title in (default, f'"{default}"'):
                return i

        return 0

    @staticmethod
    def create_menu_entry_row(*, entry: MenuEntry, is_selected: bool) -> Gtk.Box:
        """Crée une ligne d'entrée de menu.

        Args:
            entry: Entrée de menu
            is_selected: Si True, cette entrée est sélectionnée

        Returns:
            Widget Gtk.Box représentant l'entrée
        """
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        entry_box.add_css_class("grub-entry")

        if is_selected:
            entry_box.add_css_class("grub-entry-selected")
            entry_box.append(Gtk.Label(label="*"))
        else:
            entry_box.append(Gtk.Label(label=" "))

        label = Gtk.Label(label=entry.title)
        label.set_halign(Gtk.Align.START)
        entry_box.append(label)

        return entry_box

    @staticmethod
    def build_help_text(*, timeout: int) -> str:
        """Construit le texte d'aide affiché en bas du preview.

        Args:
            timeout: Timeout en secondes

        Returns:
            Texte d'aide formaté
        """
        help_text = (
            "Utilisez les touches ↑ et ↓ pour sélectionner l'entrée en surbrillance.\n"
            "Appuyez sur Entrée pour démarrer l'OS sélectionné, 'e' pour éditer les\n"
            "commandes avant le démarrage ou 'c' pour une ligne de commande."
        )
        if timeout >= 0:
            help_text += f"\n\nL'entrée sélectionnée sera démarrée automatiquement dans {timeout}s."
        return help_text

    @classmethod
    def render_preview(
        cls,
        *,
        container: Gtk.Box,
        timeout: int,
        default_entry: str,
        menu_entries: list[MenuEntry],
        is_text_mode: bool,
    ) -> None:
        """Rend le preview GRUB complet dans un container.

        Args:
            container: Container GTK où rendre le preview
            timeout: Timeout en secondes
            default_entry: ID/index de l'entrée par défaut
            menu_entries: Liste des entrées de menu
            is_text_mode: Si True, mode console texte
        """
        # Titre GNU GRUB
        title_label = Gtk.Label(label="GNU GRUB version 2.12")
        title_label.add_css_class("grub-title")
        if is_text_mode:
            title_label.set_halign(Gtk.Align.CENTER)
        container.append(title_label)

        # Séparateur en mode texte
        if is_text_mode:
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            separator.add_css_class("grub-title-separator")
            container.append(separator)

        # Container des entrées
        if is_text_mode:
            entries_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            entries_container.set_valign(Gtk.Align.START)
            entries_container.set_halign(Gtk.Align.START)
            entries_container.add_css_class("grub-entries-list")
            container.append(entries_container)
            target_box = entries_container
        else:
            target_box = container

        # Rendu des entrées
        default_index = cls.default_entry_index(menu_entries, default_entry)
        for i, entry in enumerate(menu_entries):
            entry_row = cls.create_menu_entry_row(entry=entry, is_selected=i == default_index)
            target_box.append(entry_row)

        # Footer en mode graphique
        if not is_text_mode:
            help_label = Gtk.Label(label=cls.build_help_text(timeout=timeout))
            help_label.set_justify(Gtk.Justification.CENTER)
            help_label.add_css_class("grub-info")
            container.append(help_label)
