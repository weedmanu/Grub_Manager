"""Contrôleur pour la gestion du choix par défaut (Single Responsibility)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk


class DefaultChoiceController:
    """Gère UNIQUEMENT le choix par défaut GRUB et ses interactions UI.
    
    Responsabilités:
    - Lire/écrire le choix par défaut
    - Gérer la liste des choix disponibles
    - Valider les sélections
    """

    def __init__(self, parent_window: Gtk.ApplicationWindow) -> None:
        """Initialise le contrôleur.
        
        Args:
            parent_window: Fenêtre parente (GrubConfigManager)
        """
        self.parent = parent_window

    def get_choice(self) -> str:
        """Obtient le choix par défaut depuis le dropdown.
        
        Returns:
            L'ID du choix par défaut (ex: "saved", "0", "1>2")
        """
        if not hasattr(self.parent, "default_dropdown") or self.parent.default_dropdown is None:
            return "0"
        try:
            selected = self.parent.default_dropdown.get_selected()
            if selected < 0:
                return "0"
            
            model = self.parent.default_dropdown.get_model()
            if model is None:
                return "0"
            
            item = model.get_item(selected)
            return str(item) if item else "0"
        except (ValueError, AttributeError):
            return "0"

    def set_choice(self, value: str) -> None:
        """Définit le choix par défaut dans le dropdown.
        
        Args:
            value: Nouvel ID du choix (ex: "saved", "0", "1>2")
        """
        if not hasattr(self.parent, "default_dropdown") or self.parent.default_dropdown is None:
            return
        
        wanted = (value or "").strip() or "0"
        if wanted == "saved":
            self.parent.default_dropdown.set_selected(0)
            return

        try:
            model = self.parent.default_dropdown.get_model()
            if model is None:
                return
            
            for i in range(model.get_n_items()):
                item = model.get_item(i)
                if str(item) == wanted:
                    self.parent.default_dropdown.set_selected(i)
                    return
            
            # Si pas trouvé, ajouter l'option
            model.append(wanted)
            self.parent.default_dropdown.set_selected(model.get_n_items() - 1)
        except (ValueError, AttributeError):
            pass

    def refresh_choices(self, choices: list[str], current: str) -> None:
        """Rafraîchit la liste des choix disponibles.
        
        Args:
            choices: Liste des IDs de choix disponibles
            current: ID du choix actuel
        """
        # Implémentation optionnelle pour reconstruire la liste
        if current:
            self.set_choice(current)
