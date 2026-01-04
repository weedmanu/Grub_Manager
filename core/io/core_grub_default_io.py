"""Lecture/écriture de /etc/default/grub (format KEY=VALUE).

Aucune logique UI ici.
"""

from __future__ import annotations

import os
import shutil
import tarfile
import uuid
from datetime import datetime
from glob import glob
from pathlib import Path

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATHS, GRUB_DEFAULT_PATH
from ..core_exceptions import GrubBackupError, GrubConfigError


def _touch_now(path: str) -> None:
    """Force le mtime à 'maintenant' (utile car copy2 copie le mtime source)."""
    try:
        os.utime(path, None)
    except OSError:
        pass


def _add_to_tar(tar: tarfile.TarFile, source: str | Path, arcname: str, filter_func) -> bool:
    """Ajoute un fichier au tar avec gestion d'erreurs. Retourne True si ajouté."""
    try:
        if os.path.exists(source):
            tar.add(source, arcname=arcname, filter=filter_func)
            logger.debug(f"Ajouté au tar: {source} as {arcname}")
            return True
    except (OSError, PermissionError) as e:
        logger.debug(f"Impossible d'ajouter {source} au tar: {e}")
    return False


def _prune_manual_backups(path: str, *, keep: int = 3) -> list[str]:
    """Supprime les plus vieilles sauvegardes manuelles au-delà de `keep`."""
    keep = max(keep, 1)
    backups = [p for p in glob(f"{path}.backup.manual.*") if os.path.isfile(p)]
    backups.sort(key=os.path.getmtime)  # plus vieux -> plus récent
    to_delete = backups[:-keep] if len(backups) > keep else []
    deleted: list[str] = []
    for p in to_delete:
        try:
            os.remove(p)
            deleted.append(p)
        except OSError:
            # Best-effort: on continue.
            continue
    return deleted


def ensure_initial_grub_default_backup(path: str = GRUB_DEFAULT_PATH) -> str | None:
    """Crée un backup *initial* complet de la configuration GRUB si absent.

    Sauvegarde :
    - /etc/default/grub
    - /etc/grub.d/ (tous les scripts)
    - /boot/grub/grub.cfg (ou /boot/grub2/grub.cfg)

    Objectif: disposer d'une copie "connue bonne" avant toute modification.
    La création est best-effort: en cas d'erreur (permissions, fichier manquant,
    FS en lecture seule), la fonction ne lève pas et renvoie None.

    Le backup initial n'est jamais écrasé.

    Returns:
        Le chemin du backup initial (archive .tar.gz), ou None si non disponible.
    """
    logger.debug(f"[ensure_initial_grub_default_backup] Vérification du backup initial pour {path}")
    backup_dir = Path(path).parent
    initial_backup_path = backup_dir / "grub_backup.initial.tar.gz"

    # En tests, on passe souvent un chemin temporaire. Dans ce cas, on évite
    # de parcourir /etc/grub.d et /boot (lent + dépend de l'environnement).
    full_system_backup = os.path.abspath(path) == os.path.abspath(GRUB_DEFAULT_PATH)

    def _safe_is_file(p: str) -> bool:
        try:
            return os.path.isfile(p)
        except OSError:
            return False

    if initial_backup_path.exists():
        logger.debug(f"[ensure_initial_grub_default_backup] Backup initial trouvé: {initial_backup_path}")
        return str(initial_backup_path)

    # Si le fichier canonique n'existe pas, tente d'abord une restauration
    if not _safe_is_file(path):
        try:
            logger.debug(f"[ensure_initial_grub_default_backup] {path} absent, tentative de restauration")
            _ = read_grub_default(path)
        except (OSError, GrubConfigError):
            logger.warning(f"[ensure_initial_grub_default_backup] Impossible de créer un backup initial: {path} absent")
            return None

    def _tar_filter(tarinfo):
        """Filtre pour ignorer les erreurs de permissions lors du tar.add()."""
        try:
            # Vérifier que le fichier source est accessible
            if os.path.exists(tarinfo.name) and not os.access(tarinfo.name, os.R_OK):
                logger.debug(f"[ensure_initial_grub_default_backup] Fichier non accessible: {tarinfo.name}")
                return None
            return tarinfo
        except (OSError, PermissionError):
            logger.debug(f"[ensure_initial_grub_default_backup] Fichier non accessible: {tarinfo.name}")
            return None

    try:
        logger.info(f"Création backup initial complet -> {initial_backup_path}")

        with tarfile.open(initial_backup_path, "w:gz", compresslevel=1) as tar:
            # 1. Sauvegarder /etc/default/grub
            _add_to_tar(tar, path, "default_grub", _tar_filter)

            if full_system_backup:
                # 2. Sauvegarder /etc/grub.d/
                grub_d_dir = Path("/etc/grub.d")
                if grub_d_dir.exists():
                    for script in grub_d_dir.iterdir():
                        if script.is_file():
                            _add_to_tar(tar, script, f"grub.d/{script.name}", _tar_filter)

                # 3. Sauvegarder grub.cfg
                for grub_cfg_path in GRUB_CFG_PATHS:
                    if _add_to_tar(
                        tar,
                        grub_cfg_path,
                        f"grub.cfg_{Path(grub_cfg_path).parts[2]}",
                        _tar_filter,
                    ):
                        break

        logger.success(f"[ensure_initial_grub_default_backup] Backup complet créé: {initial_backup_path}")
        return str(initial_backup_path)

    except (OSError, tarfile.TarError) as e:
        logger.warning(f"[ensure_initial_grub_default_backup] Impossible de créer le backup initial: {e}")
        return None


def list_grub_default_backups(path: str = GRUB_DEFAULT_PATH) -> list[str]:
    """List GRUB default backups associated with `/etc/default/grub`.

    Retourne tous les fichiers qui matchent `<path>.backup*` ou `<path>_backup.initial*`.
    Le résultat est trié par date de modification décroissante.
    """
    candidates = [p for p in glob(f"{path}.backup*") if os.path.isfile(p) and p != path]

    # Ajouter aussi le backup initial s'il existe
    initial_backup = f"{path}_backup.initial.tar.gz"
    if os.path.isfile(initial_backup):
        candidates.append(initial_backup)

    # Tri stable: plus récent d'abord, puis par chemin.
    candidates.sort(key=lambda p: (-os.path.getmtime(p), p))
    return candidates


def create_grub_default_backup(path: str = GRUB_DEFAULT_PATH) -> str:
    """Crée une nouvelle sauvegarde complète horodatée au format tar.gz.

    Sauvegarde :
    - /etc/default/grub
    - /etc/grub.d/ (tous les scripts)
    - /boot/grub/grub.cfg (ou /boot/grub2/grub.cfg)

    Le backup créé a la forme `<path>.backup.manual.YYYYMMDD-HHMMSS.tar.gz`.

    Returns:
        Le chemin du backup créé.

    Raises:
        OSError: si la création échoue.
        FileNotFoundError: si aucune source (fichier ou fallback) n'est trouvée.
    """
    logger.debug(f"[create_grub_default_backup] Création d'une nouvelle sauvegarde pour {path}")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_backup_path = f"{path}.backup.manual.{ts}.tar.gz"
    backup_path = base_backup_path

    def _safe_exists(p: str) -> bool:
        try:
            return os.path.exists(p)
        except OSError:
            return False

    def _safe_is_file(p: str) -> bool:
        try:
            return os.path.isfile(p)
        except OSError:
            return False

    # Assure un nom unique (borne la boucle pour éviter un blocage si exists()
    # est mocké/buggé et renvoie toujours True).
    suffix = 1
    max_attempts = 128
    while _safe_exists(backup_path) and suffix <= max_attempts:
        backup_path = f"{path}.backup.manual.{ts}.{suffix}.tar.gz"
        suffix += 1
    if _safe_exists(backup_path):
        backup_path = f"{path}.backup.manual.{ts}.{uuid.uuid4().hex}.tar.gz"

    source_path = path
    if not _safe_is_file(source_path):
        logger.debug(f"[create_grub_default_backup] {path} absent, recherche de fallback")
        fallback = _best_fallback_for_missing_config(path)
        if fallback is None:
            logger.error("[create_grub_default_backup] ERREUR: Aucune source trouvée")
            raise GrubConfigError(f"Aucune source trouvée pour le backup: {path}")
        source_path = fallback
        logger.debug(f"[create_grub_default_backup] Fallback trouvé: {source_path}")

    logger.info(f"Création sauvegarde complète manuelle -> {backup_path}")

    # En tests, on passe souvent un chemin temporaire. Dans ce cas, on évite
    # de parcourir /etc/grub.d et /boot (lent + dépend de l'environnement).
    full_system_backup = os.path.abspath(path) == os.path.abspath(GRUB_DEFAULT_PATH)

    def _tar_filter_manual(tarinfo):
        """Filtre pour ignorer les erreurs de permissions lors du tar.add()."""
        try:
            # Vérifier que le fichier source est accessible
            if os.path.exists(tarinfo.name) and not os.access(tarinfo.name, os.R_OK):
                logger.debug(f"[create_grub_default_backup] Fichier non accessible: {tarinfo.name}")
                return None
            return tarinfo
        except (OSError, PermissionError):
            logger.debug(f"[create_grub_default_backup] Fichier non accessible: {tarinfo.name}")
            return None

    try:
        with tarfile.open(backup_path, "w:gz", compresslevel=1) as tar:
            # 1. Sauvegarder /etc/default/grub
            _add_to_tar(tar, source_path, "default_grub", _tar_filter_manual)

            if full_system_backup:
                # 2. Sauvegarder /etc/grub.d/
                grub_d_dir = Path("/etc/grub.d")
                if grub_d_dir.exists():
                    for script in grub_d_dir.iterdir():
                        if script.is_file():
                            _add_to_tar(tar, script, f"grub.d/{script.name}", _tar_filter_manual)

                # 3. Sauvegarder grub.cfg
                for grub_cfg_path in GRUB_CFG_PATHS:
                    if _add_to_tar(
                        tar,
                        grub_cfg_path,
                        f"grub.cfg_{Path(grub_cfg_path).parts[2]}",
                        _tar_filter_manual,
                    ):
                        break

        _touch_now(backup_path)
        logger.success(f"[create_grub_default_backup] Succès - {backup_path}")

    except (OSError, tarfile.TarError) as e:
        logger.error(f"[create_grub_default_backup] ERREUR: {e}")
        raise OSError(f"Échec création sauvegarde: {e}") from e

    # Roulement: ne garde que les 3 plus récentes sauvegardes manuelles.
    deleted = _prune_manual_backups(path, keep=3)
    if deleted:
        logger.info(f"[create_grub_default_backup] Nettoyage: {len(deleted)} anciennes sauvegarde(s) supprimée(s)")
    return backup_path


def delete_grub_default_backup(backup_path: str, *, path: str = GRUB_DEFAULT_PATH) -> None:
    """Supprime un fichier de sauvegarde de `/etc/default/grub`.

    Par sécurité, on n'autorise la suppression que si `backup_path` commence par
    `<path>.backup` ou est le backup initial.
    """
    if os.path.abspath(backup_path) == os.path.abspath(path):
        raise ValueError("Refus de supprimer le fichier canonique")

    allowed_prefix = f"{path}.backup"
    initial_backup = f"{path}_backup.initial.tar.gz"

    if not backup_path.startswith(allowed_prefix) and backup_path != initial_backup:
        raise ValueError("Chemin de sauvegarde invalide")

    os.remove(backup_path)


def restore_grub_default_backup(backup_path: str, target_path: str = GRUB_DEFAULT_PATH) -> None:
    """Restaure une sauvegarde GRUB complète au format tar.gz.

    Extrait et restaure :
    - /etc/default/grub
    - /etc/grub.d/ (tous les scripts)
    - /boot/grub/grub.cfg

    Args:
        backup_path: Chemin vers l'archive tar.gz à restaurer.
        target_path: Chemin de destination pour /etc/default/grub.

    Raises:
        FileNotFoundError: si l'archive n'existe pas.
        tarfile.TarError: si l'archive est corrompue.
        OSError: si la restauration échoue.
    """
    logger.info(f"[restore_grub_default_backup] Restauration depuis {backup_path}")

    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Archive de sauvegarde introuvable: {backup_path}")

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            members = tar.getmembers()
            logger.debug(f"[restore_grub_default_backup] Archive contient {len(members)} fichiers")

            for member in members:
                if member.name == "default_grub":
                    # Restaurer /etc/default/grub
                    tar.extract(member, path="/tmp", filter="data")
                    shutil.copy2("/tmp/default_grub", target_path)
                    os.remove("/tmp/default_grub")
                    logger.debug(f"[restore_grub_default_backup] Restauré: {target_path}")

                elif member.name.startswith("grub.d/"):
                    # Restaurer scripts /etc/grub.d/
                    script_name = member.name.split("/", 1)[1]
                    tar.extract(member, path="/tmp", filter="data")
                    dest_path = f"/etc/grub.d/{script_name}"
                    shutil.copy2(f"/tmp/{member.name}", dest_path)
                    os.remove(f"/tmp/{member.name}")
                    logger.debug(f"[restore_grub_default_backup] Restauré: {dest_path}")

                elif member.name.startswith("grub.cfg_"):
                    # Restaurer grub.cfg
                    grub_type = member.name.split("_")[1]  # "grub" ou "grub2"
                    tar.extract(member, path="/tmp", filter="data")
                    dest_path = f"/boot/{grub_type}/grub.cfg"
                    shutil.copy2(f"/tmp/{member.name}", dest_path)
                    os.remove(f"/tmp/{member.name}")
                    logger.debug(f"[restore_grub_default_backup] Restauré: {dest_path}")

            # Nettoyer le répertoire temporaire
            if os.path.exists("/tmp/grub.d"):
                shutil.rmtree("/tmp/grub.d")

        logger.success(f"[restore_grub_default_backup] Restauration réussie depuis {backup_path}")

    except (tarfile.TarError, OSError) as e:
        logger.error(f"[restore_grub_default_backup] ERREUR: {e}")
        raise OSError(f"Échec de la restauration: {e}") from e


def _best_fallback_for_missing_config(path: str) -> str | None:
    """Trouve un fichier de secours si `path` n'existe pas.

    Certains systèmes/outils peuvent déplacer ou supprimer `/etc/default/grub`
    tout en laissant des backups (ex: `grub.backup.current`).

    Returns:
        Chemin du fallback le plus pertinent (le plus récent), ou None.
    """
    candidates: list[str] = []

    # Format rencontré sur ton système: grub.backup.current
    candidates.append(f"{path}.backup.current")

    # Format utilisé par notre propre writer: grub.backup
    candidates.append(f"{path}.backup")

    # Variantes historisées
    candidates.extend(sorted(glob(f"{path}.backup.*")))
    candidates.extend(sorted(glob(f"{path}.backup*")))

    existing = [p for p in candidates if p != path and os.path.isfile(p)]
    if not existing:
        return None

    # Prend le plus récent.
    return max(existing, key=os.path.getmtime)


def parse_grub_default(text: str) -> dict[str, str]:
    """Parse le contenu brut de `/etc/default/grub` en dictionnaire `KEY -> VALUE`."""
    logger.debug(f"[parse_grub_default] Parsing {len(text)} caractères")
    config: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        if key:
            config[key] = value
    logger.debug(f"[parse_grub_default] Succès - {len(config)} clés extraites")
    return config


def format_grub_default(config: dict[str, str], backup_path: str) -> str:
    """Format a configuration dict as `/etc/default/grub`.

    Args:
        config: Paires clé/valeur à écrire.
        backup_path: Chemin du fichier de sauvegarde (inclus dans l'en-tête).

    Returns:
        Le texte prêt à écrire dans le fichier.
    """
    lines: list[str] = [
        "# Configuration GRUB modifiée par GRUB Configuration Manager",
        f"# Sauvegarde: {backup_path}",
        "",
    ]
    for key, value in config.items():
        needs_quotes = any(ch.isspace() for ch in value) or any(c in value for c in ("$", "`", '"', "'"))
        if needs_quotes:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}="{escaped}"')
        else:
            lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def read_grub_default(path: str = GRUB_DEFAULT_PATH) -> dict[str, str]:
    """Lit `/etc/default/grub` et renvoie un dictionnaire de configuration."""
    logger.debug(f"[read_grub_default] Lecture {path}")
    if not os.path.exists(path):
        logger.debug(f"[read_grub_default] {path} n'existe pas, recherche fallback")
        fallback = _best_fallback_for_missing_config(path)
        if fallback is None:
            logger.error("[read_grub_default] ERREUR: Fichier et fallback introuvables")
            raise GrubConfigError(f"Fichier de configuration introuvable: {path}")

        logger.warning(f"[read_grub_default] Configuration absente: {path} (fallback: {fallback})")

        # Si possible, on restaure le chemin canonique (utile pour les writes).
        try:
            shutil.copy2(fallback, path)
            logger.info(f"Restauration: {fallback} -> {path}")
        except OSError as e:
            # Best-effort: on lira directement le fallback.
            logger.warning(
                f"[read_grub_default] Impossible de restaurer {path} depuis {fallback} - lecture directe: {e}"
            )
            path = fallback

    logger.debug(f"[read_grub_default] Ouverture fichier: {path}")
    with open(path, encoding="utf-8", errors="replace") as f:
        config = parse_grub_default(f.read())
    logger.success(f"[read_grub_default] Succès - {len(config)} clés lues")
    return config


def write_grub_default(config: dict[str, str], path: str = GRUB_DEFAULT_PATH) -> str:
    """Écrit /etc/default/grub et renvoie le chemin du backup créé."""
    logger.debug(f"[write_grub_default] Écriture {len(config)} clés dans {path}")
    backup_path = path + ".backup"
    try:
        logger.info(f"Sauvegarde {path} -> {backup_path}")
        shutil.copy2(path, backup_path)
        logger.debug("[write_grub_default] Backup créé")
    except OSError as e:
        logger.error(f"[write_grub_default] ERREUR: Impossible de créer le backup - {e}")
        raise GrubBackupError(f"Impossible de créer le backup: {e}") from e
    try:
        logger.info(f"Écriture configuration GRUB: {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_grub_default(config, backup_path))
        logger.success(f"[write_grub_default] Succès - {len(config)} clés écrites")
    except OSError as e:
        logger.error(f"[write_grub_default] ERREUR: Écriture échouée - {e}")
        raise GrubConfigError(f"Écriture échouée: {e}") from e
    return backup_path
