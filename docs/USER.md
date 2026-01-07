# Manuel d'Utilisation

Grub Manager est une application graphique permettant de configurer le chargeur de démarrage GRUB de manière simple et sécurisée.

Ce projet fait de son mieux pour être prudent, mais il agit sur des fichiers système. Si tu n'es pas à l'aise avec GRUB, je te recommande de prévoir un moyen de récupération (clé USB live, accès au BIOS/UEFI, etc.).

## Fonctionnalités Principales

- **Configuration Générale** : Modification du délai (timeout) et de l'entrée par défaut.
- **Gestion des Entrées** : Masquage/Affichage des entrées de menu indésirables.
- **Thèmes** : Installation, prévisualisation et configuration de thèmes GRUB.
- **Maintenance** : Outils de nettoyage et de vérification des paquets liés à GRUB.

## Installation

L'installation (prérequis système + création du venv + dépendances QEMU/OVMF) est décrite dans le README :

- [README.md](../README.md)

Ce guide utilisateur se concentre sur l'usage et les comportements côté application.

### Important (droits)

- Certaines actions nécessitent les droits administrateur (lecture/écriture de fichiers GRUB). L'application peut demander une élévation (pkexec).
- La preview QEMU est lancée côté utilisateur lorsque c'est possible (même si l'app a été lancée avec élévation), pour éviter des problèmes de permissions/affichage.

## Utilisation

Pour lancer l'application :

```bash
source .venv/bin/activate
python main.py
```

> **Note** : L'application demandera une élévation de privilèges (mot de passe administrateur) au démarrage pour pouvoir modifier les fichiers de configuration système protégés.

### Prévisualisation (Preview) GRUB

- Le bouton **Preview** ouvre une fenêtre QEMU (ISO bootable) pour afficher un menu GRUB avec un rendu proche du réel.
- Le mode utilisé cherche à "miroiter" ton `grub.cfg` (en retirant ce qui dépend du disque hôte, et en adaptant le thème si possible).
- Fermer la fenêtre QEMU ferme la preview.
- Si tu fermes Grub Manager alors qu'une preview est encore ouverte, l'application tente de fermer QEMU automatiquement.

### Dépannage (rapide)

- **La preview ne démarre pas**: vérifie que `qemu-system-x86_64` est installé (paquet `qemu-system-x86`).
- **Erreur OVMF/UEFI**: installe `ovmf` (sinon la preview peut se rabattre sur BIOS selon la machine).
- **Erreur grub-mkrescue**: installe les paquets GRUB listés plus haut (notamment `grub2-common` et les binaires grub-\*).

## Sécurité

L'application intègre plusieurs mécanismes de sécurité :

- **Sauvegardes automatiques** des fichiers de configuration avant modification.
- **Validation** de la configuration générée avant application réelle.
- **Restauration** facile en cas de problème.

Pour plus de détails techniques (architecture, organisation core/ui, qualité), voir : [DEV.md](DEV.md).
