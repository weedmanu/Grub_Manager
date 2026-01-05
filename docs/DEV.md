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
- `ui/` : interface GTK, état et orchestration côté GUI. **Organisation modulaire SOLID** :
  - `builders/` : construction UI (widgets, layout)
  - `components/` : composants réutilisables
  - `config/` : constantes et styles
  - `controllers/` : orchestration et workflows
  - `dialogs/` : fenêtres spécialisées
  - `helpers/` : utilitaires GTK
  - `models/` : état et protocoles UI
  - `tabs/` : onglets de l'application
- API explicites : éviter les couches "magiques" (délégation d'attributs) pour que les usages soient lisibles et testables.
- Qualité outillée : `ruff/isort/black/mypy/pylint/radon` + `pytest`.
- **Score qualité** : 10/10 Pylint, 0 duplication, complexité Radon : 506 fonctions A, 79 B, 14 C (aucune D/E/F).

Il y a beaucoup de surface (GUI + parsing + fichiers système). Le but est surtout d’avoir des contrats clairs et des tests utiles.

## Tree (main.py / core / ui) avec commentaires


Arborescence volontairement limitée à `main.py`, `core/` et `ui/`.

```text
main.py                                       # Point d’entrée : logging, élévation pkexec, init GTK, fenêtre principale

core/                                         # Logique métier (pas de GTK)
  __init__.py                                 # Package core
  core_exceptions.py                          # Exceptions du domaine GRUB
  config/                                     # Config/runtime (logging, paths, args)
    __init__.py
    core_config_logging.py                    # Configuration loguru/logging
    core_config_paths.py                      # Chemins importants (projet / système)
    core_config_runtime.py                    # Helpers runtime (ex: parse flags, init)
  io/                                         # I/O GRUB : lire/écrire/valider/parsing
    __init__.py
    core_io_grub_default.py                   # Lecture/écriture /etc/default/grub + backups
    core_io_grub_menu_parser.py               # Parsing du menu GRUB (grub.cfg)
    core_io_grub_parsing_utils.py             # Utilitaires de parsing
    core_io_grub_validation.py                # Validation/cohérence des données parsées
  managers/                                   # Orchestration de changements et d’états
    __init__.py
    core_managers_apply.py                    # Application des changements (écriture + commandes)
    core_managers_apply_states.py             # Modèle d’état d’application (pending/applied)
    core_managers_entry_visibility.py         # Masquage/affichage des entrées GRUB
  models/                                     # Modèles de données (UI model / thèmes)
    __init__.py
    core_models_grub_ui.py                    # Modèle agrégé manipulé par l’UI
    core_models_theme.py                      # Modèles liés aux thèmes
  services/                                   # Services “métier” (coordonnent I/O + managers)
    __init__.py
    core_services_grub.py                     # Service principal GRUB
    core_services_grub_script.py              # Génération/gestion scripts appliqués à GRUB
    core_services_maintenance.py              # Maintenance (nettoyage, vérifications)
    core_services_theme.py                    # Service thèmes (apply/génération)
  system/                                     # Commandes système / vérifs système
    __init__.py
    core_system_grub_commands.py              # Wrappers d’appels (update-grub, etc.)
    core_system_sync_checker.py               # Détection de désynchronisation/état
  theme/                                      # Gestion des thèmes (actif + génération)
    __init__.py
    core_theme_active_manager.py              # Détecte/applique le thème actif
    generator/                                # Génération de thèmes (modèles + templates)
      __init__.py
      core_theme_generator.py                 # Façade/Orchestration génération thème
      core_theme_generator_enums.py           # Enums (résolutions, schémas couleurs)
      core_theme_generator_models.py          # Dataclasses de config (boot_menu/item/terminal/...)
      core_theme_generator_palettes.py        # Palettes de couleurs
      core_theme_generator_resolution.py      # Helpers de config selon résolution
      core_theme_generator_templates.py       # Génération des templates / theme.txt
      core_theme_generator_validation.py      # Validation des thèmes générés

ui/                                           # Interface GTK (organisation modulaire SOLID)
  __init__.py                                 # Package ui
  ui_exceptions.py                            # Exceptions UI
  builders/                                   # Construction UI (widgets, layout)
    __init__.py
    ui_builders_index.py                      # Construction UI principale (tabs, notebook)
    ui_builders_widgets.py                    # Widgets partagés (factory/helpers)
  components/                                 # Composants réutilisables
    __init__.py
    ui_components_color_picker.py
    ui_components_theme.py
    ui_components_theme_config_actions.py
    ui_components_theme_scripts_list.py
    ui_components_theme_scripts_renderer.py
    ui_components_theme_simple_config.py
    ui_components_theme_simple_config_logic.py
  config/                                     # Configuration UI (constantes, styles)
    __init__.py
    ui_config_constants.py
    style.css
  controllers/                                # Orchestration et workflows
    __init__.py
    ui_controllers_infobar.py
    ui_controllers_manager.py
    ui_controllers_permission.py
    ui_controllers_tab_policy.py
    ui_controllers_workflow.py
  dialogs/                                    # Dialogs GTK
    ui_dialogs_index.py
    ui_dialogs_file.py
    ui_dialogs_grub_preview.py
    ui_dialogs_interactive_theme_generator.py
    ui_dialogs_interactive_theme_generator_window.py
    preview/
      __init__.py
      ui_dialogs_preview_grub_css.py
      ui_dialogs_preview_grub_data.py
      ui_dialogs_preview_grub_parsers.py
      ui_dialogs_preview_grub_renderer.py
    theme_editors/
      ui_dialogs_theme_editors_base.py
      ui_dialogs_theme_editors_layout.py
      ui_dialogs_theme_editors_text.py
      ui_dialogs_theme_editors_visual.py
  helpers/                                    # Helpers et utilitaires GTK
    __init__.py
    ui_helpers_gtk.py
    ui_helpers_gtk_imports.py
    ui_helpers_model_mapper.py
  models/                                     # Modèles UI (état, protocoles)
    __init__.py
    ui_models_protocols.py
    ui_models_state.py
  tabs/                                       # Onglets
    __init__.py
    ui_tabs_entries_renderer.py
    ui_tabs_backups.py
    ui_tabs_display.py
    ui_tabs_entries.py
    ui_tabs_general.py
    ui_tabs_maintenance.py
    ui_tabs_theme_config.py
    theme_config/
      __init__.py
      ui_tabs_theme_config_handlers.py
```
