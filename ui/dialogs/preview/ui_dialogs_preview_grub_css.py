"""Générateur CSS pour le preview GRUB - responsabilité unique de styling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreviewColors:
    """Couleurs du preview GRUB."""

    fg_color: str
    bg_color: str
    hl_fg: str
    hl_bg: str
    title_color: str


@dataclass(frozen=True, slots=True)
class PreviewFonts:
    """Polices du preview GRUB."""

    title_font: str
    entry_font: str


@dataclass(frozen=True, slots=True)
class PreviewLayout:
    """Layout du preview GRUB."""

    menu_top: str
    menu_left: str
    menu_width: str
    menu_height: str


@dataclass(slots=True)
class PreviewCssConfig:
    """Configuration CSS du preview."""

    desktop_color: str
    item_padding: int
    item_spacing: int
    item_height: int
    screen_border: str
    screen_shadow: str
    menu_frame_border: str
    menu_frame_padding: str
    menu_frame_margin: str
    container_padding: str
    title_separator_color: str


class GrubPreviewCssGenerator:
    """Génère le CSS pour le preview GRUB selon le mode et la configuration."""

    @staticmethod
    def normalize_font_for_gtk(font_desc: str) -> str:
        """Normalise une police pour GTK.

        Args:
            font_desc: Description de police

        Returns:
            Police normalisée
        """
        # Enlever .pf2 et convertir pt en px
        if ".pf2" in font_desc:
            if "Bold" in font_desc or "title" in font_desc.lower():
                font_desc = "DejaVu Sans Bold 14pt"
            else:
                font_desc = "DejaVu Sans Mono 12pt"

        return font_desc.replace("pt", "px").replace("  ", " ")

    @staticmethod
    def _gtk_font_rules(font_desc: str, *, indent: str = "") -> str:
        """Convertit une description de police en règles CSS GTK.

        Args:
            font_desc: Description de police (ex: "DejaVu Sans Bold 14px")
            indent: Indentation pour le formatage

        Returns:
            Règles CSS formatées
        """
        parts = font_desc.split()
        rules = []

        # Extraire la famille de police
        family_parts = []
        size = None
        weight = "normal"
        style = "normal"

        for part in parts:
            if part.lower() == "bold":
                weight = "bold"
            elif part.lower() == "italic":
                style = "italic"
            elif part.endswith("px") or part.endswith("pt"):
                size = part
            else:
                family_parts.append(part)

        if family_parts:
            rules.append(f'{indent}font-family: "{" ".join(family_parts)}";')
        if size:
            rules.append(f"{indent}font-size: {size};")
        if weight != "normal":
            rules.append(f"{indent}font-weight: {weight};")
        if style != "normal":
            rules.append(f"{indent}font-style: {style};")

        return "\n".join(rules)

    @staticmethod
    def build_css_config_for_text_mode(desktop_color: str, fg_color: str) -> PreviewCssConfig:
        """Construit la config CSS pour le mode texte."""
        return PreviewCssConfig(
            desktop_color=desktop_color,
            item_padding=10,
            item_spacing=4,
            item_height=0,
            screen_border="2px solid white",
            screen_shadow="none",
            menu_frame_border="none",
            menu_frame_padding="0",
            menu_frame_margin="0",
            container_padding="0",
            title_separator_color=fg_color,
        )

    @staticmethod
    def build_css_config_for_gfx_mode(desktop_color: str) -> PreviewCssConfig:
        """Construit la config CSS pour le mode graphique."""
        return PreviewCssConfig(
            desktop_color=desktop_color,
            item_padding=10,
            item_spacing=4,
            item_height=0,
            screen_border="2px solid rgba(255, 255, 255, 0.75)",
            screen_shadow="inset 0 0 0 1px rgba(255, 255, 255, 0.35)",
            menu_frame_border="none",
            menu_frame_padding="0",
            menu_frame_margin="0",
            container_padding="18px 24px",
            title_separator_color="transparent",
        )

    @classmethod
    def generate_css(
        cls,
        *,
        colors: PreviewColors,
        fonts: PreviewFonts,
        config: PreviewCssConfig,
    ) -> str:
        """Génère le CSS complet pour le preview.

        Args:
            colors: Couleurs du thème
            fonts: Polices du thème
            config: Configuration CSS

        Returns:
            CSS complet formaté
        """
        entry_font_rules = cls._gtk_font_rules(fonts.entry_font, indent="                ")
        title_font_rules = cls._gtk_font_rules(fonts.title_font, indent="                ")

        item_height_rule = f"min-height: {config.item_height}px;" if config.item_height > 0 else ""
        item_margin = max(0, int(config.item_spacing / 2))

        return f"""
            .preview-bg {{
                background-color: black;
            }}
            .preview-bg-fallback {{
                background-color: {config.desktop_color};
            }}
            .grub-screen-frame {{
                border: {config.screen_border};
                box-shadow: {config.screen_shadow};
                padding: 0;
                border-radius: 0;
            }}
            .grub-menu-container {{
                background-color: transparent;
                border: none;
                border-radius: 0;
                padding: {config.container_padding};
            }}
            .grub-menu-frame {{
                border: {config.menu_frame_border};
                padding: {config.menu_frame_padding};
                margin-top: {config.menu_frame_margin};
                margin-bottom: {config.menu_frame_margin};
            }}
            .grub-entry {{
                color: {colors.fg_color};
{entry_font_rules}
                padding: 4px {config.item_padding}px;
                margin: {item_margin}px 0;
                {item_height_rule}
            }}
            .grub-entry-selected {{
                color: {colors.hl_fg};
                background-color: {colors.hl_bg};
                font-weight: bold;
                border-radius: 2px;
            }}
            .grub-title {{
                color: {colors.title_color};
{title_font_rules}
                margin: 12px 16px 8px 16px;
                font-weight: bold;
            }}
            .grub-info {{
                color: rgba(255, 255, 255, 0.7);
{entry_font_rules}
                font-size: 0.8em;
                margin-top: 8px;
            }}
            .grub-title-separator {{
                background-color: {config.title_separator_color};
                min-height: 2px;
                margin: 4px 0 12px 0;
            }}
            .grub-entries-list {{
                padding: 0;
                margin: 0;
            }}
        """
