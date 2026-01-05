"""Interactive theme generator with element-wise configuration.

Provides a modular UI where each theme element (boot_menu, progress_bar, etc.)
can be enabled/disabled with a switch, and configured in a side panel.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gi.repository import Gtk

from .theme_editors.base_editor import BaseElementEditor
from .theme_editors.layout_editors import BootMenuEditor, ProgressBarEditor, TerminalBoxEditor
from .theme_editors.text_editors import ColorsEditor, FontsEditor, TextElementEditor
from .theme_editors.visual_editors import DesktopImageEditor, IconsEditor, ImageEditor

logger = logging.getLogger(__name__)


@dataclass
class ThemeElement:
    """Definition of a theme element that can be toggled."""

    name: str
    label: str
    description: str
    enabled: bool = True
    properties: dict[str, Any] = field(default_factory=dict)


class ThemeElementRow(Gtk.Box):
    """A row containing element name, switch, and configuration button."""

    def __init__(
        self,
        element: ThemeElement,
        on_toggle: Callable[[ThemeElement, bool], None],
        on_configure: Callable[[ThemeElement], None],
    ):
        """Initialize element row.

        Args:
            element: Theme element definition
            on_toggle: Callback when switch is toggled
            on_configure: Callback when configure button is clicked
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.element = element
        self.on_toggle = on_toggle
        self.on_configure = on_configure

        # Element info (icon + name/description)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        # Name
        name_label = Gtk.Label(label=element.label)
        name_label.set_markup(f"<b>{element.label}</b>")
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        # Description
        desc_label = Gtk.Label(label=element.description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class("dim-label")
        info_box.append(desc_label)

        self.append(info_box)

        # Switch
        self.switch = Gtk.Switch()
        self.switch.set_active(element.enabled)
        self.switch.set_valign(Gtk.Align.CENTER)
        self.switch.connect("notify::active", self._on_switch_toggled)
        self.append(self.switch)

        # Configure button
        config_btn = Gtk.Button(label="⚙")
        config_btn.set_tooltip_text("Configurer cet élément")
        config_btn.set_size_request(40, 40)
        config_btn.connect("clicked", lambda _: self.on_configure(self.element))
        self.append(config_btn)

    def _on_switch_toggled(self, switch, _pspec) -> None:
        """Handle switch toggle."""
        self.element.enabled = switch.get_active()
        self.on_toggle(self.element, switch.get_active())


class ElementConfigPanel(Gtk.Box):
    """Configuration panel for a theme element."""

    def __init__(self, element: ThemeElement):
        """Initialize config panel.

        Args:
            element: Element to configure
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_hexpand(True)

        self.element = element
        self.config_widgets = {}

        # Title
        title = Gtk.Label()
        title.set_markup(f"<b>Configuration de {element.label}</b>")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        # Build config UI based on element type
        self._build_config_ui()

    def _build_config_ui(self) -> None:
        """Build configuration UI for the element."""
        element_configs = {
            "boot_menu": lambda: BootMenuEditor(),
            "progress_bar": lambda: ProgressBarEditor(),
            "timeout_label": lambda: TextElementEditor("timeout_label", "Label de délai", "Booting in %d seconds", 82),
            "footer_image": lambda: ImageEditor("footer_image", "Image de pied de page", "info.png"),
            "logo_image": lambda: ImageEditor("logo_image", "Logo", "logo.png"),
            "instruction_label": lambda: TextElementEditor(
                "instruction_label",
                "Instructions",
                "Appuyez sur 'e' pour éditer, 'c' pour la ligne de commande",
                85,
            ),
            "desktop_image": lambda: DesktopImageEditor(),
            "icons": lambda: IconsEditor(),
            "selection": lambda: TerminalBoxEditor("selection", "Barre de sélection", "select"),
            "terminal_box": lambda: TerminalBoxEditor("terminal_box", "Boîte terminal", "terminal_box"),
            "colors": lambda: ColorsEditor(),
            "fonts": lambda: FontsEditor(),
        }

        if self.element.name in element_configs:
            editor = element_configs[self.element.name]()
            self.append(editor)
            self.config_widgets = editor.config_widgets
        else:
            self._build_generic_config()

    def _build_generic_config(self) -> None:
        """Build generic configuration."""
        label = Gtk.Label(label="Aucune configuration disponible pour cet élément")
        label.add_css_class("dim-label")
        self.append(label)

    def get_properties(self) -> dict[str, Any]:
        """Get configured properties."""
        # Find the editor child (avoid calling GObject's get_properties on Gtk.Label, etc.)
        child = self.get_first_child()
        while child:
            if isinstance(child, BaseElementEditor):
                return child.get_properties()
            child = child.get_next_sibling()
        return {}


class InteractiveThemeGeneratorPanel(Gtk.Box):
    """Main interactive theme generator panel with switches and configuration."""

    def __init__(self, on_theme_updated: Callable | None = None):
        """Initialize the generator panel.

        Args:
            on_theme_updated: Callback when theme is updated
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.on_theme_updated = on_theme_updated
        self.elements: dict[str, ThemeElement] = {}
        self.config_panels: dict[str, ElementConfigPanel] = {}

        # Left panel: Elements list
        self._build_left_panel()

        # Right panel: Configuration
        self._build_right_panel()

        # Initialize elements
        self._init_theme_elements()

        logger.info("Interactive theme generator initialized")

    def _build_left_panel(self) -> None:
        """Build left panel with element switches."""
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        left_box.set_size_request(350, -1)
        left_box.set_vexpand(True)

        # Title
        title = Gtk.Label()
        title.set_markup("<b>Éléments du thème</b>")
        title.set_halign(Gtk.Align.START)
        title.set_margin_top(12)
        title.set_margin_start(12)
        title.set_margin_end(12)
        left_box.append(title)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_start(12)
        self.progress_bar.set_margin_end(12)
        self.progress_bar.set_margin_bottom(12)
        left_box.append(self.progress_bar)

        # Elements list (scrolled)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        self.elements_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(self.elements_box)
        left_box.append(scroll)

        self.append(left_box)

    def _build_right_panel(self) -> None:
        """Build right panel for configuration."""
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right_box.set_size_request(400, -1)
        right_box.set_hexpand(True)
        right_box.set_vexpand(True)

        # Title
        title = Gtk.Label()
        title.set_markup("<b>Configuration</b>")
        title.set_halign(Gtk.Align.START)
        title.set_margin_top(12)
        title.set_margin_start(12)
        title.set_margin_end(12)
        right_box.append(title)

        # Configuration container (scrolled)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        self.config_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        scroll.set_child(self.config_container)
        right_box.append(scroll)

        self.append(right_box)

    def _init_theme_elements(self) -> None:
        """Initialize theme elements with switches."""
        elements_def = [
            ThemeElement(
                name="boot_menu",
                label="Menu de démarrage",
                description="Liste des entrées GRUB",
                enabled=True,
            ),
            ThemeElement(
                name="progress_bar",
                label="Barre de progression",
                description="Barre de progression du chargement",
                enabled=True,
            ),
            ThemeElement(
                name="timeout_label",
                label="Label de délai",
                description="Message de démarrage automatique",
                enabled=True,
            ),
            ThemeElement(
                name="footer_image",
                label="Image de pied de page",
                description="Image en bas d'écran (info.png)",
                enabled=False,
            ),
            ThemeElement(
                name="logo_image",
                label="Logo",
                description="Image personnalisée (ex: logo.png)",
                enabled=True,
            ),
            ThemeElement(
                name="instruction_label",
                label="Instructions",
                description="Texte d'aide en bas d'écran",
                enabled=True,
            ),
            ThemeElement(
                name="desktop_image",
                label="Image d'arrière-plan",
                description="Image de fond",
                enabled=True,
            ),
            ThemeElement(
                name="icons",
                label="Icônes",
                description="Dossier d'icônes pour le menu",
                enabled=True,
            ),
            ThemeElement(
                name="selection",
                label="Barre de sélection",
                description="Images pour la sélection du menu",
                enabled=True,
            ),
            ThemeElement(
                name="terminal_box",
                label="Boîte terminal",
                description="Images pour le cadre du terminal",
                enabled=True,
            ),
            ThemeElement(
                name="colors",
                label="Couleurs",
                description="Palette de couleurs du thème",
                enabled=True,
            ),
            ThemeElement(
                name="fonts",
                label="Polices",
                description="Configuration des polices",
                enabled=True,
            ),
        ]

        for element in elements_def:
            self.elements[element.name] = element

            # Create row
            row = ThemeElementRow(
                element=element,
                on_toggle=self._on_element_toggled,
                on_configure=self._on_configure_element,
            )
            self.elements_box.append(row)

            # Create config panel
            panel = ElementConfigPanel(element)
            self.config_panels[element.name] = panel

        # Show first element's config by default
        self._show_config_panel("boot_menu")
        self._update_progress()

    def _on_element_toggled(self, element: ThemeElement, enabled: bool) -> None:
        """Handle element toggle."""
        logger.info(f"Element {element.name} toggled: {enabled}")
        self._update_progress()
        self._notify_update()

    def _on_configure_element(self, element: ThemeElement) -> None:
        """Handle element configuration."""
        logger.info(f"Configuring element: {element.name}")
        self._show_config_panel(element.name)

    def _show_config_panel(self, element_name: str) -> None:
        """Show configuration panel for element."""
        # Clear current
        while True:
            child = self.config_container.get_first_child()
            if child is None:
                break
            self.config_container.remove(child)

        # Show selected
        if element_name in self.config_panels:
            panel = self.config_panels[element_name]
            self.config_container.append(panel)

    def _update_progress(self) -> None:
        """Update progress bar based on enabled elements."""
        total = len(self.elements)
        enabled = sum(1 for e in self.elements.values() if e.enabled)

        progress = enabled / total if total > 0 else 0
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{int(progress*100)}% ({enabled}/{total})")

    def _notify_update(self) -> None:
        """Notify that theme has been updated."""
        if self.on_theme_updated:
            self.on_theme_updated()

    def get_theme_config(self) -> dict[str, Any]:
        """Get current theme configuration."""
        config = {
            "elements": {},
            "properties": {},
        }

        for name, element in self.elements.items():
            config["elements"][name] = {
                "enabled": element.enabled,
            }

            if name in self.config_panels:
                panel = self.config_panels[name]
                config["properties"][name] = panel.get_properties()

        return config
