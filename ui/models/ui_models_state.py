"""Gestion de l'état de l'application GTK.

Centralise toute la logique d'état (CLEAN/DIRTY/APPLYING) et les flags mutables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from enum import Enum

from loguru import logger

from core.managers.core_managers_entry_visibility import load_hidden_entry_ids
from core.system.core_system_grub_commands import GrubUiModel, GrubUiState

# Garder ce symbole exposé (tests patchent ui.ui_state.ActiveThemeManager)
from core.theme.core_theme_active_manager import ActiveThemeManager as _ActiveThemeManager

ActiveThemeManager = _ActiveThemeManager
del _ActiveThemeManager

__all__ = [
    "ActiveThemeManager",
    "AppState",
    "AppStateManager",
]


@dataclass(slots=True)
class _EntryVisibilityState:
    hidden_entry_ids: set[str]
    dirty: bool = False


class AppState(str, Enum):
    """État interne de la fenêtre (propre/modifié/en cours d'application)."""

    CLEAN = "clean"
    DIRTY = "dirty"
    APPLYING = "applying"


class AppStateManager:
    """Gestionnaire centralisé de l'état de l'application.

    Responsabilités:
    - Gestion état (CLEAN/DIRTY/APPLYING)
    - État de chargement (_loading flag)
    - Entrées masquées (hidden_entry_ids)
    - Synchronisation UI state
    """

    def __init__(self):
        """Initialise le gestionnaire d'état."""
        logger.debug("[AppStateManager.__init__] Initialisation du gestionnaire d'état")

        self.state_data = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})
        self._default_choice_ids: list[str] = ["saved"]
        self._state = AppState.CLEAN
        self._loading = False  # Flag pour ignorer les changements UI lors du chargement initial

        self.pending_script_changes: dict[str, bool] = {}

        self._visibility = _EntryVisibilityState(hidden_entry_ids=load_hidden_entry_ids())

        logger.debug("[AppStateManager.__init__] État initialisé")

    def apply_state(self, state: AppState, save_btn, reload_btn) -> None:
        """Applique un nouvel état et met à jour les boutons.

        Args:
            state: Nouvel état à appliquer
            save_btn: Bouton d'enregistrement GTK
            reload_btn: Bouton de rechargement GTK
        """
        logger.debug(f"[AppStateManager.apply_state] Transition: {self.state} → {state}")
        self.state = state

        can_save = (
            (state == AppState.DIRTY) or self.entries_visibility_dirty or bool(self.pending_script_changes)
        ) and (os.geteuid() == 0)
        busy = state == AppState.APPLYING

        save_btn.set_sensitive(can_save and not busy)
        reload_btn.set_sensitive(not busy)
        logger.debug(f"[AppStateManager.apply_state] Boutons: save={can_save and not busy}, reload={not busy}")

    def mark_dirty(self, save_btn, reload_btn) -> None:
        """Marque l'état comme modifié (DIRTY) si pas en cours d'application.

        Args:
            save_btn: Bouton d'enregistrement GTK
            reload_btn: Bouton de rechargement GTK
        """
        if self.state != AppState.APPLYING:
            logger.debug("[AppStateManager.mark_dirty] État marqué comme modifié")
            self.apply_state(AppState.DIRTY, save_btn, reload_btn)

    def set_loading(self, loading: bool) -> None:
        """Active/désactive le flag de chargement.

        Args:
            loading: True pour activer le mode chargement, False sinon
        """
        self._loading = loading
        logger.debug(f"[AppStateManager.set_loading] Loading flag: {loading}")

    def is_loading(self) -> bool:
        """Vérifie si le chargement est en cours.

        Returns:
            True si le chargement est en cours, False sinon
        """
        return self._loading

    def is_dirty(self) -> bool:
        """Indique si l'application a des changements non appliqués.

        Inclut:
        - modifications de configuration (state == DIRTY)
        - changements de visibilité des entrées GRUB
        - changements d'état des scripts
        """
        return bool(self.modified or self.entries_visibility_dirty or self.pending_script_changes)

    @property
    def state(self) -> AppState:
        """Retourne l'état applicatif courant."""
        return self._state

    @state.setter
    def state(self, value: AppState) -> None:
        """Définit l'état applicatif courant."""
        self._state = value

    @property
    def modified(self) -> bool:
        """Indique si l'application est dans l'état DIRTY."""
        return self._state == AppState.DIRTY

    @property
    def hidden_entry_ids(self) -> set[str]:
        """Retourne l'ensemble des IDs d'entrées masquées."""
        return self._visibility.hidden_entry_ids

    @hidden_entry_ids.setter
    def hidden_entry_ids(self, value: set[str]) -> None:
        """Remplace l'ensemble des IDs d'entrées masquées."""
        self._visibility.hidden_entry_ids = value

    @property
    def entries_visibility_dirty(self) -> bool:
        """Indique si l'état de masquage a été modifié."""
        return self._visibility.dirty

    @entries_visibility_dirty.setter
    def entries_visibility_dirty(self, value: bool) -> None:
        """Définit le flag de modification lié au masquage."""
        self._visibility.dirty = value

    def update_state_data(self, state_data: GrubUiState) -> None:
        """Met à jour les données d'état de l'application.

        Args:
            state_data: Nouvelles données d'état
        """
        logger.debug("[AppStateManager.update_state_data] Mise à jour des données d'état")
        self.state_data = state_data

    def update_default_choice_ids(self, ids: list[str]) -> None:
        """Met à jour la liste des IDs de choix par défaut.

        Args:
            ids: Liste des IDs de choix disponibles
        """
        logger.debug(f"[AppStateManager.update_default_choice_ids] {len(ids)} choix disponibles")
        self._default_choice_ids = ids

    def get_default_choice_ids(self) -> list[str]:
        """Retourne la liste des IDs de choix par défaut.

        Returns:
            Liste des IDs de choix disponibles
        """
        return self._default_choice_ids

    def get_model(self) -> GrubUiModel:
        """Retourne le modèle de configuration actuel."""
        return self.state_data.model

    def update_model(self, model: GrubUiModel) -> None:
        """Met à jour le modèle de configuration.

        Args:
            model: Nouveau modèle
        """
        self.state_data = replace(self.state_data, model=model)
