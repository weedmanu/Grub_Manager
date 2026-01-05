"""Générateur de thèmes GRUB.

Façade (PGR/ROI): ce module expose l'API publique minimale et orchestre
les sous-modules (résolution, palettes, templates, validation).
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict, Unpack, cast

from .core_theme_generator_enums import ColorScheme, ThemeResolution
from .core_theme_generator_models import (
    BootMenuConfig,
    ColorPalette,
    InfoImageConfig,
    ItemConfig,
    ResolutionConfig,
    TerminalConfig,
)
from .core_theme_generator_palettes import ColorPaletteFactory
from .core_theme_generator_resolution import ThemeResolutionHelper
from .core_theme_generator_templates import ThemeTemplateBuilder
from .core_theme_generator_validation import ThemeValidator

logger = logging.getLogger(__name__)


class _CustomColorThemeKwargs(TypedDict):
    bg_color: str
    item_color: str
    selected_color: str
    label_color: str


class ThemeGenerator:
    """Générateur principal de thème."""

    def __init__(self) -> None:
        """Initialise le générateur de thèmes."""
        logger.info("Initializing theme generator")

    def create_theme_package(
        self,
        name: str,
        theme_config: dict[str, Any],
        resolution: ThemeResolution,
        custom_resolution: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """Crée un package complet de thème (theme.txt + metadata + assets)."""
        logger.info("Creating theme: %s, resolution: %s", name, resolution.value)

        res_config = self._resolve_resolution_config(resolution, custom_resolution)

        theme_content = ThemeTemplateBuilder.generate_theme_file(
            title=f"{name} Theme ({resolution.value})",
            config=theme_config,
            resolution_config=res_config,
        )

        is_valid, errors = ThemeValidator.validate_theme_file(theme_content)
        if not is_valid:
            logger.warning("Theme validation warnings: %s", errors)

        return {
            "theme.txt": theme_content,
            "metadata": f"Theme: {name}\nResolution: {resolution.value}",
            "assets": self._collect_assets(theme_config),
        }

    def create_custom_color_theme(
        self,
        name: str,
        *positional_colors: str,
        resolution: ThemeResolution,
        custom_resolution: tuple[int, int] | None = None,
        **colors: Unpack[_CustomColorThemeKwargs],
    ) -> dict[str, str]:
        """Crée un thème minimal basé uniquement sur une palette custom."""
        bg_color, item_color, selected_color, label_color = self._parse_custom_colors(
            positional_colors,
            cast(dict[str, str], colors),
        )

        logger.info("Creating custom color theme: %s", name)

        self._validate_custom_colors(bg_color, item_color, selected_color, label_color)

        ColorPaletteFactory.create_custom_palette(name, bg_color, item_color, selected_color, label_color)

        res_config = self._resolve_resolution_config(resolution, custom_resolution)
        theme_config = self._build_minimal_theme_config(
            bg_color,
            item_color,
            selected_color,
            label_color,
            res_config,
        )

        theme_content = ThemeTemplateBuilder.generate_theme_file(
            title=f"{name} (Custom Colors)",
            config=theme_config,
            resolution_config=res_config,
        )

        return {
            "theme.txt": theme_content,
            "metadata": f"Theme: {name}\nColors: Custom\nResolution: {resolution.value}",
        }

    @staticmethod
    def _resolve_resolution_config(
        resolution: ThemeResolution,
        custom_resolution: tuple[int, int] | None,
    ) -> ResolutionConfig:
        if custom_resolution:
            return ThemeResolutionHelper.get_custom_resolution_config(*custom_resolution)
        return ThemeResolutionHelper.get_config_for_resolution(resolution)

    @staticmethod
    def _parse_custom_colors(
        positional_colors: tuple[str, ...],
        keyword_colors: dict[str, str],
    ) -> tuple[str, str, str, str]:
        if positional_colors and keyword_colors:
            raise TypeError("Use either positional colors or keyword colors, not both")

        if positional_colors:
            if len(positional_colors) != 4:
                raise TypeError("Expected 4 positional colors: bg, item, selected, label")
            bg_color, item_color, selected_color, label_color = positional_colors
            return bg_color, item_color, selected_color, label_color

        missing = {"bg_color", "item_color", "selected_color", "label_color"} - set(keyword_colors)
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise TypeError(f"Missing required color keyword(s): {missing_list}")

        return (
            keyword_colors["bg_color"],
            keyword_colors["item_color"],
            keyword_colors["selected_color"],
            keyword_colors["label_color"],
        )

    @staticmethod
    def _validate_custom_colors(
        bg_color: str,
        item_color: str,
        selected_color: str,
        label_color: str,
    ) -> None:
        for color, color_name in (
            (bg_color, "background"),
            (item_color, "item"),
            (selected_color, "selected item"),
            (label_color, "label"),
        ):
            if not ThemeValidator.validate_color(color):
                logger.warning("Invalid color format for %s: %s", color_name, color)

    @staticmethod
    def _build_minimal_theme_config(
        bg_color: str,
        item_color: str,
        selected_color: str,
        label_color: str,
        res_config: ResolutionConfig,
    ) -> dict[str, Any]:
        return {
            "elements": {
                "boot_menu": {"enabled": True},
                "timeout_label": {"enabled": True},
                "footer_image": {"enabled": True},
            },
            "properties": {
                "colors": {
                    "background": bg_color,
                    "text": item_color,
                    "selected": selected_color,
                    "label": label_color,
                },
                "fonts": {
                    "item_font": f"Unifont Regular {res_config.item_font_size}",
                    "terminal_font": f"Terminus Regular {res_config.terminal_font_size}",
                },
            },
        }

    def _collect_assets(self, config: dict[str, Any]) -> dict[str, str]:
        """Collecte des chemins d'assets depuis la config."""
        assets: dict[str, str] = {}
        props: dict[str, Any] = config.get("properties", {})
        elements: dict[str, Any] = config.get("elements", {})

        self._collect_image_assets(assets, props, elements)
        self._collect_font_assets(assets, props, elements)
        self._collect_icon_assets(assets, props, elements)
        self._collect_selection_assets(assets, props, elements)
        self._collect_progress_assets(assets, props, elements)
        self._collect_terminal_assets(assets, props, elements)

        return assets

    @staticmethod
    def _add_asset(
        assets: dict[str, str],
        src_path: str | None,
        dest_name: str | None = None,
        *,
        require_slash: bool = False,
    ) -> None:
        if not src_path:
            return
        if require_slash and "/" not in src_path:
            return
        assets[dest_name or src_path.split("/")[-1]] = src_path

    def _collect_image_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        for element_key, prop_key, dest_name in (
            ("desktop_image", "desktop_image", "background.jpg"),
            ("logo_image", "logo_image", None),
            ("footer_image", "footer_image", "info.png"),
        ):
            if not elements.get(element_key, {}).get("enabled"):
                continue
            src = props.get(prop_key, {}).get("file")
            self._add_asset(assets, src, dest_name, require_slash=True)

    def _collect_font_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        if not elements.get("fonts", {}).get("enabled"):
            return

        fonts_props = props.get("fonts", {})
        for font_key in ("item_font_file", "terminal_font_file"):
            self._add_asset(assets, fonts_props.get(font_key), require_slash=False)

    def _collect_icon_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        if not elements.get("icons", {}).get("enabled"):
            return

        icons_path = props.get("icons", {}).get("icons_path")
        if icons_path:
            assets["icons"] = icons_path

    def _collect_selection_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        if not elements.get("selection", {}).get("enabled"):
            return

        selection_props = props.get("selection", {})
        for key, dest in (
            ("select_w", "select_w.png"),
            ("select_c", "select_c.png"),
            ("select_e", "select_e.png"),
        ):
            self._add_asset(assets, selection_props.get(key), dest)

    def _collect_progress_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        if not elements.get("progress_bar", {}).get("enabled"):
            return

        pb_props = props.get("progress_bar", {})
        self._add_asset(assets, pb_props.get("progress_bar_c"), "progress_bar_c.png")

    def _collect_terminal_assets(
        self,
        assets: dict[str, str],
        props: dict[str, Any],
        elements: dict[str, Any],
    ) -> None:
        if not elements.get("terminal_box", {}).get("enabled"):
            return

        tb_props = props.get("terminal_box", {})
        self._add_asset(assets, tb_props.get("terminal_box_c"), "terminal_box_c.png")


__all__ = [
    "BootMenuConfig",
    "ColorPalette",
    "ColorPaletteFactory",
    "ColorScheme",
    "InfoImageConfig",
    "ItemConfig",
    "ResolutionConfig",
    "TerminalConfig",
    "ThemeGenerator",
    "ThemeResolution",
    "ThemeResolutionHelper",
    "ThemeTemplateBuilder",
    "ThemeValidator",
]
