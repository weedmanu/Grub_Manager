"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.models.core_theme_models import GrubTheme
from core.services.core_grub_script_service import GrubScriptService
from core.services.core_theme_service import ThemeService
from core.theme.core_active_theme_manager import ActiveThemeManager
from ui.components.ui_theme_config_actions import build_theme_config_right_column
from ui.components.ui_theme_scripts_list import ThemeScriptsList
from ui.components.ui_theme_simple_config import ThemeSimpleConfigPanel
from ui.components.ui_theme_simple_config_logic import apply_simple_theme_config_from_widgets
from ui.tabs.theme_config import ui_theme_config_handlers as handlers
from ui.ui_constants import GRUB_COLORS
from ui.ui_file_dialogs import open_image_file_dialog
from ui.ui_widgets import create_main_box, create_two_column_layout

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


class TabThemeConfig:
    """Onglet pour sélectionner et configurer le thème GRUB."""

    def __init__(self, state_manager: Any, window: Gtk.Window | None = None) -> None:
        """Initialise l'onglet de configuration de thème.

        Args:
            state_manager: Gestionnaire d'état global.
            window: Fenêtre parente (optionnel).
        """
        self.state_manager = state_manager
        self.current_theme: GrubTheme | None = None
        self.theme_manager = ActiveThemeManager()
        self.script_service = GrubScriptService()
        self.theme_service = ThemeService()
        self.available_themes: dict[str, GrubTheme] = {}
        self.theme_paths: dict[str, Path] = {}  # Pour stocker le chemin de chaque thème
        self.parent_window: Gtk.Window | None = window
        self._updating_ui: bool = False

        # Référence conservée sur la fenêtre du générateur interactif.
        # (Compat tests: certains tests vérifient la présence/absence de cet attribut.)
        self._interactive_theme_generator_window: Gtk.Window | None = None

        # Widgets
        self.theme_list_box: Gtk.ListBox | None = None
        self.current_script: Any = None
        self.preview_btn: Gtk.Button | None = None
        self.activate_theme_btn: Gtk.Button | None = None
        self.deactivate_theme_btn: Gtk.Button | None = None
        self.edit_btn: Gtk.Button | None = None
        self.delete_btn: Gtk.Button | None = None
        self.theme_switch: Gtk.Switch | None = None

        # Compat tests (anciens attributs)
        self.scripts_list_box: Gtk.ListBox | None = None

        # Compat tests (anciens widgets de config simple)
        self.bg_image_entry: Gtk.Entry | None = None
        self.normal_fg_combo: Gtk.DropDown | None = None
        self.normal_bg_combo: Gtk.DropDown | None = None
        self.highlight_fg_combo: Gtk.DropDown | None = None
        self.highlight_bg_combo: Gtk.DropDown | None = None

        # Composants
        self.simple_config_panel: ThemeSimpleConfigPanel | None = None
        self.scripts_list: ThemeScriptsList | None = None

        # Sections à afficher/masquer avec le switch
        self.theme_sections_container: Gtk.Box | None = None
        self.simple_config_container: Gtk.Box | None = None

        logger.debug("[TabThemeConfig.__init__] Onglet initialisé")

    def mark_dirty(self) -> None:
        """Marque l'état comme modifié."""
        save_btn = getattr(self.parent_window, "save_btn", None)
        reload_btn = getattr(self.parent_window, "reload_btn", None)
        if save_btn and reload_btn:
            self.state_manager.mark_dirty(save_btn, reload_btn)

    # Compat: ancien nom (évite de casser d'anciens appels/tests).
    def _mark_dirty(self) -> None:  # pylint: disable=invalid-name
        self.mark_dirty()

    def set_interactive_theme_generator_window(self, window: Gtk.Window) -> None:
        """Conserve une référence Python à la fenêtre du générateur."""
        self._interactive_theme_generator_window = window

    def clear_interactive_theme_generator_window(self) -> None:
        """Supprime la référence au générateur, si présente."""
        try:
            delattr(self, "_interactive_theme_generator_window")
        except AttributeError:
            pass

    def build(self) -> Gtk.Box:
        """Construit l'interface utilisateur de l'onglet.

        Returns:
            Widget racine de l'onglet.
        """
        main_box = create_main_box(spacing=12, margin=12)

        self._build_header(main_box)

        switch_section = self._build_switch_section()
        main_box.append(switch_section)

        # Séparateur
        separator = Gtk.Separator(orientation=HORIZONTAL)
        main_box.append(separator)

        # === SECTION 1: Configuration Simple (Switch OFF) ===
        self.simple_config_container = self._build_simple_config_section()
        main_box.append(self.simple_config_container)

        # === SECTION 2: Gestion Complète des Thèmes (Switch ON) ===
        # Conteneur pour toutes les sections de thèmes (masquable)
        self.theme_sections_container, left_section, right_section = create_two_column_layout(main_box)

        self._build_left_column(left_section)
        self._build_right_column(right_section)

        # Initialement masqué (sera géré par _load_themes)
        self.theme_sections_container.set_visible(False)
        self.simple_config_container.set_visible(True)

        # Charger les thèmes
        self._load_themes()

        return main_box

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        if self.scripts_list is not None:
            self.scripts_list.refresh()
        self.scan_system_themes()

    def _build_header(self, container: Gtk.Box) -> None:
        """Construit l'en-tête de l'onglet."""
        header_label = Gtk.Label(xalign=0)
        header_label.set_markup("<b>Configuration du Thème</b>")
        header_label.add_css_class("section-title")
        container.append(header_label)

        desc_label = Gtk.Label(xalign=0, label="Gérez l'apparence du menu de démarrage GRUB.")
        desc_label.add_css_class("dim-label")
        desc_label.add_css_class("subtitle-label")
        desc_label.set_margin_bottom(12)
        container.append(desc_label)

    def _build_left_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de gauche (liste des thèmes)."""
        list_title = Gtk.Label(xalign=0)
        list_title.set_markup("<b>Thèmes disponibles</b>")
        list_title.add_css_class("section-title")
        container.append(list_title)

        # Frame + Scrolled window pour harmoniser avec les autres onglets
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        frame.set_hexpand(True)
        container.append(frame)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.theme_list_box = Gtk.ListBox()
        self.theme_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.theme_list_box.add_css_class("rich-list")
        self.theme_list_box.connect("row-selected", lambda lb, row: handlers.on_theme_selected(lb, row, self))

        scrolled.set_child(self.theme_list_box)
        frame.set_child(scrolled)

    def _build_simple_config_section(self) -> Gtk.Box:
        """Construit la section de configuration simple (couleurs et fond)."""
        container = Gtk.Box(orientation=VERTICAL, spacing=15)
        container.set_margin_top(10)
        container.set_margin_bottom(10)
        container.set_margin_start(10)
        container.set_margin_end(10)

        # Panneau de configuration simple
        self.simple_config_panel = ThemeSimpleConfigPanel(state_manager=self.state_manager, on_changed=self.mark_dirty)
        container.append(self.simple_config_panel)

        # Aliases attendus par certains tests/anciens appels.
        self.bg_image_entry = self.simple_config_panel.bg_image_entry
        self.normal_fg_combo = self.simple_config_panel.normal_fg_combo
        self.normal_bg_combo = self.simple_config_panel.normal_bg_combo
        self.highlight_fg_combo = self.simple_config_panel.highlight_fg_combo
        self.highlight_bg_combo = self.simple_config_panel.highlight_bg_combo

        # Séparateur
        sep = Gtk.Separator(orientation=HORIZONTAL)
        sep.set_margin_top(15)
        sep.set_margin_bottom(15)
        container.append(sep)

        # Liste des scripts
        self.scripts_list = ThemeScriptsList(state_manager=self.state_manager, script_service=self.script_service)
        # Expose la listbox pour compatibilité avec les tests/anciens appels.
        self.scripts_list_box = self.scripts_list.scripts_list_box
        container.append(self.scripts_list)

        return container

    def _on_select_bg_image(self, button: Gtk.Button) -> None:
        """Ouvre un sélecteur de fichier pour l'image de fond (compat tests)."""
        open_image_file_dialog(
            gtk_module=Gtk,
            button=button,
            title="Choisir une image de fond",
            parent_window=self.parent_window,
            on_selected=lambda path: self.bg_image_entry.set_text(path) if self.bg_image_entry else None,
        )

    def _on_bg_image_selected(self, dialog: Gtk.FileDialog, result) -> None:
        """Callback après sélection de l'image (compat tests)."""
        try:
            file = dialog.open_finish(result)
            if file and self.bg_image_entry:
                self.bg_image_entry.set_text(file.get_path())
        except (OSError, RuntimeError) as e:
            logger.warning(f"[TabThemeConfig] Sélection d'image annulée ou échouée: {e}")

    def _on_simple_config_changed(self, *_) -> None:
        """Met à jour le modèle depuis la config simple (compat tests)."""
        if self._updating_ui:
            return
        try:
            updated = apply_simple_theme_config_from_widgets(
                state_manager=self.state_manager,
                colors=list(GRUB_COLORS),
                bg_image_entry=self.bg_image_entry,
                normal_fg_combo=self.normal_fg_combo,
                normal_bg_combo=self.normal_bg_combo,
                highlight_fg_combo=self.highlight_fg_combo,
                highlight_bg_combo=self.highlight_bg_combo,
            )
        except (AttributeError, IndexError) as exc:
            logger.debug(f"[TabThemeConfig] Widgets incomplets/invalides: {exc}")
            return

        if updated:
            self.mark_dirty()

    def _build_right_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite (actions)."""
        parts = build_theme_config_right_column(
            on_preview=lambda: handlers.on_preview_theme(self),
            on_activate_theme=lambda b: handlers.on_activate_theme(b, self),
            on_deactivate_theme=lambda b: handlers.on_deactivate_theme(b, self),
            on_edit=lambda b: handlers.on_edit_theme(b, self.current_theme.name, self) if self.current_theme else None,
            on_delete=lambda b: (
                handlers.on_delete_theme(b, self.current_theme.name, self) if self.current_theme else None
            ),
            on_open_editor=lambda b: handlers.on_open_editor(self, b),
        )

        self.preview_btn = parts.preview_btn
        self.activate_theme_btn = parts.activate_theme_btn
        self.deactivate_theme_btn = parts.deactivate_theme_btn
        self.edit_btn = parts.edit_btn
        self.delete_btn = parts.delete_btn
        # self.activate_script_btn et self.deactivate_script_btn sont maintenant dans _build_simple_config_section

        container.append(parts.actions_title)
        container.append(parts.actions_box)
        container.append(parts.global_actions_box)

    def _build_switch_section(self) -> Gtk.Widget:
        """Construit la section de switch pour afficher/masquer les thèmes.

        Returns:
            Widget de la section.
        """
        box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        box.set_margin_bottom(10)

        # Utilisation d'un style "card" ou "box" pour le switch principal
        box.add_css_class("info-box")

        label = Gtk.Label(label="Activer la gestion des thèmes GRUB")
        label.set_markup("<b>Activer la gestion des thèmes GRUB</b>")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)

        self.theme_switch = Gtk.Switch()
        self.theme_switch.set_halign(Gtk.Align.END)
        self.theme_switch.set_valign(Gtk.Align.CENTER)
        self.theme_switch.connect("notify::active", lambda sw, _p: handlers.on_theme_switch_toggled(sw, _p, self))
        box.append(self.theme_switch)

        return box

    # _build_theme_list_section et _build_actions_section sont supprimés car intégrés dans build()

    def load_themes(self) -> None:
        """Charge la configuration du thème depuis le modèle et met à jour l'UI."""
        # Utiliser l'état du modèle chargé (basé sur les scripts)
        if not self.state_manager.state_data or not self.state_manager.state_data.model:
            logger.debug("[TabThemeConfig.load_themes] Pas de modèle disponible")
            return

        # On bloque les mises à jour de l'UI vers le modèle pendant le chargement
        self._updating_ui = True
        try:
            model = self.state_manager.state_data.model
            theme_enabled = model.theme_management_enabled
            logger.info(
                f"[TabThemeConfig.load_themes] Chargement config thème - theme_management_enabled={theme_enabled}"
            )

            # Définir l'état du switch
            if self.theme_switch:
                self.theme_switch.set_active(theme_enabled)
                logger.debug(f"[TabThemeConfig.load_themes] Switch mis à {theme_enabled}")

                # Afficher les sections si activé
                if self.theme_sections_container:
                    self.theme_sections_container.set_visible(theme_enabled)
                if self.simple_config_container:
                    self.simple_config_container.set_visible(not theme_enabled)

            # === Charger la config simple ===
            if self.simple_config_panel:
                self.simple_config_panel.update_from_model(model)

            # Charger le thème actif s'il existe
            try:
                active_theme = self.theme_manager.load_active_theme()
                if active_theme:
                    self.current_theme = active_theme
                    logger.debug(f"[TabThemeConfig.load_themes] Thème actif: {active_theme.name}")
            except (OSError, RuntimeError) as e:
                logger.warning(f"[TabThemeConfig.load_themes] Pas de thème actif: {e}")

            # Si le switch est activé, charger les thèmes maintenant
            if theme_enabled:
                self.refresh()

                # Sélectionner le premier thème si disponible
                if self.theme_list_box and len(self.available_themes) > 0:
                    first_row = self.theme_list_box.get_row_at_index(0)
                    if first_row:
                        self.theme_list_box.select_row(first_row)

            logger.debug(f"[TabThemeConfig.load_themes] Switch état: {theme_enabled}")
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig.load_themes] Erreur: {e}")
        finally:
            self._updating_ui = False

    def _load_themes(self) -> None:
        """Alias interne pour compatibilité."""
        self.load_themes()

    def scan_system_themes(self) -> None:
        """Scanne les répertoires système pour trouver les thèmes."""
        self.available_themes.clear()
        self.theme_paths.clear()

        if self.theme_list_box is None:
            return

        # Nettoyer la liste des thèmes dans l'UI
        while True:
            child = self.theme_list_box.get_first_child()
            if child is None:
                break
            self.theme_list_box.remove(child)

        # 1. Ajouter l'option "Aucun"
        none_theme = GrubTheme(name="Aucun (GRUB par défaut)")
        self.available_themes[none_theme.name] = none_theme
        self._add_theme_to_list(none_theme, None)

        # 2. Utiliser le service pour scanner les thèmes
        scanned_themes = self.theme_service.scan_system_themes()

        for theme_name, (theme, item) in scanned_themes.items():
            self.available_themes[theme_name] = theme
            self.theme_paths[theme_name] = item
            self._add_theme_to_list(theme, item)

        if len(self.available_themes) == 0:
            logger.warning("[TabThemeConfig.scan_system_themes] Aucun thème valide trouvé")
            # Ajouter un placeholder
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            label = Gtk.Label(label="Aucun thème trouvé")
            label.set_halign(Gtk.Align.START)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(10)
            row.set_child(label)
            self.theme_list_box.append(row)

    def _add_theme_to_list(self, theme: GrubTheme, theme_path: Path | None) -> None:
        """Ajoute un thème à la liste.

        Args:
            theme: Thème à ajouter.
            theme_path: Chemin du répertoire du thème (None pour 'Aucun').
        """
        row = Gtk.ListBoxRow()

        # Contenu de la ligne
        content_box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)

        # Icône
        icon_label = Gtk.Label(label="🎨")
        if theme_path is None:
            icon_label.set_label("🚫")
        icon_label.set_margin_end(8)
        content_box.append(icon_label)

        # Nom du thème
        theme_label = Gtk.Label(label=theme.name or "Thème sans nom")
        theme_label.set_halign(Gtk.Align.START)
        theme_label.set_hexpand(True)
        theme_label.add_css_class("title-4")
        content_box.append(theme_label)

        # Vérifier si le thème est modifiable
        is_custom = False
        if theme_path:
            is_custom = self.theme_service.is_theme_custom(theme_path)

        # Vérifier si le thème est actif dans le modèle
        model = self.state_manager.get_model()
        is_active = False
        if theme_path:
            theme_txt_path = theme_path / "theme.txt"
            is_active = str(theme_txt_path) == model.grub_theme
        else:
            # Cas "Aucun"
            is_active = not model.grub_theme

        # Badge pour l'état actif
        if is_active:
            active_badge = Gtk.Label(label="✅ Actif")
            active_badge.add_css_class("success")
            active_badge.set_margin_end(10)
            content_box.append(active_badge)
        # Badge pour les thèmes système
        elif theme_path and not is_custom:
            system_badge = Gtk.Label(label="Système")
            system_badge.add_css_class("dim-label")
            system_badge.set_margin_end(10)
            content_box.append(system_badge)
        elif theme_path:
            custom_badge = Gtk.Label(label="Custom")
            custom_badge.add_css_class("success")
            custom_badge.set_margin_end(10)
            content_box.append(custom_badge)

        row.set_child(content_box)
        self.theme_list_box.append(row)
