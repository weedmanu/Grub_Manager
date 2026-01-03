"""Composant de sélection de couleur pour l'édition de thème GRUB.

Fournit un ColorButton GTK4 préconfiguré avec label et gestion
des événements color-set.
"""

from __future__ import annotations

from collections.abc import Callable

from gi.repository import Gdk, Gtk
from loguru import logger


class ColorPicker:
    """Composant ColorButton avec label et callbacks."""

    def __init__(
        self,
        label: str,
        initial_color: str = "#FFFFFF",
        *,
        callback: Callable[[str], None] | None = None,
    ):
        """Initialise le sélecteur de couleur.

        Args:
            label: Libellé du champ de couleur
            initial_color: Couleur initiale (format #RRGGBB)
            callback: Fonction appelée lors du changement de couleur (optionnel)
        """
        self.label_text = label
        self.callback = callback

        # Créer le label
        self.label = Gtk.Label(label=label)
        self.label.set_halign(Gtk.Align.START)

        # Créer le ColorButton
        self.color_button = Gtk.ColorButton()
        self.color_button.set_property("use-alpha", False)

        # Définir la couleur initiale
        self.set_color(initial_color)

        # Connecter le signal
        self.color_button.connect("color-set", self._on_color_changed)

        logger.debug(f"[ColorPicker] Créé pour '{label}' avec couleur {initial_color}")

    def _on_color_changed(self, _button: Gtk.ColorButton) -> None:
        """Callback interne pour changement de couleur.

        Args:
            _button: ColorButton modifié
        """
        color = self.get_color()
        logger.debug(f"[ColorPicker] Couleur changée: {self.label_text} -> {color}")

        if self.callback:
            self.callback(color)

    def get_color(self) -> str:
        """Récupère la couleur actuelle au format #RRGGBB.

        Returns:
            Couleur au format hexadécimal
        """
        rgba = self.color_button.get_property("rgba")
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02X}{g:02X}{b:02X}"

    def set_color(self, color_hex: str) -> None:
        """Définit la couleur du ColorButton.

        Args:
            color_hex: Couleur au format #RRGGBB ou #RGB
        """
        rgba = Gdk.RGBA()
        try:
            if rgba.parse(color_hex):
                self.color_button.set_property("rgba", rgba)
                logger.debug(f"[ColorPicker] Couleur définie: {color_hex}")
            else:
                logger.warning(f"[ColorPicker] Couleur invalide '{color_hex}'")
        except (ValueError, TypeError) as e:
            logger.warning(f"[ColorPicker] Erreur lors du parsing de la couleur '{color_hex}': {e}")

    def get_widget(self) -> Gtk.Box:
        """Récupère le widget complet (label + button dans une HBox).

        Returns:
            HBox contenant le label et le ColorButton
        """
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.append(self.label)
        hbox.append(self.color_button)
        return hbox


def create_color_grid_row(
    label_text: str,
    initial_color: str = "#FFFFFF",
    *,
    callback: Callable[[str], None] | None = None,
) -> tuple[Gtk.Label, Gtk.ColorButton]:
    """Fonction helper pour créer un picker dans un Grid.

    Args:
        label_text: Texte du label
        initial_color: Couleur initiale
        callback: Callback pour changement de couleur

    Returns:
        Tuple (Label, ColorButton) à attacher au Grid
    """
    picker = ColorPicker(label_text, initial_color, callback=callback)
    return picker.label, picker.color_button
