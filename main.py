"""Point d'entrée principal (production).

Ce lanceur configure le logging, demande une élévation unique via `pkexec` si
nécessaire, puis démarre l'application GTK.
"""

import os
import shutil
import sys
from pathlib import Path

from loguru import logger

from core.grub_default import ensure_initial_grub_default_backup
from core.runtime import configure_logging, parse_debug_flag


def _reexec_as_root_once() -> None:
    """Relance le processus via pkexec une seule fois si nécessaire.

    L'application doit pouvoir écrire `/etc/default/grub` et exécuter `update-grub`.
    Sur un environnement desktop, `pkexec` est utilisé pour obtenir un prompt
    graphique (PolicyKit).
    """
    # Cette application modifie /etc/default/grub et lance update-grub.
    # Cela requiert des droits administrateur. Plutôt que de demander un mot de passe
    # à chaque action, on (re)lance l'application UNE SEULE FOIS en root au démarrage.
    if os.geteuid() == 0:
        return

    if os.environ.get("GRUB_MANAGER_PKEXEC") == "1":
        # Si on revient ici avec ce flag, c'est que pkexec a été refusé ou a échoué.
        # On évite une boucle infinie de relance.
        print("Impossible d'obtenir les droits administrateur (pkexec a échoué).", file=sys.stderr)
        raise SystemExit(1)

    pkexec = shutil.which("pkexec")
    if not pkexec:
        # pkexec est fourni par PolicyKit. Sur desktop Linux c'est le chemin standard
        # pour demander une élévation de privilèges avec un prompt graphique.
        print(
            "Cette application nécessite les droits administrateur. "
            "Installez 'pkexec' (PolicyKit) ou lancez via sudo.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    env_kv: list[str] = [
        "GRUB_MANAGER_PKEXEC=1",
        "GIO_USE_PORTALS=0",
        "GTK_USE_PORTAL=0",
    ]

    # En root, l'accès au DBus de session de l'utilisateur est souvent impossible.
    # Désactiver les portals évite que GTK/GIO tente d'y accéder (sinon warning:
    # "Unable to acquire session bus").

    # On propage les variables nécessaires à l'affichage + session, pour éviter
    # des comportements bizarres selon l'environnement (X11/Wayland/DBus).
    for key in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
        "LANG",
        "LC_ALL",
    ):
        value = os.environ.get(key)
        if value:
            env_kv.append(f"{key}={value}")

    xauth = os.environ.get("XAUTHORITY")
    if not xauth:
        # Sur X11, root doit connaître le cookie X11 pour se connecter au serveur X.
        # Si XAUTHORITY n'est pas défini, on tente ~/.Xauthority.
        candidate = Path.home() / ".Xauthority"
        if candidate.exists():
            xauth = str(candidate)
    if xauth:
        env_kv.append(f"XAUTHORITY={xauth}")

    script_path = str(Path(__file__).resolve())
    # execv remplace le process courant : un seul prompt pkexec au lancement,
    # puis l'app tourne en root jusqu'à sa fermeture.
    args = [pkexec, "env", *env_kv, sys.executable, script_path, *sys.argv[1:]]
    os.execv(pkexec, args)


def main() -> None:
    """Point d'entrée applicatif."""
    debug, remaining_argv = parse_debug_flag(sys.argv[1:])
    configure_logging(debug=debug)

    # Garantit que l'application a les droits nécessaires dès le démarrage.
    _reexec_as_root_once()

    # Au premier lancement, crée un backup "initial" si absent.
    # Best-effort: ne bloque pas l'UI si impossible.
    created_or_existing = ensure_initial_grub_default_backup()
    if created_or_existing:
        logger.info("Backup initial disponible: {}", created_or_existing)

    # Import tardif: évite d'importer GTK/PyGObject avant l'élévation pkexec.
    import gi  # pylint: disable=import-outside-toplevel

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk  # pylint: disable=import-outside-toplevel

    from ui.app import GrubConfigManager  # pylint: disable=import-outside-toplevel

    app = Gtk.Application(application_id="com.example.grub_manager")

    def _on_activate(application: Gtk.Application) -> None:
        win = GrubConfigManager(application)
        win.present()

    app.connect("activate", _on_activate)
    raise SystemExit(int(app.run([sys.argv[0], *remaining_argv])))


if __name__ == "__main__":
    main()
