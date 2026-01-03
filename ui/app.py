"""GTK4 UI layer.

Contient uniquement l'interface et l'orchestration (utilise grub_core).
"""

# Pylint: l'ordre d'import est imposé par `gi.require_version()`, et l'UI attrape
# volontairement des exceptions larges aux frontières (affichage d'erreurs).
# pylint: disable=wrong-import-position,broad-exception-caught

from __future__ import annotations

import os
from enum import Enum

import gi
from loguru import logger

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import GLib, Gtk  # noqa: E402

from core.apply_manager import GrubApplyManager  # noqa: E402
from core.entry_visibility import apply_hidden_entries_to_grub_cfg, load_hidden_entry_ids  # noqa: E402
from core.grub import (  # noqa: E402
    GrubDefaultChoice,
    GrubUiModel,
    GrubUiState,
    load_grub_ui_state,
)
from core.model import merged_config_from_model  # noqa: E402
from ui.tabs.backups import build_backups_tab  # noqa: E402
from ui.tabs.display import build_display_tab  # noqa: E402
from ui.tabs.entries import build_entries_tab  # noqa: E402
from ui.tabs.entries_view import render_entries as render_entries_view  # noqa: E402
from ui.tabs.general import build_general_tab  # noqa: E402

INFO = "info"
WARNING = "warning"
ERROR = "error"


class AppState(str, Enum):
    """État interne de la fenêtre (propre/modifié/en cours d'application)."""

    CLEAN = "clean"
    DIRTY = "dirty"
    APPLYING = "applying"


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
        self.set_default_size(800, 600)

        # Membres initialisés par les onglets (déclarés ici pour la lisibilité et pylint).
        # DEV: Ces références sont remplies par build_*_tab() lors de create_ui()
        self.timeout_dropdown: Gtk.DropDown | None = None
        self.default_dropdown: Gtk.DropDown | None = None
        self.hidden_timeout_check: Gtk.CheckButton | None = None

        self.gfxmode_dropdown: Gtk.DropDown | None = None
        self.gfxpayload_dropdown: Gtk.DropDown | None = None

        self.color_normal_fg_dropdown: Gtk.DropDown | None = None
        self.color_normal_bg_dropdown: Gtk.DropDown | None = None
        self.color_highlight_fg_dropdown: Gtk.DropDown | None = None
        self.color_highlight_bg_dropdown: Gtk.DropDown | None = None

        self.disable_submenu_check: Gtk.CheckButton | None = None
        self.disable_recovery_check: Gtk.CheckButton | None = None
        self.disable_os_prober_check: Gtk.CheckButton | None = None
        self.terminal_color_check: Gtk.CheckButton | None = None

        self.entries_listbox: Gtk.ListBox | None = None

        # État de l'application
        self.state_data = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})
        self._default_choice_ids: list[str] = ["saved"]
        self.modified = False
        self.state = AppState.CLEAN
        self._loading = False  # DEV: Flag pour ignorer les changements UI lors du chargement initial

        # Gestion des entrées masquées
        self.hidden_entry_ids: set[str] = load_hidden_entry_ids()
        self.entries_visibility_dirty = False

        self.create_ui()
        self.load_config()
        self.check_permissions()
        logger.success("[GrubConfigManager.__init__] Initialisation complète")

    def _get_timeout_value(self) -> int:
        if self.timeout_dropdown is None:
            return 5
        idx = self.timeout_dropdown.get_selected()
        model = self.timeout_dropdown.get_model()
        if idx is None or model is None:
            return 5
        try:
            return int(str(model.get_string(int(idx))))
        except (TypeError, ValueError):
            return 5

    def _stringlist_find(self, model, wanted: str) -> int | None:
        if model is None:
            return None
        for i in range(model.get_n_items()):
            if str(model.get_string(i)) == wanted:
                return i
        return None

    def _stringlist_insert(self, model, index: int, value: str) -> None:
        try:
            model.splice(index, 0, [value])
        except Exception:
            model.append(value)

    def _sync_timeout_choices(self, current: int) -> None:
        if self.timeout_dropdown is None:
            return
        model = self.timeout_dropdown.get_model()
        if model is None:
            return

        base_values = ["0", "1", "2", "5", "10", "30"]
        values = {v.strip() for v in base_values}
        values.add(str(int(current)))

        # Tri numérique croissant, valeurs uniques.
        ordered: list[str] = []
        for v in sorted(values, key=int):
            ordered.append(v)

        try:
            model.splice(0, model.get_n_items(), ordered)
        except Exception:
            while model.get_n_items() > 0:
                model.remove(0)
            for v in ordered:
                model.append(v)

        idx = self._stringlist_find(model, str(int(current)))
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)

    def _ensure_timeout_choice(self, wanted: str) -> int | None:
        if self.timeout_dropdown is None:
            return None
        model = self.timeout_dropdown.get_model()
        if model is None:
            return None
        existing = self._stringlist_find(model, wanted)
        if existing is not None:
            return existing

        # Insertion triée (numérique) pour éviter une liste "bizarre".
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

        self._stringlist_insert(model, insert_at, wanted)
        return self._stringlist_find(model, wanted)

    def _set_timeout_value(self, value: int) -> None:
        if self.timeout_dropdown is None:
            return
        wanted = str(int(value))
        idx = self._ensure_timeout_choice(wanted)
        if idx is not None:
            self.timeout_dropdown.set_selected(idx)
            return
        self.timeout_dropdown.set_selected(0)

    def _dropdown_get_value(self, dropdown: Gtk.DropDown, *, auto_prefix: str = "auto") -> str:
        idx = dropdown.get_selected()
        model = dropdown.get_model()
        if idx is None or model is None:
            return ""
        try:
            label = str(model.get_string(int(idx)))
        except Exception:
            return ""
        if label.startswith(auto_prefix):
            return ""
        return label

    def _dropdown_set_value(self, dropdown: Gtk.DropDown, value: str, *, auto_prefix: str = "auto") -> None:
        model = dropdown.get_model()
        if model is None:
            return

        wanted = (value or "").strip()
        if not wanted:
            for i in range(model.get_n_items()):
                if str(model.get_string(i)).startswith(auto_prefix):
                    dropdown.set_selected(i)
                    return
            dropdown.set_selected(0)
            return

        for i in range(model.get_n_items()):
            if str(model.get_string(i)) == wanted:
                dropdown.set_selected(i)
                return

        # Valeur non prévue par la liste: on l'ajoute pour refléter la config réelle.
        # (Toujours après le premier item "auto (défaut)" si présent.)
        has_auto = model.get_n_items() >= 1 and str(model.get_string(0)).startswith(auto_prefix)
        insert_at = 1 if has_auto else model.get_n_items()
        self._stringlist_insert(model, insert_at, wanted)
        idx = self._stringlist_find(model, wanted)
        if idx is not None:
            dropdown.set_selected(idx)
            return

        for i in range(model.get_n_items()):
            if str(model.get_string(i)).startswith(auto_prefix):
                dropdown.set_selected(i)
                return
        dropdown.set_selected(0)

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
        self._default_choice_ids = ids
        try:
            model.splice(0, model.get_n_items(), items)
        except Exception:
            while model.get_n_items() > 0:
                model.remove(0)
            for it in items:
                model.append(it)

    def _get_default_choice(self) -> str:
        if self.default_dropdown is None:
            return "0"
        idx = self.default_dropdown.get_selected()
        if idx is None:
            return "0"
        try:
            return self._default_choice_ids[int(idx)]
        except Exception:
            return "0"

    def _set_default_choice(self, value: str) -> None:
        if self.default_dropdown is None:
            return
        wanted = (value or "").strip() or "0"
        if wanted == "saved":
            self.default_dropdown.set_selected(0)
            return

        for i, cid in enumerate(self._default_choice_ids):
            if cid == wanted:
                self.default_dropdown.set_selected(i)
                return

        # Si GRUB_DEFAULT est un libellé (mode "string") ou une valeur inattendue,
        # on l'ajoute à la liste pour refléter la config actuelle (sans champ texte).
        model = self.default_dropdown.get_model()
        if model is not None:
            try:
                model.append(wanted)
                self._default_choice_ids.append(wanted)
                self.default_dropdown.set_selected(len(self._default_choice_ids) - 1)
                return
            except Exception:
                pass

        self.default_dropdown.set_selected(0)

    def _apply_model_to_ui(self, model: GrubUiModel, entries: list[GrubDefaultChoice]) -> None:
        """Synchronize data model to GTK4 widgets.

        DEV: Used on startup and after reload. _loading flag prevents loops.
        """
        logger.debug("[_apply_model_to_ui] Début - synchronisation modèle → UI")
        self._loading = True
        try:
            # === Délai et menu caché ===
            self._sync_timeout_choices(int(model.timeout))
            self._set_timeout_value(int(model.timeout))
            logger.debug(f"[_apply_model_to_ui] Timeout={model.timeout}s, Hidden={model.hidden_timeout}")
            if self.hidden_timeout_check is not None:
                self.hidden_timeout_check.set_active(bool(model.hidden_timeout))

            # === Affichage graphique ===
            if self.gfxmode_dropdown is not None:
                self._dropdown_set_value(self.gfxmode_dropdown, model.gfxmode)
            if self.gfxpayload_dropdown is not None:
                self._dropdown_set_value(self.gfxpayload_dropdown, model.gfxpayload_linux)
            logger.debug(f"[_apply_model_to_ui] Gfxmode={model.gfxmode}, Gfxpayload={model.gfxpayload_linux}")

            # === Couleurs ===
            if self.color_normal_fg_dropdown is not None:
                self._dropdown_set_value(self.color_normal_fg_dropdown, model.color_normal_fg)
            if self.color_normal_bg_dropdown is not None:
                self._dropdown_set_value(self.color_normal_bg_dropdown, model.color_normal_bg)
            if self.color_highlight_fg_dropdown is not None:
                self._dropdown_set_value(self.color_highlight_fg_dropdown, model.color_highlight_fg)
            if self.color_highlight_bg_dropdown is not None:
                self._dropdown_set_value(self.color_highlight_bg_dropdown, model.color_highlight_bg)
            logger.debug(
                f"[_apply_model_to_ui] Couleurs: normal={model.color_normal_fg}/{model.color_normal_bg}, highlight={model.color_highlight_fg}/{model.color_highlight_bg}"
            )

            # === Options booléennes ===
            if self.disable_submenu_check is not None:
                self.disable_submenu_check.set_active(bool(model.disable_submenu))
            if self.disable_recovery_check is not None:
                self.disable_recovery_check.set_active(bool(model.disable_recovery))
            if self.disable_os_prober_check is not None:
                self.disable_os_prober_check.set_active(bool(model.disable_os_prober))
            if self.terminal_color_check is not None:
                self.terminal_color_check.set_active(bool(model.terminal_color))
            logger.debug(
                f"[_apply_model_to_ui] Options: submenu={model.disable_submenu}, recovery={model.disable_recovery}, os_prober={model.disable_os_prober}, terminal_color={model.terminal_color}"
            )

            # === Entrées GRUB ===
            self._refresh_default_choices(entries)
            self._set_default_choice(model.default)
            logger.success(f"[_apply_model_to_ui] Synchronisation complète - {len(entries)} entrées disponibles")
        finally:
            self._loading = False

    def _read_model_from_ui(self) -> GrubUiModel:
        """Extract current widget values into GrubUiModel for persistence.

        Collects timeout, default entry, disabled options, and color settings
        from all GTK4 widgets. Used before save operation to synchronize UI
        state to the data model.

        Returns:
            GrubUiModel with all current UI values.
        """
        logger.debug("[_read_model_from_ui] Début - lecture UI → modèle")

        # === Délai et menu caché ===
        default_value = self._get_default_choice()
        timeout_val = self._get_timeout_value()
        hidden_timeout = (
            bool(self.hidden_timeout_check.get_active()) if self.hidden_timeout_check is not None else False
        )
        logger.debug(f"[_read_model_from_ui] Timeout={timeout_val}s, Hidden={hidden_timeout}")

        # === Affichage ===
        gfxmode = (
            (self._dropdown_get_value(self.gfxmode_dropdown) or "").strip() if self.gfxmode_dropdown is not None else ""
        )
        gfxpayload = (
            (self._dropdown_get_value(self.gfxpayload_dropdown) or "").strip()
            if self.gfxpayload_dropdown is not None
            else ""
        )
        logger.debug(f"[_read_model_from_ui] Gfxmode={gfxmode}, Gfxpayload={gfxpayload}")

        # === Options booléennes ===
        disable_submenu = (
            bool(self.disable_submenu_check.get_active()) if self.disable_submenu_check is not None else False
        )
        disable_recovery = (
            bool(self.disable_recovery_check.get_active()) if self.disable_recovery_check is not None else False
        )
        disable_os_prober = (
            bool(self.disable_os_prober_check.get_active()) if self.disable_os_prober_check is not None else False
        )
        terminal_color = (
            bool(self.terminal_color_check.get_active()) if self.terminal_color_check is not None else False
        )
        logger.debug(
            f"[_read_model_from_ui] Options: submenu={disable_submenu}, recovery={disable_recovery}, os_prober={disable_os_prober}, terminal_color={terminal_color}"
        )

        # === Couleurs ===
        color_normal_fg = (
            (self._dropdown_get_value(self.color_normal_fg_dropdown) or "").strip()
            if self.color_normal_fg_dropdown is not None
            else ""
        )
        color_normal_bg = (
            (self._dropdown_get_value(self.color_normal_bg_dropdown) or "").strip()
            if self.color_normal_bg_dropdown is not None
            else ""
        )
        color_highlight_fg = (
            (self._dropdown_get_value(self.color_highlight_fg_dropdown) or "").strip()
            if self.color_highlight_fg_dropdown is not None
            else ""
        )
        color_highlight_bg = (
            (self._dropdown_get_value(self.color_highlight_bg_dropdown) or "").strip()
            if self.color_highlight_bg_dropdown is not None
            else ""
        )
        logger.debug(
            f"[_read_model_from_ui] Couleurs: normal={color_normal_fg}/{color_normal_bg}, highlight={color_highlight_fg}/{color_highlight_bg}"
        )

        model = GrubUiModel(
            timeout=timeout_val,
            default=default_value,
            # DEV: Redondance supprimée: si GRUB_DEFAULT=saved, on active automatiquement GRUB_SAVEDEFAULT.
            save_default=(default_value == "saved"),
            hidden_timeout=hidden_timeout,
            gfxmode=gfxmode,
            gfxpayload_linux=gfxpayload,
            color_normal_fg=color_normal_fg,
            color_normal_bg=color_normal_bg,
            color_highlight_fg=color_highlight_fg,
            color_highlight_bg=color_highlight_bg,
            disable_submenu=disable_submenu,
            disable_recovery=disable_recovery,
            disable_os_prober=disable_os_prober,
            terminal_color=terminal_color,
        )
        logger.success("[_read_model_from_ui] Modèle extrait avec succès")
        return model

    def create_ui(self):
        """Build main GTK4 window with all UI components and event handlers.

        Initializes the main window, creates notebook with tabs (General, Entries,
        Display, Backups), sets up action buttons (Save, Reload, Apply), and
        configures initial state from loaded GRUB configuration.
        """
        logger.debug("[create_ui] Début de la construction de l'interface")
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        self.set_child(main_box)

        # === Zone d'information (messages temporaires) ===
        self.info_revealer = Gtk.Revealer()
        self.info_revealer.set_reveal_child(False)

        info_frame = Gtk.Frame()
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.info_box.set_margin_top(8)
        self.info_box.set_margin_bottom(8)
        self.info_box.set_margin_start(10)
        self.info_box.set_margin_end(10)
        self.info_box.set_hexpand(True)

        self.info_label = Gtk.Label(xalign=0)
        self.info_label.set_wrap(True)
        self.info_label.set_hexpand(True)
        self.info_box.append(self.info_label)

        info_frame.set_child(self.info_box)
        self.info_revealer.set_child(info_frame)
        main_box.append(self.info_revealer)

        # === Notebook avec onglets ===
        logger.debug("[create_ui] Construction des onglets")
        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        main_box.append(notebook)

        # DEV: Chaque builder remplit les références de widgets déclarés dans __init__
        build_general_tab(self, notebook)
        build_entries_tab(self, notebook)
        build_display_tab(self, notebook)
        build_backups_tab(self, notebook)
        logger.debug("[create_ui] Onglets construits")

        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # === Boutons d'action ===
        logger.debug("[create_ui] Construction des boutons d'action")
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)
        main_box.append(button_box)

        self.reload_btn = Gtk.Button(label="Recharger")
        self.reload_btn.connect("clicked", self.on_reload)
        button_box.append(self.reload_btn)

        self.save_btn = Gtk.Button(label="Appliquer")
        self.save_btn.get_style_context().add_class("suggested-action")
        self.save_btn.connect("clicked", self.on_save)
        button_box.append(self.save_btn)

        self._apply_state(AppState.CLEAN)
        logger.success("[create_ui] Interface construite complètement")

    def _apply_state(self, state: AppState) -> None:
        self.state = state
        self.modified = state == AppState.DIRTY

        can_save = ((state == AppState.DIRTY) or self.entries_visibility_dirty) and (os.geteuid() == 0)
        busy = state == AppState.APPLYING

        self.save_btn.set_sensitive(can_save and not busy)
        self.reload_btn.set_sensitive(not busy)

    def _mark_dirty(self) -> None:
        if self.state != AppState.APPLYING:
            self._apply_state(AppState.DIRTY)

    def check_permissions(self):
        """Affiche un avertissement si l'application n'a pas les droits root."""
        uid = os.geteuid()
        logger.debug(f"[check_permissions] UID de l'utilisateur: {uid}")
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
            state = load_grub_ui_state()
            logger.debug(
                f"[load_config] Configuration chargée: timeout={state.model.timeout}, default={state.model.default}"
            )
            logger.debug(f"[load_config] Entrées GRUB disponibles: {len(state.entries)}")

            self.state_data = state
            self._apply_model_to_ui(state.model, state.entries)
            render_entries_view(self)
            self._apply_state(AppState.CLEAN)

            # === SÉCURITÉ: Avertir si des entrées sont masquées ===
            if self.hidden_entry_ids:
                logger.warning(
                    f"[load_config] {len(self.hidden_entry_ids)} entrée(s) masquée(s): {self.hidden_entry_ids}"
                )
                self.show_info(
                    f"ATTENTION: {len(self.hidden_entry_ids)} entrée(s) GRUB sont masquées. "
                    f"Allez dans l'onglet Entrées pour les gérer.",
                    WARNING,
                )

            # === Vérifier les droits de lecture sur grub.cfg ===
            if not state.entries and os.geteuid() != 0:
                logger.warning("[load_config] Entrées indisponibles: permissions insuffisantes sur grub.cfg")
                self.show_info(
                    "Entrées GRUB indisponibles: lecture de /boot/grub/grub.cfg refusée (droits). "
                    "Relancez l'application avec pkexec/sudo.",
                    WARNING,
                )
            elif not state.entries and os.geteuid() == 0:
                logger.warning("[load_config] Aucune entrée détectée dans grub.cfg")
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

    def on_modified(self, _widget, *_args):
        """Mark configuration as modified when any widget value changes.

        Prevents auto-reload of unchanged values. Sets modified flag to True
        to enable Save button.
        """
        if self._loading:
            logger.debug("[on_modified] Changement ignoré (chargement initial en cours)")
            return
        logger.debug("[on_modified] Widget changé - État: CLEAN → DIRTY")
        self._mark_dirty()

    def on_hidden_timeout_toggled(self, widget):
        """Toggle hidden timeout mode (GRUB_TIMEOUT_STYLE between hidden/menu).

        Shows/hides the delay indicator widget based on checkbox state.
        """
        is_active = widget.get_active()
        logger.debug(f"[on_hidden_timeout_toggled] Menu caché: {is_active}")
        if is_active:
            logger.debug("[on_hidden_timeout_toggled] Activation du menu caché → timeout = 0")
            self._sync_timeout_choices(0)
            self._set_timeout_value(0)
        self.on_modified(widget)

    def on_menu_options_toggled(self, widget):
        """Toggle visibility of advanced menu options.

        Shows/hides the submenu disable, recovery disable, and os-prober
        disable options based on checkbox state.
        """
        label = getattr(widget, "_option_name", "unknown")
        logger.debug(f"[on_menu_options_toggled] Option '{label}' = {widget.get_active()}")
        self.on_modified(widget)
        render_entries_view(self)

    def on_reload(self, _button):
        """Reload GRUB configuration from disk, discarding all UI changes.

        Re-reads /etc/default/grub and grub.cfg, updates all widgets to
        current disk state, and clears modified flag.
        """
        logger.info("[on_reload] Demande de recharge")
        if self.modified:
            logger.debug("[on_reload] Modifications en attente - demande confirmation")
            dialog = Gtk.AlertDialog()
            dialog.set_message("Modifications non enregistrées")
            dialog.set_detail("Voulez-vous vraiment recharger et perdre vos modifications ?")
            dialog.set_buttons(["Annuler", "Recharger"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(1)

            def _on_choice(dlg, result):
                try:
                    idx = dlg.choose_finish(result)
                except GLib.Error:
                    logger.debug("[on_reload] Recharge annulée par utilisateur")
                    return
                if idx == 1:
                    logger.info("[on_reload] Recharge confirmée")
                    self.load_config()
                    self.show_info("Configuration rechargée", INFO)

            dialog.choose(self, None, _on_choice)
            return

        logger.info("[on_reload] Recharge sans modifications")
        self.load_config()
        self.show_info("Configuration rechargée", INFO)

    def on_save(self, _button):
        """Validate UI values and save configuration using ApplyManager.

        Runs the complete save workflow: creates backup, validates configuration,
        applies changes, and handles rollback on errors. Shows result dialogs.
        """
        logger.info("[on_save] Demande de sauvegarde")
        if os.geteuid() != 0:
            logger.warning("[on_save] ERREUR: droits root nécessaires")
            self.show_info("Droits administrateur requis pour enregistrer", ERROR)
            return

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
            try:
                idx = dlg.choose_finish(result)
            except GLib.Error:
                logger.debug("[on_save] Sauvegarde annulée par utilisateur")
                return

            if idx == 1:  # Appliquer
                logger.info("[on_save] Sauvegarde confirmée")
                self._perform_save(apply_now=True)

        dialog.choose(self, None, _on_response)

    def _perform_save(self, apply_now: bool):
        """Execute save workflow in background thread using ApplyManager.

        Coordinates state machine transitions: backup → validate → apply →
        update-grub. Handles rollback on any error. Updates UI with progress.
        """
        logger.info("[_perform_save] Début du workflow de sauvegarde")
        logger.debug(f"[_perform_save] apply_now={apply_now}")
        self._apply_state(AppState.APPLYING)

        try:
            # === 1. Préparation de la configuration ===
            logger.debug("[_perform_save] Étape 1: Lecture modèle depuis UI")
            model = self._read_model_from_ui()
            logger.debug(f"[_perform_save] Modèle lu: default={model.default}, timeout={model.timeout}")

            # DEV: On fusionne avec la config brute existante pour ne pas perdre les clés inconnues
            logger.debug("[_perform_save] Étape 2: Fusion avec config existante")
            merged_config = merged_config_from_model(self.state_data.raw_config, model)
            logger.debug(f"[_perform_save] Config fusionnée: {len(merged_config)} clés")

            # === 2. Exécution via le Manager (9-state machine) ===
            logger.info("[_perform_save] Étape 3: Application via GrubApplyManager")
            manager = GrubApplyManager()
            result = manager.apply_configuration(merged_config, apply_changes=apply_now)
            logger.debug(f"[_perform_save] Résultat: success={result.success}, state={result.state.name}")

            if result.success:
                logger.success("[_perform_save] Workflow réussi")
                # Mise à jour de l'état interne
                self.state_data = GrubUiState(model=model, entries=self.state_data.entries, raw_config=merged_config)
                self._apply_state(AppState.CLEAN)

                msg = result.message
                msg_type = INFO

                # === 3. Gestion des entrées masquées (post-traitement sur grub.cfg) ===
                # DEV: On applique toujours si update-grub vient de tourner et qu'il y a des IDs à masquer.
                if apply_now:
                    if self.hidden_entry_ids:
                        logger.info(f"[_perform_save] Application du masquage: {len(self.hidden_entry_ids)} entrée(s)")
                        try:
                            used_path, masked = apply_hidden_entries_to_grub_cfg(self.hidden_entry_ids)
                            self.entries_visibility_dirty = False
                            logger.success(f"[_perform_save] Masquage appliqué: {masked} entrée(s) au {used_path}")
                            msg += f"\nEntrées masquées: {masked} ({used_path})"
                        except Exception as e:
                            logger.error(f"[_perform_save] ERREUR masquage: {e}")
                            msg += f"\nAttention: Masquage échoué: {e}"
                            msg_type = WARNING
                elif self.entries_visibility_dirty and not apply_now:
                    logger.debug("[_perform_save] Masquage non appliqué (update-grub ignoré)")
                    msg += "\n(Masquage non appliqué car update-grub ignoré)"

                self.show_info(msg, msg_type)
            else:
                # === Échec ===
                logger.error(f"[_perform_save] ERREUR: {result.message}")
                self._apply_state(AppState.DIRTY)
                self.show_info(f"Erreur: {result.message}", ERROR)
                if result.details:
                    logger.error(f"[_perform_save] Détails: {result.details}")

        except Exception as e:
            logger.exception("[_perform_save] ERREUR inattendue")
            self._apply_state(AppState.DIRTY)
            self.show_info(f"Erreur inattendue: {e}", ERROR)

    def show_info(self, message, msg_type):
        """Display temporary message in info area.

        DEV: Auto-hides after 5 seconds. CSS classes: info/warning/error.
        """
        logger.debug(f"[show_info] Message {msg_type}: {message[:60]}")
        self.info_label.set_text(message)

        ctx = self.info_box.get_style_context()
        # DEV: Retire les anciennes classes CSS avant d'en ajouter une nouvelle
        for klass in ("info", "warning", "error"):
            if ctx.has_class(klass):
                ctx.remove_class(klass)
        if msg_type in (INFO, WARNING, ERROR):
            ctx.add_class(msg_type)

        self.info_revealer.set_reveal_child(True)

        def _hide():
            logger.debug("[show_info] Masquage du message après 5s")
            self.info_revealer.set_reveal_child(False)
            return False

        GLib.timeout_add_seconds(5, _hide)
