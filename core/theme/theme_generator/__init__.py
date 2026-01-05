"""Génération de thèmes GRUB (theme.txt).

Ce package contient le générateur, découpé en modules simples (configs, palettes,
templates, validation) afin de rester SOLID et testable.

API publique: importer depuis `core.theme.theme_generator`.
"""

from .core_theme_generator import (
    ColorPaletteFactory,
    ColorScheme,
    ThemeGenerator,
    ThemeResolution,
    ThemeResolutionHelper,
    ThemeTemplateBuilder,
    ThemeValidator,
)
from .core_theme_generator_models import (
    BootMenuConfig,
    ColorPalette,
    InfoImageConfig,
    ItemConfig,
    ResolutionConfig,
    TerminalConfig,
)

_EXPORTS: dict[str, object] = {
    "BootMenuConfig": BootMenuConfig,
    "ColorPalette": ColorPalette,
    "ColorPaletteFactory": ColorPaletteFactory,
    "ColorScheme": ColorScheme,
    "InfoImageConfig": InfoImageConfig,
    "ItemConfig": ItemConfig,
    "ResolutionConfig": ResolutionConfig,
    "TerminalConfig": TerminalConfig,
    "ThemeGenerator": ThemeGenerator,
    "ThemeResolution": ThemeResolution,
    "ThemeResolutionHelper": ThemeResolutionHelper,
    "ThemeTemplateBuilder": ThemeTemplateBuilder,
    "ThemeValidator": ThemeValidator,
}

__all__ = list(_EXPORTS)
