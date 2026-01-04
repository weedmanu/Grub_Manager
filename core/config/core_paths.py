"""Chemins système GRUB.

Module séparé pour éviter les dépendances circulaires et clarifier les responsabilités.
"""

from __future__ import annotations

from glob import glob
from pathlib import Path
from typing import Final

GRUB_DEFAULT_PATH: Final[str] = "/etc/default/grub"

# Certains systèmes utilisent /boot/grub2/grub.cfg.
GRUB_CFG_PATHS: Final[list[str]] = ["/boot/grub/grub.cfg", "/boot/grub2/grub.cfg"]
GRUB_CFG_PATH: Final[str] = GRUB_CFG_PATHS[0]

# Répertoires GRUB
GRUB_THEMES_DIR: Final[str] = "/boot/grub/themes"
GRUB_THEMES_DIRS: Final[list[str]] = [
    "/boot/grub/themes",
    "/boot/grub2/themes",
    "/usr/share/grub/themes",
]


def get_grub_themes_dir() -> Path:
    """Retourne le premier répertoire des thèmes GRUB qui existe.

    Returns:
        Path vers le répertoire des thèmes
    """
    for theme_dir in GRUB_THEMES_DIRS:
        path = Path(theme_dir)
        if path.exists():
            return path
    # Retour au chemin par défaut même s'il n'existe pas
    return Path(GRUB_THEMES_DIR)


def get_all_grub_themes_dirs() -> list[Path]:
    """Retourne tous les répertoires de thèmes GRUB existants.

    Returns:
        Liste des chemins vers les répertoires des thèmes
    """
    return [Path(d) for d in GRUB_THEMES_DIRS if Path(d).exists()]


def discover_grub_cfg_paths() -> list[str]:
    """Découvre tous les chemins grub.cfg candidats (standards + EFI).

    Returns:
        Liste dédoublonnée des chemins potentiels vers grub.cfg
    """
    candidates = list(GRUB_CFG_PATHS)
    efi_paths = sorted(glob("/boot/efi/EFI/*/grub.cfg"))

    # Dédoublonnage préservant l'ordre
    seen = set()
    result = []
    for p in [*candidates, *efi_paths]:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result
