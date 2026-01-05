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

    @property
    def boot_menu_left(self) -> str:
        """Compat: left en pourcentage."""
        return self.boot_menu.left

    @property
    def boot_menu_top(self) -> str:
        """Compat: top en pourcentage."""
        return self.boot_menu.top

    @property
    def boot_menu_width(self) -> str:
        """Compat: width en pourcentage."""
        return self.boot_menu.width

    @property
    def boot_menu_height(self) -> str:
        """Compat: height en pourcentage."""
        return self.boot_menu.height

    @property
    def item_font_size(self) -> int:
        """Compat: taille de police des items."""
        return self.item.font_size

    @property
    def item_icon_width(self) -> int:
        """Compat: largeur d'icône."""
        return self.item.icon_width

    @property
    def item_icon_height(self) -> int:
        """Compat: hauteur d'icône."""
        return self.item.icon_height

    @property
    def item_icon_space(self) -> int:
        """Compat: espace icône-texte."""
        return self.item.icon_space

    @property
    def item_height(self) -> int:
        """Compat: hauteur d'item."""
        return self.item.height

    @property
    def item_padding(self) -> int:
        """Compat: padding vertical."""
        return self.item.padding

    @property
    def item_spacing(self) -> int:
        """Compat: spacing entre items."""
        return self.item.spacing

    @property
    def terminal_font_size(self) -> int:
        """Compat: taille de police du terminal."""
        return self.terminal.font_size

    @property
    def info_image_height(self) -> int:
        """Compat: hauteur de l'image info/footer."""
        return self.info_image.height


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
