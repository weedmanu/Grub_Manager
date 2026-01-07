# Documentation Technique

Ce document présente l'architecture et les directives de développement pour le projet Grub Manager.

## Architecture

L'application suit une séparation stricte entre la logique métier et l'interface utilisateur.

- **`core/`** : Contient toute la logique métier, les accès système et la gestion de configuration. Ce module ne dépend d'aucune bibliothèque graphique.
- **`ui/`** : Contient l'interface utilisateur basée sur GTK4. Elle orchestre les interactions et relaie les actions vers le `core`.

### Arborescence du Projet

```text
.
├── core/                               # COEUR DU SYSTÈME
│   ├── config/                         # Configuration (logs, chemins, runtime)
│   ├── io/                             # Entrées/Sorties (parsing GRUB, validation)
│   ├── managers/                       # Logique d'application et d'état
│   │   ├── core_managers_apply.py      # Orchestrateur de sauvegarde
│   │   ├── core_managers_protocol.py   # Interfaces et contrats
│   │   └── ...
│   ├── models/                         # Structures de données (Dataclasses)
│   ├── services/                       # Services métier (Maintenance, Thèmes...)
│   │   ├── core_services_qemu_preview.py# Preview "réelle" via QEMU (ISO + boot)
│   ├── system/                         # Commandes système (update-grub, etc.)
│   └── theme/                          # Moteur de génération de thèmes
│
├── ui/                                 # INTERFACE GRAPHIQUE (GTK4)
│   ├── builders/                       # Construction des widgets et fenêtres
│   ├── components/                     # Composants réutilisables
│   ├── config/                         # Styles CSS et constantes UI
│   ├── controllers/                    # Contrôleurs (MVC/MVP)
│   │   ├── ui_controllers_manager.py    # Bouton "Preview" -> service QEMU (thread)
│   ├── dialogs/                        # Fenêtres de dialogue
│   ├── helpers/                        # Utilitaires GTK
│   ├── models/                         # État de l'UI et Mappers
│   └── tabs/                           # Logique des onglets principaux
│
├── tests/                              # SUITE DE TESTS
│   ├── core/                           # Tests unitaires du coeur
│   ├── ui/                             # Tests unitaires de l'interface
│   └── conftest.py                     # Configuration Pytest
│
├── docs/                               # DOCUMENTATION
├── main.py                             # Point d'entrée de l'application
├── run_quality.sh                      # Script de qualité (lint, format, test)
└── requirements.txt                    # Dépendances Python
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
