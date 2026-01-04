# TODO — Grub Manager (AAA maintenable)

Date: 3 janvier 2026

## Priorités (sans changement d’UX)

### 1) Harmoniser la fenêtre parente (dialogs/popups)

- [ ] Remplacer les appels dispersés à `get_root()` par `GtkHelper.resolve_parent_window()` dans les onglets/dialogs restants.
- [ ] S’assurer que tous les `Gtk.AlertDialog.choose(parent=...)` reçoivent un parent quand disponible.
- [ ] Mettre à jour/ajouter des tests ciblés pour les chemins “parent introuvable”.

### 2) Centraliser la politique des boutons d’onglets (Recharger/Appliquer)

- [ ] Extraire la logique de `UIBuilder._create_notebook/_on_switch_page` dans un module dédié (ex: `ui/ui_tab_policy.py`).
- [ ] Couvrir par tests unitaires (labels d’onglets → état des boutons) sans boucle GTK complète.

### 3) Réduire la taille de `ui/ui_manager.py`

- [ ] Extraire un contrôleur “InfoBar” (affichage messages + timers).
- [ ] Extraire un contrôleur “Apply/Reload workflow” (dialog confirmations + orchestration) en gardant les mêmes méthodes publiques.
- [ ] Extraire les helpers “model <-> widgets” si possible (sans casser les tests existants).

## Validation

- [ ] `make lint`
- [ ] `pytest`

## Notes

- Objectif: refactor interne uniquement (zéro changement d’UX).
- Garder les APIs publiques utilisées par les tests (`GrubConfigManager.on_save/on_reload/_perform_save`, etc.).
