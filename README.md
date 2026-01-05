# Gestionnaire de Configuration GRUB

Une application graphique simple pour configurer le chargeur de démarrage GRUB sur Linux.

Ce projet permet de modifier les paramètres de démarrage de votre système (délai, entrée par défaut, apparence) via une interface visuelle, sans avoir à éditer manuellement des fichiers de configuration complexes.

## Fonctionnalités

- **Configuration Générale** : Modifiez le délai d'attente (timeout) et choisissez le système d'exploitation par défaut.
- **Apparence** : Changez la résolution de l'écran de démarrage et les couleurs du menu.
- **Gestion des Entrées** : Masquez ou affichez certaines entrées du menu (comme les options de récupération ou les tests mémoire).
- **Thèmes** : Créez et appliquez des thèmes personnalisés.
- **Sécurité** : Le système effectue des sauvegardes automatiques avant chaque modification pour éviter tout problème.

## Installation

### Prérequis

- Linux avec GRUB2 installé.
- Python 3.12 ou plus récent.
- GTK 4.

### Dépendances Système

Sur Ubuntu/Debian :

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 grub2-common
```

Sur Fedora :

```bash
sudo dnf install python3-gobject gtk4 grub2-tools
```

Sur Arch Linux :

```bash
sudo pacman -S python-gobject gtk4 grub
```

### Installation du Projet

1.  Clonez le dépôt :

    ```bash
    git clone https://github.com/votre-nom/grub_manager.git
    cd grub_manager
    ```

2.  Créez un environnement virtuel et installez les dépendances :
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

## Utilisation

Pour lancer l'application, vous devez disposer des droits d'administration (root) car elle modifie des fichiers système.

```bash
sudo .venv/bin/python main.py
```

## Développement

Si vous souhaitez contribuer ou modifier le code :

- **Tests** : Le projet dispose d'une suite de tests complète.
  ```bash
  pytest
  ```
- **Qualité du code** : Un script est disponible pour vérifier le style et la qualité du code.
  ```bash
  ./run_quality.sh --lint
  ```

Le code est structuré en deux parties principales :

- `core/` : La logique de gestion de GRUB (lecture, écriture, sauvegarde).
- `ui/` : L'interface graphique (fenêtres, boutons, interactions).
