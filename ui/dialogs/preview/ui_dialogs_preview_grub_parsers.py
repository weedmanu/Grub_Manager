"""Parsers pour fichiers de configuration GRUB - responsabilité unique de parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass(frozen=True, slots=True)
class SystemMenuColors:
    """Couleurs menu extraites de grub.cfg."""

    normal_fg: str
    normal_bg: str
    highlight_fg: str
    highlight_bg: str


@dataclass(slots=True)
class ThemeTxtOverrides:
    """Overrides extraits d'un fichier theme.txt."""

    desktop_image: str = ""
    desktop_color: str = ""
    terminal_font: str = ""
    boot_menu_left: str = ""
    boot_menu_top: str = ""
    boot_menu_width: str = ""
    boot_menu_height: str = ""
    item_font: str = ""
    item_color: str = ""
    selected_item_color: str = ""
    item_height: int | None = None
    item_padding: int | None = None
    item_spacing: int | None = None


class GrubConfigParser:
    """Parse les fichiers de configuration GRUB (grub.cfg, theme.txt)."""

    # Regex patterns
    _MENU_COLOR_RE = re.compile(r"^\s*set\s+menu_color_(normal|highlight)\s*=\s*([^\s#]+)")
    _THEME_SET_RE = re.compile(r"^\s*set\s+theme\s*=\s*(.+?)\s*$")
    _THEME_KV_RE = re.compile(r"^([a-zA-Z0-9_-]+)\s*:\s*\"(.*)\"\s*$")
    _BOOT_MENU_START_RE = re.compile(r"^\+\s*boot_menu\s*\{")
    _BLOCK_END_RE = re.compile(r"^\}\s*$")
    _BOOT_MENU_PROP_RE = re.compile(r"^([a-zA-Z0-9_]+)\s*=\s*(.+?)\s*$")

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Supprime les quotes autour d'une valeur."""
        v = (value or "").strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        return v

    @classmethod
    def parse_grub_cfg_menu_colors(cls, lines: list[str]) -> SystemMenuColors | None:
        """Parse les couleurs menu_color_* depuis grub.cfg.

        Args:
            lines: Lignes du fichier grub.cfg

        Returns:
            SystemMenuColors si trouvé, None sinon
        """
        colors = {"normal": None, "highlight": None}

        for line in lines:
            match = cls._MENU_COLOR_RE.match(line)
            if match:
                color_type, color_value = match.groups()
                colors[color_type] = color_value.strip()

        if colors["normal"] and colors["highlight"]:
            normal_parts = colors["normal"].split("/")
            highlight_parts = colors["highlight"].split("/")

            if len(normal_parts) >= 2 and len(highlight_parts) >= 2:
                return SystemMenuColors(
                    normal_fg=normal_parts[0],
                    normal_bg=normal_parts[1],
                    highlight_fg=highlight_parts[0],
                    highlight_bg=highlight_parts[1],
                )

        return None

    @classmethod
    def parse_grub_cfg_theme_path(cls, lines: list[str]) -> str | None:
        """Parse le chemin du thème depuis grub.cfg.

        Args:
            lines: Lignes du fichier grub.cfg

        Returns:
            Chemin du theme.txt si trouvé, None sinon
        """
        for line in lines:
            match = cls._THEME_SET_RE.match(line)
            if match:
                theme_path = match.group(1).strip()
                return cls._strip_quotes(theme_path)
        return None

    @staticmethod
    def _parse_boot_menu_property(overrides: ThemeTxtOverrides, key: str, value: str) -> None:
        """Parse une propriété boot_menu et met à jour overrides."""
        prop_map = {
            "left": "boot_menu_left",
            "top": "boot_menu_top",
            "width": "boot_menu_width",
            "height": "boot_menu_height",
            "item_font": "item_font",
            "item_color": "item_color",
            "selected_item_color": "selected_item_color",
        }

        if key in prop_map:
            setattr(overrides, prop_map[key], value)
        elif key in ("item_height", "item_padding", "item_spacing"):
            try:
                setattr(overrides, key, int(value))
            except ValueError:
                pass

    @staticmethod
    def _parse_root_property(overrides: ThemeTxtOverrides, key: str, value: str) -> None:
        """Parse une propriété racine du theme.txt."""
        prop_map = {
            "desktop-image": "desktop_image",
            "desktop-color": "desktop_color",
            "terminal-font": "terminal_font",
        }

        if key in prop_map:
            setattr(overrides, prop_map[key], value)

    @classmethod
    def parse_theme_txt(cls, theme_file: Path) -> ThemeTxtOverrides:
        """Parse un fichier theme.txt pour extraire les overrides.

        Args:
            theme_file: Chemin vers le fichier theme.txt

        Returns:
            ThemeTxtOverrides avec les valeurs extraites
        """
        overrides = ThemeTxtOverrides()

        try:
            with open(theme_file, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError as e:
            logger.debug(f"[GrubConfigParser] Impossible de lire {theme_file}: {e}")
            return overrides

        in_boot_menu_block = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Détecter début bloc boot_menu
            if cls._BOOT_MENU_START_RE.match(line):
                in_boot_menu_block = True
                continue

            # Détecter fin bloc
            if in_boot_menu_block and cls._BLOCK_END_RE.match(line):
                in_boot_menu_block = False
                continue

            # Parser propriétés boot_menu
            if in_boot_menu_block:
                match = cls._BOOT_MENU_PROP_RE.match(line)
                if match:
                    key, value = match.groups()
                    cls._parse_boot_menu_property(overrides, key, cls._strip_quotes(value))
                continue

            # Parser propriétés racine
            match = cls._THEME_KV_RE.match(line)
            if match:
                key, value = match.groups()
                cls._parse_root_property(overrides, key, value)

        return overrides

    @staticmethod
    def parse_grub_color_pair(
        color_pair: str, *, default_fg: str = "white", default_bg: str = "black"
    ) -> tuple[str, str]:
        """Parse une paire de couleurs GRUB (fg/bg).

        Args:
            color_pair: String au format "fg/bg"
            default_fg: Couleur foreground par défaut
            default_bg: Couleur background par défaut

        Returns:
            Tuple (fg, bg)
        """
        if not color_pair or "/" not in color_pair:
            return default_fg, default_bg

        parts = color_pair.split("/")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()

        return default_fg, default_bg

    @staticmethod
    def parse_grub_color(color: str, default: str = "white") -> str:
        """Parse une couleur GRUB unique.

        Args:
            color: Couleur à parser
            default: Couleur par défaut

        Returns:
            Couleur parsée ou défaut
        """
        if not color:
            return default

        color = color.strip().strip('"').strip("'")

        # Conversion couleurs GRUB → CSS
        grub_to_css = {
            "light-gray": "#D3D3D3",
            "light-grey": "#D3D3D3",
            "dark-gray": "#A9A9A9",
            "dark-grey": "#A9A9A9",
        }

        return grub_to_css.get(color.lower(), color)
