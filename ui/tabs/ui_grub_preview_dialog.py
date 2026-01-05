"""Dialog pour afficher un aperçu réaliste du menu GRUB.

Utilisé par tab_theme_config et tab_theme_editor pour prévisualiser
les thèmes avec la configuration réelle du système.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from gi.repository import Gdk, GLib, Gtk
from loguru import logger

from core.models.core_grub_ui_model import GrubUiModel
from core.models.core_theme_models import GrubTheme
from core.services.core_grub_service import GrubService, MenuEntry

_GRUB_COLOR_MAP: dict[str, str] = {
    "light-gray": "#D3D3D3",
    "dark-gray": "#555555",
    "black": "black",
    "white": "white",
    "red": "red",
    "green": "green",
    "blue": "blue",
    "cyan": "cyan",
    "magenta": "magenta",
    "yellow": "yellow",
}


def _parse_grub_color(grub_color: str, default: str) -> str:
    if not grub_color:
        return default
    fg = grub_color.split("/")[0].strip() if "/" in grub_color else grub_color.strip()
    return _GRUB_COLOR_MAP.get(fg, fg)


def _default_entry_index(menu_entries: list[MenuEntry], default_entry: str) -> int:
    try:
        if default_entry.isdigit():
            return int(default_entry)
        if ">" in default_entry and default_entry.split(">", maxsplit=1)[0].isdigit():
            return int(default_entry.split(">", maxsplit=1)[0])
    except (TypeError, ValueError):
        return 0

    for i, entry in enumerate(menu_entries):
        if default_entry in (entry.title, entry.id):
            return i
    return 0


_FONT_SIZE_RE = re.compile(r"^\d+(?:\.\d+)?(?:(?:pt)|(?:px)|(?:em)|(?:rem))?$")
_BOLD_TOKENS = {"bold", "semibold", "demibold", "extrabold", "ultrabold"}


def _gtk_font_rules(font: str, *, indent: str = "") -> str:
    """Construit des règles CSS GTK valides à partir d'une chaîne de police.

    Les thèmes GRUB utilisent souvent un format type "DejaVu Sans Bold 14pt".
    En GTK CSS, `font-family` ne tolère pas la taille (sinon warning "Junk at end");
    on extrait donc la famille, la taille et (si détectée) la graisse.
    """
    raw = (font or "").strip()
    if not raw:
        return ""

    tokens = raw.split()
    size_token: str | None = None
    if tokens and _FONT_SIZE_RE.match(tokens[-1]):
        size_token = tokens.pop(-1)

    # Si la taille n'a pas d'unité (ex: "12"), on suppose "pt" (format GRUB courant).
    if size_token and size_token.isdigit():
        size_token = f"{size_token}pt"

    weight: str | None = None
    family_tokens: list[str] = []
    for token in tokens:
        lower = token.lower()
        if lower in _BOLD_TOKENS or token == "Bold":
            weight = "bold"
            continue
        if token == "Regular":
            continue
        family_tokens.append(token)

    family = " ".join(family_tokens).strip()

    rules: list[str] = []
    if family:
        # Les familles avec espaces doivent être entre guillemets.
        rules.append(f'{indent}font-family: "{family}";')
    if size_token:
        rules.append(f"{indent}font-size: {size_token};")
    if weight:
        rules.append(f"{indent}font-weight: {weight};")

    return ("\n".join(rules) + "\n") if rules else ""


@dataclass(frozen=True, slots=True)
class _PreviewColors:
    fg_color: str
    bg_color: str
    hl_fg: str
    hl_bg: str
    title_color: str


@dataclass(frozen=True, slots=True)
class _PreviewFonts:
    title_font: str
    entry_font: str


@dataclass(frozen=True, slots=True)
class _PreviewLayout:
    menu_top: str
    menu_left: str
    menu_width: str
    menu_height: str


class GrubPreviewDialog:
    """Dialog pour prévisualiser un thème GRUB."""

    def __init__(self, theme: GrubTheme, model: GrubUiModel | None = None, theme_name: str = "") -> None:
        """Initialise le dialog de preview.

        Args:
            theme: Thème à prévisualiser
            model: Modèle UI actuel (optionnel)
            theme_name: Nom du thème pour le titre
        """
        self.theme = theme
        self.model = model
        self.theme_name = theme_name or theme.name

    def show(self) -> None:
        """Affiche le dialog de preview."""
        dialog = self._create_dialog_window()
        main_box = self._create_main_box()
        main_box.append(self._create_title_label())

        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)
        overlay.set_child(self._create_background_widget())

        preview_box = self._create_preview_box()
        self._create_grub_preview(preview_box)
        overlay.add_overlay(preview_box)

        frame = Gtk.Frame()
        frame.set_child(overlay)
        main_box.append(frame)
        main_box.append(self._create_close_buttons(dialog))

        self._apply_preview_styles()
        dialog.set_child(main_box)
        dialog.present()

    def get_background_path(self) -> str:
        """Retourne le chemin d'image de fond utilisé pour l'aperçu (si existant)."""
        if self.theme and self.theme.image.desktop_image:
            return self.theme.image.desktop_image
        if self.model and self.model.grub_background:
            return self.model.grub_background
        return ""

    def _create_dialog_window(self) -> Gtk.Window:
        dialog = Gtk.Window()
        dialog.set_title(f"Aperçu GRUB: {self.theme_name}")
        dialog.set_default_size(1000, 700)
        dialog.set_modal(True)
        return dialog

    def _create_main_box(self) -> Gtk.Box:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        return main_box

    def _create_title_label(self) -> Gtk.Label:
        title = Gtk.Label()
        title.set_markup(f"<b>Aperçu du menu GRUB avec {self.theme_name}</b>")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("section-title")
        return title

    def _create_background_widget(self) -> Gtk.Picture:
        bg_widget = Gtk.Picture()
        if hasattr(bg_widget, "set_content_fit"):
            bg_widget.set_content_fit(Gtk.ContentFit.FILL)
        else:
            bg_widget.set_keep_aspect_ratio(False)
        bg_widget.set_overflow(Gtk.Overflow.HIDDEN)

        bg_path = self.get_background_path()
        if bg_path and os.path.exists(bg_path):
            try:
                bg_widget.set_filename(bg_path)
                bg_widget.add_css_class("preview-bg")
                return bg_widget
            except (GLib.Error, OSError, ValueError, TypeError) as e:
                logger.warning(f"[GrubPreviewDialog] Impossible de charger l'image {bg_path}: {e}")

        bg_widget.add_css_class("preview-bg-fallback")
        return bg_widget

    def _create_preview_box(self) -> Gtk.Box:
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        preview_box.set_margin_start(40)
        preview_box.set_margin_end(40)
        preview_box.set_margin_top(40)
        preview_box.set_margin_bottom(40)
        preview_box.set_valign(Gtk.Align.CENTER)
        preview_box.set_halign(Gtk.Align.CENTER)
        preview_box.add_css_class("grub-menu-container")
        return preview_box

    def _create_close_buttons(self, dialog: Gtk.Window) -> Gtk.Box:
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)

        close_btn = Gtk.Button(label="Fermer")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", lambda _btn: dialog.close())
        button_box.append(close_btn)
        return button_box

    def _resolve_preview_style(self) -> tuple[_PreviewColors, _PreviewFonts, _PreviewLayout]:
        colors = _PreviewColors(
            fg_color="white",
            bg_color="rgba(0, 0, 0, 0.5)",
            hl_fg="black",
            hl_bg="#D3D3D3",
            title_color="white",
        )
        fonts = _PreviewFonts(title_font="DejaVu Sans Bold 14pt", entry_font="DejaVu Sans Mono 12pt")
        layout = _PreviewLayout(menu_top="20%", menu_left="15%", menu_width="70%", menu_height="auto")

        if self.model and self.model.theme_management_enabled and self.theme:
            theme_bg = self.theme.colors.menu_normal_bg
            resolved_bg = (
                "rgba(0, 0, 0, 0.4)" if theme_bg == "black" else _parse_grub_color(theme_bg, "rgba(0, 0, 0, 0.4)")
            )
            colors = _PreviewColors(
                fg_color=_parse_grub_color(self.theme.colors.menu_normal_fg, "white"),
                bg_color=resolved_bg,
                hl_fg=_parse_grub_color(self.theme.colors.menu_highlight_fg, "black"),
                hl_bg=_parse_grub_color(self.theme.colors.menu_highlight_bg, "#D3D3D3"),
                title_color=_parse_grub_color(self.theme.colors.title_color, "white"),
            )

            if self.theme.layout:
                layout = _PreviewLayout(
                    menu_top=self.theme.layout.menu_top,
                    menu_left=self.theme.layout.menu_left,
                    menu_width=self.theme.layout.menu_width,
                    menu_height=self.theme.layout.menu_height,
                )

            if self.theme.fonts:
                fonts = _PreviewFonts(
                    title_font=self.theme.fonts.title_font.replace("Regular", "").strip(),
                    entry_font=self.theme.fonts.terminal_font.replace("Regular", "").strip(),
                )

        elif self.model:
            colors = _PreviewColors(
                fg_color=_parse_grub_color(self.model.grub_color_normal, "white"),
                bg_color="rgba(0, 0, 0, 0.6)",
                hl_fg=_parse_grub_color(self.model.grub_color_highlight, "black"),
                hl_bg=colors.hl_bg,
                title_color=colors.title_color,
            )

        return colors, fonts, layout

    def _apply_preview_styles(self) -> None:
        """Applique des styles CSS pour rendre l'aperçu plus fidèle."""
        css_provider = Gtk.CssProvider()

        colors, fonts, _layout = self._resolve_preview_style()

        entry_font_rules = _gtk_font_rules(fonts.entry_font, indent="                ")
        title_font_rules = _gtk_font_rules(fonts.title_font, indent="                ")

        css = f"""
            .preview-bg {{
                background-color: black;
            }}
            .preview-bg-fallback {{
                background-color: #000044; /* Bleu GRUB classique */
            }}
            .grub-menu-container {{
                background-color: {colors.bg_color};
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 20px;
            }}
            .grub-entry {{
                color: {colors.fg_color};
{entry_font_rules}
                padding: 4px 10px;
                margin: 2px 0;
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
                margin-bottom: 20px;
                font-weight: bold;
            }}
            .grub-info {{
                color: rgba(255, 255, 255, 0.7);
{entry_font_rules}
                font-size: 0.8em;
                margin-top: 20px;
            }}
        """
        # Gtk.CssProvider.load_from_data est déprécié en GTK4.
        if hasattr(css_provider, "load_from_string"):
            css_provider.load_from_string(css)
        else:
            css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _read_preview_data(self) -> tuple[int, str, list[MenuEntry]]:
        try:
            if self.model:
                timeout = self.model.timeout
                default_entry = self.model.default
            else:
                config = GrubService.read_current_config()
                timeout = config.timeout
                default_entry = config.default_entry

            menu_entries = GrubService.get_menu_entries()
            return timeout, default_entry, menu_entries
        except (OSError, RuntimeError) as e:
            logger.warning(f"[GrubPreviewDialog] Erreur lecture config: {e}")
            return 10, "0", [MenuEntry(title="Ubuntu", id="gnulinux")]

    def _append_menu_entry_row(self, container: Gtk.Box, *, entry: MenuEntry, is_selected: bool) -> None:
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        entry_box.add_css_class("grub-entry")

        if is_selected:
            entry_box.add_css_class("grub-entry-selected")
            entry_box.append(Gtk.Label(label="*"))
        else:
            entry_box.append(Gtk.Label(label=" "))

        label = Gtk.Label(label=entry.title)
        label.set_halign(Gtk.Align.START)
        entry_box.append(label)
        container.append(entry_box)

    def _build_help_text(self, *, timeout: int) -> str:
        help_text = (
            "Utilisez les touches \u2191 et \u2193 pour sélectionner l'entrée en surbrillance.\n"
            "Appuyez sur Entrée pour démarrer l'OS sélectionné, 'e' pour éditer les\n"
            "commandes avant le démarrage ou 'c' pour une ligne de commande."
        )
        if timeout >= 0:
            help_text += f"\n\nL'entrée sélectionnée sera démarrée automatiquement dans {timeout}s."
        return help_text

    def _create_grub_preview(self, container: Gtk.Box) -> None:
        """Crée un aperçu réaliste du menu GRUB.

        Args:
            container: Container où placer le preview
        """
        timeout, default_entry, menu_entries = self._read_preview_data()

        title_label = Gtk.Label(label="GNU GRUB version 2.12")
        title_label.add_css_class("grub-title")
        container.append(title_label)

        default_index = _default_entry_index(menu_entries, default_entry)
        for i, entry in enumerate(menu_entries):
            self._append_menu_entry_row(container, entry=entry, is_selected=i == default_index)

        help_label = Gtk.Label(label=self._build_help_text(timeout=timeout))
        help_label.set_justify(Gtk.Justification.CENTER)
        help_label.add_css_class("grub-info")
        container.append(help_label)

        logger.debug("[GrubPreviewDialog] Preview créé")
