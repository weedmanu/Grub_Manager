"""Contrôleur pour la gestion du timeout GRUB (Single Responsibility)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk


class TimeoutController:
    """Gère UNIQUEMENT le timeout GRUB et ses interactions UI.
    
    Responsabilités:
    - Lire/écrire la valeur du timeout
    - Synchroniser les choix disponibles
    - Valider les entrées
    """

    def __init__(self, parent_window: Gtk.ApplicationWindow) -> None:
        """Initialise le contrôleur.
        
        Args:
            parent_window: Fenêtre parente (GrubConfigManager)
        """
        self.parent = parent_window

    def get_value(self) -> int:
        """Obtient la valeur du timeout depuis le dropdown."""
        if not hasattr(self.parent, "timeout_dropdown") or self.parent.timeout_dropdown is None:
            return 5
        try:
            value = self.parent.timeout_dropdown.get_selected()
            return int(value) if isinstance(value, str) else value
        except (ValueError, AttributeError):
            return 5

    def set_value(self, value: int) -> None:
        """Définit la valeur du timeout dans le dropdown.
        
        Args:
            value: Nouvelle valeur du timeout (en secondes)
        """
        if not hasattr(self.parent, "timeout_dropdown") or self.parent.timeout_dropdown is None:
            return
        try:
            timeout_model = self.parent.timeout_dropdown.get_model()
            if timeout_model is None:
                return
            
            timeout_dropdown = self.parent.timeout_dropdown
            for i in range(timeout_model.get_n_items()):
                item = timeout_model.get_item(i)
                if int(item) == value:
                    timeout_dropdown.set_selected(i)
                    return
            
            # Si la valeur n'existe pas, sélectionner la première
            timeout_dropdown.set_selected(0)
        except (ValueError, AttributeError):
            pass

    def sync_choices(self, current: int) -> None:
        """Synchronise les choix disponibles du timeout.
        
        Args:
            current: Valeur actuelle du timeout
        """
        # Implémentation optionnelle pour ajouter de nouvelles valeurs
        pass
