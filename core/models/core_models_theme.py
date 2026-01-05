"""Modèles de données pour les thèmes GRUB."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ThemeColors:
    """Couleurs du thème GRUB."""

    # Couleurs du texte
    title_color: str = "#FFFFFF"
    desktop_color: str = "#000000"

    # Couleurs du menu
    menu_normal_fg: str = "white"
    menu_normal_bg: str = "black"
    menu_highlight_fg: str = "black"
    menu_highlight_bg: str = "light-gray"


@dataclass
class ThemeFonts:
    """Polices du thème GRUB."""

    title_font: str = "DejaVu Sans Bold 16"
    message_font: str = "DejaVu Sans Regular 12"
    terminal_font: str = "DejaVu Sans Mono Regular 12"


@dataclass
class ThemeLayout:
    """Mise en page du thème GRUB."""

    # pylint: disable=too-many-instance-attributes

    # Position et taille du menu
    menu_left: str = "20%"
    menu_top: str = "25%"
    menu_width: str = "60%"
    menu_height: str = "50%"

    # Taille des éléments du menu
    item_height: int = 32
    item_padding: int = 8
    item_icon_space: int = 12
    item_spacing: int = 4

    # Icônes
    icon_width: int = 32
    icon_height: int = 32

    # Terminal
    terminal_left: str = "10%"
    terminal_top: str = "10%"
    terminal_width: str = "80%"
    terminal_height: str = "80%"

    # Barre de progression
    progress_left: str = "20%"
    progress_top: str = "80%"
    progress_width: str = "60%"
    progress_height: int = 24


@dataclass
class ThemeImage:
    """Images et arrière-plan du thème."""

    desktop_image: str = ""
    desktop_image_scale_method: Literal["stretch", "crop", "padding", "fitwidth", "fitheight"] = "stretch"
    desktop_image_h_align: Literal["left", "center", "right"] = "center"
    desktop_image_v_align: Literal["top", "center", "bottom"] = "center"


@dataclass
class GrubTheme:
    """Définition complète d'un thème GRUB."""

    # pylint: disable=too-many-instance-attributes

    name: str
    colors: ThemeColors = field(default_factory=ThemeColors)
    fonts: ThemeFonts = field(default_factory=ThemeFonts)
    layout: ThemeLayout = field(default_factory=ThemeLayout)
    image: ThemeImage = field(default_factory=ThemeImage)

    # Options avancées d'affichage
    show_boot_menu: bool = True
    show_progress_bar: bool = True
    show_timeout_message: bool = True
    show_scrollbar: bool = True

    # Titre personnalisé
    title_text: str = ""

    # ========== Paramètres GRUB ==========
    # Tous les paramètres GRUB sont maintenant dans le thème

    # Comportement du menu
    grub_default: str = "0"  # Entrée par défaut
    grub_timeout: int = 5  # Délai d'attente en secondes
    grub_timeout_style: str = "menu"  # menu, countdown, hidden
    grub_recordfail_timeout: int | None = None  # Timeout après échec

    # Affichage graphique
    grub_gfxmode: str = "auto"  # Résolution du menu
    grub_gfxpayload_linux: str = "keep"  # Résolution du kernel
    grub_terminal_output: str = "gfxterm"  # Type de terminal
    grub_terminal_input: str = "console"  # Type d'entrée
    grub_disable_linux_uuid: bool = False  # Utiliser /dev/sdX au lieu d'UUID

    # Paramètres du kernel
    grub_cmdline_linux: str = ""  # Paramètres pour tous les modes
    grub_cmdline_linux_default: str = "quiet splash"  # Paramètres pour le mode normal

    # Options de démarrage
    grub_disable_recovery: bool = False  # Masquer le mode récupération
    grub_disable_os_prober: bool = False  # Désactiver la détection d'autres OS
    grub_disable_submenu: bool = False  # Désactiver les sous-menus

    # Sécurité et performance
    grub_savedefault: bool = False  # Mémoriser la dernière entrée
    grub_hidden_timeout_quiet: bool = False  # Mode silencieux
    grub_init_tune: str = ""  # Mélodie au démarrage
    grub_preload_modules: str = ""  # Modules à précharger

    # Distribteur et titre
    grub_distributor: str = "`lsb_release -i -s 2> /dev/null || echo Debian`"

    # Visibilité des entrées (pour gestion des entrées)
    hidden_entries: list[str] = field(default_factory=list)  # IDs des entrées masquées


def create_custom_theme(
    name: str,
    *,
    title_color: str = "#FFFFFF",
    background_color: str = "#000000",
    menu_fg: str = "white",
    menu_bg: str = "black",
    highlight_fg: str = "black",
    highlight_bg: str = "light-gray",
    background_image: str = "",
) -> GrubTheme:
    """Crée un thème personnalisé avec des paramètres de base.

    Args:
        name: Nom du thème
        title_color: Couleur du titre
        background_color: Couleur de fond (si pas d'image)
        menu_fg: Couleur du texte du menu
        menu_bg: Couleur de fond du menu
        highlight_fg: Couleur du texte sélectionné
        highlight_bg: Couleur de fond de la sélection
        background_image: Chemin vers une image de fond (optionnel)

    Returns:
        Thème GRUB personnalisé
    """
    # pylint: disable=too-many-arguments
    return GrubTheme(
        name=name,
        colors=ThemeColors(
            title_color=title_color,
            desktop_color=background_color,
            menu_normal_fg=menu_fg,
            menu_normal_bg=menu_bg,
            menu_highlight_fg=highlight_fg,
            menu_highlight_bg=highlight_bg,
        ),
        image=ThemeImage(
            desktop_image=background_image,
            desktop_image_scale_method="stretch",
        ),
    )
