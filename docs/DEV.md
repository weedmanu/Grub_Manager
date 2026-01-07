# Documentation Technique

Ce document présente l'architecture et les directives de développement pour le projet Grub Manager.

## Architecture

L'application suit une séparation stricte entre la logique métier et l'interface utilisateur.

- **`core/`** : Contient toute la logique métier, les accès système et la gestion de configuration. Ce module ne dépend d'aucune bibliothèque graphique.
- **`ui/`** : Contient l'interface utilisateur basée sur GTK4. Elle orchestre les interactions et relaie les actions vers le `core`.

### Arborescence du Projet

```text
.
├── core/
│   ├── config/
│   │   ├── core_config_logging.py
│   │   ├── core_config_paths.py
│   │   ├── core_config_runtime.py
│   │   └── __init__.py
│   ├── core_exceptions.py
│   ├── __init__.py
│   ├── io/
│   │   ├── core_io_grub_default.py
│   │   ├── core_io_grub_menu_parser.py
│   │   ├── core_io_grub_parsing_utils.py
│   │   ├── core_io_grub_validation.py
│   │   └── __init__.py
│   ├── managers/
│   │   ├── core_managers_apply.py
│   │   ├── core_managers_apply_states.py
│   │   ├── core_managers_entry_visibility.py
│   │   ├── core_managers_protocol.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── core_models_grub_ui.py
│   │   ├── core_models_theme.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── core_services_grub.py
│   │   ├── core_services_grub_script.py
│   │   ├── core_services_maintenance.py
│   │   ├── core_services_qemu_preview.py
│   │   ├── core_services_theme.py
│   │   └── __init__.py
│   ├── system/
│   │   ├── core_system_grub_commands.py
│   │   ├── core_system_sync_checker.py
│   │   └── __init__.py
│   └── theme/
│       ├── core_theme_active_manager.py
│       ├── generator/
│       │   ├── core_theme_generator_enums.py
│       │   ├── core_theme_generator_models.py
│       │   ├── core_theme_generator_palettes.py
│       │   ├── core_theme_generator.py
│       │   ├── core_theme_generator_resolution.py
│       │   ├── core_theme_generator_templates.py
│       │   ├── core_theme_generator_validation.py
│       │   └── __init__.py
│       └── __init__.py
├── ui/
│   ├── builders/
│   │   ├── __init__.py
│   │   ├── ui_builders_index.py
│   │   └── ui_builders_widgets.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── ui_components_color_picker.py
│   │   ├── ui_components_theme_config_actions.py
│   │   ├── ui_components_theme.py
│   │   ├── ui_components_theme_scripts_list.py
│   │   ├── ui_components_theme_scripts_renderer.py
│   │   ├── ui_components_theme_simple_config_logic.py
│   │   └── ui_components_theme_simple_config.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── style.css
│   │   └── ui_config_constants.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── ui_controllers_infobar.py
│   │   ├── ui_controllers_manager.py
│   │   ├── ui_controllers_permission.py
│   │   ├── ui_controllers_tab_policy.py
│   │   └── ui_controllers_workflow.py
│   ├── dialogs/
│   │   ├── preview/
│   │   │   ├── __init__.py
│   │   │   ├── ui_dialogs_preview_grub_css.py
│   │   │   ├── ui_dialogs_preview_grub_data.py
│   │   │   ├── ui_dialogs_preview_grub_parsers.py
│   │   │   └── ui_dialogs_preview_grub_renderer.py
│   │   ├── theme_editors/
│   │   │   ├── ui_dialogs_theme_editors_base.py
│   │   │   ├── ui_dialogs_theme_editors_layout.py
│   │   │   ├── ui_dialogs_theme_editors_text.py
│   │   │   └── ui_dialogs_theme_editors_visual.py
│   │   ├── ui_dialogs_file.py
│   │   ├── ui_dialogs_index.py
│   │   ├── ui_dialogs_interactive_theme_generator.py
│   │   ├── ui_dialogs_interactive_theme_generator_window.py
│   │   └── ui_dialogs_theme_preview.py
│   ├── helpers/
│   │   ├── __init__.py
│   │   ├── ui_helpers_gtk_imports.py
│   │   ├── ui_helpers_gtk.py
│   │   └── ui_helpers_model_mapper.py
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ui_models_protocols.py
│   │   └── ui_models_state.py
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── theme_config/
│   │   │   ├── __init__.py
│   │   │   └── ui_tabs_theme_config_handlers.py
│   │   ├── ui_tabs_backups.py
│   │   ├── ui_tabs_display.py
│   │   ├── ui_tabs_entries.py
│   │   ├── ui_tabs_entries_renderer.py
│   │   ├── ui_tabs_general.py
│   │   ├── ui_tabs_maintenance.py
│   │   └── ui_tabs_theme_config.py
│   └── ui_exceptions.py
├── docs/
├── tests/
├── main.py
├── pyproject.toml
├── requirements.txt
└── run_quality.sh
```

### Principes (pratiques)

- **`core/` ne dépend pas de GTK**: il doit rester testable en isolation.
- **`ui/` orchestre**: appels vers le `core`, threads pour ne pas bloquer GTK, affichage d'erreurs/messages.
- **Exceptions**: le `core` lève des exceptions métier; l'UI les transforme en feedback utilisateur.
- **Threading UI**: quand une action part en thread, les mises à jour UI repassent par `GLib.idle_add`.

### Preview GRUB (QEMU)

La preview du menu GRUB est implémentée comme suit :

- **Core** : [core/services/core_services_qemu_preview.py](../core/services/core_services_qemu_preview.py)
  - Génère un ISO bootable GRUB via `grub-mkrescue`.
  - Supporte un mode "mirror" (sanitise + wrapper) et un mode "safe" (menu non bootable).
  - Lance QEMU en **UEFI** (OVMF) quand c'est pertinent.
  - Nettoie automatiquement les ressources temporaires (ex: copie OVMF_VARS) quand QEMU se ferme.
- **UI** : [ui/controllers/ui_controllers_manager.py](../ui/controllers/ui_controllers_manager.py)
  - Lance la preview dans un thread pour ne pas bloquer l'UI.
  - Empêche les previews multiples.
  - Termine QEMU si l'application est fermée alors qu'une preview est encore ouverte.

Note: sur un lancement via pkexec (root), le service tente de lancer QEMU en tant qu'utilisateur d'origine (`PKEXEC_UID`/`SUDO_UID`) pour éviter des soucis de permissions et d'affichage.

## Standards de Qualité

Le projet vise un niveau de qualité élevé pour garantir la stabilité et la maintenabilité.

### Bonnes Pratiques

1.  **SOLID** : Respect des principes de conception, notamment la responsabilité unique et l'inversion de dépendance (utilisée dans les contrôleurs UI).
2.  **Typage** : Utilisation stricte des `Type Hints` Python vérifiée par `mypy`.
3.  **Tests** : Couverture de tests unitaires (via `pytest`) pour sécuriser les refactorings.
4.  **Formatage** : Code formaté automatiquement par `black` et `isort`, et vérifié par `ruff`.

### Commandes Utiles

Un script utilitaire `run_quality.sh` est fourni pour faciliter les vérifications :

- **Linting et Formatage** :

  ```bash
  ./run_quality.sh --fix
  ```

- **Tests Unitaires** :

  ```bash
  ./run_quality.sh --test
  ```

- **Couverture de Code** :

  ```bash
  ./run_quality.sh --cov
  ```

- **Pipeline complet** :

  ```bash
  ./run_quality.sh --all
  ```

## Environnement de Développement

### Installation

#### Prérequis système (Ubuntu "fresh")

```bash
sudo apt update

# Python + outils de base
sudo apt install -y python3 python3-venv python3-pip

# GTK4 / PyGObject
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0

# GRUB tooling (inclut grub-mkrescue pour la preview)
sudo apt install -y grub2-common grub-common-bin grub-pc-bin grub-efi-amd64-bin

# Preview réelle via QEMU/UEFI
sudo apt install -y qemu-system-x86 ovmf xorriso mtools
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Où mettre quoi (règles simples)

- Parsing/validation GRUB: `core/io/`
- Accès système/commandes: `core/system/`
- Orchestration métier: `core/managers/` et `core/services/`
- Widgets, handlers, dialogs: `ui/`
- Tests core: `tests/core/` ; tests UI: `tests/ui/`

### Lancement

```bash
# Lancement simple
python main.py

# Avec logs détaillés
DEBUG=1 python main.py
```

Si tu veux une vue "utilisateur" (installation + prérequis + usage), voir : [USER.md](USER.md).
