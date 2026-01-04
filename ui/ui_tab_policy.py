"""Politique de gestion des boutons d'onglets (Recharger/Appliquer)."""

from __future__ import annotations

from loguru import logger


class TabPolicy:
    """Définit la politique d'activation des boutons selon l'onglet actif."""

    @staticmethod
    def get_button_states(tab_label: str, is_dirty: bool) -> tuple[bool, bool]:
        """Détermine l'état (sensible ou non) des boutons Recharger et Appliquer.

        Args:
            tab_label: Libellé de l'onglet actif.
            is_dirty: True si des changements non enregistrés existent.

        Returns:
            Un tuple (reload_sensitive, save_sensitive).
        """
        # - Sauvegardes/Maintenance: pas d'édition => boutons désactivés.
        if tab_label in ("Sauvegardes", "Maintenance"):
            logger.debug(f"[TabPolicy] Boutons désactivés pour l'onglet '{tab_label}'")
            return False, False

        # - Général/Menu/Affichage: Recharger + Appliquer toujours disponibles.
        if tab_label in ("Général", "General", "Menu", "Affichage"):
            return True, True

        # - Par défaut: Recharger reste disponible; Appliquer dépend des changements.
        return True, is_dirty


def apply_tab_policy(window, tab_label: str) -> None:
    """Applique la politique des boutons à la fenêtre principale.

    Args:
        window: Instance de GrubConfigManager.
        tab_label: Libellé de l'onglet actif.
    """
    is_dirty = bool(window.state_manager.is_dirty())
    reload_sens, save_sens = TabPolicy.get_button_states(tab_label, is_dirty)

    window.reload_btn.set_sensitive(reload_sens)
    window.save_btn.set_sensitive(save_sens)
    logger.info(f"[apply_tab_policy] Tab: '{tab_label}', Reload: {reload_sens}, Save: {save_sens}")
