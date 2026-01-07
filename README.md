# Grub Manager

Application GTK (Python) pour configurer GRUB sur Linux.

Ce projet essaye d'être utile et prudent, mais il modifie des fichiers système (GRUB). Utilise-le en connaissance de cause.

## Prérequis

- Linux avec **GRUB2**.
- Python **3.12+**.
- GTK4 + PyGObject.

### Paquets système (Ubuntu/Debian)

Installation "Ubuntu propre" (dépendances UI + outils GRUB + preview QEMU) :

```bash
sudo apt update

# Python + venv
sudo apt install -y python3 python3-venv python3-pip

# GTK4 / PyGObject (bindings GI)
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0

# Outils GRUB (inclut grub-mkrescue)
sudo apt install -y grub2-common grub-common-bin grub-pc-bin grub-efi-amd64-bin

# Preview "réelle" via QEMU (recommandé)
sudo apt install -y qemu-system-x86 ovmf xorriso mtools
```

## Installation (venv)

```bash
git clone <URL_DU_DEPOT>
cd Grub_manager

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
source .venv/bin/activate
python main.py
```

L'application peut demander une élévation de privilèges (pkexec) pour lire/écrire la configuration GRUB.

## Documentation

- Guide utilisateur (installation, usage, prérequis, preview QEMU) : [docs/USER.md](docs/USER.md)
- Guide développeur (architecture core/ui, qualité, tests, preview QEMU) : [docs/DEV.md](docs/DEV.md)

## Qualité (dev)

```bash
./run_quality.sh --lint
./run_quality.sh --test
./run_quality.sh --all
```
