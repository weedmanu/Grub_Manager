"""GTK4 UI layer - Fenêtre principale.

Contient uniquement l'orchestration (délègue construction UI et gestion d'état).
"""

# isort: skip_file

# Pylint: l'ordre d'import est imposé par `gi.require_version()`, et l'UI attrape
# volontairement des exceptions larges aux frontières (affichage d'erreurs).
# pylint: disable=wrong-import-position,broad-exception-caught

from __future__ import annotations

import os

import gi
from loguru import logger

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk

from core.core_exceptions import GrubConfigError, GrubParsingError
from core.config.core_paths import get_grub_themes_dir
from core.managers.core_apply_manager import GrubApplyManager
from core.managers.core_entry_visibility_manager import apply_hidden_entries_to_grub_cfg, save_hidden_entry_ids
from core.models.core_grub_ui_model import merged_config_from_model
from core.system.core_grub_system_commands import GrubDefaultChoice, GrubUiModel, load_grub_ui_state, run_update_grub
from core.system.core_sync_checker import check_grub_sync
from core.theme.core_active_theme_manager import ActiveThemeManager
from ui.tabs.ui_entries_renderer import render_entries as render_entries_view
from ui.ui_builder import UIBuilder
from ui.ui_gtk_helpers import GtkHelper
from ui.ui_infobar_controller import InfoBarController, INFO, WARNING, ERROR
from ui.ui_model_mapper import ModelWidgetMapper
from ui.ui_workflow_controller import WorkflowController
from ui.ui_state import AppState, AppStateManager
from ui.controllers import PermissionController

__all__ = [
    "ActiveThemeManager",
    "GrubApplyManager",
    "GrubConfigManager",
    "apply_hidden_entries_to_grub_cfg",
    "get_grub_themes_dir",
    "merged_config_from_model",
]


class GrubConfigManager(Gtk.ApplicationWindow):
    """Fenêtre principale de l'application GTK (édition de `/etc/default/grub`).

    Implémente les Protocols (interfaces ségrégées):
    - TimeoutWidget: gestion du timeout GRUB
    - DefaultChoiceWidget: gestion du choix par défaut
    - ConfigModelMapper: sync modèle ↔ widgets
    - PermissionChecker: vérifications de permissions
    - InfoDisplay: affichage de messages

    Note: Les Protocols sont utilisés pour la vérification de type statique (mypy),
          pas hérités à runtime (incompatibilité métaclasse GTK).
    """

    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    # Membres pour les contrôleurs délégués (déclarés ici pour les tests qui bypassent __init__)
    infobar: InfoBarController | None = None
    workflow: WorkflowController | None = None

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

        self.disable_os_prober_check: Gtk.Switch | None = None

        # Options globales de masquage (via hidden_entries.json + post-traitement grub.cfg)
        self.hide_advanced_options_check: Gtk.Switch | None = None
        self.hide_memtest_check: Gtk.Switch | None = None

        self.entries_listbox: Gtk.ListBox | None = None

        # Contrôleur de l'onglet Thème
        from ui.tabs.ui_tab_theme_config import TabThemeConfig

        self.theme_config_controller: TabThemeConfig | None = None

        # Widgets créés par UIBuilder
        self.info_revealer: Gtk.Revealer | None = None
        self.info_box: Gtk.Box | None = None
        self.info_label: Gtk.Label | None = None
        self.reload_btn: Gtk.Button | None = None
        self.save_btn: Gtk.Button | None = None

        # Contrôleurs délégués
        self.infobar: InfoBarController | None = None
        self.workflow: WorkflowController | None = None
        self.state_manager = AppStateManager()

        # Contrôleurs SRP (Single Responsibility)
        self.perm_ctrl = PermissionController()

        self.create_ui()
        self.load_config(refresh_grub=True)
        self.check_permissions()
        logger.success("[GrubConfigManager.__init__] Initialisation complète")

    def _apply_state(self, state: AppState) -> None:
        """Wrapper interne pour synchroniser l'état et les boutons.

        Certains handlers (ex: renderer des entrées) appellent cette méthode.
        """
        self.state_manager.apply_state(state, self.save_btn, self.reload_btn)

    # ========================================================================
    # HELPERS: Manipulation de widgets GTK (timeout, dropdown, etc.)
    # ========================================================================

    def get_cmdline_value(self) -> str:
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

    def get_timeout_value(self) -> int:
        """Récupère la valeur du timeout depuis le widget."""
        if self.timeout_dropdown is None:
            return 5
        val_str = GtkHelper.dropdown_get_value(self.timeout_dropdown, auto_prefix="NO_AUTO_PREFIX")
        try:
            return int(val_str)
        except (ValueError, TypeError):
            return 5

    def sync_timeout_choices(self, current: int) -> None:
        """Met à jour la liste des choix du timeout pour inclure la valeur actuelle."""
        if self.timeout_dropdown is None:
            logger.debug("[sync_timeout_choices] timeout_dropdown is None")
            return
        model = self.timeout_dropdown.get_model()
        if model is None:
            logger.debug("[sync_timeout_choices] model is None")
            return

        base_values = ["0", "1", "2", "5", "10", "30"]
        values = {v.strip() for v in base_values}
        values.add(str(int(current)))

        ordered: list[str] = []
        for v in sorted(values, key=int):
            ordered.append(v)

        logger.debug(f"[sync_timeout_choices] current={current}, ordered={ordered}")

        GtkHelper.stringlist_replace_all(model, ordered)

        idx = GtkHelper.stringlist_find(model, str(int(current)))
        logger.debug(f"[sync_timeout_choices] found idx={idx} for value={int(current)!s}")
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)
            logger.debug(f"[sync_timeout_choices] selected index {idx}")
        else:
            logger.warning(f"[sync_timeout_choices] could not find index for value {current}")

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

    def set_timeout_value(self, value: int) -> None:
        """Définit la valeur sélectionnée dans le dropdown timeout."""
        if self.timeout_dropdown is None:
            return
        wanted = str(int(value))
        idx = self._ensure_timeout_choice(wanted)
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)
            return
        self.timeout_dropdown.set_selected(0)

    def refresh_default_choices(self, entries: list[GrubDefaultChoice]) -> None:
        """Met à jour la liste des choix pour l'entrée par défaut."""
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

    def get_default_choice(self) -> str:
        """Récupère l'ID de l'entrée par défaut sélectionnée."""
        if self.default_dropdown is None:
            return "0"
        idx = self.default_dropdown.get_selected()
        if idx is None:
            return "0"
        try:
            return self.state_manager.get_default_choice_ids()[int(idx)]
        except Exception:
            return "0"

    def set_default_choice(self, value: str) -> None:
        """Définit l'entrée par défaut sélectionnée dans le dropdown."""
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

    def apply_model_to_ui(self, model: GrubUiModel, entries: list[GrubDefaultChoice]) -> None:
        """Synchronize data model to GTK4 widgets."""
        ModelWidgetMapper.apply_model_to_ui(self, model, entries)

    def read_model_from_ui(self) -> GrubUiModel:
        """Extract current widget values into GrubUiModel for persistence."""
        return ModelWidgetMapper.read_model_from_ui(self)

    # ========================================================================
    # CONSTRUCTION UI & CHARGEMENT
    # ========================================================================

    def create_ui(self):
        """Build main GTK4 window with all UI components and event handlers."""
        UIBuilder.create_main_ui(self)
        self.infobar = InfoBarController(self.info_revealer, self.info_box, self.info_label)
        self.workflow = WorkflowController(
            window=self,
            state_manager=self.state_manager,
            save_btn=self.save_btn,
            reload_btn=self.reload_btn,
            load_config_cb=self.load_config,
            read_model_cb=self.read_model_from_ui,
            show_info_cb=self.show_info,
        )
        self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

    def check_permissions(self):
        """Affiche un avertissement si l'application n'a pas les droits root."""
        self.perm_ctrl.check_and_warn(self.show_info)

    def load_config(self, refresh_grub: bool = False) -> None:
        """Charge la configuration depuis le système et met à jour l'UI.

        Args:
            refresh_grub: Si True et root, exécute update-grub avant de charger.
        """
        logger.info(f"[load_config] Début du chargement (refresh_grub={refresh_grub})")
        try:
            # Mise à jour des entrées GRUB (os-prober) au démarrage si root
            if refresh_grub and os.geteuid() == 0:
                logger.info("[load_config] Exécution de update-grub pour rafraîchir les entrées...")
                # On pourrait afficher un splash screen ici, mais pour l'instant on bloque
                # car c'est requis avant de charger la config.
                res = run_update_grub()
                if res.returncode != 0:
                    logger.warning(f"[load_config] update-grub a échoué: {res.stderr}")
                    self.show_info(f"Erreur lors de la mise à jour GRUB: {res.stderr}", WARNING)
                else:
                    logger.success("[load_config] update-grub terminé avec succès")

            state = load_grub_ui_state()
            self.state_manager.update_state_data(state)
            self.apply_model_to_ui(state.model, state.entries)
            render_entries_view(self)

            # On applique l'état CLEAN par défaut
            self.state_manager.apply_state(AppState.CLEAN, self.save_btn, self.reload_btn)

            # Mais on vérifie la synchro APRES avoir chargé l'état
            # Si désynchronisé, _check_sync_status passera l'état à DIRTY
            self._check_sync_status()

            self._validate_and_warn(state)

            logger.success("[load_config] Configuration chargée et UI synchronisée")

        except FileNotFoundError as e:
            logger.error(f"[load_config] ERREUR: Fichier /etc/default/grub introuvable - {e}")
            self.show_info("Fichier /etc/default/grub introuvable", ERROR)
        except (GrubParsingError, GrubConfigError) as e:
            logger.error(f"[load_config] Configuration invalide: {e}")
            self.show_info(f"Configuration GRUB invalide: {e}", ERROR)
        except OSError as e:
            logger.error(f"[load_config] Erreur d'accès fichier: {e}")
            self.show_info(f"Impossible de lire la configuration: {e}", ERROR)

    def _check_sync_status(self):
        """Vérifie la synchronisation entre /etc/default/grub et grub.cfg."""
        sync_status = check_grub_sync()

        if not sync_status.in_sync and sync_status.grub_default_exists and sync_status.grub_cfg_exists:
            logger.warning(f"[load_config] Fichiers désynchronisés: {sync_status.message}")
            self.show_info(
                f"⚠ {sync_status.message}",
                WARNING,
            )
            # Si désynchronisé, on permet d'appliquer (update-grub) même si l'UI est "clean"
            # On marque l'état comme DIRTY pour activer le bouton Appliquer
            self.state_manager.mark_dirty(self.save_btn, self.reload_btn)

    def _validate_and_warn(self, state):
        """Valide l'état chargé et affiche des avertissements si nécessaire."""
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
            self.sync_timeout_choices(0)
            self.set_timeout_value(0)
        self.on_modified(widget)

    def on_menu_options_toggled(self, widget, _pspec=None):
        """Toggle visibility of advanced menu options.

        Connected to GTK signals like ``notify::active`` which pass (widget, pspec).
        """
        if self.state_manager.is_loading():
            logger.debug("[on_menu_options_toggled] Ignored - loading in progress")
            return
        logger.debug(f"[on_menu_options_toggled] Menu option toggled - {widget.__class__.__name__}")
        self.on_modified(widget)
        render_entries_view(self)

    def on_hide_category_toggled(self, widget, _pspec=None) -> None:
        """Masque/démasque en bloc certaines catégories d'entrées (Advanced options, memtest).

        Implémenté via hidden_entries.json + post-traitement de grub.cfg lors de l'application.
        """
        if self.state_manager.is_loading():
            logger.debug("[on_hide_category_toggled] Ignored - loading in progress")
            return

        category = getattr(widget, "category_name", "")
        active = bool(widget.get_active())
        entries = list(self.state_manager.state_data.entries or [])

        def _ids_for_advanced() -> set[str]:
            ids: set[str] = set()
            for e in entries:
                mid = (getattr(e, "menu_id", "") or "").strip()
                if not mid:
                    continue
                t = (getattr(e, "title", "") or "").lower()
                if "advanced options" in t or "options avanc" in t:
                    ids.add(mid)
            return ids

        def _ids_for_memtest() -> set[str]:
            ids: set[str] = set()
            for e in entries:
                mid = (getattr(e, "menu_id", "") or "").strip()
                if not mid:
                    continue
                t = (getattr(e, "title", "") or "").lower()
                src = (getattr(e, "source", "") or "").lower()
                if "memtest" in t or "memtest" in src:
                    ids.add(mid)
            return ids

        if category == "advanced_options":
            ids = _ids_for_advanced()
        elif category == "memtest":
            ids = _ids_for_memtest()
        else:
            logger.debug(f"[on_hide_category_toggled] Unknown category='{category}'")
            return

        if not ids:
            logger.debug(f"[on_hide_category_toggled] No matching IDs for '{category}'")
            return

        if active:
            self.state_manager.hidden_entry_ids |= ids
        else:
            self.state_manager.hidden_entry_ids -= ids

        save_hidden_entry_ids(self.state_manager.hidden_entry_ids)
        self.state_manager.entries_visibility_dirty = True
        self._apply_state(self.state_manager.state)
        render_entries_view(self)

    def on_reload(self, button):
        """Reload GRUB configuration from disk, discarding all UI changes."""
        if self.workflow:
            self.workflow.on_reload(button)

    def on_save(self, button):
        """Validate UI values and save configuration using ApplyManager."""
        if self.workflow:
            self.workflow.on_save(button)

    def perform_save(self, apply_now: bool):
        """Wrapper pour compatibilité avec les tests."""
        if self.workflow:
            self.workflow.perform_save(apply_now)

    def hide_info_callback(self):
        """Wrapper pour compatibilité avec les tests."""
        if self.infobar:
            return self.infobar.hide_info_callback()
        return False

    def show_info(self, message, msg_type):
        """Display temporary message in info area."""
        if self.infobar:
            self.infobar.show(message, msg_type)
        elif self.info_label:
            # Fallback pour les tests qui n'initialisent pas infobar
            self.info_label.set_text(message)
            if self.info_revealer:
                self.info_revealer.set_reveal_child(True)
