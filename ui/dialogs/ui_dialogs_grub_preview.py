"""Dialog pour afficher un aperçu réaliste du menu GRUB.

Architecture modulaire SOLID :
- ui_grub_preview_css : Génération CSS (Single Responsibility)
- ui_grub_preview_parsers : Parsing config GRUB (Single Responsibility)
- ui_grub_preview_data : Chargement données (Single Responsibility)
- ui_grub_preview_renderer : Rendu UI (Single Responsibility)
- ui_grub_preview_dialog : Orchestration (Dependency Inversion)
"""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gdk, GLib, Gtk
from loguru import logger

from core.models.core_models_grub_ui import GrubUiModel
from core.models.core_models_theme import GrubTheme
from ui.dialogs.preview.ui_dialogs_preview_grub_css import (
    GrubPreviewCssGenerator,
    PreviewColors,
    PreviewFonts,
)
from ui.dialogs.preview.ui_dialogs_preview_grub_data import GrubPreviewDataLoader
from ui.dialogs.preview.ui_dialogs_preview_grub_renderer import GrubPreviewRenderer


class GrubPreviewDialog:
    """Dialog pour prévisualiser un thème GRUB - Orchestrateur."""

    def __init__(
        self,
        theme: GrubTheme,
        model: GrubUiModel | None = None,
        theme_name: str = "",
        *,
        theme_txt_path: str | Path | None = None,
        use_system_files: bool = False,
    ) -> None:
        """Initialise le dialog de preview.

        Args:
            theme: Thème à prévisualiser
            model: Modèle UI actuel (optionnel)
            theme_name: Nom du thème pour le titre
            theme_txt_path: Chemin explicite vers theme.txt
            use_system_files: Si True, lit les fichiers système
        """
        self.theme = theme
        self.model = model
        self.theme_name = theme_name or (theme.name if theme else "Preview")

        # Data loader (Dependency Injection)
        self.data_loader = GrubPreviewDataLoader(
            use_system_files=use_system_files,
            model=model,
            theme=theme,
            theme_txt_path=Path(theme_txt_path) if theme_txt_path else None,
        )

    @property
    def is_text_mode(self) -> bool:
        """Retourne True si mode texte/console."""
        overrides = self.data_loader.load_system_theme_overrides()
        if self.data_loader.use_system_files:
            return overrides is None
        return self.theme is None

    def _apply_preview_styles(self, colors: PreviewColors, fonts: PreviewFonts) -> None:
        """Applique les styles CSS au preview.

        Args:
            colors: Couleurs du thème
            fonts: Polices du thème
        """
        # Mode texte : polices fixes
        if self.is_text_mode:
            normalized_fonts = PreviewFonts(title_font="Monospace 10px", entry_font="Monospace 9px")
        else:
            # Normaliser les polices pour GTK
            normalized_fonts = PreviewFonts(
                title_font=GrubPreviewCssGenerator.normalize_font_for_gtk(fonts.title_font),
                entry_font=GrubPreviewCssGenerator.normalize_font_for_gtk(fonts.entry_font),
            )

        # Récupérer les dimensions et couleur desktop
        desktop_color = self.data_loader.get_desktop_color()
        item_padding, item_spacing, item_height = self.data_loader.get_item_dimensions()

        # Construire la config CSS selon le mode
        if self.is_text_mode:
            css_config = GrubPreviewCssGenerator.build_css_config_for_text_mode(
                desktop_color=desktop_color, fg_color=colors.fg_color
            )
        else:
            css_config = GrubPreviewCssGenerator.build_css_config_for_gfx_mode(desktop_color=desktop_color)

        # Appliquer les dimensions personnalisées
        css_config.item_padding = item_padding
        css_config.item_spacing = item_spacing
        css_config.item_height = item_height

        # Générer et appliquer le CSS
        css = GrubPreviewCssGenerator.generate_css(colors=colors, fonts=normalized_fonts, config=css_config)

        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_data(css.encode())
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        except GLib.Error as e:
            logger.warning(f"[GrubPreviewDialog] Erreur CSS: {e}")

    def show(self) -> None:
        """Affiche le dialog de preview."""
        # Créer la fenêtre
        dialog = Gtk.Window()
        dialog.set_title(f"Preview - {self.theme_name}")
        dialog.set_default_size(1100, 700)
        dialog.set_modal(True)

        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        # Titre
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>Aperçu du thème : {self.theme_name}</b>")
        title_label.set_margin_bottom(16)
        main_box.append(title_label)

        # Charger les données et le style
        timeout, default_entry, menu_entries = self.data_loader.load_preview_data()
        colors, fonts, _layout = self.data_loader.resolve_preview_style(is_text_mode=self.is_text_mode)

        # Appliquer les styles CSS
        self._apply_preview_styles(colors, fonts)

        # Créer le container du preview GRUB
        if self.is_text_mode:
            # Mode texte : cadre blanc avec contenu qui s'étire
            grub_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            grub_section.set_vexpand(True)
            grub_section.set_hexpand(True)
            grub_section.add_css_class("grub-screen-frame")
            grub_section.add_css_class("grub-menu-container")

            # Rendu du preview
            GrubPreviewRenderer.render_preview(
                container=grub_section,
                timeout=timeout,
                default_entry=default_entry,
                menu_entries=menu_entries,
                is_text_mode=True,
            )

            main_box.append(grub_section)

            # Footer externe au cadre
            footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            footer_box.set_margin_top(12)
            help_label = Gtk.Label(label=GrubPreviewRenderer.build_help_text(timeout=timeout))
            help_label.set_justify(Gtk.Justification.LEFT)
            help_label.add_css_class("grub-info")
            help_label.set_halign(Gtk.Align.START)
            footer_box.append(help_label)
            main_box.append(footer_box)
        else:
            # Mode graphique : fond + cadre
            preview_bg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            preview_bg.set_vexpand(True)
            preview_bg.set_hexpand(True)
            preview_bg.add_css_class("preview-bg-fallback")

            grub_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            grub_box.set_valign(Gtk.Align.CENTER)
            grub_box.set_halign(Gtk.Align.CENTER)
            grub_box.add_css_class("grub-screen-frame")

            grub_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            grub_container.add_css_class("grub-menu-container")

            # Rendu du preview
            GrubPreviewRenderer.render_preview(
                container=grub_container,
                timeout=timeout,
                default_entry=default_entry,
                menu_entries=menu_entries,
                is_text_mode=False,
            )

            grub_box.append(grub_container)
            preview_bg.append(grub_box)
            main_box.append(preview_bg)

        # Bouton de fermeture
        close_button = Gtk.Button(label="Fermer")
        close_button.add_css_class("suggested-action")
        close_button.connect("clicked", lambda _: dialog.close())
        close_button.set_margin_top(16)
        main_box.append(close_button)

        # Afficher
        dialog.set_child(main_box)
        dialog.present()

        logger.debug(f"[GrubPreviewDialog] Preview affiché - {len(menu_entries)} entrées")
