"""Politique de gestion des boutons d'onglets (Recharger/Appliquer)."""

from __future__ import annotations

from loguru import logger

from ui.models.ui_models_state import AppState


class TabPolicy:
    """Définit la politique d'activation des boutons selon l'onglet actif."""

    @staticmethod
    def is_readonly_tab(tab_label: str) -> bool:
        """Indique si l'onglet est en lecture seule (pas d'édition)."""
        return tab_label in ("Sauvegardes", "Maintenance")

    @staticmethod
    def get_button_states(tab_label: str, *, busy: bool) -> tuple[bool, bool]:
        """Détermine l'état (sensible ou non) des boutons Recharger et Appliquer.

        Args:
            tab_label: Libellé de l'onglet actif.
            busy: True si un workflow d'application est en cours.

        Returns:
            Un tuple (reload_sensitive, save_sensitive).
        """
        # - Pendant l'application: on évite les actions concurrentes.
        if busy:
            return False, False

        # - Sauvegardes/Maintenance: onglets dédiés, on désactive la barre globale.
        if TabPolicy.is_readonly_tab(tab_label):
            logger.debug(f"[TabPolicy] Boutons désactivés pour l'onglet '{tab_label}'")
            return False, False

        # - Tous les autres onglets: boutons toujours disponibles.
        return True, True


def apply_tab_policy(window, tab_label: str) -> None:
    """Applique la politique des boutons à la fenêtre principale.

    Args:
        window: Instance de GrubConfigManager.
        tab_label: Libellé de l'onglet actif.
    """
    busy = getattr(window.state_manager, "state", None) == AppState.APPLYING
    reload_sens, save_sens = TabPolicy.get_button_states(tab_label, busy=busy)

    window.reload_btn.set_sensitive(reload_sens)
    preview_btn = getattr(window, "preview_btn", None)
    if preview_btn is not None:
        preview_btn.set_sensitive(reload_sens)
    window.save_btn.set_sensitive(save_sens)
    logger.info(f"[apply_tab_policy] Tab: '{tab_label}', Reload: {reload_sens}, Save: {save_sens}")
