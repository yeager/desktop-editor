"""Main editor window."""
import csv
import json
import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk, Pango  # noqa: E402

from desktop_editor.i18n import _
from desktop_editor.desktop_file import (
from datetime import datetime as _dt_now
    DesktopFile,
    MAIN_CATEGORIES,
    list_desktop_files,
)


class DesktopEditorWindow(Adw.ApplicationWindow):
    """The main editor window with sidebar browser and editor panes."""

    def __init__(self, **kwargs):
        super().__init__(
            title=_("Desktop File Editor"),
            default_width=1000,
            default_height=700,
            **kwargs,
        )
        self.desktop_file: DesktopFile | None = None
        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        # Header bar
        header = Adw.HeaderBar()

        # Menu button
        menu = Gio.Menu.new()
        menu.append(_("New"), "app.new")
        menu.append(_("Open…"), "app.open")
        menu.append(_("Save"), "app.save")
        menu.append(_("Save As…"), "app.save-as")
        menu.append(_("About"), "app.about")
        menu.append(_("Quit"), "app.quit")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_button)

        # Theme toggle
        self._theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                                     tooltip_text="Toggle dark/light theme")
        self._theme_btn.connect("clicked", self._on_theme_toggle)
        header.pack_end(self._theme_btn)

        # Export button
        export_btn = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export data"))
        export_btn.set_icon_name("document-send-symbolic")
        export_btn.connect("clicked", self._on_export_clicked)
        header.pack_end(export_btn)

        # Save button in header
        save_btn = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Save"))
        save_btn.connect("clicked", lambda b: self.save_file())
        header.pack_start(save_btn)

        # Main layout: split view with sidebar
        self.split_view = Adw.OverlaySplitView(
            show_sidebar=True,
            min_sidebar_width=220,
            max_sidebar_width=320,
        )

        # ── Sidebar: file browser ──
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_title_widget(Gtk.Label(label=_("Applications")))
        sidebar_header.set_show_end_title_buttons(False)
        sidebar_box.append(sidebar_header)

        # File list
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        self.file_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.file_list.add_css_class("navigation-sidebar")
        self.file_list.connect("row-activated", self._on_file_selected)
        scrolled.set_child(self.file_list)
        sidebar_box.append(scrolled)

        self.split_view.set_sidebar(sidebar_box)

        # ── Content: editor ──
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.append(header)

        # Stack for editor pages
        self.stack = Adw.ViewStack()

        # Editor page
        editor_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.editor_page = self._build_editor_page()
        editor_scroll.set_child(self.editor_page)
        self.stack.add_titled(editor_scroll, "editor", _("Editor"))

        # Translations page
        trans_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.translations_page = self._build_translations_page()
        trans_scroll.set_child(self.translations_page)
        self.stack.add_titled(trans_scroll, "translations", _("Translations"))

        # Validation page
        valid_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.validation_page = self._build_validation_page()
        valid_scroll.set_child(self.validation_page)
        self.stack.add_titled(valid_scroll, "validation", _("Validation"))

        # Preview page
        preview_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.preview_page = self._build_preview_page()
        preview_scroll.set_child(self.preview_page)
        self.stack.add_titled(preview_scroll, "preview", _("Preview"))

        # View switcher bar
        switcher = Adw.ViewSwitcherBar(stack=self.stack, reveal=True)
        content_box.append(self.stack)
        content_box.append(switcher)

        self.split_view.set_content(content_box)

        # Wrap in toolbarview
        # Status bar
        self._status_bar = Gtk.Label(label="", halign=Gtk.Align.START,
                                     margin_start=12, margin_end=12, margin_bottom=4)
        self._status_bar.add_css_class("dim-label")
        self._status_bar.add_css_class("caption")

        _outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        _outer_box.append(self.split_view)
        _outer_box.append(self._status_bar)
        self.set_content(_outer_box)

        # Populate sidebar
        self._populate_file_list()

    def _build_editor_page(self) -> Gtk.Widget:
        """Build the main editor form."""
        clamp = Adw.Clamp(maximum_size=700, margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Basic fields group
        basic_group = Adw.PreferencesGroup(title=_("Basic Properties"))

        self.entry_name = Adw.EntryRow(title=_("Name"))
        basic_group.add(self.entry_name)

        self.entry_generic_name = Adw.EntryRow(title=_("Generic Name"))
        basic_group.add(self.entry_generic_name)

        self.entry_comment = Adw.EntryRow(title=_("Comment"))
        basic_group.add(self.entry_comment)

        self.entry_exec = Adw.EntryRow(title=_("Exec"))
        basic_group.add(self.entry_exec)

        self.entry_icon = Adw.EntryRow(title=_("Icon"))
        basic_group.add(self.entry_icon)

        self.entry_path = Adw.EntryRow(title=_("Working Directory"))
        basic_group.add(self.entry_path)

        box.append(basic_group)

        # Type & options
        options_group = Adw.PreferencesGroup(title=_("Options"))

        self.combo_type = Adw.ComboRow(title=_("Type"))
        type_model = Gtk.StringList.new(["Application", "Link", "Directory"])
        self.combo_type.set_model(type_model)
        options_group.add(self.combo_type)

        self.switch_terminal = Adw.SwitchRow(title=_("Run in Terminal"))
        options_group.add(self.switch_terminal)

        self.switch_no_display = Adw.SwitchRow(title=_("No Display"))
        options_group.add(self.switch_no_display)

        self.switch_startup_notify = Adw.SwitchRow(title=_("Startup Notification"))
        options_group.add(self.switch_startup_notify)

        box.append(options_group)

        # Categories
        cat_group = Adw.PreferencesGroup(title=_("Categories"))
        self.entry_categories = Adw.EntryRow(title=_("Categories (semicolon-separated)"))
        cat_group.add(self.entry_categories)

        # Quick category toggles
        cat_flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=6,
            row_spacing=4,
            column_spacing=4,
            margin_top=8,
        )
        self.cat_checks = {}
        for cat in MAIN_CATEGORIES:
            check = Gtk.CheckButton(label=cat)
            check.connect("toggled", self._on_category_toggled)
            self.cat_checks[cat] = check
            cat_flow.append(check)
        cat_group.add(cat_flow)
        box.append(cat_group)

        # Extra fields
        extra_group = Adw.PreferencesGroup(title=_("Additional Fields"))
        self.entry_mimetype = Adw.EntryRow(title=_("MIME Types"))
        extra_group.add(self.entry_mimetype)
        self.entry_keywords = Adw.EntryRow(title=_("Keywords"))
        extra_group.add(self.entry_keywords)
        self.entry_wm_class = Adw.EntryRow(title=_("StartupWMClass"))
        extra_group.add(self.entry_wm_class)
        self.entry_url = Adw.EntryRow(title=_("URL"))
        extra_group.add(self.entry_url)
        box.append(extra_group)

        clamp.set_child(box)
        return clamp

    def _build_translations_page(self) -> Gtk.Widget:
        clamp = Adw.Clamp(maximum_size=700, margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Add locale row
        add_group = Adw.PreferencesGroup(title=_("Add Translation"))
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.new_locale_entry = Gtk.Entry(placeholder_text=_("Locale code (e.g. sv, de, fr)"))
        self.new_locale_entry.set_hexpand(True)
        add_box.append(self.new_locale_entry)
        add_btn = Gtk.Button(label=_("Add"), css_classes=["suggested-action"])
        add_btn.connect("clicked", self._on_add_locale)
        add_box.append(add_btn)
        add_group.add(add_box)
        box.append(add_group)

        # Translation entries container
        self.translations_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(self.translations_box)

        clamp.set_child(box)
        return clamp

    def _build_validation_page(self) -> Gtk.Widget:
        clamp = Adw.Clamp(maximum_size=700, margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        validate_btn = Gtk.Button(label=_("Run Validation"), css_classes=["suggested-action"])
        validate_btn.connect("clicked", self._on_validate)
        box.append(validate_btn)

        self.validation_list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
        )
        box.append(self.validation_list)

        clamp.set_child(box)
        return clamp

    def _build_preview_page(self) -> Gtk.Widget:
        clamp = Adw.Clamp(maximum_size=400, margin_top=48, margin_bottom=24,
                          margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                      halign=Gtk.Align.CENTER)

        # App launcher preview
        frame = Gtk.Frame(css_classes=["card"])
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        margin_top=24, margin_bottom=24, margin_start=32, margin_end=32,
                        halign=Gtk.Align.CENTER)

        self.preview_icon = Gtk.Image(
            icon_name="application-x-executable",
            pixel_size=64,
        )
        inner.append(self.preview_icon)

        self.preview_name = Gtk.Label(
            label=_("Application Name"),
            css_classes=["title-3"],
        )
        inner.append(self.preview_name)

        self.preview_comment = Gtk.Label(
            label=_("Description"),
            css_classes=["dim-label"],
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        inner.append(self.preview_comment)

        frame.set_child(inner)
        box.append(frame)

        # File path label
        self.preview_path = Gtk.Label(
            label="",
            css_classes=["dim-label", "caption"],
            ellipsize=Pango.EllipsizeMode.MIDDLE,
        )
        box.append(self.preview_path)

        refresh_btn = Gtk.Button(label=_("Refresh Preview"), halign=Gtk.Align.CENTER)
        refresh_btn.connect("clicked", lambda b: self._update_preview())
        box.append(refresh_btn)

        clamp.set_child(box)
        return clamp

    # ── Sidebar ─────────────────────────────────────────────────────

    def _populate_file_list(self):
        while True:
            row = self.file_list.get_row_at_index(0)
            if row is None:
                break
            self.file_list.remove(row)

        for path in list_desktop_files():
            basename = os.path.basename(path)
            row = Gtk.ListBoxRow()
            label = Gtk.Label(
                label=basename,
                xalign=0,
                ellipsize=Pango.EllipsizeMode.END,
                margin_start=8, margin_end=8, margin_top=4, margin_bottom=4,
            )
            label.set_tooltip_text(path)
            row.set_child(label)
            row._desktop_path = path
            self.file_list.append(row)

    def _on_file_selected(self, listbox, row):
        if hasattr(row, "_desktop_path"):
            self.open_file(row._desktop_path)

    # ── File operations ─────────────────────────────────────────────

    def new_file(self):
        self.desktop_file = DesktopFile.new_application()
        self._load_into_ui()
        self.set_title(_("Desktop File Editor") + " — " + _("New File"))

    def open_file(self, path: str):
        try:
            self.desktop_file = DesktopFile.load(path)
            self._load_into_ui()
            self.set_title(_("Desktop File Editor") + " — " + os.path.basename(path))
        except Exception as e:
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=_("Error Opening File"),
                body=str(e),
            )
            dialog.add_response("ok", _("OK"))
            dialog.present()

    def save_file(self):
        if not self.desktop_file:
            return
        self._save_from_ui()
        if self.desktop_file.path:
            try:
                self.desktop_file.save()
                toast = Adw.Toast(title=_("File saved"))
                # Find or create toast overlay — just use simple approach
                self._show_toast(_("File saved"))
            except Exception as e:
                self._show_error(_("Error Saving File"), str(e))
        else:
            self.show_save_dialog()

    def _show_toast(self, message: str):
        """Show a simple toast notification."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=message,
        )
        dialog.add_response("ok", _("OK"))
        dialog.present()

    def _show_error(self, heading: str, body: str):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=heading,
            body=body,
        )
        dialog.add_response("ok", _("OK"))
        dialog.present()

    def show_open_dialog(self):
        dialog = Gtk.FileDialog(title=_("Open .desktop File"))
        f = Gtk.FileFilter()
        f.set_name(_("Desktop Files"))
        f.add_pattern("*.desktop")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_open_response)

    def _on_open_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.open_file(file.get_path())
        except Exception:
            pass

    def show_save_dialog(self):
        dialog = Gtk.FileDialog(title=_("Save .desktop File"))
        dialog.save(self, None, self._on_save_response)

    def _on_save_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                self._save_from_ui()
                self.desktop_file.save(file.get_path())
                self.set_title(_("Desktop File Editor") + " — " + os.path.basename(file.get_path()))
                self._show_toast(_("File saved"))
        except Exception:
            pass

    # ── UI ↔ Model ──────────────────────────────────────────────────

    def _load_into_ui(self):
        self._update_status_bar()
        """Load desktop file data into UI fields."""
        df = self.desktop_file
        if not df:
            return

        self.entry_name.set_text(df.entries.get("Name", ""))
        self.entry_generic_name.set_text(df.entries.get("GenericName", ""))
        self.entry_comment.set_text(df.entries.get("Comment", ""))
        self.entry_exec.set_text(df.entries.get("Exec", ""))
        self.entry_icon.set_text(df.entries.get("Icon", ""))
        self.entry_path.set_text(df.entries.get("Path", ""))
        self.entry_categories.set_text(df.entries.get("Categories", ""))
        self.entry_mimetype.set_text(df.entries.get("MimeType", ""))
        self.entry_keywords.set_text(df.entries.get("Keywords", ""))
        self.entry_wm_class.set_text(df.entries.get("StartupWMClass", ""))
        self.entry_url.set_text(df.entries.get("URL", ""))

        # Type combo
        dtype = df.entries.get("Type", "Application")
        type_map = {"Application": 0, "Link": 1, "Directory": 2}
        self.combo_type.set_selected(type_map.get(dtype, 0))

        # Switches
        self.switch_terminal.set_active(df.entries.get("Terminal", "false").lower() == "true")
        self.switch_no_display.set_active(df.entries.get("NoDisplay", "false").lower() == "true")
        self.switch_startup_notify.set_active(df.entries.get("StartupNotify", "false").lower() == "true")

        # Category checkboxes
        cats = [c.strip() for c in df.entries.get("Categories", "").split(";") if c.strip()]
        for cat, check in self.cat_checks.items():
            check.set_active(cat in cats)

        self._update_translations_page()
        self._update_preview()

    def _save_from_ui(self):
        """Save UI field values back to desktop file model."""
        df = self.desktop_file
        if not df:
            return

        type_map = {0: "Application", 1: "Link", 2: "Directory"}
        df.entries["Type"] = type_map.get(self.combo_type.get_selected(), "Application")
        df.entries["Name"] = self.entry_name.get_text()

        # Only set non-empty optional fields
        for key, entry in [
            ("GenericName", self.entry_generic_name),
            ("Comment", self.entry_comment),
            ("Exec", self.entry_exec),
            ("Icon", self.entry_icon),
            ("Path", self.entry_path),
            ("Categories", self.entry_categories),
            ("MimeType", self.entry_mimetype),
            ("Keywords", self.entry_keywords),
            ("StartupWMClass", self.entry_wm_class),
            ("URL", self.entry_url),
        ]:
            val = entry.get_text()
            if val:
                df.entries[key] = val
            elif key in df.entries:
                del df.entries[key]

        df.entries["Terminal"] = "true" if self.switch_terminal.get_active() else "false"
        df.entries["NoDisplay"] = "true" if self.switch_no_display.get_active() else "false"
        df.entries["StartupNotify"] = "true" if self.switch_startup_notify.get_active() else "false"

        # Save translations from UI
        self._save_translations_from_ui()

    def _on_category_toggled(self, check):
        """Update categories entry from checkboxes."""
        cats = [cat for cat, cb in self.cat_checks.items() if cb.get_active()]
        # Preserve any non-standard categories already in the entry
        current = [c.strip() for c in self.entry_categories.get_text().split(";") if c.strip()]
        extra = [c for c in current if c not in MAIN_CATEGORIES]
        all_cats = cats + extra
        self.entry_categories.set_text(";".join(all_cats) + ";" if all_cats else "")

    # ── Translations ────────────────────────────────────────────────

    def _update_translations_page(self):
        """Rebuild translations page from model."""
        # Clear
        while True:
            child = self.translations_box.get_first_child()
            if child is None:
                break
            self.translations_box.remove(child)

        df = self.desktop_file
        if not df:
            return

        self._trans_entries = {}  # (key, locale) -> EntryRow

        translatable_keys = ["Name", "GenericName", "Comment", "Keywords"]
        locales = df.get_locales()

        for locale in locales:
            group = Adw.PreferencesGroup(title=locale)

            # Delete locale button
            del_btn = Gtk.Button(
                icon_name="user-trash-symbolic",
                tooltip_text=_("Remove locale %s") % locale,
                css_classes=["destructive-action", "flat"],
                valign=Gtk.Align.CENTER,
            )
            del_btn._locale = locale
            del_btn.connect("clicked", self._on_remove_locale)
            group.set_header_suffix(del_btn)

            for key in translatable_keys:
                trans = df.get_translations(key)
                if locale in trans:
                    row = Adw.EntryRow(title=f"{key}[{locale}]")
                    row.set_text(trans[locale])
                    row._trans_key = key
                    row._trans_locale = locale
                    self._trans_entries[(key, locale)] = row
                    group.add(row)

            self.translations_box.append(group)

    def _save_translations_from_ui(self):
        """Write translation entries back to model."""
        if not hasattr(self, "_trans_entries"):
            return
        for (key, locale), row in self._trans_entries.items():
            text = row.get_text()
            if text:
                self.desktop_file.set_translation(key, locale, text)
            else:
                self.desktop_file.remove_translation(key, locale)

    def _on_add_locale(self, btn):
        locale = self.new_locale_entry.get_text().strip()
        if not locale or not self.desktop_file:
            return
        # Add empty translations for translatable keys
        for key in ["Name", "GenericName", "Comment", "Keywords"]:
            if self.desktop_file.entries.get(key):
                self.desktop_file.set_translation(key, locale, "")
        self.new_locale_entry.set_text("")
        self._update_translations_page()

    def _on_remove_locale(self, btn):
        locale = btn._locale
        if self.desktop_file:
            self.desktop_file.remove_locale(locale)
            self._update_translations_page()

    # ── Validation ──────────────────────────────────────────────────

    def _on_validate(self, btn):
        if not self.desktop_file:
            return
        self._save_from_ui()

        # Clear
        while True:
            row = self.validation_list.get_row_at_index(0)
            if row is None:
                break
            self.validation_list.remove(row)

        msgs = self.desktop_file.validate()
        if not msgs:
            row = Adw.ActionRow(title=_("✓ No issues found"), icon_name="emblem-ok-symbolic")
            self.validation_list.append(row)
        else:
            for msg in msgs:
                icon = "dialog-error-symbolic" if msg.level == "error" else "dialog-warning-symbolic"
                row = Adw.ActionRow(
                    title=msg.message,
                    icon_name=icon,
                )
                self.validation_list.append(row)

    # ── Preview ─────────────────────────────────────────────────────

    def _update_preview(self):
        if not self.desktop_file:
            return
        df = self.desktop_file
        name = df.entries.get("Name", _("Unnamed"))
        comment = df.entries.get("Comment", "")
        icon = df.entries.get("Icon", "application-x-executable")

        self.preview_name.set_label(name or _("Unnamed"))
        self.preview_comment.set_label(comment or "")

        # Try to set icon — could be a name or path
        if icon and os.path.isfile(icon):
            self.preview_icon.set_from_file(icon)
        else:
            self.preview_icon.set_from_icon_name(icon or "application-x-executable")

        self.preview_path.set_label(df.path or _("(unsaved)"))
    def _on_theme_toggle(self, _btn):
        sm = Adw.StyleManager.get_default()
        if sm.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._theme_btn.set_icon_name("weather-clear-night-symbolic")
        else:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._theme_btn.set_icon_name("weather-clear-symbolic")

    def _on_export_clicked(self, *_args):
        dialog = Adw.MessageDialog(transient_for=self,
                                   heading=_("Export Data"),
                                   body=_("Choose export format:"))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("csv", "CSV")
        dialog.add_response("json", "JSON")
        dialog.set_response_appearance("csv", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_export_format_chosen)
        dialog.present()

    def _on_export_format_chosen(self, dialog, response):
        if response not in ("csv", "json"):
            return
        self._export_fmt = response
        fd = Gtk.FileDialog()
        fd.set_initial_name(f"desktop-export.{response}")
        fd.save(self, None, self._on_export_save)

    def _on_export_save(self, dialog, result):
        try:
            path = dialog.save_finish(result).get_path()
        except Exception:
            return
        if not self.desktop_file:
            return
        data = [{"key": k, "value": v} for k, v in self.desktop_file.entries.items()]
        for (k, loc), v in self.desktop_file.localized.items():
            data.append({"key": f"{k}[{loc}]", "value": v})
        if not data:
            return
        if self._export_fmt == "csv":
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["key", "value"])
                w.writeheader()
                w.writerows(data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def _update_status_bar(self):
        self._status_bar.set_text("Last updated: " + _dt_now.now().strftime("%Y-%m-%d %H:%M"))

