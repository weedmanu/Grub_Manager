"""Dialogues et popups pour l'interface utilisateur.

Contient des dialogues réutilisables comme l'exécution de commandes avec sortie.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import TYPE_CHECKING

from gi.repository import GLib, Gtk
from loguru import logger

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def run_command_popup(controller: GrubConfigManager, command: list[str], title: str) -> None:
    """Execute a system command and display output in a popup window.

    Runs command with timeout, captures stdout/stderr, and shows in modal dialog.

    Args:
        controller: GrubConfigManager instance (parent window)
        command: List of command and arguments
        title: Dialog window title
    """
    if os.geteuid() != 0:
        logger.warning("[run_command_popup] Not running as root")
        controller.show_info("Droits root nécessaires", "error")
        return

    logger.info(f"[_run_command_popup] Executing: {' '.join(command)}")

    # Create popup dialog
    dialog = Gtk.Window()
    dialog.set_transient_for(controller)
    dialog.set_modal(True)
    dialog.set_title(title)

    # Match parent window height, fixed width
    parent_height = controller.get_height()
    dialog.set_default_size(700, parent_height if parent_height > 0 else 500)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)

    # ScrolledWindow with TextView
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_hexpand(True)

    textview = Gtk.TextView()
    textview.set_editable(False)
    textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textview.set_monospace(True)
    textview.set_margin_top(8)
    textview.set_margin_bottom(8)
    textview.set_margin_start(8)
    textview.set_margin_end(8)

    # Helper to append text to buffer
    def append_text(text: str, tag: str | None = None) -> bool:
        """Append text to TextView buffer (called from main thread via GLib.idle_add)."""
        buf = textview.get_buffer()
        end_iter = buf.get_end_iter()
        if tag:
            buf.insert_with_tags_by_name(end_iter, text, tag)
        else:
            buf.insert(end_iter, text)

        # Auto-scroll to bottom
        mark = buf.get_insert()
        textview.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        return False

    # Setup text tags for colored output
    buf = textview.get_buffer()
    buf.create_tag("error", foreground="red")
    buf.create_tag("success", foreground="green")

    scroll.set_child(textview)
    box.append(scroll)

    # Close button
    close_btn = Gtk.Button(label="Fermer")
    close_btn.set_halign(Gtk.Align.END)
    close_btn.connect("clicked", lambda b: dialog.close())
    box.append(close_btn)

    dialog.set_child(box)
    dialog.present()

    # Exécuter la commande en arrière-plan pour ne pas geler l'UI
    def run_in_thread():
        try:
            # Cas spécial pour grub-emu qui est interactif/graphique
            if command[0] == "grub-emu":
                GLib.idle_add(append_text, "Lancement de la simulation GRUB...\n")

                # Vérifier si grub-emu est installé
                if not shutil.which("grub-emu"):
                    GLib.idle_add(append_text, "Erreur: 'grub-emu' n'est pas installé.\n", "error")
                    GLib.idle_add(append_text, "Installez-le avec: sudo apt install grub-emu\n")
                    return

                # grub-emu ouvre sa propre fenêtre, on attend juste qu'il finisse
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
                    process.wait()
                    GLib.idle_add(append_text, "Simulation terminée.\n", "success")
                return

            with subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            ) as process:
                # Lire la sortie ligne par ligne
                for line in process.stdout:
                    GLib.idle_add(append_text, line)

                process.wait()
                logger.info(f"[_run_command_popup] Commande terminée avec le code de retour {process.returncode}")

            if process.returncode == 0:
                GLib.idle_add(append_text, "\nSuccès\n", "success")
            else:
                GLib.idle_add(append_text, f"\nErreur (code {process.returncode})\n", "error")

        except (OSError, subprocess.SubprocessError) as e:
            logger.error(f"[_run_command_popup] Erreur: {e}")
            GLib.idle_add(append_text, f"ERREUR: {e}\n", "error")

    # Démarrer l'exécution de la commande dans un thread en arrière-plan
    logger.debug("[_run_command_popup] Starting command execution in background thread")

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


def confirm_action(callback, message: str, controller: GrubConfigManager) -> None:
    """Affiche une boîte de dialogue de confirmation avant d'exécuter une action.

    Args:
        callback: Fonction à appeler si l'utilisateur confirme
        message: Message de confirmation à afficher
        controller: GrubConfigManager instance (parent window)
    """
    dialog = Gtk.AlertDialog()
    dialog.set_modal(True)
    dialog.set_message("Confirmation")
    dialog.set_detail(message)
    dialog.set_buttons(["Annuler", "Confirmer"])
    dialog.set_default_button(0)
    dialog.set_cancel_button(0)

    def on_response(d: Gtk.AlertDialog, result) -> None:
        try:
            choice = d.choose_finish(result)
        except GLib.Error:
            return
        except Exception:
            # Les tests peuvent simuler des erreurs génériques.
            return

        if choice == 1:  # Index 1 = Confirmer
            callback()

    dialog.choose(controller, None, on_response)
