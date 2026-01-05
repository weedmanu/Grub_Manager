# Utilisation (Grub_manager)

Application GTK (Python) pour configurer GRUB sur Linux (timeout, entrée par défaut, visibilité des entrées, thèmes).

Ça touche à des fichiers système et peut lancer des commandes GRUB : garde une méthode de récupération sous la main (clé USB live, snapshot, etc.).

## Prérequis

- Linux avec GRUB2.
- Python 3.12+.
- GTK4 (PyGObject).

Exemples de dépendances système :

Ubuntu/Debian :

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 grub2-common
```

Fedora :

```bash
sudo dnf install python3-gobject gtk4 grub2-tools
```

Arch :

```bash
sudo pacman -S python-gobject gtk4 grub
```

## Installation

```bash
git clone https://github.com/votre-nom/grub_manager.git
cd grub_manager

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l’application

Le point d’entrée est [main.py](../main.py). Il tente une élévation unique via `pkexec` (prompt graphique) si tu n’es pas déjà root.

```bash
.venv/bin/python main.py
```

Si `pkexec` n’est pas dispo, tu peux lancer via sudo :

```bash
sudo .venv/bin/python main.py
```

## À quoi servent les onglets

- Général : timeout + entrée par défaut.
- Entrées : masquer/afficher certaines entrées (récup, memtest, etc.).
- Affichage : options liées au rendu/menu.
- Thèmes : appliquer/générer des thèmes.
- Sauvegardes / Maintenance : sauvegarder/restaurer et opérations d’entretien.

## Dépannage rapide

- Si l’app refuse l’élévation : vérifier `pkexec` (PolicyKit) ou lancer via sudo.
- Si tu as cassé un boot : utiliser l’onglet sauvegardes/restauration (ou restaurer depuis un live).
