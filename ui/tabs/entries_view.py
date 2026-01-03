"""Manage GRUB boot menu entry display and visibility filtering."""

# pylint: disable=too-many-statements

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk, Pango
from loguru import logger

from core.entry_visibility import save_hidden_entry_ids
from core.grub_menu import GrubDefaultChoice, get_simulated_os_prober_entries
from ui.tabs.widgets import clear_listbox

if TYPE_CHECKING:  # pragma: no cover - types only
    from ui.app import GrubConfigManager


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


def _entry_display_title(title: str, disable_submenu: bool) -> str:
    """Format boot entry title for display in menu list.

    Extracts readable title, handles truncation and special boot mode formatting.
    """
    title_str = str(title or "").strip()
    if not title_str:
        return "(Untitled)"
    if disable_submenu and ">>" in title_str:
        # Remove submenu marker when submenus are disabled
        return title_str.split(">>", maxsplit=1)[0].strip()
    return title_str[:100]  # Truncate very long titles


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

    state = controller.state_data
    wanted_id = (state.model.default or "").strip()

    hide_recovery = (
        bool(controller.disable_recovery_check.get_active()) if controller.disable_recovery_check is not None else False
    )
    hide_os_prober = (
        bool(controller.disable_os_prober_check.get_active())
        if controller.disable_os_prober_check is not None
        else False
    )
    disable_submenu = (
        bool(controller.disable_submenu_check.get_active()) if controller.disable_submenu_check is not None else False
    )
    logger.debug(
        f"[render_entries] Filters: hide_recovery={hide_recovery}, "
        f"hide_os_prober={hide_os_prober}, disable_submenu={disable_submenu}"
    )

    clear_listbox(listbox)

    # === Prepare entries list ===
    entries_to_show = list(state.entries)

    # If os-prober enabled, check for missing entries and simulate
    if not hide_os_prober:
        has_os_prober = any(_entry_is_os_prober(e) for e in entries_to_show)
        if not has_os_prober:
            logger.debug("[render_entries] Attempting to add simulated os-prober entries")
            simulated = get_simulated_os_prober_entries()
            if simulated:
                logger.debug(f"[render_entries] Added {len(simulated)} simulated os-prober entries")
                entries_to_show.extend(simulated)

    logger.debug(f"[render_entries] Displaying {len(entries_to_show)} total entries")

    for i, choice in enumerate(entries_to_show):
        title = str(getattr(choice, "title", "") or "")
        menu_id = (getattr(choice, "menu_id", "") or "").strip()

        if hide_recovery and _entry_is_recovery(title):
            logger.debug(f"[render_entries] Entry #{i} filtered (recovery): {title[:30]}")
            continue
        if hide_os_prober and _entry_is_os_prober(choice):
            logger.debug(f"[render_entries] Entry #{i} filtered (os-prober): {title[:30]}")
            continue

        row = Gtk.ListBoxRow()
        row.set_selectable(True)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        hbox.set_margin_start(6)
        hbox.set_margin_end(6)

        num_label = Gtk.Label(label=str(i), xalign=0)
        num_label.set_width_chars(3)
        hbox.append(num_label)

        title_label = Gtk.Label(label=_entry_display_title(title, disable_submenu), xalign=0)
        title_label.set_hexpand(True)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        hbox.append(title_label)

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)

        is_simulated_os = choice.source == "30_os-prober" and menu_id.startswith("osprober-simulated")

        if not menu_id:
            logger.debug(f"[render_entries] Entry #{i} no ID - masking disabled")
            switch.set_sensitive(False)
            switch.set_tooltip_text("Entry ID unavailable (masking not supported)")
        elif is_simulated_os:
            logger.debug(f"[render_entries] Entry #{i} simulated - masking disabled (apply required)")
            switch.set_sensitive(False)
            switch.set_tooltip_text("Entry detected (simulated). Apply to get real ID.")
        else:
            is_hidden = menu_id in controller.hidden_entry_ids
            logger.debug(f"[render_entries] Entry #{i} [ID={menu_id}] hidden={is_hidden}: {title[:30]}")
            switch.set_active(is_hidden)
            switch.set_tooltip_text("Hide this entry (apply via update-grub)")

            def _on_switch(_sw, _pspec, *, _mid=menu_id):
                """Handle entry visibility toggle."""
                active = bool(_sw.get_active())
                logger.info(f"[_on_switch] Entry ID={_mid} hidden={active}")
                if active:
                    controller.hidden_entry_ids.add(_mid)
                    logger.debug("[_on_switch] Entry added to hidden_entry_ids")
                else:
                    controller.hidden_entry_ids.discard(_mid)
                    logger.debug("[_on_switch] Entry removed from hidden_entry_ids")
                save_hidden_entry_ids(controller.hidden_entry_ids)
                controller.entries_visibility_dirty = True
                controller._apply_state(controller.state)  # pylint: disable=protected-access
                controller.show_info("Hide state saved. Apply with update-grub.", "info")

            switch.connect("notify::active", _on_switch)

        hbox.append(switch)

        row.set_child(hbox)
        listbox.append(row)

        if wanted_id and choice.id == wanted_id:
            listbox.select_row(row)
            logger.debug(f"[render_entries] Entry #{i} selected (default={wanted_id})")

    logger.success("[render_entries] Rendering complete")
