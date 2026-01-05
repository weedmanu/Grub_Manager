"""États de la machine à états pour l'application de la configuration GRUB."""

from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATH
from ..core_exceptions import (
    GrubBackupError,
    GrubCommandError,
    GrubRollbackError,
    GrubValidationError,
)
from ..io.core_grub_default_io import write_grub_default
from ..io.grub_validation import validate_grub_file
from ..services.core_grub_script_service import GrubScriptService


@dataclass
class ApplyContext:
    """Contexte partagé entre les états."""

    grub_default_path: Path
    backup_path: Path
    temp_cfg_path: Path
    new_config: dict[str, str]
    apply_changes: bool
    theme_management_enabled: bool = True
    pending_script_changes: dict[str, bool] = field(default_factory=dict)
    verification_details: str | None = None


class GrubApplyState(ABC):
    """Classe de base abstraite pour un état d'application."""

    def __init__(self, context: ApplyContext):
        """Initialise l'état avec le contexte partagé."""
        self.context = context

    @abstractmethod
    def execute(self) -> type[GrubApplyState] | None:
        """Exécute la logique de l'état et retourne le prochain état."""

    def rollback(self) -> None:
        """Effectue le rollback spécifique à cet état (si nécessaire)."""
        return


class BackupState(GrubApplyState):
    """État 1: Création du backup de sécurité."""

    def execute(self) -> type[GrubApplyState] | None:
        """Crée une sauvegarde du fichier de configuration actuel."""
        logger.debug(f"[BackupState] Vérification de {self.context.grub_default_path}")
        if not self.context.grub_default_path.exists():
            logger.error(f"[BackupState] ERREUR: Le fichier {self.context.grub_default_path} n'existe pas")
            raise GrubBackupError(f"Le fichier {self.context.grub_default_path} n'existe pas.")

        # Validation source
        try:
            validation = validate_grub_file(self.context.grub_default_path)
            if not validation.is_valid:
                logger.error(f"[BackupState] ERREUR: {validation.error_message}")
                raise GrubBackupError(f"Source invalide: {validation.error_message}")
        except OSError as e:
            logger.error(f"[BackupState] ERREUR: Impossible de vérifier le fichier source - {e}")
            raise

        # Création backup
        try:
            source_size = self.context.grub_default_path.stat().st_size
            shutil.copy2(self.context.grub_default_path, self.context.backup_path)

            backup_size = self.context.backup_path.stat().st_size
            if backup_size != source_size:
                raise GrubBackupError(f"Le backup est incomplet: {backup_size} vs {source_size} bytes")

            logger.success(f"[BackupState] Backup créé: {self.context.backup_path}")
            return WriteState
        except OSError as e:
            logger.error(f"[BackupState] ERREUR: Impossible de créer le backup - {e}")
            raise GrubBackupError(f"Impossible de créer le backup: {e}") from e


class WriteState(GrubApplyState):
    """État 2: Écriture de la nouvelle configuration."""

    def execute(self) -> type[GrubApplyState] | None:
        """Écrit la nouvelle configuration dans le fichier par défaut."""
        write_grub_default(self.context.new_config, str(self.context.grub_default_path))

        # Validation post-écriture
        written_content = self.context.grub_default_path.read_text(encoding="utf-8", errors="replace")
        written_lines = [line for line in written_content.splitlines() if line.strip() and not line.startswith("#")]

        if len(written_lines) == 0:
            logger.error("[WriteState] ERREUR: Fichier écrit est vide ou invalide")
            raise GrubValidationError("Le fichier écrit ne contient pas de configuration valide")

        logger.debug(f"[WriteState] Fichier écrit valide: {len(written_lines)} lignes")
        return GenerateTestState

    def rollback(self) -> None:
        """Restaure le fichier original depuis le backup."""
        logger.warning("[WriteState] Rollback demandé")
        if not self.context.backup_path.exists():
            raise GrubRollbackError(f"Backup introuvable: {self.context.backup_path}")

        # Vérification du backup avant restauration
        if self.context.backup_path.stat().st_size == 0:
            raise GrubRollbackError("Le fichier de sauvegarde est vide")

        try:
            shutil.copy2(self.context.backup_path, self.context.grub_default_path)
            logger.info(f"Fichier restauré depuis {self.context.backup_path}")

            # Validation post-restauration
            restored_content = self.context.grub_default_path.read_text(encoding="utf-8", errors="replace")
            restored_lines = [
                line for line in restored_content.splitlines() if line.strip() and not line.startswith("#")
            ]
            if len(restored_lines) == 0:
                raise GrubRollbackError("Le fichier restauré est invalide")

        except OSError as e:
            raise GrubRollbackError(f"Impossible de restaurer le backup: {e}") from e


class GenerateTestState(GrubApplyState):
    """État 3: Génération d'une configuration de test."""

    def execute(self) -> type[GrubApplyState] | None:
        """Génère un fichier grub.cfg temporaire pour validation."""
        cmd = ["grub-mkconfig", "-o", str(self.context.temp_cfg_path)]
        logger.debug(f"[GenerateTestState] Exécution: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error(f"[GenerateTestState] ERREUR: grub-mkconfig failed - {result.stderr[:200]}")
            raise GrubCommandError(
                f"grub-mkconfig a échoué:\n{result.stderr}",
                command=" ".join(cmd),
                returncode=result.returncode,
                stderr=result.stderr,
            )

        if not self.context.temp_cfg_path.exists() or self.context.temp_cfg_path.stat().st_size == 0:
            raise GrubValidationError("Le fichier de configuration généré est vide ou absent.")

        return ValidateState

    def rollback(self) -> None:
        """Nettoie le fichier temporaire en cas d'échec."""
        # Hérite du rollback de WriteState (restauration fichier)
        # Mais on peut aussi nettoyer le fichier temporaire
        if self.context.temp_cfg_path.exists():
            try:
                os.remove(self.context.temp_cfg_path)
            except OSError:
                pass
        # Appel explicite au rollback parent n'est pas possible ici car WriteState n'est pas parent
        # Le manager gérera le rollback principal (restauration fichier)


class ValidateState(GrubApplyState):
    """État 4: Validation de la configuration générée."""

    def execute(self) -> type[GrubApplyState] | None:
        """Valide le fichier de configuration généré."""
        # Validation 1: Existence et taille
        if not self.context.temp_cfg_path.exists():
            raise GrubValidationError("Le fichier de configuration de test a disparu")

        if self.context.temp_cfg_path.stat().st_size == 0:
            raise GrubValidationError("Le fichier de configuration généré est vide")

        # Validation 2: Syntaxe GRUB
        check_cmd = shutil.which("grub-script-check")
        if check_cmd:
            cmd = [check_cmd, str(self.context.temp_cfg_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise GrubValidationError(f"Validation syntaxique échouée:\n{result.stderr}")

        # Validation 3: Cohérence contenu
        try:
            content = self.context.temp_cfg_path.read_text(encoding="utf-8", errors="replace")
            lines = [line for line in content.splitlines() if line.strip() and not line.startswith("#")]
            if len(lines) < 3:
                raise GrubValidationError(f"La configuration générée semble incomplète ({len(lines)} lignes)")
        except OSError as e:
            raise GrubValidationError(f"Erreur de lecture du fichier de configuration: {e}") from e

        return ApplyFinalState


class ApplyFinalState(GrubApplyState):
    """État 5: Application finale (update-grub)."""

    def execute(self) -> type[GrubApplyState] | None:
        """Applique la configuration finale via update-grub."""
        if not self.context.apply_changes:
            logger.info("[ApplyFinalState] Application ignorée à la demande.")
            self.context.verification_details = "Configuration validée (update-grub non exécuté)"
            return CleanupState

        # Gestion des scripts de thème AVANT update-grub
        try:
            script_service = GrubScriptService()
            theme_scripts = script_service.scan_theme_scripts()

            logger.info(
                f"[ApplyFinalState] Gestion des scripts (Target Enabled={self.context.theme_management_enabled})"
            )

            for script in theme_scripts:
                should_be_executable = None

                # Si la gestion de thème est activée (Mode Thème), on active les scripts par défaut (comportement existant)
                if self.context.theme_management_enabled:
                    should_be_executable = True
                # Si la gestion de thème est désactivée (Mode Simple Config), on applique les changements demandés
                elif script.path in self.context.pending_script_changes:
                    should_be_executable = self.context.pending_script_changes[script.path]
                
                # Si should_be_executable est None, on ne change rien (on garde l'état actuel)

                if should_be_executable is not None:
                    # Si l'état actuel diffère de l'état souhaité
                    if script.is_executable != should_be_executable:
                        logger.info(
                            f"[ApplyFinalState] Modification script {script.name}: {script.is_executable} -> {should_be_executable}"
                        )
                        try:
                            if should_be_executable:
                                script_service.make_executable(script.path)
                            else:
                                script_service.make_non_executable(script.path)
                            logger.success(f"[ApplyFinalState] Script {script.name} mis à jour")
                        except Exception as e:
                            logger.error(f"[ApplyFinalState] Échec modification {script.name}: {e}")
                    else:
                        logger.debug(
                            f"[ApplyFinalState] Script {script.name} déjà dans l'état souhaité ({should_be_executable})"
                        )

        except Exception as e:
            logger.warning(f"[ApplyFinalState] Erreur lors de la gestion des scripts de thème: {e}")
            # On continue quand même pour update-grub

        grub_cfg_mtime_before = Path(GRUB_CFG_PATH).stat().st_mtime if Path(GRUB_CFG_PATH).exists() else 0

        update_cmd = shutil.which("update-grub")
        cmd = [update_cmd] if update_cmd else ["grub-mkconfig", "-o", GRUB_CFG_PATH]

        logger.info(f"[ApplyFinalState] Exécution: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise GrubCommandError(
                f"Mise à jour finale échouée:\n{result.stderr}",
                command=" ".join(cmd),
                returncode=result.returncode,
                stderr=result.stderr,
            )

        # Vérification modification
        if Path(GRUB_CFG_PATH).exists():
            grub_cfg_mtime_after = Path(GRUB_CFG_PATH).stat().st_mtime
            if grub_cfg_mtime_after > grub_cfg_mtime_before:
                self.context.verification_details = f"✓ {GRUB_CFG_PATH} régénéré"
            else:
                self.context.verification_details = f"⚠ {GRUB_CFG_PATH} non modifié"

        return CleanupState


class CleanupState(GrubApplyState):
    """État 6: Nettoyage des fichiers temporaires."""

    def execute(self) -> None:
        """Supprime les fichiers temporaires et de sauvegarde."""
        try:
            if self.context.backup_path.exists():
                os.remove(self.context.backup_path)
            if self.context.temp_cfg_path.exists():
                os.remove(self.context.temp_cfg_path)
        except OSError as e:
            logger.warning(f"[CleanupState] Erreur nettoyage: {e}")
