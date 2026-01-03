"""Lecture/écriture de /etc/default/grub (format KEY=VALUE).

Aucune logique UI ici.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from glob import glob

from loguru import logger

from .paths import GRUB_DEFAULT_PATH


def _touch_now(path: str) -> None:
    """Force le mtime à 'maintenant' (utile car copy2 copie le mtime source)."""
    try:
        os.utime(path, None)
    except OSError:
        pass


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
    """Crée un backup *initial* de `/etc/default/grub` si absent.

    Objectif: disposer d'une copie "connue bonne" avant toute modification.
    La création est best-effort: en cas d'erreur (permissions, fichier manquant,
    FS en lecture seule), la fonction ne lève pas et renvoie None.

    Le backup initial n'est jamais écrasé.

    Returns:
        Le chemin du backup initial (existant ou créé), ou None si non disponible.
    """
    logger.debug(f"[ensure_initial_grub_default_backup] Vérification du backup initial pour {path}")
    initial_backup_path = path + ".backup.initial"
    if os.path.isfile(initial_backup_path):
        logger.debug(f"[ensure_initial_grub_default_backup] Backup initial trouvé: {initial_backup_path}")
        return initial_backup_path

    # Si le fichier canonique n'existe pas, tente d'abord une restauration
    # best-effort depuis un fallback (cf. read_grub_default).
    if not os.path.exists(path):
        try:
            logger.debug(f"[ensure_initial_grub_default_backup] {path} absent, tentative de restauration")
            _ = read_grub_default(path)
        except OSError:
            logger.warning(f"[ensure_initial_grub_default_backup] Impossible de créer un backup initial: {path} absent")
            return None

    try:
        logger.info(f"Création backup initial {path} -> {initial_backup_path}")
        shutil.copy2(path, initial_backup_path)
        logger.success("[ensure_initial_grub_default_backup] Succès")
        return initial_backup_path
    except OSError as e:
        logger.warning(f"[ensure_initial_grub_default_backup] Impossible de créer le backup initial: {e}")
        return None


def list_grub_default_backups(path: str = GRUB_DEFAULT_PATH) -> list[str]:
    """List GRUB default backups associated with `/etc/default/grub`.

    Retourne tous les fichiers qui matchent `<path>.backup*`.
    Le résultat est trié par date de modification décroissante.
    """
    candidates = [p for p in glob(f"{path}.backup*") if os.path.isfile(p) and p != path]
    # Tri stable: plus récent d'abord, puis par chemin.
    candidates.sort(key=lambda p: (-os.path.getmtime(p), p))
    return candidates


def create_grub_default_backup(path: str = GRUB_DEFAULT_PATH) -> str:
    """Crée une nouvelle sauvegarde horodatée de `/etc/default/grub`.

    Le backup créé a la forme `<path>.backup.manual.YYYYMMDD-HHMMSS`.

    Returns:
        Le chemin du backup créé.

    Raises:
        OSError: si la copie échoue.
        FileNotFoundError: si aucune source (fichier ou fallback) n'est trouvée.
    """
    logger.debug(f"[create_grub_default_backup] Création d'une nouvelle sauvegarde pour {path}")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_backup_path = f"{path}.backup.manual.{ts}"
    backup_path = base_backup_path

    # Assure un nom unique.
    suffix = 1
    while os.path.exists(backup_path):
        backup_path = f"{base_backup_path}.{suffix}"
        suffix += 1

    source_path = path
    if not os.path.exists(source_path):
        logger.debug(f"[create_grub_default_backup] {path} absent, recherche de fallback")
        fallback = _best_fallback_for_missing_config(path)
        if fallback is None:
            logger.error("[create_grub_default_backup] ERREUR: Aucune source trouvée")
            raise FileNotFoundError(path)
        source_path = fallback
        logger.debug(f"[create_grub_default_backup] Fallback trouvé: {source_path}")

    logger.info(f"Création sauvegarde manuelle {source_path} -> {backup_path}")
    shutil.copy2(source_path, backup_path)
    _touch_now(backup_path)
    logger.success(f"[create_grub_default_backup] Succès - {backup_path}")

    # Roulement: ne garde que les 3 plus récentes sauvegardes manuelles.
    deleted = _prune_manual_backups(path, keep=3)
    if deleted:
        logger.info(f"[create_grub_default_backup] Nettoyage: {len(deleted)} anciennes sauvegarde(s) supprimée(s)")
    return backup_path


def delete_grub_default_backup(backup_path: str, *, path: str = GRUB_DEFAULT_PATH) -> None:
    """Supprime un fichier de sauvegarde de `/etc/default/grub`.

    Par sécurité, on n'autorise la suppression que si `backup_path` commence par
    `<path>.backup`.
    """
    allowed_prefix = f"{path}.backup"
    if not backup_path.startswith(allowed_prefix):
        raise ValueError("Chemin de sauvegarde invalide")
    if os.path.abspath(backup_path) == os.path.abspath(path):
        raise ValueError("Refus de supprimer le fichier canonique")
    os.remove(backup_path)


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
            raise FileNotFoundError(path)

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
        raise
    try:
        logger.info(f"Écriture configuration GRUB: {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_grub_default(config, backup_path))
        logger.success(f"[write_grub_default] Succès - {len(config)} clés écrites")
    except OSError as e:
        logger.error(f"[write_grub_default] ERREUR: Écriture échouée - {e}")
        raise
    return backup_path
