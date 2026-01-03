"""GTK4 UI layer - Fenêtre principale.

Contient uniquement l'orchestration (délègue construction UI et gestion d'état).
"""

# Pylint: l'ordre d'import est imposé par `gi.require_version()`, et l'UI attrape
# volontairement des exceptions larges aux frontières (affichage d'erreurs).
# pylint: disable=wrong-import-position,broad-exception-caught

from __future__ import annotations

import os

import gi
from loguru import logger

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import GLib, Gtk  # noqa: E402

from core.io.core_grub_default_io import read_grub_default  # noqa: E402
from core.managers.core_apply_manager import GrubApplyManager  # noqa: E402
from core.managers.core_entry_visibility_manager import apply_hidden_entries_to_grub_cfg  # noqa: E402
from core.models.core_grub_ui_model import merged_config_from_model  # noqa: E402
from core.system.core_grub_system_commands import (  # noqa: E402
    GrubDefaultChoice,
    GrubUiModel,
    GrubUiState,
    load_grub_ui_state,
)
from core.system.core_sync_checker import check_grub_sync  # noqa: E402
from core.config.core_paths import get_grub_themes_dir  # noqa: E402
from core.theme.core_active_theme_manager import ActiveThemeManager  # noqa: E402
from ui.tabs.ui_entries_renderer import render_entries as render_entries_view  # noqa: E402
from ui.ui_builder import UIBuilder  # noqa: E402
from ui.ui_gtk_helpers import GtkHelper  # noqa: E402
from ui.ui_state import AppState, AppStateManager  # noqa: E402

INFO = "info"
WARNING = "warning"
ERROR = "error"


class GrubConfigManager(Gtk.ApplicationWindow):
    """Fenêtre principale de l'application GTK (édition de `/etc/default/grub`)."""

    def __init__(self, application: Gtk.Application):
        """Initialise la fenêtre.

        Args:
            application: Instance `Gtk.Application`.
        """
        logger.debug("[GrubConfigManager.__init__] Démarrage initialisation de la fenêtre principale")
        title = "Gestionnaire de Configuration GRUB"
        super().__init__(application=application, title=title)
        self.set_default_size(850, 700)

        # Membres initialisés par les onglets (déclarés ici pour la lisibilité et pylint).
        # DEV: Ces références sont remplies par build_*_tab() lors de create_ui()
        self.timeout_dropdown: Gtk.DropDown | None = None
        self.default_dropdown: Gtk.DropDown | None = None
        self.hidden_timeout_check: Gtk.Switch | None = None
        self.cmdline_dropdown: Gtk.DropDown | None = None

        self.gfxmode_dropdown: Gtk.DropDown | None = None
        self.gfxpayload_dropdown: Gtk.DropDown | None = None

        self.disable_submenu_check: Gtk.Switch | None = None
        self.disable_recovery_check: Gtk.Switch | None = None
        self.disable_os_prober_check: Gtk.Switch | None = None

        self.entries_listbox: Gtk.ListBox | None = None

        # Widgets onglet Maintenance
        self.maintenance_output: Gtk.TextView | None = None

        # Widgets créés par UIBuilder
        self.info_revealer: Gtk.Revealer | None = None
        self.info_box: Gtk.Box | None = None
        self.info_label: Gtk.Label | None = None
        self.reload_btn: Gtk.Button | None = None
        self.save_btn: Gtk.Button | None = None

        # Délégation: Gestionnaire d'état
        self.state_manager = AppStateManager()

        self.create_ui()
        self.load_config()
        self.check_permissions()
        logger.success("[GrubConfigManager.__init__] Initialisation complète")

    # ========================================================================
    # HELPERS: Manipulation de widgets GTK (timeout, dropdown, etc.)
    # ========================================================================

    def _get_cmdline_value(self) -> str:
        """Obtient la valeur de GRUB_CMDLINE_LINUX_DEFAULT depuis le dropdown."""
        cmdline_dropdown = getattr(self, "cmdline_dropdown", None)
        if cmdline_dropdown is None:
            return "quiet splash"
        selected = cmdline_dropdown.get_selected()
        if selected == 0:  # quiet splash (recommandé)
            return "quiet splash"
        if selected == 1:  # quiet
            return "quiet"
        if selected == 2:  # splash
            return "splash"
        # verbose (aucun paramètre)
        return ""

    def _get_timeout_value(self) -> int:
        if self.timeout_dropdown is None:
            return 5
        val_str = GtkHelper.dropdown_get_value(self.timeout_dropdown, auto_prefix="NO_AUTO_PREFIX")
        try:
            return int(val_str)
        except (ValueError, TypeError):
            return 5

    def _sync_timeout_choices(self, current: int) -> None:
        if self.timeout_dropdown is None:
            logger.debug("[_sync_timeout_choices] timeout_dropdown is None")
            return
        model = self.timeout_dropdown.get_model()
        if model is None:
            logger.debug("[_sync_timeout_choices] model is None")
            return

        base_values = ["0", "1", "2", "5", "10", "30"]
        values = {v.strip() for v in base_values}
        values.add(str(int(current)))

        ordered: list[str] = []
        for v in sorted(values, key=int):
            ordered.append(v)

        logger.debug(f"[_sync_timeout_choices] current={current}, ordered={ordered}")

        GtkHelper.stringlist_replace_all(model, ordered)

        idx = GtkHelper.stringlist_find(model, str(int(current)))
        logger.debug(f"[_sync_timeout_choices] found idx={idx} for value={int(current)!s}")
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)
            logger.debug(f"[_sync_timeout_choices] selected index {idx}")
        else:
            logger.warning(f"[_sync_timeout_choices] could not find index for value {current}")

    def _ensure_timeout_choice(self, wanted: str) -> int | None:
        if self.timeout_dropdown is None:
            return None
        model = self.timeout_dropdown.get_model()
        if model is None:
            return None
        existing = GtkHelper.stringlist_find(model, wanted)
        if existing is not None:
            return existing

        try:
            wanted_int = int(wanted)
        except (TypeError, ValueError):
            wanted_int = None

        insert_at = model.get_n_items()
        if wanted_int is not None:
            for i in range(model.get_n_items()):
                try:
                    cur = int(str(model.get_string(i)))
                except (TypeError, ValueError):
                    continue
                if wanted_int < cur:
                    insert_at = i
                    break

        GtkHelper.stringlist_insert(model, insert_at, wanted)
        return GtkHelper.stringlist_find(model, wanted)

    def _set_timeout_value(self, value: int) -> None:
        if self.timeout_dropdown is None:
            return
        wanted = str(int(value))
        idx = self._ensure_timeout_choice(wanted)
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)
            return
        self.timeout_dropdown.set_selected(0)

    def _refresh_default_choices(self, entries: list[GrubDefaultChoice]) -> None:
        if self.default_dropdown is None:
            return
        model = self.default_dropdown.get_model()
        if model is None:
            return
        items: list[str] = ["saved (dernière sélection)"]
        ids: list[str] = ["saved"]
        for choice in entries:
            items.append(choice.title)
            ids.append(choice.id)
        self.state_manager.update_default_choice_ids(ids)
        GtkHelper.stringlist_replace_all(model, items)

    def _get_default_choice(self) -> str:
        if self.default_dropdown is None:
            return "0"
        idx = self.default_dropdown.get_selected()
        if idx is None:
            return "0"
        try:
            return self.state_manager.get_default_choice_ids()[int(idx)]
        except Exception:
            return "0"

    def _set_default_choice(self, value: str) -> None:
        if self.default_dropdown is None:
            return
        wanted = (value or "").strip() or "0"
        if wanted == "saved":
            self.default_dropdown.set_selected(0)
            return

        default_choice_ids = self.state_manager.get_default_choice_ids()
        for i, cid in enumerate(default_choice_ids):
            if cid == wanted:
                self.default_dropdown.set_selected(i)
                return

        model = self.default_dropdown.get_model()
        if model is not None:
            try:
                model.append(wanted)
                updated_ids = [*default_choice_ids, wanted]
                self.state_manager.update_default_choice_ids(updated_ids)
                self.default_dropdown.set_selected(len(updated_ids) - 1)
                return
            except Exception:
                pass

        self.default_dropdown.set_selected(0)

    # ========================================================================
    # SYNCHRONISATION: Modèle ↔ UI
    # ========================================================================

    def _apply_model_to_ui(self, model: GrubUiModel, entries: list[GrubDefaultChoice]) -> None:
        """Synchronize data model to GTK4 widgets."""
        logger.debug("[_apply_model_to_ui] Début - synchronisation modèle → UI")
        logger.debug(
            f"[_apply_model_to_ui] Model values: timeout={model.timeout}, "
            f"default={model.default}, hidden_timeout={model.hidden_timeout}"
        )
        logger.debug(f"[_apply_model_to_ui] Graphics: gfxmode={model.gfxmode}, gfxpayload={model.gfxpayload_linux}")
        logger.debug(
            f"[_apply_model_to_ui] Flags: disable_submenu={model.disable_submenu}, "
            f"disable_recovery={model.disable_recovery}, disable_os_prober={model.disable_os_prober}"
        )

        self.state_manager.set_loading(True)
        logger.debug("[_apply_model_to_ui] Loading flag set to True")
        try:
            self._sync_timeout_choices(int(model.timeout))

            if self.hidden_timeout_check is not None:
                self.hidden_timeout_check.set_active(bool(model.hidden_timeout))
                logger.debug(f"[_apply_model_to_ui] hidden_timeout_check.set_active({bool(model.hidden_timeout)})")

            # Configurer le dropdown cmdline selon les valeurs quiet/splash
            cmdline_dropdown = getattr(self, "cmdline_dropdown", None)
            if cmdline_dropdown is not None:
                if model.quiet and model.splash:
                    cmdline_dropdown.set_selected(0)  # quiet splash
                elif model.quiet:
                    cmdline_dropdown.set_selected(1)  # quiet
                elif model.splash:
                    cmdline_dropdown.set_selected(2)  # splash
                else:
                    cmdline_dropdown.set_selected(3)  # verbose
                logger.debug(f"[_apply_model_to_ui] cmdline_dropdown set to index {cmdline_dropdown.get_selected()}")

            if self.gfxmode_dropdown is not None:
                GtkHelper.dropdown_set_value(self.gfxmode_dropdown, model.gfxmode)
                logger.debug(f"[_apply_model_to_ui] gfxmode_dropdown set to '{model.gfxmode}'")
            if self.gfxpayload_dropdown is not None:
                GtkHelper.dropdown_set_value(self.gfxpayload_dropdown, model.gfxpayload_linux)
                logger.debug(f"[_apply_model_to_ui] gfxpayload_dropdown set to '{model.gfxpayload_linux}'")

            if self.disable_submenu_check is not None:
                self.disable_submenu_check.set_active(bool(model.disable_submenu))
                logger.debug(f"[_apply_model_to_ui] disable_submenu_check.set_active({bool(model.disable_submenu)})")
            if self.disable_recovery_check is not None:
                self.disable_recovery_check.set_active(bool(model.disable_recovery))
                logger.debug(f"[_apply_model_to_ui] disable_recovery_check.set_active({bool(model.disable_recovery)})")
            if self.disable_os_prober_check is not None:
                self.disable_os_prober_check.set_active(bool(model.disable_os_prober))
                logger.debug(
                    f"[_apply_model_to_ui] disable_os_prober_check.set_active({bool(model.disable_os_prober)})"
                )

            self._refresh_default_choices(entries)
            logger.debug(f"[_apply_model_to_ui] refresh_default_choices completed with {len(entries)} entries")

            self._set_default_choice(model.default)
            logger.debug(f"[_apply_model_to_ui] set_default_choice to '{model.default}'")

            logger.success(f"[_apply_model_to_ui] Synchronisation complète - {len(entries)} entrées disponibles")
        finally:
            self.state_manager.set_loading(False)
            logger.debug("[_apply_model_to_ui] Loading flag set to False")

    def _read_model_from_ui(self) -> GrubUiModel:
        """Extract current widget values into GrubUiModel for persistence."""
        logger.debug("[_read_model_from_ui] Début - lecture UI → modèle")

        default_value = self._get_default_choice()
        logger.debug(f"[_read_model_from_ui] default_value='{default_value}'")

        timeout_val = self._get_timeout_value()
        logger.debug(f"[_read_model_from_ui] timeout_val={timeout_val}")

        hidden_timeout = (
            bool(self.hidden_timeout_check.get_active()) if self.hidden_timeout_check is not None else False
        )
        logger.debug(f"[_read_model_from_ui] hidden_timeout={hidden_timeout}")

        gfxmode = (
            (GtkHelper.dropdown_get_value(self.gfxmode_dropdown) or "").strip()
            if self.gfxmode_dropdown is not None
            else ""
        )
        logger.debug(f"[_read_model_from_ui] gfxmode='{gfxmode}'")

        gfxpayload = (
            (GtkHelper.dropdown_get_value(self.gfxpayload_dropdown) or "").strip()
            if self.gfxpayload_dropdown is not None
            else ""
        )
        logger.debug(f"[_read_model_from_ui] gfxpayload='{gfxpayload}'")

        disable_submenu = (
            bool(self.disable_submenu_check.get_active()) if self.disable_submenu_check is not None else False
        )
        disable_recovery = (
            bool(self.disable_recovery_check.get_active()) if self.disable_recovery_check is not None else False
        )
        disable_os_prober = (
            bool(self.disable_os_prober_check.get_active()) if self.disable_os_prober_check is not None else False
        )
        logger.debug(
            f"[_read_model_from_ui] flags: disable_submenu={disable_submenu}, "
            f"disable_recovery={disable_recovery}, disable_os_prober={disable_os_prober}"
        )

        # Lire les paramètres kernel depuis le dropdown
        cmdline_value = self._get_cmdline_value()
        quiet = "quiet" in cmdline_value
        splash = "splash" in cmdline_value
        logger.debug(f"[_read_model_from_ui] cmdline='{cmdline_value}', quiet={quiet}, splash={splash}")

        # Lire le thème actif depuis le gestionnaire de thème
        grub_theme = ""
        try:
            theme_manager = ActiveThemeManager()
            active_theme = theme_manager.get_active_theme()
            if active_theme and active_theme.name:
                # Construire le chemin vers le fichier theme.txt
                theme_dir = get_grub_themes_dir()
                grub_theme = str(theme_dir / active_theme.name / "theme.txt")
                logger.debug(f"[_read_model_from_ui] grub_theme='{grub_theme}'")
        except (OSError, RuntimeError) as e:
            logger.debug(f"[_read_model_from_ui] Pas de thème actif: {e}")

        model = GrubUiModel(
            timeout=timeout_val,
            default=default_value,
            save_default=(default_value == "saved"),
            hidden_timeout=hidden_timeout,
            gfxmode=gfxmode,
            gfxpayload_linux=gfxpayload,
            disable_submenu=disable_submenu,
            disable_recovery=disable_recovery,
            disable_os_prober=disable_os_prober,
            grub_theme=grub_theme,
            quiet=quiet,
            splash=splash,
        )
        logger.success("[_read_model_from_ui] Modèle extrait avec succès")
        return model

    # ========================================================================
    # CONSTRUCTION UI & CHARGEMENT
    # ========================================================================

    def create_ui(self):
        """Build main GTK4 window with all UI components and event handlers."""
        UIBuilder.create_main_ui(self)
        self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

    def check_permissions(self):
        """Affiche un avertissement si l'application n'a pas les droits root."""
        uid = os.geteuid()
        if uid != 0:
            logger.warning(f"[check_permissions] ATTENTION: Non exécuté en tant que root (uid={uid})")
            self.show_info(
                "Cette application nécessite les droits administrateur pour modifier la configuration GRUB. "
                "Relancez avec: sudo python3 " + os.path.basename(__file__),
                WARNING,
            )
        else:
            logger.success("[check_permissions] Exécuté en tant que root - OK")

    def load_config(self):
        """Charge la configuration depuis le système et met à jour l'UI."""
        logger.info("[load_config] Début du chargement de configuration GRUB")
        try:
            # Vérifier la synchronisation des fichiers GRUB
            sync_status = check_grub_sync()

            if not sync_status.in_sync and sync_status.grub_default_exists and sync_status.grub_cfg_exists:
                logger.warning(f"[load_config] Fichiers désynchronisés: {sync_status.message}")
                self.show_info(
                    f"⚠ {sync_status.message}",
                    WARNING,
                )

            state = load_grub_ui_state()
            self.state_manager.update_state_data(state)
            self._apply_model_to_ui(state.model, state.entries)
            render_entries_view(self)
            self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

            # Vérifier si le menu est caché et alerter l'utilisateur
            if state.model.hidden_timeout:
                logger.warning("[load_config] Menu GRUB caché (hidden_timeout=True)")
                self.show_info(
                    "Info: Le menu GRUB est configuré en mode caché. "
                    "Décochez 'Cacher le menu' dans l'onglet Général pour l'afficher au démarrage.",
                    INFO,
                )

            if self.state_manager.hidden_entry_ids:
                logger.warning(
                    f"[load_config] {len(self.state_manager.hidden_entry_ids)} entrée(s) masquée(s): "
                    f"{self.state_manager.hidden_entry_ids}"
                )
                self.show_info(
                    f"ATTENTION: {len(self.state_manager.hidden_entry_ids)} entrée(s) GRUB sont masquées. "
                    f"Allez dans l'onglet Entrées pour les gérer.",
                    WARNING,
                )

            if not state.entries and os.geteuid() != 0:
                self.show_info(
                    "Entrées GRUB indisponibles: lecture de /boot/grub/grub.cfg refusée (droits). "
                    "Relancez l'application avec pkexec/sudo.",
                    WARNING,
                )
            elif not state.entries and os.geteuid() == 0:
                self.show_info(
                    "Aucune entrée GRUB détectée dans grub.cfg. Vérifiez que grub.cfg est présent et valide.",
                    WARNING,
                )

            logger.success("[load_config] Configuration chargée et UI synchronisée")

        except FileNotFoundError as e:
            logger.error(f"[load_config] ERREUR: Fichier /etc/default/grub introuvable - {e}")
            self.show_info("Fichier /etc/default/grub introuvable", ERROR)
        except Exception as e:
            logger.exception("[load_config] ERREUR inattendue lors du chargement")
            self.show_info(f"Erreur lors du chargement: {e!s}", ERROR)

    # ========================================================================
    # CALLBACKS: Événements UI
    # ========================================================================

    def on_modified(self, _widget, *_args):
        """Mark configuration as modified when any widget value changes."""
        if self.state_manager.is_loading():
            logger.debug("[on_modified] Ignored - loading in progress")
            return
        logger.debug(f"[on_modified] Configuration marked as modified by {_widget.__class__.__name__}")
        self.state_manager.mark_dirty(self.save_btn, self.reload_btn)

    def on_hidden_timeout_toggled(self, widget):
        """Toggle hidden timeout mode (GRUB_TIMEOUT_STYLE between hidden/menu)."""
        if self.state_manager.is_loading():
            logger.debug("[on_hidden_timeout_toggled] Ignored - loading in progress")
            return
        active = widget.get_active()
        logger.debug(f"[on_hidden_timeout_toggled] hidden_timeout toggled to {active}")
        if active:
            logger.debug("[on_hidden_timeout_toggled] Setting timeout choices to 0")
            self._sync_timeout_choices(0)
            self._set_timeout_value(0)
        self.on_modified(widget)

    def on_menu_options_toggled(self, widget):
        """Toggle visibility of advanced menu options."""
        if self.state_manager.is_loading():
            logger.debug("[on_menu_options_toggled] Ignored - loading in progress")
            return
        logger.debug(f"[on_menu_options_toggled] Menu option toggled - {widget.__class__.__name__}")
        self.on_modified(widget)
        render_entries_view(self)

    def on_reload(self, _button):
        """Reload GRUB configuration from disk, discarding all UI changes."""
        logger.info("[on_reload] Demande de recharge")
        logger.debug(f"[on_reload] Config modified state: {self.state_manager.modified}")
        if self.state_manager.modified:
            logger.debug("[on_reload] Showing confirmation dialog")
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
                    logger.debug(f"[on_reload._on_choice] Dialog result: {idx}")
                except GLib.Error as e:
                    logger.debug(f"[on_reload._on_choice] Dialog cancelled: {e}")

                if idx == 1:
                    logger.debug("[on_reload._on_choice] User confirmed reload")
                    self.load_config()
                    self.show_info("Configuration rechargée", INFO)

            dialog.choose(self, None, _on_choice)
            return

        logger.debug("[on_reload] No modifications, reloading config")
        self.load_config()
        self.show_info("Configuration rechargée", INFO)

    def on_save(self, _button):
        """Validate UI values and save configuration using ApplyManager."""
        logger.info("[on_save] Demande de sauvegarde")
        logger.debug(f"[on_save] Current UID: {os.geteuid()}")

        if os.geteuid() != 0:
            logger.error("[on_save] Not running as root")
            self.show_info("Droits administrateur requis pour enregistrer", ERROR)
            return

        logger.debug("[on_save] Showing confirmation dialog")
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
                logger.debug(f"[on_save._on_response] Dialog result: {idx}")
            except GLib.Error as e:
                logger.debug(f"[on_save._on_response] Dialog cancelled: {e}")

            if idx == 1:
                logger.debug("[on_save._on_response] User confirmed save")
                self._perform_save(apply_now=True)

        dialog.choose(self, None, _on_response)

    def _perform_save(self, apply_now: bool):
        """Execute save workflow using ApplyManager."""
        logger.info(f"[_perform_save] Début du workflow de sauvegarde (apply_now={apply_now})")
        self.state_manager.apply_state(AppState.APPLYING, self.save_btn, self.reload_btn)

        try:
            model = self._read_model_from_ui()
            logger.debug(f"[_perform_save] Model read from UI: timeout={model.timeout}, default={model.default}")

            merged_config = merged_config_from_model(self.state_manager.state_data.raw_config, model)
            logger.debug(f"[_perform_save] Config merged, apply_now={apply_now}")

            manager = GrubApplyManager()
            result = manager.apply_configuration(merged_config, apply_changes=apply_now)
            logger.debug(f"[_perform_save] Apply result: success={result.success}")

            if result.success:
                logger.debug("[_perform_save] Configuration applied successfully")

                # Vérification post-application: lire le fichier pour confirmer
                try:
                    verified_config = read_grub_default()
                    matches = (
                        verified_config.get("GRUB_TIMEOUT") == str(model.timeout)
                        and verified_config.get("GRUB_DEFAULT") == model.default
                    )
                    logger.debug(f"[_perform_save] Vérification: matches={matches}")

                    if not matches:
                        logger.warning("[_perform_save] ATTENTION: Valeurs écrites ne correspondent pas au modèle")
                except Exception as e:
                    logger.warning(f"[_perform_save] Impossible de vérifier les valeurs écrites: {e}")

                self.state_manager.update_state_data(
                    GrubUiState(model=model, entries=self.state_manager.state_data.entries, raw_config=merged_config)
                )
                self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

                msg = result.message
                msg_type = INFO

                # Ajouter détails de vérification si disponibles
                if result.details:
                    msg += f"\n{result.details}"

                if apply_now:
                    if self.state_manager.hidden_entry_ids:
                        try:
                            used_path, masked = apply_hidden_entries_to_grub_cfg(self.state_manager.hidden_entry_ids)
                            self.state_manager.entries_visibility_dirty = False
                            msg += f"\nEntrées masquées: {masked} ({used_path})"
                        except Exception as e:
                            logger.error(f"[_perform_save] ERREUR masquage: {e}")
                            msg += f"\nAttention: Masquage échoué: {e}"
                            msg_type = WARNING
                elif self.state_manager.entries_visibility_dirty and not apply_now:
                    msg += "\n(Masquage non appliqué car update-grub ignoré)"

                self.show_info(msg, msg_type)
            else:
                self.state_manager.apply_state(AppState.DIRTY, self.save_btn, self.reload_btn)
                self.show_info(f"Erreur: {result.message}", ERROR)

        except Exception as e:
            logger.exception("[_perform_save] ERREUR inattendue")
            self.state_manager.apply_state(AppState.DIRTY, self.save_btn, self.reload_btn)
            self.show_info(f"Erreur inattendue: {e}", ERROR)

    def _hide_info_callback(self):
        if self.info_revealer is None:
            return False
        self.info_revealer.set_reveal_child(False)
        return False

    def show_info(self, message, msg_type):
        """Display temporary message in info area."""
        if self.info_label is None:
            return
        self.info_label.set_text(message)

        if self.info_box is None or self.info_revealer is None:
            return

        for klass in ("info", "warning", "error"):
            if self.info_box.has_css_class(klass):
                self.info_box.remove_css_class(klass)
        if msg_type in (INFO, WARNING, ERROR):
            self.info_box.add_css_class(msg_type)

        self.info_revealer.set_reveal_child(True)

        GLib.timeout_add_seconds(5, self._hide_info_callback)
