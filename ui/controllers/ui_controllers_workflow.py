"""Contrôleur pour les workflows de sauvegarde et recharge de la configuration."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from core.config.core_config_paths import GRUB_DEFAULT_PATH
from core.io.core_io_grub_default import (
    create_last_modif_backup,
    read_grub_default,
    restore_grub_default_backup,
)
from core.managers.core_managers_apply import GrubApplyManager
from core.managers.core_managers_entry_visibility import apply_hidden_entries_to_grub_cfg, save_hidden_entry_ids
from core.models.core_models_grub_ui import merged_config_from_model
from core.system.core_system_grub_commands import GrubUiState
from ui.controllers.ui_controllers_infobar import ERROR, INFO, WARNING
from ui.helpers.ui_helpers_gtk_imports import GLib, Gtk
from ui.models.ui_models_state import AppState

if TYPE_CHECKING:
    from core.system.core_system_grub_commands import GrubUiModel
    from ui.models.ui_models_state import AppStateManager


@dataclass(frozen=True, slots=True)
class WorkflowDeps:
    """Dépendances injectées dans le contrôleur (UI + callbacks)."""

    save_btn: Gtk.Button | None
    reload_btn: Gtk.Button | None
    load_config_cb: Callable[[], None]
    read_model_cb: Callable[[], GrubUiModel]
    show_info_cb: Callable[[str, str], None]


class WorkflowController:
    """Gère l'orchestration des actions de sauvegarde et recharge."""

    def __init__(
        self,
        window: Gtk.Window,
        state_manager: AppStateManager,
        deps: WorkflowDeps,
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
        self.save_btn = deps.save_btn
        self.reload_btn = deps.reload_btn
        self.load_config_cb = deps.load_config_cb
        self.read_model_cb = deps.read_model_cb
        self.show_info_cb = deps.show_info_cb

    def _apply_state(self, state: AppState) -> None:
        """Applique l'état UI.

        Compatibilité tests: certains mocks n'exposent que `_apply_state`.
        Runtime: la fenêtre (GrubConfigManager) expose `apply_state`.
        """
        apply_state_fn = getattr(self.window, "_apply_state", None)
        if callable(apply_state_fn):
            apply_state_fn(state)
            return

        apply_state_fn = getattr(self.window, "apply_state", None)
        if callable(apply_state_fn):
            apply_state_fn(state)
            return

        # Fallback (défensif): applique l'état via state_manager si disponible.
        self.state_manager.apply_state(state, self.save_btn, self.reload_btn)

    def _maybe_create_last_modif_backup(self, apply_now: bool) -> None:
        if not apply_now:
            return
        try:
            create_last_modif_backup()
        except OSError as e:
            logger.warning(f"Impossible de créer le backup last_modif: {e}")

    def _verify_written_config(self, *, model: GrubUiModel) -> None:
        try:
            verified_config = read_grub_default()
            matches = (
                verified_config.get("GRUB_TIMEOUT") == str(model.timeout)
                and verified_config.get("GRUB_DEFAULT") == model.default
            )
            logger.debug(f"[WorkflowController._verify_written_config] matches={matches}")
            if not matches:
                logger.warning("[WorkflowController._verify_written_config] ATTENTION: Valeurs écrites incohérentes")
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            logger.warning(f"[WorkflowController._verify_written_config] Impossible de vérifier: {e}")

    def _apply_hidden_entries_if_needed(self, *, msg: str, apply_now: bool) -> tuple[str, str]:
        msg_type = INFO

        if apply_now:
            # Persistance: uniquement lors d'une application explicite.
            # Les switches/listes ne doivent pas écrire sur disque.
            try:
                save_hidden_entry_ids(self.state_manager.hidden_entry_ids)
            except OSError:
                # best-effort
                pass

            if self.state_manager.hidden_entry_ids:
                try:
                    used_path, masked = apply_hidden_entries_to_grub_cfg(self.state_manager.hidden_entry_ids)
                    self.state_manager.entries_visibility_dirty = False
                    msg += f"\nEntrées masquées: {masked} ({used_path})"
                except (OSError, RuntimeError, ValueError, TypeError) as e:
                    logger.error(f"[WorkflowController._apply_hidden_entries_if_needed] ERREUR masquage: {e}")
                    msg += f"\nAttention: Masquage échoué: {e}"
                    msg_type = WARNING
        elif self.state_manager.entries_visibility_dirty:
            msg += "\n(Masquage non appliqué car update-grub ignoré)"

        return msg, msg_type

    def _handle_apply_success(
        self,
        *,
        result,
        merged_config: dict[str, str],
        model: GrubUiModel,
        apply_now: bool,
    ) -> None:
        self.state_manager.pending_script_changes.clear()
        self._verify_written_config(model=model)

        self.state_manager.update_state_data(
            GrubUiState(model=model, entries=self.state_manager.state_data.entries, raw_config=merged_config)
        )
        self._apply_state(AppState.CLEAN)

        msg = result.message
        if result.details:
            msg += f"\n{result.details}"

        msg, msg_type = self._apply_hidden_entries_if_needed(msg=msg, apply_now=apply_now)
        self.show_info_cb(msg, msg_type)
        self.load_config_cb()

    def on_reload(self, _button: Gtk.Button | None = None) -> None:
        """Recharge la configuration GRUB depuis le disque."""
        logger.info("[WorkflowController.on_reload] Demande de recharge")
        logger.debug(f"[WorkflowController.on_reload] Config modified state: {self.state_manager.modified}")

        # Vérifier si un backup "last_modif" existe
        backup_path = os.path.join(os.path.dirname(GRUB_DEFAULT_PATH), "grub_backup.last_modif.tar.gz")
        has_last_modif = os.path.exists(backup_path)

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
                except GLib.Error:
                    pass

                if idx == 1:
                    # Si confirmé, on vérifie ensuite si on veut restaurer le backup
                    self._check_restore_last_modif(has_last_modif, backup_path)

            dialog.choose(self.window, None, _on_choice)
            return

        self._check_restore_last_modif(has_last_modif, backup_path)

    def _check_restore_last_modif(self, has_last_modif: bool, backup_path: str) -> None:
        """Propose de restaurer la dernière modification si disponible."""
        if not has_last_modif:
            self.load_config_cb()
            self.show_info_cb("Configuration rechargée", INFO)
            return

        # Proposer de restaurer la version précédente
        dialog = Gtk.AlertDialog()
        dialog.set_message("Restaurer la version précédente ?")
        dialog.set_detail(
            "Une sauvegarde automatique (avant la dernière application) a été trouvée.\n"
            "Voulez-vous restaurer cette version ou simplement recharger le fichier actuel ?"
        )
        dialog.set_buttons(["Annuler", "Recharger actuel", "Restaurer précédent"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(2)

        dialog.choose(self.window, None, lambda dlg, res: self._handle_restore_choice(dlg, res, backup_path))

    def _handle_restore_choice(self, dlg, result, backup_path: str) -> None:
        idx = None
        try:
            idx = dlg.choose_finish(result)
        except GLib.Error:
            pass

        if idx == 1:  # Recharger actuel
            self.load_config_cb()
            self.show_info_cb("Configuration rechargée", INFO)
        elif idx == 2:  # Restaurer précédent
            try:
                if os.geteuid() != 0:
                    self.show_info_cb("Droits root requis pour restaurer", ERROR)
                    return
                restore_grub_default_backup(backup_path)
                self.load_config_cb()
                self.show_info_cb("Version précédente restaurée avec succès", INFO)
            except (OSError, ValueError) as e:
                logger.error(f"Erreur restauration last_modif: {e}")
                self.show_info_cb(f"Erreur restauration: {e}", ERROR)

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
                self.perform_save(apply_now=True)

        dialog.choose(self.window, None, _on_response)

    def perform_save(self, apply_now: bool) -> None:
        """Exécute le workflow de sauvegarde via ApplyManager."""
        logger.info(f"[WorkflowController.perform_save] Début (apply_now={apply_now})")
        self._apply_state(AppState.APPLYING)

        try:
            self._maybe_create_last_modif_backup(apply_now)

            model = self.read_model_cb()
            logger.debug(
                f"[WorkflowController.perform_save] Modèle lu: timeout={model.timeout}, default={model.default}"
            )
            logger.info(f"[WorkflowController.perform_save] theme_management_enabled={model.theme_management_enabled}")

            merged_config = merged_config_from_model(self.state_manager.state_data.raw_config, model)
            logger.debug(f"[WorkflowController._perform_save] Config fusionnée, apply_now={apply_now}")

            manager = GrubApplyManager()
            result = manager.apply_configuration(
                merged_config,
                apply_changes=apply_now,
                theme_management_enabled=model.theme_management_enabled,
                pending_script_changes=self.state_manager.pending_script_changes,
            )
            logger.info(
                "[WorkflowController._perform_save] "
                f"Passé theme_management_enabled={model.theme_management_enabled} au manager"
            )
            logger.debug(f"[WorkflowController._perform_save] Résultat apply: success={result.success}")

            if result.success:
                logger.debug("[WorkflowController._perform_save] Configuration appliquée avec succès")
                self._handle_apply_success(result=result, merged_config=merged_config, model=model, apply_now=apply_now)
            else:
                self._apply_state(AppState.DIRTY)
                self.show_info_cb(f"Erreur: {result.message}", ERROR)

        except (OSError, RuntimeError, ValueError, TypeError) as e:
            logger.exception("[WorkflowController._perform_save] ERREUR inattendue")
            self._apply_state(AppState.DIRTY)
            self.show_info_cb(f"Erreur inattendue: {e}", ERROR)
