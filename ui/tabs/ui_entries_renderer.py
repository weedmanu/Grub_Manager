"""Manage GRUB boot menu entry display and visibility filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gi.repository import Gtk, Pango
from loguru import logger

from core.io.core_grub_menu_parser import GrubDefaultChoice, get_simulated_os_prober_entries
from core.managers.core_entry_visibility_manager import save_hidden_entry_ids
from ui.ui_widgets import clear_listbox

if TYPE_CHECKING:  # pragma: no cover - types only
    from ui.ui_manager import GrubConfigManager


@dataclass(frozen=True, slots=True)
class EntryFilters:
    """Filtres d'affichage des entrées GRUB."""

    hide_recovery: bool
    hide_os_prober: bool
    disable_submenu: bool
    hide_advanced: bool
    hide_memtest: bool


@dataclass(frozen=True, slots=True)
class EntryRowData:
    """Données nécessaires à la construction d'une ligne d'entrée."""

    index: int
    choice: GrubDefaultChoice
    title: str
    menu_id: str


def _entry_is_recovery(title: str) -> bool:
    """Detect if entry title is a recovery/repair mode."""
    t = (title or "").lower()
    return ("recovery" in t) or ("recup" in t)


def _entry_is_os_prober(choice: GrubDefaultChoice) -> bool:
    """Detect if entry is from os-prober source."""
    if choice.source == "30_os-prober":
        return True
    # Fallback for old entries without parsed source
    return choice.menu_id.startswith("osprober-")


def _entry_is_advanced_options(title: str) -> bool:
    """Detect if entry title belongs to GRUB 'Advanced options' submenu."""
    t = (title or "").lower()
    return ("advanced options" in t) or ("options avanc" in t)


def _entry_is_memtest(choice: GrubDefaultChoice) -> bool:
    """Detect if entry comes from memtest scripts."""
    t = (getattr(choice, "title", "") or "").lower()
    src = (getattr(choice, "source", "") or "").lower()
    return ("memtest" in t) or ("memtest" in src)


def _entry_display_title(title: str, disable_submenu: bool) -> str:
    """Format boot entry title for display in menu list.

    Extracts readable title, handles truncation and special boot mode formatting.
    """
    title_str = str(title or "").strip()
    if not title_str:
        return "(Untitled)"
    if disable_submenu and ">" in title_str:
        # When submenus are disabled, keep only the leaf entry title.
        # core_grub_menu_parser builds titles like: "Submenu title > Entry title".
        # Some older formats may use ">>".
        if ">>" in title_str:
            parts = [p.strip() for p in title_str.split(">>") if p.strip()]
        else:
            parts = [p.strip() for p in title_str.split(">") if p.strip()]
        if parts:
            return parts[-1]
    return title_str[:100]  # Truncate very long titles


def _read_entry_filters(controller: GrubConfigManager) -> EntryFilters:
    disable_recovery_check = getattr(controller, "disable_recovery_check", None)
    hide_recovery = bool(disable_recovery_check.get_active()) if disable_recovery_check is not None else False

    hide_os_prober = (
        bool(controller.disable_os_prober_check.get_active())
        if controller.disable_os_prober_check is not None
        else False
    )

    disable_submenu_check = getattr(controller, "disable_submenu_check", None)
    disable_submenu = bool(disable_submenu_check.get_active()) if disable_submenu_check is not None else False

    hide_advanced_check = getattr(controller, "hide_advanced_options_check", None)
    hide_advanced = bool(hide_advanced_check.get_active()) if hide_advanced_check is not None else False

    hide_memtest_check = getattr(controller, "hide_memtest_check", None)
    hide_memtest = bool(hide_memtest_check.get_active()) if hide_memtest_check is not None else False

    return EntryFilters(
        hide_recovery=hide_recovery,
        hide_os_prober=hide_os_prober,
        disable_submenu=disable_submenu,
        hide_advanced=hide_advanced,
        hide_memtest=hide_memtest,
    )


def _prepare_entries(state_entries: list[GrubDefaultChoice], *, hide_os_prober: bool) -> list[GrubDefaultChoice]:
    entries_to_show = list(state_entries)

    if hide_os_prober:
        return entries_to_show

    has_os_prober = any(_entry_is_os_prober(e) for e in entries_to_show)
    if has_os_prober:
        return entries_to_show

    logger.debug("[render_entries] Attempting to add simulated os-prober entries")
    simulated = get_simulated_os_prober_entries()
    if simulated:
        logger.debug(f"[render_entries] Added {len(simulated)} simulated os-prober entries")
        entries_to_show.extend(simulated)
    return entries_to_show


def _entry_is_filtered(
    choice: GrubDefaultChoice,
    *,
    title: str,
    filters: EntryFilters,
) -> bool:
    if filters.hide_recovery and _entry_is_recovery(title):
        return True
    if filters.hide_os_prober and _entry_is_os_prober(choice):
        return True
    if filters.hide_memtest and _entry_is_memtest(choice):
        return True
    if filters.hide_advanced and _entry_is_advanced_options(title):
        return True
    return False


def _apply_state_buttons(controller: GrubConfigManager) -> None:
    save_btn = getattr(controller, "save_btn", None)
    reload_btn = getattr(controller, "reload_btn", None)
    controller.state_manager.apply_state(controller.state_manager.state, save_btn, reload_btn)


def _configure_entry_switch(
    controller: GrubConfigManager,
    *,
    switch: Gtk.Switch,
    menu_id: str,
    is_simulated_os: bool,
) -> None:
    if not menu_id:
        switch.set_sensitive(False)
        switch.set_tooltip_text("Entry ID unavailable (masking not supported)")
        return

    if is_simulated_os:
        switch.set_sensitive(False)
        switch.set_tooltip_text("Entry detected (simulated). Apply to get real ID.")
        return

    is_hidden = menu_id in controller.state_manager.hidden_entry_ids
    switch.set_active(is_hidden)
    switch.set_tooltip_text("Hide this entry (apply via update-grub)")

    def _on_switch(_sw, _pspec, *, _mid=menu_id):
        active = bool(_sw.get_active())
        logger.info(f"[_on_switch] Entry ID={_mid} hidden={active}")
        if active:
            controller.state_manager.hidden_entry_ids.add(_mid)
        else:
            controller.state_manager.hidden_entry_ids.discard(_mid)

        save_hidden_entry_ids(controller.state_manager.hidden_entry_ids)
        controller.state_manager.entries_visibility_dirty = True
        _apply_state_buttons(controller)
        controller.show_info("Hide state saved. Apply with update-grub.", "info")

    switch.connect("notify::active", _on_switch)


def _build_entry_row(controller: GrubConfigManager, *, data: EntryRowData, filters: EntryFilters) -> Gtk.ListBoxRow:
    row = Gtk.ListBoxRow()
    row.set_selectable(True)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    hbox.set_margin_top(6)
    hbox.set_margin_bottom(6)
    hbox.set_margin_start(6)
    hbox.set_margin_end(6)

    num_label = Gtk.Label(label=str(data.index), xalign=0)
    num_label.set_width_chars(3)
    hbox.append(num_label)

    title_label = Gtk.Label(label=_entry_display_title(data.title, filters.disable_submenu), xalign=0)
    title_label.set_hexpand(True)
    title_label.set_ellipsize(Pango.EllipsizeMode.END)
    hbox.append(title_label)

    switch = Gtk.Switch()
    switch.set_valign(Gtk.Align.CENTER)

    is_simulated_os = data.choice.source == "30_os-prober" and data.menu_id.startswith("osprober-simulated")
    _configure_entry_switch(controller, switch=switch, menu_id=data.menu_id, is_simulated_os=is_simulated_os)
    hbox.append(switch)

    row.set_child(hbox)
    return row


def render_entries(controller: GrubConfigManager) -> None:
    """Populate Entries listbox with GRUB boot menu entries.

    Displays all available entries with visibility toggles. Filters out
    recovery/os-prober entries based on user settings. Handles entry
    selection and state persistence.
    """
    listbox = controller.entries_listbox
    if listbox is None:
        logger.warning("[render_entries] ListBox not initialized")
        return

    state = controller.state_manager.state_data
    wanted_id = (state.model.default or "").strip()

    filters = _read_entry_filters(controller)
    logger.debug(
        f"[render_entries] Filters: hide_recovery={filters.hide_recovery}, "
        f"hide_os_prober={filters.hide_os_prober}, disable_submenu={filters.disable_submenu}, "
        f"hide_advanced={filters.hide_advanced}, hide_memtest={filters.hide_memtest}"
    )

    clear_listbox(listbox)

    entries_to_show = _prepare_entries(list(state.entries), hide_os_prober=filters.hide_os_prober)

    logger.debug(f"[render_entries] Displaying {len(entries_to_show)} total entries")

    for i, choice in enumerate(entries_to_show):
        title = str(getattr(choice, "title", "") or "")
        menu_id = (getattr(choice, "menu_id", "") or "").strip()

        if _entry_is_filtered(
            choice,
            title=title,
            filters=filters,
        ):
            continue

        data = EntryRowData(index=i, choice=choice, title=title, menu_id=menu_id)
        row = _build_entry_row(controller, data=data, filters=filters)
        listbox.append(row)

        if wanted_id and choice.id == wanted_id:
            listbox.select_row(row)
            logger.debug(f"[render_entries] Entry #{i} selected (default={wanted_id})")

    logger.success("[render_entries] Rendering complete")
