"""Contrôleur pour la gestion des permissions (Single Responsibility)."""

from __future__ import annotations

import os

from loguru import logger

from ui.ui_infobar_controller import WARNING


class PermissionController:
    """Gère UNIQUEMENT les vérifications de permissions.

    Responsabilités:
    - Vérifier les permissions root
    - Avertir l'utilisateur si nécessaire
    - Déterminer les fonctionnalités disponibles
    """

    def __init__(self) -> None:
        """Initialise le contrôleur."""
        self._is_root: bool | None = None

    def is_root(self) -> bool:
        """Vérifie si l'application s'exécute avec les droits root.

        Returns:
            True si uid == 0 (root), False sinon
        """
        if self._is_root is None:
            self._is_root = os.geteuid() == 0
        return self._is_root

    def check_and_warn(self, show_info_callback) -> bool:
        """Vérifie les permissions et affiche un avertissement si nécessaire.

        Args:
            show_info_callback: Callback pour afficher une notification
                               signature: (message: str, level: str) -> None

        Returns:
            True si root, False sinon
        """
        if not self.is_root():
            logger.warning("[PermissionController] Application exécutée sans droits root")
            show_info_callback(
                "Attention: Application exécutée sans droits root. "
                "Les modifications peuvent être limitées. "
                "Relancez avec 'pkexec' ou 'sudo' pour accès complet.",
                WARNING,
            )
            return False

        logger.debug("[PermissionController] Application exécutée avec droits root")
        return True

    def can_modify_system(self) -> bool:
        """Détermine si l'utilisateur peut modifier la configuration système.

        Returns:
            True si modifications autorisées, False sinon
        """
        return self.is_root()
