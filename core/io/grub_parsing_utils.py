"""Utilitaires de parsing pour GRUB.

Ce module centralise les expressions régulières et les fonctions de parsing
réutilisées dans plusieurs parties de l'application pour respecter le principe DRY.
"""

from __future__ import annotations

import re
from typing import Final

# Regex pour extraire l'ID d'une entrée de menu
# Cas 1: --id foo / --id=foo / --id 'foo'
_MENUENTRY_ID_RE: Final = re.compile(r"\s--id(?:=|\s+)(['\"]?)([^'\"\s]+)\1")
# Cas 2: $menuentry_id_option 'foo'
_MENUENTRY_DYNAMIC_ID_RE: Final = re.compile(r"\$\{?menuentry_id_option\}?\s+['\"]([^'\"]+)['\"]")

# Regex pour extraire le titre d'une entrée de menu
_MENUENTRY_TITLE_RE: Final = re.compile(r"^\s*menuentry\b.*?['\"]([^'\"]+)['\"]")


def extract_menuentry_id(line: str) -> str:
    """Extrait l'ID d'une ligne menuentry GRUB.

    Gère 2 formats:
    - --id=foo ou --id 'foo'
    - $menuentry_id_option 'foo'

    Args:
        line: La ligne contenant la définition du menuentry

    Returns:
        L'ID extrait ou une chaîne vide si non trouvé
    """
    m = _MENUENTRY_ID_RE.search(line)
    if m:
        return m.group(2)
    m = _MENUENTRY_DYNAMIC_ID_RE.search(line)
    if m:
        return m.group(1)
    return ""


def extract_menuentry_title(line: str) -> str:
    """Extrait le titre d'une ligne menuentry GRUB.

    Args:
        line: La ligne contenant 'menuentry ...'

    Returns:
        Le titre extrait ou une chaîne vide si non trouvé.
    """
    m = _MENUENTRY_TITLE_RE.search(line)
    if m:
        return m.group(1)
    return ""
    return ""
