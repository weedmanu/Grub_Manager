"""Protocols (interfaces) des managers core.

Objectif: découpler la couche UI des implémentations concrètes via DIP.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.managers.core_managers_apply import ApplyResult


@runtime_checkable
class IGrubApplyManager(Protocol):
    """Interface pour le gestionnaire d'application de configuration GRUB.

    Permet l'inversion de dépendance dans les contrôleurs UI.
    """

    # pylint: disable=too-few-public-methods

    def apply_configuration(
        self,
        new_config: dict[str, str],
        apply_changes: bool = True,
        theme_management_enabled: bool = True,
        pending_script_changes: dict[str, bool] | None = None,
    ) -> "ApplyResult":
        """Applique la configuration."""
        raise NotImplementedError
