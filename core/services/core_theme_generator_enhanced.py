"""
Enhanced theme generator with templates, color palettes, and validation.

Based on GRUB theme documentation and best practices from vinceliuice/grub2-themes.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ThemeResolution(Enum):
    """Supported GRUB resolutions."""

    RESOLUTION_1080P = "1080p"
    RESOLUTION_2K = "2k"
    RESOLUTION_4K = "4k"
    RESOLUTION_ULTRAWIDE = "ultrawide"
    RESOLUTION_ULTRAWIDE_2K = "ultrawide2k"
    CUSTOM = "custom"


class ColorScheme(Enum):
    """Pre-built color schemes."""

    DARK = "dark"
    LIGHT = "light"
    MINIMAL = "minimal"
    DRACULA = "dracula"
    NORD = "nord"
    CUSTOM = "custom"


@dataclass
class ResolutionConfig:
    """Resolution-specific configuration."""

    width: int
    height: int
    boot_menu_left: str = "30%"
    boot_menu_top: str = "30%"
    boot_menu_width: str = "40%"
    boot_menu_height: str = "40%"
    item_font_size: int = 16
    item_icon_width: int = 32
    item_icon_height: int = 32
    item_icon_space: int = 20
    item_height: int = 36
    item_padding: int = 5
    item_spacing: int = 10
    terminal_font_size: int = 14
    info_image_height: int = 42


@dataclass
class ColorPalette:
    """Theme color palette."""

    name: str
    background_color: str  # HTML color like #000000
    item_color: str  # Regular text color
    selected_item_color: str  # Highlighted item color
    label_color: str  # Label text color
    terminal_foreground: str | None = None
    terminal_background: str | None = None


class ThemeResolutionHelper:
    """Helpers for resolution-specific configurations."""

    RESOLUTION_CONFIGS: dict[ThemeResolution, ResolutionConfig] = {
        ThemeResolution.RESOLUTION_1080P: ResolutionConfig(1920, 1080, terminal_font_size=14, item_font_size=16),
        ThemeResolution.RESOLUTION_2K: ResolutionConfig(
            2560,
            1440,
            terminal_font_size=18,
            item_font_size=24,
            item_icon_width=48,
            item_icon_height=48,
            item_icon_space=24,
            item_height=56,
            item_padding=8,
            item_spacing=16,
        ),
        ThemeResolution.RESOLUTION_4K: ResolutionConfig(
            3840,
            2160,
            terminal_font_size=18,
            item_font_size=32,
            item_icon_width=64,
            item_icon_height=64,
            item_icon_space=36,
            item_height=80,
            item_padding=12,
            item_spacing=24,
        ),
        ThemeResolution.RESOLUTION_ULTRAWIDE: ResolutionConfig(2560, 1080, terminal_font_size=14, item_font_size=16),
        ThemeResolution.RESOLUTION_ULTRAWIDE_2K: ResolutionConfig(3440, 1440, terminal_font_size=18, item_font_size=24),
    }

    @staticmethod
    def get_config_for_resolution(resolution: ThemeResolution) -> ResolutionConfig:
        """Get configuration for given resolution."""
        if resolution in ThemeResolutionHelper.RESOLUTION_CONFIGS:
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[resolution]
        # Default to 1080p
        return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_1080P]

    @staticmethod
    def get_custom_resolution_config(width: int, height: int) -> ResolutionConfig:
        """Generate config for custom resolution."""
        # Intelligently scale based on pixel count
        pixel_count = width * height

        if pixel_count <= 1920 * 1080:  # ~2MP
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_1080P]
        elif pixel_count <= 2560 * 1440:  # ~3.6MP
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_2K]
        else:  # 4K+
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_4K]


class ColorPaletteFactory:
    """Factory for creating color palettes."""

    PALETTES: dict[ColorScheme, ColorPalette] = {
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
        """Get color palette for scheme."""
        return ColorPaletteFactory.PALETTES.get(scheme, ColorPaletteFactory.PALETTES[ColorScheme.DARK])

    @staticmethod
    def create_custom_palette(name: str, bg: str, item: str, selected: str, label: str) -> ColorPalette:
        """Create custom color palette."""
        return ColorPalette(name, bg, item, selected, label)


class ThemeTemplateBuilder:
    """Build GRUB theme files from templates."""

    THEME_HEADER = """\
# GRUB2 gfxmenu Linux theme
# {title}
# Elements: {elements_list}
# Generated by 05_xxx
"""

    GLOBAL_PROPS = """
# Global Properties
title-text: ""
desktop-image: "{desktop_image}"
desktop-image-scale-method: "{scale_method}"
desktop-image-h-align: "{h_align}"
desktop-image-v-align: "{v_align}"
desktop-color: "{background_color}"
terminal-font: "{terminal_font}"
terminal-box: "terminal_box_*.png"
terminal-width: "100%"
terminal-height: "100%"
terminal-border: "0"
"""

    BOOT_MENU_TEMPLATE = """
# Boot Menu Component
+ boot_menu {{
  left = {left}%
  top = {top}%
  width = {width}%
  height = {height}%
  item_font = "{item_font}"
  item_color = "{item_color}"
  selected_item_color = "{selected_item_color}"
  icon_width = {icon_size}
  icon_height = {icon_size}
  item_icon_space = 20
  item_height = {item_height}
  item_padding = 5
  item_spacing = {item_spacing}
  selected_item_pixmap_style = "{selection_style}"
}}
"""

    PROGRESS_BAR_TEMPLATE = """
# Progress Bar Component
+ progress_bar {{
  id = "__timeout__"
  left = 50%-{width_half}%
  top = {top}%
  width = {width}%
  height = {height}
  text_color = "{fg_color}"
  bg_color = "{bg_color}"
  fg_color = "{fg_color}"
  bar_style = "progress_bar_*.png"
}}
"""

    TIMEOUT_LABEL_TEMPLATE = """
# Timeout Label
+ label {{
  top = {top}%
  left = 32%
  width = 36%
  align = "center"
  id = "__timeout__"
  text = "{text}"
  color = "{color}"
  font = "{font}"
}}
"""

    IMAGE_TEMPLATE = """
# Info/Footer Image
+ image {{
  top = 100%-{height}
  left = 50%-{width_half}
  width = {width}
  height = {height}
  file = "{file}"
}}
"""

    LOGO_TEMPLATE = """
# Logo Image
+ image {{
  top = {top}%
  left = 50%-{width_half}
  width = {width}
  height = {height}
  file = "{file}"
}}
"""

    LABEL_TEMPLATE = """
# Generic Label
+ label {{
  top = {top}%
  left = {left}%
  width = {width}%
  align = "{align}"
  text = "{text}"
  color = "{color}"
  font = "{font}"
}}
"""

    @staticmethod
    def generate_theme_file(
        title: str,
        config: dict[str, Any],
        resolution_config: ResolutionConfig,
    ) -> str:
        """Generate theme.txt content dynamically."""
        elements_config = config.get("elements", {})
        properties = config.get("properties", {})

        # 1. Header
        enabled_elements = [name for name, e in elements_config.items() if e.get("enabled")]
        elements_list = ", ".join(enabled_elements)
        content = ThemeTemplateBuilder.THEME_HEADER.format(
            title=title,
            elements_list=elements_list,
        )

        # 2. Global Properties
        colors = properties.get("colors", {})
        fonts = properties.get("fonts", {})
        desktop_image_props = properties.get("desktop_image", {})
        content += ThemeTemplateBuilder.GLOBAL_PROPS.format(
            background_color=desktop_image_props.get("background_color", colors.get("background", "#000000")),
            terminal_font=fonts.get("terminal_font", f"Terminus Regular {resolution_config.terminal_font_size}"),
            desktop_image=desktop_image_props.get("file", "background.jpg").split("/")[-1],
            scale_method=desktop_image_props.get("scale_method", "stretch"),
            h_align=desktop_image_props.get("h_align", "center"),
            v_align=desktop_image_props.get("v_align", "center"),
        )

        # 3. Components
        if elements_config.get("boot_menu", {}).get("enabled"):
            p = properties.get("boot_menu", {})
            icons_p = properties.get("icons", {})
            selection_p = properties.get("selection", {})
            
            # Use icon size from icons element if enabled, else from boot_menu
            icon_size = icons_p.get("icon_size", p.get("icon_size", 32))
            
            # Selection style
            selection_style = "select_*.png"
            if elements_config.get("selection", {}).get("enabled"):
                # If selection is enabled, we assume the user wants to use the select_*.png pattern
                # but we could also allow custom patterns if needed.
                pass

            content += ThemeTemplateBuilder.BOOT_MENU_TEMPLATE.format(
                left=p.get("left", 30),
                top=p.get("top", 30),
                width=p.get("width", 40),
                height=p.get("height", 40),
                item_font=fonts.get("item_font", f"Unifont Regular {resolution_config.item_font_size}"),
                item_color=colors.get("text", "#cccccc"),
                selected_item_color=colors.get("selected", "#ffffff"),
                icon_size=icon_size,
                item_height=p.get("item_height", 36),
                item_spacing=p.get("item_spacing", 10),
                selection_style=selection_style,
            )

        if elements_config.get("progress_bar", {}).get("enabled"):
            p = properties.get("progress_bar", {})
            width = p.get("width", 60)
            content += ThemeTemplateBuilder.PROGRESS_BAR_TEMPLATE.format(
                top=p.get("top", 80),
                width=width,
                width_half=width // 2,
                height=p.get("height", 24),
                fg_color=p.get("fg_color", colors.get("selected_bg", "#cccccc")),
                bg_color=p.get("bg_color", "#333333"),
            )

        if elements_config.get("timeout_label", {}).get("enabled"):
            p = properties.get("timeout_label", {})
            content += ThemeTemplateBuilder.TIMEOUT_LABEL_TEMPLATE.format(
                top=p.get("top", 82),
                text=p.get("text", "Booting in %d seconds"),
                color=colors.get("label", colors.get("text", "#cccccc")),
                font=fonts.get("item_font", f"Unifont Regular {resolution_config.item_font_size}"),
            )

        if elements_config.get("footer_image", {}).get("enabled"):
            p = properties.get("footer_image", {})
            height = p.get("height", 42)
            width = resolution_config.width // 3
            content += ThemeTemplateBuilder.IMAGE_TEMPLATE.format(
                height=height,
                width=width,
                width_half=width // 2,
                file=p.get("file", "info.png").split("/")[-1],
            )

        if elements_config.get("logo_image", {}).get("enabled"):
            p = properties.get("logo_image", {})
            width = p.get("width", 256)
            content += ThemeTemplateBuilder.LOGO_TEMPLATE.format(
                top=p.get("top", 10),
                width=width,
                width_half=width // 2,
                height=p.get("height", 128),
                file=p.get("file", "logo.png").split("/")[-1],
            )

        if elements_config.get("instruction_label", {}).get("enabled"):
            p = properties.get("instruction_label", {})
            content += ThemeTemplateBuilder.LABEL_TEMPLATE.format(
                top=p.get("top", 85),
                left=p.get("left", 0),
                width=p.get("width", 100),
                align=p.get("align", "center"),
                text=p.get("text", "Appuyez sur 'e' pour éditer, 'c' pour la ligne de commande"),
                color=p.get("color", colors.get("label", colors.get("text", "#aaaaaa"))),
                font=fonts.get("item_font", f"Unifont Regular {resolution_config.item_font_size}"),
            )

        logger.info(f"Generated dynamic theme file for {title}")
        return content


class ThemeValidator:
    """Validate theme files."""

    REQUIRED_FIELDS = {
        "desktop-image",
        "terminal-font",
        "boot_menu",
    }

    VALID_COLOR_PATTERNS = [
        r"^#[0-9a-fA-F]{6}$",  # HTML color #RRGGBB
        r"^\d+,\s*\d+,\s*\d+$",  # RGB decimal: 255, 128, 0
    ]

    @staticmethod
    def validate_theme_file(content: str) -> tuple[bool, list[str]]:
        """Validate theme file content."""
        errors = []
        lines = content.split("\n")

        # Check for required components
        content_lower = content.lower()
        for field in ThemeValidator.REQUIRED_FIELDS:
            if field.lower() not in content_lower:
                errors.append(f"Missing required component: {field}")

        # Check boot_menu structure
        if "+ boot_menu {" not in content:
            errors.append("boot_menu component not properly structured")

        # Check for proper closing braces
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            errors.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

        logger.info(f"Theme validation: {len(errors)} errors found")
        return len(errors) == 0, errors

    @staticmethod
    def validate_color(color_str: str) -> bool:
        """Validate color format."""
        import re

        for pattern in ThemeValidator.VALID_COLOR_PATTERNS:
            if re.match(pattern, color_str):
                return True
        # Check SVG color names
        svg_colors = {"black", "white", "red", "green", "blue", "gray", "yellow"}
        return color_str.lower() in svg_colors


class EnhancedThemeGenerator:
    """Main enhanced theme generator."""

    def __init__(self):
        logger.info("Initializing enhanced theme generator")

    def create_theme_package(
        self,
        name: str,
        theme_config: dict[str, Any],
        resolution: ThemeResolution,
        custom_resolution: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """Create complete theme package."""
        logger.info(f"Creating theme: {name}, resolution: {resolution.value}")

        # Determine resolution config
        if custom_resolution:
            res_config = ThemeResolutionHelper.get_custom_resolution_config(*custom_resolution)
        else:
            res_config = ThemeResolutionHelper.get_config_for_resolution(resolution)

        # Generate theme file
        theme_content = ThemeTemplateBuilder.generate_theme_file(
            title=f"{name} Theme ({resolution.value})",
            config=theme_config,
            resolution_config=res_config,
        )

        # Validate
        is_valid, errors = ThemeValidator.validate_theme_file(theme_content)
        if not is_valid:
            logger.warning(f"Theme validation warnings: {errors}")

        package = {
            "theme.txt": theme_content,
            "metadata": f"Theme: {name}\nResolution: {resolution.value}",
            "assets": self._collect_assets(theme_config),
        }

        return package

    def _collect_assets(self, config: dict[str, Any]) -> dict[str, str]:
        """Collect asset paths from configuration."""
        assets = {}
        props = config.get("properties", {})
        elements = config.get("elements", {})

        # Background
        if elements.get("desktop_image", {}).get("enabled"):
            path = props.get("desktop_image", {}).get("file")
            if path and "/" in path:
                assets["background.jpg"] = path

        # Logo
        if elements.get("logo_image", {}).get("enabled"):
            path = props.get("logo_image", {}).get("file")
            if path and "/" in path:
                assets[path.split("/")[-1]] = path

        # Footer
        if elements.get("footer_image", {}).get("enabled"):
            path = props.get("footer_image", {}).get("file")
            if path and "/" in path:
                assets["info.png"] = path

        # Fonts
        if elements.get("fonts", {}).get("enabled"):
            p = props.get("fonts", {})
            if p.get("item_font_file"):
                assets[p["item_font_file"].split("/")[-1]] = p["item_font_file"]
            if p.get("terminal_font_file"):
                assets[p["terminal_font_file"].split("/")[-1]] = p["terminal_font_file"]

        # Icons
        if elements.get("icons", {}).get("enabled"):
            path = props.get("icons", {}).get("icons_path")
            if path:
                assets["icons"] = path  # This is a folder

        # Selection
        if elements.get("selection", {}).get("enabled"):
            p = props.get("selection", {})
            if p.get("select_w"): assets["select_w.png"] = p["select_w"]
            if p.get("select_c"): assets["select_c.png"] = p["select_c"]
            if p.get("select_e"): assets["select_e.png"] = p["select_e"]

        # Progress Bar
        if elements.get("progress_bar", {}).get("enabled"):
            p = props.get("progress_bar", {})
            if p.get("progress_bar_c"): assets["progress_bar_c.png"] = p["progress_bar_c"]
            # We could add _l and _r if needed

        # Terminal Box
        if elements.get("terminal_box", {}).get("enabled"):
            p = props.get("terminal_box", {})
            if p.get("terminal_box_c"): assets["terminal_box_c.png"] = p["terminal_box_c"]

        return assets

    def create_custom_color_theme(
        self,
        name: str,
        bg_color: str,
        item_color: str,
        selected_color: str,
        label_color: str,
        resolution: ThemeResolution,
        custom_resolution: tuple[int, int] | None = None,
    ) -> dict[str, str]:
        """Create theme with custom colors."""
        logger.info(f"Creating custom color theme: {name}")

        # Validate colors
        for color, color_name in [
            (bg_color, "background"),
            (item_color, "item"),
            (selected_color, "selected item"),
            (label_color, "label"),
        ]:
            if not ThemeValidator.validate_color(color):
                logger.warning(f"Invalid color format for {color_name}: {color}")

        # Create palette
        palette = ColorPaletteFactory.create_custom_palette(name, bg_color, item_color, selected_color, label_color)

        # Determine resolution config
        if custom_resolution:
            res_config = ThemeResolutionHelper.get_custom_resolution_config(*custom_resolution)
        else:
            res_config = ThemeResolutionHelper.get_config_for_resolution(resolution)

        # Create a minimal config for the template builder
        theme_config = {
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
                }
            }
        }

        # Generate theme
        theme_content = ThemeTemplateBuilder.generate_theme_file(
            title=f"{name} (Custom Colors)",
            config=theme_config,
            resolution_config=res_config,
        )

        return {
            "theme.txt": theme_content,
            "metadata": f"Theme: {name}\nColors: Custom\nResolution: {resolution.value}",
        }
