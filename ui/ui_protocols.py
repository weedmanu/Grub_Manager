"""Protocoles (interfaces) pour l'UI GTK - Interface Segregation Principle.

Les Protocols définissent des contrats minimaux entre composants.
Les clients qui ne besoin que d'une interface spécifique dépendent UNIQUEMENT de ce Protocol.
"""

from __future__ import annotations

from typing import Protocol

from core.models.core_grub_ui_model import GrubUiModel
from core.system.core_grub_system_commands import GrubDefaultChoice


class TimeoutWidget(Protocol):
    """Interface minimale pour les composants qui gèrent le timeout GRUB."""

    def get_timeout_value(self) -> int:
        """Obtient la valeur du timeout depuis l'UI.

        Returns:
            Valeur du timeout en secondes
        """

    def set_timeout_value(self, value: int) -> None:
        """Définit la valeur du timeout dans l'UI.

        Args:
            value: Nouvelle valeur du timeout
        """

    def sync_timeout_choices(self, current: int) -> None:
        """Synchronise les choix disponibles du timeout.

        Args:
            current: Valeur actuelle du timeout
        """


class DefaultChoiceWidget(Protocol):
    """Interface minimale pour les composants qui gèrent le choix par défaut."""

    def get_default_choice(self) -> str:
        """Obtient le choix par défaut depuis l'UI.

        Returns:
            ID du choix par défaut
        """

    def set_default_choice(self, value: str) -> None:
        """Définit le choix par défaut dans l'UI.

        Args:
            value: Nouvel ID du choix
        """

    def refresh_default_choices(self, _choices: list[GrubDefaultChoice], _current: str) -> None:
        """Rafraîchit la liste des choix disponibles.

        Args:
            _choices: Liste des choix disponibles
            _current: ID du choix actuel
        """


class ConfigModelMapper(Protocol):
    """Interface minimale pour la synchronisation modèle ↔ widgets."""

    def apply_model_to_ui(self, model: GrubUiModel, entries: list[GrubDefaultChoice]) -> None:
        """Synchronise le modèle de données vers les widgets UI.

        Args:
            model: Modèle de configuration GRUB
            entries: Entrées GRUB disponibles
        """

    def read_model_from_ui(self) -> GrubUiModel:
        """Extrait les valeurs des widgets UI vers un modèle.

        Returns:
            Modèle contenant les valeurs actuelles de l'UI
        """


class PermissionChecker(Protocol):
    """Interface minimale pour les vérifications de permissions."""

    def is_root(self) -> bool:
        """Vérifie si l'application s'exécute avec les droits root.

        Returns:
            True si exécuté en tant que root
        """

    def can_modify_system(self) -> bool:
        """Détermine si l'utilisateur peut modifier la configuration système.

        Returns:
            True si modifications autorisées
        """


class InfoDisplay(Protocol):
    """Interface minimale pour afficher des messages informatifs."""

    def show_info(self, _message: str, _level: str = "info") -> None:
        """Affiche un message informatif à l'utilisateur.

        Args:
            _message: Texte du message
            _level: Niveau ("info", "warning", "error")
        """

    def hide_info_callback(self) -> bool:
        """Masque le message informatif affiché.

        Returns:
            True si message était affiché et a été masqué
        """
