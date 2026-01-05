"""Modèles (DTO) pour la génération de theme.txt.

Objectif: isoler les structures de données (SOLID) et éviter des dicts libres
au niveau orchestration. Les propriétés de compatibilité permettent de garder
une API stable tout en regroupant les champs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BootMenuConfig:
    """Configuration de positionnement du menu."""

    left: str = "30%"
    top: str = "30%"
    width: str = "40%"
    height: str = "40%"


@dataclass(frozen=True)
class ItemConfig:
    """Configuration d'affichage des items."""

    font_size: int = 16
    icon_width: int = 32
    icon_height: int = 32
    icon_space: int = 20
    height: int = 36
    padding: int = 5
    spacing: int = 10


@dataclass(frozen=True)
class TerminalConfig:
    """Configuration du terminal."""

    font_size: int = 14


@dataclass(frozen=True)
class InfoImageConfig:
    """Configuration de l'image d'information/footer."""

    height: int = 42


@dataclass(frozen=True)
class ResolutionConfig:
    """Configuration dépendante de la résolution."""

    width: int
    height: int
    boot_menu: BootMenuConfig = field(default_factory=BootMenuConfig)
    item: ItemConfig = field(default_factory=ItemConfig)
    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    info_image: InfoImageConfig = field(default_factory=InfoImageConfig)


@dataclass
class ColorPalette:
    """Palette de couleurs d'un thème."""

    name: str
    background_color: str
    item_color: str
    selected_item_color: str
    label_color: str
    terminal_foreground: str | None = None
    terminal_background: str | None = None
