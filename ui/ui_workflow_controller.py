"""Contrôleur pour les workflows de sauvegarde et recharge de la configuration."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import gi
from loguru import logger

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from core.io.core_grub_default_io import read_grub_default
from core.managers.core_apply_manager import GrubApplyManager
from core.managers.core_entry_visibility_manager import apply_hidden_entries_to_grub_cfg
from core.models.core_grub_ui_model import merged_config_from_model
from core.system.core_grub_system_commands import GrubUiState
from ui.ui_infobar_controller import ERROR, INFO, WARNING
from ui.ui_state import AppState

if TYPE_CHECKING:
    from core.system.core_grub_system_commands import GrubUiModel
    from ui.ui_state import AppStateManager


class WorkflowController:
    """Gère l'orchestration des actions de sauvegarde et recharge."""

    def __init__(
        self,
        window: Gtk.Window,
        state_manager: AppStateManager,
        save_btn: Gtk.Button | None,
        reload_btn: Gtk.Button | None,
        load_config_cb: Callable[[], None],
        read_model_cb: Callable[[], GrubUiModel],
        show_info_cb: Callable[[str, str], None],
    ):
        """Initialise le contrôleur de workflow.

        Args:
            window: Fenêtre parente pour les dialogues.
            state_manager: Gestionnaire d'état de l'application.
            save_btn: Bouton de sauvegarde.
            reload_btn: Bouton de recharge.
            load_config_cb: Callback pour recharger la config depuis le disque.
            read_model_cb: Callback pour lire le modèle depuis l'UI.
            show_info_cb: Callback pour afficher des messages.
        """
        self.window = window
        self.state_manager = state_manager
        self.save_btn = save_btn
        self.reload_btn = reload_btn
        self.load_config_cb = load_config_cb
        self.read_model_cb = read_model_cb
        self.show_info_cb = show_info_cb

    def on_reload(self, _button: Gtk.Button | None = None) -> None:
        """Recharge la configuration GRUB depuis le disque."""
        logger.info("[WorkflowController.on_reload] Demande de recharge")
        logger.debug(f"[WorkflowController.on_reload] Config modified state: {self.state_manager.modified}")

        if self.state_manager.modified:
            logger.debug("[WorkflowController.on_reload] Affichage dialogue de confirmation")
            dialog = Gtk.AlertDialog()
            dialog.set_message("Modifications non enregistrées")
            dialog.set_detail("Voulez-vous vraiment recharger et perdre vos modifications ?")
            dialog.set_buttons(["Annuler", "Recharger"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(1)

            def _on_choice(dlg, result):
                idx = None
                try:
                    idx = dlg.choose_finish(result)
                    logger.debug(f"[WorkflowController.on_reload._on_choice] Résultat dialogue: {idx}")
                except GLib.Error as e:
                    logger.debug(f"[WorkflowController.on_reload._on_choice] Dialogue annulé: {e}")

                if idx == 1:
                    logger.debug("[WorkflowController.on_reload._on_choice] Confirmation utilisateur")
                    self.load_config_cb()
                    self.show_info_cb("Configuration rechargée", INFO)

            dialog.choose(self.window, None, _on_choice)
            return

        logger.debug("[WorkflowController.on_reload] Pas de modifications, recharge directe")
        self.load_config_cb()
        self.show_info_cb("Configuration rechargée", INFO)

    def on_save(self, _button: Gtk.Button | None = None) -> None:
        """Valide et sauvegarde la configuration."""
        logger.info("[WorkflowController.on_save] Demande de sauvegarde")
        logger.debug(f"[WorkflowController.on_save] UID actuel: {os.geteuid()}")

        if os.geteuid() != 0:
            logger.error("[WorkflowController.on_save] Pas les droits root")
            self.show_info_cb("Droits administrateur requis pour enregistrer", ERROR)
            return

        logger.debug("[WorkflowController.on_save] Affichage dialogue de confirmation")
        dialog = Gtk.AlertDialog()
        dialog.set_message("Appliquer la configuration")
        dialog.set_detail(
            "Voulez-vous appliquer les changements maintenant ?\n"
            "Cela exécutera 'update-grub' et peut prendre quelques secondes."
        )
        dialog.set_buttons(["Annuler", "Appliquer"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(1)

        def _on_response(dlg, result):
            idx = None
            try:
                idx = dlg.choose_finish(result)
                logger.debug(f"[WorkflowController.on_save._on_response] Résultat dialogue: {idx}")
            except GLib.Error as e:
                logger.debug(f"[WorkflowController.on_save._on_response] Dialogue annulé: {e}")

            if idx == 1:
                logger.debug("[WorkflowController.on_save._on_response] Confirmation utilisateur")
                self._perform_save(apply_now=True)

        dialog.choose(self.window, None, _on_response)

    def _perform_save(self, apply_now: bool) -> None:
        """Exécute le workflow de sauvegarde via ApplyManager."""
        logger.info(f"[WorkflowController._perform_save] Début (apply_now={apply_now})")
        self.state_manager.apply_state(AppState.APPLYING, self.save_btn, self.reload_btn)

        try:
            model = self.read_model_cb()
            logger.debug(
                f"[WorkflowController._perform_save] Modèle lu: timeout={model.timeout}, default={model.default}"
            )

            merged_config = merged_config_from_model(self.state_manager.state_data.raw_config, model)
            logger.debug(f"[WorkflowController._perform_save] Config fusionnée, apply_now={apply_now}")

            manager = GrubApplyManager()
            result = manager.apply_configuration(merged_config, apply_changes=apply_now)
            logger.debug(f"[WorkflowController._perform_save] Résultat apply: success={result.success}")

            if result.success:
                logger.debug("[WorkflowController._perform_save] Configuration appliquée avec succès")

                # Vérification post-application
                try:
                    verified_config = read_grub_default()
                    matches = (
                        verified_config.get("GRUB_TIMEOUT") == str(model.timeout)
                        and verified_config.get("GRUB_DEFAULT") == model.default
                    )
                    logger.debug(f"[WorkflowController._perform_save] Vérification: matches={matches}")

                    if not matches:
                        logger.warning("[WorkflowController._perform_save] ATTENTION: Valeurs écrites incohérentes")
                except Exception as e:
                    logger.warning(f"[WorkflowController._perform_save] Impossible de vérifier: {e}")

                self.state_manager.update_state_data(
                    GrubUiState(model=model, entries=self.state_manager.state_data.entries, raw_config=merged_config)
                )
                self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

                msg = result.message
                msg_type = INFO

                if result.details:
                    msg += f"\n{result.details}"

                if apply_now:
                    if self.state_manager.hidden_entry_ids:
                        try:
                            used_path, masked = apply_hidden_entries_to_grub_cfg(self.state_manager.hidden_entry_ids)
                            self.state_manager.entries_visibility_dirty = False
                            msg += f"\nEntrées masquées: {masked} ({used_path})"
                        except Exception as e:
                            logger.error(f"[WorkflowController._perform_save] ERREUR masquage: {e}")
                            msg += f"\nAttention: Masquage échoué: {e}"
                            msg_type = WARNING
                elif self.state_manager.entries_visibility_dirty and not apply_now:
                    msg += "\n(Masquage non appliqué car update-grub ignoré)"

                self.show_info_cb(msg, msg_type)
            else:
                self.state_manager.apply_state(AppState.DIRTY, self.save_btn, self.reload_btn)
                self.show_info_cb(f"Erreur: {result.message}", ERROR)

        except Exception as e:
            logger.exception("[WorkflowController._perform_save] ERREUR inattendue")
            self.state_manager.apply_state(AppState.DIRTY, self.save_btn, self.reload_btn)
            self.show_info_cb(f"Erreur inattendue: {e}", ERROR)
