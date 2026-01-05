# Développement (Grub_manager)

Ce document est orienté “dev”. Il décrit la structure, les points clés et comment travailler sur le repo.

## Démarrage rapide

Créer l’environnement et installer les dépendances :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Lancer l’app :

```bash
.venv/bin/python main.py
```

## Qualité et tests

Le script `run_quality.sh` regroupe les checks et accepte des chemins (fichiers/dossiers) pour cibler.

```bash
./run_quality.sh --lint core ui main.py
./run_quality.sh --fix core
./run_quality.sh --test
./run_quality.sh --test tests/core/theme/test_core_theme_generator.py
./run_quality.sh --cov tests/core/theme
```

Notes :

- `--fix/--lint` : les chemins filtrent ce qui est analysé.
- `--test/--cov` : si des chemins sont fournis, ils sont passés à pytest (sélection). Sans chemins, pytest lance toute la suite.

## Mini-audit AAA (humble)

Objectif : rester simple, testable, et avec des frontières claires.

- `core/` : logique métier, pas de dépendance à GTK et pas d’import depuis `ui/`.
- `ui/` : interface GTK, état et orchestration côté GUI.
- API explicites : éviter les couches “magiques” (délégation d’attributs) pour que les usages soient lisibles et testables.
- Qualité outillée : `ruff/isort/black/mypy/pylint/radon` + `pytest`.

Il y a beaucoup de surface (GUI + parsing + fichiers système). Le but est surtout d’avoir des contrats clairs et des tests utiles.

## Tree (main.py / core / ui) avec commentaires

Arborescence volontairement limitée à `main.py`, `core/` et `ui/`.

```text
main.py                                       # Point d’entrée : logging, élévation pkexec, init GTK, fenêtre principale

core/                                         # Logique métier (pas de GTK)
  __init__.py                                 # Package core
  core_exceptions.py                          # Exceptions du domaine GRUB
  config/                                     # Config/runtime (logging, paths, args)
    __init__.py                               # Package config
    core_logging_config.py                    # Configuration loguru/logging
    core_paths.py                             # Chemins importants (projet / système)
    core_runtime.py                           # Helpers runtime (ex: parse flags, init)
  io/                                         # I/O GRUB : lire/écrire/valider/parsing
    __init__.py                               # Package io
    core_grub_default_io.py                   # Lecture/écriture /etc/default/grub + backups
    core_grub_menu_parser.py                  # Parsing du menu GRUB (grub.cfg)
    grub_parsing_utils.py                     # Petites fonctions utilitaires de parsing
    grub_validation.py                        # Validation/cohérence des données parseées
  managers/                                   # Orchestration de changements et d’états
    __init__.py                               # Package managers
    apply_states.py                           # Modèle d’état d’application (pending/applied)
    core_apply_manager.py                     # Application des changements (écriture + commandes)
    core_entry_visibility_manager.py          # Masquage/affichage des entrées GRUB
  models/                                     # Modèles de données (UI model / thèmes)
    __init__.py                               # Package models
    core_grub_ui_model.py                     # Modèle agrégé manipulé par l’UI
    core_theme_models.py                      # Modèles liés aux thèmes
  services/                                   # Services “métier” (coordonnent I/O + managers)
    __init__.py                               # Package services
    core_grub_script_service.py               # Génération/gestion scripts appliqués à GRUB
    core_grub_service.py                      # Service principal GRUB
    core_maintenance_service.py               # Maintenance (nettoyage, vérifications)
    core_theme_service.py                     # Service thèmes (apply/génération)
  system/                                     # Commandes système / vérifs système
    __init__.py                               # Package system
    core_grub_system_commands.py              # Wrappers d’appels (update-grub, etc.)
    core_sync_checker.py                      # Détection de désynchronisation/état
  theme/                                      # Gestion des thèmes (actif + génération)
    __init__.py                               # Package theme
    core_active_theme_manager.py              # Détecte/applique le thème actif
    theme_generator/                          # Générateur de thèmes (modèles + templates)
      __init__.py                             # Package theme_generator
      core_theme_generator.py                 # Orchestration génération paquet thème
      core_theme_generator_enums.py           # Enums (résolutions, schémas couleurs)
      core_theme_generator_models.py          # Dataclasses de config (boot_menu/item/terminal/...)
      core_theme_generator_palettes.py        # Palettes de couleurs
      core_theme_generator_resolution.py      # Helpers de config selon résolution
      core_theme_generator_templates.py       # Génération des fichiers template/theme
      core_theme_generator_validation.py      # Validation des thèmes générés

ui/                                           # Interface GTK (widgets, contrôleurs, tabs)
  __init__.py                                 # Package ui
  style.css                                   # Style GTK (chargé au démarrage)
  ui_builder.py                               # Construction UI (widgets, layout)
  ui_constants.py                             # Constantes UI
  ui_dialogs.py                               # Dialogs génériques
  ui_exceptions.py                            # Exceptions UI
  ui_file_dialogs.py                          # Dialogs fichiers (ouvrir/enregistrer)
  ui_gtk_helpers.py                           # Helpers GTK (widgets, signaux)
  ui_gtk_imports.py                           # Imports GTK centralisés (tests/headless)
  ui_infobar_controller.py                    # InfoBar (messages, erreurs, succès)
  ui_manager.py                               # Fenêtre principale + orchestration UI
  ui_model_mapper.py                          # Mappe UI <-> modèle core
  ui_protocols.py                             # Protocols/typing pour contrats UI
  ui_state.py                                 # État UI (sélection, flags, etc.)
  ui_tab_policy.py                            # Règles d’accès/permissions par onglet
  ui_widgets.py                               # Widgets partagés (factory/helpers)
  ui_workflow_controller.py                   # Workflows (apply, backups, validations)
  components/                                 # Composants réutilisables (thèmes, listes, etc.)
    __init__.py                               # Package components
    ui_color_picker.py                        # Sélecteur de couleur
    ui_theme_components.py                    # Briques UI thème
    ui_theme_config_actions.py                # Actions/boutons liés à la config thème
    ui_theme_scripts_list.py                  # Liste des scripts d’un thème
    ui_theme_scripts_renderer.py              # Rendu scripts + état pending
    ui_theme_simple_config.py                 # Panneau config “simple” thème
    ui_theme_simple_config_logic.py           # Logique non-widget du panneau simple
  controllers/                                # Contrôleurs UI (ex: permissions)
    __init__.py                               # Package controllers
    permission_controller.py                  # Gestion droits (root, accès fichiers)
  dialogs/                                    # Fenêtres/dialogs spécialisés
    ui_interactive_theme_generator.py         # Générateur interactif (logique)
    ui_interactive_theme_generator_window.py  # Fenêtre GTK associée
    theme_editors/                            # Sous-éditeurs (layout/texte/visuel)
      base_editor.py                          # Base/contrat commun
      layout_editors.py                       # Éditeurs layout
      text_editors.py                         # Éditeurs texte
      visual_editors.py                       # Éditeurs visuels
  tabs/                                       # Onglets de l’application
    __init__.py                               # Package tabs
    ui_entries_renderer.py                    # Rendu liste des entrées GRUB
    ui_grub_preview_dialog.py                 # Prévisualisation du menu GRUB
    ui_tab_backups.py                         # Onglet sauvegardes/restauration
    ui_tab_display.py                         # Onglet affichage
    ui_tab_entries.py                         # Onglet entrées
    ui_tab_general.py                         # Onglet général
    ui_tab_maintenance.py                     # Onglet maintenance
    ui_tab_theme_config.py                    # Onglet configuration thème
    theme_config/                             # Handlers dédiés au thème
      __init__.py                             # Package theme_config
      ui_theme_config_handlers.py             # Handlers (signals/callbacks) config thème
```
