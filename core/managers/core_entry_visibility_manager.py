"""Gestion de la visibilité des entrées GRUB (masquer/démasquer).

Approche:
- On persiste une liste d'IDs d'entrées (menuentry id) à masquer.
- Lors de l'application (après `update-grub`), on post-traite `grub.cfg` en
  supprimant les blocs `menuentry { ... }` correspondants.

Note: `grub.cfg` est généré; cette étape doit être rejouée après chaque
`update-grub`.
"""

from __future__ import annotations

import json
import os
import shutil

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATHS, discover_grub_cfg_paths
from ..core_exceptions import GrubConfigError, GrubValidationError
from ..io.grub_parsing_utils import extract_menuentry_id, extract_menuentry_title

HIDDEN_ENTRIES_PATH = "/etc/grub_manager/hidden_entries.json"


def load_hidden_entry_ids(path: str = HIDDEN_ENTRIES_PATH) -> set[str]:
    """Load hidden entry IDs from JSON file."""
    logger.debug(f"[load_hidden_entry_ids] Chargement de {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            ids = {str(x) for x in data if str(x).strip()}
            logger.debug(f"[load_hidden_entry_ids] Succès - {len(ids)} entrées masquées")
            return ids
    except FileNotFoundError:
        logger.debug(f"[load_hidden_entry_ids] Fichier non trouvé: {path}")
        return set()
    except json.JSONDecodeError as e:
        logger.warning(f"[load_hidden_entry_ids] Erreur JSON: {e}")
        return set()
    except OSError as e:
        logger.warning(f"[load_hidden_entry_ids] ERREUR de lecture: {e}")
        return set()
    return set()


def save_hidden_entry_ids(ids: set[str], path: str = HIDDEN_ENTRIES_PATH) -> None:
    """Persist hidden entry IDs to JSON file (atomic replace)."""
    logger.debug(f"[save_hidden_entry_ids] Enregistrement de {len(ids)} entrées masquées")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f, indent=2)
        os.replace(tmp, path)
        logger.success(f"[save_hidden_entry_ids] Succès - {len(ids)} entrées sauvegardées")
    except OSError as e:
        logger.warning(f"[save_hidden_entry_ids] ERREUR: Impossible d'enregistrer les entrées masquées: {e}")


def find_grub_cfg_path() -> str | None:
    """Return the first existing grub.cfg path among known candidates."""
    for p in discover_grub_cfg_paths():
        if os.path.exists(p):
            return p
    return None


def _validate_masking_safety(lines: list[str], hidden_ids: set[str]) -> None:
    """Vérifie qu'il restera au moins une entrée visible après masquage."""
    total_entries = sum(1 for line in lines if line.lstrip().startswith("menuentry"))
    would_mask = sum(
        1 for line in lines if line.lstrip().startswith("menuentry") and extract_menuentry_id(line) in hidden_ids
    )

    remaining = total_entries - would_mask
    logger.debug(
        f"[apply_hidden_entries_to_grub_cfg] Total={total_entries}, À masquer={would_mask}, Restera={remaining}"
    )

    if remaining < 1:
        logger.error(
            f"[apply_hidden_entries_to_grub_cfg] ERREUR: PROTECTION - Masquage interdit ({would_mask}/{total_entries})"
        )
        raise GrubValidationError(
            f"PROTECTION: Impossible de masquer {would_mask} entrées sur {total_entries}. "
            f"Au moins 1 entrée doit rester visible pour éviter un système non-bootable."
        )

    if remaining < 2:
        logger.warning(
            f"[apply_hidden_entries_to_grub_cfg] Attention: seulement {remaining} entrée(s) restera(ont) visible(s)"
        )


def _process_lines_for_masking(lines: list[str], hidden_ids: set[str]) -> tuple[list[str], int]:
    """Traite les lignes pour masquer les entrées demandées."""
    out: list[str] = []
    brace_depth = 0
    skipping = False
    skip_start_depth = 0
    masked_count = 0

    for line in lines:
        opens = line.count("{")
        closes = line.count("}")

        if not skipping:
            if line.lstrip().startswith("menuentry"):
                mid = extract_menuentry_id(line)
                if mid and mid in hidden_ids:
                    title = extract_menuentry_title(line)
                    logger.debug(f"[apply_hidden_entries_to_grub_cfg] Masquage: id={mid}, title={title}")
                    out.append(f"### GRUB_MANAGER_HIDDEN id={mid} title={title}")
                    skipping = True
                    skip_start_depth = brace_depth
                    masked_count += 1
                    brace_depth += opens - closes
                    continue

            out.append(line)
            brace_depth += opens - closes
            continue

        # Skipping branch: ne recopie pas les lignes du bloc
        brace_depth += opens - closes
        if brace_depth <= skip_start_depth:
            skipping = False

    return out, masked_count


def apply_hidden_entries_to_grub_cfg(
    hidden_ids: set[str],
    *,
    grub_cfg_path: str | None = None,
) -> tuple[str, int]:
    """Applique le masquage d'entrées dans `grub.cfg`.

    Returns:
        (chemin_utilisé, nombre_d'entrées_masquées)

    Raises:
        FileNotFoundError si grub.cfg est introuvable.
        GrubConfigError si la lecture/écriture échoue.
        GrubValidationError si le masquage ne laisserait aucune entrée visible.
    """
    logger.debug(f"[apply_hidden_entries_to_grub_cfg] Début - {len(hidden_ids)} entrées à masquer")
    if not hidden_ids:
        used = grub_cfg_path or find_grub_cfg_path() or GRUB_CFG_PATHS[0]
        logger.debug("[apply_hidden_entries_to_grub_cfg] Aucune entrée à masquer")
        return used, 0

    used_path = grub_cfg_path or find_grub_cfg_path()
    if not used_path:
        logger.error("[apply_hidden_entries_to_grub_cfg] ERREUR: grub.cfg introuvable")
        raise GrubConfigError("grub.cfg introuvable")

    logger.debug(f"[apply_hidden_entries_to_grub_cfg] Utilisation: {used_path}")
    try:
        with open(used_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        raise GrubConfigError(f"Impossible de lire grub.cfg: {e}") from e

    _validate_masking_safety(lines, hidden_ids)

    out, masked_count = _process_lines_for_masking(lines, hidden_ids)

    new_text = "\n".join(out) + "\n"
    old_text = "\n".join(lines) + "\n"
    if new_text == old_text:
        logger.debug("[apply_hidden_entries_to_grub_cfg] Aucune modification nécessaire")
        return used_path, 0

    # Best-effort backp (même fichier): un seul niveau.
    try:
        shutil.copy2(used_path, used_path + ".grub_manager.bak")
        logger.debug("[apply_hidden_entries_to_grub_cfg] Backup créé")
    except OSError as e:
        logger.warning(f"[apply_hidden_entries_to_grub_cfg] Impossible de créer le backup: {e}")

    try:
        with open(used_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except OSError as e:
        raise GrubConfigError(f"Impossible d'écrire grub.cfg: {e}") from e

    logger.success(f"[apply_hidden_entries_to_grub_cfg] Succès - {masked_count} entrée(s) masquée(s)")
    return used_path, masked_count
