"""Générateur de thèmes GRUB personnalisés.

Basé sur la documentation officielle GRUB 2.12 Theme File Format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger


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


class ThemeGenerator:
    """Générateur de fichiers de configuration de thème GRUB."""

    @staticmethod
    def export_grub_config(theme: GrubTheme) -> dict[str, str]:
        """Exporte tous les paramètres GRUB du thème.

        Args:
            theme: Thème contenant la configuration GRUB

        Returns:
            Dictionnaire des paramètres GRUB (clé=valeur)
        """
        logger.info(f"[ThemeGenerator] Export de la configuration GRUB pour '{theme.name}'")

        config = {}

        # Paramètres de base
        config["GRUB_DEFAULT"] = theme.grub_default
        config["GRUB_TIMEOUT"] = str(theme.grub_timeout)
        config["GRUB_TIMEOUT_STYLE"] = theme.grub_timeout_style

        if theme.grub_recordfail_timeout is not None:
            config["GRUB_RECORDFAIL_TIMEOUT"] = str(theme.grub_recordfail_timeout)

        # Affichage
        config["GRUB_GFXMODE"] = theme.grub_gfxmode
        config["GRUB_GFXPAYLOAD_LINUX"] = theme.grub_gfxpayload_linux
        config["GRUB_TERMINAL_OUTPUT"] = theme.grub_terminal_output
        config["GRUB_TERMINAL_INPUT"] = theme.grub_terminal_input

        # Paramètres du kernel
        if theme.grub_cmdline_linux:
            config["GRUB_CMDLINE_LINUX"] = theme.grub_cmdline_linux
        config["GRUB_CMDLINE_LINUX_DEFAULT"] = theme.grub_cmdline_linux_default

        # Options booléennes
        if theme.grub_disable_recovery:
            config["GRUB_DISABLE_RECOVERY"] = "true"

        if theme.grub_disable_os_prober:
            config["GRUB_DISABLE_OS_PROBER"] = "true"

        if theme.grub_disable_submenu:
            config["GRUB_DISABLE_SUBMENU"] = "y"

        if theme.grub_disable_linux_uuid:
            config["GRUB_DISABLE_LINUX_UUID"] = "true"

        if theme.grub_savedefault:
            config["GRUB_SAVEDEFAULT"] = "true"

        # Options avancées
        if theme.grub_hidden_timeout_quiet:
            config["GRUB_HIDDEN_TIMEOUT_QUIET"] = "true"

        if theme.grub_init_tune:
            config["GRUB_INIT_TUNE"] = theme.grub_init_tune

        if theme.grub_preload_modules:
            config["GRUB_PRELOAD_MODULES"] = theme.grub_preload_modules

        config["GRUB_DISTRIBUTOR"] = theme.grub_distributor

        # Thème visuel (chemin vers theme.txt)
        themes_dir = Path("/boot/grub/themes")
        theme_file = themes_dir / theme.name / "theme.txt"
        config["GRUB_THEME"] = str(theme_file)

        logger.success(f"[ThemeGenerator] {len(config)} paramètres GRUB exportés")
        return config

    @staticmethod
    def generate_theme_txt(theme: GrubTheme) -> str:
        """Génère le contenu du fichier theme.txt.

        Args:
            theme: Configuration du thème

        Returns:
            Contenu du fichier theme.txt au format GRUB
        """
        logger.info(f"[ThemeGenerator] Génération du thème '{theme.name}'")

        lines = [
            f"# GRUB Theme: {theme.name}",
            "# Generated by GRUB Configuration Manager",
            "",
            "# Global Properties",
            f'title-text: "{theme.title_text}"',
            f'title-font: "{theme.fonts.title_font}"',
            f'title-color: "{theme.colors.title_color}"',
            "",
        ]

        # Image de fond
        if theme.image.desktop_image:
            lines.extend(
                [
                    "# Desktop Image",
                    f'desktop-image: "{theme.image.desktop_image}"',
                    f'desktop-image-scale-method: "{theme.image.desktop_image_scale_method}"',
                    f'desktop-image-h-align: "{theme.image.desktop_image_h_align}"',
                    f'desktop-image-v-align: "{theme.image.desktop_image_v_align}"',
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "# Desktop Color",
                    f'desktop-color: "{theme.colors.desktop_color}"',
                    "",
                ]
            )

        # Terminal
        lines.extend(
            [
                "# Terminal",
                'terminal-box: "terminal_*.png"',
                f"terminal-left: {theme.layout.terminal_left}",
                f"terminal-top: {theme.layout.terminal_top}",
                f"terminal-width: {theme.layout.terminal_width}",
                f"terminal-height: {theme.layout.terminal_height}",
                f'terminal-font: "{theme.fonts.terminal_font}"',
                "",
            ]
        )

        # Boot Menu
        if theme.show_boot_menu:
            lines.extend(
                [
                    "# Boot Menu",
                    "+ boot_menu {",
                    f"  left = {theme.layout.menu_left}",
                    f"  top = {theme.layout.menu_top}",
                    f"  width = {theme.layout.menu_width}",
                    f"  height = {theme.layout.menu_height}",
                    "",
                    f'  item_font = "{theme.fonts.message_font}"',
                    f'  item_color = "{theme.colors.menu_normal_fg}"',
                    f'  selected_item_color = "{theme.colors.menu_highlight_fg}"',
                    "",
                    f"  item_height = {theme.layout.item_height}",
                    f"  item_padding = {theme.layout.item_padding}",
                    f"  item_icon_space = {theme.layout.item_icon_space}",
                    f"  item_spacing = {theme.layout.item_spacing}",
                    "",
                    f"  icon_width = {theme.layout.icon_width}",
                    f"  icon_height = {theme.layout.icon_height}",
                    "",
                    '  menu_pixmap_style = "menu_*.png"',
                    '  selected_item_pixmap_style = "select_*.png"',
                    "",
                ]
            )

            # Scrollbar (optionnel)
            if theme.show_scrollbar:
                lines.extend(
                    [
                        "  scrollbar = true",
                        '  scrollbar_frame = "scrollbar_*.png"',
                        '  scrollbar_thumb = "scrollbar_thumb_*.png"',
                        "  scrollbar_width = 20",
                    ]
                )

            lines.extend(
                [
                    "}",
                    "",
                ]
            )

        # Progress Bar (timeout)
        if theme.show_progress_bar:
            lines.extend(
                [
                    "# Progress Bar",
                    "+ progress_bar {",
                    '  id = "__timeout__"',
                    f"  left = {theme.layout.progress_left}",
                    f"  top = {theme.layout.progress_top}",
                    f"  width = {theme.layout.progress_width}",
                    f"  height = {theme.layout.progress_height}",
                    "",
                    f'  fg_color = "{theme.colors.menu_highlight_bg}"',
                    f'  bg_color = "{theme.colors.menu_normal_bg}"',
                    f'  border_color = "{theme.colors.menu_normal_fg}"',
                    f'  text_color = "{theme.colors.menu_normal_fg}"',
                    "",
                    '  bar_style = "progress_frame_*.png"',
                    '  highlight_style = "progress_highlight_*.png"',
                    '  text = "@TIMEOUT_NOTIFICATION_MIDDLE@"',
                    "}",
                    "",
                ]
            )

        # Label de timeout
        if theme.show_timeout_message:
            lines.extend(
                [
                    "# Timeout Message",
                    "+ label {",
                    '  id = "__timeout__"',
                    "  left = 20%",
                    "  top = 85%",
                    "  width = 60%",
                    "  align = center",
                    "",
                    f'  font = "{theme.fonts.message_font}"',
                    f'  color = "{theme.colors.menu_normal_fg}"',
                    '  text = "@TIMEOUT_NOTIFICATION_LONG@"',
                    "}",
                    "",
                ]
            )

        result = "\n".join(lines)
        logger.success(f"[ThemeGenerator] Thème '{theme.name}' généré ({len(lines)} lignes)")
        return result

    @staticmethod
    def save_theme(theme: GrubTheme, theme_dir: Path) -> Path:
        """Sauvegarde un thème dans un répertoire.

        Args:
            theme: Configuration du thème
            theme_dir: Répertoire de destination

        Returns:
            Chemin du fichier theme.txt créé
        """
        theme_path = theme_dir / theme.name
        theme_path.mkdir(parents=True, exist_ok=True)

        theme_file = theme_path / "theme.txt"
        content = ThemeGenerator.generate_theme_txt(theme)

        theme_file.write_text(content, encoding="utf-8")
        logger.success(f"[ThemeGenerator] Thème sauvegardé: {theme_file}")

        return theme_file

    @staticmethod
    def create_default_themes() -> list[GrubTheme]:
        """Crée une collection de thèmes par défaut.

        Returns:
            Liste de thèmes prédéfinis
        """
        themes = []

        # Thème classique
        classic = GrubTheme(
            name="classic",
            colors=ThemeColors(
                title_color="#FFFFFF",
                desktop_color="#000000",
                menu_normal_fg="white",
                menu_normal_bg="black",
                menu_highlight_fg="black",
                menu_highlight_bg="light-gray",
            ),
        )
        themes.append(classic)

        # Thème sombre
        dark = GrubTheme(
            name="dark",
            colors=ThemeColors(
                title_color="#AAAAAA",
                desktop_color="#1A1A1A",
                menu_normal_fg="light-gray",
                menu_normal_bg="#2A2A2A",
                menu_highlight_fg="white",
                menu_highlight_bg="#4A4A4A",
            ),
        )
        themes.append(dark)

        # Thème bleu
        blue = GrubTheme(
            name="blue",
            colors=ThemeColors(
                title_color="#FFFFFF",
                desktop_color="#001F3F",
                menu_normal_fg="cyan",
                menu_normal_bg="blue",
                menu_highlight_fg="white",
                menu_highlight_bg="light-blue",
            ),
        )
        themes.append(blue)

        # Thème Matrix (vert)
        matrix = GrubTheme(
            name="matrix",
            colors=ThemeColors(
                title_color="#00FF00",
                desktop_color="#000000",
                menu_normal_fg="light-green",
                menu_normal_bg="black",
                menu_highlight_fg="black",
                menu_highlight_bg="light-green",
            ),
        )
        themes.append(matrix)

        logger.info(f"[ThemeGenerator] {len(themes)} thèmes par défaut créés")
        return themes


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
    """Crée un thème personnalisé avec des paramètres simples.

    Args:
        name: Nom du thème
        title_color: Couleur du titre (format #RRGGBB)
        background_color: Couleur de fond
        menu_fg: Couleur du texte du menu
        menu_bg: Couleur de fond du menu
        highlight_fg: Couleur du texte sélectionné
        highlight_bg: Couleur de fond de la sélection
        background_image: Chemin vers une image de fond (optionnel)

    Returns:
        Thème GRUB personnalisé
    """
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
