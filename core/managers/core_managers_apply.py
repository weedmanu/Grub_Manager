"""Gestionnaire d'application sécurisée de la configuration GRUB.

Implémente une machine à états pour valider la configuration avant de l'appliquer
définitivement, afin d'éviter de rendre le système non-bootable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from loguru import logger

from ..config.core_config_paths import GRUB_DEFAULT_PATH
from ..core_exceptions import (
    GrubRollbackError,
)
from .core_managers_apply_states import (
    ApplyContext,
    ApplyFinalState,
    ApplyPaths,
    BackupState,
    CleanupState,
    GenerateTestState,
    GrubApplyState,
    ValidateState,
    WriteState,
)


class ApplyState(Enum):
    """États possibles de la machine à états d'application."""

    IDLE = auto()
    BACKUP = auto()
    WRITE_TEMP = auto()
    GENERATE_TEST = auto()
    VALIDATE = auto()
    APPLY = auto()
    ROLLBACK = auto()
    ERROR = auto()
    SUCCESS = auto()


@dataclass
class ApplyResult:
    """Résultat de l'opération d'application."""

    success: bool
    message: str
    state: ApplyState
    details: str | None = None


class GrubApplyManager:
    """Gère le cycle de vie de l'application de la configuration GRUB."""

    # pylint: disable=too-few-public-methods

    def __init__(self, grub_default_path: str = GRUB_DEFAULT_PATH):
        """Initialise le gestionnaire avec le chemin du fichier de configuration."""
        self.grub_default_path = Path(grub_default_path)
        self.backup_path = self.grub_default_path.with_suffix(".bak.apply")
        # Utiliser le même répertoire que grub_default pour le fichier de test
        self.temp_cfg_path = self.grub_default_path.parent / "grub.cfg.test"
        self._state = ApplyState.IDLE

    def apply_configuration(
        self,
        new_config: dict[str, str],
        apply_changes: bool = True,
        theme_management_enabled: bool = True,
        pending_script_changes: dict[str, bool] | None = None,
    ) -> ApplyResult:
        """Exécute le workflow complet d'application via la machine à états."""
        logger.info("[apply_configuration] Démarrage du processus d'application sécurisée...")

        # Initialisation du contexte
        context = ApplyContext(
            paths=ApplyPaths(backup_path=self.backup_path, temp_cfg_path=self.temp_cfg_path),
            grub_default_path=self.grub_default_path,
            new_config=new_config,
            apply_changes=apply_changes,
            theme_management_enabled=theme_management_enabled,
            pending_script_changes=pending_script_changes or {},
        )

        # État initial
        current_state_class: type[GrubApplyState] | None = BackupState
        self._state = ApplyState.BACKUP

        try:
            # Boucle de la machine à états
            while current_state_class is not None:
                # Instanciation de l'état courant
                state_instance: GrubApplyState = current_state_class(context)

                # Mise à jour de l'état interne (pour le reporting)
                self._update_internal_state(current_state_class)

                logger.debug(f"[apply_configuration] Exécution de l'état: {current_state_class.__name__}")

                # Exécution de l'état
                next_state_class = state_instance.execute()

                # Transition
                current_state_class = next_state_class

            # Si on sort de la boucle normalement (CleanupState retourne None)
            self._state = ApplyState.SUCCESS
            return ApplyResult(
                True,
                "Configuration appliquée avec succès." if apply_changes else "Configuration sauvegardée et validée.",
                ApplyState.SUCCESS,
                details=context.verification_details,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            failed_state = self._state
            logger.error(f"[apply_configuration] Erreur durant l'étape {failed_state.name}: {e}")
            error_msg = str(e)
            error_details = f"État: {failed_state.name} | Erreur: {error_msg}"

            # Tentative de rollback si nécessaire
            if failed_state in (ApplyState.WRITE_TEMP, ApplyState.GENERATE_TEST, ApplyState.VALIDATE, ApplyState.APPLY):
                logger.warning(f"[apply_configuration] Lancement du rollback depuis l'état {failed_state.name}...")
                try:
                    self._state = ApplyState.ROLLBACK
                    self._perform_rollback(context)
                    return ApplyResult(
                        False,
                        f"Échec à l'étape {failed_state.name}: {error_msg}. Restauration effectuée.",
                        ApplyState.ROLLBACK,
                        details=error_details,
                    )
                except Exception as rollback_error:  # pylint: disable=broad-exception-caught
                    logger.critical(f"[apply_configuration] ÉCHEC DU ROLLBACK: {rollback_error}")
                    return ApplyResult(
                        False,
                        f"Échec CRITIQUE à l'étape {failed_state.name}: {error_msg}. Rollback échoué: {rollback_error}",
                        ApplyState.ERROR,
                        details=f"{error_details} | Rollback échoué: {rollback_error}",
                    )

            self._state = ApplyState.ERROR
            return ApplyResult(
                False, f"Erreur à l'étape {failed_state.name}: {error_msg}", ApplyState.ERROR, details=error_details
            )

    def _update_internal_state(self, state_class):
        """Met à jour l'état interne basé sur la classe d'état en cours."""
        if state_class == BackupState:
            self._state = ApplyState.BACKUP
        elif state_class == WriteState:
            self._state = ApplyState.WRITE_TEMP
        elif state_class == GenerateTestState:
            self._state = ApplyState.GENERATE_TEST
        elif state_class == ValidateState:
            self._state = ApplyState.VALIDATE
        elif state_class == ApplyFinalState:
            self._state = ApplyState.APPLY
        elif state_class == CleanupState:
            # Cleanup est la dernière étape avant SUCCESS
            pass

    def _perform_rollback(self, context: ApplyContext):
        """Exécute le rollback global."""
        # 1. Nettoyage du fichier temporaire (responsabilité de GenerateTestState/ValidateState)
        if context.temp_cfg_path.exists():
            try:
                os.remove(context.temp_cfg_path)
                logger.info("[_perform_rollback] Fichier temporaire supprimé.")
            except OSError as e:
                logger.warning(f"[_perform_rollback] Impossible de supprimer le fichier temporaire: {e}")

        # 2. Restauration du backup (responsabilité de WriteState)
        # On utilise WriteState pour effectuer le rollback car il contient la logique de restauration
        try:
            WriteState(context).rollback()
        except GrubRollbackError:
            raise
        except Exception as e:
            raise GrubRollbackError(f"Erreur inattendue lors du rollback: {e}") from e
