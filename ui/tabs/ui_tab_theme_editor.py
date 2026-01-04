"""Onglet de création et gestion de thèmes GRUB personnalisés."""

from __future__ import annotations

from gi.repository import Gdk, Gtk
from loguru import logger

from core.config.core_paths import get_grub_themes_dir
from core.theme.core_theme_generator import GrubTheme, ThemeGenerator, create_custom_theme
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog
from ui.ui_constants import COLOR_PRESETS
from ui.ui_gtk_helpers import GtkHelper
from ui.ui_widgets import (
    create_error_dialog,
    create_main_box,
    create_section_header,
    create_section_title,
    create_success_dialog,
)


class TabThemeEditor:
    """Onglet de création de thèmes GRUB."""

    def __init__(self, state_manager) -> None:
        """Initialise l'onglet de création de thèmes.

        Args:
            state_manager: Gestionnaire d'état de l'application
        """
        self.state_manager = state_manager
        self.current_theme: GrubTheme | None = None
        self._updating_ui = False  # Flag pour bloquer les événements pendant la mise à jour

        # Widgets de couleurs
        self.title_color_btn: Gtk.ColorButton | None = None
        self.bg_color_btn: Gtk.ColorButton | None = None
        self.menu_fg_btn: Gtk.ColorButton | None = None
        self.menu_bg_btn: Gtk.ColorButton | None = None
        self.highlight_fg_btn: Gtk.ColorButton | None = None
        self.highlight_bg_btn: Gtk.ColorButton | None = None

        # Widgets d'image
        self.bg_image_entry: Gtk.Entry | None = None
        self.bg_image_scale_combo: Gtk.DropDown | None = None

        # Widgets de mise en page
        self.show_boot_menu_check: Gtk.CheckButton | None = None
        self.show_progress_check: Gtk.CheckButton | None = None
        self.show_timeout_check: Gtk.CheckButton | None = None
        self.show_scrollbar_check: Gtk.CheckButton | None = None

        # Widget de nom
        self.theme_name_entry: Gtk.Entry | None = None

        # Widgets de titre et paramètres GRUB
        self.title_text_entry: Gtk.Entry | None = None
        self.grub_timeout_spin: Gtk.SpinButton | None = None
        self.grub_gfxmode_entry: Gtk.Entry | None = None

        # Zone de prévisualisation du code
        self.preview_buffer: Gtk.TextBuffer | None = None

        logger.info("[TabThemeEditor] Onglet initialisé")

    def build(self) -> Gtk.Box:
        """Construit l'interface de l'onglet.

        Returns:
            Container principal de l'onglet
        """
        main_box = create_main_box(spacing=12, margin=12)

        # En-tête
        header = create_section_header("Générateur de Thèmes GRUB")
        main_box.append(header)

        # === Conteneur 2 colonnes ===
        two_columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        two_columns.set_homogeneous(True)
        two_columns.set_hexpand(True)
        two_columns.set_vexpand(True)
        main_box.append(two_columns)

        # === COLONNE GAUCHE : Configuration ===
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_vexpand(True)
        left_scroll.set_hexpand(True)
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        left_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        left_content.set_margin_start(5)
        left_content.set_margin_end(5)
        left_content.set_margin_bottom(10)
        left_scroll.set_child(left_content)

        # Section: Informations du thème
        left_content.append(self._build_theme_info_section())

        # Section: Couleurs
        left_content.append(self._build_colors_section())

        # Section: Image de fond
        left_content.append(self._build_background_section())

        # Section: Options d'affichage
        left_content.append(self._build_display_options_section())

        two_columns.append(left_scroll)

        # === COLONNE DROITE : Prévisualisation et Actions ===
        right_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right_column.set_hexpand(True)
        right_column.set_vexpand(True)

        # Section: Prévisualisation
        # On veut que la preview prenne tout l'espace disponible
        preview_section = self._build_preview_section()
        preview_section.set_vexpand(True)
        right_column.append(preview_section)

        # Section: Actions (en bas)
        right_column.append(self._build_actions_section())

        two_columns.append(right_column)

        # Charger le thème par défaut
        self.load_default_theme()

        logger.success("[TabThemeEditor] Interface construite")
        return main_box

    def _build_theme_info_section(self) -> Gtk.Box:
        """Construit la section d'informations du thème."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = create_section_title("Informations")
        section.append(title)

        frame = Gtk.Frame()
        frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_box.set_margin_start(10)
        frame_box.set_margin_end(10)
        frame_box.set_margin_top(10)
        frame_box.set_margin_bottom(10)
        frame.set_child(frame_box)

        # Nom du thème
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        name_label = Gtk.Label(label="Nom du thème:")
        name_label.set_xalign(0)
        name_label.set_size_request(150, -1)
        name_box.append(name_label)

        self.theme_name_entry = Gtk.Entry()
        self.theme_name_entry.set_placeholder_text("mon_theme")
        self.theme_name_entry.set_hexpand(True)
        self.theme_name_entry.connect("changed", self._on_theme_property_changed)
        name_box.append(self.theme_name_entry)

        frame_box.append(name_box)

        # Titre affiché dans GRUB
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_label = Gtk.Label(label="Titre GRUB:")
        title_label.set_xalign(0)
        title_label.set_size_request(150, -1)
        title_box.append(title_label)

        self.title_text_entry = Gtk.Entry()
        self.title_text_entry.set_placeholder_text("Mon système Linux")
        self.title_text_entry.set_hexpand(True)
        self.title_text_entry.connect("changed", self._on_theme_property_changed)
        title_box.append(self.title_text_entry)

        frame_box.append(title_box)

        # Timeout
        timeout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        timeout_label = Gtk.Label(label="Délai d'attente (s):")
        timeout_label.set_xalign(0)
        timeout_label.set_size_request(150, -1)
        timeout_box.append(timeout_label)

        self.grub_timeout_spin = Gtk.SpinButton()
        self.grub_timeout_spin.set_range(0, 60)
        self.grub_timeout_spin.set_increments(1, 5)
        self.grub_timeout_spin.set_value(5)
        self.grub_timeout_spin.connect("value-changed", self._on_theme_property_changed)
        timeout_box.append(self.grub_timeout_spin)

        frame_box.append(timeout_box)

        # Résolution
        gfxmode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        gfxmode_label = Gtk.Label(label="Résolution:")
        gfxmode_label.set_xalign(0)
        gfxmode_label.set_size_request(150, -1)
        gfxmode_box.append(gfxmode_label)

        self.grub_gfxmode_entry = Gtk.Entry()
        self.grub_gfxmode_entry.set_text("auto")
        self.grub_gfxmode_entry.set_placeholder_text("auto ou 1920x1080")
        self.grub_gfxmode_entry.set_hexpand(True)
        self.grub_gfxmode_entry.connect("changed", self._on_theme_property_changed)
        gfxmode_box.append(self.grub_gfxmode_entry)

        frame_box.append(gfxmode_box)

        section.append(frame)
        return section

    def _build_colors_section(self) -> Gtk.Box:
        """Construit la section de configuration des couleurs."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = create_section_title("Couleurs")
        section.append(title)

        frame = Gtk.Frame()
        frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_box.set_margin_start(10)
        frame_box.set_margin_end(10)
        frame_box.set_margin_top(10)
        frame_box.set_margin_bottom(10)
        frame.set_child(frame_box)

        # Grille de couleurs en 2 colonnes
        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(24)
        grid.set_margin_top(10)
        grid.set_column_homogeneous(False)
        grid.add_css_class("color-grid")

        # Colonne gauche
        self.title_color_btn = self._add_color_picker(grid, 0, 0, "Titre:", "#FFFFFF")
        self.bg_color_btn = self._add_color_picker(grid, 1, 0, "Fond:", "#000000")
        self.menu_fg_btn = self._add_color_picker(grid, 2, 0, "Texte menu:", "#FFFFFF")

        # Colonne droite
        self.menu_bg_btn = self._add_color_picker(grid, 0, 2, "Fond menu:", "#000000")
        self.highlight_fg_btn = self._add_color_picker(grid, 1, 2, "Texte sélection:", "#000000")
        self.highlight_bg_btn = self._add_color_picker(grid, 2, 2, "Fond sélection:", "#D3D3D3")

        frame_box.append(grid)

        section.append(frame)
        return section

    def _add_color_picker(  # pylint: disable=too-many-positional-arguments
        self, grid: Gtk.Grid, row: int, col: int, label_text: str, default_color: str
    ) -> Gtk.ColorButton:
        """Ajoute un sélecteur de couleur en format carré."""
        # Container horizontal pour label + bouton
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        container.set_halign(Gtk.Align.START)

        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        label.set_size_request(120, -1)
        container.append(label)

        color_btn = Gtk.ColorButton()
        color_btn.set_property("use-alpha", False)
        # Taille carrée forcée via CSS
        color_btn.set_size_request(50, 50)

        # Convertir la couleur hex en RGBA
        rgba = self._parse_color(default_color)
        color_btn.set_property("rgba", rgba)
        color_btn.connect("color-set", self._on_theme_property_changed)
        container.append(color_btn)

        grid.attach(container, col, row, 2, 1)

        return color_btn

    def _parse_color(self, color_str: str) -> object:
        """Parse une couleur (hex ou nom) en RGBA."""
        rgba = Gdk.RGBA()
        color_str = COLOR_PRESETS.get(color_str.lower(), color_str)
        rgba.parse(color_str)
        return rgba

    def _color_to_hex(self, rgba: object) -> str:
        """Convertit un RGBA en hex."""
        return f"#{int(rgba.red * 255):02x}{int(rgba.green * 255):02x}{int(rgba.blue * 255):02x}"

    def _build_background_section(self) -> Gtk.Box:
        """Construit la section de configuration de l'image de fond."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = create_section_title("Image de fond (optionnel)")
        section.append(title)

        frame = Gtk.Frame()
        frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_box.set_margin_start(10)
        frame_box.set_margin_end(10)
        frame_box.set_margin_top(10)
        frame_box.set_margin_bottom(10)
        frame.set_child(frame_box)

        # Chemin de l'image
        img_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        img_label = Gtk.Label(label="Chemin de l'image:")
        img_label.set_xalign(0)
        img_label.set_size_request(150, -1)
        img_box.append(img_label)

        self.bg_image_entry = Gtk.Entry()
        self.bg_image_entry.set_placeholder_text("/boot/grub/themes/mon_theme/background.png")
        self.bg_image_entry.set_hexpand(True)
        self.bg_image_entry.connect("changed", self._on_theme_property_changed)
        img_box.append(self.bg_image_entry)

        frame_box.append(img_box)

        # Méthode de mise à l'échelle
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        scale_label = Gtk.Label(label="Mise à l'échelle:")
        scale_label.set_xalign(0)
        scale_label.set_size_request(150, -1)
        scale_box.append(scale_label)

        scale_methods = Gtk.StringList()
        for method in ["stretch", "crop", "padding", "fitwidth", "fitheight"]:
            scale_methods.append(method)

        self.bg_image_scale_combo = Gtk.DropDown(model=scale_methods)
        self.bg_image_scale_combo.set_selected(0)  # stretch par défaut
        self.bg_image_scale_combo.connect("notify::selected", self._on_theme_property_changed)
        scale_box.append(self.bg_image_scale_combo)

        frame_box.append(scale_box)

        section.append(frame)
        return section

    def _build_display_options_section(self) -> Gtk.Box:
        """Construit la section des options d'affichage."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = create_section_title("Options d'affichage")
        section.append(title)

        frame = Gtk.Frame()
        frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_box.set_margin_start(10)
        frame_box.set_margin_end(10)
        frame_box.set_margin_top(10)
        frame_box.set_margin_bottom(10)
        frame.set_child(frame_box)

        self.show_boot_menu_check = Gtk.CheckButton(label="Afficher le menu de démarrage")
        self.show_boot_menu_check.set_active(True)
        self.show_boot_menu_check.connect("toggled", self._on_theme_property_changed)
        frame_box.append(self.show_boot_menu_check)

        self.show_progress_check = Gtk.CheckButton(label="Afficher la barre de progression")
        self.show_progress_check.set_active(True)
        self.show_progress_check.connect("toggled", self._on_theme_property_changed)
        frame_box.append(self.show_progress_check)

        self.show_timeout_check = Gtk.CheckButton(label="Afficher le message de timeout")
        self.show_timeout_check.set_active(True)
        self.show_timeout_check.connect("toggled", self._on_theme_property_changed)
        frame_box.append(self.show_timeout_check)

        self.show_scrollbar_check = Gtk.CheckButton(label="Afficher la barre de défilement")
        self.show_scrollbar_check.set_active(True)
        self.show_scrollbar_check.connect("toggled", self._on_theme_property_changed)
        frame_box.append(self.show_scrollbar_check)

        section.append(frame)
        return section

    def _build_preview_section(self) -> Gtk.Box:
        """Construit la section de prévisualisation du code."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = create_section_title("Aperçu du fichier theme.txt")
        section.append(title)

        frame = Gtk.Frame()
        frame.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_monospace(True)
        text_view.set_margin_start(10)
        text_view.set_margin_end(10)
        text_view.set_margin_top(10)
        text_view.set_margin_bottom(10)

        self.preview_buffer = text_view.get_buffer()

        scrolled.set_child(text_view)
        frame.set_child(scrolled)

        section.append(frame)
        return section

    def _build_actions_section(self) -> Gtk.Box:
        """Construit la section des boutons d'actions."""
        section = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        section.set_halign(Gtk.Align.END)

        # Bouton pour charger un thème prédéfini
        load_preset_btn = Gtk.Button(label="Charger un thème prédéfini")
        load_preset_btn.connect("clicked", self._on_load_preset)
        section.append(load_preset_btn)

        # Bouton aperçu
        preview_btn = Gtk.Button(label="Aperçu GRUB")
        preview_btn.connect("clicked", self._on_preview_grub)
        section.append(preview_btn)

        # Bouton pour sauvegarder
        save_btn = Gtk.Button(label="Sauvegarder le thème")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_theme)
        section.append(save_btn)

        return section

    def load_default_theme(self) -> None:
        """Charge un thème par défaut dans l'interface."""
        self.current_theme = create_custom_theme("mon_theme")
        self._updating_ui = True
        self._update_ui_from_theme()
        self._updating_ui = False
        self._update_preview()

    def _update_ui_from_theme(self) -> None:
        """Met à jour l'interface depuis le thème actuel."""
        if not self.current_theme:
            return

        theme = self.current_theme

        self.theme_name_entry.set_text(theme.name)
        self.title_text_entry.set_text(theme.title_text)
        self.grub_timeout_spin.set_value(theme.grub_timeout)
        self.grub_gfxmode_entry.set_text(theme.grub_gfxmode)

        self.title_color_btn.set_property("rgba", self._parse_color(theme.colors.title_color))
        self.bg_color_btn.set_property("rgba", self._parse_color(theme.colors.desktop_color))
        self.menu_fg_btn.set_property("rgba", self._parse_color(theme.colors.menu_normal_fg))
        self.menu_bg_btn.set_property("rgba", self._parse_color(theme.colors.menu_normal_bg))
        self.highlight_fg_btn.set_property("rgba", self._parse_color(theme.colors.menu_highlight_fg))
        self.highlight_bg_btn.set_property("rgba", self._parse_color(theme.colors.menu_highlight_bg))

        self.bg_image_entry.set_text(theme.image.desktop_image)

        self.show_boot_menu_check.set_active(theme.show_boot_menu)
        self.show_progress_check.set_active(theme.show_progress_bar)
        self.show_timeout_check.set_active(theme.show_timeout_message)
        self.show_scrollbar_check.set_active(theme.show_scrollbar)

    def _update_theme_from_ui(self) -> None:
        """Met à jour le thème depuis les valeurs de l'interface."""
        name = self.theme_name_entry.get_text().strip() or "mon_theme"

        self.current_theme = create_custom_theme(
            name=name,
            title_color=self._color_to_hex(self.title_color_btn.get_property("rgba")),
            background_color=self._color_to_hex(self.bg_color_btn.get_property("rgba")),
            menu_fg=self._color_to_hex(self.menu_fg_btn.get_property("rgba")),
            menu_bg=self._color_to_hex(self.menu_bg_btn.get_property("rgba")),
            highlight_fg=self._color_to_hex(self.highlight_fg_btn.get_property("rgba")),
            highlight_bg=self._color_to_hex(self.highlight_bg_btn.get_property("rgba")),
            background_image=self.bg_image_entry.get_text().strip(),
        )

        self.current_theme.show_boot_menu = self.show_boot_menu_check.get_active()
        self.current_theme.show_progress_bar = self.show_progress_check.get_active()
        self.current_theme.show_timeout_message = self.show_timeout_check.get_active()
        self.current_theme.show_scrollbar = self.show_scrollbar_check.get_active()

        self.current_theme.title_text = self.title_text_entry.get_text().strip()
        self.current_theme.grub_timeout = int(self.grub_timeout_spin.get_value())
        self.current_theme.grub_gfxmode = self.grub_gfxmode_entry.get_text().strip() or "auto"

        # Méthode de mise à l'échelle
        scale_idx = self.bg_image_scale_combo.get_selected()
        scale_methods = ["stretch", "crop", "padding", "fitwidth", "fitheight"]
        self.current_theme.image.desktop_image_scale_method = scale_methods[scale_idx]

    def _update_preview(self) -> None:
        """Met à jour la prévisualisation du code theme.txt."""
        if not self.current_theme:
            return

        code = ThemeGenerator.generate_theme_txt(self.current_theme)
        self.preview_buffer.set_text(code)

    def _on_theme_property_changed(self, _widget) -> None:
        """Appelé quand une propriété du thème change."""
        if self._updating_ui:
            return  # Évite les boucles infinies lors de la mise à jour de l'UI
        self._update_theme_from_ui()
        self._update_preview()

    def _on_load_preset(self, button: Gtk.Button) -> None:
        """Charge un thème prédéfini."""
        # Créer un dialog de sélection
        dialog = Gtk.AlertDialog()
        dialog.set_message("Charger un thème prédéfini")
        dialog.set_detail("Choisissez un thème parmi les modèles disponibles:")
        dialog.set_buttons(["Classic", "Dark", "Blue", "Matrix", "Annuler"])
        dialog.set_default_button(0)
        dialog.set_cancel_button(4)

        dialog.choose(
            parent=GtkHelper.resolve_parent_window(button),
            cancellable=None,
            callback=self._on_preset_selected,
        )

    def _on_preset_selected(self, dialog: Gtk.AlertDialog, result) -> None:
        """Appelé quand un thème prédéfini est sélectionné."""
        try:
            choice = dialog.choose_finish(result)

            presets = ThemeGenerator.create_default_themes()
            preset_names = ["classic", "dark", "blue", "matrix"]

            if choice < len(preset_names):
                preset_name = preset_names[choice]
                self.current_theme = next((t for t in presets if t.name == preset_name), None)

                if self.current_theme:
                    self._updating_ui = True
                    self._update_ui_from_theme()
                    self._updating_ui = False
                    self._update_preview()
                    logger.info(f"[TabThemeEditor] Thème prédéfini chargé: {preset_name}")

        except (OSError, RuntimeError) as e:
            logger.debug(f"[TabThemeEditor] Sélection de thème annulée: {e}")

    def _on_preview_grub(self, _button: Gtk.Button) -> None:
        """Affiche un aperçu GRUB avec le thème actuel."""
        if not self.current_theme:
            self._show_error("Créez ou chargez un thème pour voir l'aperçu")
            return

        try:
            preview = GrubPreviewDialog(self.current_theme, self.current_theme.name or "Édition")
            preview.show()
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeEditor] Erreur lors de l'aperçu: {e}")
            self._show_error(f"Erreur lors de l'aperçu:\n{e}")

    def _on_save_theme(self, _button: Gtk.Button) -> None:
        """Sauvegarde le thème actuel."""
        if not self.current_theme:
            self._show_error("Aucun thème à sauvegarder")
            return

        try:
            # Vérifier le nom
            if not self.current_theme.name or self.current_theme.name.strip() == "":
                self._show_error("Le nom du thème ne peut pas être vide")
                return

            # Créer le répertoire des thèmes
            themes_dir = get_grub_themes_dir()

            # Sauvegarder
            theme_file = ThemeGenerator.save_theme(self.current_theme, themes_dir)

            # Succès
            self._show_success(
                f"Thème sauvegardé avec succès!\n\n"
                f"Fichier: {theme_file}\n\n"
                f'Pour l\'activer, définissez GRUB_THEME="{theme_file}" '
                f"dans /etc/default/grub et exécutez update-grub."
            )

        except OSError as e:
            logger.error(f"[TabThemeEditor] Erreur lors de la sauvegarde: {e}")
            self._show_error(f"Erreur lors de la sauvegarde:\n{e}")

    def _show_error(self, message: str) -> None:
        """Affiche un message d'erreur."""
        create_error_dialog(message)

    def _show_success(self, message: str) -> None:
        """Affiche un message de succès."""
        create_success_dialog(message)
