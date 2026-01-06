"""Point d'entrée principal (production).

Ce lanceur configure le logging, demande une élévation unique via `pkexec` si
nécessaire, puis démarre l'application GTK.
"""

import os
import shutil
import sys
from pathlib import Path

from loguru import logger

from core.config.core_config_runtime import configure_logging, parse_verbosity_flags
from core.io.core_io_grub_default import ensure_initial_grub_default_backup

# Loguru installe un handler par défaut (niveau DEBUG) dès l'import.
# On le retire ici pour éviter des logs DEBUG en mode normal, avant l'appel
# explicite à configure_logging().
try:
    logger.remove()
except (TypeError, ValueError):
    pass


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

    if uid == 0:
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
        "PYTHONDONTWRITEBYTECODE=1",
        "GSETTINGS_BACKEND=memory",
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
    try:
        os.execv(pkexec, args)
    except OSError:
        # OSError est l'exception attendue si execv échoue (binaire introuvable,
        # permissions, etc.).
        print("Impossible d'obtenir les droits administrateur (pkexec a échoué).", file=sys.stderr)
        return


def _load_css(*, gtk, gdk, glib, css_path: Path) -> None:
    logger.debug("[main] Loading custom CSS stylesheet")
    css_provider = gtk.CssProvider()
    if not css_path.exists():
        logger.warning(f"[main] CSS file not found: {css_path}")
        return

    try:
        css_provider.load_from_path(str(css_path))
        gtk.StyleContext.add_provider_for_display(
            gdk.Display.get_default(),
            css_provider,
            gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        logger.success(f"[main] CSS loaded from {css_path}")
    except (glib.Error, OSError, ValueError) as exc:
        logger.error(f"[main] Failed to load CSS ({css_path}): {exc}")


def _run_gtk_app(*, remaining_argv: list[str]) -> int:
    # Pour éviter les avertissements dconf lors de l'exécution en root (pkexec/sudo),
    # on force l'utilisation du backend mémoire pour les paramètres GSettings.
    # Ceci doit être fait AVANT toute initialisation de GTK.
    os.environ["GSETTINGS_BACKEND"] = "memory"

    # Import tardif: évite d'importer GTK/PyGObject avant l'élévation pkexec.
    logger.debug("[main] Late-importing GTK and application modules")
    import gi  # pylint: disable=import-outside-toplevel

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import (  # pylint: disable=import-outside-toplevel
        Gdk,
        GLib,
        Gtk,
    )

    from ui.controllers.ui_controllers_manager import (  # pylint: disable=import-outside-toplevel
        GrubConfigManager,
    )

    css_path = Path(__file__).parent / "ui" / "config" / "style.css"
    _load_css(gtk=Gtk, gdk=Gdk, glib=GLib, css_path=css_path)

    logger.debug("[main] Creating GTK application instance")
    app = Gtk.Application(application_id="com.example.grub_manager")

    def _on_activate(application: Gtk.Application) -> None:
        logger.debug("[_on_activate] GTK activate signal received")
        logger.info("[_on_activate] Creating main window (GrubConfigManager)")
        win = GrubConfigManager(application)
        logger.debug("[_on_activate] Presenting main window to user")
        win.present()
        logger.success("[_on_activate] Main window displayed")

    app.connect("activate", _on_activate)
    logger.info("[main] Starting GTK application event loop")
    return int(app.run([sys.argv[0], *remaining_argv]))


def _run_main() -> int:
    """Exécute l'application et retourne un code de sortie."""
    debug, verbose, remaining_argv = parse_verbosity_flags(sys.argv[1:])

    # Élévation avant logging: évite un doublon de logs (process initial + root).
    _reexec_as_root_once()

    configure_logging(debug=debug, verbose=verbose)
    logger.debug("[main] Starting GRUB Manager application")
    logger.debug(f"[main] Debug mode: {debug}, verbose: {verbose}, remaining args: {remaining_argv}")
    logger.info("[main] Logging configured - application ready")
    logger.info("[main] Running as root - proceeding with initialization")

    # Au premier lancement, crée un backup "initial" si absent.
    # Best-effort: ne bloque pas l'UI si impossible.
    logger.debug("[main] Attempting to create initial backup")
    created_or_existing = ensure_initial_grub_default_backup()
    if created_or_existing:
        logger.success(f"[main] Initial backup available: {created_or_existing}")
    else:
        logger.warning("[main] Could not create or find initial backup")

    exit_code = _run_gtk_app(remaining_argv=remaining_argv)
    logger.info(f"[main] Application exited with code {exit_code}")
    return exit_code


def main() -> None:
    """Point d'entrée Python.

    Les tests (et certains usages) attendent que `main()` termine via SystemExit.
    """
    try:
        exit_code = _run_main()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(f"[main] Critical error during startup: {exc}")
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)


def _main_entry() -> int:
    try:
        return _run_main()
    except SystemExit as exc:
        return int(getattr(exc, "code", 1) or 0)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        logger.error(f"[main] Critical error during startup: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main_entry())
