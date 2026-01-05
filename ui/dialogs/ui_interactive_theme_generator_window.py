"""Complete interactive theme generator window.

Full-featured window with theme element switches, configuration panels,
live preview, and theme export capabilities.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gi.repository import Gtk

from core.theme.theme_generator import ThemeGenerator, ThemeResolution
from ui.dialogs.ui_interactive_theme_generator import InteractiveThemeGeneratorPanel

logger = logging.getLogger(__name__)


class InteractiveThemeGeneratorWindow(Gtk.Window):
    """Main window for interactive theme generation."""

    def __init__(
        self,
        parent_window: Gtk.Window | None = None,
        on_theme_created: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        """Initialize the generator window.

        Args:
            parent_window: Parent window (for modal behavior)
            on_theme_created: Callback when theme is created (name, package)
        """
        super().__init__()

        self.set_title("Générateur de Thème GRUB Interactif")
        self.set_default_size(900, 700)
        self.set_modal(True)

        # En tests, `parent_window` peut être un MagicMock; GTK attend un vrai Gtk.Window/GObject.
        # En prod, c'est bien un Gtk.Window.
        if parent_window is not None:
            try:
                self.set_transient_for(parent_window)
            except TypeError:
                pass

        self.on_theme_created = on_theme_created
        self.generator = ThemeGenerator()

        # Build UI
        self._build_ui()

        # Connect to window close
        self.connect("close-request", self._on_close)

        logger.info("Interactive theme generator window opened")

    def _build_ui(self) -> None:
        """Build the window UI."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        # Header bar
        header = Gtk.HeaderBar()
        main_box.append(header)

        # Generator panel
        self.generator_panel = InteractiveThemeGeneratorPanel(
            on_theme_updated=self._on_theme_updated,
        )
        main_box.append(self.generator_panel)

        # Footer bar with buttons
        footer = self._build_footer()
        main_box.append(footer)

    def _build_footer(self) -> Gtk.Box:
        """Build footer with action buttons."""
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        footer.set_margin_top(12)
        footer.set_margin_bottom(12)
        footer.set_margin_start(12)
        footer.set_margin_end(12)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)

        # Cancel button
        cancel_btn = Gtk.Button(label="Annuler")
        cancel_btn.connect("clicked", lambda _: self.close())
        footer.append(cancel_btn)

        # Create button
        create_btn = Gtk.Button(label="Créer le thème")
        create_btn.add_css_class("suggested-action")
        create_btn.connect("clicked", self._on_create_theme)
        footer.append(create_btn)

        return footer

    def _on_theme_updated(self) -> None:
        """Handle theme update."""
        logger.debug("Theme updated in generator")

    def _on_create_theme(self, button: Gtk.Button) -> None:
        """Handle theme creation."""
        try:
            # Create a simple name dialog
            dialog = Gtk.Dialog(
                title="Installer le nouveau thème",
                transient_for=self,
                modal=True,
            )

            content = dialog.get_content_area()
            content.set_spacing(12)
            content.set_margin_top(12)
            content.set_margin_bottom(12)
            content.set_margin_start(12)
            content.set_margin_end(12)

            # Theme name input
            name_label = Gtk.Label(label="Nom du thème:")
            name_label.set_halign(Gtk.Align.START)
            content.append(name_label)

            name_entry = Gtk.Entry()
            name_entry.set_placeholder_text("Ex: Mon Thème Personnalisé")
            name_entry.set_text("custom_theme")
            content.append(name_entry)

            # Resolution selection
            res_label = Gtk.Label(label="Résolution de l'écran:")
            res_label.set_halign(Gtk.Align.START)
            content.append(res_label)

            res_combo = Gtk.DropDown.new_from_strings(
                [
                    "1080p (1920x1080)",
                    "2K (2560x1440)",
                    "4K (3840x2160)",
                    "Ultrawide (2560x1080)",
                    "Ultrawide 2K (3440x1440)",
                ]
            )
            res_combo.set_selected(0)
            content.append(res_combo)

            # Add buttons
            dialog.add_buttons(
                "Annuler",
                Gtk.ResponseType.CANCEL,
                "Créer et Installer",
                Gtk.ResponseType.OK,
            )

            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                theme_name = name_entry.get_text()

                # Map resolution
                resolutions = {
                    0: ThemeResolution.RESOLUTION_1080P,
                    1: ThemeResolution.RESOLUTION_2K,
                    2: ThemeResolution.RESOLUTION_4K,
                    3: ThemeResolution.RESOLUTION_ULTRAWIDE,
                    4: ThemeResolution.RESOLUTION_ULTRAWIDE_2K,
                }
                resolution = resolutions.get(
                    res_combo.get_selected(),
                    ThemeResolution.RESOLUTION_1080P,
                )

                # Get configuration
                theme_config = self.generator_panel.get_theme_config()

                # Génération du thème via le générateur
                package = self.generator.create_theme_package(
                    name=theme_name,
                    theme_config=theme_config,
                    resolution=resolution,
                )

                # Notify callback
                if self.on_theme_created:
                    self.on_theme_created(theme_name, package)

                # Show success message
                success_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=Gtk.DialogFlags.MODAL,
                    type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Thème créé et installé!",
                )
                success_dialog.format_secondary_text(
                    f"Le thème '{theme_name}' a été généré et installé dans votre dossier de thèmes GRUB.\n\n"
                    "Vous pouvez maintenant le sélectionner dans la liste des thèmes."
                )
                success_dialog.run()
                success_dialog.destroy()

                # Close window
                self.close()

        except Exception as e:
            logger.error(f"Failed to create theme: {e}")
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=Gtk.DialogFlags.MODAL,
                type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Erreur lors de la création du thème",
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()

    def _on_close(self, widget) -> bool:
        """Handle window close."""
        logger.info("Interactive theme generator window closed")
        return False
