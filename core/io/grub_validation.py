"""Validation de fichiers GRUB.

Ce module centralise la logique de validation des fichiers de configuration GRUB.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Résultat de la validation d'un fichier GRUB."""

    is_valid: bool
    error_message: str | None = None
    meaningful_lines: int = 0


def validate_grub_file(path: Path, *, min_lines: int = 1) -> ValidationResult:
    """Valide qu'un fichier GRUB contient une configuration valide.

    Args:
        path: Chemin vers le fichier à valider
        min_lines: Nombre minimum de lignes significatives attendues

    Returns:
        ValidationResult contenant le statut et les détails
    """
    if not path.exists():
        return ValidationResult(False, f"Fichier absent: {path}")

    try:
        size = path.stat().st_size
        if size == 0:
            return ValidationResult(False, "Fichier vide")

        content = path.read_text(encoding="utf-8", errors="replace")
        lines = [line for line in content.splitlines() if line.strip() and not line.startswith("#")]

        if len(lines) < min_lines:
            return ValidationResult(False, f"Trop peu de lignes ({len(lines)} < {min_lines})")

        return ValidationResult(True, meaningful_lines=len(lines))

    except OSError as e:
        return ValidationResult(False, f"Erreur de lecture: {e}")
