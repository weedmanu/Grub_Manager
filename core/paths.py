"""Chemins système GRUB.

Module séparé pour éviter les dépendances circulaires et clarifier les responsabilités.
"""

from __future__ import annotations

from typing import Final

GRUB_DEFAULT_PATH: Final[str] = "/etc/default/grub"

# Certains systèmes utilisent /boot/grub2/grub.cfg.
GRUB_CFG_PATHS: Final[list[str]] = ["/boot/grub/grub.cfg", "/boot/grub2/grub.cfg"]
GRUB_CFG_PATH: Final[str] = GRUB_CFG_PATHS[0]
