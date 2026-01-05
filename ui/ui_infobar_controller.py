"""Contrôleur pour la barre d'information (InfoBar) de l'application."""

from __future__ import annotations

from loguru import logger

from ui.ui_gtk_imports import GLib, Gtk

INFO = "info"
WARNING = "warning"
ERROR = "error"


class InfoBarController:
    """Gère l'affichage des messages temporaires et les timers associés."""

    def __init__(
        self,
        revealer: Gtk.Revealer | None,
        box: Gtk.Box | None,
        label: Gtk.Label | None,
    ):
        """Initialise le contrôleur avec les widgets nécessaires.

        Args:
            revealer: Le widget Gtk.Revealer contenant la barre.
            box: Le conteneur Gtk.Box pour le style CSS.
            label: Le label Gtk.Label pour le texte du message.
        """
        self.revealer = revealer
        self.box = box
        self.label = label
        self._timeout_id: int = 0

    def show(self, message: str, msg_type: str = INFO) -> None:
        """Affiche un message temporaire dans la barre d'information.

        Args:
            message: Le texte à afficher.
            msg_type: Le type de message ('info', 'warning', 'error').
        """
        if self.label is None:
            logger.warning(f"[InfoBarController] Label manquant pour afficher: {message}")
            return

        logger.debug(f"[InfoBarController] Affichage message ({msg_type}): {message}")
        self.label.set_text(message)

        if self.box is not None:
            # Nettoyer les classes CSS précédentes
            for klass in (INFO, WARNING, ERROR):
                if self.box.has_css_class(klass):
                    self.box.remove_css_class(klass)

            # Ajouter la nouvelle classe si valide
            if msg_type in (INFO, WARNING, ERROR):
                self.box.add_css_class(msg_type)

        if self.revealer is not None:
            self.revealer.set_reveal_child(True)

            # Annuler le timer précédent s'il existe
            if self._timeout_id > 0:
                GLib.source_remove(self._timeout_id)

            # Masquer automatiquement après 5 secondes
            self._timeout_id = GLib.timeout_add_seconds(5, self.hide_info_callback)

    def hide_info_callback(self) -> bool:
        """Callback pour masquer la barre d'information."""
        if self.revealer is not None:
            self.revealer.set_reveal_child(False)
        self._timeout_id = 0
        return False
