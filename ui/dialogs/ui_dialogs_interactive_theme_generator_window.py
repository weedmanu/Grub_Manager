"""Complete interactive theme generator window.

Full-featured window with theme element switches, configuration panels,
live preview, and theme export capabilities.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gi.repository import Gtk

from core.models.core_models_theme import GrubTheme
from core.theme.generator import ThemeGenerator, ThemeResolution
from ui.dialogs.ui_dialogs_interactive_theme_generator import InteractiveThemeGeneratorPanel
from ui.dialogs.ui_dialogs_theme_preview import GrubThemePreviewDialog as GrubPreviewDialog

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
        self.set_default_size(1100, 700)
        self.set_resizable(False)
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
        self._preview_tmpdir: tempfile.TemporaryDirectory[str] | None = None

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

        # Preview button
        preview_btn = Gtk.Button(label="Aperçu")
        preview_btn.connect("clicked", self._on_preview)
        footer.append(preview_btn)

        # Create button
        create_btn = Gtk.Button(label="Créer le thème")
        create_btn.add_css_class("suggested-action")
        create_btn.connect("clicked", self._on_create_theme)
        footer.append(create_btn)

        return footer

    def _on_preview(self, _button: Gtk.Button) -> None:
        """Ouvre un aperçu du thème en cours (sans l'installer)."""
        try:
            # Nettoie l'ancien dossier temporaire si besoin
            if self._preview_tmpdir is not None:
                try:
                    self._preview_tmpdir.cleanup()
                except Exception:
                    pass
                self._preview_tmpdir = None

            theme_config = self.generator_panel.get_theme_config()

            # Résolution fixe pour l'aperçu (le but est la fidélité visuelle du theme.txt)
            package = self.generator.create_theme_package(
                name="preview",
                theme_config=theme_config,
                resolution=ThemeResolution.RESOLUTION_1080P,
            )

            tmpdir = tempfile.TemporaryDirectory(prefix="grub-theme-preview-")
            self._preview_tmpdir = tmpdir
            theme_dir = Path(tmpdir.name)

            (theme_dir / "theme.txt").write_text(package.get("theme.txt", ""), encoding="utf-8")

            # Copie des assets si disponibles (background.jpg, info.png, fonts, icons...)
            assets: dict[str, str] = package.get("assets", {}) or {}
            for target_name, source_path in assets.items():
                try:
                    src = Path(source_path)
                    if not src.exists():
                        continue
                    dst = theme_dir / target_name
                    if src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy(src, dst)
                except (OSError, shutil.Error, ValueError):
                    continue

            dialog = GrubPreviewDialog(
                GrubTheme(name="Aperçu générateur"),
                model=None,
                theme_txt_path=theme_dir / "theme.txt",
            )
            dialog.show()

        except (OSError, RuntimeError, TypeError, ValueError) as e:
            logger.error("Failed to preview theme: %s", e)
            error_dialog = Gtk.AlertDialog()
            error_dialog.set_modal(True)
            error_dialog.set_message("Erreur lors de l'aperçu")
            error_dialog.set_detail(str(e))
            error_dialog.set_buttons(["OK"])
            error_dialog.show(parent=self)

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
                success_dialog = Gtk.AlertDialog()
                success_dialog.set_modal(True)
                success_dialog.set_message("Thème créé et installé!")
                success_dialog.set_detail(
                    f"Le thème '{theme_name}' a été généré et installé dans votre dossier de thèmes GRUB.\n\n"
                    "Vous pouvez maintenant le sélectionner dans la liste des thèmes."
                )
                success_dialog.set_buttons(["OK"])

                def _after_ok(dlg: Gtk.AlertDialog, result: Gtk.AsyncResult) -> None:
                    try:
                        dlg.choose_finish(result)
                    except (OSError, RuntimeError):
                        pass
                    self.close()

                success_dialog.choose(self, None, _after_ok)

        except (OSError, RuntimeError, TypeError, ValueError) as e:
            logger.error(f"Failed to create theme: {e}")
            error_dialog = Gtk.AlertDialog()
            error_dialog.set_modal(True)
            error_dialog.set_message("Erreur lors de la création du thème")
            error_dialog.set_detail(str(e))
            error_dialog.set_buttons(["OK"])
            error_dialog.show(parent=self)

    def _on_close(self, widget) -> bool:
        """Handle window close."""
        logger.info("Interactive theme generator window closed")
        if self._preview_tmpdir is not None:
            try:
                self._preview_tmpdir.cleanup()
            except Exception:
                pass
            self._preview_tmpdir = None
        return False
