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


def compute_text_mode_metrics(*, width: int, height: int) -> dict[str, int]:
    """Calcule les métriques de layout pour imiter le GRUB texte, adaptées à la taille.

    Le rendu GRUB (capture) montre un cadre blanc quasi plein écran avec une marge fine,
    et un contenu légèrement inset dans le cadre.
    """
    min_dim = max(1, min(width, height))

    def _scaled(*, ratio: float, min_px: int, max_px: int) -> int:
        return max(min_px, min(max_px, round(min_dim * ratio)))

    return {
        # Basé sur le rendu actuel (1100x700): 18px marge, 16px padding X, 12px padding Y
        "outer_margin": _scaled(ratio=18 / 700, min_px=10, max_px=40),
        "inner_pad_x": _scaled(ratio=16 / 700, min_px=8, max_px=36),
        "inner_pad_y": _scaled(ratio=12 / 700, min_px=6, max_px=28),
        "footer_gap": _scaled(ratio=12 / 700, min_px=6, max_px=28),
    }


def _parse_layout_px(value: str, *, total: int) -> int | None:
    """Convertit une valeur de layout GRUB (px ou %) en pixels.

    Exemples: "20%", "320", "320px", "auto".
    """
    raw = (value or "").strip().lower()
    if not raw or raw == "auto":
        return None

    try:
        if raw.endswith("%"):
            pct = float(raw[:-1].strip())
            return round(total * pct / 100.0)
        if raw.endswith("px"):
            return round(float(raw[:-2].strip()))
        return round(float(raw))
    except ValueError:
        return None


class GrubThemePreviewDialog:
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
        # 1) Si on a un modèle UI, c'est la source la plus fiable (l'utilisateur a choisi une option).
        if self.model and self.model.grub_terminal:
            return "gfxterm" not in self.model.grub_terminal.lower()

        # 2) Mode système: lire GRUB_TERMINAL_OUTPUT (ou GRUB_TERMINAL)
        if self.data_loader.use_system_files:
            terminal_is_gfx = False
            try:
                cfg = self.data_loader.grub_service.read_current_config()
                if cfg.grub_terminal_output:
                    terminal_is_gfx = "gfxterm" in cfg.grub_terminal_output.lower()
            except Exception:
                pass

            # Si le terminal est gfxterm mais qu'aucun thème n'est détecté, on veut un rendu "GRUB par défaut"
            # (fond noir + cadre quasi plein écran + menu en haut à gauche), plus proche du mode texte.
            if terminal_is_gfx:
                overrides = self.data_loader.load_system_theme_overrides()
                if overrides is None:
                    return True

                return False

        # 3) Heuristique: un theme.txt implique généralement un rendu graphique.
        overrides = self.data_loader.load_system_theme_overrides()
        if overrides is not None:
            return False

        # 4) Fallback: pas de thème => rendu GRUB par défaut (texte).
        return True

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
        desktop_image_path = self.data_loader.get_desktop_image_path()
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

        # Si un desktop-image est défini, on l'utilise comme fond du preview (mode graphique)
        if desktop_image_path:
            # GTK CSS attend une URL; on encode les espaces au minimum.
            url = "file://" + desktop_image_path.replace(" ", "%20")
            css += (
                "\n.preview-bg-fallback {"
                f'\n  background-image: url("{url}");'
                "\n  background-size: cover;"
                "\n  background-repeat: no-repeat;"
                "\n  background-position: center;"
                "\n}"
            )

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
        dialog.set_default_size(1100, 820)
        dialog.set_resizable(False)
        dialog.set_modal(True)

        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Charger les données et le style
        timeout, default_entry, menu_entries = self.data_loader.load_preview_data()
        colors, fonts, layout = self.data_loader.resolve_preview_style(is_text_mode=self.is_text_mode)

        # Appliquer les styles CSS
        self._apply_preview_styles(colors, fonts)

        # Fond commun
        main_box.set_margin_top(0)
        main_box.set_margin_bottom(0)
        main_box.set_margin_start(0)
        main_box.set_margin_end(0)

        # Header: titre seul hors cadre
        header_label = Gtk.Label(label="GNU GRUB version 2.12")
        header_label.add_css_class("grub-title")
        header_label.set_halign(Gtk.Align.CENTER)
        main_box.append(header_label)

        # Zone centrale (cadre + menu)
        center_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_area.set_vexpand(True)
        center_area.set_hexpand(True)

        # Footer (hors cadre)
        footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        help_label = Gtk.Label(label=GrubPreviewRenderer.build_help_text(timeout=timeout))
        help_label.set_justify(Gtk.Justification.LEFT)
        help_label.add_css_class("grub-info")
        help_label.set_halign(Gtk.Align.START)
        footer_box.append(help_label)

        # Créer le container du preview GRUB
        if self.is_text_mode:
            # Mode texte : fond noir
            main_box.add_css_class("preview-bg")

            grub_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            grub_frame.set_vexpand(True)
            grub_frame.set_hexpand(True)
            grub_frame.add_css_class("grub-screen-frame")
            grub_frame.set_halign(Gtk.Align.CENTER)

            grub_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            grub_container.set_vexpand(True)
            grub_container.set_hexpand(True)
            grub_container.add_css_class("grub-menu-container")
            grub_frame.append(grub_container)

            center_area.append(grub_frame)
            main_box.append(center_area)
            main_box.append(footer_box)

            def _apply_text_layout(*, w: int, h: int) -> None:
                metrics = compute_text_mode_metrics(width=w, height=h)

                # Cadre centré avec ~95% de largeur (marge ~2.5% de chaque côté)
                side_margin = max(10, min(80, round(w * 0.025)))
                top_margin = metrics["outer_margin"]

                header_label.set_margin_top(top_margin)
                header_label.set_margin_bottom(max(6, top_margin // 2))

                center_area.set_margin_start(side_margin)
                center_area.set_margin_end(side_margin)
                center_area.set_margin_top(0)
                center_area.set_margin_bottom(max(6, top_margin // 2))

                grub_frame.set_size_request(max(1, w - (2 * side_margin)), -1)

                grub_frame.set_margin_top(0)
                grub_frame.set_margin_bottom(0)

                grub_container.set_margin_top(metrics["inner_pad_y"])
                grub_container.set_margin_bottom(metrics["inner_pad_y"])
                grub_container.set_margin_start(metrics["inner_pad_x"])
                grub_container.set_margin_end(metrics["inner_pad_x"])

                footer_box.set_margin_top(metrics["footer_gap"])
                footer_box.set_margin_start(side_margin)
                footer_box.set_margin_end(side_margin)
                footer_box.set_margin_bottom(top_margin)

            # Appliquer une première fois (taille par défaut), puis suivre le redimensionnement.
            _apply_text_layout(w=1100, h=820)
            last_size: tuple[int, int] = (0, 0)

            def _on_size_allocate(_widget: Gtk.Widget, allocation: Gdk.Rectangle) -> None:
                nonlocal last_size
                size = (int(allocation.width), int(allocation.height))
                if size == last_size or size[0] <= 0 or size[1] <= 0:
                    return
                last_size = size
                _apply_text_layout(w=size[0], h=size[1])

            try:
                dialog.connect("size-allocate", _on_size_allocate)
            except TypeError:
                # Certaines plateformes/backends peuvent ne pas exposer le signal; on garde la mise en page fixe.
                logger.debug("[GrubPreviewDialog] Signal size-allocate indisponible; layout fixe.")

            # Rendu du preview
            GrubPreviewRenderer.render_preview(
                container=grub_container,
                timeout=timeout,
                default_entry=default_entry,
                menu_entries=menu_entries,
                is_text_mode=True,
                show_title=False,
                show_footer=False,
            )
        else:
            # Mode graphique : rendu immersif (fond + menu positionné)
            preview_bg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            preview_bg.set_vexpand(True)
            preview_bg.set_hexpand(True)
            preview_bg.add_css_class("preview-bg-fallback")

            fixed = Gtk.Fixed()
            fixed.set_hexpand(True)
            fixed.set_vexpand(True)

            grub_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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
                show_title=False,
                show_footer=False,
            )

            grub_box.append(grub_container)
            fixed.put(grub_box, 0, 0)
            preview_bg.append(fixed)
            center_area.append(preview_bg)
            main_box.append(center_area)
            main_box.append(footer_box)

            def _apply_gfx_layout(*, w: int, h: int) -> None:
                left = _parse_layout_px(layout.menu_left, total=w)
                top = _parse_layout_px(layout.menu_top, total=h)
                width = _parse_layout_px(layout.menu_width, total=w)
                height = _parse_layout_px(layout.menu_height, total=h)

                x = max(0, left or 0)
                y = max(0, top or 0)
                fixed.move(grub_box, x, y)

                # Appliquer une taille explicite si définie
                if width is not None or height is not None:
                    grub_box.set_size_request(width or -1, height or -1)
                else:
                    grub_box.set_size_request(-1, -1)

            # Appliquer une première fois puis suivre le redimensionnement
            _apply_gfx_layout(w=1100, h=820)
            last_size: tuple[int, int] = (0, 0)

            def _on_gfx_size_allocate(_widget: Gtk.Widget, allocation: Gdk.Rectangle) -> None:
                nonlocal last_size
                size = (int(allocation.width), int(allocation.height))
                if size == last_size or size[0] <= 0 or size[1] <= 0:
                    return
                last_size = size
                _apply_gfx_layout(w=size[0], h=size[1])

            try:
                dialog.connect("size-allocate", _on_gfx_size_allocate)
            except TypeError:
                logger.debug("[GrubPreviewDialog] Signal size-allocate indisponible; layout gfx fixe.")

            # Marges pour header/footer en mode gfx (cadre déjà positionné via layout)
            def _apply_gfx_header_footer(*, w: int, h: int) -> None:
                metrics = compute_text_mode_metrics(width=w, height=h)
                m = metrics["outer_margin"]
                header_label.set_margin_top(m)
                header_label.set_margin_bottom(max(6, m // 2))
                footer_box.set_margin_top(metrics["footer_gap"])
                footer_box.set_margin_start(m)
                footer_box.set_margin_end(m)
                footer_box.set_margin_bottom(m)

            _apply_gfx_header_footer(w=1100, h=820)

        # Afficher
        dialog.set_child(main_box)
        dialog.present()

        logger.debug(f"[GrubPreviewDialog] Preview affiché - {len(menu_entries)} entrées")
