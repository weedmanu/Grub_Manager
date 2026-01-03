"""Gestionnaire de thème actif pour l'application.

Ce module gère le thème actif qui contient toute la configuration GRUB.
Toutes les modifications de l'application passent par le thème actif.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from loguru import logger

from core.theme.core_theme_generator import (
    GrubTheme,
    ThemeGenerator,
    create_custom_theme,
)


class ActiveThemeManager:
    """Gestionnaire du thème actif de l'application avec cache."""

    ACTIVE_THEME_FILE: Final[Path] = Path.home() / ".config" / "grub_manager" / "active_theme.json"

    def __init__(self) -> None:
        """Initialise le gestionnaire de thème actif."""
        self.active_theme: GrubTheme | None = None
        self._cache_timestamp: float = 0.0
        logger.debug("[ActiveThemeManager] Gestionnaire initialisé")

    def load_active_theme(self) -> GrubTheme:
        """Charge le thème actif depuis le fichier de configuration avec cache.

        Utilise un cache basé sur le timestamp du fichier pour éviter
        les lectures disque inutiles.

        Returns:
            Thème actif (ou thème par défaut si aucun n'est défini)
        """
        # Vérifier si le cache est valide
        if self.active_theme and self._is_cache_valid():
            logger.debug("[ActiveThemeManager] Utilisation du cache")
            return self.active_theme

        logger.debug("[ActiveThemeManager] Chargement du thème depuis le disque")

        if not self.ACTIVE_THEME_FILE.exists():
            logger.warning("[ActiveThemeManager] Aucun thème actif, création du thème par défaut")
            self.active_theme = self._create_default_theme()
            self.save_active_theme()
            return self.active_theme

        try:
            with open(self.ACTIVE_THEME_FILE, encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruire le thème depuis le JSON
            self.active_theme = self._theme_from_dict(data)
            self._cache_timestamp = self.ACTIVE_THEME_FILE.stat().st_mtime
            logger.info(f"[ActiveThemeManager] Thème actif chargé: {self.active_theme.name}")
            return self.active_theme

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"[ActiveThemeManager] Erreur chargement thème actif: {e}")
            self.active_theme = self._create_default_theme()
            return self.active_theme

    def save_active_theme(self) -> None:
        """Sauvegarde le thème actif dans le fichier de configuration."""
        if not self.active_theme:
            logger.warning("[ActiveThemeManager] Aucun thème actif à sauvegarder")
            return

        logger.debug(f"[ActiveThemeManager] Sauvegarde du thème actif: {self.active_theme.name}")

        # Créer le répertoire si nécessaire
        self.ACTIVE_THEME_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Convertir le thème en dictionnaire
        data = self._theme_to_dict(self.active_theme)

        # Sauvegarder
        with open(self.ACTIVE_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Invalider le cache en mettant à jour le timestamp
        self._cache_timestamp = self.ACTIVE_THEME_FILE.stat().st_mtime
        logger.info("[ActiveThemeManager] Thème actif sauvegardé")

    def get_active_theme(self) -> GrubTheme:
        """Retourne le thème actif (charge si nécessaire).

        Returns:
            Thème actif
        """
        if self.active_theme is None:
            return self.load_active_theme()
        return self.active_theme

    def export_to_grub_config(self) -> dict[str, str]:
        """Exporte le thème actif vers les paramètres GRUB.

        Returns:
            Dictionnaire des paramètres GRUB
        """
        theme = self.get_active_theme()
        return ThemeGenerator.export_grub_config(theme)

    def _create_default_theme(self) -> GrubTheme:
        """Crée un thème par défaut.

        Returns:
            Thème par défaut
        """
        logger.info("[ActiveThemeManager] Création du thème par défaut")
        return create_custom_theme(
            name="default",
            title_color="#FFFFFF",
            background_color="#000000",
            menu_fg="white",
            menu_bg="black",
            highlight_fg="black",
            highlight_bg="light-gray",
        )

    def _is_cache_valid(self) -> bool:
        """Vérifie si le cache est toujours valide.

        Returns:
            True si le cache est valide, False sinon
        """
        if not self.ACTIVE_THEME_FILE.exists():
            return False

        try:
            current_mtime = self.ACTIVE_THEME_FILE.stat().st_mtime
            return current_mtime == self._cache_timestamp
        except OSError:
            return False

    def _theme_to_dict(self, theme: GrubTheme) -> dict:
        """Convertit un thème en dictionnaire pour JSON.

        Args:
            theme: Thème à convertir

        Returns:
            Dictionnaire JSON
        """
        return {
            "name": theme.name,
            "title_text": theme.title_text,
            # Couleurs
            "colors": {
                "title_color": theme.colors.title_color,
                "desktop_color": theme.colors.desktop_color,
                "menu_normal_fg": theme.colors.menu_normal_fg,
                "menu_normal_bg": theme.colors.menu_normal_bg,
                "menu_highlight_fg": theme.colors.menu_highlight_fg,
                "menu_highlight_bg": theme.colors.menu_highlight_bg,
            },
            # Polices
            "fonts": {
                "title_font": theme.fonts.title_font,
                "message_font": theme.fonts.message_font,
                "terminal_font": theme.fonts.terminal_font,
            },
            # Mise en page
            "layout": {
                "menu_left": theme.layout.menu_left,
                "menu_top": theme.layout.menu_top,
                "menu_width": theme.layout.menu_width,
                "menu_height": theme.layout.menu_height,
                "item_height": theme.layout.item_height,
                "item_padding": theme.layout.item_padding,
                "item_icon_space": theme.layout.item_icon_space,
                "item_spacing": theme.layout.item_spacing,
                "icon_width": theme.layout.icon_width,
                "icon_height": theme.layout.icon_height,
                "terminal_left": theme.layout.terminal_left,
                "terminal_top": theme.layout.terminal_top,
                "terminal_width": theme.layout.terminal_width,
                "terminal_height": theme.layout.terminal_height,
                "progress_left": theme.layout.progress_left,
                "progress_top": theme.layout.progress_top,
                "progress_width": theme.layout.progress_width,
                "progress_height": theme.layout.progress_height,
            },
            # Image
            "image": {
                "desktop_image": theme.image.desktop_image,
                "desktop_image_scale_method": theme.image.desktop_image_scale_method,
                "desktop_image_h_align": theme.image.desktop_image_h_align,
                "desktop_image_v_align": theme.image.desktop_image_v_align,
            },
            # Options d'affichage
            "show_boot_menu": theme.show_boot_menu,
            "show_progress_bar": theme.show_progress_bar,
            "show_timeout_message": theme.show_timeout_message,
            "show_scrollbar": theme.show_scrollbar,
            # Paramètres GRUB
            "grub_default": theme.grub_default,
            "grub_timeout": theme.grub_timeout,
            "grub_timeout_style": theme.grub_timeout_style,
            "grub_recordfail_timeout": theme.grub_recordfail_timeout,
            "grub_gfxmode": theme.grub_gfxmode,
            "grub_gfxpayload_linux": theme.grub_gfxpayload_linux,
            "grub_terminal_output": theme.grub_terminal_output,
            "grub_terminal_input": theme.grub_terminal_input,
            "grub_disable_linux_uuid": theme.grub_disable_linux_uuid,
            "grub_cmdline_linux": theme.grub_cmdline_linux,
            "grub_cmdline_linux_default": theme.grub_cmdline_linux_default,
            "grub_disable_recovery": theme.grub_disable_recovery,
            "grub_disable_os_prober": theme.grub_disable_os_prober,
            "grub_disable_submenu": theme.grub_disable_submenu,
            "grub_savedefault": theme.grub_savedefault,
            "grub_hidden_timeout_quiet": theme.grub_hidden_timeout_quiet,
            "grub_init_tune": theme.grub_init_tune,
            "grub_preload_modules": theme.grub_preload_modules,
            "grub_distributor": theme.grub_distributor,
            "hidden_entries": theme.hidden_entries,
        }

    def _theme_from_dict(self, data: dict) -> GrubTheme:
        """Reconstruit un thème depuis un dictionnaire JSON.

        Args:
            data: Dictionnaire JSON

        Returns:
            Thème reconstruit
        """
        theme = create_custom_theme(
            name=data["name"],
            title_color=data["colors"]["title_color"],
            background_color=data["colors"]["desktop_color"],
            menu_fg=data["colors"]["menu_normal_fg"],
            menu_bg=data["colors"]["menu_normal_bg"],
            highlight_fg=data["colors"]["menu_highlight_fg"],
            highlight_bg=data["colors"]["menu_highlight_bg"],
            background_image=data["image"]["desktop_image"],
        )

        # Mettre à jour tous les autres champs
        theme.title_text = data.get("title_text", "")

        # Polices
        theme.fonts.title_font = data["fonts"]["title_font"]
        theme.fonts.message_font = data["fonts"]["message_font"]
        theme.fonts.terminal_font = data["fonts"]["terminal_font"]

        # Layout
        layout = data["layout"]
        theme.layout.menu_left = layout["menu_left"]
        theme.layout.menu_top = layout["menu_top"]
        theme.layout.menu_width = layout["menu_width"]
        theme.layout.menu_height = layout["menu_height"]
        theme.layout.item_height = layout["item_height"]
        theme.layout.item_padding = layout["item_padding"]
        theme.layout.item_icon_space = layout["item_icon_space"]
        theme.layout.item_spacing = layout["item_spacing"]
        theme.layout.icon_width = layout["icon_width"]
        theme.layout.icon_height = layout["icon_height"]
        theme.layout.terminal_left = layout["terminal_left"]
        theme.layout.terminal_top = layout["terminal_top"]
        theme.layout.terminal_width = layout["terminal_width"]
        theme.layout.terminal_height = layout["terminal_height"]
        theme.layout.progress_left = layout["progress_left"]
        theme.layout.progress_top = layout["progress_top"]
        theme.layout.progress_width = layout["progress_width"]
        theme.layout.progress_height = layout["progress_height"]

        # Image
        theme.image.desktop_image_scale_method = data["image"]["desktop_image_scale_method"]
        theme.image.desktop_image_h_align = data["image"]["desktop_image_h_align"]
        theme.image.desktop_image_v_align = data["image"]["desktop_image_v_align"]

        # Options d'affichage
        theme.show_boot_menu = data["show_boot_menu"]
        theme.show_progress_bar = data["show_progress_bar"]
        theme.show_timeout_message = data["show_timeout_message"]
        theme.show_scrollbar = data.get("show_scrollbar", True)

        # Paramètres GRUB
        theme.grub_default = data["grub_default"]
        theme.grub_timeout = data["grub_timeout"]
        theme.grub_timeout_style = data["grub_timeout_style"]
        theme.grub_recordfail_timeout = data.get("grub_recordfail_timeout")
        theme.grub_gfxmode = data["grub_gfxmode"]
        theme.grub_gfxpayload_linux = data["grub_gfxpayload_linux"]
        theme.grub_terminal_output = data["grub_terminal_output"]
        theme.grub_terminal_input = data.get("grub_terminal_input", "console")
        theme.grub_disable_linux_uuid = data.get("grub_disable_linux_uuid", False)
        theme.grub_cmdline_linux = data.get("grub_cmdline_linux", "")
        theme.grub_cmdline_linux_default = data["grub_cmdline_linux_default"]
        theme.grub_disable_recovery = data.get("grub_disable_recovery", False)
        theme.grub_disable_os_prober = data.get("grub_disable_os_prober", False)
        theme.grub_disable_submenu = data.get("grub_disable_submenu", False)
        theme.grub_savedefault = data.get("grub_savedefault", False)
        theme.grub_hidden_timeout_quiet = data.get("grub_hidden_timeout_quiet", False)
        theme.grub_init_tune = data.get("grub_init_tune", "")
        theme.grub_preload_modules = data.get("grub_preload_modules", "")
        theme.grub_distributor = data.get("grub_distributor", "`lsb_release -i -s 2> /dev/null || echo Debian`")
        theme.hidden_entries = data.get("hidden_entries", [])

        return theme
