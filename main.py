"""Point d'entrée principal (production).

Ce lanceur configure le logging, demande une élévation unique via `pkexec` si
nécessaire, puis démarre l'application GTK.
"""

import os
import shutil
import sys
from pathlib import Path

from loguru import logger

from core.config.core_runtime import configure_logging, parse_debug_flag
from core.io.core_grub_default_io import ensure_initial_grub_default_backup


def _reexec_as_root_once() -> None:
    """Relance le processus via pkexec une seule fois si nécessaire.

    L'application doit pouvoir écrire `/etc/default/grub` et exécuter `update-grub`.
    Sur un environnement desktop, `pkexec` est utilisé pour obtenir un prompt
    graphique (PolicyKit).
    """
    # Cette application modifie /etc/default/grub et lance update-grub.
    # Cela requiert des droits administrateur. Plutôt que de demander un mot de passe
    # à chaque action, on (re)lance l'application UNE SEULE FOIS en root au démarrage.
    uid = os.geteuid()
    logger.debug(f"[_reexec_as_root_once] Current UID: {uid}")

    if uid == 0:
        logger.debug("[_reexec_as_root_once] Already running as root, skipping pkexec")
        return

    if os.environ.get("GRUB_MANAGER_PKEXEC") == "1":
        # Si on revient ici avec ce flag, c'est que pkexec a été refusé ou a échoué.
        # On évite une boucle infinie de relance.
        logger.error("[_reexec_as_root_once] pkexec failed or was denied - aborting")
        print("Impossible d'obtenir les droits administrateur (pkexec a échoué).", file=sys.stderr)
        raise SystemExit(1)

    pkexec = shutil.which("pkexec")
    if not pkexec:
        logger.error("[_reexec_as_root_once] pkexec not found in PATH")
        # pkexec est fourni par PolicyKit. Sur desktop Linux c'est le chemin standard
        # pour demander une élévation de privilèges avec un prompt graphique.
        print(
            "Cette application nécessite les droits administrateur. "
            "Installez 'pkexec' (PolicyKit) ou lancez via sudo.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    logger.info("[_reexec_as_root_once] Relaunching via pkexec for root elevation")

    env_kv: list[str] = [
        "GRUB_MANAGER_PKEXEC=1",
        "GIO_USE_PORTALS=0",
        "GTK_USE_PORTAL=0",
        "PYTHONDONTWRITEBYTECODE=1",
    ]
    logger.debug(f"[_reexec_as_root_once] Initial env vars: {env_kv}")

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
            logger.debug(f"[_reexec_as_root_once] Propagating {key}")

    xauth = os.environ.get("XAUTHORITY")
    if not xauth:
        # Sur X11, root doit connaître le cookie X11 pour se connecter au serveur X.
        # Si XAUTHORITY n'est pas défini, on tente ~/.Xauthority.
        candidate = Path.home() / ".Xauthority"
        if candidate.exists():
            xauth = str(candidate)
            logger.debug(f"[_reexec_as_root_once] Found XAUTHORITY: {xauth}")
    if xauth:
        env_kv.append(f"XAUTHORITY={xauth}")
        logger.debug("[_reexec_as_root_once] Added XAUTHORITY to env")

    script_path = str(Path(__file__).resolve())
    logger.debug(f"[_reexec_as_root_once] Script path: {script_path}")
    logger.debug(f"[_reexec_as_root_once] Total env vars: {len(env_kv)}")

    # execv remplace le process courant : un seul prompt pkexec au lancement,
    # puis l'app tourne en root jusqu'à sa fermeture.
    args = [pkexec, "env", *env_kv, sys.executable, script_path, *sys.argv[1:]]
    logger.debug(f"[_reexec_as_root_once] Executing: {' '.join(args[:5])}... (total {len(args)} args)")
    try:
        os.execv(pkexec, args)
    except Exception as e:
        logger.error(f"[_reexec_as_root_once] Failed to re-exec: {e}")


def main() -> None:
    """Point d'entrée applicatif.

    Workflow:
    1. Parse command-line arguments (--debug flag)
    2. Configure logging based on debug mode
    3. Request root elevation via pkexec if needed
    4. Create initial backup of /etc/default/grub
    5. Initialize GTK4 application and show main window
    """
    logger.debug("[main] Starting GRUB Manager application")

    try:
        debug, remaining_argv = parse_debug_flag(sys.argv[1:])
        logger.debug(f"[main] Debug mode: {debug}, remaining args: {remaining_argv}")

        configure_logging(debug=debug)
        logger.info("[main] Logging configured - application ready")

        # Garantit que l'application a les droits nécessaires dès le démarrage.
        logger.debug("[main] Checking root elevation requirements")
        _reexec_as_root_once()
        logger.info("[main] Running as root - proceeding with initialization")

        # Au premier lancement, crée un backup "initial" si absent.
        # Best-effort: ne bloque pas l'UI si impossible.
        logger.debug("[main] Attempting to create initial backup")
        created_or_existing = ensure_initial_grub_default_backup()
        if created_or_existing:
            logger.success(f"[main] Initial backup available: {created_or_existing}")
        else:
            logger.warning("[main] Could not create or find initial backup")

        # Import tardif: évite d'importer GTK/PyGObject avant l'élévation pkexec.
        logger.debug("[main] Late-importing GTK and application modules")
        import gi  # pylint: disable=import-outside-toplevel

        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gtk  # pylint: disable=import-outside-toplevel

        from ui.ui_manager import GrubConfigManager  # pylint: disable=import-outside-toplevel

        # Charger le CSS personnalisé
        logger.debug("[main] Loading custom CSS stylesheet")
        css_provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "ui" / "style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            logger.success(f"[main] CSS loaded from {css_path}")
        else:
            logger.warning(f"[main] CSS file not found: {css_path}")

        logger.debug("[main] Creating GTK application instance")
        app = Gtk.Application(application_id="com.example.grub_manager")

        def _on_activate(application: Gtk.Application) -> None:
            """GTK activation callback - creates and shows main window."""
            logger.debug("[_on_activate] GTK activate signal received")
            logger.info("[_on_activate] Creating main window (GrubConfigManager)")
            win = GrubConfigManager(application)
            logger.debug("[_on_activate] Presenting main window to user")
            win.present()
            logger.success("[_on_activate] Main window displayed")

        app.connect("activate", _on_activate)
        logger.info("[main] Starting GTK application event loop")
        exit_code = int(app.run([sys.argv[0], *remaining_argv]))
        logger.info(f"[main] Application exited with code {exit_code}")
        raise SystemExit(exit_code)
    except Exception as e:
        logger.error(f"[main] Critical error during startup: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
