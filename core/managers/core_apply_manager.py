"""Gestionnaire d'application sécurisée de la configuration GRUB.

Implémente une machine à états pour valider la configuration avant de l'appliquer
définitivement, afin d'éviter de rendre le système non-bootable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH
from ..io.core_grub_default_io import write_grub_default


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

    def apply_configuration(self, new_config: dict[str, str], apply_changes: bool = True) -> ApplyResult:
        """Exécute le workflow complet d'application."""
        logger.info("[apply_configuration] Démarrage du processus d'application sécurisée...")

        try:
            # === VALIDATION PRÉALABLE: Vérifier que la nouvelle config a du contenu ===
            logger.debug("[apply_configuration] Validation préalable de la config")
            if not new_config:
                logger.error("[apply_configuration] ERREUR: Configuration vide fournie")
                raise ValueError("Configuration fournie est vide")

            required_keys = {"GRUB_TIMEOUT", "GRUB_DEFAULT"}
            missing_keys = required_keys - set(new_config.keys())
            if missing_keys:
                logger.warning(f"[apply_configuration] Clés recommandées manquantes: {missing_keys}")

            logger.debug(f"[apply_configuration] Config valide: {len(new_config)} clés")

            # 1. BACKUP
            self._transition_to(ApplyState.BACKUP)
            self._create_backup()

            # 2. WRITE (On écrit directement sur le fichier cible car grub-mkconfig le lit)
            # Si on échoue plus tard, on fera un rollback.
            self._transition_to(ApplyState.WRITE_TEMP)
            write_grub_default(new_config, str(self.grub_default_path))

            # === Validation post-écriture ===
            logger.debug("[apply_configuration] Vérification post-écriture")
            written_content = self.grub_default_path.read_text(encoding="utf-8", errors="replace")
            written_lines = [line for line in written_content.splitlines() if line.strip() and not line.startswith("#")]
            if len(written_lines) == 0:
                logger.error("[apply_configuration] ERREUR: Fichier écrit est vide ou invalide")
                raise RuntimeError("Le fichier écrit ne contient pas de configuration valide")
            logger.debug(f"[apply_configuration] Fichier écrit valide: {len(written_lines)} lignes")

            # 3. GENERATE TEST
            self._transition_to(ApplyState.GENERATE_TEST)
            self._generate_test_config()

            # 4. VALIDATE
            self._transition_to(ApplyState.VALIDATE)
            self._validate_config()

            # 5. APPLY (Finalize)
            verification_details = None
            if apply_changes:
                self._transition_to(ApplyState.APPLY)
                grub_cfg_mtime_before = Path(GRUB_CFG_PATH).stat().st_mtime if Path(GRUB_CFG_PATH).exists() else 0

                self._apply_final()

                # Vérification que grub.cfg a bien été modifié
                if Path(GRUB_CFG_PATH).exists():
                    grub_cfg_mtime_after = Path(GRUB_CFG_PATH).stat().st_mtime
                    grub_cfg_size_after = Path(GRUB_CFG_PATH).stat().st_size

                    if grub_cfg_mtime_after > grub_cfg_mtime_before:
                        verification_details = (
                            f"Workflow: {ApplyState.BACKUP.name} → {ApplyState.WRITE_TEMP.name} → "
                            f"{ApplyState.GENERATE_TEST.name} → {ApplyState.VALIDATE.name} → "
                            f"{ApplyState.APPLY.name} → {ApplyState.SUCCESS.name}\n"
                            f"✓ {GRUB_CFG_PATH} régénéré ({grub_cfg_size_after} bytes)"
                        )
                        logger.success(f"[apply_configuration] {verification_details}")
                    else:
                        logger.warning(f"[apply_configuration] {GRUB_CFG_PATH} n'a pas été modifié (suspect)")
                        verification_details = f"⚠ {GRUB_CFG_PATH} non modifié"
            else:
                logger.info("[apply_configuration] Application (update-grub) ignorée à la demande.")
                verification_details = (
                    f"Workflow: {ApplyState.BACKUP.name} → {ApplyState.WRITE_TEMP.name} → "
                    f"{ApplyState.GENERATE_TEST.name} → {ApplyState.VALIDATE.name} → {ApplyState.SUCCESS.name}\n"
                    f"Configuration validée (update-grub non exécuté)"
                )

            self._transition_to(ApplyState.SUCCESS)
            self._cleanup_backup()
            return ApplyResult(
                True,
                "Configuration appliquée avec succès." if apply_changes else "Configuration sauvegardée et validée.",
                ApplyState.SUCCESS,
                details=verification_details,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            failed_state = self._state
            logger.error(f"[apply_configuration] Erreur durant l'étape {failed_state.name}: {e}")
            error_msg = str(e)
            error_details = f"État: {failed_state.name} | Erreur: {error_msg}"

            # Tentative de rollback si on a dépassé l'étape de backup
            if failed_state in (ApplyState.WRITE_TEMP, ApplyState.GENERATE_TEST, ApplyState.VALIDATE, ApplyState.APPLY):
                logger.warning(f"[apply_configuration] Lancement du rollback depuis l'état {failed_state.name}...")
                try:
                    self._transition_to(ApplyState.ROLLBACK)
                    self._rollback()
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

            self._transition_to(ApplyState.ERROR)
            return ApplyResult(
                False, f"Erreur à l'étape {failed_state.name}: {error_msg}", ApplyState.ERROR, details=error_details
            )

    def _transition_to(self, new_state: ApplyState):
        logger.debug(f"Transition: {self._state.name} -> {new_state.name}")
        self._state = new_state

    def _create_backup(self):
        """Crée une copie de sauvegarde de /etc/default/grub."""
        logger.debug(f"[_create_backup] Vérification de {self.grub_default_path}")
        if not self.grub_default_path.exists():
            # Si le fichier n'existe pas, c'est étrange mais on peut créer un fichier vide pour le rollback
            # ou juste noter qu'il n'existait pas. Pour l'instant on assume qu'il doit exister.
            logger.error(f"[_create_backup] ERREUR: Le fichier {self.grub_default_path} n'existe pas")
            raise FileNotFoundError(f"Le fichier {self.grub_default_path} n'existe pas.")

        # === Vérification du fichier source ===
        logger.debug("[_create_backup] Vérification du fichier source")
        try:
            source_size = self.grub_default_path.stat().st_size
            if source_size == 0:
                logger.error("[_create_backup] ERREUR: Le fichier source est vide")
                raise RuntimeError("Le fichier source est vide")

            # Vérifier que le fichier contient de la configuration valide
            content = self.grub_default_path.read_text(encoding="utf-8", errors="replace")
            lines = [line for line in content.splitlines() if line.strip() and not line.startswith("#")]
            if len(lines) == 0:
                logger.error("[_create_backup] ERREUR: Le fichier source ne contient pas de configuration")
                raise RuntimeError("Le fichier source ne contient pas de configuration valide")

            logger.debug(f"[_create_backup] Fichier source valide: {source_size} bytes, {len(lines)} lignes")
        except OSError as e:
            logger.error(f"[_create_backup] ERREUR: Impossible de vérifier le fichier source - {e}")
            raise

        # === Création du backup ===
        try:
            shutil.copy2(self.grub_default_path, self.backup_path)
            logger.info(f"[_create_backup] Backup créé: {self.backup_path}")

            # Vérifier que le backup a été créé avec succès
            backup_size = self.backup_path.stat().st_size
            if backup_size != source_size:
                logger.error(f"[_create_backup] ERREUR: Taille du backup ({backup_size}) != source ({source_size})")
                raise RuntimeError(f"Le backup est incomplet: {backup_size} vs {source_size} bytes")

            logger.success(f"[_create_backup] Succès - {source_size} bytes sauvegardés, backup: {self.backup_path}")
        except OSError as e:
            logger.error(f"[_create_backup] ERREUR: Impossible de créer le backup - {e}")
            raise

    def _generate_test_config(self):
        """Génère une configuration GRUB de test."""
        cmd = ["grub-mkconfig", "-o", str(self.temp_cfg_path)]
        logger.debug(f"[_generate_test_config] Exécution: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        logger.debug(f"[_generate_test_config] Résultat: returncode={result.returncode}")

        if result.returncode != 0:
            logger.error(f"[_generate_test_config] ERREUR: grub-mkconfig failed - {result.stderr[:200]}")
            raise RuntimeError(f"grub-mkconfig a échoué:\n{result.stderr}")

        if not self.temp_cfg_path.exists() or self.temp_cfg_path.stat().st_size == 0:
            logger.error("[_generate_test_config] ERREUR: Fichier généré vide ou absent")
            raise RuntimeError("Le fichier de configuration généré est vide ou absent.")

        # === VALIDATION SUPPLÉMENTAIRE: Contenu du fichier généré ===
        logger.debug("[_generate_test_config] Vérification du contenu du fichier généré")
        try:
            with open(self.temp_cfg_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
                # Au minimum, un grub.cfg valide doit avoir des lignes non-vides
                lines = [line for line in content.splitlines() if line.strip()]
                if len(lines) < 5:
                    logger.error(
                        f"[_generate_test_config] ERREUR: Fichier généré trop court ({len(lines)} lignes utiles)"
                    )
                    raise RuntimeError(
                        f"Le fichier de configuration généré est anormalement court ({len(lines)} lignes)."
                    )

                # Vérifier la présence de marqueurs essentiels
                if "menuentry" not in content.lower() and "echo" not in content.lower():
                    logger.warning(
                        "[_generate_test_config] ATTENTION: Pas de 'menuentry' trouvé, configuration minimaliste"
                    )

                logger.debug(f"[_generate_test_config] Validation contenu: OK ({len(lines)} lignes utiles)")
        except OSError as e:
            logger.error(f"[_generate_test_config] ERREUR: Impossible de lire le fichier généré - {e}")
            raise RuntimeError(f"Impossible de valider le fichier généré: {e}") from e

        logger.info(f"Configuration de test générée: {self.temp_cfg_path} ({self.temp_cfg_path.stat().st_size} bytes)")

    def _validate_config(self):
        """Vérifie la syntaxe du fichier généré et sa cohérence."""
        logger.debug("[_validate_config] Début des validations")

        # === VALIDATION 1: Vérification du fichier ===
        logger.debug("[_validate_config] Validation 1: Existence et format du fichier")
        if not self.temp_cfg_path.exists():
            logger.error("[_validate_config] ERREUR: Fichier de test introuvable")
            raise RuntimeError("Le fichier de configuration de test a disparu")

        file_size = self.temp_cfg_path.stat().st_size
        if file_size == 0:
            logger.error("[_validate_config] ERREUR: Fichier vide")
            raise RuntimeError("Le fichier de configuration généré est vide")

        if file_size < 100:
            logger.warning(
                f"[_validate_config] Fichier très petit ({file_size} bytes), validation attentive recommandée"
            )

        logger.debug(f"[_validate_config] Fichier valide: {file_size} bytes")

        # === VALIDATION 2: Syntaxe GRUB ===
        check_cmd = shutil.which("grub-script-check")
        if check_cmd:
            cmd = [check_cmd, str(self.temp_cfg_path)]
            logger.debug(f"[_validate_config] Validation 2: Syntaxe GRUB via {check_cmd}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            logger.debug(f"[_validate_config] grub-script-check returncode={result.returncode}")
            if result.returncode != 0:
                logger.error(f"[_validate_config] ERREUR: Validation syntaxique échouée - {result.stderr[:200]}")
                raise RuntimeError(f"Validation syntaxique échouée:\n{result.stderr}")
            logger.success("[_validate_config] Validation syntaxique: OK")
        else:
            logger.warning("[_validate_config] grub-script-check non trouvé, validation syntaxique ignorée.")

        # === VALIDATION 3: Cohérence du contenu ===
        logger.debug("[_validate_config] Validation 3: Cohérence du contenu")
        try:
            with open(self.temp_cfg_path, encoding="utf-8", errors="replace") as f:
                content = f.read()

                # Compte les menuentry (entrées de boot)
                menuentry_count = content.count("menuentry ")
                logger.debug(f"[_validate_config] Nombre de menuentry: {menuentry_count}")

                # Vérifie la présence d'éléments minimaux
                required_elements = {
                    "### BEGIN /etc/": "Marqueur de début",
                    "### END /etc/": "Marqueur de fin",
                    "linux": "Entrée de kernel",
                }

                missing = []
                for marker, desc in required_elements.items():
                    if marker not in content:
                        missing.append(desc)

                if missing:
                    logger.warning(f"[_validate_config] Éléments manquants: {', '.join(missing)}")

                # Vérification finale: la config n'est pas trop anormale
                lines = content.splitlines()
                non_empty_lines = [line for line in lines if line.strip() and not line.startswith("#")]
                if len(non_empty_lines) < 3:
                    logger.error(
                        f"[_validate_config] ERREUR: Config générée trop minimale "
                        f"({len(non_empty_lines)} lignes de code)"
                    )
                    raise RuntimeError(
                        f"La configuration générée semble incomplète " f"({len(non_empty_lines)} lignes de code)"
                    )

                logger.success(f"[_validate_config] Cohérence vérifiée: {len(non_empty_lines)} lignes de code")
        except OSError as e:
            logger.error(f"[_validate_config] ERREUR: Impossible de lire le fichier - {e}")
            raise RuntimeError(f"Erreur de lecture du fichier de configuration: {e}") from e

        logger.success("[_validate_config] Toutes les validations réussies")

    def _apply_final(self):
        """Applique la configuration finale (update-grub)."""
        update_cmd = shutil.which("update-grub")
        if update_cmd:
            cmd = [update_cmd]
            logger.debug("[_apply_final] Utilisation de update-grub")
        else:
            cmd = ["grub-mkconfig", "-o", GRUB_CFG_PATH]
            logger.debug("[_apply_final] update-grub non trouvé, utilisation de grub-mkconfig")

        logger.info(f"[_apply_final] Exécution: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        logger.debug(f"[_apply_final] Résultat: returncode={result.returncode}")
        if result.returncode != 0:
            logger.error(f"[_apply_final] ERREUR: Mise à jour finale échouée - {result.stderr[:200]}")
            raise RuntimeError(f"Mise à jour finale échouée:\n{result.stderr}")
        logger.success("[_apply_final] Configuration GRUB appliquée avec succès")

    def _rollback(self):
        """Restaure le fichier /etc/default/grub original."""
        logger.warning("[_rollback] Début du rollback")
        if not self.backup_path.exists():
            logger.error(f"[_rollback] ERREUR CRITIQUE: Backup introuvable à {self.backup_path}")
            raise FileNotFoundError(f"Backup introuvable: {self.backup_path}")

        # === SÉCURITÉ: Vérifier que le backup est valide avant de l'appliquer ===
        logger.debug("[_rollback] Vérification du backup avant restauration")
        try:
            backup_size = self.backup_path.stat().st_size
            if backup_size == 0:
                logger.error("[_rollback] ERREUR CRITIQUE: Le backup est vide, refus de restaurer")
                raise RuntimeError("Le fichier de sauvegarde est vide")
            logger.debug(f"[_rollback] Backup valide: {backup_size} bytes")
        except OSError as e:
            logger.error(f"[_rollback] ERREUR CRITIQUE: Impossible de vérifier le backup - {e}")
            raise

        # === Restauration ===
        try:
            # Créer un backup du fichier corrompu avant de l'écraser
            corrupted_backup = self.grub_default_path.with_suffix(".corrupted")
            if self.grub_default_path.exists():
                logger.debug(f"[_rollback] Archivage de la version problématique: {corrupted_backup}")
                try:
                    shutil.copy2(self.grub_default_path, corrupted_backup)
                    logger.info(f"Version problématique archivée: {corrupted_backup}")
                except OSError as e:
                    logger.warning(f"[_rollback] Impossible d'archiver la version problématique: {e}")

            # Restaurer depuis le backup
            shutil.copy2(self.backup_path, self.grub_default_path)
            logger.info(f"Fichier /etc/default/grub restauré depuis {self.backup_path}")

            # === Validation post-restauration ===
            logger.debug("[_rollback] Vérification post-restauration")
            restored_content = self.grub_default_path.read_text(encoding="utf-8", errors="replace")
            restored_lines = [
                line for line in restored_content.splitlines() if line.strip() and not line.startswith("#")
            ]
            if len(restored_lines) == 0:
                logger.error("[_rollback] ERREUR CRITIQUE: Fichier restauré est vide ou invalide")
                raise RuntimeError("Le fichier restauré est invalide")
            logger.debug(f"[_rollback] Fichier restauré valide: {len(restored_lines)} lignes de config")

            logger.success("[_rollback] Succès - ancien fichier restauré et vérifié")
        except Exception as e:
            logger.error(f"[_rollback] ERREUR: Impossible de restaurer le backup - {e!s}")
            raise

    def _cleanup_backup(self):
        """Supprime le backup temporaire en cas de succès."""
        try:
            if self.backup_path.exists():
                os.remove(self.backup_path)
                logger.debug(f"[_cleanup_backup] Backup temporaire supprimé: {self.backup_path}")
        except OSError as e:
            logger.warning(f"[_cleanup_backup] Impossible de supprimer le backup: {e}")
