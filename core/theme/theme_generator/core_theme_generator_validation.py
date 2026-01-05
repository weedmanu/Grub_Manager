"""Validation de contenu theme.txt."""

from __future__ import annotations

import logging
import re
from typing import ClassVar

logger = logging.getLogger(__name__)


class ThemeValidator:
    """Valide la structure et certaines propriétés du theme.txt."""

    REQUIRED_FIELDS: ClassVar[set[str]] = {
        "desktop-image",
        "terminal-font",
        "boot_menu",
    }

    VALID_COLOR_PATTERNS: ClassVar[list[str]] = [
        r"^#[0-9a-fA-F]{6}$",
        r"^\d+,\s*\d+,\s*\d+$",
    ]

    @staticmethod
    def validate_theme_file(content: str) -> tuple[bool, list[str]]:
        """Valide le contenu complet d'un theme.txt."""
        errors: list[str] = []

        content_lower = content.lower()
        for field_name in ThemeValidator.REQUIRED_FIELDS:
            if field_name.lower() not in content_lower:
                errors.append(f"Missing required component: {field_name}")

        if "+ boot_menu {" not in content:
            errors.append("boot_menu component not properly structured")

        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            errors.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

        logger.info("Theme validation: %s errors found", len(errors))
        return len(errors) == 0, errors

    @staticmethod
    def validate_color(color_str: str) -> bool:
        """Valide le format d'une couleur."""
        for pattern in ThemeValidator.VALID_COLOR_PATTERNS:
            if re.match(pattern, color_str):
                return True

        svg_colors = {"black", "white", "red", "green", "blue", "gray", "yellow"}
        return color_str.lower() in svg_colors
