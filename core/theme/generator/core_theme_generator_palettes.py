"""Palettes de couleurs et factory."""

from __future__ import annotations

from typing import ClassVar

from .core_theme_generator_enums import ColorScheme
from .core_theme_generator_models import ColorPalette


class ColorPaletteFactory:
    """Factory pour créer/obtenir des palettes de couleurs."""

    PALETTES: ClassVar[dict[ColorScheme, ColorPalette]] = {
        ColorScheme.DARK: ColorPalette(
            name="Dark",
            background_color="#000000",
            item_color="#cccccc",
            selected_item_color="#ffffff",
            label_color="#cccccc",
        ),
        ColorScheme.LIGHT: ColorPalette(
            name="Light",
            background_color="#ffffff",
            item_color="#333333",
            selected_item_color="#000000",
            label_color="#333333",
        ),
        ColorScheme.MINIMAL: ColorPalette(
            name="Minimal",
            background_color="#1a1a1a",
            item_color="#aaaaaa",
            selected_item_color="#ffaa00",
            label_color="#aaaaaa",
        ),
        ColorScheme.DRACULA: ColorPalette(
            name="Dracula",
            background_color="#282a36",
            item_color="#f8f8f2",
            selected_item_color="#ff79c6",
            label_color="#bd93f9",
        ),
        ColorScheme.NORD: ColorPalette(
            name="Nord",
            background_color="#2e3440",
            item_color="#d8dee9",
            selected_item_color="#88c0d0",
            label_color="#81a1c1",
        ),
    }

    @staticmethod
    def get_palette(scheme: ColorScheme) -> ColorPalette:
        """Retourne la palette pour un schéma donné."""
        return ColorPaletteFactory.PALETTES.get(scheme, ColorPaletteFactory.PALETTES[ColorScheme.DARK])

    @staticmethod
    def create_custom_palette(name: str, bg: str, item: str, selected: str, label: str) -> ColorPalette:
        """Crée une palette custom (et la retourne)."""
        palette = ColorPalette(name, bg, item, selected, label)
        return palette
