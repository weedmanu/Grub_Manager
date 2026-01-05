"""Enums utilisés pour la génération de thèmes GRUB."""

from __future__ import annotations

from enum import Enum


class ThemeResolution(Enum):
    """Résolutions GRUB supportées."""

    RESOLUTION_1080P = "1080p"
    RESOLUTION_2K = "2k"
    RESOLUTION_4K = "4k"
    RESOLUTION_ULTRAWIDE = "ultrawide"
    RESOLUTION_ULTRAWIDE_2K = "ultrawide2k"
    CUSTOM = "custom"


class ColorScheme(Enum):
    """Schémas de couleurs préconfigurés."""

    DARK = "dark"
    LIGHT = "light"
    MINIMAL = "minimal"
    DRACULA = "dracula"
    NORD = "nord"
    CUSTOM = "custom"
