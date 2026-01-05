"""Composants réutilisables pour l'éditeur de thème GRUB.

Fournit des widgets préfabriqués pour la sélection de résolution,
méthode de redimensionnement, et autres paramètres de thème.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from gi.repository import Gtk
from loguru import logger


class ResolutionSelector:
    """Composant de sélection de résolution d'écran."""

    RESOLUTIONS: ClassVar[list[str]] = [
        "640x480",
        "800x600",
        "1024x768",
        "1280x720",
        "1280x1024",
        "1366x768",
        "1440x900",
        "1600x900",
        "1920x1080",
        "2560x1440",
        "3840x2160",
    ]

    def __init__(
        self,
        initial_resolution: str = "1920x1080",
        *,
        callback: Callable[[str], None] | None = None,
    ):
        """Initialise le sélecteur de résolution.

        Args:
            initial_resolution: Résolution initiale
            callback: Fonction appelée lors du changement
        """
        self.callback = callback

        # Créer le label
        self.label = Gtk.Label(label="Résolution:")
        self.label.set_halign(Gtk.Align.START)

        # Créer le DropDown
        self.dropdown = Gtk.DropDown.new_from_strings(self.RESOLUTIONS)

        # Sélectionner la résolution initiale
        if initial_resolution in self.RESOLUTIONS:
            index = self.RESOLUTIONS.index(initial_resolution)
            self.dropdown.set_selected(index)

        # Connecter le signal
        self.dropdown.connect("notify::selected", self._on_changed)

        logger.debug(f"[ResolutionSelector] Initialisé avec {initial_resolution}")

    def _on_changed(self, _dropdown: Gtk.DropDown, _pspec) -> None:
        """Callback pour changement de sélection.

        Args:
            _dropdown: Widget DropDown
            _pspec: Propriété modifiée (ignoré)
        """
        resolution = self.get_resolution()
        logger.debug(f"[ResolutionSelector] Résolution changée: {resolution}")

        if self.callback:
            self.callback(resolution)

    def get_resolution(self) -> str:
        """Récupère la résolution sélectionnée.

        Returns:
            Résolution au format "WIDTHxHEIGHT"
        """
        index = self.dropdown.get_selected()
        return self.RESOLUTIONS[index]

    def set_resolution(self, resolution: str) -> None:
        """Définit la résolution sélectionnée.

        Args:
            resolution: Résolution à sélectionner
        """
        if resolution in self.RESOLUTIONS:
            index = self.RESOLUTIONS.index(resolution)
            self.dropdown.set_selected(index)
            logger.debug(f"[ResolutionSelector] Résolution définie: {resolution}")
        else:
            logger.warning(f"[ResolutionSelector] Résolution inconnue: {resolution}")


class ImageScaleSelector:
    """Composant de sélection de méthode de redimensionnement d'image."""

    SCALE_METHODS: ClassVar[list[str]] = ["fit", "stretch", "crop"]

    def __init__(
        self,
        initial_method: str = "fit",
        *,
        callback: Callable[[str], None] | None = None,
    ):
        """Initialise le sélecteur de méthode.

        Args:
            initial_method: Méthode initiale
            callback: Fonction appelée lors du changement
        """
        self.callback = callback

        # Créer le label
        self.label = Gtk.Label(label="Redimensionnement:")
        self.label.set_halign(Gtk.Align.START)

        # Créer le DropDown
        self.dropdown = Gtk.DropDown.new_from_strings(self.SCALE_METHODS)

        # Sélectionner la méthode initiale
        if initial_method in self.SCALE_METHODS:
            index = self.SCALE_METHODS.index(initial_method)
            self.dropdown.set_selected(index)

        # Connecter le signal
        self.dropdown.connect("notify::selected", self._on_changed)

        logger.debug(f"[ImageScaleSelector] Initialisé avec {initial_method}")

    def _on_changed(self, _dropdown: Gtk.DropDown, _pspec) -> None:
        """Callback pour changement de sélection.

        Args:
            _dropdown: Widget DropDown
            _pspec: Propriété modifiée (ignoré)
        """
        method = self.get_method()
        logger.debug(f"[ImageScaleSelector] Méthode changée: {method}")

        if self.callback:
            self.callback(method)

    def get_method(self) -> str:
        """Récupère la méthode sélectionnée.

        Returns:
            Méthode ('fit', 'stretch', ou 'crop')
        """
        index = self.dropdown.get_selected()
        return self.SCALE_METHODS[index]

    def set_method(self, method: str) -> None:
        """Définit la méthode sélectionnée.

        Args:
            method: Méthode à sélectionner
        """
        if method in self.SCALE_METHODS:
            index = self.SCALE_METHODS.index(method)
            self.dropdown.set_selected(index)
            logger.debug(f"[ImageScaleSelector] Méthode définie: {method}")
        else:
            logger.warning(f"[ImageScaleSelector] Méthode inconnue: {method}")


class TextEntry:
    """Composant Entry avec label pour saisie de texte."""

    def __init__(
        self,
        label_text: str,
        initial_value: str = "",
        *,
        placeholder: str = "",
        callback: Callable[[str], None] | None = None,
    ):
        """Initialise le champ de texte.

        Args:
            label_text: Texte du label
            initial_value: Valeur initiale
            placeholder: Texte placeholder
            callback: Fonction appelée lors du changement
        """
        self.callback = callback

        # Créer le label
        self.label = Gtk.Label(label=label_text)
        self.label.set_halign(Gtk.Align.START)

        # Créer l'Entry
        self.entry = Gtk.Entry()
        self.entry.set_text(initial_value)

        if placeholder:
            self.entry.set_placeholder_text(placeholder)

        # Connecter le signal
        self.entry.connect("changed", self._on_changed)

        logger.debug(f"[TextEntry] Créé pour '{label_text}'")

    def _on_changed(self, _entry: Gtk.Entry) -> None:
        """Callback pour changement de texte.

        Args:
            _entry: Widget Entry
        """
        text = self.get_text()
        logger.debug(f"[TextEntry] Texte changé: {text[:50]}")

        if self.callback:
            self.callback(text)

    def get_text(self) -> str:
        """Récupère le texte saisi.

        Returns:
            Texte actuel
        """
        return self.entry.get_text()

    def set_text(self, text: str) -> None:
        """Définit le texte.

        Args:
            text: Nouveau texte
        """
        self.entry.set_text(text)
