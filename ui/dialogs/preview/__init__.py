"""Modules pour le preview GRUB - architecture modulaire SOLID.

Ce package implémente le système de prévisualisation GRUB selon les principes SOLID :
- ui_grub_preview_css : Génération CSS (Single Responsibility)
- ui_grub_preview_parsers : Parsing fichiers config GRUB (Single Responsibility)
- ui_grub_preview_data : Chargement et résolution données (Single Responsibility)
- ui_grub_preview_renderer : Rendu interface utilisateur (Single Responsibility)
- Orchestré par ui_grub_preview_dialog (Dependency Inversion Principle)
"""

from ui.dialogs.preview.ui_dialogs_preview_grub_css import (
    GrubPreviewCssGenerator,
    PreviewColors,
    PreviewFonts,
    PreviewLayout,
)
from ui.dialogs.preview.ui_dialogs_preview_grub_data import GrubPreviewDataLoader
from ui.dialogs.preview.ui_dialogs_preview_grub_parsers import (
    GrubConfigParser,
    SystemMenuColors,
    ThemeTxtOverrides,
)
from ui.dialogs.preview.ui_dialogs_preview_grub_renderer import GrubPreviewRenderer

__all__ = [
    "GrubConfigParser",
    "GrubPreviewCssGenerator",
    "GrubPreviewDataLoader",
    "GrubPreviewRenderer",
    "PreviewColors",
    "PreviewFonts",
    "PreviewLayout",
    "SystemMenuColors",
    "ThemeTxtOverrides",
]
