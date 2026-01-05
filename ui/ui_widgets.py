"""Module consolidé de widgets et helpers UI pour GTK4.

Fusionne les fonctionnalités de widget_factory.py et tab_helpers.py.
Fournit des utilitaires réutilisables pour la construction d'interfaces.
"""

from __future__ import annotations

from gi.repository import Gtk, Pango
from loguru import logger

# ============================================================================
# CRÉATION DE WIDGETS
# ============================================================================


def create_section_header(text: str) -> Gtk.Label:
    """Crée un en-tête de section stylisé.

    Args:
        text: Texte de l'en-tête

    Returns:
        Label formaté comme en-tête
    """
    label = Gtk.Label()
    label.set_markup(f"<span size='large' weight='bold'>{text}</span>")
    label.set_halign(Gtk.Align.START)
    label.add_css_class("section-header")
    return label


def create_section_title(text: str) -> Gtk.Label:
    """Crée un titre de section.

    Args:
        text: Texte du titre

    Returns:
        Label formaté comme titre
    """
    label = Gtk.Label()
    label.set_markup(f"<b>{text}</b>")
    label.set_halign(Gtk.Align.START)
    label.add_css_class("section-title")
    return label


def box_append_section_grid(
    box: Gtk.Box,
    title: str,
    *,
    row_spacing: int = 12,
    column_spacing: int = 12,
) -> Gtk.Grid:
    """Ajoute un titre de sous-section + un Grid préconfiguré.

    Centralise un motif très fréquent dans les onglets :
    - un titre (classe CSS section-title)
    - une grille avec des espacements homogènes.
    """
    box.append(create_section_title(title))

    grid = Gtk.Grid()
    grid.set_row_spacing(row_spacing)
    grid.set_column_spacing(column_spacing)
    box.append(grid)
    return grid


# ============================================================================
# HELPERS DE DISPOSITION (GRID)
# ============================================================================


def grid_add_labeled(
    grid: Gtk.Grid,
    row: int,
    label_text: str,
    widget: Gtk.Widget,
    *,
    label_xalign: float = 0,
    label_valign: Gtk.Align | None = None,
) -> int:
    """Ajoute une ligne Label + Widget à un Grid.

    Args:
        grid: Grid cible
        row: Index de ligne
        label_text: Texte du label
        widget: Widget à ajouter
        label_xalign: Alignement horizontal du label (0-1)
        label_valign: Alignement vertical du label

    Returns:
        Prochain index de ligne
    """
    # pylint: disable=too-many-arguments
    logger.debug(f"[grid_add_labeled] Ligne {row}: {label_text[:30]} + {widget.__class__.__name__}")
    label = Gtk.Label(label=label_text, xalign=label_xalign)
    if label_valign is not None:
        label.set_valign(label_valign)
    grid.attach(label, 0, row, 1, 1)
    grid.attach(widget, 1, row, 1, 1)
    return row + 1


def grid_add_check(grid: Gtk.Grid, row: int, check: Gtk.CheckButton, *, colspan: int = 2) -> int:
    """Ajoute un CheckButton sur une ligne du Grid.

    Args:
        grid: Grid cible
        row: Index de ligne
        check: CheckButton à ajouter
        colspan: Nombre de colonnes à occuper

    Returns:
        Prochain index de ligne
    """
    logger.debug(f"[grid_add_check] Ligne {row}: {check.get_label()[:30]}")
    grid.attach(check, 0, row, colspan, 1)
    return row + 1


def grid_add_switch(grid: Gtk.Grid, row: int, label_text: str, switch: Gtk.Switch) -> int:
    """Ajoute un Switch avec son label dans le Grid (aligné professionnellement).

    Args:
        grid: Grid cible
        row: Index de ligne
        label_text: Texte du label
        switch: Switch à ajouter

    Returns:
        Prochain index de ligne
    """
    logger.debug(f"[grid_add_switch] Ligne {row}: {label_text[:50]}")

    # Box pour organiser label + switch
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    hbox.set_hexpand(True)

    label = Gtk.Label(label=label_text, xalign=0)
    label.set_hexpand(True)
    hbox.append(label)
    hbox.append(switch)

    grid.attach(hbox, 0, row, 2, 1)
    return row + 1


# ============================================================================
# HELPERS DE DISPOSITION (BOX)
# ============================================================================


def box_append_label(
    box: Gtk.Box,
    text: str,
    *,
    halign: Gtk.Align = Gtk.Align.START,
    italic: bool = False,
) -> Gtk.Label:
    """Ajoute un label à une Box.

    Args:
        box: Box cible
        text: Texte du label
        halign: Alignement horizontal
        italic: Si True, affiche en italique

    Returns:
        Label créé
    """
    logger.debug(f"[box_append_label] Label: {text[:30]} (italic={italic})")
    label = Gtk.Label()
    if italic:
        label.set_markup(f"<i>{text}</i>")
        label.add_css_class("dim-label")
        label.add_css_class("subtitle-label")
    else:
        label.set_text(text)
    label.set_wrap(True)
    label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    label.set_xalign(0)
    label.set_justify(Gtk.Justification.LEFT)
    label.set_halign(halign)
    box.append(label)
    return label


def box_append_section_title(box: Gtk.Box, text: str) -> Gtk.Label:
    """Ajoute un titre de section dans une Box.

    Args:
        box: Box cible
        text: Texte du titre

    Returns:
        Label créé
    """
    logger.debug(f"[box_append_section_title] Titre: {text}")
    label = Gtk.Label()
    label.set_markup(f"<b>{text}</b>")
    label.set_halign(Gtk.Align.START)
    label.add_css_class("section-title")
    box.append(label)
    return label


def box_append_switch(box: Gtk.Box, label_text: str, switch: Gtk.Switch) -> Gtk.Box:
    """Ajoute un Switch avec son label dans une Box (aligné professionnellement).

    Args:
        box: Box cible
        label_text: Texte du label
        switch: Switch à ajouter

    Returns:
        Box horizontale créée contenant label + switch
    """
    logger.debug(f"[box_append_switch] Switch: {label_text[:50]}")

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    hbox.set_hexpand(True)

    label = Gtk.Label(label=label_text, xalign=0)
    label.set_hexpand(True)
    hbox.append(label)
    hbox.append(switch)

    box.append(hbox)
    return hbox


# ============================================================================
# HELPERS DE MARGES
# ============================================================================


def apply_margins(widget: Gtk.Widget, margin: int = 12) -> None:
    """Applique des marges uniformes à un widget.

    Args:
        widget: Widget cible
        margin: Taille de la marge en pixels
    """
    logger.debug(f"[apply_margins] margin={margin} pour {widget.__class__.__name__}")
    widget.set_margin_top(margin)
    widget.set_margin_bottom(margin)
    widget.set_margin_start(margin)
    widget.set_margin_end(margin)


# ============================================================================
# CRÉATION DE CONTENEURS
# ============================================================================


def create_main_box(spacing: int = 10, margin: int = 10) -> Gtk.Box:
    """Crée une boîte principale avec configuration standard.

    Args:
        spacing: Espacement entre les éléments
        margin: Marge autour de la boîte

    Returns:
        Box verticale configurée
    """
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    main_box.set_margin_start(margin)
    main_box.set_margin_end(margin)
    main_box.set_margin_top(margin)
    main_box.set_margin_bottom(margin)
    return main_box


def make_scrolled_grid(
    *,
    h_policy: Gtk.PolicyType = Gtk.PolicyType.NEVER,
    v_policy: Gtk.PolicyType = Gtk.PolicyType.AUTOMATIC,
    margin: int = 12,
    col_spacing: int = 12,
    row_spacing: int = 12,
) -> tuple[Gtk.ScrolledWindow, Gtk.Grid]:
    """Crée un Grid scrollable avec espacement configurable.

    Args:
        h_policy: Politique de scroll horizontal
        v_policy: Politique de scroll vertical
        margin: Marge autour du grid
        col_spacing: Espacement entre colonnes
        row_spacing: Espacement entre lignes

    Returns:
        Tuple (ScrolledWindow, Grid)
    """
    logger.debug(f"[make_scrolled_grid] margin={margin}, spacing=({col_spacing},{row_spacing})")
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(h_policy, v_policy)

    grid = Gtk.Grid()
    grid.set_column_spacing(col_spacing)
    grid.set_row_spacing(row_spacing)
    apply_margins(grid, margin)

    scroll.set_child(grid)
    return scroll, grid


# ============================================================================
# HELPERS LISTBOX
# ============================================================================


def create_list_box_row_with_margins(
    margin_top: int = 6,
    margin_bottom: int = 6,
    margin_start: int = 8,
    margin_end: int = 8,
) -> tuple[Gtk.ListBoxRow, Gtk.Box]:
    """Crée une ligne de ListBox avec Box préformatée.

    Args:
        margin_top: Marge supérieure
        margin_bottom: Marge inférieure
        margin_start: Marge gauche
        margin_end: Marge droite

    Returns:
        Tuple (ListBoxRow, HBox)
    """
    row = Gtk.ListBoxRow()
    row.set_selectable(True)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    hbox.set_margin_top(margin_top)
    hbox.set_margin_bottom(margin_bottom)
    hbox.set_margin_start(margin_start)
    hbox.set_margin_end(margin_end)

    row.set_child(hbox)
    return row, hbox


def create_two_column_layout(parent_box: Gtk.Box, spacing: int = 12) -> tuple[Gtk.Box, Gtk.Box, Gtk.Box]:
    """Crée une disposition à deux colonnes homogènes.

    Args:
        parent_box: Conteneur parent
        spacing: Espacement entre les colonnes

    Returns:
        Tuple (conteneur_principal, colonne_gauche, colonne_droite)
    """
    columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
    columns.set_homogeneous(True)
    columns.set_hexpand(True)
    columns.set_vexpand(True)
    parent_box.append(columns)

    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    left.set_hexpand(True)
    left.set_vexpand(True)
    columns.append(left)

    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    right.set_hexpand(True)
    right.set_vexpand(True)
    columns.append(right)

    return columns, left, right


def create_info_box(title: str, text: str, css_class: str = "info-box") -> Gtk.Box:
    """Crée une boîte d'information stylisée.

    Args:
        title: Titre de la boîte
        text: Texte du contenu
        css_class: Classe CSS à appliquer

    Returns:
        Widget Gtk.Box contenant l'info
    """
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box.add_css_class(css_class)
    box.set_margin_top(12)

    if title:
        lbl_title = Gtk.Label(xalign=0)
        lbl_title.set_markup(f"<b>{title}</b>")
        box.append(lbl_title)

    lbl_text = Gtk.Label(xalign=0, label=text)
    lbl_text.set_wrap(True)
    box.append(lbl_text)

    return box


def clear_listbox(listbox: Gtk.ListBox) -> None:
    """Supprime toutes les lignes d'une ListBox.

    Args:
        listbox: ListBox à nettoyer
    """
    logger.debug("[clear_listbox] Nettoyage de la ListBox")
    child = listbox.get_first_child()
    count = 0
    while child is not None:
        nxt = child.get_next_sibling()
        listbox.remove(child)
        count += 1
        child = nxt
    logger.debug(f"[clear_listbox] {count} élément(s) supprimé(s)")


# ============================================================================
# DIALOGUES STANDARD
# ============================================================================


def create_error_dialog(message: str, parent=None) -> None:
    """Affiche un dialogue d'erreur standard.

    Args:
        message: Message d'erreur
        parent: Fenêtre parente (optionnel)
    """
    dialog = Gtk.AlertDialog()
    dialog.set_message("Erreur")
    dialog.set_detail(message)
    dialog.set_buttons(["OK"])
    dialog.show(parent=parent)


def create_success_dialog(message: str, parent=None) -> None:
    """Affiche un dialogue de succès standard.

    Args:
        message: Message de succès
        parent: Fenêtre parente (optionnel)
    """
    dialog = Gtk.AlertDialog()
    dialog.set_message("Succès")
    dialog.set_detail(message)
    dialog.set_buttons(["OK"])
    dialog.show(parent=parent)


# ============================================================================
# UTILITAIRES
# ============================================================================


def categorize_backup_type(path: str) -> str:
    """Catégorise le type de sauvegarde d'après le chemin.

    Args:
        path: Chemin de la sauvegarde

    Returns:
        Catégorie de la sauvegarde
    """
    if path.endswith(".backup.initial"):
        return "Initiale"
    if ".backup.manual." in path:
        return "Manuelle"
    if path.endswith(".backup"):
        return "Auto (enregistrement)"
    return "Auto"
