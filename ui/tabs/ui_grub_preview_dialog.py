"""Dialog pour afficher un aperçu réaliste du menu GRUB.

Utilisé par tab_theme_config et tab_theme_editor pour prévisualiser
les thèmes avec la configuration réelle du système.
"""

from __future__ import annotations

import os
from gi.repository import Gtk, Gdk, Gio
from loguru import logger

from core.services.core_grub_service import GrubConfig, GrubService, MenuEntry
from core.models.core_theme_models import GrubTheme
from core.models.core_grub_ui_model import GrubUiModel


class GrubPreviewDialog:
    """Dialog pour prévisualiser un thème GRUB."""

    # pylint: disable=too-few-public-methods

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
        # Créer le dialog
        dialog = Gtk.Window()
        dialog.set_title(f"Aperçu GRUB: {self.theme_name}")
        dialog.set_default_size(1000, 700)
        dialog.set_modal(True)

        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)

        # Titre
        title = Gtk.Label()
        title.set_markup(f"<b>Aperçu du menu GRUB avec {self.theme_name}</b>")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("section-title")
        main_box.append(title)

        # Zone de prévisualisation GRUB avec Overlay pour le fond
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)

        # Image de fond
        bg_widget = Gtk.Picture()
        # Gtk.Picture.set_keep_aspect_ratio est déprécié en GTK4.
        # On veut un comportement "stretch" proche de GRUB.
        if hasattr(bg_widget, "set_content_fit"):
            bg_widget.set_content_fit(Gtk.ContentFit.FILL)
        else:
            bg_widget.set_keep_aspect_ratio(False)
        bg_widget.set_overflow(Gtk.Overflow.HIDDEN)
        
        # Déterminer l'image de fond
        bg_path = ""
        if self.theme and self.theme.image.desktop_image:
            bg_path = self.theme.image.desktop_image
        elif self.model and self.model.grub_background:
            bg_path = self.model.grub_background
            
        if bg_path and os.path.exists(bg_path):
            try:
                bg_widget.set_filename(bg_path)
                bg_widget.add_css_class("preview-bg")
            except Exception as e:
                logger.warning(f"[GrubPreviewDialog] Impossible de charger l'image {bg_path}: {e}")
        else:
            # Fond noir par défaut
            bg_widget.add_css_class("preview-bg-fallback")

        overlay.set_child(bg_widget)

        # Contenu du menu par dessus
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        preview_box.set_margin_start(40)
        preview_box.set_margin_end(40)
        preview_box.set_margin_top(40)
        preview_box.set_margin_bottom(40)
        preview_box.set_valign(Gtk.Align.CENTER)
        preview_box.set_halign(Gtk.Align.CENTER)
        preview_box.add_css_class("grub-menu-container")

        # Remplir avec le contenu du preview
        self._create_grub_preview(preview_box)

        overlay.add_overlay(preview_box)
        
        # Frame pour la bordure
        frame = Gtk.Frame()
        frame.set_child(overlay)
        main_box.append(frame)

        # Bouton fermer
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)

        close_btn = Gtk.Button(label="Fermer")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", lambda b: dialog.close())
        button_box.append(close_btn)

        main_box.append(button_box)

        # Appliquer du CSS personnalisé pour l'aperçu
        self._apply_preview_styles(dialog)

        dialog.set_child(main_box)
        dialog.present()

    def _apply_preview_styles(self, window: Gtk.Window) -> None:
        """Applique des styles CSS pour rendre l'aperçu plus fidèle."""
        css_provider = Gtk.CssProvider()
        
        # Valeurs par défaut (Mode Simple ou Fallback)
        fg_color = "white"
        bg_color = "rgba(0, 0, 0, 0.5)" # Semi-transparent par défaut pour le menu
        hl_fg = "black"
        hl_bg = "#D3D3D3" # light-gray
        
        title_color = "white"
        title_font = "DejaVu Sans Bold 14pt"
        entry_font = "DejaVu Sans Mono 12pt"
        
        # Mise en page par défaut
        menu_top = "20%"
        menu_left = "15%"
        menu_width = "70%"
        menu_height = "auto"

        def parse_grub_color(grub_color: str, default: str) -> str:
            if not grub_color:
                return default
            # Gérer le format fg/bg ou juste fg
            fg = grub_color.split("/")[0].strip() if "/" in grub_color else grub_color.strip()
            
            color_map = {
                "light-gray": "#D3D3D3",
                "dark-gray": "#555555",
                "black": "black",
                "white": "white",
                "red": "red",
                "green": "green",
                "blue": "blue",
                "cyan": "cyan",
                "magenta": "magenta",
                "yellow": "yellow"
            }
            return color_map.get(fg, fg)

        # 1. Priorité au thème si activé
        if self.model and self.model.theme_management_enabled and self.theme:
            fg_color = parse_grub_color(self.theme.colors.menu_normal_fg, "white")
            
            # Si le fond du menu est noir dans un thème, c'est souvent transparent
            theme_bg = self.theme.colors.menu_normal_bg
            if theme_bg == "black":
                bg_color = "rgba(0, 0, 0, 0.4)"
            else:
                bg_color = parse_grub_color(theme_bg, "rgba(0, 0, 0, 0.4)")
            
            hl_fg = parse_grub_color(self.theme.colors.menu_highlight_fg, "black")
            hl_bg = parse_grub_color(self.theme.colors.menu_highlight_bg, "#D3D3D3")
            
            title_color = parse_grub_color(self.theme.colors.title_color, "white")
            
            # Layout
            if self.theme.layout:
                menu_top = self.theme.layout.menu_top
                menu_left = self.theme.layout.menu_left
                menu_width = self.theme.layout.menu_width
                menu_height = self.theme.layout.menu_height
            
            # Fonts (simplifié pour GTK)
            if self.theme.fonts:
                # On essaie de convertir le format GRUB "DejaVu Sans Bold 16" en CSS
                title_font = self.theme.fonts.title_font.replace("Regular", "").strip()
                entry_font = self.theme.fonts.terminal_font.replace("Regular", "").strip()
        
        # 2. Sinon utiliser la configuration simple du modèle
        elif self.model:
            fg_color = parse_grub_color(self.model.grub_color_normal, "white")
            hl_fg = parse_grub_color(self.model.grub_color_highlight, "black")
            
            # En mode simple, GRUB n'a pas de boîte de menu, mais on en garde une pour la lisibilité
            bg_color = "rgba(0, 0, 0, 0.6)"

        css = f"""
            .preview-bg {{
                background-color: black;
            }}
            .preview-bg-fallback {{
                background-color: #000044; /* Bleu GRUB classique */
            }}
            .grub-menu-container {{
                background-color: {bg_color};
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 20px;
                margin-top: {menu_top};
                margin-left: {menu_left};
                width: {menu_width};
                height: {menu_height};
            }}
            .grub-entry {{
                color: {fg_color};
                font-family: {entry_font};
                padding: 4px 10px;
                margin: 2px 0;
            }}
            .grub-entry-selected {{
                color: {hl_fg};
                background-color: {hl_bg};
                font-weight: bold;
                border-radius: 2px;
            }}
            .grub-title {{
                color: {title_color};
                font-family: {title_font};
                margin-bottom: 20px;
                font-weight: bold;
            }}
            .grub-info {{
                color: rgba(255, 255, 255, 0.7);
                font-family: {entry_font};
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
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_grub_preview(self, container: Gtk.Box) -> None:
        """Crée un aperçu réaliste du menu GRUB.

        Args:
            container: Container où placer le preview
        """
        # pylint: disable=too-many-locals,too-many-statements
        try:
            # Utiliser le modèle si disponible, sinon le service
            if self.model:
                timeout = self.model.timeout
                default_entry = self.model.default
                gfxmode = self.model.gfxmode
            else:
                config = GrubService.read_current_config()
                timeout = config.timeout
                default_entry = config.default_entry
                gfxmode = config.grub_gfxmode
                
            menu_entries = GrubService.get_menu_entries()
        except (OSError, RuntimeError) as e:
            logger.warning(f"[GrubPreviewDialog] Erreur lecture config: {e}")
            timeout = 10
            default_entry = "0"
            gfxmode = "auto"
            menu_entries = [MenuEntry(title="Ubuntu", id="gnulinux")]

        # Titre du système
        title_label = Gtk.Label(label="GNU GRUB version 2.12")
        title_label.add_css_class("grub-title")
        container.append(title_label)

        # Menu entries
        # Déterminer l'index par défaut (peut être un index, un titre ou un ID)
        default_index = 0
        try:
            # Cas 1: Index numérique (ex: "0" ou "1>2")
            if default_entry.isdigit():
                default_index = int(default_entry)
            elif ">" in default_entry and default_entry.split(">")[0].isdigit():
                default_index = int(default_entry.split(">")[0])
            else:
                # Cas 2: Titre ou ID
                for i, entry in enumerate(menu_entries):
                    if entry.title == default_entry or entry.id == default_entry:
                        default_index = i
                        break
        except (ValueError, IndexError):
            default_index = 0

        for i, entry in enumerate(menu_entries):
            is_selected = i == default_index
            
            entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            entry_box.add_css_class("grub-entry")
            
            if is_selected:
                entry_box.add_css_class("grub-entry-selected")
                # GRUB utilise souvent une bordure ou un fond différent, 
                # mais l'astérisque est classique pour le mode texte
                marker = Gtk.Label(label="*")
                entry_box.append(marker)
            else:
                # Espace pour aligner
                spacer = Gtk.Label(label=" ")
                entry_box.append(spacer)

            label = Gtk.Label(label=entry.title)
            label.set_halign(Gtk.Align.START)
            entry_box.append(label)
            container.append(entry_box)

        # Aide en bas (plus fidèle à GRUB)
        help_text = (
            "Utilisez les touches \u2191 et \u2193 pour sélectionner l'entrée en surbrillance.\n"
            "Appuyez sur Entrée pour démarrer l'OS sélectionné, 'e' pour éditer les\n"
            "commandes avant le démarrage ou 'c' pour une ligne de commande."
        )
        if timeout >= 0:
            help_text += f"\n\nL'entrée sélectionnée sera démarrée automatiquement dans {timeout}s."
            
        help_label = Gtk.Label(label=help_text)
        help_label.set_justify(Gtk.Justification.CENTER)
        help_label.add_css_class("grub-info")
        container.append(help_label)

        logger.debug("[GrubPreviewDialog] Preview créé")
