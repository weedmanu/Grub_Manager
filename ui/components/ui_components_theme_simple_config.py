"""Composant pour la configuration simple du thème GRUB (couleurs et fond)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gi.repository import Gtk
from loguru import logger

from ui.components.ui_components_theme_simple_config_logic import (
    SimpleThemeConfigWidgets,
    apply_simple_theme_config_from_widgets,
)
from ui.config.ui_config_constants import GRUB_COLORS
from ui.dialogs.ui_dialogs_file import open_image_file_dialog
from ui.helpers.ui_helpers_gtk import GtkHelper

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


@dataclass(slots=True)
class ThemeSimpleConfigPanelWidgets:
    """Références vers les widgets internes du panneau de config simple."""

    bg_image_entry: Gtk.Entry | None = None
    normal_fg_combo: Gtk.DropDown | None = None
    normal_bg_combo: Gtk.DropDown | None = None
    highlight_fg_combo: Gtk.DropDown | None = None
    highlight_bg_combo: Gtk.DropDown | None = None


@dataclass(slots=True)
class _ThemeSimpleBlocks:
    background: Gtk.Box | None = None
    colors: Gtk.Box | None = None


class ThemeSimpleConfigPanel(Gtk.Box):
    """Panneau de configuration simple (couleurs et image de fond)."""

    def __init__(self, state_manager: Any, on_changed: callable) -> None:
        """Initialise le panneau.

        Args:
            state_manager: Gestionnaire d'état global.
            on_changed: Callback appelé quand une valeur change.
        """
        # UI compacte: espacement réduit.
        super().__init__(orientation=VERTICAL, spacing=8)
        self.state_manager = state_manager
        self.on_changed = on_changed
        self._updating_ui = False

        self._widgets = ThemeSimpleConfigPanelWidgets()

        self._colors_box: Gtk.Box | None = None
        self._colors_note: Gtk.Label | None = None

        self._blocks = _ThemeSimpleBlocks()

        self._build_ui()

    @property
    def widgets(self) -> ThemeSimpleConfigPanelWidgets:
        """Accès explicite aux widgets internes du panneau."""
        return self._widgets

    def _widgets_view(self) -> ThemeSimpleConfigPanelWidgets:
        return self._widgets

    def _build_background_section(self, grid: Gtk.Grid) -> None:
        """Construit la section image de fond."""
        widgets = self._widgets_view()

        bg_label = Gtk.Label(label="Image de fond", xalign=0)
        bg_label.add_css_class("heading")
        bg_label.add_css_class("label-blue")
        grid.attach(bg_label, 0, 0, 4, 1)

        bg_box = Gtk.Box(orientation=HORIZONTAL, spacing=5)
        widgets.bg_image_entry = Gtk.Entry()
        widgets.bg_image_entry.set_hexpand(True)
        widgets.bg_image_entry.set_placeholder_text("/boot/grub/themes/mon-theme/background.jpg")
        widgets.bg_image_entry.connect("changed", self._on_config_changed)
        bg_box.append(widgets.bg_image_entry)

        bg_btn = Gtk.Button(label="Parcourir...")
        bg_btn.connect("clicked", self._on_select_bg_image)
        bg_box.append(bg_btn)

        grid.attach(bg_box, 0, 1, 4, 1)

        # Séparateur supprimé: le bloc "Image de fond" est maintenant autonome.

    def _build_color_row(self, colors_grid: Gtk.Grid, row: int, label_text: str, combo_attrs: tuple[str, str]) -> None:
        """Construit une ligne de sélecteurs de couleurs."""
        widgets = self._widgets_view()

        label = Gtk.Label(label=label_text, xalign=0)
        label.set_width_chars(15)
        colors_grid.attach(label, 0, row, 1, 1)

        fg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        fg_combo.connect("notify::selected", self._on_config_changed)
        fg_combo.set_tooltip_text("Couleur du texte")
        setattr(widgets, combo_attrs[0], fg_combo)
        colors_grid.attach(fg_combo, 1, row, 1, 1)

        sep = Gtk.Label(label="sur")
        sep.add_css_class("dim-label")
        colors_grid.attach(sep, 2, row, 1, 1)

        bg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        bg_combo.connect("notify::selected", self._on_config_changed)
        bg_combo.set_tooltip_text("Couleur de fond")
        setattr(widgets, combo_attrs[1], bg_combo)
        colors_grid.attach(bg_combo, 3, row, 1, 1)

    def _ensure_color_widgets(self) -> None:
        """Crée les dropdowns de couleurs si nécessaire (une seule fois)."""
        widgets = self._widgets_view()
        if (
            widgets.normal_fg_combo
            and widgets.normal_bg_combo
            and widgets.highlight_fg_combo
            and widgets.highlight_bg_combo
        ):
            return

        def _make_combo() -> Gtk.DropDown:
            combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
            combo.connect("notify::selected", self._on_config_changed)
            return combo

        if widgets.normal_fg_combo is None:
            widgets.normal_fg_combo = _make_combo()
            widgets.normal_fg_combo.set_tooltip_text("Couleur du texte")
        if widgets.normal_bg_combo is None:
            widgets.normal_bg_combo = _make_combo()
            widgets.normal_bg_combo.set_tooltip_text("Couleur de fond")
        if widgets.highlight_fg_combo is None:
            widgets.highlight_fg_combo = _make_combo()
            widgets.highlight_fg_combo.set_tooltip_text("Couleur du texte")
        if widgets.highlight_bg_combo is None:
            widgets.highlight_bg_combo = _make_combo()
            widgets.highlight_bg_combo.set_tooltip_text("Couleur de fond")

    def _build_colors_section(self) -> Gtk.Box:
        """Construit la section couleurs du menu."""
        colors_box = Gtk.Box(orientation=VERTICAL, spacing=6)
        self._colors_box = colors_box

        colors_title = Gtk.Label(label="Couleurs du menu", xalign=0)
        colors_title.add_css_class("heading")
        colors_title.add_css_class("label-green")
        colors_box.append(colors_title)

        colors_grid = Gtk.Grid()
        colors_grid.set_row_spacing(8)
        colors_grid.set_column_spacing(10)
        colors_grid.set_margin_top(8)
        colors_box.append(colors_grid)

        self._build_color_row(colors_grid, 0, "Entrée normale", ("normal_fg_combo", "normal_bg_combo"))
        self._build_color_row(colors_grid, 1, "Entrée sélectionnée", ("highlight_fg_combo", "highlight_bg_combo"))

        return colors_box

    def build_background_block(self) -> Gtk.Box:
        """Construit et retourne le bloc "Image de fond".

        Ce bloc est conçu pour être placé indépendamment du bloc couleurs dans l'onglet.
        """
        if self._blocks.background is not None:
            return self._blocks.background

        block = Gtk.Box(orientation=VERTICAL, spacing=6)
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(10)
        block.append(grid)

        self._build_background_section(grid)
        self._blocks.background = block
        return block

    def build_colors_block(self) -> Gtk.Box:
        """Construit et retourne le bloc "Couleurs du menu"."""
        if self._blocks.colors is not None:
            return self._blocks.colors

        self._blocks.colors = self._build_colors_section()
        return self._blocks.colors

    def build_color_normal_option_block(self) -> Gtk.Box:
        """Construit le bloc option pour GRUB_COLOR_NORMAL (une option = un bloc)."""
        self._ensure_color_widgets()
        widgets = self._widgets_view()

        block = Gtk.Box(orientation=VERTICAL, spacing=6)
        title = Gtk.Label(label="Couleur entrée normale", xalign=0)
        title.add_css_class("heading")
        title.add_css_class("label-green")
        block.append(title)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(10)
        grid.set_margin_top(6)
        block.append(grid)

        label = Gtk.Label(label="Entrée normale", xalign=0)
        label.set_width_chars(15)
        grid.attach(label, 0, 0, 1, 1)
        grid.attach(widgets.normal_fg_combo, 1, 0, 1, 1)
        sep = Gtk.Label(label="sur")
        sep.add_css_class("dim-label")
        grid.attach(sep, 2, 0, 1, 1)
        grid.attach(widgets.normal_bg_combo, 3, 0, 1, 1)

        return block

    def build_color_highlight_option_block(self) -> Gtk.Box:
        """Construit le bloc option pour GRUB_COLOR_HIGHLIGHT (une option = un bloc)."""
        self._ensure_color_widgets()
        widgets = self._widgets_view()

        block = Gtk.Box(orientation=VERTICAL, spacing=6)
        title = Gtk.Label(label="Couleur entrée sélectionnée", xalign=0)
        title.add_css_class("heading")
        title.add_css_class("label-green")
        block.append(title)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(10)
        grid.set_margin_top(6)
        block.append(grid)

        label = Gtk.Label(label="Entrée sélectionnée", xalign=0)
        label.set_width_chars(15)
        grid.attach(label, 0, 0, 1, 1)
        grid.attach(widgets.highlight_fg_combo, 1, 0, 1, 1)
        sep = Gtk.Label(label="sur")
        sep.add_css_class("dim-label")
        grid.attach(sep, 2, 0, 1, 1)
        grid.attach(widgets.highlight_bg_combo, 3, 0, 1, 1)

        return block

    def _build_ui(self) -> None:
        """Construit l'interface du panneau."""
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        # Note (utile si un script de couleurs surcharge les réglages)
        note = Gtk.Label(xalign=0)
        note.add_css_class("dim-label")
        note.set_wrap(True)
        note.set_visible(False)
        self._colors_note = note
        self.append(note)

        # Par défaut, on n'impose pas un layout unique: le parent place les blocs.
        # On garde des helpers publics pour obtenir les deux sections.

    def set_colors_section_enabled(self, enabled: bool, *, reason: str | None = None) -> None:
        """Active/désactive la section couleurs.

        Quand un script /etc/grub.d/*colors* est actif, il force les couleurs dans
        grub.cfg lors de `update-grub`. On garde la section visible (informatif)
        mais on la désactive pour éviter la confusion.
        """
        if self._colors_box is not None:
            self._colors_box.set_sensitive(bool(enabled))

        if self._colors_note is not None:
            if enabled:
                self._colors_note.set_visible(False)
            else:
                suffix = f" ({reason})" if reason else ""
                self._colors_note.set_text(
                    "Un script de couleurs est actif" + suffix + ". Les réglages de couleurs ci-dessous seront ignorés."
                )
                self._colors_note.set_visible(True)

    def update_from_model(self, model: Any) -> None:
        """Met à jour les widgets depuis le modèle.

        Args:
            model: Le modèle de données.
        """
        self._updating_ui = True
        try:
            widgets = self._widgets_view()
            if widgets.bg_image_entry:
                widgets.bg_image_entry.set_text(model.grub_background or "")

            def set_combo_color(combo: Gtk.DropDown | None, color_pair: str, index: int) -> None:
                if not combo or not color_pair or "/" not in color_pair:
                    return
                color = color_pair.split("/")[index].strip()
                if color in GRUB_COLORS:
                    combo.set_selected(GRUB_COLORS.index(color))

            set_combo_color(widgets.normal_fg_combo, model.grub_color_normal, 0)
            set_combo_color(widgets.normal_bg_combo, model.grub_color_normal, 1)
            set_combo_color(widgets.highlight_fg_combo, model.grub_color_highlight, 0)
            set_combo_color(widgets.highlight_bg_combo, model.grub_color_highlight, 1)
        finally:
            self._updating_ui = False

    def _on_select_bg_image(self, button: Gtk.Button) -> None:
        """Ouvre un sélecteur de fichier pour l'image de fond."""
        bg_image_entry = self._widgets_view().bg_image_entry
        open_image_file_dialog(
            gtk_module=Gtk,
            button=button,
            title="Choisir une image de fond",
            parent_window=GtkHelper.resolve_parent_window(button),
            on_selected=lambda path: bg_image_entry.set_text(path) if bg_image_entry else None,
        )

    def _on_config_changed(self, *_) -> None:
        """Met à jour le modèle quand la config change."""
        if self._updating_ui:
            return

        try:
            widgets = self._widgets_view()
            updated = apply_simple_theme_config_from_widgets(
                state_manager=self.state_manager,
                colors=list(GRUB_COLORS),
                widgets=SimpleThemeConfigWidgets(
                    bg_image_entry=widgets.bg_image_entry,
                    normal_fg_combo=widgets.normal_fg_combo,
                    normal_bg_combo=widgets.normal_bg_combo,
                    highlight_fg_combo=widgets.highlight_fg_combo,
                    highlight_bg_combo=widgets.highlight_bg_combo,
                ),
            )
        except (AttributeError, IndexError) as exc:
            logger.debug(f"[ThemeSimpleConfigPanel] Widgets incomplets/invalides: {exc}")
            return

        if updated:
            self.on_changed()
