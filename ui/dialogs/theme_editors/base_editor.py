"""Base class for theme element editors."""

from __future__ import annotations

from typing import Any

from gi.repository import Gtk


def _try_set_spin_suffix(spin: Gtk.SpinButton, suffix: str) -> None:
    """Applique un suffixe si l'API GTK l'expose."""
    set_suffix = getattr(spin, "set_suffix", None)
    if callable(set_suffix):
        set_suffix(suffix)


class BaseElementEditor(Gtk.Box):
    """Base class for all theme element editors."""

    def __init__(self, element_name: str, element_label: str):
        """Initialize editor.

        Args:
            element_name: Internal name of the element
            element_label: Display label of the element
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.element_name = element_name
        self.element_label = element_label
        self.config_widgets = {}

        # Title
        title = Gtk.Label()
        title.set_markup(f"<b>Configuration de {element_label}</b>")
        title.set_halign(Gtk.Align.START)
        self.append(title)

    def _create_config_row(self, label: str, widget: Gtk.Widget) -> Gtk.Box:
        """Create a configuration row."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        label_widget = Gtk.Label(label=label)
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_size_request(150, -1)
        row.append(label_widget)

        widget.set_hexpand(True)
        row.append(widget)

        return row

    def _create_file_row(
        self,
        label: str,
        entry: Gtk.Entry,
        action: Gtk.FileChooserAction = Gtk.FileChooserAction.OPEN,
        file_filter: Gtk.FileFilter | None = None,
    ) -> Gtk.Box:
        """Create a row with an entry and a browse button."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        entry.set_hexpand(True)
        box.append(entry)

        browse_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        browse_btn.set_tooltip_text("Parcourir...")
        browse_btn.connect("clicked", self._on_browse_clicked, entry, action, file_filter)
        box.append(browse_btn)

        return self._create_config_row(label, box)

    def _on_browse_clicked(
        self,
        _button: Gtk.Button,
        entry: Gtk.Entry,
        action: Gtk.FileChooserAction = Gtk.FileChooserAction.OPEN,
        file_filter: Gtk.FileFilter | None = None,
    ) -> None:
        """Open file/folder chooser dialog."""
        title = "Choisir un dossier" if action == Gtk.FileChooserAction.SELECT_FOLDER else "Choisir un fichier"
        dialog = Gtk.FileChooserNative.new(
            title,
            self.get_root() if isinstance(self.get_root(), Gtk.Window) else None,
            action,
            "Sélectionner",
            "Annuler",
        )

        if file_filter:
            dialog.add_filter(file_filter)
        elif action == Gtk.FileChooserAction.OPEN:
            # Default image filter if none provided for OPEN
            filter_img = Gtk.FileFilter()
            filter_img.set_name("Images (PNG, JPG)")
            filter_img.add_mime_type("image/png")
            filter_img.add_mime_type("image/jpeg")
            filter_img.add_pattern("*.png")
            filter_img.add_pattern("*.jpg")
            filter_img.add_pattern("*.jpeg")
            dialog.add_filter(filter_img)

        def on_response(native, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                file = native.get_file()
                if file:
                    entry.set_text(file.get_path())

        dialog.connect("response", on_response)
        dialog.show()

    def get_properties(self) -> dict[str, Any]:
        """Get current properties from widgets."""
        props = {}
        for key, widget in self.config_widgets.items():
            if isinstance(widget, Gtk.SpinButton):
                props[key] = widget.get_value()
            elif isinstance(widget, Gtk.Entry):
                props[key] = widget.get_text()
            elif isinstance(widget, Gtk.ColorButton):
                rgba = widget.get_property("rgba")
                props[key] = f"#{int(rgba.red*255):02x}{int(rgba.green*255):02x}{int(rgba.blue*255):02x}"
            elif isinstance(widget, Gtk.DropDown):
                model = widget.get_model()
                selected = widget.get_selected()
                if model and selected != Gtk.INVALID_LIST_POSITION:
                    item = model.get_item(selected)
                    if hasattr(item, "get_string"):
                        props[key] = item.get_string()
                    else:
                        props[key] = selected
                else:
                    props[key] = selected
            elif isinstance(widget, Gtk.FontButton):
                props[key] = widget.get_property("font")
            elif isinstance(widget, Gtk.Switch):
                props[key] = widget.get_active()

        return props
